from LLM_SYS import BioBrainAgent
from IO_SYS import GraphVisualizer,PDFProcessor
import os
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
        """将新抽取的连线关系，合并到全局关系库中（防止完全重复的边）"""
        if not new_relations:
            return
        for new_rel in new_relations:
            if not isinstance(new_rel, dict):
                continue
            s = new_rel.get("source")
            t = new_rel.get("target")
            r = new_rel.get("relation")
            if not s or not t:
                continue
            # 判断这条边是否已经存在（根据起点、终点和关系类型）
            duplicate = any(
                item.get("source") == s and
                item.get("target") == t and
                item.get("relation") == r
                for item in self.global_relations
            )
            if not duplicate:
                self.global_relations.append(new_rel)

    def run(self, pdf_path, start_page=0, end_page=None, is_summary_only=False,use_reflection=True,source_name="未知文献",entity_lang="关闭 (保持原文语言)",output_lang="zh",progress_callback=None,concurrency=4,vision_strategy="off",vision_keyword="",vision_model=None):
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

        # 单块情况（例如仅有1张机制图、或纯摘要模式）：采用极简单流处理
        if total_chunks == 1:
            chunk = chunks[0]
            c_source = chunk_sources[0]
            msg1 = f"🧠 [Single Chunk] [Step 1/2] Deeply extracting entities..." if is_en else f"🧠 [单一切块] [Step 1/2] 正在深度提取实体..."
            report_progress(0.25, 1.0, msg1)
            chunk_entities = self.agent.extract_entities_with_reflection(chunk, use_reflection=use_reflection, entity_lang=entity_lang)
            for ent in chunk_entities:
                if isinstance(ent, dict):
                    ent["doc_source"] = c_source
            self._merge_entities(chunk_entities)

            msg2 = f"🔗 [Single Chunk] [Step 2/2] Deducing network relations..." if is_en else f"🔗 [单一切块] [Step 2/2] 正在推演实体间的网络调控关系..."
            report_progress(0.65, 1.0, msg2)
            chunk_relations = self.agent.extract_relations(chunk, self.global_entities)
            default_reason = "No detailed explanation" if is_en else "无详细解释"
            source_prefix = "Source" if is_en else "源自"
            source_tag = c_source if c_source != source_name else current_source
            for rel in chunk_relations:
                if isinstance(rel, dict):
                    rel["doc_source"] = c_source
                    original_reason = rel.get("reason", default_reason)
                    rel["reason"] = f"{original_reason} [{source_prefix}: {source_tag}]"
            self._merge_relations(chunk_relations)

            print(f"\n📊 [Pipeline] 分析完毕！全局共捕获 {len(self.global_entities)} 个标准实体，{len(self.global_relations)} 条调控关系。")
            msg_done = f"✨ Analysis complete! Caught {len(self.global_entities)} entities, {len(self.global_relations)} relations." if is_en else f"✨ 分析完毕！本轮共捕获 {len(self.global_entities)} 个实体，{len(self.global_relations)} 条关系。"
            report_progress(1.0, 1.0, msg_done)
            return self.global_entities, self.global_relations

        # -------------------------------------------------------------
        # 🚀 多块情况：启动两阶段多线程并发提取流水线
        # -------------------------------------------------------------
        worker_count = max(1, min(int(concurrency), total_chunks))
        print(f"🚀 [Pipeline 并发引擎] 启动两阶段多线程并发提取: 切块总数={total_chunks}, 并发线程数={worker_count}")

        # =============================================================
        # 阶段 1：并行实体提取 (Phase 1: Parallel Entity Extraction)
        # =============================================================
        raw_chunk_entities = [[] for _ in range(total_chunks)]

        def _worker_entity(idx, chunk_text):
            try:
                ents = self.agent.extract_entities_with_reflection(
                    chunk_text, use_reflection=use_reflection, entity_lang=entity_lang
                )
                return idx, ents, None
            except Exception as exc:
                return idx, [], exc

        completed_entities = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_worker_entity, i, chunk): i
                for i, chunk in enumerate(chunks)
            }
            for fut in concurrent.futures.as_completed(futures):
                idx, ents, err = fut.result()
                if err:
                    print(f"⚠️ [Chunk {idx + 1}] 实体提取遇到异常 (已跳过): {err}")
                raw_chunk_entities[idx] = ents if ents else []
                completed_entities += 1

                # 主线程安全更新进度：0.15 -> 0.52
                progress = 0.15 + 0.37 * (completed_entities / total_chunks)
                msg = (
                    f"🧠 [Entities {completed_entities}/{total_chunks}] Chunk {idx + 1} extracted..."
                    if is_en else
                    f"🧠 [实体并发抽取 {completed_entities}/{total_chunks}] 文本块 {idx + 1} 提取完成..."
                )
                report_progress(progress, 1.0, msg)

        # 阶段 1 汇总：主线程安全合并至全局实体库
        for idx, ents in enumerate(raw_chunk_entities):
            c_source = chunk_sources[idx]
            for ent in ents:
                if isinstance(ent, dict):
                    ent["doc_source"] = c_source
            self._merge_entities(ents)

        msg_entities_done = (
            f"🧬 Merged {len(self.global_entities)} standard entities. Starting relation deductions..."
            if is_en else
            f"🧬 全局实体合并完成 (共 {len(self.global_entities)} 个标准实体)，即将推演关系网..."
        )
        report_progress(0.55, 1.0, msg_entities_done)

        # =============================================================
        # 阶段 2：共享完整实体字典的全量并行关系推演 (Phase 2: Parallel Relation Extraction)
        # =============================================================
        snapshot_entities = list(self.global_entities)
        raw_chunk_relations = [[] for _ in range(total_chunks)]

        def _worker_relation(idx, chunk_text):
            try:
                rels = self.agent.extract_relations(chunk_text, snapshot_entities)
                return idx, rels, None
            except Exception as exc:
                return idx, [], exc

        completed_relations = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_worker_relation, i, chunk): i
                for i, chunk in enumerate(chunks)
            }
            for fut in concurrent.futures.as_completed(futures):
                idx, rels, err = fut.result()
                if err:
                    print(f"⚠️ [Chunk {idx + 1}] 关系推演遇到异常 (已跳过): {err}")
                raw_chunk_relations[idx] = rels if rels else []
                completed_relations += 1

                # 主线程安全更新进度：0.55 -> 0.95
                progress = 0.55 + 0.40 * (completed_relations / total_chunks)
                msg = (
                    f"🔗 [Relations {completed_relations}/{total_chunks}] Chunk {idx + 1} deduced..."
                    if is_en else
                    f"🔗 [关系并发推演 {completed_relations}/{total_chunks}] 文本块 {idx + 1} 推演完成..."
                )
                report_progress(progress, 1.0, msg)

        # 阶段 2 汇总：主线程格式化 Hover 详情并合并关系
        default_reason = "No detailed explanation" if is_en else "无详细解释"
        source_prefix = "Source" if is_en else "源自"
        for idx, rels in enumerate(raw_chunk_relations):
            c_source = chunk_sources[idx]
            source_tag = c_source if c_source != source_name else current_source
            for rel in rels:
                if isinstance(rel, dict):
                    rel["doc_source"] = c_source
                    original_reason = rel.get("reason", default_reason)
                    rel["reason"] = f"{original_reason} [{source_prefix}: {source_tag}]"
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