from LLM_SYS import BioBrainAgent
from IO_SYS import GraphVisualizer,PDFProcessor
import os
import collections

# =====================================================================
# 4. 系统总调度管道（核心：增量式累加记忆）
# =====================================================================
class BioGraphPipeline:
    def __init__(self, api_key, model="tencent/hy3-preview"):
        self.processor = PDFProcessor()
        # 把前端传进来的 model 继续传给大模型智能体
        self.agent = BioBrainAgent(api_key=api_key, model=model)
        self.visualizer = GraphVisualizer()

        # 全局图谱存储（增量更新的基础）
        self.global_entities = []  # 存储格式：[{"standard_name": "...", "aliases": [...]}]
        self.global_relations = []  # 存储格式：[{"source": "...", "target": "...", "relation": "...", "evidence": "..."}]

    def _merge_entities(self, new_entities):
        """将新抽取的实体，合并到全局实体库中（去重并合并别名）"""
        for new_ent in new_entities:
            name = new_ent["standard_name"]
            aliases = new_ent.get("aliases", [])

            # 检查全局库里是否已存在该标准实体的记录
            match = next((e for e in self.global_entities if e["standard_name"] == name), None)
            if match:
                # 存在则合并别名并去重
                match["aliases"] = list(set(match["aliases"] + aliases))
            else:
                # 不存在则新增
                self.global_entities.append(new_ent)

    def _merge_relations(self, new_relations):
        """将新抽取的连线关系，合并到全局关系库中（防止完全重复的边）"""
        for new_rel in new_relations:
            # 判断这条边是否已经存在（根据起点、终点和关系类型）
            duplicate = any(
                r["source"] == new_rel["source"] and
                r["target"] == new_rel["target"] and
                r["relation"] == new_rel["relation"]
                for r in self.global_relations
            )
            if not duplicate:
                self.global_relations.append(new_rel)

    def run(self, pdf_path, start_page=0, end_page=None, is_summary_only=False,use_reflection=True,source_name="未知文献",entity_lang="关闭 (保持原文语言)"):
        print("🚀 [Pipeline] 启动全自动化生物知识图谱构建系统...")

        current_source = os.path.basename(pdf_path)

        print(f"📌 [Pipeline] 当前处理文献来源已锁定: {current_source}")

        # ---------------------------------------------------------
        # 🚀 模式一：仅摘要模式 (混合双打流)
        # ---------------------------------------------------------
        if is_summary_only:
            # start_page 在前端传过来时减了1，这里加1是为了人类阅读直观
            print(f"⚡ 开启摘要模式，仅在第 {start_page + 1} 到 {end_page} 页中寻找摘要...")

            # 注意：这里的 raw_text 已经严格限制在了用户选定的页码范围内！
            raw_text = self.processor.get_raw_text(pdf_path, start_page, end_page)
            final_text = ""

            # 1. 第一道防线：正则捕获
            abstract_text = self.processor.extract_abstract_regex(raw_text)

            if abstract_text:
                print(f"🔍 正则成功捕获疑似摘要 (长度: {len(abstract_text)})，请求大模型质检...")
                verified = self.agent.verify_and_clean_abstract(abstract_text)
                if "[NOT_ABSTRACT]" not in verified:
                    final_text = verified
                    print("✅ 质检通过，已获取高纯度摘要！")
                else:
                    print("⚠️ 大模型认为正则提取的不是有效摘要。")

            # 2. 终极兜底：让大模型在选定的页码文本 (raw_text) 中硬找
            if not final_text:
                print("⚠️ 启动大模型全量兜底搜索 (范围仅限选定页码)...")
                fallback_result = self.agent.fallback_extract_abstract(raw_text)
                if "[NOT_ABSTRACT]" not in fallback_result:
                    final_text = fallback_result
                    print("✅ 兜底成功，大模型已捕获摘要！")
                else:
                    # 如果这几页里真没摘要，就直接中断并报错给前端
                    raise Exception("❌ 无法在指定页码中找到摘要内容，请尝试扩大页码范围，或关闭摘要模式。")

            # 摘要模式下，处理块就只有这精炼的 1 个块
            chunks = [final_text]

        # ---------------------------------------------------------
        # 🐢 模式二：全文解析模式 (传统的暴力分块)
        # ---------------------------------------------------------
        else:
            print(f"🐢 开启普通全文分块模式 (第 {start_page + 1} 到 {end_page} 页)...")
            chunks = self.processor.extract_chunks(pdf_path, start_page, end_page)

        # =========================================================
        # 准备变量，开始让 Agent 提取实体和关系
        # =========================================================
        total_chunks = len(chunks)
        all_entities = []
        all_relations = []

        if not chunks:
            return self.global_entities, self.global_relations

        # 2. 循环流水线处理
        for idx, chunk in enumerate(chunks):
            print(f"\n🧠 [Pipeline] 正在处理第 {idx + 1}/{len(chunks)} 个文本块...")

            chunk_entities = self.agent.extract_entities_with_reflection(chunk,use_reflection=use_reflection,entity_lang=entity_lang)
            self._merge_entities(chunk_entities)

            for ent in chunk_entities:
                ent["doc_source"] = source_name

            chunk_relations = self.agent.extract_relations(chunk, self.global_entities)
            self._merge_relations(chunk_relations)

            for rel in chunk_relations:
                rel["doc_source"] = source_name
                # 按照你的要求，直接把来源拼接到原因 (reason) 里面，方便图谱展示
                original_reason = rel.get("reason", "无详细解释")
                rel["reason"] = f"{original_reason} [源自: {current_source}]"

        print(f"\n📊 [Pipeline] 分析完毕！全局共捕获 {len(self.global_entities)} 个标准实体，{len(self.global_relations)} 条调控关系。")

        # 3. 可视化
        # self.visualizer.generate_html(self.global_entities, self.global_relations)
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