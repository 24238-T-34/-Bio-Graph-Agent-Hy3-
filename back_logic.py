from LLM_SYS import BioBrainAgent
from IO_SYS import GraphVisualizer,PDFProcessor
import os
import re
import collections
import concurrent.futures

# =====================================================================
# 4. 系统总调度管道（核心：增量式累加记忆）
# =====================================================================
class BioGraphPipeline:
    def __init__(self, api_key, model="tencent/hy3-preview",base_url = "https://openrouter.ai/api/v1"):
        self.processor = PDFProcessor()
        # 把前端传进来的 model 继续传给大模型智能体
        self.agent = BioBrainAgent(api_key=api_key, model=model,base_url=base_url)
        self.visualizer = GraphVisualizer()

        # 全局图谱存储（增量更新的基础）
        self.global_entities = []  # 存储格式：[{"standard_name": "...", "aliases": [...]}]
        self.global_relations = []  # 存储格式：[{"source": "...", "target": "...", "relation": "...", "evidence": "..."}]

    def _merge_entities(self, new_entities):
        """将新抽取的实体，合并到全局实体库中（去重并合并别名）"""
        if not new_entities:
            return
        for new_ent in new_entities:
            if not isinstance(new_ent, dict):
                continue
            name = new_ent.get("standard_name")
            if not name:
                continue
            aliases = new_ent.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = [aliases] if aliases else []

            # 检查全局库里是否已存在该标准实体的记录
            match = next((e for e in self.global_entities if e.get("standard_name") == name), None)
            if match:
                # 存在则合并别名并去重
                existing_aliases = match.get("aliases", [])
                match["aliases"] = list(set(existing_aliases + aliases))
            else:
                # 不存在则新增
                self.global_entities.append(new_ent)

    def _merge_relations(self, new_relations):
        """将新抽取的连线关系，合并到全局关系库中（防止完全重复的边，且强校验两端节点合法性）"""
        if not new_relations:
            return

        # 收集全局已登记的所有合法实体名（含别名）映射
        std_map = {}
        for e in self.global_entities:
            s_name = str(e.get("standard_name", "")).strip()
            if s_name:
                std_map[s_name.lower()] = s_name
                for a in e.get("aliases", []):
                    if a:
                        std_map[str(a).strip().lower()] = s_name

        for new_rel in new_relations:
            if not isinstance(new_rel, dict):
                continue
            s = new_rel.get("source")
            t = new_rel.get("target")
            r = new_rel.get("relation")
            if not s or not t:
                continue

            s_clean = str(s).strip()
            t_clean = str(t).strip()
            s_std = std_map.get(s_clean.lower())
            t_std = std_map.get(t_clean.lower())

            # 🛡️ 校验两端节点：若端点未在已登记实体库中，坚决拦截
            if not s_std or not t_std:
                print(f"   ⚠️ [关系防线] 拦截非法关系（端点未在实体字典中登记）: '{s}' -> '{t}'")
                continue

            # 规范化端点为全局标准名
            new_rel["source"] = s_std
            new_rel["target"] = t_std

            if s_std == t_std:
                continue

            # 判断这条边是否已经存在（根据起点、终点和关系类型）
            duplicate = any(
                item.get("source") == s_std and
                item.get("target") == t_std and
                item.get("relation") == r
                for item in self.global_relations
            )
            if not duplicate:
                self.global_relations.append(new_rel)

    @staticmethod
    def _is_entity_grounded_in_text(entity_name: str, text: str) -> bool:
        """使用弹性正则检查某个实体名称是否真实存在于文献原文或证据中"""
        if not entity_name or not isinstance(entity_name, str):
            return False
        clean_name = entity_name.strip()
        if len(clean_name) < 2:
            return False

        # 1. 如果是纯英文/数字/常见分子符号代号 (如 TGFBR1, p53, Smad2, CDK-4)
        if re.search(r'^[a-zA-Z0-9_\-\s/+\.\(\)]+$', clean_name):
            core_name = clean_name.strip("()[]{}").strip()
            if len(core_name) < 2:
                return False
            # 采用单词边界匹配 (前后非字母数字)
            pattern = rf"(?<![a-zA-Z0-9]){re.escape(core_name)}(?![a-zA-Z0-9])"
            if re.search(pattern, text, re.IGNORECASE):
                return True
            # 支持常见连字符变体 (如 Smad-2 vs Smad2, NF-kB vs NFkB)
            if "-" in core_name or " " in core_name:
                alt = re.sub(r'[-\s]+', '', core_name)
                alt_pattern = rf"(?<![a-zA-Z0-9]){re.escape(alt)}(?![a-zA-Z0-9])"
                if re.search(alt_pattern, text, re.IGNORECASE):
                    return True
        else:
            # 2. 中文或混合语言：子串包含检索
            if clean_name in text:
                return True

        return False

    def _ground_and_recover_chunk_hallucinations(self, chunk_text: str, ents: list, rels: list, c_source: str, enabled: bool = True):
        """
        切块结束后的终审拦截与正则文献兜底追溯器：
        - 收集该切块所有关系端点；
        - 坚决剔除任何包含生化动作伪节点（如“磷酸化”、“入核转运”）的关系；
        - 若开启兜底 (enabled=True)：对于未在初选实体字典中登记的端点，在切块原文/证据中执行弹性正则匹配；
          若原文确有其实体，则自动回填创建实体并入 ents（落实为真实节点，消除粉色幻觉！）；
          若原文完全未出现，则判定为模型虚构伪节点，安全剔除该关系；
        - 若关闭兜底 (enabled=False)：直接剔除两端未登记的关系，杜绝粉色孤岛。
        """
        if not rels:
            return ents, []

        std_map = {}
        for e in ents:
            if isinstance(e, dict):
                s_name = str(e.get("standard_name", "")).strip()
                if s_name:
                    std_map[s_name.lower()] = s_name
                    for a in e.get("aliases", []):
                        if a:
                            std_map[str(a).strip().lower()] = s_name

        recovered_entities_count = 0
        valid_relations = []

        for rel in rels:
            if not isinstance(rel, dict):
                continue
            s_raw = str(rel.get("source", "")).strip()
            t_raw = str(rel.get("target", "")).strip()
            if not s_raw or not t_raw or s_raw == t_raw:
                continue

            rel_valid = True
            endpoints_to_check = [("source", s_raw), ("target", t_raw)]

            for role, node_name in endpoints_to_check:
                node_lower = node_name.lower()
                if node_lower in std_map:
                    # 已登记实体，标准化
                    rel[role] = std_map[node_lower]
                else:
                    # 未登记端点：判断是否开启正则补漏
                    if enabled:
                        evidence = str(rel.get("evidence", ""))
                        search_scope = f"{chunk_text}\n{evidence}"
                        if self._is_entity_grounded_in_text(node_name, search_scope):
                            # 🎉 正则兜底命中！第一轮漏检的文献真实体，立刻落实回填为正规实体
                            print(f"   🔍 [正则兜底命中] 成功在文献中匹配到端点 '{node_name}'，已自动落实为真实实体！")
                            rescued_ent = {
                                "standard_name": node_name,
                                "aliases": [],
                                "category": "文献追溯实体",
                                "doc_source": c_source
                            }
                            ents.append(rescued_ent)
                            std_map[node_lower] = node_name
                            rel[role] = node_name
                            recovered_entities_count += 1
                        else:
                            # 🚫 文献无据，纯属模型幻觉捏造
                            print(f"   🛡️ [幻觉终审拦截] 端点 '{node_name}' 未在文献原文中找到任何文字支撑，已安全剔除虚构关系: '{s_raw}' -> '{t_raw}'")
                            rel_valid = False
                            break
                    else:
                        # 补漏关闭：严格丢弃未登记端点
                        print(f"   ⚠️ [未登记端点拦截] 端点 '{node_name}' 未在实体库中登记 (补漏开关已关闭)，已剔除该关系: '{s_raw}' -> '{t_raw}'")
                        rel_valid = False
                        break

            if rel_valid:
                valid_relations.append(rel)

        if recovered_entities_count > 0:
            print(f"   🧬 [切块汇总] 本切块通过正则文献兜底成功抢救落实了 {recovered_entities_count} 个漏检实体！")

        return ents, valid_relations

    def run(self, pdf_path, start_page=0, end_page=None, is_summary_only=False,use_reflection=True,source_name="未知文献",entity_lang="关闭 (保持原文语言)",output_lang="zh",progress_callback=None,concurrency=4,vision_strategy="off",vision_keyword="",vision_model=None,enable_relation_grounding=True):
        print("🚀 [Pipeline] 启动全自动化生物知识图谱构建系统...")

        current_source = os.path.basename(pdf_path)

        print(f"📌 [Pipeline] 当前处理文献来源已锁定: {current_source}")

        def report_progress(current_step, total_steps, msg):
            if progress_callback:
                progress_callback(current_step, total_steps, msg)

        is_en = "en" in output_lang.lower()

        # ---------------------------------------------------------
        # 📷 前置视觉转译流水线 (Upfront Vision Transcription)
        # ---------------------------------------------------------
        vision_chunks = []
        vision_chunk_sources = []
        if vision_strategy and vision_strategy != "off":
            print(f"👁️ [Pipeline] 启动机制图前置视觉转译 (策略: {vision_strategy}, 关键词: '{vision_keyword}')...")
            msg_vision_init = (
                f"📷 [Vision] Sniffing figures in pages {start_page + 1} to {end_page}..."
                if is_en else
                f"📷 [视觉解析] 正在检索第 {start_page + 1} 到 {end_page} 页的候选机制图..."
            )
            report_progress(0.02, 1.0, msg_vision_init)

            figures = self.processor.extract_figures(
                pdf_path,
                start_page=start_page,
                end_page=end_page,
                mode=vision_strategy,
                keyword=vision_keyword
            )

            if figures:
                msg_fig_found = (
                    f"📷 [Vision] Found {len(figures)} candidate figure(s). Transcribing mechanism text..."
                    if is_en else
                    f"📷 [视觉解析] 命中 {len(figures)} 张目标插图，正在调用视觉模型转译为学术机制文本..."
                )
                report_progress(0.05, 1.0, msg_fig_found)

                for f_idx, fig in enumerate(figures):
                    fig_label = fig.get("label", f"Fig_{f_idx+1}")
                    fig_caption = fig.get("caption", "")
                    fig_page = fig.get("page", start_page + 1)

                    text_transcription = self.agent.transcribe_figure_to_text(
                        image_bytes=fig["image_bytes"],
                        image_ext=fig.get("ext", "png"),
                        caption=fig_caption,
                        vision_model=vision_model,
                        output_lang=output_lang
                    )
                    if text_transcription and text_transcription.strip():
                        # 组装为带学术元数据的机制文本 Chunk，融入后续两阶段实体与关系抽取流
                        v_chunk = (
                            f"【文献机制通路图解析 / Visual Figure: {fig_label} (P.{fig_page})】\n"
                            f"图注说明: {fig_caption}\n"
                            f"分子调控机制与级联拓扑:\n{text_transcription}"
                        )
                        vision_chunks.append(v_chunk)
                        vision_chunk_sources.append(f"{source_name} [Figure: {fig_label} (P.{fig_page})]")
            else:
                if vision_strategy == "match" and vision_keyword:
                    print(f"ℹ️ [Pipeline] 未在选定页码中匹配到关键词 '{vision_keyword}' 的关联插图。")

        # ---------------------------------------------------------
        # 🚀 模式一：仅摘要模式 (混合双打流)
        # ---------------------------------------------------------
        if is_summary_only:
            # start_page 在前端传过来时减了1，这里加1是为了人类阅读直观
            print(f"⚡ 开启摘要模式，仅在第 {start_page + 1} 到 {end_page} 页中寻找摘要...")
            msg_init = f"⚡ [Init] Regex scanning pages {start_page + 1} to {end_page}..." if is_en else f"⚡ [初始化] 开启摘要模式，正在正则扫描第 {start_page + 1} 到 {end_page}..."
            report_progress(0.1, 1.0, msg_init)

            # 注意：这里的 raw_text 已经严格限制在了用户选定的页码范围内！
            raw_text = self.processor.get_raw_text(pdf_path, start_page, end_page)
            final_text = ""

            # 1. 第一道防线：正则捕获
            abstract_text = self.processor.extract_abstract_regex(raw_text)

            if abstract_text:
                print(f"🔍 正则成功捕获疑似摘要 (长度: {len(abstract_text)})，请求大模型质检...")
                msg_verify = "🔍 [Verifying] Regex caught potential abstract, requesting LLM content check..." if is_en else "🔍 [质检中] 正则捕获疑似摘要，请求大模型进行内容质检..."
                report_progress(0.12, 1.0, msg_verify)
                verified = self.agent.verify_and_clean_abstract(abstract_text)
                if "[NOT_ABSTRACT]" not in verified:
                    final_text = verified
                    print("✅ 质检通过，已获取高纯度摘要！")
                else:
                    print("⚠️ 大模型认为正则提取的不是有效摘要。")

            # 2. 终极兜底：让大模型在选定的页码文本 (raw_text) 中硬找
            if not final_text:
                print("⚠️ 启动大模型全量兜底搜索 (范围仅限选定页码)...")
                msg_fallback = "⚠️ [Fallback] Starting full LLM search for abstract block..." if is_en else "⚠️ [兜底搜索] 启动大模型全量兜底寻找摘要区块..."
                report_progress(0.14, 1.0, msg_fallback)
                fallback_result = self.agent.fallback_extract_abstract(raw_text)
                if "[NOT_ABSTRACT]" not in fallback_result:
                    final_text = fallback_result
                    print("✅ 兜底成功，大模型已捕获摘要！")
                else:
                    # 如果这几页里真没摘要，检查是否有视觉块
                    if not vision_chunks:
                        raise Exception("❌ 无法在指定页码中找到摘要内容，请尝试扩大页码范围，或关闭摘要模式。")
                    else:
                        print("⚠️ 未找到纯文本摘要，但捕获了机制图转译文本，将以机制图为主进行构建。")

            text_chunks = [final_text] if final_text else []

        # ---------------------------------------------------------
        # 🐢 模式二：全文解析模式 (传统的暴力分块)
        # ---------------------------------------------------------
        else:
            print(f"🐢 开启普通全文分块模式 (第 {start_page + 1} 到 {end_page} 页)...")
            text_chunks = self.processor.extract_chunks(pdf_path, start_page, end_page)

        # =========================================================
        # 融合视觉块与文本块，构建统一分析输入流
        # =========================================================
        chunks = vision_chunks + text_chunks
        chunk_sources = vision_chunk_sources + [source_name] * len(text_chunks)
        total_chunks = len(chunks)

        if not chunks:
            return self.global_entities, self.global_relations

        # =============================================================
        # 🚀 切块级局部高纯度闭环提取流水线 (Chunk-Centric Localized Pipeline)
        # 彻底解决两阶段全局大字典污染导致的幻觉激增问题！
        # 每个切块独立提取本地实体，并严格仅基于本地实体推演该切块的关系
        # =============================================================
        default_reason = "No detailed explanation" if is_en else "无详细解释"
        source_prefix = "Source" if is_en else "源自"
        worker_count = max(1, min(int(concurrency), total_chunks))

        def _process_single_chunk(idx, chunk_text, c_source):
            """单个切块的自给自足闭环处理函数"""
            try:
                # 1. 块内精准实体提取与反思
                ents = self.agent.extract_entities_with_reflection(
                    chunk_text, use_reflection=use_reflection, entity_lang=entity_lang
                )
                if not isinstance(ents, list):
                    ents = []

                for ent in ents:
                    if isinstance(ent, dict):
                        ent["doc_source"] = c_source

                # 2. 紧扣当前切块本地实体的闭环关系抽取 (绝无跨切块全局无关大字典污染！)
                rels = []
                if ents:
                    rels = self.agent.extract_relations(chunk_text, ents)
                    if not isinstance(rels, list):
                        rels = []

                    source_tag = c_source if c_source != source_name else current_source
                    for rel in rels:
                        if isinstance(rel, dict):
                            rel["doc_source"] = c_source
                            original_reason = rel.get("reason", default_reason)
                            rel["reason"] = f"{original_reason} [{source_prefix}: {source_tag}]"

                # 3. 🔍 切块结束后的终审拦截与正则文献兜底追溯落实
                ents, rels = self._ground_and_recover_chunk_hallucinations(
                    chunk_text=chunk_text,
                    ents=ents,
                    rels=rels,
                    c_source=c_source,
                    enabled=enable_relation_grounding
                )

                return idx, ents, rels, None
            except Exception as exc:
                return idx, [], [], exc

        raw_chunk_results = [([], []) for _ in range(total_chunks)]

        if total_chunks == 1 or worker_count == 1:
            # 单块或串行模式：直观顺畅推进
            for idx in range(total_chunks):
                chunk = chunks[idx]
                c_source = chunk_sources[idx]
                msg = (
                    f"🧠 [Chunk {idx + 1}/{total_chunks}] Extracting local entities & relations..."
                    if is_en else
                    f"🧠 [文本切块 {idx + 1}/{total_chunks}] 正在闭环推演局部实体与调控关系..."
                )
                report_progress(0.2 + 0.7 * (idx / total_chunks), 1.0, msg)
                _, ents, rels, err = _process_single_chunk(idx, chunk, c_source)
                if err:
                    print(f"⚠️ [Chunk {idx + 1}] 处理遇到异常 (已跳过): {err}")
                raw_chunk_results[idx] = (ents, rels)
        else:
            # 多切块并发模式：每个 Worker 独立走完本地切块的实体+关系闭环，无两阶段屏障阻塞！
            print(f"🚀 [Pipeline 并发引擎] 启动切块局部闭环并发流水线: 切块总数={total_chunks}, 并发线程数={worker_count}")
            completed_chunks = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(_process_single_chunk, i, chunks[i], chunk_sources[i]): i
                    for i in range(total_chunks)
                }
                for fut in concurrent.futures.as_completed(futures):
                    idx, ents, rels, err = fut.result()
                    if err:
                        print(f"⚠️ [Chunk {idx + 1}] 并发处理遇到异常 (已跳过): {err}")
                    raw_chunk_results[idx] = (ents, rels)
                    completed_chunks += 1

                    progress = 0.15 + 0.80 * (completed_chunks / total_chunks)
                    msg = (
                        f"⚡ [Progress {completed_chunks}/{total_chunks}] Chunk {idx + 1} analyzed..."
                        if is_en else
                        f"⚡ [并发进度 {completed_chunks}/{total_chunks}] 切块 {idx + 1} 分析完成..."
                    )
                    report_progress(progress, 1.0, msg)

        # 汇总阶段：主线程统一安全归并至全局实体库与关系库
        for idx in range(total_chunks):
            ents, rels = raw_chunk_results[idx]
            self._merge_entities(ents)
            self._merge_relations(rels)

        print(f"\n📊 [Pipeline] 分析完毕！全局共捕获 {len(self.global_entities)} 个标准实体，{len(self.global_relations)} 条调控关系。")

        msg_done = (
            f"✨ Analysis complete! Caught {len(self.global_entities)} entities, {len(self.global_relations)} relations."
            if is_en else
            f"✨ 分析完毕！本轮共捕获 {len(self.global_entities)} 个实体，{len(self.global_relations)} 条关系。"
        )
        report_progress(1.0, 1.0, msg_done)
        return self.global_entities, self.global_relations


