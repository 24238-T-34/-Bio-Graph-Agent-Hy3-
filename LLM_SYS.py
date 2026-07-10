import json
from openai import OpenAI


class BioBrainAgent:
    def __init__(self, api_key, base_url="https://openrouter.ai/api/v1", model="tencent/hy3-preview"):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        print(f"🔧 [System] 已加载底层模型: {self.model}")

    def _clean_json_string(self, raw_str):
        # 💡 真正的安全气囊：直接判断传进来的 raw_str 是不是空的就行了
        if raw_str is None:
            raise Exception("大模型未能正常返回内容（返回值为空），可能是 API 被限流或网络超时，请检查 API Key 或稍后再试。")

        return raw_str.replace("```json", "").replace("```", "").strip()

    def _ask_llm(self, system_prompt, user_content):
        try:
            # 发起真正的 API 请求
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                timeout=60.0  # 60秒超时控制
            )
            # 只有成功拿到 response，才会执行这一行
            return response.choices[0].message.content

        except Exception as e:
            # 🔥 核心防线：如果上面这步崩了，立刻在这里拦截！
            # 这样就能在终端里清清楚楚看到真正的死因（比如：AuthenticationError、RateLimitError 等）
            print(f"\n🚨 [LLM API 核心报错] 接口请求失败了！真实死因 -> {e}")

            # 主动把这个真实的错误扔给外层的 Step 1，不再往下走，彻底绝杀 NameError！
            raise e

    def extract_entities_with_reflection(self, text,use_reflection,entity_lang="关闭 (保持原文语言)"):
        """智能体工作流：提取包含标准名和别名的实体字典"""

        language_instruction = ""
        if "中文" in entity_lang:
            language_instruction = "\n【⚠️ 强力约束】：请务必将提取出的所有实体（主节点）的“标准名”统一翻译并输出为**纯中文**（如果是专有英文缩写可保留，但常规名词必须严格用中文，并且最好使用中文学术圈的常见名）。"
        elif "English" in entity_lang:
            language_instruction = "\n【⚠️ 强力约束】：请务必将提取出的所有实体（主节点）的“标准名”统一翻译并输出为**纯英文 (English)**（即便原文是中文，也必须翻译成英文）。"

        prompt_s1 = f"""你是一个严谨的生物学实体识别专家。请从给定的文献中提取出所有的核心生物实体（如基因、蛋白质、疾病、细胞、药物等）。
        
        【核心任务】：你需要为每个实体确定一个【标准名称 (standard_name)】，并把文中指代该实体的其他有效表达作为【别名 (aliases)】。
        
        【实体提取与别名规范（极其重要，严格遵守）】：
        1. 确立【标准名称】：优先使用官方简写或公认名称（如 "p53", "MDM2"），长度尽量控制在 1-3 个单词内。
        2. 确立【别名】：只保留真正的生物学同义词、全称或简称（如 "TP53"）。
        3. 🚫 严禁保留无意义修饰变体：绝对不要把加了状态语、修饰语的词组当作别名提取！（例如：遇到 "endogenous p53", "p53 protein", "~53"，请直接忽略这些噪音，不要放入别名）。
        4. 🚫 严禁提取“关系/事件”为实体（极度致命）：例如绝对不要把诸如 "p53-MDM2 interaction", "MDM2 overexpression", "binding to DNA" 提取为实体！这些属于【关系】或【事件】，它们应该在关系提取阶段作为连线出现，而不是独立的节点！实体必须是纯粹的生物学物质名词。
        5.文章讨论中带有方向性名词的应当转为中性表现，如原文为”促进代谢“应当提取为”代谢活性“而不是代谢
        6. 🚫 严禁生成重复的同源节点：例如不要让图谱里出现多个本质上都是 p53或p53系统 的节点。除了明确的突变型，所有普通 p53 必须归一化为唯一的 "p53"。
        7. ⚠如果遇到同一实体在细节或者功能存在相反或明显区别的子对象时，应当当作两个不同的实体，尤其是文章探讨了他们的区别及不同影响时，如突变与野生型：如果文中同时明确对比了 "mutant p53"（突变型）和 "wild-type p53"（野生型），请将它们提取为两个【独立的实体】，绝对不能混为一谈。
        {language_instruction}
        
        请严格只输出一个合法的 JSON 数组，绝对不要有其他废话。格式必须如下：（仅作格式参考）
        [
          {{
            "standard_name": "p53",
            "aliases": ["TP53"]
          }},
          {{
            "standard_name": "mutant p53",
            "aliases": ["mutp53"]
          }}
        ]"""

        # 📜 日志埋点 1
        print("   └─ 🧠 [Step 1/2] 正在进行实体初次提取...")
        try:
            raw_s1 = self._ask_llm(prompt_s1, text)
            cleaned_s1 = self._clean_json_string(raw_s1)
        except Exception as e:
            print(f"   ❌ [Step 1/2] 请求超时或失败: {e}")
            return []

        prompt_s1_5 = f"""你是一个严谨的知识图谱数据清洗专家。
        用户将提供一段【原始文献】和一份【初次提取的实体字典】。
        【核心任务】：你需要为每个实体确定一个终极的【标准名称 (standard_name)】，并把真正的同义词保留为【别名 (aliases)】。

        你的任务是进行“外科手术级”的数据清洗：
        
        1. 查漏补缺：是否有关键的生物学实体被完全遗漏了？如果有，请补全。
        2. 🧹 剔除假实体与事件节点（极度重要）：如果发现初次提取的字典里有诸如 "p53-MDM2 interaction", "MDM2 overexpression", "apoptosis activation" 等描述【关系、状态或事件】的词组被错误地当成了实体，请直接将它们【彻底删除】！实体必须是纯粹的物质名词。
        3. 实体去重合并：将不同叫法但指代同一概念的实体强制合并。绝对不能出现多个本质上都是 p53 的独立节点（除非是 mutant vs wild-type 这样在作用上不同的明确对比）。
        4. 📏 标准名精简压缩：如果标准名称过长，请必须将其缩短概括（优先使用官方简写，如 "p53"），并将原来的长名称移入 aliases 中！
        5. 别名瘦身去噪：初次提取的 aliases 中可能混入了大量垃圾信息（如 "p53 protein", "endogenous MDM2", "~53"）。请大刀阔斧地剔除这些带有无意义修饰词的噪音，每个实体只保留最核心的学术同义词！
        6. 拆分错误合并：发现功能截然相反的实体（如突变型和野生型）被合并时，必须将其拆分为独立实体。
        {language_instruction}
        
        请直接输出清洗、合并、精简后的最终 JSON 数组，保持与初次提取相同的格式。绝对不要有其他废话。"""

        # 📜 日志埋点 2

        if use_reflection:
            # 📝 日志埋点 2 (也就是你截图里的 Step 1.5 流程)
            print("    └─ 🪞 [Step 1.5/2] 正在进行大脑自我反思纠错...")
            prompt_s1_5 = prompt_s1_5 + "\n⚠️ 致命警告：不管你有没有发现错误，你的回复必须且只能是一个合法的 JSON 数组 (JSON Array)。如果没有需要修改的地方，请直接返回原始的 JSON 数组。绝不允许输出任何解释性文字！"
            reflection_input = f"【原始文献】:\n{text}\n\n【初次提取】:\n{cleaned_s1}"

            try:
                raw_final = self._ask_llm(prompt_s1_5, reflection_input)
                return json.loads(self._clean_json_string(raw_final))  # 将反思后的结果作为最终结果
            except Exception as e:
                print(f"   ❌ [Step 1.5/2] 反思阶段请求失败或超时: {e}")
                return []
        else:
            # ⏩ 如果用户关闭了开关，直接打印跳过，把初次提取的结果当成最终结果！
            print("    └─ ⏩ [Step 1.5/2] 已关闭自我反思，跳过纠错步骤...")
            raw_final = cleaned_s1
            return json.loads(self._clean_json_string(raw_final))

