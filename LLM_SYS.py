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

    def diagnose_graph(self, entities, relations,output_lang="zh"):
        """🤖 核心引擎：AI 图谱智能洗树 (检测同义词、层级与捷径边)"""
        if not entities or not relations:
            return []
        lang_str = "中文" if "zh" in output_lang else "English"
        prompt = f"""你是一个顶级的生物医药知识图谱架构师。
        我将提供一份当前图谱的【实体列表】和【关系连线列表】（包含起点、终点、关系类型和原文证据）。
        请你根据原文证据进行“图谱洗树（Graph Pruning & Merging）”，并返回结构化的 JSON 操作指令。

        你需要执行以下四种操作：
        1. 【合并同义词 (MERGE)】：如果两个节点完全指代同一事物（如“尿路感染”与“泌尿系统感染”），请指令合并。
        2. 【建立层级 (HIERARCHY)】：如果两个节点是包含/分类关系（如“大肠杆菌”是父，“UTI89”是子），请指令新增一条 `[包含]` 关系线。⚠️【机制并存规则】：如果某实体（如抗生素）既连着父节点又连着子节点，请保留这些机制连线！
        3. 【彻底删除越级分类 (REMOVE)】：⚠️【多级嵌套规则】：如果存在三级以上的包含/从属关系（如 尿路感染包含膀胱炎，膀胱炎包含急性膀胱炎），请严格保证只建立相邻层级的联系。如果原图中存在**越级**的分类连线（如 急性膀胱炎与尿路感染之间的相关/属于关系），请务必指令将其【彻底删除】。
        4. 【标记机制捷径边 (DOWNGRADE)】：针对“机制推导”产生的表象捷径边（A->B且B->C，导致的A->C），将其标记为捷径边进行视觉降级。

        请严格只输出一个合法的 JSON 数组，格式如下（可返回多条指令）：
        [
          {{"action": "MERGE", "target_node": "保留的标准实体", "nodes_to_remove": ["要删掉的冗余实体"], "reason": "说明"}},
          {{"action": "HIERARCHY", "parent": "父节点名称", "child": "子节点名称", "reason": "说明"}},
          {{"action": "REMOVE", "source": "起点名称", "target": "终点名称", "relation": "关系词", "reason": "越级层级冗余，需彻底删除"}},
          {{"action": "DOWNGRADE", "source": "起点名称", "target": "终点名称", "relation": "关系词", "reason": "机制捷径降级"}}
        ]
        🚨 【强制输出语言与字段隔离指令】：
        1. 🚨 【键名与枚举冻结】：你必须严格保持 JSON 的所有键名（如 'action', 'reason'）为英文！同时，'action' 字段的值必须【严格保持】为模板中指定的英文大写枚举值（MERGE, HIERARCHY, REMOVE, DOWNGRADE），绝对不允许翻译或改成其他词！
        2. 🚨 【节点名称原样对齐】：JSON 中涉及的所有实体/节点名称（如 'target_node', 'nodes_to_remove', 'parent', 'child', 'source', 'target' 等字段的值），必须与我提供给你的输入列表中的名称【完全保持一模一样，原样返回】，绝对不允许翻译或改变字面！
        3. 🌐 【唯一允许翻译的字段】：【只有】'reason'（解释/说明）字段的内容，需要根据当前要求，严格使用【{lang_str}】来编写和表达。
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

    def explain_mechanism(self, node_a, node_b, paths_data,output_lang="zh"):
        """
        分支一专用：根据图谱中找到的多步路径，推导深层机制
        """
        lang_str = "中文" if "zh" in output_lang else "English"
        system_prompt = f"""你是一个顶级的分子生物学家和系统生物学专家。
        用户将提供从现有知识图谱中提取的，连接【起点实体】和【终点实体】的多条拓扑路径及对应的文献证据碎片。
        你的任务是：仔细阅读这些跨文献的证据碎片，将它们串联起来，进行全局视角的生物学逻辑推导，生成一份专业的【跨文献分子机制桥接报告】。

        报告结构要求：
        1. 🌟 【桥接通路总览】：用文本箭头（例如 A ─[激活]▶ C ─[抑制]▶ B）直观展现发现的 1~2 条最核心机制通路。
        2. 🔬 【机制深度剖析】：结合提供的 evidence（证据原句），详细解释起点如何通过中间节点一步步影响到终点。
        3. 🛡️ 【可信度与审计】：必须明确引用路径数据中的 doc_source（文献来源）。
        4. 💡 【新发现暗示】：如果有明显的跨文献拼图（例如文献1证明A调控C，文献2证明C调控B），请特别高亮指出这可能是一个具有研究价值的串联新机制。

        🚨 【强制输出语言指令】：你必须严格使用【{lang_str}】输出整篇报告（包含所有的标题、正文和列表）。如果要求的语言是 English，请你自动将报告模板中的中文标题全部翻译为英文。
        全程使用优美的 Markdown 格式输出。
        """
        user_content = f"起点实体：{node_a}\n终点实体：{node_b}\n\n【提取到的拓扑路径与证据碎片】：\n{json.dumps(paths_data, ensure_ascii=False)}"

        print(f"🧠 [Agent] 正在推导 {node_a} 与 {node_b} 的深层机制...")
        return self._ask_llm(system_prompt, user_content)

    def generate_bridge_query(self, node_a, node_b):
        """
        分支二/三专用：生成强调“机制/通路”的检索式，自带防幻觉强制报错。
        """
        system_prompt = """你是一个顶尖的生物学专家与 PubMed 检索策略师。
        用户在知识图谱中发现【实体A】和【实体B】之间缺乏深层机制通路，希望你构造检索式去网络上挖掘。

        【🛡️ 核心强制规则】：
        1. 逻辑审核：首先利用你的科学常识判断这两个实体是否可能存在生物学/医学上的关联。如果它们在科学上绝对毫无关联（例如一个是"苹果"，一个是"黑洞"），你必须仅输出纯文本：[NO_RELATION_ERROR]。
        2. 策略构造：如果可能存在关联，请构造一个高度专业的 PubMed 布尔检索式。
        3. 必须侧重机制：检索式不仅要包含实体 A 和 B（考虑它们的同义词），还必须强行加入机制探索词（如 mechanism, pathway, mediate, interact, cross-talk 等），以确保搜出来的是机制研究论文，而不是泛泛而谈的水文。
        4. ⚠️ 严禁输出任何解释性文本或 Markdown 代码块！只能输出纯粹的检索式字符串，或者 [NO_RELATION_ERROR]。
        """
        user_content = f"实体A：{node_a}\n实体B：{node_b}"

        print(f"🧠 [Agent] 正在思考 {node_a} 与 {node_b} 的机制探索策略...")
        raw_response = self._ask_llm(system_prompt, user_content)
        query = self._clean_json_string(raw_response)

        print(f"🎯 [Agent] 桥接检索策略: {query}")
        return query

    def extract_bridge_mechanism(self, node_a, node_b, abstracts_text, entity_lang="English"):
        """
        专门用于【智能桥接】模块：阅读多篇文献摘要，狙击式提取只与 A 和 B 联系相关的实体与关系。
        增加 entity_lang 参数以统一图谱命名规范。
        """
        system_prompt = f"""你是一个顶尖的分子生物学机制挖掘专家。
        用户将提供【实体A】和【实体B】，以及从 PubMed 检索到的【多篇相关文献摘要】。
        你的任务是：专门寻找并提取连接 A 和 B 的深层调控机制或中间通路。
        ⚠️ 核心警告：请彻底忽略与连接这两个实体无关的其他背景知识、旁支靶点！

        【🌐 命名语言强制规范】：
        所有提取出的 entities (主要是标准名 standard_name ) 以及 ，必须强制使用 {entity_lang} 进行输出！
        (注：explanation, evidence, reason 以及 relation 关系动词可以使用中文，以方便阅读)

        请严格按照以下 JSON 格式返回数据：
        {{
            "explanation": "在这里写一段连贯的文本报告（支持Markdown）：综合这些文献，解释 A 是如何通过哪些中间介导物影响 B 的。如果没有找到任何确切证据，请在此说明。",
            "entities": [
                {{"standard_name": "实体名", "aliases": ["别名1", "别名2"]}}
            ],
            "relations": [
                {{
                    "source": "主语",
                    "target": "宾语",
                    "relation": "关系动词(如 激活, 抑制, 磷酸化)",
                    "evidence": "从文献中摘抄的证明原句",
                    "reason": "你对这条调控逻辑的简短解释",
                    "doc_source": "对应的 PMID 或文献标题"
                }}
            ]
        }}
        注意：entities 中必须包含你找出的所有关键中间节点，以及 A 和 B 本身。如果没有找到桥接关系，entities 和 relations 请返回空列表 []。
        """
        user_content = f"【实体A】：{node_a}\n【实体B】：{node_b}\n\n【供分析的文献摘要合集】：\n{abstracts_text}"

        print(f"🧠 [Agent] 正在使用 {entity_lang} 命名规范，挖掘 {node_a} 与 {node_b} 的桥接机制...")
        raw_response = self._ask_llm(system_prompt, user_content)

        try:
            cleaned_json = self._clean_json_string(raw_response)
            result = json.loads(cleaned_json)
            return result
        except Exception as e:
            print(f"❌ [Agent] 桥接机制 JSON 解析失败: {e}")
            return {"explanation": "解析大模型返回结果失败，请重试。", "entities": [], "relations": []}

    def generate_topic_query(self, user_topic):
        """
        冷启动模块：将用户的自然语言研究意图，转化为专业的 PubMed 检索式。
        【结构化拆解版】：防止过度泛化导致器官丢失，强制保留靶向组织。
        """
        system_prompt = """你是一个顶级的生物医学信息检索专家（Medical Librarian）。
        请根据用户的【自然语言研究意图】，构造一个专业、精准且高召回率的 PubMed 布尔检索式。

        【🚨 核心检索策略 (绝对遵守)】：
        1. 剔除泛机制类“元词汇”（致命错误）：【绝对禁止】在检索式中加入 pathway, mechanism, protein, bridge protein, adaptor, crosstalk, interaction, target 等泛指词汇！在 PubMed 中搜索具体表型和实体即可。
        2. 必须保留“器官/组织/细胞”锚点：如果用户明确了研究对象（如“肠道”），必须把它作为一个独立的 AND 逻辑块，加上同义词（如 intestinal OR gut OR colon）。
        3. 自然切分逻辑块（解除数量限制）：如果用户描述了 A -> B -> C 的多步机制，请将它们分为独立的 AND 逻辑块。⚠️ 严禁把完全不同的生物学概念（如“细胞衰老”和“免疫逃逸”）强行塞进同一个 OR 括号里！
        4. 极致同义词拓展 (预防0结果)：你必须为每一个概念提供 4-6 个极其宽泛的同义词或相关词（用 OR 连接）。
        5. 禁用 MeSH 标签：绝对禁止添加 [Mesh]、[majr] 等标签，直接使用自由词或 [tiab]。
        6. 🌟 鼓励分段组合检索 (大招)：对于 A -> B -> C 的长链宏大假说，单靠全链条串联极容易搜不到文献。我们极其鼓励你拆开搜索！你可以建立 A+B+C 的全貌网络，也同时建立 A+B, B+C, A+C 的局部网络，并将这些网络用大的 OR 连接起来（例如：(A AND B AND C) OR (A AND B) OR (B AND C)）。在每一个小的 AND 区间内，请放开手脚大胆发挥你的专业度！

        【实战示范】：
        用户意图：“长期熬夜导致肠道上皮细胞衰老，通过哪些桥梁蛋白引起肿瘤免疫逃逸？”
        ❌ 错误（不同概念强行合并进 OR）：(circadian rhythm) AND (intestinal) AND (senescence OR tumor immune escape)
        ❌ 错误（包含泛机制词）：(circadian rhythm) AND (intestinal) AND (senescence) AND (pathway OR bridge protein)
        ✅ 正确的自由分段组合式：
        ((circadian rhythm OR sleep deprivation) AND (intestinal OR gut) AND (senescence OR SASP) AND (immune evasion OR tumor immune escape)) OR ((circadian rhythm OR sleep deprivation) AND (intestinal OR gut) AND (senescence OR SASP)) OR ((intestinal OR gut) AND (senescence OR SASP) AND (immune evasion OR tumor immune escape))

        【最后警告】：如果用户的输入完全无科学意义，请直接输出纯文本：[INVALID_TOPIC]。
        ⚠️ 严禁输出任何解释性文字，严禁使用 Markdown 代码块，只能输出纯粹的检索式字符串！
        """

        user_content = f"【用户研究意图】：{user_topic}"

        print(f"🧠 [Agent] 正在将意图转化为检索式...")
        raw_response = self._ask_llm(system_prompt, user_content)
        return self._clean_json_string(raw_response)

    def evaluate_abstracts_relevance(self, user_topic, abstracts_text,output_lang="zh"):
        """
        冷启动反思模块：检查抓取回来的文献摘要是否符合意图。
        【核心技巧】：在 JSON 中强制要求先输出 reason，再输出 is_relevant，通过思维链 (CoT) 大幅提升判断准确率。
        """
        lang_str = "中文" if "zh" in output_lang else "English"
        system_prompt = f"""你是一个宽容的知识图谱构建助手。
        你需要评估检索到的文献摘要，是否有助于为用户的研究意图构建【初始图谱】。

        【🟢 核心放行标准 (局部命中 = 完美)】：
        用户经常提出 A -> B -> C 这样跨界宏大的假说。真实的文献绝大多数只会研究其中的一小段（比如只研究 A->B，或者只研究 B->C）。
        因此，只要这批文献中有【任何一篇】探讨了假说中的【局部环节】（例如：只探讨了“熬夜与肠道”，或者只探讨了“肠道衰老”），这就叫极其有价值的拼图！
        【绝对禁止】因为“文献没有涵盖用户提到的所有环节”而驳回！

        【🛑 驳回标准】：
        只有当这些文献与用户的各个切片【完全无关】（例如全都是讲植物、或者全都是毫无细胞机制的流行病学调查）时，才驳回。

        请严格返回如下 JSON 格式：
        {{
            "reason": "请说明该文献命中了用户宏大假说中的哪一个局部切片（说明为什么放行）。严禁抱怨文献没有覆盖全链条！",
            "is_relevant": true 或 false
        }}
        🚨 【强制输出语言与字段隔离指令】：
        1. 🚨 【键名与布尔值冻结】：你必须严格保持 JSON 的所有键名（'reason', 'is_relevant'）为英文！同时，'is_relevant' 字段的值必须【严格保持】为标准的 JSON 布尔值（true 或 false），绝对不允许加引号，也不允许翻译成其他文字！
        2. 🌐 【唯一允许翻译的字段】：【只有】'reason'（解释/说明）字段的内容，需要结合文献内容，严格使用【{lang_str}】来编写和表达。
        
        """
        user_content = f"【用户研究意图】：{user_topic}\n\n【检索到的文献摘要】：\n{abstracts_text}"

        print(f"🧠 [Agent] 正在使用思维链 (CoT) 反思文献相关性...")
        raw_response = self._ask_llm(system_prompt, user_content)
        try:
            cleaned_json = self._clean_json_string(raw_response)
            return json.loads(cleaned_json)
        except Exception as e:
            print(f"❌ [Agent] 相关性评估 JSON 解析失败: {e}")
            default_reason = "解析大模型输出失败，默认放行。" if "中文" in lang_str else "Failed to parse LLM output, passing by default."
            return {"reason": default_reason, "is_relevant": True}

    def prune_nodes_by_intent(self, user_intent, entities, relations,output_lang="zh"):
        """
        基于意图的智能剪枝：让大模型根据用户的研究兴趣，揪出无关的“杂草”节点。
        """
        lang_str = "中文" if "zh" in output_lang else "English"
        # 构建带有拓扑上下文的轻量级节点字典，节省 Token 并提供判断依据
        node_context = []
        for ent in entities:
            node_name = ent.get("standard_name")
            neighbors = set()
            for r in relations:
                if r.get("source") == node_name:
                    neighbors.add(r.get("target"))
                elif r.get("target") == node_name:
                    neighbors.add(r.get("source"))
            # 如果没有邻居，就标注为孤立节点
            neighbor_str = ", ".join(list(neighbors)) if neighbors else "无(孤立节点)"
            node_context.append(f"节点: {node_name} | 其连接的邻居: {neighbor_str}")

        context_str = "\n".join(node_context)

        system_prompt = f"""你是一个严谨且果断的生物医学知识图谱清理专家。
        当前图谱在构建过程中不可避免地引入了一些偏离主题的节点（噪音）。你需要根据用户提供的【核心研究方向】，对下列所有节点逐一进行严格审视。

        【风险等级标准】：
        1. "完全无关": 与用户研究方向毫无关联，或者是明显被误判进来的同名异义词、其他无关器官/疾病的节点，坚决建议删除。
        2. "可能无关": 偏离研究核心，或者联系极其薄弱的旁支对象，建议删除。
        3. "关联度低": 依然在相关领域内，但对核心问题扩展性不足或过于泛泛而谈，交由用户定夺。
        4. "核心相关": 与研究方向紧密相关，非常重要（注意：核心相关的节点直接跳过，绝对不要输出到最终结果中！）。

        请返回 JSON 数组格式（仅包含前三种风险级别的节点），格式如下：
        [
            {{
                "node_name": "被判定的节点名称",
                "risk_level": "完全无关/可能无关/关联度低",
                "reason": "请结合其邻居信息，简短说明为什么该节点偏离了用户的研究意图"
            }}
        ]
        
        🚨 【强制输出语言与字段隔离指令】：
        1. 🚨 【键名与枚举冻结】：你必须严格保持 JSON 的所有键名（如 'node_name', 'risk_level', 'reason'）为英文！同时，'risk_level' 字段的值必须【严格保持】为指定英文枚举值（Completely_Irrelevant, Potentially_Irrelevant, Low_Relevance），绝对不允许翻译成中文或其他格式！
        2. 🚨 【节点名称原样对齐】：'node_name' 字段的值必须与输入的图谱节点名称【完全保持一模一样】，无论是大小写、空格还是语言，绝对不允许进行任何翻译或擅自改动！
        3. 🌐 【唯一允许翻译的字段】：【只有】'reason'（原因说明）字段的内容，需要结合邻居和用户意图，严格使用【{lang_str}】来编写输出。

        ⚠️ 严禁输出任何多余的解释，严禁使用 Markdown 代码块，只能输出纯粹的 JSON 数组！如果所有节点都极其完美相关，请返回空数组 []。
        """

        user_content = f"【用户核心研究方向】：{user_intent}\n\n【图谱节点上下文列表】：\n{context_str}"

        print(f"🧠 [Agent] 正在基于意图对图谱节点进行清洗评估...")
        raw_response = self._ask_llm(system_prompt, user_content)
        try:
            cleaned_json = self._clean_json_string(raw_response)
            return json.loads(cleaned_json)
        except Exception as e:
            print(f"❌ [Agent] 节点清洗 JSON 解析失败: {e}")
            return []

    def explain_graph_element(self, element_type, element_name, local_context,output_lang="zh"):
        """
        Ask AI 核心模块：为选中的图谱节点或关系提供专业且锚定上下文的解读。
        【终极完全体 + 动态分流】：区分节点和关系的模板逻辑。
        """
        lang_str = "中文" if "zh" in output_lang else "English"
        # ✨ 根据传入的类型，动态组装不同的排版紧身衣
        if element_type == "节点":
            template_block = """
        <OUTPUT_TEMPLATE>
        ### 📖 基础生物学定义
        **概念解析**：(用通俗专业的语言简述该元素是什么)
        **主要功能**：(说明它在细胞/分子层面的常规生理或病理作用)

        ### 🕸️ 在本图谱中的研究定位
        **网络枢纽机制分析**：
        - **上游调控机制**：(结合数据，深入解释上游节点是如何诱导/调控它的，若无写暂无)
        - **下游靶点效应**：(结合数据，深入解释它是如何影响下游靶点的，若无写暂无)

        **提取机制与文献来源**：
        > (根据 <CONTEXT_DATA> 中的依据进行学术总结。若依据为空，则进行优雅的学术补充推断，并明确列出相关文献名。)
        </OUTPUT_TEMPLATE>
            """
        else:  # 元素类型是“关系连线”
            template_block = """
        <OUTPUT_TEMPLATE>
        ### 📖 生物学关联机制解析
        **起点解析**：(简述该连线起点实体的核心生物学功能)
        **终点解析**：(简述该连线终点实体的核心生物学功能)

        ### 🕸️ 连线深度推演
        **核心作用机制 (Mechanism of Action)**：
        - (⚠️ 绝对不要分析上游下游！请直接结合你的生物学知识与 <CONTEXT_DATA>，深入剖析起点实体是如何通过具体的生化通路、受体或分子级联反应，去调控/影响终点实体的。这是一对一的机制级解析。一定要参考文献证据并做出合理扩充)

        **提取机制与文献来源**：
        > (根据 <CONTEXT_DATA> 中的依据进行学术总结。若依据为空，则进行优雅的学术补充推断，并明确列出相关文献名。)
        </OUTPUT_TEMPLATE>
            """

        system_prompt = f"""你是一个顶级的生物医学知识图谱解说专家。
        请基于用户选中的图谱元素和 <CONTEXT_DATA> 提供深入的生物学解读。

        【🚨 核心行为准则 (绝对遵守)】：
        1. 格式隔离：你必须且只能输出下方 <OUTPUT_TEMPLATE> 标签内的内容！【绝对禁止】输出“核心警告”、“注意”等我的系统指令！
        2. 🎨 强制排版规范：为了页面美观，【绝对禁止】使用一级标题(#)和二级标题(##)！只能使用三级标题(###)和加粗(**)。必须完全遵照模板的格式。
        3. 拒绝“复读机”：在解释机制时，必须结合你的生物学知识，深度推演 <CONTEXT_DATA> 中的通路机制和级联反应。
        4. 优雅处理无依据：如果 <CONTEXT_DATA> 提示提取依据是“无”，请委婉说明：“图谱暂未记录具体细节，但基于经典生物学通路推测...”。如果有明确的文献来源，请在依据中大方引用！

        {template_block}

        🚨 【强制输出语言指令】：你必须严格使用【{lang_str}】输出整篇解读报告。在生成最终内容时，如果要求的语言是 English，请你动态将 <OUTPUT_TEMPLATE> 模板里的所有中文标题（如“概念解析”等）翻译为地道的英文标题。
        ⚠️ 请立刻输出填充后的模板内容，不要包含 <OUTPUT_TEMPLATE> 标签本身，绝对不要使用 # 或 ## 标题！
        """

        user_content = f"【选中的元素】：[{element_type}] {element_name}\n\n<CONTEXT_DATA>\n{local_context}\n</CONTEXT_DATA>"

        print(f"🧠 [Agent] 正在生成专属解读 (已启用 [{element_type}] 专属动态推演模板)...")
        raw_response = self._ask_llm(system_prompt, user_content)
        return raw_response


