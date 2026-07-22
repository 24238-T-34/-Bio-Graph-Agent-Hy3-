import streamlit as st
import tempfile
import os
from pypdf import PdfReader
from back_logic import BioGraphPipeline,GraphVisualizer
import streamlit.components.v1 as components
import gc
import fitz  # 🚀 优化：把 PyMuPDF 移到文件顶部，规范代码结构
import json
import pandas as pd
import uuid
import re

CONFIG_FILE = ".bio_graph_config.json"


@st.dialog("📖 User Guide / 操作指南", width="large")
def show_help_dialog():
    # 🌐 动态获取当前系统的 UI 语言
    current_ui_lang = st.session_state.get("language", "zh")
    is_en = "en" in current_ui_lang.lower()

    if is_en:
        st.markdown(""" 
    📖 **Bio-Graph Agent Core Functionality Guide**
    Welcome to Bio-Graph Agent! A specialized LLM-powered scientific counselor crafted specifically for biomedical researchers.

    🧬 **Graph Base Logic:**
    This system is far more than a simple "summarization tool". It leverages Large Language Models to deeply read literature and extract structured **"Entities (Nodes)"** and **"Regulatory Relationships (Edges)"**. When analyzing multiple papers, the system automatically performs semantic alignment (e.g., merging "p53" from Paper A and "TP53" from Paper B into a single node), weaving isolated papers into a globally verifiable, dynamic knowledge network!

    ⚙️ **I. Initial Environment Setup (Sidebar "More Settings")**
    Before use, please expand the ⚙️ **More Settings** panel in the left sidebar for basic configuration:

    🌐 **LLM Engine:** Select your API provider and input the key. It supports cloud-based models as well as offline privacy mode (simply select Ollama to handle highly classified data with the network disconnected, running key-free).

    📚 **Smart Retrieval Source:** Choose PubMed (absolute medical authority) or Semantic Scholar (all-discipline AI-driven high-speed retrieval with built-in anti-blocking fallback mechanisms).

    🎛️ **Interface Feature Toggles:** Enable the 📝 **Manual Editing Panel** (for pruning) and 🤖 **AI Intelligent Graph Analysis** (for tree cleaning) as needed.

    📂 **II. From Scratch: Building the Knowledge Graph (Left Control Panel)**
    In the left "1. Literature Input & Configuration" panel, the system offers two distinct paths to get started:

    **Option A: 💡 Zero-Based Cold Start**
    Have no papers on hand? Not a problem at all!
    Without uploading any files, simply tell the AI your research direction in the text box (e.g., *"Role of macrophage polarization in tumor microenvironment"*).
    Click **"One-click Retrieve & Generate Initial Graph"**, and the AI will automatically generate a professional query, dive into the database to scrape the latest papers, verify relevance using a "sliding window," and instantly erect your first initial knowledge graph!

    **Option B: 📄 Precise Local Literature Analysis**
    If you already have PDF files:

    * **Upload Literature:** Drag a single PDF into the upload zone (Note: Only one file can be parsed at a time, but you can use "Append Mode" to accumulate infinitely).
    * **🎯 Define Parsing Range:** Pinpoint exactly via starting and ending pages (e.g., parsing only pages 3-5 which contain the core mechanism diagram), saving time and computational costs.
    * **⚙️ Advanced Extraction Settings:**
        * ⚡ **Abstract-Only Mode:** High-speed mode that intelligently targets abstract contents to analyze only core relationships within abstracts.
        * 🔍 **Self-Reflection & Error Correction:** Lets the AI act as an independent quality inspector, double-checking and discarding "hallucinated" nodes lacking textual evidence to boost accuracy.
        * 🔗 **Append Mode (The Core Soul):** When enabled, newly parsed literature will not overwrite the existing graph, but will blend and grow into it! Turning this off will clear the current graph and start from scratch.
        * 🌐 **Entity Naming Convention:** Forces all graph nodes to be unified into pure Chinese or pure English, rejecting mixed bilingual naming.

    Click **"🚀 Start Parsing & Generate Graph"**.

    🕸️ **III. Visual Empowerment Engine (Top Console of Main Interface)**
    Once the graph is generated, utilize the four hardcore visual algorithms in the top console to instantly spot scientific targets from a tangled mess:

    * 👁️ **Mechanism Shortcuts:** When enabled, reveals "express paths" bypassing intermediate nodes, offering a macro view of the ultimate impact from upstream to downstream.
    * 🧬 **Ontology Empowerment (Containment Feedback):** Feedback the weight of micro-entities (e.g., a specific protein) to their macro parent categories, making crucial "kinase families" or "signaling pathways" automatically grow larger in the graph.
    * 🔥 **Node Empowerment (Degree Centrality):** Based on graph theory degree algorithms, "core hub genes" with more molecular interactions will become visually prominent through larger node sizes.
    * 🔗 **Edge Empowerment (Mainstream Pathway Bolden):** Regulatory edges repeatedly mentioned across multiple papers with the solidest evidence chains will be automatically bolded, letting you pierce through to mainstream consensus at a glance.

    The model automatically generates graphs with relationships, where node size represents popularity, and complex biological pathways are intelligently summarized. Each color, line style, and thickness holds distinct biological significance:

    * 🟢 **Green Solid Line + Arrow:** Represents Positive Regulation / Promotion / Activation. E.g., a cytokine stimulating the phosphorylation of a signaling pathway.
    * 🔴 **Red Solid Line + Arrow:** Represents Negative Regulation / Inhibition / Down-regulation. E.g., a specific miRNA degrading target gene mRNA, or a drug inhibiting receptor activity.
    * 🟣 **Purple Solid Line + Arrow:** Represents Containment / Belonging / Component relationship. E.g., a protein being a core subunit of a complex, or a receptor belonging to a superfamily.
    * ⚪ **Grey Solid Line / No Arrow:** Represents General Association / Correlation / Interaction. Typically indicates co-mentioning in literature, showing interactions or synergy without a clarified positive/negative regulatory direction.
    * ⚠️ **Grey Dashed Line (with [AI Flagged as Mechanism Shortcut] label):** This is a feature algorithm of our agent. When the AI detects a "cross-level skip" between two pathways (e.g., literature says A activates C, while the graph contains a refined A -> B -> C cascade), the system automatically flags the coarse A -> C edge as a mechanism shortcut, changing it to a grey dashed line to prevent coarse relations from interfering with your precise analysis of specific molecular cascades.
    * 📐 **Line Thickness (Width):** The thicker the line, the higher the frequency of direct association mentioned or extracted from literature, serving as the "backbone" of the graph.

    💾 **IV. Vault & Project Management (Bottom of Left Column)**
    Scientific research requires long-term accumulation. Bio-Graph Agent comes equipped with a professional data persistence and project management module to ensure every single analysis is safely archived and seamlessly restored.

    At the very bottom of the left sidebar, you can perform the following macro operations:

    1.  ✨ **Create Blank Project**
        * *Purpose:* Reset your current workbench with a single click when starting a brand-new research topic.
        * *Safety Lock Mechanism:* Since this operation thoroughly clears graphs in memory and local caches, the system features a two-step misclick prevention panel. After clicking, you must click "🔴 Confirm Clear" again to actually destroy the data. It is highly recommended to export and archive your current achievements before doing this.
    2.  📤 **Export Project (.biokg)**
        * *Purpose:* Pack and download your painstakingly constructed graph (containing all nodes, edges, extraction evidence, and manual edits) to your local machine.
        * *Format Description:* The exported file is in the system's proprietary `.biokg` format (underneath it's standard JSON). It is not only your personal research asset backup but can also be sent directly to peers or mentors, allowing them to load and review your graph on their own machines.
    3.  📥 **Load Historical Project (.biokg / .json)**
        * *Purpose:* Unlock the "Load Save" functionality of your research. Drag and drop a previously exported `.biokg` project file here to instantly restore your historical workspace.
        * *Seamless Rendering Mechanism:* To prevent accidental overwriting of current progress, after dragging in the file, you must click "🚀 Confirm Loading Project" to execute the replacement. Upon successful loading, the system recomputes the topology in the background and instantly redraws the dynamic graph. Concurrently, the upload panel automatically hides and clears itself, returning a highly clean interface to you.

    🎯 **Summary & Recommendations:**
    *"Do research daily, export before logging off."* By utilizing Append Mode (to accumulate new literature) and the Vault (to save current progress), you can treat Bio-Graph Agent as a long-running external super-brain, gradually weaving dozens or hundreds of papers over months into a priceless network of diseases and molecular targets!

    ✂️ **V. Expert Manual Intervention (Right Side "Graph Data Management Center")**
    No matter how powerful an AI is, the professional judgment of human experts always holds the highest priority in rigorous scientific mapping. Toggle on 📝 **Enable Manual Editing Panel** in settings, and you will gain "God-mode permissions" over the graph on the right side.

    The management center is divided into three major modules:

    1.  ⚡ **Quick Features (Global Overview Management)**
        * 🧹 *Clear Isolated Nodes:* Click to scan globally. Any node that neither points to others nor is pointed to by others will be wiped out instantly as an "isolated and helpless" junk node.
        * 📝 *Batch Modify Literature/Source Names:* Found a messy name for a PDF in your graph? Select the old name here and type a new one (e.g., *Nature_2023_p53*), and the system will automatically substitute the source for all related nodes and edges, ensuring crisp traceability.
        * ➕ *Manually Add Node:* If the AI missed a highly critical gene or protein, you can manually type its name, aliases, and source here to force it onto the canvas.
    2.  🎯 **Node Operations (Surgical Strikes)**
        Search and select a node of interest from the dropdown menu; the system offers four surgery-grade operations:
        * ✏️ *Modify Info:* Rename the standard name of a node, or add/remove its aliases.
        * 🧲 *Force Merge (Highly Useful):* If you find both "p53" and "TP53" on the graph which should be the same thing, select "p53" and choose to merge it into "TP53". The system will instantly transfer all edges belonging to "p53" over to "TP53", combine their aliases, and safely destroy the separate "p53" node.
        * 🔀 *Node Split:* Break down a generic node (such as *Mutant & Wild-type p53*) into two independent new nodes. Crucially, the system lists every single edge connected to the original node, letting you assign each edge to new node A, new node B, copy it to both, or discard it entirely.
        * 🗑️ *Dangerous Delete:* Completely destroy the node and uproot all regulatory edges connected to it.
    3.  🔗 **Relationship Operations (Edge Pruning & Bridging)**
        Select Source Node A and Target Node B from the dropdown menus respectively, and the system will fetch all bonds between them:
        * ✏ *Manage Existing Edges:* Reverse direction if AI flipped the upstream/downstream; toggle the relationship type among standard vocabularies (positive, negative, correlation) and edit its textual evidence or source.
        * 🚨 *Sever Edge:* For meaningless background intros or false positives extracted from literature, click delete to completely wipe that edge from the graph.
        * ➕ *Add New Edge:* If the literature didn't mention it but you confirm A promotes B based on your background knowledge? Choose who points to whom, set the relation type, and manually build this hidden bridge.

    🤖 **VI. AI Intelligent Graph Tools (Right Dedicated Panel)**
    If the "Manual Editing Panel" is your scalpel, then the "AI Intelligent Graph Tools" act as your **"Super Think Tank"**. Select the corresponding AI module on the right panel to let the large model intervene deeply in graph cleaning, growth, and interpretation.

    1.  🧹 **Intelligent Tree Cleaning (Pruning)**
        When you import a massive volume of literature, the graph often becomes bloated and redundant. The tree cleaning module provides two powerful automated cleaning capabilities:
        * 🔍 *Intelligent Topological Diagnosis:* Click "Start AI Intelligent Graph Diagnosis", and the large model will scan through the edge logic of the entire graph to generate an "Audit Checklist" suggesting to **Merge** synonymous nodes, **Establish Hierarchy** for family traits, or **Downgrade** broad shortcuts to dashed lines. Check the suggestions you approve of and click one-key execution to instantly complete reorganization!
        * ✂ *Intent-Based Node Cleaning (Intent-Based Pruning):* Type your "core research direction" in plain vernacular into the text box. AI will act like a reviewer, checking nodes and neighbors one by one to compile a "Deviation Node Execution List" for you. Once confirmed, click "Execute", and these irrelevant nodes along with their implicated edges will be thoroughly eliminated from the canvas.
    2.  🔍 **Intelligent Expansion (Smart Expansion)**
        Break through boundaries of existing literature to let the graph "self-grow"! When you find an important branch in the graph that needs deep digging:
        * 🎯 *Select Anchor Nodes & Retrieval Strategy:* Pick 1-3 core nodes in the graph and mount the search engine via Direct, Smart, or Background Search (the strongest, which reverse-engineers advanced queries based on known network relationships).
        * 📑 *Filter and Enqueue:* The system pulls the latest literature from the web to generate a table; check the papers you find valuable to send them into the parsing queue.
        * ⚙ *Automated Fusion Queue (Autopilot Mode):* Turn on the continuous auto-parsing switch and go grab a cup of coffee. The system will automatically line up, grab, and read each paper, perfectly aligning and welding newly extracted nodes with existing ones.
    3.  🔗 **Intelligent Bridging (Bridging)**
        The ultimate weapon to discover hidden scientific targets. When you are curious about the relationship between two molecules A and B in the graph:
        * If indirect paths already exist, AI will instantly traverse the network, mapping out the multi-step conduction pathway of "how A ultimately impacts B through X and Y".
        * If they are isolated islands with no direct contact, the system will automatically spawn a retrieval task, calling the external large model to forcefully mine whether a link between A and B has been verified in the latest cutting-edge papers, instantly sparking innovative inspiration for grant proposals!
    4.  🤖 **Ask AI**
        The graph's "pocket micro-narrator". When facing a labyrinthine graph and unsure what biochemical reaction a specific edge stands for, simply select that node or edge directly in the graph, and the system will feed its micro-context (including original extraction evidence and source attribution) to the large model to generate a detailed local mechanism interpretation report.
    """)
    else:
        st.markdown(""" 
    📖 **Bio-Graph Agent 核心功能操作指南**
    欢迎使用 Bio-Graph Agent！这是一款专为生物医学研究者打造的“大模型科研军师”。

    🧬 **基础图谱逻辑 (Graph Base Logic)：**
    本系统并非简单的“总结工具”，它会通过大语言模型深度阅读文献，抽取出结构化的“实体（节点）”与“调控关系（连线）”。当你分析多篇文献时，系统会自动进行实体语义对齐（例如将文献A中的 p53 和文献B中的 TP53 完美融合为同一个节点），从而将孤立的论文编织成一张具备交叉印证能力的全局动态知识网络！

    ⚙️ **一、 初始环境搭建 (侧边栏「更多设置」)**
    在使用前，请先展开左侧边栏的 ⚙️ **更多设置** 进行基础环境配置：

    🌐 **大模型引擎：** 选择 API 提供商并输入密钥。支持云端大模型，也支持离线隐私模式（选择 Ollama 即可在拔掉网线的情况下处理极密数据，免密钥运行）。

    📚 **智能检索源：** 选择 PubMed (医学绝对权威) 或 Semantic Scholar (全科 AI 智能极速检索，自带降级防封机制)。

    🎛️ **界面功能开关：** 根据需要开启 📝 **手动编辑面板** (用于剪枝) 与 🤖 **AI 智能图谱分析** (用于洗树)。

    📂 **二、 从零到一：构建知识图谱 (左侧控制栏)**
    在左侧 1. 文献输入与配置 面板，系统提供两种截然不同的起步方式：

    **方式 A：💡 零基础冷启动 (Cold Start)**
    手头没有任何文献？完全没问题！
    只要不在上方上传文件，你只需在输入框告诉 AI 你的研究方向（例如：“巨噬细胞极化在肿瘤微环境中的作用”）。
    点击 “一键检索并生成初始图谱”，AI 将自动为你生成专业检索式，潜入数据库抓取最新文献，利用“滑动窗口”进行匹配度验证，并直接为你搭建出第一张初始知识图谱！

    **方式 B：📄 本地文献精准解析**
    如果你已经有了 PDF 文件：

    * **上传文献：** 将单篇 PDF 拖入上传区（注意：每次仅支持解析一篇文献，但可以通过“追加模式”无限累加）。
    * **🎯 划定解析范围：** 通过控制起始页与终点页精准定位（例如仅解析含有核心机制图的第 3-5 页），极大节省时间和计算成本。
    * **⚙️ 高级提取模式设置：**
        * ⚡ **仅提取摘要模式：** 极速模式，智能匹配摘要内容，仅分析摘要中核心关系。
        * 🔍 **自我反思纠错：** 让 AI 充当独立质检员，二次核对剔除没有原文证据的“幻觉”节点，提高准确率。
        * 🔗 **追加模式 (核心灵魂)：** 开启后，新解析的文献不会覆盖现有图谱，而是与之融合生长！关闭此项将清空现有图谱从零开始。
        * 🌐 **实体命名规范：** 强制将所有图谱节点统一为纯中文或纯英文，拒绝中英混杂。

    点击 “🚀 开始解析 & 生成图谱”。

    🕸️ **三、 视觉赋权引擎 (主界面上方控制台)**
    图谱生成后，利用上方控制台的四大硬核视觉算法，可瞬间在一团乱麻中找出科研靶点：

    * 👁️ **机制捷径边：** 开启后，展现跨越中间节点的“直达捷径”，宏观审视上游到下游的最终影响。
    * 🧬 **包含关系反哺 (Ontology Empower)：** 微观实体（如某特定蛋白）的权重反哺给其宏观父类，让重要的“激酶家族”或“信号通路”在图中自动变大。
    * 🔥 **节点辐射度 (Node Empower)：** 基于图论连接度算法，与其他分子交互越多的“核心枢纽基因”，其节点体积会越显眼。
    * 🔗 **主干通路加粗 (Edge Empower)：** 被多篇文献反复提及、证据链最坚固的调控连线会自动加粗，一眼看穿主流共识。

    模型会自动生成带关系的图谱，节点大小代表热度，而复杂的生物学通路进行了智能化归纳，每种颜色、线型和粗细都代表着特定的生物学意义：

    * 🟢 **绿色实线 + 箭头：** 代表 正作用 / 促进 / 激活 (Activation/Up-regulation)。例如：细胞因子刺激了某一信号通路的磷酸化。
    * 🔴 **红色实线 + 箭头：** 代表 负作用 / 抑制 / 下调 (Inhibition/Down-regulation)。例如：某种 miRNA 降解了靶基因的 mRNA，或某药物抑制了受体活性。
    * 🟣 **紫色实线 + 箭头：** 代表 包含 / 归属 / 组成关系 (Containment/Component)。例如：某个蛋白质属于某一复合物的核心亚基，或者某个受体属于某个超家族。
    * ⚪ **灰色实线 / 无箭头：** 代表 一般关联 / 相关性 (Correlation/Interaction)。通常表示两者在文献中被共同提及，存在相互作用或协同现象，但尚未明确正负调控方向。
    * ⚠️ **灰色虚线 (带有 [AI 判定为机制捷径] 标签)：** 这是本智能体的特色算法。当 AI 检测到两条通路之间存在“跨级跳跃”时（例如文献中提到 A 激活了 C，但同时图中又存在 A -> B -> C 的细腻通路），系统会自动将粗放的 A -> C 标记为机制捷径（Shortcut），并将其变为灰色虚线，避免粗放关系干扰您对具体分子级联反应（Cascade）的精确分析。
    * 📐 **连线粗细 (Width)：** 线越粗，代表两节点间的直接关联在文献中被提及或抽取的频次越高，属于图谱中的“主干骨架”。

    💾 **四、 记忆库与工程管理 (左栏底部)**
    科研工作往往需要长期积累，Bio-Graph Agent 为此配备了专业的数据持久化与工程管理模块，确保你的每一次分析都能被安全存档与无缝恢复。

    在页面左侧边栏的最下方，你可以进行以下大盘操作：

    1.  ✨ **新建空白工程**
        * *作用：* 当你准备开启一个全新的研究课题时，一键重置当前工作台。
        * *安全锁机制：* 由于此操作会彻底清空内存中的图谱与本地缓存，系统设计了二次防误触确认面板。点击后，你需要再次点击“🔴 确定清空”才会真正销毁数据。建议在执行此操作前，先将当前成果导出存档。
    2.  📤 **导出工程 (.biokg)**
        * *作用：* 将当前辛勤搭建出的整张图谱（包含所有节点、连线、提取证据以及你的手动修改记录）打包下载到本地。
        * *格式说明：* 导出的文件为系统专属的 `.biokg` 格式（底层为标准 JSON）。它不仅是你个人的科研资产备份，还可以直接发送给你的同行或导师，让他们在自己的电脑上载入并继续审阅你的图谱。
    3.  📥 **载入历史工程 (.biokg / .json)**
        * *作用：* 打通科研的“读档”功能。将之前导出的 `.biokg` 工程文件拖拽至此，即可瞬间恢复历史工作状态。
        * *无缝渲染机制：* 为防止误覆盖当前进度，拖入文件后需要点击“🚀 确认载入该工程”才会真正执行替换。载入成功后，系统会在后台重新计算拓扑结构，并瞬间重绘出动态图谱。同时，上传面板会自动隐身清空，还你一个极度清爽的界面。

    🎯 **总结建议：**
    *“每天搞科研，下班先导出”*。利用好追加模式（累加新文献）与记忆库（存档当前进度），你可以将 Bio-Graph Agent 作为一个长期运行的超级大脑，在几个月的时间里，慢慢将几十上百篇文献，编织成一张价值连城的疾病与分子靶点网络！

    ✂️ **五、 专家手动干预 (右侧 "图谱数据管理中心")**
    无论 AI 多么强大，在严谨的科研图谱中，人类专家的专业判断永远拥有最高优先级。开启 📝 **开启手动编辑面板**，你将在右侧获得图谱的“上帝权限”。

    管理中心分为三大模块：

    1.  ⚡ **快捷功能 (全局大盘管理)**
        * 🧹 *一键清除孤立节点：* 点击后，系统会全盘扫描。只要某个节点既没有指向别人的线，也没有被别人指的线，就会被当做“孤立无援”的废弃节点一键清空。
        * 📝 *批量修改文献/来源名：* 发现图谱中某篇 PDF 的名字太乱？在这里选中旧名字，输入新名字（如 *Nature_2023_p53*），系统会自动替换所有相关节点 and 连线的出处来源，确保溯源清晰。
        * ➕ *手动添加节点：* 如果 AI 漏掉了一个极其核心的基因或蛋白，你可以在此手动输入其名称、别名和来源，直接将它强制加入画布。
    2.  🎯 **节点操作 (精确打击)**
        在下拉菜单中搜索并选中你关心的某个节点，系统提供四种手术级别的操作：
        * ✏️ *修改信息：* 重命名节点的标准名称，或增减它的别名。
        * 🧲 *强制合并 (极其好用)：* 如果你发现图中有 p53 和 TP53 两个节点应该是一个东西。选中 p53，选择合并到 TP53。系统会瞬间将 p53 身上的所有连线转移给 TP53，并将两者的别名合并，最后销毁 p53。
        * 🔀 *节点拆分：* 将一个笼统的节点（如 *突变型与野生型p53*）硬拆成两个独立的新节点。最绝的是，系统会列出原来节点身上的每一条连线，让你逐一分配这条线是给新节点A、给新节点B、复制给两者，还是直接丢弃。
        * 🗑️ *危险删除：* 彻底销毁该节点，并连带拔除所有与它有关的调控连线。
    3.  🔗 **关系操作 (连线修剪与搭桥)**
        在下拉菜单中分别选定图上的 起点节点 A 和 终点节点 B，系统会帮你找出它们之间的所有羁绊：
        * ✏ *管理已有连线：* 逆转方向（如果发现 AI 把上游和下游搞反了，可以一键反转箭头方向）；修改性质（将关联类型在标准词汇中切换，并可修改其原文证据和来源）。
        * 🚨 *斩断连线：* 对于文献中提取出的毫无意义的背景介绍或假阳性，点击删除，该连线会彻底从图谱中抹除。
        * ➕ *新增一条连线：* 文献中没提到但你凭借背景知识确认 A 促进了 B？直接选择由谁指向谁、定好关系类型，手动建立这座隐秘的桥梁。

    🤖 **六、 AI 智能图谱工具 (右侧专属面板)**
    如果说“手动编辑面板”是你的手术刀，那么 AI 智能图谱工具 就是你的“超级智囊团”。在右侧面板选择对应的 AI 模块，你可以让大模型深度介入图谱的清洗、生长与解读。

    1.  🧹 **智能洗树 (Pruning)**
        当你导入了大量文献，图谱往往会变得庞杂且存在冗余。洗树模块提供两种强大的自动化清洗能力：
        * 🔍 *拓扑结构智能诊断：* 点击“开始 AI 智能诊断图谱”，大模型将通读全图谱的连线逻辑，并生成一份“审查清单”建议去 **Merge** 同义节点、**Hierarchy** 建立家族层级、或 **Downgrade** 宽泛捷径为虚线。在清单中勾选你认可的建议，点击一键执行，图谱将瞬间完成重组与权重叠加！
        * ✂ *意图节点清洗 (Intent-Based Pruning)：* 在文本框内用大白话输入你的“核心研究方向”。AI 会像审稿人一样，逐一排查图谱中的节点及邻居，为你罗列出一份“偏题节点处决名单”。确认无误后点击“处决”，这些无关节点及牵连的连线将被彻底从画布上抹杀。
    2.  🔍 **智能拓展 (Smart Expansion)**
        突破现有文献的边界，让图谱“自我生长”！当你发现图谱有个重要的分支需要深挖时：
        * 🎯 *选定锚点与检索策略：* 选择图谱中 1-3 个核心节点，并挂载检索引擎（支持直接搜索、智能扩展搜索、以及基于当前网络已知关系的最高级背景搜索）。
        * 📑 *筛选入库：* 系统会拉取外网最新文献并生成表格，勾选你认为有价值的文献，将其送入“解析队列”。
        * ⚙ *自动化融合队列 (无人值守模式)：* 开启连续自动解析开关。系统会自动排队抓取、阅读每一篇文献，并将新提取的节点与图谱现有节点进行“完美对齐与熔接”，回来时，你的图谱已经长成了一棵参天大树！
    3.  🔗 **智能桥接 (Bridging)**
        寻找潜藏科研靶点的终极利器。当你在图谱中对 A 和 B 两个分子的关系感到好奇时：
        * 如果图中已有间接路径：AI 会瞬间遍历网络，为你梳理出“A 是如何通过 X 和 Y 最终影响 B”的多步传导路径，并生成连贯的机制报告。
        * 如果是孤岛或无直接联系：系统判定它们断链后，会自动生成检索任务，呼叫外网大模型去强行挖掘 A 与 B 之间在最新前沿文献中是否已被证实存在关联，直接为你寻找基金申报的创新灵感！
    4.  🤖 **问 AI**
        图谱的“随身微观解说员”。当你面对错综复杂的图谱，不知道某条连线究竟代表什么生化反应时，直接在图谱中选中该“节点”或“连线”，系统会将这部分的微上下文（包括原文提取依据、文献来源出处）喂给大模型。AI 将为你生成一篇极其详实的“局部机制解读报告”。
    """)