# =====================================================================
# 🧠 图谱挖掘引擎：负责在已有知识图谱中寻找拓扑路径
# =====================================================================
class GraphMiner:
    @staticmethod
    def find_paths(relations, start_node, end_node, max_depth=4, exclude_shortcuts=True):
        """
        无向图 BFS（广度优先搜索）算法：寻找两个节点之间的所有路径
        :param relations: 全局关系字典列表
        :param start_node: 起点名称
        :param end_node: 终点名称
        :param max_depth: 最大搜索深度
        :param exclude_shortcuts: 💡 是否屏蔽被洗树功能降级的捷径边（默认 True，逼迫算法寻找深层机制）
        :return: list of paths
        """
        # 1. 构建双向邻接表 (Adjacency List)
        adj = collections.defaultdict(list)
        for rel in relations:
            # 🛡️ 核心屏蔽网：如果是捷径边，直接当它不存在！
            if exclude_shortcuts and rel.get("is_shortcut", False):
                continue

            src = rel.get("source", "").strip()
            tgt = rel.get("target", "").strip()
            if not src or not tgt:
                continue

            # 正向边
            adj[src].append((tgt, rel))
            # 反向边 (无向化处理)
            adj[tgt].append((src, rel))

        # 2. 广度优先搜索 (BFS) 寻找所有路径
        queue = collections.deque([(start_node, [], {start_node})])
        valid_paths = []

        while queue:
            current, path, visited = queue.popleft()

            # 触达终点，保存路径
            if current == end_node and len(path) > 0:
                valid_paths.append(path)
                continue

            # 超过最大步数限制，不再往下钻取
            if len(path) >= max_depth:
                continue

            # 遍历当前节点的所有邻居
            for neighbor, edge in adj[current]:
                if neighbor not in visited:
                    new_visited = set(visited)
                    new_visited.add(neighbor)
                    new_path = list(path)
                    new_path.append(edge)

                    queue.append((neighbor, new_path, new_visited))

        # 3. 按路径长度（步数）从小到大排序返回
        valid_paths.sort(key=len)
        return valid_paths

# =====================================================================
# ⚙️ 启动入口
# =====================================================================
if __name__ == "__main__":
    MY_API_KEY = ""
    PDF_FILE = "sample_paper.pdf"  # 请确保这个文件存在

    if os.path.exists(PDF_FILE):
        pipeline = BioGraphPipeline(api_key=MY_API_KEY)
        pipeline.run(PDF_FILE)
    else:
        print(f"❌ 错误：未能在当前目录下找到测试文件 '{PDF_FILE}'，请放置一个PDF并重命名后再试。")