#        print("   └─ 🪞 [Step 1.5/2] 正在进行大脑自我反思纠错...")
#        reflection_input = f"【原始文献】:\n{text}\n\n【初次提取】:\n{cleaned_s1}"
#
#        try:
#            raw_final = self._ask_llm(prompt_s1_5, reflection_input)
#            return json.loads(self._clean_json_string(raw_final))
#        except Exception as e:
#            print(f"   ❌ [Step 1.5/2] 反思阶段请求失败或超时: {e}")
#            return []

    def extract_relations(self, text, entities_list):
        """根据实体字典，抽取文本中的实体关系"""
        if not entities_list:
            return []

        prompt_s2 = """你是一个计算生物学专家。
        用户将提供一段【原始文献】和一份【确定的实体字典（含标准名称和别名）】。
        请提取出这些实体之间的相互作用。
        
        规则：
        1. 只能提取四种关系："正作用"、"负作用"、"相关"、"包含" (注："包含"用于表示宏观与微观、整体与部分、分类层级的从属关系)。
        2. 你的输出中，"source" 和 "target" 必须严格使用字典中提供的【standard_name】！不要使用文中的原词或别名，从而保证图谱节点的统一。
        3. 只输出合法 JSON 数组格式。格式如下：
        [
          {"source": "标准实体A", "target": "标准实体B", "relation": "正作用/负作用/相关", "evidence": "英文原文"}
        ]"""


        # 📜 日志埋点 3
        print("   └─ 🔗 [Step 2/2] 正在抽取实体间的调控关系网...")
        relation_input = f"【原始文献】:\n{text}\n\n【确定的实体字典】:\n{json.dumps(entities_list, ensure_ascii=False)}"

        try:
            raw_relations = self._ask_llm(prompt_s2, relation_input)
            return json.loads(self._clean_json_string(raw_relations))
        except Exception as e:
            print(f"   ❌ [Step 2/2] 关系抽取阶段请求失败或超时: {e}")
            return []

    def verify_and_clean_abstract(self, raw_abstract):
        """大模型保安：只做判断题，绝对不碰原文本！"""
        prompt = f"""
        你是一个文献审查员。请判断以下文本中，是否真的包含了一篇学术论文的摘要(Abstract)内容。
        你只需要回答 YES 或 NO。绝对不要输出任何其他解释性文字！

        待检验文本：
        {raw_abstract}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            reply = response.choices[0].message.content.strip().upper()

            # 如果判定是摘要，直接把【一字未改】的原始文本退回去！0损耗！
            if "YES" in reply:
                return raw_abstract
            else:
                return "[NOT_ABSTRACT]"
        except Exception as e:
            print(f"⚠️ 质检失败: {e}，默认保留原文。")
            return raw_abstract

    def fallback_extract_abstract(self, full_text):
        """终极兜底：让大模型自己去海量文本里抠摘要"""
        prompt = f"""
        ⚠️ 注意，部分顶级期刊（如 Nature, Science 等）排版非常特殊：
        1. 它们通常没有 "Abstract" 也没有 "Introduction" 等明确的分段标题。
        2. 摘要通常紧随在作者、单位、日期等元数据之后，是一段高度概括研究背景、方法和结论的独立大段落。
        3. 摘要段落结束后的下一个段落，通常会突然开始详细介绍具体的研究背景。

        请凭借你的专业语义理解，精准切割出这唯一的“摘要概括段落”：
        - 彻底剔除论文标题、作者、通讯地址、日期、DOI 等无用的元数据。
        - 绝对不要包含后面的正文（具体背景介绍/引言）内容。
        - 只返回纯净的摘要文本，不要包含任何多余的解释词语。
        - 如果文本中根本没有包含类似摘要的段落，请直接严格回复：[NOT_ABSTRACT]

        论文文本：
        {full_text}
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content.strip()

    def align_global_entities(self, master_entities, new_entities):
        """🌟 核心大招：跨文献实体对齐融合器 (包含别名增强增强识别)"""
        if not master_entities or not new_entities:
            return {}

        # 💡 核心优化：把 entities 里的 aliases (别名) 也提取出来，发给大模型作为重要的对齐参考！
        master_list = [{"name": e.get("standard_name"), "type": e.get("type", "未知"), "aliases": e.get("aliases", [])}
                       for e in master_entities]
        new_list = [{"name": e.get("standard_name"), "type": e.get("type", "未知"), "aliases": e.get("aliases", [])} for e
                    in new_entities]

        prompt = f"""
        你是一个严谨的生物信息学图谱融合专家。
        你的任务是比对【新提取的实体】和【现有知识库实体】，找出它们之间代表“同一个生物学概念”的同义词、缩写或中英文对照。

        【现有知识库实体】:
        {master_list}

        【新提取的实体】:
        {new_list}

        判断标准与严格警告：
        1. 寻找同义基因/蛋白质（如 p53 与 TP53，TNF-alpha 与 TNFA）。
        2. 寻找全称与简称（如 Reactive oxygen species 与 ROS）。
        3. 寻找中英文对照（如 肿瘤坏死因子 与 TNF）。
        4. 💡 重点参考：请充分利用实体提供的 "aliases" (别名) 列表进行交叉比对。如果一个新实体的名称或别名，与现有实体的名称或别名存在交集或高度重合，它们极有可能是同一个概念。
        5. ⚠️ 极其致命：如果两个实体只是“有关系”或者“属于同一类”，绝对不能合并！必须是【完全等价】的概念才能合并！不确定的坚决不合并！

        请输出一个合法的 JSON 字典，格式必须如下：
        {{
            "新实体名称1": "对应的现有实体名称",
            "新实体名称2": "对应的现有实体名称"
        }}
        如果没有发现任何可以合并的实体，请直接输出空字典：{{}}
        绝对不要输出任何其他解释文字！
        """

        try:
            print("    └─ 🧠 [Entity Aligner] 正在呼叫大模型进行跨文献语义比对(别名辅助模式)...")
            raw_response = self._ask_llm(prompt, "请开始比对。")
            clean_json = self._clean_json_string(raw_response)

            if not clean_json:
                return {}

            mapping = json.loads(clean_json)
            return mapping
        except Exception as e:
            print(f"    ⚠️ [Entity Aligner] 实体对齐解析失败，跳过融合: {e}")
            return {}

    def diagnose_graph(self, entities, relations):
        """🤖 核心引擎：AI 图谱智能洗树 (检测同义词、层级与捷径边)"""
        if not entities or not relations:
            return []

        prompt = """你是一个顶级的生物医药知识图谱架构师。
        我将提供一份当前图谱的【实体列表】和【关系连线列表】（包含起点、终点、关系类型和原文证据）。
        请你根据原文证据进行“图谱洗树（Graph Pruning & Merging）”，并返回结构化的 JSON 操作指令。

        你需要执行以下四种操作：
        1. 【合并同义词 (MERGE)】：如果两个节点完全指代同一事物（如“尿路感染”与“泌尿系统感染”），请指令合并。
        2. 【建立层级 (HIERARCHY)】：如果两个节点是包含/分类关系（如“大肠杆菌”是父，“UTI89”是子），请指令新增一条 `[包含]` 关系线。⚠️【机制并存规则】：如果某实体（如抗生素）既连着父节点又连着子节点，请保留这些机制连线！
        3. 【彻底删除越级分类 (REMOVE)】：⚠️【多级嵌套规则】：如果存在三级以上的包含/从属关系（如 尿路感染包含膀胱炎，膀胱炎包含急性膀胱炎），请严格保证只建立相邻层级的联系。如果原图中存在**越级**的分类连线（如 急性膀胱炎与尿路感染之间的相关/属于关系），请务必指令将其【彻底删除】。
        4. 【标记机制捷径边 (DOWNGRADE)】：针对“机制推导”产生的表象捷径边（A->B且B->C，导致的A->C），将其标记为捷径边进行视觉降级。

        请严格只输出一个合法的 JSON 数组，格式如下（可返回多条指令）：
        [
          {"action": "MERGE", "target_node": "保留的标准实体", "nodes_to_remove": ["要删掉的冗余实体"], "reason": "说明"},
          {"action": "HIERARCHY", "parent": "父节点名称", "child": "子节点名称", "reason": "说明"},
          {"action": "REMOVE", "source": "起点名称", "target": "终点名称", "relation": "关系词", "reason": "越级层级冗余，需彻底删除"},
          {"action": "DOWNGRADE", "source": "起点名称", "target": "终点名称", "relation": "关系词", "reason": "机制捷径降级"}
        ]
        绝对不要输出任何其他解释文字！
        """

        # 将当前的图谱数据喂给大模型
        graph_data = f"【实体列表】:\n{json.dumps(entities, ensure_ascii=False)}\n\n【关系列表】:\n{json.dumps(relations, ensure_ascii=False)}"

        try:
            print("   └─ 🤖 [AI Cleaner] 正在进行图谱全局深度诊断...")
            raw_response = self._ask_llm(prompt, graph_data)
            clean_json = self._clean_json_string(raw_response)
            return json.loads(clean_json)
        except Exception as e:
            print(f"   ❌ [AI Cleaner] 诊断失败: {e}")
            return []

    def generate_pubmed_query(self, nodes_info, context_relations=None):
        """
        根据用户选择的节点及其本地别名生成 PubMed 检索式。
        如果传入了 context_relations，大模型将进行深度背景理解。
        """
        if context_relations:
            # 🌐 模式 3：背景搜索 (结合图谱现有关系)
            system_prompt = """你是一个顶级的计算生物学与文献检索专家。
            用户将提供他们希望检索的【核心实体】，以及这些实体在当前图谱中的【已有关系网络（背景上下文）】。
            你的任务是：深刻理解这些背景逻辑，为这些实体构建一个高度专业的 PubMed 布尔检索式（Boolean Query）。

            策略要求：
            1. 既然已知了部分关系，你的检索式应当倾向于探索“更深层的机制”、“未知的中间桥梁”或“具体的临床表型”。
            2. 可以根据上下文推断，自行加入一到两个关键的机制词（如 pathway, mechanism, phosphorylation, inhibitor 等）作为 AND 条件，以缩小范围，提高文献质量。
            3. 同一个实体的标准名称与别名之间用 OR 连接，实体组之间用 AND 连接。必须带上 [Title/Abstract] 或 [Mesh] 标签。
            4. ⚠️ 严禁输出任何解释性文本或 Markdown 格式。只能输出纯粹的检索式字符串！
            """
            user_content = f"【希望拓展的核心实体】：\n{json.dumps(nodes_info, ensure_ascii=False)}\n\n【已知图谱上下文】：\n{json.dumps(context_relations, ensure_ascii=False)}"
        else:
            # 🧠 模式 2：智能搜索 (仅扩充同义词)
            system_prompt = """你是一个顶级的生物医学文献检索专家。
            用户将提供几个他们希望在 PubMed 中检索的核心生物学实体（包含标准名称和已知别名）。
            你的任务是：为这些实体构建一个高度专业的 PubMed 布尔检索式（Boolean Query）。

            规则：
            1. 不同的实体之间必须用 AND 连接。同一个实体的标准名与别名之间用 OR 连接。
            2. 必须在词汇后加上合适的检索字段标签，例如 [Title/Abstract] 或 [Mesh]。
            3. 根据医学常识，自行补充常见且重要的英文同义词到 OR 逻辑中。
            4. ⚠️ 严禁输出任何解释性文本或 Markdown 格式。只能输出纯粹的检索式字符串！
            """
            user_content = f"请为以下选中的实体生成 PubMed 检索式：\n{json.dumps(nodes_info, ensure_ascii=False)}"

        print(f"🧠 [Agent] 正在生成 PubMed 检索策略 (背景模式: {bool(context_relations)})...")
        raw_response = self._ask_llm(system_prompt, user_content)
        query = self._clean_json_string(raw_response)

        print(f"🎯 [Agent] 生成的检索式: {query}")
        return query