def load_config():
    """在应用初次加载时，读取本地配置并注入到 session_state 中"""
    if "config_loaded" not in st.session_state:
        # 1. 设定需要持久化的默认值（去掉了所有绘图相关的选项）
        default_config = {
            "api_provider": "OpenRouter (国际节点)",
            "custom_base_url": "https://api.openai.com/v1",
            "selected_model_name": "Hunyuan 3 Preview (预览版 - 高性价比)",  # 记录下拉框的选择名称
            "custom_model_id": "",  # 用于 Ollama 等自定义手填的模型
            "search_database": "PubMed (生物医学权威)",
            "is_summary_only": False,
            "use_reflection": True,
            "append_mode": True,
            "entity_language": "关闭 (保持原文语言)",
            "ENABLE_EDITOR": True,  # ✨ 恢复的开关 1
            "ENABLE_AI_CLEANER": True,  # ✨ 恢复的开关 2
            "ui_language": "zh"
        }

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    local_config = json.load(f)
                    default_config.update(local_config)
            except Exception as e:
                print(f"读取本地配置失败: {e}")

        for k, v in default_config.items():
            if k not in st.session_state:
                st.session_state[k] = v

        if "language" not in st.session_state:
            st.session_state.language = st.session_state.ui_language

        st.session_state.config_loaded = True


def save_config():
    """仅保存核心业务设置，忽略绘图参数"""
    config_keys = [
        "api_provider", "custom_base_url", "selected_model_name", "custom_model_id",
        "search_database", "is_summary_only", "use_reflection", "append_mode",
        "entity_language", "ENABLE_EDITOR", "ENABLE_AI_CLEANER","ui_language"  # ✨ 添加这两个开关
    ]
    # 注意：这里已经没有 empower_ontology 等绘图参数了
    config_to_save = {k: st.session_state[k] for k in config_keys if k in st.session_state}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_to_save, f, indent=4)


def redraw_and_update():
    from back_logic import GraphVisualizer
    import os
    visualizer = GraphVisualizer()
    html_file = ".bio_knowledge_graph.html"
    if os.path.exists(html_file):
        os.remove(html_file)

    current_show_shortcuts = st.session_state.get("show_shortcuts_toggle", False)

    # 🧮 抓取三大赋权引擎的开关状态
    empower_ontology = st.session_state.get("empower_ontology", False)
    alpha_ontology = st.session_state.get("alpha_ontology", 0.5)

    # ✨ 新增：节点互相辐射开关
    empower_node = st.session_state.get("empower_node", False)
    beta_node = st.session_state.get("beta_node", 0.2)

    # ✨ 新增：主干连线加粗开关
    empower_edge = st.session_state.get("empower_edge", False)
    gamma_edge = st.session_state.get("gamma_edge", 0.1)

    visualizer.generate_html(
        st.session_state.master_entities,
        st.session_state.master_relations,
        output_file=html_file,
        show_shortcuts=current_show_shortcuts,
        empower_ontology=empower_ontology,
        alpha_ontology=alpha_ontology,
        empower_node=empower_node,  # 传给后端
        beta_node=beta_node,
        empower_edge=empower_edge,  # 传给后端
        gamma_edge=gamma_edge,
        output_lang=st.session_state.get("ui_language", "zh")
    )


    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            st.session_state.html_data = f.read()


