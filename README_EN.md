<p align="right">
   <strong>English</strong> &nbsp;｜&nbsp; <a href="README.md">中文</a>
</p>

<div align="center">

# 🧬 Bio-Graph Agent

**Bio-Graph Agent: A Cross-Literature Incremental Biological Knowledge Graph Engine Powered by Tencent Hunyuan Hy3**

[![Tencent Hunyuan](https://img.shields.io/badge/Powered_by-Tencent_Hunyuan-blue.svg)](https://hunyuan.tencent.com/)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-green.svg)](https://www.python.org/)

</div>


This project was developed in response to the long-text structural extraction and knowledge grounding requirements outlined in [Tencent-Hunyuan/Hy3/issues/4](https://github.com/Tencent-Hunyuan/Hy3/issues/4). Leveraging the powerful long-text context understanding and rigorous reasoning capabilities of **Tencent Hunyuan Hy3**, we have built a **Bio-Knowledge Graph LLM Agent**. This system automatically extracts information from literature (PDFs), performs dual-layer reflective quality checks, aligns semantics across multiple documents, and ultimately generates highly interactive dynamic network topology graphs.

---

## 🎯 Project Motivation & Scientific Value (Why this project?)

A classic pain point in biomedical research is: **How do we find highly valuable novel research topics in a vast sea of literature?**

In biology, it is common that "Molecule A regulates Protein B" and "Protein B regulates Biological Phenotype/Physiological System C" are isolated findings scattered across papers from different years and journals. However, **proving the regulatory cascade pathway "A mediates and affects C through the key node B" is often a highly scientifically valuable topic that can directly support a major research project or grant application.**

Relying on manual reading to piece together these cross-literature cascade relationships is extremely inefficient and prone to omissions.

**Bio-Graph Agent** was born precisely to overcome this pain point. It serves as an "intelligent topic selection strategist" for researchers:
1. **Multi-Literature Input**: Automatically and efficiently parses long, complex academic papers.
2. **Bridging Knowledge Islands**: Through AI semantic alignment, it connects and networks entities (molecules, proteins, physiological systems, etc.) and their potential relationships across different papers.
3. **Intuitive Topological Rendering**: Automatically renders dynamic topological networks strictly adhering to professional biological regulatory logic, helping researchers spot potential `A ➔ B ➔ C` core regulatory pathways at a glance.

---

## 🎨 Topological Network Visual Specification

This system strictly follows professional visual rendering specifications for biological regulatory network graphs to help researchers quickly capture the essence of signaling pathways:
* **🟢 Green Line**: Represents **Positive Effect / Activation / Promotion**.
* **🔴 Red Line**: Represents **Negative Effect / Inhibition / Suppression**, clear at a glance during topological interaction.
* **⚪ Grey Line (Solid)**: Represents **General Association / Correlation (Interaction exists but direction is unspecified)**.
* **🟣 Purple Line (Solid)**: Represents **Subordinate Containment / Component / Attribution Relationship**.
* **⚠️ Grey Dashed Line (Shortcut Edge)**: When AI detects cross-level skip relationships (e.g., A->B->C is known, and A->C is found), it automatically downgrades the coarse A->C to a grey dashed shortcut edge, highlighting the main logical trunk.
* **🔮 Node Dynamic Popularity (Degree)**: Node sizes automatically scale up based on their "connectivity (popularity)" in the cross-literature network. Hovering over a node reveals all its cross-literature aliases, evidence supporting the relationships, and precise literature source tracing.

---

## 🌟 Core Features & Operational Guide

1. **Flexible Environment & Model Settings (Sidebar)**
   * **🌐 Flexible LLM Engine**: Supports cloud APIs like Tencent Cloud, OpenRouter, SiliconFlow, and natively supports Ollama for local offline execution, protecting highly sensitive medical data.
   * **📚 Intelligent Search Sources**: Built-in dual engines: PubMed (Absolute authority in medicine) and Semantic Scholar (Comprehensive AI intelligent ultra-fast search).

2. **Knowledge Graph Construction (Dual Mode Start)**
   * **💡 Zero-Basis Cold Start**: No local literature needed. Simply input your research direction in natural language (e.g., "The role of macrophage polarization in the tumor microenvironment"), and the AI will automatically generate search queries, scrape external literature, and directly build the first graph.
   * **📄 Precise Local Literature Parsing**: Drag and drop a single PDF, supporting specific page parsing and an ultra-fast abstract mode. Enabling "🔗 Append Mode" ensures newly parsed literature won't overwrite the existing graph, but rather seamlessly integrate and grow with it indefinitely.

3. **Visual Empowerment Engine & Professional Topology Standards**
   * After graph generation, the system utilizes hardcore visual algorithms to pinpoint research targets amidst the complexity.
   * **🔮 Node Radiance & Main Trunk Thickening**: Based on graph theory connectivity algorithms, nodes of core hub genes automatically enlarge; consensus edges repeatedly verified by multiple papers automatically thicken.

4. **AI Intelligent Research Assistant**
   * The 🤖 Ask AI panel on the right integrates four automated weapons:
   * **🧹 Intelligent Pruning (Tree Washing)**: Automatically discovers and suggests merging synonyms, and establishing macro/micro containment hierarchies. Also supports intent-based node pruning (input research direction to wipe out off-topic organs or irrelevant molecules with one click).
   * **🔍 Smart Expansion**: Select isolated nodes at the graph's edge, and AI automatically generates PubMed queries to scrape cutting-edge literature, enabling "unattended mode" to align and fuse them automatically into the current graph.
   * **🔗 Intelligent Bridging**: Select any two seemingly unrelated nodes, call the algorithm with one click to find hidden conduction pathways between them, providing ultimate inspiration for writing grant proposals.
   * **📖 In-depth Mechanism Interpretation**: Click any node or edge, and AI generates an in-depth biological deduction report combined with original text context.

5. **Expert Manual Intervention (Data Management Center)**
   * Possess "God-mode" privileges over the graph:
   * **One-Click Clear**: Clean up isolated stray nodes or batch-replace literature source tags.
   * **Node Surgery**: Rename, forcefully merge (renaming to an existing node triggers perfect edge transfer), or even forcefully split a generic node into two and reassign edges individually.
   * **Edge Pruning**: Reverse upstream/downstream directions, modify association attributes, or manually establish hidden association bridges.

6. **Project Memory & Localization Management (.biokg)**
   * **Safety Lock Mechanism**: Strict double-confirmation safeguards against accidental canvas clearing.
   * **One-Click Export/Load**: Supports exporting the entire massive network, complete with historical evidence and modification logs, into a proprietary `.biokg` save file. Also supports seamless drag-and-drop loading at any time, facilitating research transfer and long-term accumulation.

7. **Fine-Grained Micro-Context Mechanism Explanation**
   * Breaks the pain point of traditional graphs: "Can only see the line, don't know why they connect."
   * **Deep Interaction**: Click on any node or edge, and the system instantly extracts the extraction basis and original literature source (micro-context) for that part, calling the LLM to deduce and generate an extremely detailed biological mechanism interpretation report on the spot, yielding proposal-grade materials directly.

8. **Industrial-Grade State Machine Management & i18n Foundation**
   * **Exclusive Resarch Asset Accumulation)**: Supports one-click exporting of the massive dynamic network carrying huge evidence chains and expert modification logs into a privatized `.biokg` save file. Supports breakpoint loading and seamless rendering anytime.
   * **Dynamic Internationalization Architecture**: Underying framework utilizes a standard i18n dynamic bilingual injection, combined with rigorous Streamlit state machine flow logic, achieving seamless hot-switching between Chinese and English for both the full interface and LLM output results.

---

## 🤖 The Core Role of Tencent Hunyuan Hy3 in the System

This system does not simply use the LLM as a "text summarizer," but rather **deeply exploits the performance dividends of the Tencent Hunyuan Hy3 open-source model**. Combining Hy3's outstanding long-context processing capabilities, rigorous logical reasoning precision, and native Agent tool-calling ecosystem, we have built six core agents covering the entire lifecycle of graph construction: **Pre-parsing - During Fusion - Post-generation**:

```text
┌──────────────────────────────────────────────────────────────────────┐
│                  🧠 Core LLM Agent Architecture                      │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
【Phase 1: Fast Parsing & Netting】 【Phase 2: Alignment & Pruning】 【Phase 3: Expansion & Insights】
  1. Long-Context Hub               3. Cross-Literature Judge        5. Expansion & Bridging Guide
  2. Dual-Layer Quality Inspector   4. Topology Cleaner              6. Micro-Mechanism Explainer
```

### 1. Long-Context Understanding Hub
* **Challenge**: Academic papers in the biomedical field are often dozens of pages long, containing massive professional terminology, chart narratives, and complex sentence structures, demanding extremely high long-text throughput and context recall (Needle in a Haystack) from the model.
* **Hunyuan's Role**: The system utilizes Hunyuan Hy3's massive context window, allowing the LLM to act as a "scientific speed-reading expert." Without losing context, it efficiently and losslessly extracts standard biological entities (genes/proteins/phenotypes) and precise regulatory mechanisms from the entire PDF paper.

### 2. Dual-Layer Reflection Inspector
* **Challenge**: Traditional single-pass LLM extraction is prone to academic hallucinations, falsely reporting or fabricating non-existent biological relationships, which is fatal in rigorous scientific research.
* **Hunyuan's Role**: The system constructed a **"Preliminary Extraction - Reflective Confrontation"** dual-stage Agent based on Hunyuan Hy3. Hy3 plays two roles here:
  - **Role A (Extractor)**: Extracts preliminary entities and edges based on the main text.
  - **Role B (Auditor)**: Uses Hunyuan's extremely strong rigorous logic to re-examine the original text against the preliminary results, performing "original text confrontation." Only relationships with solid evidence in the original text are retained, utilizing Hunyuan's reflection capability to reduce the hallucination rate to an absolute minimum.

### 3. Cross-Literature Semantic Alignment Judge
* **Challenge**: After parsing multiple papers independently, synonyms (e.g., `p53` / `TP53` / `Tumor Protein 53`) cause graph fragmentation, forming massive knowledge islands.
* **Hunyuan's Role**: In append mode, Hunyuan Hy3 takes on the heavy responsibility of **"Global Knowledge Fusion Judge."** It breaks through literal meanings to deeply understand the semantic layer of biological concepts. By cross-referencing ontology names and aliases lists extracted from different papers, Hunyuan accurately executes semantic-level fusion, weaving fragmented cross-literature edges perfectly into a single, massive signaling regulatory network.

### 4. Topology Cleaner (Intelligent Pruning)
* **Challenge**: Post-generation networks often have complex topological redundancies, such as chaotic macro/micro containment relationships and broad conclusions spanning multiple levels (shortcut edges). Manually sorting out this cobweb-like structure is highly challenging. Furthermore, literature often extracts off-topic molecules or organs that the researcher doesn't care about.
* **Hunyuan's Role**: Relying on Hunyuan Hy3's strong macro structural analysis and logical deduction capabilities, it reads through the global topological logic to automatically diagnose and suggest "downgrading mechanism shortcut edges" and establishing hierarchical containment relationships. It also supports "intent pruning" based on natural language, accurately understanding the user's research direction to instantly single out and wipe out all off-topic marginal branches.

### 5. Web-Browsing Explorer (Expansion & Bridging Guide)
* **Challenge**: Local literature databases always have boundaries. When isolated nodes appear in the graph, or when exploring potential conduction pathways between two seemingly unrelated molecules is needed, traditional methods require massive manual time spent on external databases for re-searching and reading.
* **Hunyuan's Role**: Fully activates Hunyuan Hy3's native Tool Calling and planning capabilities. Selecting isolated nodes allows Hy3 to autonomously generate advanced search queries and call external APIs (like PubMed / Semantic Scholar) to scrape cutting-edge literature. In "unattended mode," it automatically parses new literature and seamlessly fuses knowledge back into the current graph; for any two unrelated nodes, it can actively seek hidden conduction bridges, achieving graph expansion beyond boundaries.

### 6. Micro-Mechanism Explainer
* **Challenge**: Highly abstract graph edges (e.g., A ➔ B) often mask the complex and delicate biochemical reaction processes in the original text. When reviewing the macro graph, researchers struggle to instantly recall the detailed mechanism and experimental origin behind a specific edge.
* **Hunyuan's Role**: Leveraging Hunyuan Hy3's strong Chinese/English long-text generation, polishing, and context understanding capabilities, the system allows users to click on any edge in the graph. Hy3 extracts the edge's specific micro-context and original text evidence on the spot to generate a logically rigorous and extremely detailed biological mechanism deduction report, providing direct material for grant writing.

---

## 🌟 Core Technical Highlights

1. **Long-Text Level Entity and Relationship Structured Extraction**: Perfectly adapts to Hunyuan Hy3's ultra-long context window, capable of directly parsing complex biochemical/medical PDF literature of dozens of pages. It extracts high-quality structured JSON data including `Standard Name`, `Aliases`, `Relationship Type`, and `Original Text Evidence`.
2. **Pioneering Dual-Layer Agent Reflection Mechanism**: The first-layer Agent captures the coarse-grained network, while the second-layer Agent acts as an "independent quality inspector," matching preliminary results against the original text one by one, eliminating all hallucinated entities without evidence, significantly improving the graph's rigor.
3. **Intelligent Cross-Literature Entity Aligner (Fusion Hub)**: When **Append Mode** is active, the knowledge threads of multiple papers are dynamically networked. Calls the Hunyuan LLM as a judge and cross-references the aliases list inherent to entities to achieve high-precision semantic alignment. For example: automatically identifies and merges `p53` from paper A and `Tumor protein 53` / `TP53` from paper B into the same global super-node, perfectly splicing their literature source tags (e.g., `PaperA.pdf | PaperB.pdf`).
4. **Dynamic Topological Rendering Independent of External Networks**: Built on Pyvis and extremely optimized for Streamlit embedded web rendering. Node size dynamically scales with "popularity (degree centrality)"; hover to view all cross-literature aliases, relationship evidence, and literature sources.
5. **Intelligent Pruning & Intent Cleansing Based on LLM Deduction**: 
   - *Topological Intelligent Pruning*: AI automatically reads the full-graph logic, identifying and suggesting merging omitted synonyms, establishing macro-containment hierarchies, and intelligently downgrading cross-level "broad conclusions" to grey dashed lines (mechanism shortcut edges) to highlight the main trunk.
   - *Natural Language Intent Cleansing*: Supports plain text input of research focus (e.g., "I only care about lung cancer mechanisms"). The LLM becomes a strict reviewer, automatically picking out off-topic organs or side-branch molecules for one-click physical deletion, ensuring extreme graph purity.
6. **Automated Expansion & Bridging Breaking Local Boundaries**: 
   - *Unattended Expansion*: Select isolated nodes, and the system automatically generates professional search queries based on graph context, calls external APIs (e.g., PubMed) to scrape cutting-edge literature into a queue, and automatically completes the perfect fusion of new knowledge with the current graph.
   - *Cross-Node Intelligent Bridging*: Specify any two completely unrelated nodes. Relying on graph theory algorithms and LLM external web mining, the system forcefully explores multi-step cascade conduction pathways between them, directly inspiring novel research topics.
7. **Fine-Grained Micro-Context Mechanism Explanation**: Breaks the pain point of traditional graphs: "Can only see the line, don't know why they connect." Deep Interaction: Click on any node or edge, and the system instantly extracts the extraction basis and original literature source (micro-context) for that part, calling the LLM to deduce and generate an extremely detailed biological mechanism interpretation report on the spot, yielding proposal-grade materials directly.
8. **Industrial-Grade State Machine Management & i18n Foundation**: 
   - *Proprietary Research Asset Accumulation*: Supports one-click exporting of the massive dynamic network carrying huge evidence chains and expert modification logs into a privatized `.biokg` save file. Supports breakpoint loading and seamless rendering anytime.
   - *Dynamic Internationalization Architecture*: Underlying framework utilizes a standard i18n dynamic bilingual injection, combined with rigorous Streamlit state machine flow logic, achieving seamless hot-switching between Chinese and English for both the full interface and LLM output results.

---

## 📂 Core Code Architecture

```text
├── app.py           # Streamlit Frontend Interaction Dashboard (Includes cross-literature entity fusion surgery logic)
├── back_logic.py     # System Main Dispatch Pipeline (BioGraphPipeline Incremental Accumulation Hub)
├── LLM_SYS.py       # LLM Agent (Includes Preliminary, Reflection, and Cross-Literature Alias-Enhanced Alignment Agents)
├── IO_SYS.py        # Infrastructure Layer (Includes PyMuPDF smart chunking and secure graph topology renderer)
├── WebSearcher.py   # Web Literature Search Functionality
├── requirements.txt # Project Dependencies
└── .gitignore       # Git Commit Ignore Configuration
```

---

## 🚀 Quick Start

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/24238-T-34/-Bio-Graph-Agent-Hy3-
cd -Bio-Graph-Agent-Hy3-
pip install -r requirements.txt
```

### 2. Configure and Run Project

**Method 1 (Linux/WSL)**
```bash
chmod +x run.sh
./run.sh
```

**Method 2 (Windows)**
Click the batch file `start.bat` (Project paths might need manual adjustment if incorrect).

**Method 3 (Direct Command)**
```bash
streamlit run app.py
```

After running, open the Streamlit interface in your browser. Enter your OpenRouter / Tencent Hunyuan API Key in the sidebar, and you can start uploading PDF literature to witness the automatic construction of dynamic biological macro-graphs!

---

## 📅 Future Work

* [x] **Secondary Correlation Filter & Intelligent Pruning**: Introduced a "regulatory pathway correlation secondary quality check" powered by LLMs, supporting intent-based pruning and one-click destruction of global isolated nodes. (✅ **Completed and merged into main branch in v1.0**)
* [ ] **Multi-Attribute Topological Coloring**: Plan to automatically assign richer categorical colors based on node attributes (e.g., Genes, Diseases, Compounds, Phenotypes), making the macro-network more biologically intuitive at a glance.
* [ ] **Concurrency & Asynchronous Processing**: Break the current performance bottleneck of single-threaded serial processing for long texts. We plan to introduce `asyncio` or thread pool mechanisms to enable high-concurrency API requests for PDF chunking and multi-literature matrices, expecting to boost parsing and graph-building speed by 5 to 10 times.
* [ ] **Intelligent LLM Routing Engine (MoE)**: Build a synergistic architecture of small and large models. Delegate basic text cleaning and entity extraction to ultra-fast lightweight models, while routing complex tasks like multi-document semantic alignment, micro-context mechanism explanation, and smart bridging to deep reasoning models like Tencent Hunyuan Hy3, achieving the optimal balance between response speed and computational cost.
* [ ] **Hypothesis & Writing Dual-Mode Workspace (Copilot)**: Evolve towards an "AI-driven Scientific Discovery Engine" by planning a Multi-page App architecture and introducing an independent AIGC writing cabin.
  - **Autonomous Exploration**: Without manual specification, the system will autonomously identify "Structural Holes" and "Dangling Nodes" in the graph, triggering web search engines for scientific blind-box exploration.
  - **Research Proposal Generation**: Based on high-potential cascade pathways mined from the graph, support one-click generation of research proposals or background drafts, complete with rigorous literature citations and rationales.