# ==========================================
# 页面全局配置
# ==========================================
st.set_page_config(page_title="Bio-Graph Agent", page_icon="🧬", layout="wide")
# ==========================================
# 🌍 国际化 (i18n) 双语引擎
# ==========================================
UI_TEXT = {
    # 全局 & 标题
    "page_title": {"zh": "🧬 混元 Hy3 生物知识图谱自动生成引擎", "en": "🧬 Hy3 Bio-Knowledge Graph Generation Engine"},
    "btn_help": {"zh": "❓ 帮助与说明", "en": "❓ Help & Docs"},

    # 侧边栏
    "sidebar_title": {"zh": "## 🧬 Bio-Graph Agent", "en": "## 🧬 Bio-Graph Agent"},
    "sidebar_api_placeholder_local": {"zh": "Ollama 免密运行，可留空", "en": "Ollama local mode, can be empty"},
    "sidebar_api_placeholder_cloud": {"zh": "🔑 请输入您的 API Key", "en": "🔑 Enter your API Key"},
    "sidebar_api_help": {"zh": "刷新即焚，不会本地留存。", "en": "Cleared on refresh, not saved locally."},
    "sidebar_more_settings": {"zh": "⚙️ 更多设置", "en": "⚙️ More Settings"},
    "sidebar_engine_title": {"zh": "#### 🌐 大模型引擎", "en": "#### 🌐 LLM Engine"},
    "sidebar_api_provider": {"zh": "API 提供商", "en": "API Provider"},
    "sidebar_base_url": {"zh": "🔗 Base URL", "en": "🔗 Base URL"},
    "sidebar_model_id_custom": {"zh": "🧠 模型 ID (如 qwen2.5:7b)", "en": "🧠 Model ID (e.g. qwen2.5:7b)"},
    "sidebar_model_select": {"zh": "🧠 选择底层驱动模型", "en": "🧠 Select Base Model"},
    "sidebar_db_title": {"zh": "#### 📚 智能检索源", "en": "#### 📚 Smart Search Source"},
    "sidebar_db_select": {"zh": "数据库", "en": "Database"},
    "sidebar_features_title": {"zh": "#### 🎛️ 界面功能开关", "en": "#### 🎛️ Feature Toggles"},
    "sidebar_toggle_editor": {"zh": "📝 开启手动编辑面板", "en": "📝 Enable Manual Editor"},
    "sidebar_toggle_ai": {"zh": "🤖 开启 AI 智能图谱分析", "en": "🤖 Enable AI Graph Analysis"},
    "sidebar_contact": {"zh": "🤝 联系我们 / 了解更多", "en": "🤝 Contact / Learn More"},
    "contact_desc": {
        "zh": "**Bio-Graph Agent** 致力于将大语言模型与生物知识图谱无缝融合。\n\n- 🐛 发现 Bug？\n- 💡 有绝妙的新功能想法？\n- 🌟 觉得好用的话，来给我们点个 Star 吧！",
        "en": "**Bio-Graph Agent** is dedicated to seamlessly integrating LLMs with biological knowledge graphs.\n\n- 🐛 Found a bug?\n- 💡 Have a brilliant feature idea?\n- 🌟 If you like it, please give us a Star!"
    },
    "contact_github": {"zh": "⭐ 访问 Github 仓库", "en": "⭐ Visit Github Repo"},
    "contact_email": {"zh": "📧 合作邮箱: zoyuhandd@126.com", "en": "📧 Contact Email: zoyuhandd@126.com"},
    # ==========================
    # 选项下拉框 (Dropdown Options)
    # ==========================
    # 1. API 提供商
    "api_openrouter": {"zh": "OpenRouter (国际节点)", "en": "OpenRouter (Global)"},
    "api_tencent": {"zh": "腾讯云 (官方兼容接口)", "en": "Tencent Cloud (Official API)"},
    "api_siliconflow": {"zh": "硅基流动 (国内极速)", "en": "SiliconFlow (Fast CN)"},
    "api_ollama": {"zh": "Ollama (本地断网运行)", "en": "Ollama (Local Offline)"},
    "api_custom": {"zh": "自定义 (Custom)", "en": "Custom URL"},

    # 2. 模型选项
    "model_hy3_preview": {"zh": "Hunyuan 3 Preview (预览版 - 高性价比)", "en": "Hunyuan 3 Preview (Cost-effective)"},
    "model_hy3": {"zh": "Hunyuan 3 (正式版 - 最强推理)", "en": "Hunyuan 3 (Official - Max Reasoning)"},


    # 3. 数据库选项
    "db_pubmed": {"zh": "PubMed (生物医学权威)", "en": "PubMed (Biomedical Auth)"},
    "db_semanticscholar": {"zh": "Semantic Scholar (全科AI智能)", "en": "Semantic Scholar (AI Smart Search)"},
    # 预留给主界面的 Key（后续慢慢加）
    # 主界面：左侧文献输入与配置区
    "col1_title": {"zh": "📂 1. 文献输入与配置", "en": "📂 1. Document Input & Config"},
    "upload_pdf": {"zh": "上传生物学文献 (PDF)", "en": "Upload Biological Document (PDF)"},
    "pdf_read_success": {"zh": "📄 成功读取 PDF 文件，总计 **{pages}** 页。", "en": "📄 Successfully loaded PDF, **{pages}** pages in total."},

    # 零基础冷启动区
    "cold_start_title": {"zh": "### 💡 没有文献？对 AI 说说你要研究什么吧", "en": "### 💡 No PDF? Tell AI what you want to study"},
    "cold_start_caption": {"zh": "只需输入一句话，AI 将自动检索、分批验证并为你搭建初始知识网络。", "en": "Just type a sentence, AI will automatically search, verify, and build your initial knowledge network."},
    "cold_start_placeholder": {"zh": "你的研究方向 (例如: 巨噬细胞极化在肿瘤微环境中的作用)", "en": "Your research topic (e.g. Role of macrophage polarization in tumor microenvironment)"},
    "btn_ai_search": {"zh": "🚀 AI 一键检索并生成初始图谱", "en": "🚀 AI: Search & Generate Initial Graph"},
    "err_no_api_key": {"zh": "❌ 请先在上方配置 API Key！", "en": "❌ Please configure API Key above first!"},
    "warn_no_topic": {"zh": "⚠️ 请输入你想研究的内容！", "en": "⚠️ Please enter your research topic!"},
    "msg_generating_query": {"zh": "🤖 AI 正在生成专业检索式...", "en": "🤖 AI is generating professional query..."},
    "err_invalid_topic": {"zh": "🛑 输入内容似乎不是有效的科研方向，请换个说法试试！", "en": "🛑 The input doesn't seem to be a valid research topic, please try another phrase!"},
    "msg_generated_query": {"zh": "🔎 **生成检索式**: `{query}`", "en": "🔎 **Generated Query**: `{query}`"},
    "msg_fetching_papers": {"zh": "🌐 正在 {db} 抓取前 10 篇高相关文献准备排查...", "en": "🌐 Fetching top 10 relevant papers from {db} for screening..."},
    "warn_no_papers": {"zh": "⚠️ 抱歉，未能检索到任何相关文献，请尝试调整研究方向词汇。", "en": "⚠️ Sorry, no relevant papers found. Please try adjusting your keywords."},
    "msg_fetch_success": {"zh": "✅ 成功获取 {count} 篇候选文献，启动滑动窗口排查...", "en": "✅ Successfully fetched {count} candidate papers. Starting sliding window screening..."},
    "msg_validating_batch": {"zh": "🤔 正在验证第 {start} 到 {end} 篇文献的匹配度...", "en": "🤔 Validating relevance of papers {start} to {end}..."},
    "msg_batch_pass": {"zh": "✅ **第 {start}-{end} 篇文献验证通过**！与你的意图高度匹配。", "en": "✅ **Papers {start}-{end} passed validation**! Highly matches your intent."},
    "msg_ai_review": {"zh": "**AI 评审意见**：{reason}", "en": "**AI Review Opinion**: {reason}"},
    "msg_batch_fail": {"zh": "⏭️ 第 {start}-{end} 篇文献跑偏了 ({reason})。继续排查下一批...", "en": "⏭️ Papers {start}-{end} are off-topic ({reason}). Checking next batch..."},
    "msg_extracting_graph": {"zh": "🧠 正在精读过审文献，深度抽取初始图谱网络...", "en": "🧠 Deeply reading approved papers, extracting initial graph network..."},
    "msg_parsing_paper_progress": {"zh": "正在解析第 {idx}/{total} 篇过审文献 (PMID: {pmid})...", "en": "Parsing approved paper {idx}/{total} (PMID: {pmid})..."},
    "msg_graph_done": {"zh": "✨ 初始图谱构建完成！", "en": "✨ Initial graph construction completed!"},
    "toast_start_success": {"zh": "✅ 一键起步成功！", "en": "✅ One-click start successful!"},
    "err_all_validation_fail": {"zh": "❌ 检索到的 {count} 篇候选文献全部未能通过相关性验证。可能是研究方向过于前沿或关键词歧义，请尝试修改研究意图后重试！", "en": "❌ All {count} candidate papers failed relevance validation. Your topic might be too cutting-edge or ambiguous. Please revise and try again!"},

    # 提取模式设置区
    "extract_settings_title": {"zh": "⚙️ 2. 提取模式设置", "en": "⚙️ 2. Extraction Mode Settings"},
    "toggle_summary_only": {"zh": "⚡ 仅提取摘要模式 (速度极快)", "en": "⚡ Summary Only Mode (Extremely Fast)"},
    "toggle_reflection": {"zh": "🔍 启用自我反思纠错", "en": "🔍 Enable Self-Reflection Check"},
    "toggle_append_mode": {"zh": "🔗 追加模式 (叠加到现有图谱)", "en": "🔗 Append Mode (Merge to Existing Graph)"},
    "entity_lang_title": {"zh": "#### 🌐 实体命名规范", "en": "#### 🌐 Entity Naming Convention"},
    "entity_lang_label": {"zh": "强制统一图谱主节点（实体）的输出语言：", "en": "Force unify output language of main graph nodes (entities):"},
    "entity_lang_opt_original": {"zh": "关闭 (保持原文语言)", "en": "Off (Keep Original Language)"},
    "entity_lang_opt_zh": {"zh": "中文 (强制翻译为中文)", "en": "Chinese (Force Translate to Chinese)"},
    "entity_lang_opt_en": {"zh": "English (强制翻译为英文)", "en": "English (Force Translate to English)"},

    # 追加模式提示
    "append_info_ready": {"zh": "📦 记忆库就绪：当前已有 {count} 个节点。新知识将与之融合！", "en": "📦 Memory Bank Ready: Currently {count} nodes. New knowledge will be merged!"},
    "append_warn_off": {"zh": "⚠️ 注意：关闭追加模式，将会【清空】现有图谱，从零开始！历史文献也会清空", "en": "⚠️ Warning: Disabling Append Mode will [CLEAR] the existing graph and start from scratch! History will be cleared too."},

    # 解析范围设置区
    "parse_range_title": {"zh": "#### 🎯 设定解析范围", "en": "#### 🎯 Set Parsing Range"},
    "start_page": {"zh": "起始页码", "en": "Start Page"},
    "end_page": {"zh": "结束页码", "en": "End Page"},
    "warn_summary_range": {"zh": "💡 提示：摘要通常在文献前两页。为了保证极速提取，建议缩小页码范围！", "en": "💡 Tip: Abstracts are usually in the first two pages. To ensure speed, suggest narrowing the page range!"},
    "btn_start_parsing": {"zh": "🚀 开始解析 & 生成图谱", "en": "🚀 Start Parsing & Generate Graph"},

    # 历史文献侧边栏
    "history_sidebar_title": {"zh": "📚 历史分析文献", "en": "📚 Analyzed History Papers"},
    "history_no_docs": {"zh": "暂无已分析的文献", "en": "No analyzed papers yet"},

    # 右侧边界预览区
    "preview_col_title": {"zh": "👀 3. 边界预览", "en": "👀 3. Boundary Preview"},
    "preview_expander": {"zh": "🔍 点击查看选定范围的起止页 (用于确认边界)", "en": "🔍 Click to view start/end pages of selected range (Confirm boundaries)"},
    "preview_start_page": {"zh": "**🟢 起始边界 (第 {page} 页)**", "en": "**🟢 Start Boundary (Page {page})**"},
    "preview_end_page": {"zh": "**🔴 结束边界 (第 {page} 页)**", "en": "**🔴 End Boundary (Page {page})**"},
    "preview_render_fail": {"zh": "渲染失败: {e}", "en": "Render Failed: {e}"},
    "preview_same_page": {"zh": "起止页相同，无需重复展示。", "en": "Start and end pages are the same. No need to show again."},
    "preview_no_pdf": {"zh": "👈 请先在左侧上传 PDF 文献以激活边界预览。", "en": "👈 Please upload a PDF document on the left to activate preview."},

    # 记忆库与工程管理区
    "memory_mgr_title": {"zh": "💾 记忆库与工程管理", "en": "💾 Memory Bank & Project Management"},
    "btn_new_project": {"zh": "✨ 新建空白工程", "en": "✨ New Blank Project"},
    "btn_export_project": {"zh": "📤 导出工程 (.biokg)", "en": "📤 Export Project (.biokg)"},
    "toast_export_empty": {"zh": "⚠️ 当前记忆库为空，请先上传并解析文献！", "en": "⚠️ Memory bank is empty. Please upload and parse documents first!"},
    "warn_new_project_confirm": {"zh": "⚠️ **危险操作**：这将清空当前所有图谱与历史记录！（建议先导出保存）\n\n您确定要从零开始吗？", "en": "⚠️ **DANGER**: This will clear all current graphs and history! (Suggest exporting first)\n\nAre you sure you want to start from scratch?"},
    "btn_confirm_clear": {"zh": "🔴 确定清空", "en": "🔴 Confirm Clear"},
    "btn_cancel": {"zh": "取消", "en": "Cancel"},
    "upload_project": {"zh": "📥 载入历史工程文件 (.biokg / .json)", "en": "📥 Load History Project (.biokg / .json)"},
    "btn_confirm_load": {"zh": "🚀 确认载入该工程", "en": "🚀 Confirm Load Project"},
    "err_load_project": {"zh": "解析工程文件失败，请检查文件格式是否正确。报错信息: {e}", "en": "Failed to parse project file. Check format. Error: {e}"},
    # 核心引擎触发区 (图谱生成、洗树、融合、渲染)
    "err_missing_api_key": {"zh": "请先在左侧输入 API Key！", "en": "Please enter API Key on the left first!"},
    "msg_parsing_pages": {"zh": "🧠 智能体正在解析第 {start} 到 {end} 页...", "en": "🧠 Agent is parsing pages {start} to {end}..."},
    "msg_init_engine": {"zh": "🚀 正在启动知识图谱自动化构建引擎...", "en": "🚀 Starting Knowledge Graph Automated Build Engine..."},
    "msg_aligning_entities": {"zh": "🔗 正在进行跨文献 AI 语义对齐与图谱融合...", "en": "🔗 Performing cross-document AI semantic alignment and graph fusion..."},
    "msg_found_synonyms": {"zh": "🧬 AI 识别到 {count} 个跨文献同义实体！", "en": "🧬 AI identified {count} cross-document synonymous entities!"},
    "msg_rendering_graph": {"zh": "🎨 正在生成网络拓扑交互图谱...", "en": "🎨 Generating network topology interactive graph..."},
    "msg_gen_success": {"zh": "🎉 图谱生成与数据融合成功！", "en": "🎉 Graph generation and data fusion successful!"},
    "err_gen_fail": {"zh": "❌ 图谱文件未生成。", "en": "❌ Graph file not generated."},
    "err_process_fail": {"zh": "处理过程中发生错误：{e}", "en": "Error occurred during processing: {e}"},
    # 图谱渲染、视觉引擎与导出区
    "export_section_title": {"zh": "### 📥 4. 知识图谱结果导出", "en": "### 📥 4. Export Knowledge Graph Results"},
    "btn_export_ent_json": {"zh": "📄 导出实体 (JSON)", "en": "📄 Export Entities (JSON)"},
    "btn_export_ent_csv": {"zh": "📊 导出实体 (CSV)", "en": "📊 Export Entities (CSV)"},
    "btn_export_rel_csv": {"zh": "🔗 导出关系 (CSV)", "en": "🔗 Export Relations (CSV)"},
    "btn_export_graph_html": {"zh": "🕸️ 导出交互图谱 (HTML)", "en": "🕸️ Export Interactive Graph (HTML)"},

    "toggle_show_shortcuts": {"zh": "👁️ 显示机制捷径边", "en": "👁️ Show Mechanism Shortcuts"},
    "toggle_empower_ontology": {"zh": "🧬 包含关系反哺\n(父节点变大)", "en": "🧬 Ontology Empower\n(Parent Node Enlarge)"},
    "slider_alpha_ontology": {"zh": "反哺转移比例 (α)", "en": "Transfer Ratio (α)"},
    "toggle_empower_node": {"zh": "🌟 节点互相辐射\n(强关联变大)", "en": "🌟 Node Empower\n(Hub Nodes Enlarge)"},
    "slider_beta_node": {"zh": "互相辐射加成率 (β)", "en": "Radiation Bonus Rate (β)"},
    "toggle_empower_edge": {"zh": "🔗 核心主干加粗\n(高频连线变粗)", "en": "🔗 Edge Empower\n(High-freq Edges Thicken)"},
    "slider_gamma_edge": {"zh": "连线增粗系数 (γ)", "en": "Edge Thickening Factor (γ)"},

    "default_biokg_filename": {"zh": "我的图谱工程.biokg", "en": "My_Graph_Project.biokg"},
    # 图谱数据管理中心：全局与导航
    "editor_title": {"zh": "🎛️ 图谱数据管理中心", "en": "🎛️ Graph Data Management Center"},
    "nav_select_module": {"zh": "选择管理模块：", "en": "Select Management Module:"},
    "nav_quick": {"zh": "⚡ 快捷功能", "en": "⚡ Quick Functions"},
    "nav_node": {"zh": "🎯 节点操作", "en": "🎯 Node Operations"},
    "nav_rel": {"zh": "🔗 关系操作", "en": "🔗 Relation Operations"},

    # 快捷功能区
    "quick_clear_title": {"zh": "#### 🧹 一键清理", "en": "#### 🧹 One-Click Cleanup"},
    "quick_clear_desc": {"zh": "清理掉那些既不是起点、也不是终点的“孤立无援”的节点。", "en": "Clean up isolated nodes that are neither source nor target."},
    "btn_clear_isolated": {"zh": "🗑️ 清除所有孤立节点", "en": "🗑️ Clear All Isolated Nodes"},
    "toast_clear_success": {"zh": "✅ 成功清理了 {count} 个孤立节点！", "en": "✅ Successfully cleared {count} isolated nodes!"},
    "toast_no_isolated": {"zh": "当前图谱很健康，没有发现孤立节点。", "en": "The graph is healthy. No isolated nodes found."},
    "quick_rename_title": {"zh": "#### 📝 批量修改文献/来源名", "en": "#### 📝 Batch Rename Source"},
    "lbl_no_source": {"zh": "当前图谱没有来源记录。", "en": "No source records in current graph."},
    "lbl_select_source": {"zh": "选择要修改的文献/来源名", "en": "Select source to rename"},
    "lbl_new_source": {"zh": "输入新的名称 (如：Nature_2023_p53)", "en": "Enter new name (e.g. Nature_2023_p53)"},
    "btn_replace_source": {"zh": "🔄 一键替换全图谱来源", "en": "🔄 Replace Source Globally"},
    "err_empty_name": {"zh": "❌ 新名称不能为空！", "en": "❌ New name cannot be empty!"},
    "toast_rename_success": {"zh": "✅ 成功替换 '{old}'", "en": "✅ Successfully replaced '{old}'"},
    "quick_add_title": {"zh": "#### ➕ 手动添加节点", "en": "#### ➕ Manually Add Node"},
    "lbl_new_node_name": {"zh": "输入新节点标准名 (必填)", "en": "New Node Standard Name (Required)"},
    "lbl_new_node_aliases": {"zh": "输入别名 (选填，逗号分隔)", "en": "Aliases (Optional, comma separated)"},
    "lbl_new_node_source": {"zh": "输入文献来源 (为空记为'手动添加')", "en": "Doc Source (Leave blank for 'Manual Add')"},
    "btn_add_node": {"zh": "💾 保存并添加节点", "en": "💾 Save & Add Node"},
    "err_node_exists": {"zh": "⚠️ 节点已经存在！", "en": "⚠️ Node already exists!"},
    "toast_add_node_success": {"zh": "✅ 节点添加成功！", "en": "✅ Node added successfully!"},
    "default_manual_add": {"zh": "手动添加", "en": "Manual Add"},

    # 节点操作区
    "err_empty_graph": {"zh": "当前图谱为空，无法操作。", "en": "Graph is empty, cannot operate."},
    "lbl_search_node": {"zh": "🔍 搜索并选择要操作的节点", "en": "🔍 Search & select node to operate"},
    "opt_select": {"zh": "-- 请选择 --", "en": "-- Please Select --"},
    "lbl_current_selected": {"zh": "### 当前选中: `{node}`", "en": "### Currently Selected: `{node}`"},
    "lbl_select_action": {"zh": "选择操作：", "en": "Select Action:"},
    "act_edit": {"zh": "✏️ 修改信息", "en": "✏️ Edit Info"},
    "act_merge": {"zh": "🧲 合并到...", "en": "🧲 Merge to..."},
    "act_split": {"zh": "🔀 节点拆分", "en": "🔀 Split Node"},
    "act_delete": {"zh": "🗑️ 危险删除", "en": "🗑️ Danger Delete"},
    "lbl_new_std_name": {"zh": "新标准名", "en": "New Standard Name"},
    "lbl_new_aliases": {"zh": "别名 (逗号分隔)", "en": "Aliases (comma separated)"},
    "btn_save_edit": {"zh": "💾 保存修改", "en": "💾 Save Changes"},
    "toast_edit_success": {"zh": "✅ 节点修改成功！", "en": "✅ Node edited successfully!"},
    "desc_merge": {"zh": "将 `{node}` 的所有关系转移给另一个节点，随后销毁本体。", "en": "Transfer all relations of `{node}` to another node, then destroy the original."},
    "lbl_select_merge_target": {"zh": "选择目标节点", "en": "Select Target Node"},
    "btn_confirm_merge": {"zh": "🧲 确认合并", "en": "🧲 Confirm Merge"},
    "toast_merge_success": {"zh": "✅ 成功合并入 {target}！", "en": "✅ Successfully merged into {target}!"},
    "desc_split": {"zh": "将 `{node}` 拆分为两个独立节点，并重新分配它的关系连线。", "en": "Split `{node}` into two independent nodes and reallocate its relations."},
    "split_step1": {"zh": "##### 1. 定义拆分后的新节点", "en": "##### 1. Define Splitted New Nodes"},
    "lbl_new_node_a": {"zh": "新节点 A (如：mutant p53)", "en": "New Node A (e.g. mutant p53)"},
    "lbl_new_aliases_a": {"zh": "节点 A 别名 (逗号分隔)", "en": "Node A Aliases (comma separated)"},
    "lbl_new_node_b": {"zh": "新节点 B (如：wild-type p53)", "en": "New Node B (e.g. wild-type p53)"},
    "lbl_new_aliases_b": {"zh": "节点 B 别名 (逗号分隔)", "en": "Node B Aliases (comma separated)"},
    "split_step2": {"zh": "##### 2. 分配原有关系连线", "en": "##### 2. Allocate Original Relations"},
    "desc_no_rel_to_split": {"zh": "（该节点目前没有任何连线，无需分配）", "en": "(This node has no relations to allocate)"},
    "split_a": {"zh": "给 A", "en": "To A"},
    "split_b": {"zh": "给 B", "en": "To B"},
    "split_both": {"zh": "A 和 B 都要 (复制)", "en": "To Both (Copy)"},
    "split_discard": {"zh": "丢弃该线", "en": "Discard Edge"},
    "btn_confirm_split": {"zh": "🔀 确认执行拆分", "en": "🔀 Confirm Split"},
    "err_split_names_empty": {"zh": "❌ 两个新节点的名称都不能为空！", "en": "❌ Both new node names cannot be empty!"},
    "err_split_names_same": {"zh": "❌ 新节点 A 和 B 不能同名！", "en": "❌ Node A and B cannot have the same name!"},
    "toast_split_success": {"zh": "✅ 节点已成功拆分为 {a} 和 {b}！", "en": "✅ Node successfully split into {a} and {b}!"},
    "default_manual_split": {"zh": "手动拆分", "en": "Manual Split"},
    "warn_delete_node": {"zh": "⚠️ 警告：删除 `{node}` 将同时拔除所有相关连线！", "en": "⚠️ Warning: Deleting `{node}` will remove all its relations!"},
    "btn_confirm_delete": {"zh": "🚨 确认彻底删除", "en": "🚨 Confirm Delete"},
    "toast_delete_success": {"zh": "✅ 彻底清除！", "en": "✅ Completely Cleared!"},

    # 关系操作区
    "lbl_search_rel_title": {"zh": "### 🔍 搜索两个节点间的关联", "en": "### 🔍 Search Association Between Nodes"},
    "lbl_select_node_a": {"zh": "📍 选择节点 A", "en": "📍 Select Node A"},
    "lbl_select_node_b": {"zh": "🎯 选择节点 B", "en": "🎯 Select Node B"},
    "warn_same_node": {"zh": "⚠️ 节点 A 和节点 B 不能相同，暂不支持操作自环关系。", "en": "⚠️ Node A and B cannot be the same. Self-loop not supported yet."},
    "lbl_rel_op_mode": {"zh": "针对 `{a}` 与 `{b}` 之间的操作：", "en": "Operations between `{a}` and `{b}`:"},
    "rel_mode_edit": {"zh": "✏️ 管理两者间已有关系", "en": "✏️ Manage Existing Relations"},
    "rel_mode_add": {"zh": "➕ 新增一条关系连线", "en": "➕ Add New Relation Edge"},
    "info_no_direct_rel": {"zh": "💡 `{a}` 和 `{b}` 之间目前没有任何直接连线。", "en": "💡 No direct relation between `{a}` and `{b}` currently."},
    "lbl_select_specific_rel": {"zh": "二级菜单：选择要修改的具体连线", "en": "Sub-menu: Select specific edge to edit"},
    "lbl_change_dir": {"zh": "🔄 修改连线方向", "en": "🔄 Change Direction"},
    "dir_x_to_y": {"zh": "从 {x} ─▶ 指向 {y}", "en": "From {x} ─▶ To {y}"},
    "lbl_change_rel_type": {"zh": "🔖 修改关系类型", "en": "🔖 Change Relation Type"},
    "lbl_evidence": {"zh": "原文证据 (Evidence)", "en": "Evidence"},
    "lbl_reason": {"zh": "推理原因 (Reason)", "en": "Reason"},
    "lbl_doc_source": {"zh": "文献来源 (Doc Source)", "en": "Doc Source"},
    "btn_save_rel": {"zh": "💾 保存修改", "en": "💾 Save Changes"},
    "default_manual_edit": {"zh": "手动修改", "en": "Manual Edit"},
    "toast_rel_mod_success": {"zh": "✅ 关系及方向修改成功！", "en": "✅ Relation and direction modified successfully!"},
    "btn_delete_rel": {"zh": "🚨 斩断 / 删除此连线", "en": "🚨 Delete this Edge"},
    "toast_rel_del_success": {"zh": "✅ 连线已彻底删除！", "en": "✅ Edge completely deleted!"},
    "lbl_confirm_dir": {"zh": "确认新连线的指向：", "en": "Confirm New Edge Direction:"},
    "lbl_select_rel_type": {"zh": "🔖 选择关系类型", "en": "🔖 Select Relation Type"},
    "lbl_rel_evidence_opt": {"zh": "原文证据 / 备注 (选填)", "en": "Evidence / Notes (Optional)"},
    "lbl_rel_source_opt": {"zh": "文献来源 (选填，为空则记为'手动添加')", "en": "Doc Source (Leave blank for 'Manual Add')"},
    "btn_add_rel": {"zh": "💾 保存并添加连线", "en": "💾 Save & Add Edge"},
    "warn_rel_exists": {"zh": "⚠️ `{src}` 到 `{tgt}` 已经存在 `{type}` 类型的连线了！", "en": "⚠️ `{type}` relation already exists from `{src}` to `{tgt}`!"},
    "toast_rel_add_success": {"zh": "✅ 新关系建立成功！", "en": "✅ New relation established successfully!"},

    # 三大核心关系词典 (极其重要：用于UI显示，内部依然保持中文硬编码以匹配算法)
    "rel_positive": {"zh": "正作用", "en": "Positive"},
    "rel_negative": {"zh": "负作用", "en": "Negative"},
    "rel_correlation": {"zh": "相关", "en": "Correlation"},
    # 🤖 AI 智能图谱工具区
    "ai_tools_title": {"zh": "🤖 AI 智能图谱工具", "en": "🤖 AI Smart Graph Tools"},
    "ai_nav_select": {"zh": "选择 AI 模块：", "en": "Select AI Module:"},
    "ai_nav_pruning": {"zh": "🧹 智能洗树 (Pruning)", "en": "🧹 Smart Pruning"},
    "ai_nav_expansion": {"zh": "🔍 智能拓展 (Smart Expansion)", "en": "🔍 Smart Expansion"},
    "ai_nav_bridging": {"zh": "🔗 智能桥接 (Bridging)", "en": "🔗 Smart Bridging"},
    "ai_nav_ask": {"zh": "🤖 问 AI", "en": "🤖 Ask AI"},

    # 🧹 智能洗树 (Pruning) 模块
    "pruning_info": {"zh": "💡 拓扑清洗：基于大模型的上下文理解，自动发现并处理图谱中的同义词冗余、宏观与微观层级关系、以及机制捷径边。",
                     "en": "💡 Topology Pruning: Based on LLM's context understanding, automatically handle synonym redundancy, macro/micro hierarchies, and mechanism shortcut edges."},
    "pruning_desc": {"zh": "点击下方按钮，将当前图谱的拓扑结构与文献证据发送给大模型进行诊断。",
                     "en": "Click the button below to send the current graph topology and evidence to LLM for diagnosis."},
    "btn_start_pruning": {"zh": "🚀 开始 AI 智能诊断图谱", "en": "🚀 Start AI Smart Graph Diagnosis"},
    "err_pruning_no_key": {"zh": "❌ 拦截：系统检测到您未填写 API Key！AI 图谱清洗需要调用大模型，请先在侧边栏配置密钥。",
                           "en": "❌ Blocked: No API Key detected! AI Pruning requires LLM. Please configure the key in the sidebar first."},
    "msg_pruning_diagnosing": {"zh": "🧠 大模型正在深度阅读文献证据并梳理图谱拓扑... (请耐心等待)",
                               "en": "🧠 LLM is deeply reading evidence and analyzing topology... (Please wait)"},
    "toast_pruning_done": {"zh": "✅ 大模型诊断完成！", "en": "✅ LLM diagnosis completed!"},
    "pruning_tip_shortcut": {"zh": "💡 诊断完成后，请直接在上方【图谱显示控制面板】灵活开启或关闭捷径边的显示。",
                             "en": "💡 After diagnosis, you can flexibly toggle the display of shortcut edges in the [Display Control Panel] above."},

    # 📋 审查清单
    "review_list_title": {"zh": "### 📋 智能修改审查清单", "en": "### 📋 Smart Modification Review List"},
    "rev_merge": {"zh": "🧲 **合并同义词**: 将 `{removes}` 合并入 `{target}` (原因: {reason})",
                  "en": "🧲 **Merge Synonyms**: Merge `{removes}` into `{target}` (Reason: {reason})"},
    "rev_hierarchy": {"zh": "🌳 **建立层级**: 建立 `{parent}` ─[包含]▶ `{child}` (原因: {reason})",
                      "en": "🌳 **Build Hierarchy**: Build `{parent}` ─[Contain]▶ `{child}` (Reason: {reason})"},
    "rev_downgrade": {"zh": "📉 **降级捷径边**: 将连线 `{src} ─[{rel}]▶ {tgt}` 降级为推导虚线 (原因: {reason})",
                      "en": "📉 **Downgrade Shortcut**: Downgrade `{src} ─[{rel}]▶ {tgt}` to inferred dashed line (Reason: {reason})"},
    "rev_remove": {"zh": "✂️ **删除越级连线**: 彻底移除 `{src} ─[{rel}]▶ {tgt}` (原因: {reason})",
                   "en": "✂️ **Remove Edge**: Completely remove `{src} ─[{rel}]▶ {tgt}` (Reason: {reason})"},
    "no_reason": {"zh": "未提供原因", "en": "No reason provided"},
    "btn_confirm_pruning": {"zh": "💾 确认执行选中的优化", "en": "💾 Confirm Executing Selected Optimizations"},
    "toast_pruning_exec_done": {"zh": "✅ 优化已完美执行！", "en": "✅ Optimizations executed perfectly!"},

    # ✂️ 智能节点清洗 (Intent-Based Pruning)
    "intent_pruning_title": {"zh": "✂️ 智能节点清洗 (Intent-Based Pruning)", "en": "✂️ Intent-Based Pruning"},
    "intent_pruning_info": {"zh": "💡 意图剪枝：大模型将根据你输入的研究兴趣方向，揪出图谱中偏题或无关的对象（如误抓的其他器官/疾病），一键抹去它们及其连线。",
                            "en": "💡 Intent Pruning: LLM will identify off-topic or irrelevant nodes (e.g., wrong organs/diseases) based on your research interest, erasing them and their edges with one click."},
    "lbl_user_interest": {"zh": "请描述你当前聚焦的核心研究方向（例如：我只关心肠道上皮细胞的衰老机制，不关心其他器官）",
                          "en": "Describe your core research focus (e.g., I only care about intestinal epithelial cell aging, ignore other organs)"},
    "btn_find_irrelevant": {"zh": "🔍 根据我的方向，找出偏题节点", "en": "🔍 Find Off-topic Nodes Based on My Focus"},
    "warn_empty_interest": {"zh": "⚠️ 请输入您的研究兴趣方向！", "en": "⚠️ Please enter your research interest focus!"},
    "msg_finding_irrelevant": {"zh": "🧠 大模型正在逐一审视节点及邻居，挖掘偏题内容...",
                               "en": "🧠 LLM is reviewing nodes and neighbors to find off-topic content..."},
    "toast_find_irrelevant_done": {"zh": "✅ 诊断完成，请在下方确认清洗名单！",
                                   "en": "✅ Diagnosis done, please confirm the purge list below!"},

    # 🧹 偏题节点处决名单
    "purge_list_title": {"zh": "### 🧹 偏题节点处决名单", "en": "### 🧹 Off-topic Nodes Purge List"},
    "purge_list_caption": {"zh": "请确认以下清洗建议。勾选【删除】的节点及其**所有相关连线**将被彻底从图谱中抹去。",
                           "en": "Please confirm the purge suggestions. Checked nodes and **ALL their relations** will be completely erased from the graph."},
    "col_delete": {"zh": "🗑️ 删除", "en": "🗑️ Delete"},
    "col_node_name": {"zh": "节点名称", "en": "Node Name"},
    "col_neighbors": {"zh": "其连接的邻居", "en": "Connected Neighbors"},
    "col_risk_level": {"zh": "风险等级", "en": "Risk Level"},
    "col_ai_reason": {"zh": "AI 判定依据", "en": "AI Judgement Basis"},
    "btn_execute_purge": {"zh": "🚨 确认处决勾选节点", "en": "🚨 Execute Purge on Checked Nodes"},
    "toast_purge_success": {"zh": "✅ 成功清理了 {count} 个偏题节点及其连线！图谱瞬间纯净！",
                            "en": "✅ Successfully purged {count} off-topic nodes & edges! Graph is now pure!"},
    "btn_cancel_purge": {"zh": "放弃本次剪枝", "en": "Cancel This Pruning"},

    # 🔍 智能拓展 (Smart Expansion) 模块
    "expansion_info": {"zh": "💡 选中图谱中的关键节点，系统将自动在 {db} 中检索前沿文献，并由 AI 提取摘要知识，自动将其延伸至当前图谱。",
                       "en": "💡 Select key nodes, the system will automatically search {db} for cutting-edge papers. AI will extract abstract knowledge and extend the current graph."},
    "lbl_select_nodes_exp": {"zh": "🎯 请选择要拓展的核心节点 (建议 1-3 个):",
                             "en": "🎯 Select core nodes to expand (Recommend 1-3):"},
    "lbl_search_strategy": {"zh": "🧠 选择检索与拓展策略：", "en": "🧠 Select Search & Expand Strategy:"},
    "strategy_direct": {"zh": "⚡ 直接搜索 (速度极快，精准字符匹配)", "en": "⚡ Direct Search (Extremely fast, exact match)"},
    "strategy_smart": {"zh": "🧠 智能搜索 (AI 扩充同义词与 Mesh 主题词)",
                       "en": "🧠 Smart Search (AI expands synonyms & Mesh terms)"},
    "strategy_bg": {"zh": "🌐 背景搜索 (最强：AI 阅读图谱已知连线，智能发散机制)",
                    "en": "🌐 Background Search (Strongest: AI reads known edges, smart divergence)"},
    "lbl_max_results": {"zh": "📄 检索返回文献数量上限", "en": "📄 Max Papers to Fetch"},
    "btn_web_search": {"zh": "🔍 联网搜索相关文献", "en": "🔍 Web Search Related Papers"},
    "warn_select_nodes_first": {"zh": "⚠️ 请先在上方选择至少一个节点！", "en": "⚠️ Please select at least one node above!"},
    "msg_fetching_api": {"zh": "🌐 正在生成策略并呼叫 {db} API 获取最新文献...",
                         "en": "🌐 Generating strategy & calling {db} API for latest papers..."},
    "err_need_key_for_ai_search": {"zh": "❌ 拦截：请先在侧边栏配置 API Key 以启用 AI 搜索功能。",
                                   "en": "❌ Blocked: Please configure API Key in sidebar to enable AI search."},
    "toast_search_success": {"zh": "✅ 成功检索到 {count} 篇相关文献！", "en": "✅ Successfully fetched {count} related papers!"},

    # 检索结果表格
    "search_results_title": {"zh": "### 📑 检索结果 (请勾选需要深度分析的文献)",
                             "en": "### 📑 Search Results (Check papers for deep analysis)"},
    "col_include_graph": {"zh": "✅ 引入图谱", "en": "✅ Include to Graph"},
    "col_paper_title": {"zh": "文献标题", "en": "Paper Title"},
    "col_year": {"zh": "年份", "en": "Year"},
    "btn_add_to_queue": {"zh": "📥 将勾选文献加入解析队列", "en": "📥 Add Checked Papers to Queue"},
    "warn_check_one_paper": {"zh": "⚠️ 请至少在表格中勾选一篇文献！", "en": "⚠️ Please check at least one paper in the table!"},
    "toast_added_to_queue": {"zh": "✅ 已加入队列！请在下方控制台进行单步处理。",
                             "en": "✅ Added to queue! Please process step-by-step in the console below."},

    # 深度融合任务队列 (状态机面板)
    "queue_title": {"zh": "### ⚙️ 深度融合任务队列 (进度: {idx}/{total})",
                    "en": "### ⚙️ Deep Fusion Task Queue (Progress: {idx}/{total})"},
    "queue_current_doc": {"zh": "👉 **当前准备解析:**\n\n📄 {title}\n*(PMID: {pmid})*",
                          "en": "👉 **Currently Parsing:**\n\n📄 {title}\n*(PMID: {pmid})*"},
    "toggle_auto_run": {"zh": "🔁 开启连续自动解析 (无人值守模式)", "en": "🔁 Auto-Run Mode (Unattended Execution)"},
    "warn_auto_running": {"zh": "⚠️ 自动巡航模式运行中... (若需中途强行中止，请点击页面右上角自带的 'Stop' 按钮)",
                          "en": "⚠️ Auto-cruise running... (To stop forcefully, click the 'Stop' button at the top right of the page)"},
    "btn_run_this": {"zh": "▶️ 解析并融合本篇", "en": "▶️ Parse & Fuse This Paper"},
    "btn_skip_this": {"zh": "⏭️ 跳过这篇", "en": "⏭️ Skip This Paper"},
    "btn_stop_queue": {"zh": "🛑 终止任务并清空", "en": "🛑 Abort Task & Clear Queue"},
    "msg_deep_parsing": {"zh": "⏳ 正在深度解析并提取 {pmid} 的知识...",
                         "en": "⏳ Deep parsing and extracting knowledge from {pmid}..."},
    "toast_skip_short_abstract": {"zh": "文献 {pmid} 摘要为空或过短，已自动跳过。",
                                  "en": "Paper {pmid} abstract is empty or too short, auto-skipped."},
# 🔗 智能桥接 (Intelligent Bridging)
    "bridge_info": {"zh": "💡 选中两个节点，AI 将在图谱中寻找它们之间的所有多步通路，并推导深层分子机制。如果是孤岛，可一键呼叫 AI 联网挖掘！", "en": "💡 Select two nodes. AI will find all multi-step paths between them and deduce deep mechanisms. If they are isolated, one-click to call AI for web mining!"},
    "lbl_bridge_node_a": {"zh": "🎯 起点实体 (Node A):", "en": "🎯 Source Entity (Node A):"},
    "lbl_bridge_node_b": {"zh": "🎯 终点实体 (Node B):", "en": "🎯 Target Entity (Node B):"},
    "lbl_max_depth": {"zh": "🛤️ 最大探索深度 (Max Hops限制，防噪音)", "en": "🛤️ Max Exploration Depth (Max Hops limit to prevent noise)"},
    "btn_start_bridge": {"zh": "🚀 启动跨文献机制桥接与推导", "en": "🚀 Start Cross-Literature Mechanism Bridging & Deduction"},
    "warn_same_nodes_bridge": {"zh": "⚠️ 起点和终点不能是同一个节点！", "en": "⚠️ Source and target cannot be the same node!"},
    "warn_select_nodes_bridge": {"zh": "⚠️ 请先在上方选择节点！", "en": "⚠️ Please select nodes above first!"},
    "msg_scanning_paths": {"zh": "🔍 正在执行图论算法，扫描全图拓扑路径...", "en": "🔍 Executing graph algorithm to scan full topology paths..."},
    "msg_island": {"zh": "🕳️ **图谱孤岛**：在当前最高 {depth} 步的限制下，【{a}】和【{b}】之间毫无关联。", "en": "🕳️ **Graph Island**: Under the limit of {depth} hops, there is no connection between [{a}] and [{b}]."},
    "prompt_island_search": {"zh": "呼叫 AI 联网挖掘【{a}】与【{b}】的潜在机制", "en": "Call AI to web mine potential mechanism between [{a}] and [{b}]"},
    "msg_direct_only": {"zh": "⚡ **直接相关**：当前图谱仅发现【{a}】和【{b}】的表面直接联系。似乎缺乏中间介导物（如通路蛋白）的解释。", "en": "⚡ **Direct Only**: Only surface direct links found between [{a}] and [{b}]. Seems to lack explanations of intermediate mediators (e.g. pathway proteins)."},
    "prompt_direct_search": {"zh": "呼叫 AI 联网挖掘【{a}】与【{b}】的深层中间通路", "en": "Call AI to web mine deep intermediate pathways between [{a}] and [{b}]"},
    "msg_complex_paths": {"zh": "🧬 发现 {count} 条跨越节点的复杂机制路径！", "en": "🧬 Found {count} complex mechanism paths across nodes!"},
    "err_need_key_for_summary": {"zh": "❌ 请先在侧边栏配置 API Key 以启用 AI 总结。", "en": "❌ Please configure API Key in the sidebar to enable AI summary."},
    "msg_writing_report": {"zh": "🧠 资深 AI 学者正在阅读证据碎片，撰写跨文献机制报告...", "en": "🧠 Senior AI scholar is reading evidence fragments to write cross-literature mechanism report..."},
    "report_title": {"zh": "### 📑 AI 跨文献机制推导报告", "en": "### 📑 AI Cross-Literature Mechanism Deduction Report"},
    "report_subtitle": {"zh": "> *起点: {a} | 终点: {b} | 基于本地图谱 {count} 条拓扑路径*", "en": "> *Source: {a} | Target: {b} | Based on {count} topology paths in local graph*"},
    "msg_evaluating_strategy": {"zh": "🧠 AI 正在评估并生成专属检索策略...", "en": "🧠 AI is evaluating and generating exclusive search strategy..."},
    "err_ai_rejected": {"zh": "🛑 **AI 驳回请求**：根据现有生命科学常识，【{a}】和【{b}】之间没有合理的生物学机制交集。", "en": "🛑 **AI Rejected**: Based on common life science knowledge, there is no reasonable biological mechanism intersection between [{a}] and [{b}]."},
    "msg_search_strategy": {"zh": "💡 **检索策略**: `{query}`", "en": "💡 **Search Strategy**: `{query}`"},
    "warn_no_mechanism_papers": {"zh": "⚠️ PubMed 中未检索到相关机制文献。", "en": "⚠️ No relevant mechanism papers found in PubMed."},
    "search_res_title_bridge": {"zh": "### 🔎 联网检索结果：关于【{a}】与【{b}】的关系文献", "en": "### 🔎 Web Search Results: Papers on the relation between [{a}] and [{b}]"},
    "search_res_caption_bridge": {"zh": "💡 请勾选你认为真正相关的文献，AI 将只下载并精读这些文献的摘要来拼接机制。", "en": "💡 Please check papers you think are truly relevant. AI will only download and deep-read their abstracts to splice the mechanism."},
    "col_deep_read": {"zh": "精读", "en": "Deep Read"},
    "col_pub_date": {"zh": "发表日期", "en": "Pub Date"},
    "btn_start_sniper_extract": {"zh": "🧬 对已勾选文献启动【狙击式机制提取】", "en": "🧬 Start [Sniper Mechanism Extraction] on checked papers"},
    "warn_check_one_paper_bridge": {"zh": "⚠️ 请至少勾选一篇文献供 AI 阅读！", "en": "⚠️ Please check at least one paper for AI to read!"},
    "msg_sniper_extracting": {"zh": "📚 正在后台秒传摘要并进行跨文献机制缝合...", "en": "📚 Sending abstracts in background for cross-literature mechanism suturing..."},
    "fmt_paper_title": {"zh": "--- 文献 PMID: {pmid} (Title: {title}) ---", "en": "--- Paper PMID: {pmid} (Title: {title}) ---"},
    "ai_bridge_report_title": {"zh": "### 💡 AI 联网桥接机制报告 (等待审批)", "en": "### 💡 AI Web Bridging Mechanism Report (Pending Approval)"},
    "no_text_explanation": {"zh": "无文本解释", "en": "No text explanation"},
    "warn_no_clear_chain": {"zh": "🕵️‍♂️ 虽然阅读了你指定的文献，但 AI 未能提取到明确连接这俩靶点的可靠微观机制链。", "en": "🕵️‍♂️ Although read the specified papers, AI failed to extract a reliable micro-mechanism chain clearly connecting these two targets."},
    "btn_clear_report": {"zh": "清空报告", "en": "Clear Report"},
    "msg_extracted_links": {"zh": "🧩 成功提取到 {count} 条专属机制链路。是否将其并入主图谱？", "en": "🧩 Successfully extracted {count} exclusive mechanism links. Merge them into the main graph?"},
    "btn_accept_merge": {"zh": "✅ 认可并完美融入主图谱", "en": "✅ Accept & Perfectly Merge into Main Graph"},
    "msg_bulletproof_merging": {"zh": "正在执行防弹级融合...", "en": "Executing bulletproof fusion..."},
    "fmt_downgrade_reason": {"zh": "[智能桥接自动降级：已挖掘出深层通路] {old}", "en": "[Smart Bridging Auto-downgrade: Deep pathways mined] {old}"},
    "toast_bridge_merged": {"zh": "✅ 桥接机制已成功融合！图谱已生长！", "en": "✅ Bridge mechanism successfully merged! Graph has grown!"},
    "btn_reject_clear": {"zh": "❌ 感觉不对，放弃并清空", "en": "❌ Feels wrong, reject and clear"},

    # 🤖 问 AI (Ask AI)
    "ask_ai_info": {"zh": "💡 选中图谱中的任何节点或连线，AI 将结合它的【文献来源依据】和【网络拓扑】，为您提供独家解读。", "en": "💡 Select any node or edge in the graph. AI will provide an exclusive interpretation combining its [Literature Evidence] and [Network Topology]."},
    "lbl_what_to_explain": {"zh": "你想让 AI 解读什么？", "en": "What do you want AI to explain?"},
    "explain_node": {"zh": "解读节点 (Node)", "en": "Explain Node"},
    "explain_edge": {"zh": "解读关系连线 (Edge)", "en": "Explain Relation (Edge)"},
    "warn_no_nodes_in_graph": {"zh": "图谱中还没有节点。", "en": "No nodes in the graph yet."},
    "lbl_select_node_to_explain": {"zh": "请选择要解读的节点：", "en": "Please select the node to explain:"},
    "btn_explain_node": {"zh": "✨ 让 AI 深度解读该节点", "en": "✨ Let AI deeply explain this node"},
    "msg_extracting_context": {"zh": "🧠 正在提取 {node} 的微上下文并生成解读...", "en": "🧠 Extracting micro-context of {node} and generating explanation..."},
    "msg_no_connections": {"zh": "该节点目前没有与其他节点相连。", "en": "This node currently has no connections to other nodes."},
    "report_node_title": {"zh": "### 📝 AI 解读报告", "en": "### 📝 AI Explanation Report"},
    "lbl_select_two_nodes": {"zh": "### 🔍 选择需要解读关系的两个节点", "en": "### 🔍 Select two nodes to explain their relation"},
    "warn_same_node_ask": {"zh": "⚠️ 节点 A 和节点 B 不能相同，暂不支持解读自环关系。", "en": "⚠️ Node A and B cannot be the same. Self-loop not supported yet."},
    "info_no_rel_between": {"zh": "ℹ️ 暂无 `{a}` 与 `{b}` 之间的关系连线。", "en": "ℹ️ No relation edge between `{a}` and `{b}` yet."},
    "lbl_select_rel_to_explain": {"zh": "🔗 发现可用连线，请选择具体要解读的那一条：", "en": "🔗 Found available edges, please select the specific one to explain:"},
    "btn_explain_edge": {"zh": "✨ 让 AI 深度解读该连线", "en": "✨ Let AI deeply explain this edge"},
    "msg_analyzing_edge": {"zh": "🧠 正在分析连线机制并生成解读...", "en": "🧠 Analyzing edge mechanism and generating explanation..."},
    "report_edge_title": {"zh": "### 📝 AI 连线机制解读报告", "en": "### 📝 AI Edge Mechanism Explanation Report"},
}


def t(key, default=""):
    """
    智能翻译函数：根据当前 session_state 中的 ui_language 选项返回对应文本。
    如果没找到 key，则返回 default，若无 default 则直接返回 key 本身。
    """
    lang = st.session_state.get("ui_language", "zh")  # 默认中文
    if key in UI_TEXT:
        return UI_TEXT[key].get(lang, default if default else key)
    return default if default else key

title_col, btn_col = st.columns([5, 1])
with title_col:
    st.title(t("page_title"))
with btn_col:
    # 稍微往下挤一点点（用一行空行），让按钮在垂直方向上和标题的文字居中对齐
    st.markdown("<br>", unsafe_allow_html=True)

    # 渲染帮助按钮，点击即触发上面的弹窗函数
    if st.button(t("btn_help"), use_container_width=True, type="secondary"):
        show_help_dialog()
st.markdown("---")
# 📁 创建一个持久化文件夹，用来保存所有分析过的原文
HISTORY_DIR = ".history_docs"
os.makedirs(HISTORY_DIR, exist_ok=True)

# 初始化全局图谱记忆中枢
if "master_entities" not in st.session_state:
    st.session_state.master_entities = []
if "master_relations" not in st.session_state:
    st.session_state.master_relations = []
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "html_data" not in st.session_state:
    st.session_state.html_data = ""
if "pubmed_search_results" not in st.session_state:
    st.session_state.pubmed_search_results = []

# 📝 初始化历史文献列表
if "analyzed_files" not in st.session_state:
    st.session_state.analyzed_files = []

load_config()

# append_mode = True
# ==========================================
# 侧边栏配置：核心 API 和模型选择
# ==========================================


with st.sidebar:
    st.markdown("## 🧬 Bio-Graph Agent")
    st.markdown("---")
    is_local = "Ollama" in st.session_state.get("api_provider", "")
    api_key_placeholder = t("sidebar_api_placeholder_local") if is_local else t("sidebar_api_placeholder_cloud")

    api_key = st.text_input("API Key", type="password",
                            label_visibility="collapsed",
                            placeholder=api_key_placeholder,
                            help=t("sidebar_api_help"))
    if is_local and not api_key:
        api_key = "dummy-key-for-ollama"

    st.markdown("---")


    with st.popover(t("sidebar_more_settings"), use_container_width=True):
        # ==========================================
        # 🌍 全局语言切换开关 (无缝接入原生配置中心版)
        # ==========================================
        # 1. 根据当前 session 的值，决定哪个按钮被高亮选中
        current_index = 0 if st.session_state.get("ui_language", "zh") == "zh" else 1

        lang_choice = st.radio(
            "🌐 Language / 语言",
            ["中文 (Chinese)", "英文（English）"],
            index=current_index,
            horizontal=True
        )

        new_lang = "en" if "English" in lang_choice else "zh"

        # 2. 如果检测到用户切换了语言
        if st.session_state.get("ui_language") != new_lang:
            st.session_state.ui_language = new_lang
            st.session_state.language = new_lang  # 👈 继续喂给后端双保险
            save_config()  # 👈 ✨ 直接呼叫你的原生保存函数！
            st.rerun()
        # ==========================================

        st.markdown("---")

        st.markdown(t("sidebar_engine_title"))

        api_providers_map = {
            t("api_openrouter"): "https://openrouter.ai/api/v1",
            t("api_tencent"): "https://api.hunyuan.cloud.tencent.com/v1",
            t("api_siliconflow"): "https://api.siliconflow.cn/v1",
            t("api_ollama"): "http://localhost:11434/v1",
            t("api_custom"): "custom"
        }

        st.selectbox(t("sidebar_api_provider"), list(api_providers_map.keys()), key="api_provider", on_change=save_config)

        # 🛡️ 安全防御 1：防止切换语言时，旧语言的选项残留在缓存中报错
        current_provider = st.session_state.get("api_provider")
        if current_provider not in api_providers_map:
            current_provider = list(api_providers_map.keys())[0]

        # 🚨 逻辑修复：直接用翻译后的键值去对比，保证中英文下都能正确匹配
        if current_provider == t("api_custom"):
            base_url = st.text_input("🔗 Base URL", key="custom_base_url", on_change=save_config)
        else:
            base_url = api_providers_map[current_provider]

        # 🚨 逻辑修复：只要包含 Ollama 或 Custom 的字眼即可，兼容中英文
        is_local_or_custom = "Ollama" in current_provider or "Custom" in current_provider or "自定义" in current_provider

        if is_local_or_custom:
            # 对于本地或自定义源，只能手填模型 ID
            selected_model_id = st.text_input(t("sidebar_model_id_custom"), key="custom_model_id", on_change=save_config)
        else:
            # 对于云端源，使用你极其优雅的字典映射
            model_options = {
                t("model_hy3_preview"): "tencent/hy3-preview",
                t("model_hy3"): "tencent/hy3",
            }
            # UI显示的是 keys，存进 config 的是 selected_model_name
            st.selectbox(t("sidebar_model_select"), list(model_options.keys()), key="selected_model_name", on_change=save_config)
            # 实际传给下游 Pipeline 或 Agent 的 ID
            # 🛡️ 安全防御 2
            current_model = st.session_state.get("selected_model_name")
            if current_model not in model_options:
                current_model = list(model_options.keys())[0]

            selected_model_id = model_options[current_model]

        st.markdown("---")
        st.markdown(t("sidebar_db_title"))
        db_sources = ["PubMed (生物医学权威)", "Semantic Scholar (全科AI智能)"]
        st.selectbox(t("sidebar_db_select"), db_sources, key="search_database", on_change=save_config)

        st.markdown("---")

        # ✨ 恢复：功能模块开关
        st.markdown(t("sidebar_features_title"))
        ENABLE_EDITOR = st.toggle(t("sidebar_toggle_editor"), key="ENABLE_EDITOR", on_change=save_config)
        ENABLE_AI_CLEANER = st.toggle(t("sidebar_toggle_ai"), key="ENABLE_AI_CLEANER", on_change=save_config)

        st.markdown("---")
        with st.expander(t("sidebar_contact")):
            st.markdown(t("contact_desc"))
            st.link_button(t("contact_github"), "https://github.com/24238-T-34/-Bio-Graph-Agent-Hy3-", use_container_width=True)
            st.caption(t("contact_email"))
        st.markdown("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n...")
        st.markdown("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nit's a bug\nif you see this")

#    st.markdown("---")

# ==========================================
# 主界面：全新的左右双栏平衡布局
# ==========================================
left_col, right_col = st.columns([1, 1], gap="large")

# 初始化全局触发变量
start_button = False
uploaded_file = None

# --- 左侧控制栏 ---
with left_col:
    st.subheader(t("col1_title"))
    uploaded_file = st.file_uploader(t("upload_pdf"), type=["pdf"])

    if uploaded_file:
        # 🛡️ 核心优化 1：文件与页数双重缓存锁
        if "tmp_path" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                st.session_state["tmp_path"] = tmp.name
                st.session_state["file_name"] = uploaded_file.name

            # 💡 性能修复：PdfReader 必须放在 if 内部！
            reader = PdfReader(st.session_state["tmp_path"])
            st.session_state["total_pages"] = len(reader.pages)

        total_pages = st.session_state["total_pages"]
        tmp_path = st.session_state["tmp_path"]
        st.markdown("---")
        st.info(t("pdf_read_success").format(pages=total_pages))
        st.divider()

    # ==========================================
    # 🌟 零基础冷启动 (Cold Start) 探索模块
    # ==========================================
    if not st.session_state.master_entities and not st.session_state.master_relations and not uploaded_file:
        st.markdown(t("cold_start_title"))
        st.caption(t("cold_start_caption"))

        user_topic = st.text_input(t("cold_start_placeholder"), key="cold_start_topic")

        if st.button(t("btn_ai_search"), type="primary", use_container_width=True):
            current_api_key = api_key.strip()
            if not current_api_key:
                st.error(t("err_no_api_key"))
            elif not user_topic.strip():
                st.warning(t("warn_no_topic"))
            else:
                from LLM_SYS import BioBrainAgent
                from WebSearcher import get_searcher

                current_db = st.session_state.get("search_database", "PubMed (生物医学权威)")
                searcher = get_searcher(current_db)
                agent = BioBrainAgent(api_key=current_api_key)

                with st.spinner(t("msg_generating_query")):
                    query = agent.generate_topic_query(user_topic)

                if "[INVALID_TOPIC]" in query:
                    st.error(t("err_invalid_topic"))
                else:
                    st.info(t("msg_generated_query").format(query=query))

                    db_name = "PubMed" if "PubMed" in current_db else "Semantic Scholar"
                    with st.spinner(t("msg_fetching_papers").format(db=db_name)):
                        results = searcher.search_articles(query, max_results=10)

                    if not results:
                        st.warning(t("warn_no_papers"))
                    else:
                        st.success(t("msg_fetch_success").format(count=len(results)))

                        batch_size = 3
                        success = False
                        valid_pmids = []

                        # 🔄 开启滑动窗口排查
                        for i in range(0, len(results), batch_size):
                            chunk = results[i: i + batch_size]
                            curr_start = i + 1
                            curr_end = min(i + batch_size, len(results))

                            with st.spinner(t("msg_validating_batch").format(start=curr_start, end=curr_end)):
                                combined_abstracts = ""
                                current_pmids = []

                                for res in chunk:
                                    pmid = res.get('pmid')
                                    abs_text = searcher.fetch_abstract(pmid)
                                    if len(abs_text) > 50:
                                        combined_abstracts += f"\n\n--- PMID: {pmid} ---\n{abs_text}"
                                        current_pmids.append(pmid)

                                if not combined_abstracts:
                                    continue
                                current_ui_lang = st.session_state.get("language", "zh")
                                eval_result = agent.evaluate_abstracts_relevance(user_topic, combined_abstracts,output_lang=current_ui_lang)

                            if eval_result.get("is_relevant"):
                                st.success(t("msg_batch_pass").format(start=curr_start, end=curr_end))
                                st.info(t("msg_ai_review").format(reason=eval_result.get('reason')))
                                valid_pmids = current_pmids
                                success = True
                                break
                            else:
                                st.warning(t("msg_batch_fail").format(start=curr_start, end=curr_end,
                                                                      reason=eval_result.get('reason')))

                        # ==========================================
                        # 循环结束后的最终处理
                        # ==========================================
                        if success and valid_pmids:
                            progress_text = t("msg_extracting_graph")
                            my_bar = st.progress(0, text=progress_text)

                            total_docs = len(valid_pmids)
                            for idx, pmid in enumerate(valid_pmids):
                                my_bar.progress((idx) / total_docs,
                                                text=t("msg_parsing_paper_progress").format(idx=idx + 1,
                                                                                            total=total_docs,
                                                                                            pmid=pmid))
                                abs_text = searcher.fetch_abstract(pmid)

                                current_use_ref = use_reflection if 'use_reflection' in locals() or 'use_reflection' in globals() else True
                                current_lang = entity_language if 'entity_language' in locals() or 'entity_language' in globals() else "English"

                                new_entities = agent.extract_entities_with_reflection(abs_text,
                                                                                      use_reflection=current_use_ref,
                                                                                      entity_lang=current_lang)
                                for ent in new_entities:
                                    ent["doc_source"] = f"PubMed:{pmid}"
                                    st.session_state.master_entities.append(ent)

                                new_relations = agent.extract_relations(abs_text, st.session_state.master_entities)
                                for rel in new_relations:
                                    rel["doc_source"] = f"PubMed:{pmid}"
                                    rel["weight"] = 1
                                    st.session_state.master_relations.append(rel)

                            my_bar.progress(1.0, text=t("msg_graph_done"))
                            st.toast(t("toast_start_success"), icon="🎉")
                            st.session_state.show_results = True
                            redraw_and_update()
                            st.rerun()
                        elif not success:
                            st.error(t("err_all_validation_fail").format(count=len(results)))

    st.subheader(t("extract_settings_title"))
    is_summary_only = st.toggle(t("toggle_summary_only"), key="is_summary_only", on_change=save_config)
    use_reflection = st.toggle(t("toggle_reflection"), key="use_reflection", on_change=save_config)
    append_mode = st.toggle(t("toggle_append_mode"), key="append_mode", on_change=save_config)

    st.markdown(t("entity_lang_title"))

    # 💡 内部固定的只读 Key（永不随语言切换而改变，彻底杜绝 KeyError 和缓存越界）
    lang_internal_keys = ["opt_original", "opt_zh", "opt_en"]


    # 💡 显示映射函数：只有在渲染到屏幕的那一瞬间，才把 Key 变成中/英文
    def get_lang_display(key):
        if key == "opt_original": return t("entity_lang_opt_original")
        if key == "opt_zh": return t("entity_lang_opt_zh")
        if key == "opt_en": return t("entity_lang_opt_en")
        return key


    selected_lang_key = st.radio(
        t("entity_lang_label"),
        options=lang_internal_keys,  # 缓存里存的永远是 "opt_xxx"
        format_func=get_lang_display,  # 界面上显示的是翻译后的文字
        index=0,
        key="entity_language_ui",  # 彻底安全了！
        horizontal=True
    )

    # 将内部 Key 映射回系统最初需要的硬编码指令（确保大模型行为不突变）
    backend_lang_map = {
        "opt_original": "关闭 (保持原文语言)",
        "opt_zh": "中文 (强制翻译为中文)",
        "opt_en": "English (强制翻译为英文)"
    }
    entity_language = backend_lang_map[selected_lang_key]

    if append_mode and len(st.session_state.master_entities) > 0:
        st.info(t("append_info_ready").format(count=len(st.session_state.master_entities)))
    elif not append_mode and len(st.session_state.master_entities) > 0:
        st.warning(t("append_warn_off"))

    if uploaded_file:
        default_end = min(2, total_pages) if is_summary_only else total_pages

        st.markdown(t("parse_range_title"))
        col_inputs1, col_inputs2 = st.columns(2)
        with col_inputs1:
            start_page = st.number_input(t("start_page"), min_value=1, max_value=total_pages, value=1)
        with col_inputs2:
            safe_default_end = max(start_page, default_end)
            end_page = st.number_input(t("end_page"), min_value=start_page, max_value=total_pages,
                                       value=safe_default_end)

        if is_summary_only and (end_page - start_page > 2):
            st.warning(t("warn_summary_range"))

        st.divider()
        start_button = st.button(t("btn_start_parsing"), use_container_width=True, type="primary")

# ==========================================
# 📁 后置侧边栏扩展区
# ==========================================
if uploaded_file and start_button:
    if append_mode:
        save_path = os.path.join(HISTORY_DIR, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        if uploaded_file.name not in st.session_state.analyzed_files:
            st.session_state.analyzed_files.append(uploaded_file.name)
    else:
        st.session_state.analyzed_files = []
        if os.path.exists(HISTORY_DIR):
            for fname in os.listdir(HISTORY_DIR):
                fpath = os.path.join(HISTORY_DIR, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                    except:
                        pass

with st.sidebar:
    if append_mode:
        st.markdown("---")
        st.header(t("history_sidebar_title"))

        if not st.session_state.analyzed_files:
            st.info(t("history_no_docs"))
        else:
            for fname in st.session_state.analyzed_files:
                fpath = os.path.join(HISTORY_DIR, fname)
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        file_bytes = f.read()
                    st.download_button(
                        label=f"📄 {fname}",
                        data=file_bytes,
                        file_name=fname,
                        mime="application/pdf",
                        key=f"history_{fname}",
                        use_container_width=True
                    )

# --- 右侧高清预览栏 ---
with right_col:
    st.subheader(t("preview_col_title"))
    if uploaded_file:
        def get_page_image_bytes(page_idx):
            doc = fitz.open(tmp_path)
            page = doc.load_page(page_idx)
            zoom_matrix = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=zoom_matrix)
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes


        with st.expander(t("preview_expander"), expanded=True):
            col_preview1, col_preview2 = st.columns(2)

            with col_preview1:
                st.markdown(t("preview_start_page").format(page=start_page))
                try:
                    img_start = get_page_image_bytes(start_page - 1)
                    st.image(img_start, use_container_width=True)
                except Exception as e:
                    st.error(t("preview_render_fail").format(e=e))

            with col_preview2:
                if start_page != end_page:
                    st.markdown(t("preview_end_page").format(page=end_page))
                    try:
                        img_end = get_page_image_bytes(end_page - 1)
                        st.image(img_end, use_container_width=True)
                    except Exception as e:
                        st.error(t("preview_render_fail").format(e=e))
                else:
                    st.markdown("**🔴 " + t("end_page") + "**")
                    st.info(t("preview_same_page"))
    else:
        st.info(t("preview_no_pdf"))

    # ==========================================
    # 💾 记忆库与工程管理区 (右栏底部)
    # ==========================================
    st.markdown("---")
    st.subheader(t("memory_mgr_title"))

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button(t("btn_new_project"), use_container_width=True):
            st.session_state.show_new_confirm = not st.session_state.get("show_new_confirm", False)

    with col_btn2:
        export_placeholder = st.empty()
        with export_placeholder:
            if st.button(t("btn_export_project"), use_container_width=True, key="fake_export_btn"):
                st.toast(t("toast_export_empty"), icon="🈳")

    if st.session_state.get("show_new_confirm", False):
        st.warning(t("warn_new_project_confirm"))
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button(t("btn_confirm_clear"), use_container_width=True):
                st.session_state.master_entities = []
                st.session_state.master_relations = []
                st.session_state.analyzed_files = []
                st.session_state.html_data = ""

                if os.path.exists(HISTORY_DIR):
                    for fname in os.listdir(HISTORY_DIR):
                        fpath = os.path.join(HISTORY_DIR, fname)
                        if os.path.isfile(fpath):
                            try:
                                os.remove(fpath)
                            except:
                                pass

                st.session_state.project_loaded_success = False
                st.session_state.show_new_confirm = False
                st.rerun()

        with col_n:
            if st.button(t("btn_cancel"), use_container_width=True):
                st.session_state.show_new_confirm = False
                st.rerun()

    if "project_uploader_key" not in st.session_state:
        st.session_state.project_uploader_key = "project_uploader_init"

    uploaded_project = st.file_uploader(
        t("upload_project"),
        type=["biokg", "json"],
        key=st.session_state.project_uploader_key
    )

    if uploaded_project is not None:
        try:
            loaded_data = json.load(uploaded_project)

            if st.button(t("btn_confirm_load"), type="primary", use_container_width=True):
                st.session_state.master_entities = loaded_data.get("entities", [])
                st.session_state.master_relations = loaded_data.get("relations", [])
                st.session_state.analyzed_files = loaded_data.get("analyzed_files", [])

                from back_logic import GraphVisualizer

                visualizer = GraphVisualizer()
                html_file = ".bio_knowledge_graph.html"

                if os.path.exists(html_file):
                    os.remove(html_file)

                visualizer.generate_html(
                    st.session_state.master_entities,
                    st.session_state.master_relations,
                    output_file=html_file,
                    output_lang=st.session_state.get("ui_language", "zh")
                )

                if os.path.exists(html_file):
                    with open(html_file, "r", encoding="utf-8") as f:
                        st.session_state.html_data = f.read()

                st.session_state.show_results = True
                st.session_state.project_uploader_key = f"project_uploader_{uuid.uuid4().hex}"

                st.rerun()
        except Exception as e:
            st.error(t("err_load_project").format(e=e))

# ==========================================
# 核心引擎触发与结果渲染区（全览画布排版）
# ==========================================
if uploaded_file and start_button:
    if not api_key:
        st.error(t("err_missing_api_key"))
    else:
        # 渲染在双栏下方，让最终的巨幅知识图谱能占满整张屏幕，视觉极其震撼
        st.markdown("---")

        # 🛠️ 核心 UI 修复：将 try 提到最外层，内部所有的 spinner 扁平化独立，避免重叠！
        try:
            # 实例化 Pipeline 并传入动态模型
            pipeline = BioGraphPipeline(api_key=api_key, model=selected_model_id,base_url=base_url)

            # 🟢 阶段一：独立的解析转圈
            with st.spinner(t("msg_parsing_pages").format(start=start_page, end=end_page)):

                # ✨ 新增 1：在前端画布准备好一个进度条组件
                ui_progress_bar = st.progress(0.0, text=t("msg_init_engine"))

                # ✨ 新增 2：定义一个“监听器”函数 (结合了进度条和气泡)
                def update_ui_progress(current, total, message):
                    # 计算安全百分比 (0.0 到 1.0 之间)
                    percent = min(max(current / total, 0.0), 1.0)
                    # 更新进度条
                    ui_progress_bar.progress(percent, text=message)
                    # 弹出右上角气泡 (模拟后端日志流)
                    st.toast(message, icon="⏳")

                # 1. 跑当前这篇文献，拿到新数据
                new_entities, new_relations = pipeline.run(
                    tmp_path,
                    start_page=start_page - 1,
                    end_page=end_page,
                    is_summary_only=is_summary_only,
                    use_reflection=use_reflection,
                    source_name=uploaded_file.name,
                    entity_lang=entity_language,
                    progress_callback=update_ui_progress,
                    output_lang=st.session_state.get("ui_language", "zh")
                )

            # 🟢 阶段二：独立的融合转圈 (上一个转圈已经销毁)
            if append_mode and len(st.session_state.master_entities) > 0:
                with st.spinner(t("msg_aligning_entities")):
                    # 1. 呼叫大模型裁判，获取同义词映射表 (如: {"TP53": "p53"})
                    alignment_map = pipeline.agent.align_global_entities(
                        st.session_state.master_entities,
                        new_entities
                    )

                    if alignment_map:
                        st.success(t("msg_found_synonyms").format(count=len(alignment_map)))

                        # ====================================================
                        # 2. 遍历新实体，执行融合手术 (双重拦截：精确匹配 + 语义对齐)
                        # ====================================================
                        aligned_new_entities = []
                        master_names = {ent["standard_name"]: ent for ent in st.session_state.master_entities}

                        for new_ent in new_entities:
                            new_name = new_ent.get("standard_name")
                            new_source = new_ent.get("doc_source", "")

                            # 🛡️ 拦截网 1：如果名字一模一样（代码级精准匹配）
                            if new_name in master_names:
                                master_ent = master_names[new_name]
                                aliases = master_ent.setdefault("aliases", [])
                                for new_alias in new_ent.get("aliases", []):
                                    if new_alias not in aliases and new_alias != new_name:
                                        aliases.append(new_alias)
                                old_source = master_ent.get("doc_source", "")
                                if new_source and new_source not in old_source:
                                    master_ent["doc_source"] = f"{old_source} | {new_source}"

                            # 🛡️ 拦截网 2：名字不一样，但大模型裁判认为它们是同一个东西
                            elif new_name in alignment_map:
                                master_name = alignment_map[new_name]
                                if master_name in master_names:
                                    master_ent = master_names[master_name]
                                    aliases = master_ent.setdefault("aliases", [])
                                    if new_name not in aliases:
                                        aliases.append(new_name)
                                    for new_alias in new_ent.get("aliases", []):
                                        if new_alias not in aliases and new_alias != master_name:
                                            aliases.append(new_alias)
                                    old_source = master_ent.get("doc_source", "")
                                    if new_source and new_source not in old_source:
                                        master_ent["doc_source"] = f"{old_source} | {new_source}"
                                else:
                                    aligned_new_entities.append(new_ent)
                            else:
                                aligned_new_entities.append(new_ent)

                    # 3. 移花接木：将新文献抽出的【关系网】强行接入全局标准节点
                    for rel in new_relations:
                        if rel.get("source") in alignment_map:
                            rel["source"] = alignment_map[rel["source"]]
                        if rel.get("target") in alignment_map:
                            rel["target"] = alignment_map[rel["target"]]

                    # ====================================================
                    # 4. 🔗 核心大招：关系去重与证据融合 (同类合并，异类保留)
                    # ====================================================
                    master_rel_map = {}
                    for existing_rel in st.session_state.master_relations:
                        key = (existing_rel.get("source"), existing_rel.get("target"), existing_rel.get("relation"))
                        master_rel_map[key] = existing_rel

                    for rel in new_relations:
                        key = (rel.get("source"), rel.get("target"), rel.get("relation"))
                        if key in master_rel_map:
                            existing_rel = master_rel_map[key]
                            existing_rel["weight"] = existing_rel.get("weight", 1) + 1

                            old_ev = existing_rel.get("evidence", "")
                            new_ev = rel.get("evidence", "")
                            if new_ev and new_ev not in old_ev:
                                existing_rel["evidence"] = f"{old_ev}\n---\n{new_ev}"

                            old_src = existing_rel.get("doc_source", "")
                            new_src = rel.get("doc_source", "")
                            if new_src and new_src not in old_src:
                                existing_rel["doc_source"] = f"{old_src} | {new_src}"
                        else:
                            rel["weight"] = 1
                            st.session_state.master_relations.append(rel)
                            master_rel_map[key] = rel

                    # 5. 将处理后的“干净”实体数据并入全局中枢
                    st.session_state.master_entities.extend(aligned_new_entities)

            elif append_mode:
                st.session_state.master_entities.extend(new_entities)
                st.session_state.master_relations.extend(new_relations)
            else:
                st.session_state.master_entities = new_entities
                st.session_state.master_relations = new_relations

            # 🟢 阶段三：独立的渲染转圈
            with st.spinner(t("msg_rendering_graph")):
                visualizer = GraphVisualizer()
                html_file = ".bio_knowledge_graph.html"

                # 🛡️ 破除幻觉机制：生成前强制删掉旧文件！
                if os.path.exists(html_file):
                    os.remove(html_file)

                # ✨ 漏洞修复：抓取当前控制台的所有开关和滑块状态（带默认值防呆）
                current_show_shortcuts = st.session_state.get("show_shortcuts_toggle", False)

                empower_ontology = st.session_state.get("empower_ontology", False)
                alpha_ontology = st.session_state.get("alpha_ontology", 0.5)

                empower_node = st.session_state.get("empower_node", False)
                beta_node = st.session_state.get("beta_node", 0.2)

                empower_edge = st.session_state.get("empower_edge", False)
                gamma_edge = st.session_state.get("gamma_edge", 0.1)

                # ✨ 将所有状态参数全部传给渲染器，保证新生成的图谱继承当前的视觉设置！
                visualizer.generate_html(
                    st.session_state.master_entities,
                    st.session_state.master_relations,
                    output_file=html_file,
                    show_shortcuts=current_show_shortcuts,
                    empower_ontology=empower_ontology,
                    alpha_ontology=alpha_ontology,
                    empower_node=empower_node,
                    beta_node=beta_node,
                    empower_edge=empower_edge,
                    gamma_edge=gamma_edge,
                    output_lang=st.session_state.get("ui_language", "zh")
                )

            # 🟢 阶段四：所有处理完成，将结果存入全局保险箱
            if os.path.exists(html_file):
                st.success(t("msg_gen_success"))
                with open(html_file, "r", encoding="utf-8") as f:
                    st.session_state.html_data = f.read()

                # 开启展示开关
                st.session_state.show_results = True
            else:
                st.error(t("err_gen_fail"))
                st.session_state.show_results = False

        except Exception as e:
            # 所有阶段任何一步报错，都会统一跳到这里处理，代码极其优雅
            st.error(t("err_process_fail").format(e=e))

# ==========================================
# 📥 独立渲染区：结果多元化导出与图谱展示（防白屏刷新机制）
# ==========================================
# 🌟 注意：下面这段代码必须完全没有缩进，贴紧最左侧！
if st.session_state.show_results and st.session_state.html_data:

    st.markdown(t("export_section_title"))

    entities_json = json.dumps(st.session_state.master_entities, ensure_ascii=False, indent=2)
    relations_json = json.dumps(st.session_state.master_relations, ensure_ascii=False, indent=2)

    df_entities = pd.DataFrame(st.session_state.master_entities)
    if 'aliases' in df_entities.columns:
        df_entities['aliases'] = df_entities['aliases'].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else x)
    csv_entities = df_entities.to_csv(index=False).encode('utf-8')

    df_relations = pd.DataFrame(st.session_state.master_relations)
    csv_relations = df_relations.to_csv(index=False).encode('utf-8') if not df_relations.empty else b""

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    with btn_col1:
        st.download_button(t("btn_export_ent_json"), entities_json, "bio_entities.json", "application/json",
                           use_container_width=True)
    with btn_col2:
        st.download_button(t("btn_export_ent_csv"), csv_entities, "bio_entities.csv", "text/csv", use_container_width=True)
    with btn_col3:
        st.download_button(t("btn_export_rel_csv"), csv_relations, "bio_relations.csv", "text/csv", use_container_width=True)
    with btn_col4:
        st.download_button(t("btn_export_graph_html"), st.session_state.html_data, "bio_graph.html", "text/html",
                           use_container_width=True)

    st.markdown("---")

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns(4)

    with ctrl_col1:
        st.toggle(t("toggle_show_shortcuts"), key="show_shortcuts_toggle", on_change=redraw_and_update)

    with ctrl_col2:
        st.toggle(t("toggle_empower_ontology"), key="empower_ontology", on_change=redraw_and_update)
        if st.session_state.get("empower_ontology", False):
            st.slider(t("slider_alpha_ontology"), 0.1, 1.0, 0.5, 0.1, key="alpha_ontology", on_change=redraw_and_update)

    with ctrl_col3:
        # ✨ 节点互相辐射
        st.toggle(t("toggle_empower_node"), key="empower_node", on_change=redraw_and_update)
        if st.session_state.get("empower_node", False):
            st.slider(t("slider_beta_node"), 0.1, 1.0, 0.2, 0.1, key="beta_node", on_change=redraw_and_update)

    with ctrl_col4:
        # ✨ 纯粹的连线加粗
        st.toggle(t("toggle_empower_edge"), key="empower_edge", on_change=redraw_and_update)
        if st.session_state.get("empower_edge", False):
            st.slider(t("slider_gamma_edge"), 0.05, 0.5, 0.1, 0.05, key="gamma_edge", on_change=redraw_and_update)


    # 🛡️ 渲染图谱 (原有代码，作为定位点)
    components.html(st.session_state.html_data, height=800, scrolling=True)

    st.markdown("---")

    # ====================================================================
    # 💡 核心位置：回填真实导出按钮 (放在 Tabs 前面防止 DOM 崩溃)
    # ====================================================================
    if len(st.session_state.master_entities) > 0:
        with export_placeholder:
            project_data = {
                "version": "1.0",
                "entities": st.session_state.master_entities,
                "relations": st.session_state.master_relations,
                "analyzed_files": st.session_state.analyzed_files
            }
            json_bytes = json.dumps(project_data, ensure_ascii=False).encode('utf-8')

            st.download_button(
                # 注意这里我们复用了之前侧边栏已经定义好的 btn_export_project 翻译
                label=t("btn_export_project"),
                data=json_bytes,
                file_name=t("default_biokg_filename"),
                mime="application/json",
                use_container_width=True,
                key="real_export_btn"
            )

    # ==========================================
    # 🎛️ 终极图谱数据管理中心
    # ==========================================

    if ENABLE_EDITOR and len(st.session_state.master_entities) > 0:
        st.subheader(t("editor_title"))

        # 🚀 终极架构修复：解耦 Navigation 渲染
        nav_keys = ["nav_quick", "nav_node", "nav_rel"]
        main_tab_key = st.radio(
            t("nav_select_module"),
            options=nav_keys,
            format_func=lambda k: t(k),
            horizontal=True,
            label_visibility="collapsed",
            key="main_nav_radio"
        )
        st.markdown("---")

        # -----------------------------------------
        # 方向一：快捷功能
        # -----------------------------------------
        if main_tab_key == "nav_quick":
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(t("quick_clear_title"))
                st.info(t("quick_clear_desc"))
                if st.button(t("btn_clear_isolated"), use_container_width=True):
                    connected_nodes = set()
                    for rel in st.session_state.master_relations:
                        connected_nodes.add(rel.get("source"))
                        connected_nodes.add(rel.get("target"))

                    old_count = len(st.session_state.master_entities)
                    st.session_state.master_entities = [
                        ent for ent in st.session_state.master_entities
                        if ent.get("standard_name") in connected_nodes
                    ]
                    if old_count - len(st.session_state.master_entities) > 0:
                        st.toast(
                            t("toast_clear_success").format(count=old_count - len(st.session_state.master_entities)),
                            icon="🧹")
                        redraw_and_update()
                        st.rerun()
                    else:
                        st.toast(t("toast_no_isolated"), icon="✨")

                st.markdown(t("quick_rename_title"))
                all_sources = set()
                for ent in st.session_state.master_entities:
                    if "doc_source" in ent: all_sources.add(ent["doc_source"])
                for rel in st.session_state.master_relations:
                    if "doc_source" in rel: all_sources.add(rel["doc_source"])
                if "analyzed_files" in st.session_state:
                    for f in st.session_state.analyzed_files: all_sources.add(f)

                all_sources = list(all_sources)

                if not all_sources:
                    st.info(t("lbl_no_source"))
                else:
                    with st.form("rename_source_form"):
                        old_source = st.selectbox(t("lbl_select_source"), all_sources)
                        new_source = st.text_input(t("lbl_new_source"))

                        if st.form_submit_button(t("btn_replace_source"), type="primary", use_container_width=True):
                            if not new_source.strip():
                                st.error(t("err_empty_name"))
                            elif new_source.strip() != old_source:
                                new_src_clean = new_source.strip()
                                for ent in st.session_state.master_entities:
                                    if ent.get("doc_source") == old_source: ent["doc_source"] = new_src_clean
                                for rel in st.session_state.master_relations:
                                    if rel.get("doc_source") == old_source:
                                        rel["doc_source"] = new_src_clean
                                        if "reason" in rel and old_source in rel["reason"]:
                                            rel["reason"] = rel["reason"].replace(f"[源自: {old_source}]",
                                                                                  f"[源自: {new_src_clean}]")
                                if old_source in st.session_state.analyzed_files:
                                    idx = st.session_state.analyzed_files.index(old_source)
                                    st.session_state.analyzed_files[idx] = new_src_clean
                                st.toast(t("toast_rename_success").format(old=old_source), icon="🎉")
                                redraw_and_update()
                                st.rerun()

            with col2:
                st.markdown(t("quick_add_title"))
                with st.form("manual_add_node_form"):
                    new_node_name = st.text_input(t("lbl_new_node_name"))
                    new_node_aliases = st.text_input(t("lbl_new_node_aliases"))
                    new_node_source = st.text_input(t("lbl_new_node_source"))

                    if st.form_submit_button(t("btn_add_node"), type="primary", use_container_width=True):
                        if not new_node_name.strip():
                            st.error(t("err_empty_name"))
                        else:
                            existing_names = [e.get("standard_name") for e in st.session_state.master_entities]
                            if new_node_name.strip() in existing_names:
                                st.warning(t("err_node_exists"))
                            else:
                                aliases_list = [a.strip() for a in
                                                new_node_aliases.split(",")] if new_node_aliases.strip() else []
                                final_source = new_node_source.strip() if new_node_source.strip() else t(
                                    "default_manual_add")
                                st.session_state.master_entities.append({
                                    "standard_name": new_node_name.strip(),
                                    "aliases": aliases_list,
                                    "doc_source": final_source
                                })
                                st.toast(t("toast_add_node_success"), icon="🎉")
                                redraw_and_update()
                                st.rerun()

        # -----------------------------------------
        # 🎯 方向二：节点操作
        # -----------------------------------------
        elif main_tab_key == "nav_node":
            all_node_names = sorted([e.get("standard_name") for e in st.session_state.master_entities])

            if not all_node_names:
                st.info(t("err_empty_graph"))
            else:
                # 💡 防崩溃下拉框设计：内部存 "__SELECT__"，外部显示翻译
                node_opts = ["__SELECT__"] + all_node_names
                target_node_name = st.selectbox(
                    t("lbl_search_node"),
                    node_opts,
                    format_func=lambda x: t("opt_select") if x == "__SELECT__" else x
                )

                if target_node_name != "__SELECT__":
                    target_ent = next(
                        (e for e in st.session_state.master_entities if e.get("standard_name") == target_node_name),
                        None)

                    if target_ent:
                        st.markdown(t("lbl_current_selected").format(node=target_node_name))

                        action_keys = ["act_edit", "act_merge", "act_split", "act_delete"]
                        action = st.radio(
                            t("lbl_select_action"),
                            options=action_keys,
                            format_func=lambda k: t(k),
                            horizontal=True,
                            label_visibility="collapsed",
                            key="node_action_radio"
                        )

                        # -- 修改信息 --
                        if action == "act_edit":
                            with st.form("edit_node_form"):
                                new_name = st.text_input(t("lbl_new_std_name"), value=target_ent.get("standard_name"))
                                current_aliases = ", ".join(target_ent.get("aliases", []))
                                new_aliases = st.text_input(t("lbl_new_aliases"), value=current_aliases)

                                if st.form_submit_button(t("btn_save_edit"), type="primary"):
                                    clean_new_name = new_name.strip()
                                    if clean_new_name:
                                        if clean_new_name != target_node_name:
                                            for rel in st.session_state.master_relations:
                                                if rel.get("source") == target_node_name: rel["source"] = clean_new_name
                                                if rel.get("target") == target_node_name: rel["target"] = clean_new_name

                                        target_ent["standard_name"] = clean_new_name
                                        target_ent["aliases"] = [a.strip() for a in new_aliases.split(",") if a.strip()]
                                        st.toast(t("toast_edit_success"), icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

                        # -- 合并节点 --
                        elif action == "act_merge":
                            st.info(t("desc_merge").format(node=target_node_name))
                            merge_target = st.selectbox(t("lbl_select_merge_target"),
                                                        [n for n in all_node_names if n != target_node_name])

                            if st.button(t("btn_confirm_merge"), type="primary", use_container_width=True):
                                for rel in st.session_state.master_relations:
                                    if rel.get("source") == target_node_name: rel["source"] = merge_target
                                    if rel.get("target") == target_node_name: rel["target"] = merge_target

                                dest_ent = next(e for e in st.session_state.master_entities if
                                                e.get("standard_name") == merge_target)
                                combined_aliases = set(
                                    dest_ent.get("aliases", []) + target_ent.get("aliases", []) + [target_node_name])
                                dest_ent["aliases"] = list(combined_aliases)

                                st.session_state.master_entities = [e for e in st.session_state.master_entities if
                                                                    e.get("standard_name") != target_node_name]
                                st.toast(t("toast_merge_success").format(target=merge_target), icon="🎉")
                                redraw_and_update()
                                st.rerun()

                        # -- 节点拆分 --
                        elif action == "act_split":
                            st.info(t("desc_split").format(node=target_node_name))

                            related_rels = []
                            for i, rel in enumerate(st.session_state.master_relations):
                                if rel.get("source") == target_node_name or rel.get("target") == target_node_name:
                                    related_rels.append((i, rel))

                            with st.form("split_node_form"):
                                st.markdown(t("split_step1"))
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    name_a = st.text_input(t("lbl_new_node_a"), value=f"{target_node_name}_A")
                                    aliases_a = st.text_input(t("lbl_new_aliases_a"),
                                                              value=", ".join(target_ent.get("aliases", [])))
                                with col_b:
                                    name_b = st.text_input(t("lbl_new_node_b"), value=f"{target_node_name}_B")
                                    aliases_b = st.text_input(t("lbl_new_aliases_b"), value="")

                                st.markdown(t("split_step2"))
                                rel_choices = {}
                                if not related_rels:
                                    st.caption(t("desc_no_rel_to_split"))
                                else:
                                    split_opt_keys = ["split_a", "split_b", "split_both", "split_discard"]


                                    # 💡 这里必须用闭包获取内部函数正确的上下文字典映射
                                    def get_safe_rel_display(val):
                                        if val == "正作用": return t("rel_positive")
                                        if val == "负作用": return t("rel_negative")
                                        if val == "相关": return t("rel_correlation")
                                        return val


                                    for idx, rel in related_rels:
                                        src = rel.get("source")
                                        tgt = rel.get("target")
                                        rel_type_str = rel.get("relation", "相关")

                                        # 界面显示的漂亮文字，如: p53 -[Positive]-> MDM2
                                        display_text = f"**{src}** ─[{get_safe_rel_display(rel_type_str)}]▶ **{tgt}**"

                                        rel_choices[idx] = st.radio(
                                            display_text,
                                            options=split_opt_keys,
                                            format_func=lambda k: t(k),
                                            horizontal=True,
                                            key=f"split_rel_{idx}"
                                        )

                                if st.form_submit_button(t("btn_confirm_split"), type="primary",
                                                         use_container_width=True):
                                    c_name_a = name_a.strip()
                                    c_name_b = name_b.strip()

                                    if not c_name_a or not c_name_b:
                                        st.error(t("err_split_names_empty"))
                                    elif c_name_a == c_name_b:
                                        st.error(t("err_split_names_same"))
                                    else:
                                        import copy

                                        st.session_state.master_entities = [e for e in st.session_state.master_entities
                                                                            if
                                                                            e.get("standard_name") != target_node_name]

                                        st.session_state.master_entities.append({
                                            "standard_name": c_name_a,
                                            "aliases": [x.strip() for x in aliases_a.split(",") if x.strip()],
                                            "doc_source": target_ent.get("doc_source", t("default_manual_split"))
                                        })
                                        st.session_state.master_entities.append({
                                            "standard_name": c_name_b,
                                            "aliases": [x.strip() for x in aliases_b.split(",") if x.strip()],
                                            "doc_source": target_ent.get("doc_source", t("default_manual_split"))
                                        })

                                        new_relations = []
                                        for i, rel in enumerate(st.session_state.master_relations):
                                            if i in rel_choices:
                                                choice_key = rel_choices[i]
                                                if choice_key == "split_discard":
                                                    continue

                                                is_source = (rel.get("source") == target_node_name)
                                                is_target = (rel.get("target") == target_node_name)


                                                def make_rel(node_name):
                                                    new_r = copy.deepcopy(rel)
                                                    if is_source: new_r["source"] = node_name
                                                    if is_target: new_r["target"] = node_name
                                                    return new_r


                                                if choice_key == "split_a":
                                                    new_relations.append(make_rel(c_name_a))
                                                elif choice_key == "split_b":
                                                    new_relations.append(make_rel(c_name_b))
                                                elif choice_key == "split_both":
                                                    new_relations.append(make_rel(c_name_a))
                                                    new_relations.append(make_rel(c_name_b))
                                            else:
                                                new_relations.append(rel)

                                        st.session_state.master_relations = new_relations
                                        st.toast(t("toast_split_success").format(a=c_name_a, b=c_name_b), icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

                        # -- 彻底删除 --
                        elif action == "act_delete":
                            st.error(t("warn_delete_node").format(node=target_node_name))
                            if st.button(t("btn_confirm_delete"), type="primary", use_container_width=True):
                                st.session_state.master_entities = [e for e in st.session_state.master_entities if
                                                                    e.get("standard_name") != target_node_name]
                                st.session_state.master_relations = [r for r in st.session_state.master_relations if
                                                                     r.get("source") != target_node_name and r.get(
                                                                         "target") != target_node_name]
                                st.toast(t("toast_delete_success"), icon="🗑️")
                                redraw_and_update()
                                st.rerun()

        # -----------------------------------------
        # 🎯 方向三：关系操作
        # -----------------------------------------
        elif main_tab_key == "nav_rel":
            all_node_names = sorted([e.get("standard_name") for e in st.session_state.master_entities])

            # 💡 数据底层必须是中文以兼容模型设定，UI显示靠 format_func
            SAFE_RELATIONS_INTERNAL = ["正作用", "负作用", "相关"]


            def get_rel_display(internal_val):
                if internal_val == "正作用": return t("rel_positive")
                if internal_val == "负作用": return t("rel_negative")
                if internal_val == "相关": return t("rel_correlation")
                return internal_val


            if not all_node_names:
                st.info(t("err_empty_graph"))
            else:
                st.markdown(t("lbl_search_rel_title"))
                col_a, col_b = st.columns(2)

                node_opts = ["__SELECT__"] + all_node_names
                with col_a:
                    node_a = st.selectbox(t("lbl_select_node_a"), node_opts,
                                          format_func=lambda x: t("opt_select") if x == "__SELECT__" else x)
                with col_b:
                    node_b = st.selectbox(t("lbl_select_node_b"), node_opts,
                                          format_func=lambda x: t("opt_select") if x == "__SELECT__" else x)

                if node_a != "__SELECT__" and node_b != "__SELECT__":
                    if node_a == node_b:
                        st.warning(t("warn_same_node"))
                    else:
                        st.markdown("---")

                        matching_rels = []
                        for i, r in enumerate(st.session_state.master_relations):
                            src = r.get("source")
                            tgt = r.get("target")
                            if (src == node_a and tgt == node_b) or (src == node_b and tgt == node_a):
                                matching_rels.append((i, r))

                        rel_mode_keys = ["rel_mode_edit", "rel_mode_add"]
                        rel_op_mode = st.radio(
                            t("lbl_rel_op_mode").format(a=node_a, b=node_b),
                            options=rel_mode_keys,
                            format_func=lambda k: t(k),
                            horizontal=True
                        )

                        # ==========================================
                        # 子功能 A：管理 / 修改 / 删除 现有关系
                        # ==========================================
                        if rel_op_mode == "rel_mode_edit":
                            if not matching_rels:
                                st.info(t("info_no_direct_rel").format(a=node_a, b=node_b))
                            else:
                                rel_options = {}
                                for idx, r in matching_rels:
                                    src = r.get("source")
                                    tgt = r.get("target")
                                    rel_type = r.get("relation", "相关")
                                    display_text = f"[{idx}] {src} ─[{get_rel_display(rel_type)}]▶ {tgt}"
                                    rel_options[display_text] = idx

                                selected_rel_text = st.selectbox(t("lbl_select_specific_rel"), list(rel_options.keys()))

                                rel_idx = rel_options[selected_rel_text]
                                target_rel = st.session_state.master_relations[rel_idx]

                                with st.form("edit_rel_form"):
                                    current_src = target_rel.get('source')

                                    dir_keys = ["dir_a_to_b", "dir_b_to_a"]


                                    def dir_display(k):
                                        if k == "dir_a_to_b": return t("dir_x_to_y").format(x=node_a, y=node_b)
                                        return t("dir_x_to_y").format(x=node_b, y=node_a)


                                    new_direction = st.selectbox(
                                        t("lbl_change_dir"),
                                        options=dir_keys,
                                        format_func=dir_display,
                                        index=0 if current_src == node_a else 1
                                    )

                                    current_rel = target_rel.get("relation", "")
                                    default_idx = SAFE_RELATIONS_INTERNAL.index(
                                        current_rel) if current_rel in SAFE_RELATIONS_INTERNAL else 0

                                    selected_rel_type = st.selectbox(
                                        t("lbl_change_rel_type"),
                                        options=SAFE_RELATIONS_INTERNAL,
                                        format_func=get_rel_display,
                                        index=default_idx
                                    )

                                    new_evidence = st.text_area(t("lbl_evidence"), value=target_rel.get("evidence", ""))
                                    new_reason = st.text_area(t("lbl_reason"), value=target_rel.get("reason", ""))
                                    new_doc_source = st.text_input(t("lbl_doc_source"),
                                                                   value=target_rel.get("doc_source",
                                                                                        t("default_manual_add")))

                                    if st.form_submit_button(t("btn_save_rel"), type="primary",
                                                             use_container_width=True):
                                        final_src, final_tgt = (node_a, node_b) if new_direction == "dir_a_to_b" else (
                                        node_b, node_a)

                                        st.session_state.master_relations[rel_idx]["source"] = final_src
                                        st.session_state.master_relations[rel_idx]["target"] = final_tgt
                                        st.session_state.master_relations[rel_idx]["relation"] = selected_rel_type
                                        st.session_state.master_relations[rel_idx]["evidence"] = new_evidence.strip()
                                        st.session_state.master_relations[rel_idx]["reason"] = new_reason.strip()
                                        st.session_state.master_relations[rel_idx][
                                            "doc_source"] = new_doc_source.strip() if new_doc_source.strip() else t(
                                            "default_manual_edit")

                                        st.toast(t("toast_rel_mod_success"), icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

                                st.markdown("---")
                                if st.button(t("btn_delete_rel"), type="primary", use_container_width=True):
                                    st.session_state.master_relations.pop(rel_idx)
                                    st.toast(t("toast_rel_del_success"), icon="✂️")
                                    redraw_and_update()
                                    st.rerun()

                        # ==========================================
                        # 子功能 B：手动搭桥，安全新增
                        # ==========================================
                        elif rel_op_mode == "rel_mode_add":
                            with st.form("add_rel_form"):

                                dir_keys = ["dir_a_to_b", "dir_b_to_a"]


                                def dir_display_add(k):
                                    if k == "dir_a_to_b": return t("dir_x_to_y").format(x=node_a, y=node_b)
                                    return t("dir_x_to_y").format(x=node_b, y=node_a)


                                direction = st.radio(
                                    t("lbl_confirm_dir"),
                                    options=dir_keys,
                                    format_func=dir_display_add,
                                    horizontal=True
                                )

                                selected_new_rel = st.selectbox(
                                    t("lbl_select_rel_type"),
                                    options=SAFE_RELATIONS_INTERNAL,
                                    format_func=get_rel_display
                                )

                                new_evidence = st.text_area(t("lbl_rel_evidence_opt"))
                                new_doc_source = st.text_input(t("lbl_rel_source_opt"))

                                if st.form_submit_button(t("btn_add_rel"), type="primary", use_container_width=True):
                                    final_src, final_tgt = (node_a, node_b) if direction == "dir_a_to_b" else (
                                    node_b, node_a)

                                    exist = any(r.get("source") == final_src and
                                                r.get("target") == final_tgt and
                                                r.get("relation") == selected_new_rel
                                                for r in st.session_state.master_relations)

                                    if exist:
                                        st.warning(t("warn_rel_exists").format(src=final_src, tgt=final_tgt,
                                                                               type=get_rel_display(selected_new_rel)))
                                    else:
                                        final_source_str = new_doc_source.strip() if new_doc_source.strip() else t(
                                            "default_manual_add")

                                        st.session_state.master_relations.append({
                                            "source": final_src,
                                            "target": final_tgt,
                                            "relation": selected_new_rel,
                                            "evidence": new_evidence.strip(),
                                            "reason": "用户手动添加",
                                            "doc_source": final_source_str
                                        })
                                        st.toast(t("toast_rel_add_success"), icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

# ==========================================
# 🤖 AI 智能图谱清洗中心 (真机驱动版)
# ==========================================

if ENABLE_AI_CLEANER and len(st.session_state.master_entities) > 0:
    st.markdown("---")
    st.subheader(t("ai_tools_title"))

    # 🚀 优化 1：使用带记忆锁的 Radio 导航替代失忆的 st.tabs
    ai_nav_keys = ["ai_nav_pruning", "ai_nav_expansion", "ai_nav_bridging", "ai_nav_ask"]
    ai_nav = st.radio(
        t("ai_nav_select"),
        options=ai_nav_keys,
        format_func=lambda k: t(k),
        horizontal=True,
        label_visibility="collapsed",
        key="ai_nav_radio"
    )
    st.markdown("---")

    # -----------------------------------------
    # 模块一：智能洗树 (Pruning)
    # -----------------------------------------
    if ai_nav == "ai_nav_pruning":
        st.info(t("pruning_info"))

        col_btn, col_toggle = st.columns([1, 1])
        with col_btn:
            st.write(t("pruning_desc"))
            if st.button(t("btn_start_pruning"), type="primary", use_container_width=True):
                current_api_key = api_key.strip()

                if not current_api_key:
                    st.error(t("err_pruning_no_key"))
                    st.stop()

                with st.spinner(t("msg_pruning_diagnosing")):
                    from LLM_SYS import BioBrainAgent

                    agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)
                    suggestions = agent.diagnose_graph(st.session_state.master_entities,
                                                       st.session_state.master_relations,
                                                       output_lang=st.session_state.get("ui_language", "zh"))

                    st.session_state.ai_suggestions = suggestions
                    st.toast(t("toast_pruning_done"), icon="🤖")
                    st.rerun()

        with col_toggle:
            st.info(t("pruning_tip_shortcut"))

        # -----------------------------------------
        # 📋 渲染真实的审查清单并执行
        # -----------------------------------------
        if hasattr(st.session_state, "ai_suggestions") and st.session_state.ai_suggestions:
            st.markdown(t("review_list_title"))

            with st.form("ai_prune_review_form"):
                selected_actions = []

                for i, sug in enumerate(st.session_state.ai_suggestions):
                    action = sug.get("action")
                    reason = sug.get("reason", t("no_reason"))

                    if action == "MERGE":
                        target = sug.get("target_node")
                        removes = sug.get("nodes_to_remove", [])
                        label = t("rev_merge").format(removes=removes, target=target, reason=reason)
                    elif action == "HIERARCHY":
                        parent = sug.get("parent")
                        child = sug.get("child")
                        label = t("rev_hierarchy").format(parent=parent, child=child, reason=reason)
                    elif action == "DOWNGRADE":
                        src = sug.get("source")
                        tgt = sug.get("target")
                        rel = sug.get("relation")
                        label = t("rev_downgrade").format(src=src, rel=rel, tgt=tgt, reason=reason)
                    elif action == "REMOVE":
                        src = sug.get("source")
                        tgt = sug.get("target")
                        rel = sug.get("relation")
                        label = t("rev_remove").format(src=src, rel=rel, tgt=tgt, reason=reason)
                    else:
                        continue

                    if st.checkbox(label, value=True, key=f"sug_{i}"):
                        selected_actions.append(sug)

                st.markdown("---")
                if st.form_submit_button(t("btn_confirm_pruning"), type="primary", use_container_width=True):

                    # 核心执行引擎
                    for act in selected_actions:
                        if act["action"] == "MERGE":
                            target = act.get("target_node")
                            removes = act.get("nodes_to_remove", [])
                            for r in st.session_state.master_relations:
                                if r.get("source") in removes: r["source"] = target
                                if r.get("target") in removes: r["target"] = target
                            st.session_state.master_entities = [e for e in st.session_state.master_entities if
                                                                e.get("standard_name") not in removes]

                        elif act["action"] == "HIERARCHY":
                            parent = act.get("parent")
                            child = act.get("child")
                            merged_evidence = "AI 智能逻辑推导"
                            merged_doc_source = "AI 分析"

                            for i in range(len(st.session_state.master_relations) - 1, -1, -1):
                                r = st.session_state.master_relations[i]
                                is_match = ((r.get("source") == parent and r.get("target") == child) or
                                            (r.get("source") == child and r.get("target") == parent))
                                # ⚠️ 注意这里内部依然保持中文 "相关" 以兼容算法
                                if is_match and r.get("relation") == "相关":
                                    merged_evidence = r.get("evidence", merged_evidence)
                                    merged_doc_source = r.get("doc_source", merged_doc_source)
                                    st.session_state.master_relations.pop(i)

                            st.session_state.master_relations.append({
                                "source": parent,
                                "target": child,
                                "relation": "包含",  # 内部保持中文
                                "evidence": merged_evidence,
                                "reason": act.get("reason"),
                                "doc_source": merged_doc_source
                            })

                        elif act["action"] == "REMOVE":
                            src = act.get("source")
                            tgt = act.get("target")
                            rel = act.get("relation")
                            for i in range(len(st.session_state.master_relations) - 1, -1, -1):
                                r = st.session_state.master_relations[i]
                                if r.get("source") == src and r.get("target") == tgt and r.get(
                                        "relation") == rel:
                                    st.session_state.master_relations.pop(i)

                        elif act["action"] == "DOWNGRADE":
                            for r in st.session_state.master_relations:
                                if r.get("source") == act.get("source") and r.get("target") == act.get(
                                        "target") and r.get("relation") == act.get("relation"):
                                    r["is_shortcut"] = True

                    # ====================================================
                    # 🧹 洗树后的终极清理
                    # ====================================================
                    cleaned_relations = []
                    master_rel_map = {}

                    for existing_rel in st.session_state.master_relations:
                        src = str(existing_rel.get("source", "")).strip()
                        tgt = str(existing_rel.get("target", "")).strip()
                        rel_type = str(existing_rel.get("relation", "")).strip()
                        key = (src, tgt, rel_type)

                        if key in master_rel_map:
                            merged_rel = master_rel_map[key]
                            merged_rel["weight"] = merged_rel.get("weight", 1) + existing_rel.get("weight", 1)
                            old_ev = merged_rel.get("evidence", "")
                            new_ev = existing_rel.get("evidence", "")
                            if new_ev and new_ev not in old_ev:
                                merged_rel["evidence"] = f"{old_ev}\n---\n{new_ev}"
                            old_src = merged_rel.get("doc_source", "")
                            new_src = existing_rel.get("doc_source", "")
                            if new_src and new_src not in old_src:
                                merged_rel["doc_source"] = f"{old_src} | {new_src}"
                            old_reason = merged_rel.get("reason", "")
                            new_reason = existing_rel.get("reason", "")
                            if new_reason and new_reason not in old_reason:
                                merged_rel["reason"] = f"{old_reason} | {new_reason}"
                        else:
                            existing_rel["source"] = src
                            existing_rel["target"] = tgt
                            existing_rel["relation"] = rel_type
                            master_rel_map[key] = existing_rel
                            cleaned_relations.append(existing_rel)

                    st.session_state.master_relations = cleaned_relations
                    st.session_state.ai_suggestions = []
                    st.toast(t("toast_pruning_exec_done"), icon="🎉")
                    redraw_and_update()
                    st.rerun()

        # ==========================================
        # ✂️ 新增模块：基于意图的智能节点剪枝
        # ==========================================
        st.markdown("---")
        st.subheader(t("intent_pruning_title"))
        st.info(t("intent_pruning_info"))

        user_interest = st.text_area(t("lbl_user_interest"), key="user_interest_prune")

        if st.button(t("btn_find_irrelevant"), type="primary", use_container_width=True):
            current_api_key = api_key.strip()
            if not current_api_key:
                st.error(t("err_missing_api_key"))
            elif not user_interest.strip():
                st.warning(t("warn_empty_interest"))
            else:
                with st.spinner(t("msg_finding_irrelevant")):
                    from LLM_SYS import BioBrainAgent

                    agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)
                    prune_suggestions = agent.prune_nodes_by_intent(
                        user_interest,
                        st.session_state.master_entities,
                        st.session_state.master_relations,
                        output_lang=st.session_state.get("ui_language", "zh")
                    )
                    st.session_state.node_prune_suggestions = prune_suggestions
                    st.toast(t("toast_find_irrelevant_done"), icon="🤖")
                    st.rerun()

        if "node_prune_suggestions" in st.session_state and st.session_state.node_prune_suggestions:
            st.markdown(t("purge_list_title"))
            st.caption(t("purge_list_caption"))

            # 💡 动态生成带翻译的列名，以确保 DataFrame 绑定的 key 正确
            col_del_txt = t("col_delete")
            col_name_txt = t("col_node_name")
            col_neigh_txt = t("col_neighbors")
            col_risk_txt = t("col_risk_level")
            col_reason_txt = t("col_ai_reason")

            df_prune_data = []
            for item in st.session_state.node_prune_suggestions:
                risk = item.get("risk_level", "")
                node_name = item.get("node_name", "")
                to_delete = True if risk in ["完全无关", "可能无关", "Completely_Irrelevant",
                                             "Potentially_Irrelevant"] else False

                neighbors = set()
                for r in st.session_state.master_relations:
                    if r.get("source") == node_name:
                        neighbors.add(r.get("target"))
                    elif r.get("target") == node_name:
                        neighbors.add(r.get("source"))

                df_prune_data.append({
                    col_del_txt: to_delete,
                    col_name_txt: node_name,
                    col_neigh_txt: ", ".join(list(neighbors))[:60] + (
                        "..." if len(", ".join(list(neighbors))) > 60 else ""),
                    col_risk_txt: risk,
                    col_reason_txt: item.get("reason", "")
                })

            df_prune = pd.DataFrame(df_prune_data)
            edited_prune_df = st.data_editor(
                df_prune,
                use_container_width=True,
                hide_index=True,
                disabled=[col_name_txt, col_neigh_txt, col_risk_txt, col_reason_txt],
                key="prune_data_editor"
            )

            col_prune_y, col_prune_n = st.columns(2)
            with col_prune_y:
                if st.button(t("btn_execute_purge"), type="primary", use_container_width=True):
                    nodes_to_delete = edited_prune_df[edited_prune_df[col_del_txt] == True][
                        col_name_txt].tolist()
                    if nodes_to_delete:
                        st.session_state.master_entities = [
                            e for e in st.session_state.master_entities if
                            e.get("standard_name") not in nodes_to_delete
                        ]
                        st.session_state.master_relations = [
                            r for r in st.session_state.master_relations
                            if r.get("source") not in nodes_to_delete and r.get("target") not in nodes_to_delete
                        ]
                        st.toast(t("toast_purge_success").format(count=len(nodes_to_delete)), icon="🎉")

                    st.session_state.node_prune_suggestions = None
                    redraw_and_update()
                    st.rerun()
            with col_prune_n:
                if st.button(t("btn_cancel_purge"), use_container_width=True):
                    st.session_state.node_prune_suggestions = None
                    st.rerun()

    # -----------------------------------------
    # 模块二：🔍 智能拓展 (Smart Expansion)
    # -----------------------------------------
    elif ai_nav == "ai_nav_expansion":
        current_db_name = "PubMed" if "PubMed" in st.session_state.get("search_database",
                                                                       "PubMed") else "Semantic Scholar"
        st.info(t("expansion_info").format(db=current_db_name))

        all_node_names = [e.get("standard_name") for e in st.session_state.master_entities]
        selected_nodes = st.multiselect(t("lbl_select_nodes_exp"), all_node_names)

        strategy_keys = ["strategy_direct", "strategy_smart", "strategy_bg"]
        search_mode_key = st.radio(
            t("lbl_search_strategy"),
            options=strategy_keys,
            format_func=lambda k: t(k),
            horizontal=False
        )
        max_results = st.slider(t("lbl_max_results"), min_value=5, max_value=20, value=10)

        if st.button(t("btn_web_search"), type="primary"):
            if not selected_nodes:
                st.warning(t("warn_select_nodes_first"))
            else:
                with st.spinner(t("msg_fetching_api").format(db=current_db_name)):
                    from WebSearcher import get_searcher

                    current_db = st.session_state.get("search_database", "PubMed (生物医学权威)")
                    searcher = get_searcher(current_db)
                    query = ""

                    if search_mode_key == "strategy_direct":
                        query_parts = [f'("{node}"[Title/Abstract])' for node in selected_nodes]
                        query = " AND ".join(query_parts)
                        st.session_state.last_generated_query = query
                    else:
                        current_api_key = api_key.strip()
                        if not current_api_key:
                            st.error(t("err_need_key_for_ai_search"))
                            st.stop()

                        from LLM_SYS import BioBrainAgent

                        agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)

                        selected_nodes_info = []
                        for e in st.session_state.master_entities:
                            if e.get("standard_name") in selected_nodes:
                                selected_nodes_info.append({
                                    "name": e.get("standard_name"),
                                    "aliases": e.get("aliases", [])
                                })

                        if search_mode_key == "strategy_smart":
                            query = agent.generate_pubmed_query(selected_nodes_info)
                        elif search_mode_key == "strategy_bg":
                            relevant_relations = [r for r in st.session_state.master_relations
                                                  if r.get("source") in selected_nodes or r.get(
                                    "target") in selected_nodes]
                            query = agent.generate_pubmed_query(selected_nodes_info,
                                                                context_relations=relevant_relations)

                        st.session_state.last_generated_query = query

                    results = searcher.search_articles(query, max_results=max_results)
                    st.session_state.pubmed_search_results = results
                    st.toast(t("toast_search_success").format(count=len(results)), icon="🎉")
                    st.rerun()

        if st.session_state.pubmed_search_results:
            st.markdown(t("search_results_title"))

            df = pd.DataFrame(st.session_state.pubmed_search_results)

            # 💡 动态表头绑定
            col_include_txt = t("col_include_graph")
            col_title_txt = t("col_paper_title")
            col_year_txt = t("col_year")

            if col_include_txt not in df.columns:
                # ⚠️ 注意这里底层用英文键兼容原来的逻辑，但是在显示的时候渲染成当地语言
                df.insert(0, col_include_txt, False)

            edited_df = st.data_editor(
                df,
                column_config={
                    col_include_txt: st.column_config.CheckboxColumn(col_include_txt, default=False),
                    "pmid": st.column_config.TextColumn("PMID", disabled=True),
                    "title": st.column_config.TextColumn(col_title_txt, disabled=True),
                    "year": st.column_config.TextColumn(col_year_txt, disabled=True),
                },
                disabled=["pmid", "title", "year", "authors", "doi"],
                hide_index=True,
                use_container_width=True,
                key="pubmed_data_editor"
            )

            st.markdown("---")
            if st.button(t("btn_add_to_queue"), type="primary", use_container_width=True):
                selected_docs = edited_df[edited_df[col_include_txt] == True]

                if selected_docs.empty:
                    st.warning(t("warn_check_one_paper"))
                else:
                    st.session_state.expansion_queue = selected_docs.to_dict('records')
                    st.session_state.expansion_idx = 0
                    st.toast(t("toast_added_to_queue"), icon="📥")
                    st.rerun()


            def bg_reset_expansion_task():
                st.session_state.expansion_queue = []
                st.session_state.expansion_idx = 0
                if "auto_run_expansion" in st.session_state:
                    st.session_state.auto_run_expansion = False


            if "expansion_queue" in st.session_state and st.session_state.expansion_queue:
                queue = st.session_state.expansion_queue
                idx = st.session_state.expansion_idx
                total = len(queue)

                st.markdown("---")
                st.markdown(t("queue_title").format(idx=idx, total=total))

                if idx < total:
                    current_doc = queue[idx]
                    pmid = current_doc['pmid']
                    title = current_doc['title']

                    st.info(t("queue_current_doc").format(title=title, pmid=pmid))

                    auto_run = st.toggle(t("toggle_auto_run"), value=False, key="auto_run_expansion")
                    if auto_run:
                        st.caption(t("warn_auto_running"))

                    col_run, col_skip, col_stop = st.columns(3)

                    btn_run = col_run.button(t("btn_run_this"), use_container_width=True, type="primary",
                                             disabled=auto_run)
                    btn_skip = col_skip.button(t("btn_skip_this"), use_container_width=True, disabled=auto_run)
                    btn_stop = col_stop.button(t("btn_stop_queue"), use_container_width=True, disabled=auto_run,
                                               on_click=bg_reset_expansion_task)

                    if btn_run or auto_run:
                        current_api_key = api_key.strip()
                        if not current_api_key:
                            st.error(t("err_missing_api_key"))
                            st.stop()

                        from WebSearcher import get_searcher

                        current_db = st.session_state.get("search_database", "PubMed (生物医学权威)")
                        searcher = get_searcher(current_db)
                        from LLM_SYS import BioBrainAgent

                        agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)

                        with st.spinner(t("msg_deep_parsing").format(pmid=pmid)):
                            abstract = searcher.fetch_abstract(pmid)
                            if len(abstract) < 50:
                                st.toast(t("toast_skip_short_abstract").format(pmid=pmid), icon="⏭️")
                            else:
                                new_entities = agent.extract_entities_with_reflection(abstract,
                                                                                      use_reflection=use_reflection,
                                                                                      entity_lang=entity_language)
                                for ent in new_entities:
                                    ent["doc_source"] = f"PubMed:{pmid}"

                                combined_entities_dict = st.session_state.master_entities + new_entities
                                new_relations = agent.extract_relations(abstract, combined_entities_dict)
                                for rel in new_relations:
                                    rel["doc_source"] = f"PubMed:{pmid}"
                                    rel["weight"] = 1

                                alignment_map = agent.align_global_entities(
                                    st.session_state.master_entities, new_entities)

                                aligned_new_entities = []
                                master_names = {ent["standard_name"]: ent for ent in
                                                st.session_state.master_entities}

                                for new_ent in new_entities:
                                    new_name = new_ent.get("standard_name")
                                    new_source = new_ent.get("doc_source", "")

                                    if new_name in master_names:
                                        master_ent = master_names[new_name]
                                        aliases = master_ent.setdefault("aliases", [])
                                        for new_alias in new_ent.get("aliases", []):
                                            if new_alias not in aliases and new_alias != new_name:
                                                aliases.append(new_alias)
                                        old_source = master_ent.get("doc_source", "")
                                        if new_source and new_source not in old_source:
                                            master_ent["doc_source"] = f"{old_source} | {new_source}"
                                    elif alignment_map and new_name in alignment_map:
                                        master_name = alignment_map[new_name]
                                        if master_name in master_names:
                                            master_ent = master_names[master_name]
                                            aliases = master_ent.setdefault("aliases", [])
                                            if new_name not in aliases:
                                                aliases.append(new_name)
                                            for new_alias in new_ent.get("aliases", []):
                                                if new_alias not in aliases and new_alias != master_name:
                                                    aliases.append(new_alias)
                                            old_source = master_ent.get("doc_source", "")
                                            if new_source and new_source not in old_source:
                                                master_ent["doc_source"] = f"{old_source} | {new_source}"
                                        else:
                                            aligned_new_entities.append(new_ent)
                                    else:
                                        aligned_new_entities.append(new_ent)

                                if alignment_map:
                                    for rel in new_relations:
                                        if rel.get("source") in alignment_map:
                                            rel["source"] = alignment_map[rel["source"]]
                                        if rel.get("target") in alignment_map:
                                            rel["target"] = alignment_map[rel["target"]]

                                master_rel_map = {}
                                for existing_rel in st.session_state.master_relations:
                                    src = str(existing_rel.get("source", "")).strip()
                                    tgt = str(existing_rel.get("target", "")).strip()
                                    rel_type = str(existing_rel.get("relation", "")).strip()
                                    key = (src, tgt, rel_type)
                                    master_rel_map[key] = existing_rel

                                for rel in new_relations:
                                    src = str(rel.get("source", "")).strip()
                                    tgt = str(rel.get("target", "")).strip()
                                    rel_type = str(rel.get("relation", "")).strip()
                                    key = (src, tgt, rel_type)

                                    if key in master_rel_map:
                                        existing_rel = master_rel_map[key]
                                        existing_rel["weight"] = existing_rel.get("weight", 1) + 1

                                        old_ev = existing_rel.get("evidence", "")
                                        new_ev = rel.get("evidence", "")
                                        if new_ev and new_ev not in old_ev:
                                            existing_rel["evidence"] = f"{old_ev}\n---\n{new_ev}"

                                        old_src = existing_rel.get("doc_source", "")
                                        new_src = rel.get("doc_source", "")
                                        if new_src and new_src not in old_src:
                                            existing_rel["doc_source"] = f"{old_src} | {new_src}"

                                        old_reason = existing_rel.get("reason", "")
                                        new_reason = rel.get("reason", "")
                                        if new_reason and new_reason not in old_reason:
                                            existing_rel["reason"] = f"{old_reason} | {new_reason}"
                                    else:
                                        rel["source"] = src
                                        rel["target"] = tgt
                                        rel["relation"] = rel_type
                                        rel["weight"] = 1
                                        st.session_state.master_relations.append(rel)
                                        master_rel_map[key] = rel

                                st.session_state.master_entities.extend(aligned_new_entities)
    # -----------------------------------------
    # 模块三：🔗 智能桥接 (Intelligent Bridging)
    # -----------------------------------------
    elif ai_nav == "ai_nav_bridging":
        st.info(t("bridge_info"))
        all_node_names = [e.get("standard_name") for e in st.session_state.master_entities]

        col_a, col_b = st.columns(2)
        node_opts = ["__SELECT__"] + all_node_names
        with col_a:
            node_a = st.selectbox(t("lbl_bridge_node_a"), options=node_opts,
                                  format_func=lambda x: t("opt_select") if x == "__SELECT__" else x,
                                  key="bridge_node_a")
        with col_b:
            node_b = st.selectbox(t("lbl_bridge_node_b"), options=node_opts,
                                  format_func=lambda x: t("opt_select") if x == "__SELECT__" else x,
                                  key="bridge_node_b")

        max_depth = st.slider(t("lbl_max_depth"), min_value=2, max_value=5, value=4)

        if st.button(t("btn_start_bridge"), type="primary", use_container_width=True):
            if node_a == node_b and node_a != "__SELECT__":
                st.warning(t("warn_same_nodes_bridge"))
            elif node_a == "__SELECT__" or node_b == "__SELECT__":
                st.warning(t("warn_select_nodes_bridge"))
            else:
                from back_logic import GraphMiner

                with st.spinner(t("msg_scanning_paths")):
                    paths = GraphMiner.find_paths(st.session_state.master_relations, node_a, node_b,
                                                  max_depth)
                    st.session_state.bridge_paths = paths
                    st.session_state.bridge_nodes = (node_a, node_b)
                    st.session_state.bridge_report = None
                    st.rerun()

        # --- 状态机：展示桥接结果与三挡分流 ---
        if "bridge_paths" in st.session_state and st.session_state.get("bridge_nodes") == (node_a, node_b):
            paths = st.session_state.bridge_paths

            # 🌿 分流三：毫无联系（孤岛）
            if len(paths) == 0:
                st.warning(t("msg_island").format(depth=max_depth, a=node_a, b=node_b))
                needs_network_search = True
                search_prompt_msg = t("prompt_island_search").format(a=node_a, b=node_b)

            else:
                max_path_len = max(len(p) for p in paths)

                # 🌿 分流二：只有直接联系
                if max_path_len == 1:
                    st.info(t("msg_direct_only").format(a=node_a, b=node_b))
                    needs_network_search = True
                    search_prompt_msg = t("prompt_direct_search").format(a=node_a, b=node_b)

                # 🌿 分流一：存在多步复杂机制
                else:
                    st.success(t("msg_complex_paths").format(count=len(paths)))
                    needs_network_search = False

                    if st.session_state.bridge_report is None:
                        current_api_key = api_key.strip()
                        if not current_api_key:
                            st.error(t("err_need_key_for_summary"))
                        else:
                            with st.spinner(t("msg_writing_report")):
                                from LLM_SYS import BioBrainAgent

                                agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)
                                report = agent.explain_mechanism(node_a, node_b, paths,output_lang=st.session_state.get("ui_language", "zh"))
                                st.session_state.bridge_report = report
                                st.rerun()

                if st.session_state.bridge_report:
                    st.markdown(t("report_title"))
                    st.markdown(t("report_subtitle").format(a=node_a, b=node_b, count=len(paths)))
                    st.markdown(st.session_state.bridge_report)

            # --- 动态联网检索模块 (针对分流二和三) ---
            if needs_network_search:
                if st.button(f"🌐 {search_prompt_msg}", type="primary", key="btn_bridge_search"):
                    current_api_key = api_key.strip()
                    if not current_api_key:
                        st.error(t("err_missing_api_key"))
                    else:
                        with st.spinner(t("msg_evaluating_strategy")):
                            from LLM_SYS import BioBrainAgent
                            from WebSearcher import get_searcher

                            agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)
                            query = agent.generate_bridge_query(node_a, node_b)

                            if "[NO_RELATION_ERROR]" in query:
                                st.error(t("err_ai_rejected").format(a=node_a, b=node_b))
                            else:
                                st.info(t("msg_search_strategy").format(query=query))
                                current_db = st.session_state.get("search_database", "PubMed (生物医学权威)")
                                searcher = get_searcher(current_db)
                                results = searcher.search_articles(query, max_results=6)

                                if not results:
                                    st.warning(t("warn_no_mechanism_papers"))
                                else:
                                    st.session_state.bridge_found_docs = results
                                    st.session_state.pending_bridge_data = None
                                    st.rerun()

        # --- 核心改进：专属文献筛选表格 (让用户过滤噪音) ---
        if "bridge_found_docs" in st.session_state and st.session_state.bridge_found_docs:
            st.markdown("---")
            st.markdown(t("search_res_title_bridge").format(a=node_a, b=node_b))
            st.caption(t("search_res_caption_bridge"))

            b_df = pd.DataFrame(st.session_state.bridge_found_docs)
            col_sel_txt = t("col_deep_read")
            col_title_txt = t("col_paper_title")
            col_date_txt = t("col_pub_date")

            if col_sel_txt not in b_df.columns:
                b_df.insert(0, col_sel_txt, True)

            edited_b_df = st.data_editor(
                b_df,
                column_config={
                    col_sel_txt: st.column_config.CheckboxColumn(col_sel_txt, default=True),
                    "pmid": "PMID",
                    "title": col_title_txt,
                    "pub_date": col_date_txt
                },
                disabled=["pmid", "title", "pub_date"],
                hide_index=True,
                key="bridge_docs_editor",
                use_container_width=True
            )

            if st.button(t("btn_start_sniper_extract"), type="primary", use_container_width=True):
                selected_b_docs = edited_b_df[edited_b_df[col_sel_txt] == True]
                if selected_b_docs.empty:
                    st.warning(t("warn_check_one_paper_bridge"))
                else:
                    with st.spinner(t("msg_sniper_extracting")):
                        from WebSearcher import get_searcher
                        from LLM_SYS import BioBrainAgent

                        current_db = st.session_state.get("search_database", "PubMed (生物医学权威)")
                        searcher = get_searcher(current_db)
                        agent = BioBrainAgent(api_key=api_key.strip(),model=selected_model_id,base_url=base_url)

                        combined_abstracts = ""
                        for _, row in selected_b_docs.iterrows():
                            pmid = row['pmid']
                            abs_text = searcher.fetch_abstract(pmid)
                            if len(abs_text) > 50:
                                combined_abstracts += "\n\n" + t("fmt_paper_title").format(pmid=pmid,
                                                                                           title=row[
                                                                                               'title']) + "\n" + abs_text

                        bridge_result = agent.extract_bridge_mechanism(
                            node_a, node_b, combined_abstracts, entity_lang=entity_language
                        )
                        st.session_state.pending_bridge_data = bridge_result
                        st.session_state.bridge_found_docs = None
                        st.rerun()

        # --- 最终阶段：桥接结果展示与图谱融合审批区 ---
        if "pending_bridge_data" in st.session_state and st.session_state.pending_bridge_data:
            bridge_data = st.session_state.pending_bridge_data
            st.markdown("---")
            st.markdown(t("ai_bridge_report_title"))
            st.info(bridge_data.get("explanation", t("no_text_explanation")))

            new_rels = bridge_data.get("relations", [])
            new_ents = bridge_data.get("entities", [])

            if not new_rels:
                st.warning(t("warn_no_clear_chain"))
                if st.button(t("btn_clear_report")):
                    st.session_state.pending_bridge_data = None
                    st.rerun()
            else:
                st.success(t("msg_extracted_links").format(count=len(new_rels)))
                st.json(new_rels)

                col_acc, col_rej = st.columns(2)
                if col_acc.button(t("btn_accept_merge"), type="primary", use_container_width=True):
                    with st.spinner(t("msg_bulletproof_merging")):
                        from LLM_SYS import BioBrainAgent

                        agent = BioBrainAgent(api_key=api_key.strip(),model=selected_model_id,base_url=base_url)

                        alignment_map = agent.align_global_entities(st.session_state.master_entities,
                                                                    new_ents)

                        for new_ent in new_ents:
                            if new_ent["standard_name"] not in [e["standard_name"] for e in
                                                                st.session_state.master_entities]:
                                st.session_state.master_entities.append(new_ent)

                        if alignment_map:
                            for rel in new_rels:
                                if rel.get("source") in alignment_map: rel["source"] = alignment_map[
                                    rel["source"]]
                                if rel.get("target") in alignment_map: rel["target"] = alignment_map[
                                    rel["target"]]

                        master_rel_map = {}
                        for existing_rel in st.session_state.master_relations:
                            key = (str(existing_rel.get("source")).strip(),
                                   str(existing_rel.get("target")).strip(),
                                   str(existing_rel.get("relation")).strip())
                            master_rel_map[key] = existing_rel

                        for rel in new_rels:
                            key = (str(rel.get("source")).strip(), str(rel.get("target")).strip(),
                                   str(rel.get("relation")).strip())
                            if key in master_rel_map:
                                existing_rel = master_rel_map[key]
                                existing_rel["weight"] = existing_rel.get("weight", 1) + 1
                                if rel.get("evidence") and rel.get("evidence") not in existing_rel.get(
                                        "evidence", ""):
                                    existing_rel[
                                        "evidence"] = f"{existing_rel.get('evidence', '')}\n---\n{rel.get('evidence')}"
                            else:
                                rel["weight"] = 1
                                st.session_state.master_relations.append(rel)

                        for existing_rel in st.session_state.master_relations:
                            src = existing_rel.get("source", "").strip()
                            tgt = existing_rel.get("target", "").strip()
                            if (src == node_a and tgt == node_b) or (src == node_b and tgt == node_a):
                                if not existing_rel.get("is_shortcut", False):
                                    existing_rel["is_shortcut"] = True
                                    old_reason = existing_rel.get("reason", "")
                                    existing_rel["reason"] = t("fmt_downgrade_reason").format(
                                        old=old_reason)

                    st.session_state.pending_bridge_data = None
                    st.toast(t("toast_bridge_merged"), icon="🎉")
                    redraw_and_update()
                    st.rerun()

                if col_rej.button(t("btn_reject_clear"), use_container_width=True):
                    st.session_state.pending_bridge_data = None
                    st.rerun()

    # -----------------------------------------
    # 模块四：🤖 问 AI (Ask AI)
    # -----------------------------------------
    elif ai_nav == "ai_nav_ask":
        st.info(t("ask_ai_info"))

        ask_mode_keys = ["explain_node", "explain_edge"]
        explain_mode = st.radio(
            t("lbl_what_to_explain"),
            options=ask_mode_keys,
            format_func=lambda k: t(k),
            horizontal=True
        )

        if explain_mode == "explain_node":
            if not st.session_state.master_entities:
                st.warning(t("warn_no_nodes_in_graph"))
            else:
                node_list = sorted([e.get("standard_name") for e in st.session_state.master_entities])
                node_opts = ["__SELECT__"] + node_list
                target_node = st.selectbox(t("lbl_select_node_to_explain"), node_opts,
                                           format_func=lambda x: t(
                                               "opt_select") if x == "__SELECT__" else x,
                                           key="ask_ai_target_node")

                if target_node != "__SELECT__":
                    if st.button(t("btn_explain_node"), type="primary"):
                        current_api_key = api_key.strip()
                        if not current_api_key:
                            st.error(t("err_missing_api_key"))
                        else:
                            with st.spinner(t("msg_extracting_context").format(node=target_node)):
                                context_lines = []


                                # 为了兼容内部保存逻辑，获取关系的中文并翻译
                                def get_safe_rel_display(val):
                                    if val == "正作用": return t("rel_positive")
                                    if val == "负作用": return t("rel_negative")
                                    if val == "相关": return t("rel_correlation")
                                    return val


                                for r in st.session_state.master_relations:
                                    rel_type = r.get('relation_type', r.get('relation', '关联'))
                                    disp_rel = get_safe_rel_display(rel_type)
                                    safe_reason = str(r.get('reason', '无')).replace('{', '(').replace('}',
                                                                                                      ')')
                                    raw_doc = r.get('doc_source', '未知')
                                    safe_doc = re.sub(r'[^\w\u4e00-\u9fa5.-]', '_', str(raw_doc))[:60]

                                    if r.get("source") == target_node:
                                        context_lines.append(
                                            f"<edge>起点:[{target_node}] -> 终点:[{r.get('target')}] | 关系:[{disp_rel}] | 提取依据:[{safe_reason}] | 来源:[{safe_doc}]</edge>")
                                    elif r.get("target") == target_node:
                                        context_lines.append(
                                            f"<edge>起点:[{r.get('source')}] -> 终点:[{target_node}] | 关系:[{disp_rel}] | 提取依据:[{safe_reason}] | 来源:[{safe_doc}]</edge>")

                                local_ctx = "\n".join(context_lines) if context_lines else t(
                                    "msg_no_connections")

                                from LLM_SYS import BioBrainAgent

                                agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)
                                explanation = agent.explain_graph_element("节点", target_node, local_ctx,output_lang=st.session_state.get("ui_language", "zh"))

                                st.markdown(t("report_node_title"))
                                st.markdown(explanation)

        else:
            if not st.session_state.master_entities:
                st.info(t("err_empty_graph"))
            else:
                all_node_names = sorted([e.get("standard_name") for e in st.session_state.master_entities])
                st.markdown(t("lbl_select_two_nodes"))

                col_a, col_b = st.columns(2)
                node_opts = ["__SELECT__"] + all_node_names
                with col_a:
                    node_a = st.selectbox(t("lbl_select_node_a"), node_opts,
                                          format_func=lambda x: t("opt_select") if x == "__SELECT__" else x,
                                          key="ask_ai_edge_node_a")
                with col_b:
                    node_b = st.selectbox(t("lbl_select_node_b"), node_opts,
                                          format_func=lambda x: t("opt_select") if x == "__SELECT__" else x,
                                          key="ask_ai_edge_node_b")

                if node_a != "__SELECT__" and node_b != "__SELECT__":
                    if node_a == node_b:
                        st.warning(t("warn_same_node_ask"))
                    else:
                        matching_rels = []
                        for i, r in enumerate(st.session_state.master_relations):
                            src = r.get("source")
                            tgt = r.get("target")
                            if (src == node_a and tgt == node_b) or (src == node_b and tgt == node_a):
                                matching_rels.append((i, r))

                        if not matching_rels:
                            st.info(t("info_no_rel_between").format(a=node_a, b=node_b))
                        else:
                            def get_safe_rel_display(val):
                                if val == "正作用": return t("rel_positive")
                                if val == "负作用": return t("rel_negative")
                                if val == "相关": return t("rel_correlation")
                                return val


                            rel_options = {}
                            for idx, r in matching_rels:
                                rel_type = r.get('relation_type', r.get('relation', '关联'))
                                disp_rel = get_safe_rel_display(rel_type)
                                label = f"[{idx}] {r.get('source')} --[{disp_rel}]--> {r.get('target')}"
                                rel_options[label] = r

                            target_rel_label = st.selectbox(t("lbl_select_rel_to_explain"),
                                                            list(rel_options.keys()),
                                                            key="ask_ai_target_rel_line")

                            if st.button(t("btn_explain_edge"), type="primary"):
                                current_api_key = api_key.strip()
                                if not current_api_key:
                                    st.error(t("err_missing_api_key"))
                                else:
                                    target_rel = rel_options[target_rel_label]
                                    with st.spinner(t("msg_analyzing_edge")):
                                        rel_type = target_rel.get('relation_type',
                                                                  target_rel.get('relation', '关联'))
                                        disp_rel = get_safe_rel_display(rel_type)
                                        safe_reason = str(target_rel.get('reason', '无')).replace('{',
                                                                                                 '(').replace(
                                            '}', ')')
                                        raw_doc = target_rel.get('doc_source', '未知')
                                        safe_doc = re.sub(r'[^\w\u4e00-\u9fa5.-]', '_', str(raw_doc))[:60]

                                        local_ctx = f"<edge_data>\n起点: {target_rel.get('source')}\n终点: {target_rel.get('target')}\n关系类型: {disp_rel}\n文献提取依据: {safe_reason}\n文献来源: {safe_doc}\n</edge_data>"

                                        from LLM_SYS import BioBrainAgent

                                        agent = BioBrainAgent(api_key=current_api_key,model=selected_model_id,base_url=base_url)
                                        explanation = agent.explain_graph_element("关系连线", target_rel_label,
                                                                                  local_ctx,output_lang=st.session_state.get("ui_language", "zh"))

                                        st.markdown(t("report_edge_title"))
                                        st.markdown(explanation)
