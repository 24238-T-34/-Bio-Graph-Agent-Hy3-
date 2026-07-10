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


# ==========================================
# 页面全局配置
# ==========================================
st.set_page_config(page_title="Bio-Graph Agent", page_icon="🧬", layout="wide")
st.title("🧬 混元 Hy3 生物知识图谱自动生成引擎")
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

append_mode = True
# ==========================================
# 侧边栏配置：核心 API 和模型选择
# ==========================================


with st.sidebar:
    st.header("⚙️ 引擎配置")
    api_key = st.text_input("OpenRouter API Key", value="", type="password")

    model_options = {
        "Hunyuan 3 Preview (预览版 - 高性价比)": "tencent/hy3-preview",
        "Hunyuan 3 (正式版 - 最强推理)": "tencent/hy3",
        "Hunyuan 3 Free (免费版 - 易被限流)": "tencent/hy3:free"
    }
    selected_model_name = st.selectbox("🧠 选择底层驱动模型", list(model_options.keys()))
    selected_model_id = model_options[selected_model_name]

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
    st.subheader("📂 1. 文献输入与配置")
    uploaded_file = st.file_uploader("上传生物学文献 (PDF)", type=["pdf"])

    if uploaded_file:
        # 🛡️ 核心优化 1：文件与页数双重缓存锁（已修复原代码中的缩进 Bug）
        if "tmp_path" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                st.session_state["tmp_path"] = tmp.name
                st.session_state["file_name"] = uploaded_file.name

            # 💡 性能修复：PdfReader 必须放在 if 内部！
            # 否则原代码每次用户改页码或点开关，都会重新解析一次 PDF，导致极其卡顿
            reader = PdfReader(st.session_state["tmp_path"])
            st.session_state["total_pages"] = len(reader.pages)

        total_pages = st.session_state["total_pages"]
        tmp_path = st.session_state["tmp_path"]

        st.info(f"📄 成功读取 PDF 文件，总计 **{total_pages}** 页。")
        st.divider()

    st.subheader("⚙️ 2. 提取模式设置")
    # 🔥 全新进阶功能：可开关的“仅摘要模式”
    is_summary_only = st.toggle("⚡ 仅提取摘要模式 (速度极快)", value=False)
    use_reflection = st.toggle("🔍 启用自我反思纠错 (提高准确率，但更耗时)", value=True)

    append_mode = st.toggle("🔗 追加模式 (将本次提取结果叠加到现有图谱)", value=True)

    st.markdown("#### 🌐 实体命名规范")
    entity_language = st.radio(
        "强制统一图谱主节点（实体）的输出语言：",
        options=["关闭 (保持原文语言)", "中文 (强制翻译为中文)", "English (强制翻译为英文)"],
        index=0,
        horizontal=True
    )

    # 智能提示：告诉用户当前库里有没有东西
    if append_mode and len(st.session_state.master_entities) > 0:
        st.info(f"📦 记忆库就绪：当前已有 {len(st.session_state.master_entities)} 个节点。新知识将与之融合！")
    elif not append_mode and len(st.session_state.master_entities) > 0:
        st.warning("⚠️ 注意：关闭追加模式，将会【清空】现有图谱，从零开始！历史文献也会清空")

    if uploaded_file:
        # 🔥 智能页码联动：开启摘要模式默认只切 1-2 页；关闭则默认加载全文
        default_end = min(2, total_pages) if is_summary_only else total_pages

        st.markdown("#### 🎯 设定解析范围")
        col_inputs1, col_inputs2 = st.columns(2)
        with col_inputs1:
            start_page = st.number_input("起始页码", min_value=1, max_value=total_pages, value=1)
        with col_inputs2:
            # 🛡️ 修复：使用 max() 确保默认值永远不会低于起始页，完美避开 Streamlit 报错陷阱
            safe_default_end = max(start_page, default_end)
            end_page = st.number_input("结束页码", min_value=start_page, max_value=total_pages, value=safe_default_end)

        # 摘要模式下的安全阈值温柔提示
        if is_summary_only and (end_page - start_page > 2):
            st.warning("💡 提示：摘要通常在文献前两页。为了保证极速提取，建议缩小页码范围！")

        st.divider()
        # 核心启动按钮：移至左侧最下方，拉宽加大，极其醒目
        start_button = st.button("🚀 开始解析 & 生成图谱", use_container_width=True, type="primary")

# ==========================================
# 📁 后置侧边栏扩展区（安全视觉展现）
# ==========================================
# ==========================================
# 💡 新增：历史文献状态前置更新（解决侧边栏显示滞后问题）
# ==========================================
if uploaded_file and start_button:
    if append_mode:
        # 🟢 追加模式：将新文件安全落地
        save_path = os.path.join(HISTORY_DIR, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        if uploaded_file.name not in st.session_state.analyzed_files:
            st.session_state.analyzed_files.append(uploaded_file.name)
    else:
        # 💥 非追加模式：只有用户确定按下了“开始解析”，才真正执行物理清空！
        st.session_state.analyzed_files = []
        if os.path.exists(HISTORY_DIR):
            for fname in os.listdir(HISTORY_DIR):
                fpath = os.path.join(HISTORY_DIR, fname)
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                    except:
                        pass


# ==========================================
# 📁 后置侧边栏扩展区（安全视觉展现）
# ==========================================
with st.sidebar:
    # 💡 只有开启追加模式时，才在侧边栏展示历史文献库
    if append_mode:
        st.markdown("---")
        st.header("📚 历史分析文献")

        if not st.session_state.analyzed_files:
            st.info("暂无已分析的文献")
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
    st.subheader("👀 3. 边界预览")
    if uploaded_file:
        # 🛡️ 核心优化 2：PyMuPDF 高清安全渲染函数（保留阅后即焚与2倍高清）
        def get_page_image_bytes(page_idx):
            doc = fitz.open(tmp_path)
            page = doc.load_page(page_idx)
            zoom_matrix = fitz.Matrix(2.0, 2.0)  # 放大 2 倍分辨率，让文字更清晰
            pix = page.get_pixmap(matrix=zoom_matrix)
            img_bytes = pix.tobytes("png")
            doc.close()  # 阅后即焚，及时关闭文档释放内存
            return img_bytes


        with st.expander("🔍 点击查看选定范围的起止页 (用于确认边界)", expanded=True):
            col_preview1, col_preview2 = st.columns(2)

            # 左侧：渲染起始页
            with col_preview1:
                st.markdown(f"**🟢 起始边界 (第 {start_page} 页)**")
                try:
                    img_start = get_page_image_bytes(start_page - 1)
                    st.image(img_start, use_container_width=True)
                except Exception as e:
                    st.error(f"渲染失败: {e}")

            # 右侧：渲染结束页
            with col_preview2:
                if start_page != end_page:
                    st.markdown(f"**🔴 结束边界 (第 {end_page} 页)**")
                    try:
                        img_end = get_page_image_bytes(end_page - 1)
                        st.image(img_end, use_container_width=True)
                    except Exception as e:
                        st.error(f"渲染失败: {e}")
                else:
                    st.markdown("**🔴 结束边界**")
                    st.info("起止页相同，无需重复展示。")
    else:
        st.info("👈 请先在左侧上传 PDF 文献以激活边界预览。")

    # ==========================================
    # 💾 记忆库与工程管理区 (左栏底部)
    # ==========================================
    st.markdown("---")
    st.subheader("💾 记忆库与工程管理")

    # 将新建和导出按钮并排放在一起
    col_btn1, col_btn2 = st.columns(2)

    # ✨ 1. 新建记忆库 (防误触触发器)
    with col_btn1:
        if st.button("✨ 新建空白工程", use_container_width=True):
            # 点击后，反转确认面板的显示状态
            st.session_state.show_new_confirm = not st.session_state.get("show_new_confirm", False)

    # 📤 2. 导出记忆库 (.biokg)
    with col_btn2:
        export_placeholder = st.empty()

        # 💡 先放一个假按钮占位，防止页面空白难看
        with export_placeholder:
            # 假按钮不能用 st.download_button，用普通的 st.button 伪装
            if st.button("📤 导出工程 (.biokg)", use_container_width=True, key="fake_export_btn"):
                # 如果用户在没数据时点击，弹出一个轻量级的提示（不会打乱排版）
                st.toast("⚠️ 当前记忆库为空，请先上传并解析文献！", icon="🈳")

    # 🚨 新建动作的“二次确认”安全锁面板
    if st.session_state.get("show_new_confirm", False):
        st.warning("⚠️ **危险操作**：这将清空当前所有图谱与历史记录！（建议先导出保存）\n\n您确定要从零开始吗？")
        col_y, col_n = st.columns(2)
        with col_y:
            if st.button("🔴 确定清空", use_container_width=True):
                # 清空内存中的所有数据
                st.session_state.master_entities = []
                st.session_state.master_relations = []
                st.session_state.analyzed_files = []
                st.session_state.html_data = ""

                # 物理清空本地隐藏历史文件夹
                if os.path.exists(HISTORY_DIR):
                    for fname in os.listdir(HISTORY_DIR):
                        fpath = os.path.join(HISTORY_DIR, fname)
                        if os.path.isfile(fpath):
                            try:
                                os.remove(fpath)
                            except:
                                pass

                # 状态复位并刷新
                st.session_state.project_loaded_success = False
                st.session_state.show_new_confirm = False
                st.rerun()

        with col_n:
            if st.button("取消", use_container_width=True):
                st.session_state.show_new_confirm = False
                st.rerun()


    # ====================================================================
    # 📥 3. 导入记忆库 (使用【动态 Key 轮转技术】实现载入成功后组件自我销毁清空)
    # ====================================================================
    # 1. 初始化一个动态 key 存储在 session_state 中
    if "project_uploader_key" not in st.session_state:
        st.session_state.project_uploader_key = "project_uploader_init"

    # 2. 将这个动态 key 绑定到上传组件上
    uploaded_project = st.file_uploader(
        "📥 载入历史工程文件 (.biokg / .json)",
        type=["biokg", "json"],
        key=st.session_state.project_uploader_key  # 🔗 绑定动态 Key
    )

    if uploaded_project is not None:
        try:
            loaded_data = json.load(uploaded_project)

            # 增加一个确认按钮，防止用户误传文件直接覆盖当前进度
            if st.button("🚀 确认载入该工程", type="primary", use_container_width=True):
                # 将存档数据恢复到内存
                st.session_state.master_entities = loaded_data.get("entities", [])
                st.session_state.master_relations = loaded_data.get("relations", [])
                st.session_state.analyzed_files = loaded_data.get("analyzed_files", [])

                # 💡 核心逻辑：载入数据后，直接在后台重新画图
                from back_logic import GraphVisualizer

                visualizer = GraphVisualizer()
                html_file = ".bio_knowledge_graph.html"

                if os.path.exists(html_file):
                    os.remove(html_file)

                visualizer.generate_html(
                    st.session_state.master_entities,
                    st.session_state.master_relations,
                    output_file=html_file
                )

                # 将重新画好的 HTML 塞回前端
                if os.path.exists(html_file):
                    with open(html_file, "r", encoding="utf-8") as f:
                        st.session_state.html_data = f.read()

                # ✨【致命漏点修复】：强行打开前端结果渲染开关！
                # 只有把它设为 True，页面刷新后下方的 components.html 渲染区才会被激活执行！
                st.session_state.show_results = True

                # 🔥【核心修复点】：确认载入成功后，利用 uuid 生成一个全新的 Key！
                # 这会强制让 Streamlit 在下一步 st.rerun() 刷新页面时，把上传框重置为最初始的空白状态！
                st.session_state.project_uploader_key = f"project_uploader_{uuid.uuid4().hex}"

                # 强行刷新页面，让右栏立刻渲染出刚刚载入的图谱，同时上传框瞬间清空！
                st.rerun()
        except Exception as e:
            st.error(f"解析工程文件失败，请检查文件格式是否正确。报错信息: {e}")

# ==========================================
# 核心引擎触发与结果渲染区（全览画布排版）
# ==========================================
if uploaded_file and start_button:
    if not api_key:
        st.error("请先在左侧输入 API Key！")
    else:
        # 渲染在双栏下方，让最终的巨幅知识图谱能占满整张屏幕，视觉极其震撼
        st.markdown("---")

        # 🛠️ 核心 UI 修复：将 try 提到最外层，内部所有的 spinner 扁平化独立，避免重叠！
        try:
            # 实例化 Pipeline 并传入动态模型
            pipeline = BioGraphPipeline(api_key=api_key, model=selected_model_id)

            # 🟢 阶段一：独立的解析转圈
            with st.spinner(f"🧠 智能体正在解析第 {start_page} 到 {end_page} 页..."):
                # 1. 跑当前这篇文献，拿到新数据
                new_entities, new_relations = pipeline.run(
                    tmp_path,
                    start_page=start_page - 1,
                    end_page=end_page,
                    is_summary_only=is_summary_only,
                    use_reflection=use_reflection,
                    source_name=uploaded_file.name,
                    entity_lang = entity_language
                )

            # 🟢 阶段二：独立的融合转圈 (上一个转圈已经销毁)
            if append_mode and len(st.session_state.master_entities) > 0:
                with st.spinner("🔗 正在进行跨文献 AI 语义对齐与图谱融合..."):
                    # 1. 呼叫大模型裁判，获取同义词映射表 (如: {"TP53": "p53"})
                    alignment_map = pipeline.agent.align_global_entities(
                        st.session_state.master_entities,
                        new_entities
                    )

                    if alignment_map:
                        st.success(f"🧬 AI 识别到 {len(alignment_map)} 个跨文献同义实体！")

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
            with st.spinner("🎨 正在生成网络拓扑交互图谱..."):
                visualizer = GraphVisualizer()
                html_file = ".bio_knowledge_graph.html"

                # 🛡️ 破除幻觉机制：生成前强制删掉旧文件！
                if os.path.exists(html_file):
                    os.remove(html_file)

                visualizer.generate_html(
                    st.session_state.master_entities,
                    st.session_state.master_relations,
                    output_file=html_file
                )

            # 🟢 阶段四：所有处理完成，将结果存入全局保险箱
            if os.path.exists(html_file):
                st.success("🎉 图谱生成与数据融合成功！")
                with open(html_file, "r", encoding="utf-8") as f:
                    st.session_state.html_data = f.read()

                # 开启展示开关
                st.session_state.show_results = True
            else:
                st.error("❌ 图谱文件未生成。")
                st.session_state.show_results = False

        except Exception as e:
            # 所有阶段任何一步报错，都会统一跳到这里处理，代码极其优雅
            st.error(f"处理过程中发生错误：{e}")

# ==========================================
# 📥 独立渲染区：结果多元化导出与图谱展示（防白屏刷新机制）
# ==========================================
# 🌟 注意：下面这段代码必须完全没有缩进，贴紧最左侧！
if st.session_state.show_results and st.session_state.html_data:

    def redraw_and_update():
        from back_logic import GraphVisualizer
        import os
        visualizer = GraphVisualizer()
        html_file = ".bio_knowledge_graph.html"
        if os.path.exists(html_file):
            os.remove(html_file)

        current_show_shortcuts = st.session_state.get("show_shortcuts_toggle", False)

        visualizer.generate_html(
            st.session_state.master_entities,
            st.session_state.master_relations,
            output_file=html_file,
            show_shortcuts=current_show_shortcuts
        )

        if os.path.exists(html_file):
            with open(html_file, "r", encoding="utf-8") as f:
                st.session_state.html_data = f.read()


    st.markdown("### 📥 4. 知识图谱结果导出")

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
        st.download_button("📄 导出实体 (JSON)", entities_json, "bio_entities.json", "application/json",
                           use_container_width=True)
    with btn_col2:
        st.download_button("📊 导出实体 (CSV)", csv_entities, "bio_entities.csv", "text/csv", use_container_width=True)
    with btn_col3:
        st.download_button("🔗 导出关系 (CSV)", csv_relations, "bio_relations.csv", "text/csv", use_container_width=True)
    with btn_col4:
        st.download_button("🕸️ 导出交互图谱 (HTML)", st.session_state.html_data, "bio_graph.html", "text/html",
                           use_container_width=True)

    st.markdown("---")

    disp_col1, disp_col2 = st.columns(2)
    with disp_col1:
        # 使用 key="show_shortcuts_toggle" 赋予它永久记忆
        # 使用 on_change=redraw_and_update 让它一被点击就瞬间重绘画布！
        st.toggle(
            "👁️ 显示机制捷径边",
            key="show_shortcuts_toggle",
            on_change=redraw_and_update
        )
    with disp_col2:
        st.caption("✨ ")



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
                label="📤 导出工程 (.biokg)",
                data=json_bytes,
                file_name="我的图谱工程.biokg",
                mime="application/json",
                use_container_width=True,
                key="real_export_btn"
            )

    # ==========================================
    # 🎛️ 终极图谱数据管理中心
    # ==========================================
    ENABLE_EDITOR = True

    if ENABLE_EDITOR and len(st.session_state.master_entities) > 0:
        st.subheader("🎛️ 图谱数据管理中心")

        # 🚀 终极架构修复：用带记忆的 Radio 替代失忆的 Tabs
        main_tab = st.radio(
            "选择管理模块：",
            ["⚡ 快捷功能", "🎯 节点操作", "🔗 关系操作"],
            horizontal=True,
            label_visibility="collapsed",
            key="main_nav_radio"  # 加上安全密钥防冲突
        )
        st.markdown("---")

        # -----------------------------------------
        # 方向一：快捷功能
        # -----------------------------------------
        if main_tab == "⚡ 快捷功能":
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🧹 一键清理")
                st.info("清理掉那些既不是起点、也不是终点的“孤立无援”的节点。")
                if st.button("🗑️ 清除所有孤立节点", use_container_width=True):
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
                        st.toast(f"✅ 成功清理了 {old_count - len(st.session_state.master_entities)} 个孤立节点！", icon="🧹")
                        redraw_and_update()
                        st.rerun()
                    else:
                        st.toast("当前图谱很健康，没有发现孤立节点。", icon="✨")

                st.markdown("#### 📝 批量修改文献/来源名")
                all_sources = set()
                for ent in st.session_state.master_entities:
                    if "doc_source" in ent: all_sources.add(ent["doc_source"])
                for rel in st.session_state.master_relations:
                    if "doc_source" in rel: all_sources.add(rel["doc_source"])
                if "analyzed_files" in st.session_state:
                    for f in st.session_state.analyzed_files: all_sources.add(f)

                all_sources = list(all_sources)

                if not all_sources:
                    st.info("当前图谱没有来源记录。")
                else:
                    with st.form("rename_source_form"):
                        old_source = st.selectbox("选择要修改的文献/来源名", all_sources)
                        new_source = st.text_input("输入新的名称 (如：Nature_2023_p53)")

                        if st.form_submit_button("🔄 一键替换全图谱来源", type="primary", use_container_width=True):
                            if not new_source.strip():
                                st.error("❌ 新名称不能为空！")
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
                                st.toast(f"✅ 成功替换 '{old_source}'", icon="🎉")
                                redraw_and_update()
                                st.rerun()

            with col2:
                st.markdown("#### ➕ 手动添加节点")
                with st.form("manual_add_node_form"):
                    new_node_name = st.text_input("输入新节点标准名 (必填)")
                    new_node_aliases = st.text_input("输入别名 (选填，逗号分隔)")
                    new_node_source = st.text_input("输入文献来源 (为空记为'手动添加')")

                    if st.form_submit_button("💾 保存并添加节点", type="primary", use_container_width=True):
                        if not new_node_name.strip():
                            st.error("❌ 节点名称不能为空！")
                        else:
                            existing_names = [e.get("standard_name") for e in st.session_state.master_entities]
                            if new_node_name.strip() in existing_names:
                                st.warning("⚠️ 节点已经存在！")
                            else:
                                aliases_list = [a.strip() for a in
                                                new_node_aliases.split(",")] if new_node_aliases.strip() else []
                                final_source = new_node_source.strip() if new_node_source.strip() else "手动添加"
                                st.session_state.master_entities.append({
                                    "standard_name": new_node_name.strip(),
                                    "aliases": aliases_list,
                                    "doc_source": final_source
                                })
                                st.toast("✅ 节点添加成功！", icon="🎉")
                                redraw_and_update()
                                st.rerun()

        # -----------------------------------------
        # 🎯 方向二：节点操作 (核心引擎)
        # -----------------------------------------
        elif main_tab == "🎯 节点操作":
            all_node_names = sorted([e.get("standard_name") for e in st.session_state.master_entities])

            if not all_node_names:
                st.info("当前图谱为空，无法操作。")
            else:
                target_node_name = st.selectbox("🔍 搜索并选择要操作的节点", ["-- 请选择 --"] + all_node_names)

                if target_node_name != "-- 请选择 --":
                    target_ent = next(
                        (e for e in st.session_state.master_entities if e.get("standard_name") == target_node_name),
                        None)

                    if target_ent:
                        st.markdown(f"### 当前选中: `{target_node_name}`")

                        action = st.radio(
                            "选择操作：",
                            ["✏️ 修改信息", "🧲 合并到...", "🔀 节点拆分", "🗑️ 危险删除"],
                            horizontal=True,
                            label_visibility="collapsed",
                            key="node_action_radio"  # 加上安全密钥防冲突
                        )

                        # -- 修改信息 --
                        if action == "✏️ 修改信息":
                            with st.form("edit_node_form"):
                                new_name = st.text_input("新标准名", value=target_ent.get("standard_name"))
                                current_aliases = ", ".join(target_ent.get("aliases", []))
                                new_aliases = st.text_input("别名 (逗号分隔)", value=current_aliases)

                                if st.form_submit_button("💾 保存修改", type="primary"):
                                    clean_new_name = new_name.strip()
                                    if clean_new_name:
                                        if clean_new_name != target_node_name:
                                            # 级联更新连线
                                            for rel in st.session_state.master_relations:
                                                if rel.get("source") == target_node_name: rel["source"] = clean_new_name
                                                if rel.get("target") == target_node_name: rel["target"] = clean_new_name

                                        target_ent["standard_name"] = clean_new_name
                                        target_ent["aliases"] = [a.strip() for a in new_aliases.split(",") if a.strip()]
                                        st.toast("✅ 节点修改成功！", icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

                        # -- 合并节点 --
                        elif action == "🧲 合并到...":
                            st.info(f"将 `{target_node_name}` 的所有关系转移给另一个节点，随后销毁本体。")
                            merge_target = st.selectbox("选择目标节点", [n for n in all_node_names if n != target_node_name])

                            if st.button("🧲 确认合并", type="primary", use_container_width=True):
                                # 转移连线
                                for rel in st.session_state.master_relations:
                                    if rel.get("source") == target_node_name: rel["source"] = merge_target
                                    if rel.get("target") == target_node_name: rel["target"] = merge_target

                                # 转移别名并去重
                                dest_ent = next(e for e in st.session_state.master_entities if
                                                e.get("standard_name") == merge_target)
                                combined_aliases = set(
                                    dest_ent.get("aliases", []) + target_ent.get("aliases", []) + [target_node_name])
                                dest_ent["aliases"] = list(combined_aliases)

                                # 销毁原节点
                                st.session_state.master_entities = [e for e in st.session_state.master_entities if
                                                                    e.get("standard_name") != target_node_name]
                                st.toast(f"✅ 成功合并入 {merge_target}！", icon="🎉")
                                redraw_and_update()
                                st.rerun()

                        # -- 节点拆分 (预留) --
                        elif action == "🔀 节点拆分":
                            st.info(f"将 `{target_node_name}` 拆分为两个独立节点，并重新分配它的关系连线。")

                            # 1. 找出所有牵扯到该节点的关系连线
                            related_rels = []
                            for i, rel in enumerate(st.session_state.master_relations):
                                if rel.get("source") == target_node_name or rel.get("target") == target_node_name:
                                    related_rels.append((i, rel))

                            with st.form("split_node_form"):
                                st.markdown("##### 1. 定义拆分后的新节点")
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    name_a = st.text_input("新节点 A (如：mutant p53)", value=f"{target_node_name}_A")
                                    aliases_a = st.text_input("节点 A 别名 (逗号分隔)",
                                                              value=", ".join(target_ent.get("aliases", [])))
                                with col_b:
                                    name_b = st.text_input("新节点 B (如：wild-type p53)", value=f"{target_node_name}_B")
                                    aliases_b = st.text_input("节点 B 别名 (逗号分隔)", value="")

                                st.markdown("##### 2. 分配原有关系连线")
                                rel_choices = {}
                                if not related_rels:
                                    st.caption("（该节点目前没有任何连线，无需分配）")
                                else:
                                    for idx, rel in related_rels:
                                        # 构造直观的关系描述
                                        src = rel.get("source")
                                        tgt = rel.get("target")
                                        rel_type = rel.get("relation", "关联")
                                        display_text = f"**{src}** ─[{rel_type}]▶ **{tgt}**"

                                        # 为每条连线生成一个独立的单选框
                                        rel_choices[idx] = st.radio(
                                            display_text,
                                            options=["给 A", "给 B", "A 和 B 都要 (复制)", "丢弃该线"],
                                            horizontal=True,
                                            key=f"split_rel_{idx}"
                                        )

                                if st.form_submit_button("🔀 确认执行拆分", type="primary", use_container_width=True):
                                    c_name_a = name_a.strip()
                                    c_name_b = name_b.strip()

                                    if not c_name_a or not c_name_b:
                                        st.error("❌ 两个新节点的名称都不能为空！")
                                    elif c_name_a == c_name_b:
                                        st.error("❌ 新节点 A 和 B 不能同名！")
                                    else:
                                        import copy

                                        # ---- 执行拆分逻辑 ----
                                        # 1. 删掉旧实体，加入新实体 A 和 B
                                        st.session_state.master_entities = [e for e in st.session_state.master_entities
                                                                            if
                                                                            e.get("standard_name") != target_node_name]

                                        st.session_state.master_entities.append({
                                            "standard_name": c_name_a,
                                            "aliases": [x.strip() for x in aliases_a.split(",") if x.strip()],
                                            "doc_source": target_ent.get("doc_source", "手动拆分")
                                        })
                                        st.session_state.master_entities.append({
                                            "standard_name": c_name_b,
                                            "aliases": [x.strip() for x in aliases_b.split(",") if x.strip()],
                                            "doc_source": target_ent.get("doc_source", "手动拆分")
                                        })

                                        # 2. 遍历全局关系，进行重组
                                        new_relations = []
                                        for i, rel in enumerate(st.session_state.master_relations):
                                            if i in rel_choices:
                                                # 这是牵扯到旧节点的关系
                                                choice = rel_choices[i]
                                                if choice == "丢弃该线":
                                                    continue  # 直接不要了

                                                is_source = (rel.get("source") == target_node_name)
                                                is_target = (rel.get("target") == target_node_name)


                                                def make_rel(node_name):
                                                    # 使用深拷贝防止内存污染
                                                    new_r = copy.deepcopy(rel)
                                                    if is_source: new_r["source"] = node_name
                                                    if is_target: new_r["target"] = node_name
                                                    return new_r


                                                if choice == "给 A":
                                                    new_relations.append(make_rel(c_name_a))
                                                elif choice == "给 B":
                                                    new_relations.append(make_rel(c_name_b))
                                                elif choice == "A 和 B 都要 (复制)":
                                                    new_relations.append(make_rel(c_name_a))
                                                    new_relations.append(make_rel(c_name_b))
                                            else:
                                                # 跟这个节点无关的连线，原样保留
                                                new_relations.append(rel)

                                        st.session_state.master_relations = new_relations
                                        st.toast(f"✅ 节点已成功拆分为 {c_name_a} 和 {c_name_b}！", icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

                        # -- 彻底删除 --
                        elif action == "🗑️ 危险删除":
                            st.error(f"⚠️ 警告：删除 `{target_node_name}` 将同时拔除所有相关连线！")
                            if st.button("🚨 确认彻底删除", type="primary", use_container_width=True):
                                st.session_state.master_entities = [e for e in st.session_state.master_entities if
                                                                    e.get("standard_name") != target_node_name]
                                st.session_state.master_relations = [r for r in st.session_state.master_relations if
                                                                     r.get("source") != target_node_name and r.get(
                                                                         "target") != target_node_name]
                                st.toast("✅ 彻底清除！", icon="🗑️")
                                redraw_and_update()
                                st.rerun()

        # -----------------------------------------
        # 🎯 方向三：关系操作 (无向搜索，有向编辑，标准词汇版)
        # -----------------------------------------
        elif main_tab == "🔗 关系操作":
            all_node_names = sorted([e.get("standard_name") for e in st.session_state.master_entities])

            # 💡 核心对齐：换成你的系统能够识别的三大标准关系！
            SAFE_RELATIONS = ["正作用", "负作用", "相关"]

            if not all_node_names:
                st.info("当前图谱为空，请先添加节点。")
            else:
                st.markdown("### 🔍 搜索两个节点间的关联")
                col_a, col_b = st.columns(2)
                with col_a:
                    node_a = st.selectbox("📍 选择节点 A", ["-- 请选择 --"] + all_node_names)
                with col_b:
                    node_b = st.selectbox("🎯 选择节点 B", ["-- 请选择 --"] + all_node_names)

                if node_a != "-- 请选择 --" and node_b != "-- 请选择 --":
                    if node_a == node_b:
                        st.warning("⚠️ 节点 A 和节点 B 不能相同，暂不支持操作自环关系。")
                    else:
                        st.markdown("---")

                        matching_rels = []
                        for i, r in enumerate(st.session_state.master_relations):
                            src = r.get("source")
                            tgt = r.get("target")
                            if (src == node_a and tgt == node_b) or (src == node_b and tgt == node_a):
                                matching_rels.append((i, r))

                        rel_op_mode = st.radio(
                            f"针对 `{node_a}` 与 `{node_b}` 之间的操作：",
                            ["✏️ 管理两者间已有关系", "➕ 新增一条关系连线"],
                            horizontal=True
                        )

                        # ==========================================
                        # 子功能 A：管理 / 修改 / 删除 现有关系
                        # ==========================================
                        if rel_op_mode == "✏️ 管理两者间已有关系":
                            if not matching_rels:
                                st.info(f"💡 `{node_a}` 和 `{node_b}` 之间目前没有任何直接连线。")
                            else:
                                rel_options = {}
                                for idx, r in matching_rels:
                                    src = r.get("source")
                                    tgt = r.get("target")
                                    rel_type = r.get("relation", SAFE_RELATIONS[0])
                                    display_text = f"[{idx}] {src} ─[{rel_type}]▶ {tgt}"
                                    rel_options[display_text] = idx

                                selected_rel_text = st.selectbox("二级菜单：选择要修改的具体连线", list(rel_options.keys()))

                                rel_idx = rel_options[selected_rel_text]
                                target_rel = st.session_state.master_relations[rel_idx]

                                with st.form("edit_rel_form"):
                                    current_src = target_rel.get('source')
                                    dir_option_1 = f"从 {node_a} ─▶ 指向 {node_b}"
                                    dir_option_2 = f"从 {node_b} ─▶ 指向 {node_a}"

                                    new_direction = st.selectbox(
                                        "🔄 修改连线方向",
                                        [dir_option_1, dir_option_2],
                                        index=0 if current_src == node_a else 1
                                    )

                                    current_rel = target_rel.get("relation", "")
                                    default_idx = SAFE_RELATIONS.index(
                                        current_rel) if current_rel in SAFE_RELATIONS else 0
                                    selected_rel_type = st.selectbox("🔖 修改关系类型", SAFE_RELATIONS, index=default_idx)

                                    new_evidence = st.text_area("原文证据 (Evidence)", value=target_rel.get("evidence", ""))
                                    new_reason = st.text_area("推理原因 (Reason)", value=target_rel.get("reason", ""))

                                    # 💡 新增：允许修改关系的来源
                                    new_doc_source = st.text_input("文献来源 (Doc Source)",
                                                                   value=target_rel.get("doc_source", "手动添加"))

                                    if st.form_submit_button("💾 保存修改", type="primary", use_container_width=True):
                                        final_src, final_tgt = (node_a, node_b) if new_direction == dir_option_1 else (
                                        node_b, node_a)

                                        st.session_state.master_relations[rel_idx]["source"] = final_src
                                        st.session_state.master_relations[rel_idx]["target"] = final_tgt
                                        st.session_state.master_relations[rel_idx]["relation"] = selected_rel_type
                                        st.session_state.master_relations[rel_idx]["evidence"] = new_evidence.strip()
                                        st.session_state.master_relations[rel_idx]["reason"] = new_reason.strip()
                                        # 💡 保存来源（如果清空了则使用默认值）
                                        st.session_state.master_relations[rel_idx][
                                            "doc_source"] = new_doc_source.strip() if new_doc_source.strip() else "手动修改"

                                        st.toast("✅ 关系及方向修改成功！", icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

                                st.markdown("---")
                                if st.button("🚨 斩断 / 删除此连线", type="primary", use_container_width=True):
                                    st.session_state.master_relations.pop(rel_idx)
                                    st.toast("✅ 连线已彻底删除！", icon="✂️")
                                    redraw_and_update()
                                    st.rerun()

                        # ==========================================
                        # 子功能 B：手动搭桥，安全新增
                        # ==========================================
                        elif rel_op_mode == "➕ 新增一条关系连线":
                            with st.form("add_rel_form"):
                                direction = st.radio(
                                    "确认新连线的指向：",
                                    [f"从 {node_a} ─▶ 指向 {node_b}", f"从 {node_b} ─▶ 指向 {node_a}"],
                                    horizontal=True
                                )

                                selected_new_rel = st.selectbox("🔖 选择关系类型", SAFE_RELATIONS)
                                new_evidence = st.text_area("原文证据 / 备注 (选填)")

                                # 💡 新增：添加关系时允许填入来源
                                new_doc_source = st.text_input("文献来源 (选填，为空则记为'手动添加')")

                                if st.form_submit_button("💾 保存并添加连线", type="primary", use_container_width=True):
                                    final_src, final_tgt = (node_a, node_b) if direction.startswith(
                                        f"从 {node_a}") else (node_b, node_a)

                                    exist = any(r.get("source") == final_src and
                                                r.get("target") == final_tgt and
                                                r.get("relation") == selected_new_rel
                                                for r in st.session_state.master_relations)

                                    if exist:
                                        st.warning(
                                            f"⚠️ `{final_src}` 到 `{final_tgt}` 已经存在 `{selected_new_rel}` 类型的连线了！")
                                    else:
                                        # 💡 确定最终来源
                                        final_source_str = new_doc_source.strip() if new_doc_source.strip() else "手动添加"

                                        st.session_state.master_relations.append({
                                            "source": final_src,
                                            "target": final_tgt,
                                            "relation": selected_new_rel,
                                            "evidence": new_evidence.strip(),
                                            "reason": "用户手动添加",
                                            "doc_source": final_source_str  # 💡 写入来源字段
                                        })
                                        st.toast("✅ 新关系建立成功！", icon="🎉")
                                        redraw_and_update()
                                        st.rerun()

    # ==========================================
    # 🤖 AI 智能图谱清洗中心 (真机驱动版)
    # ==========================================
    ENABLE_AI_CLEANER = True

    if ENABLE_AI_CLEANER and len(st.session_state.master_entities) > 0:
        st.markdown("---")
        st.subheader("🤖 AI 智能图谱工具")

        # 🚀 优化 1：使用带记忆锁的 Radio 导航替代失忆的 st.tabs
        ai_nav = st.radio(
            "选择 AI 模块：",
            ["🧹 智能洗树 (Pruning)", "🔍 智能拓展 (Smart Expansion)"],
            horizontal=True,
            label_visibility="collapsed",
            key="ai_nav_radio"  # 🔗 专属记忆密钥，任何刷新都不会丢失当前标签
        )
        st.markdown("---")

        # -----------------------------------------
        # 模块一：智能洗树 (Pruning)
        # -----------------------------------------
        if ai_nav == "🧹 智能洗树 (Pruning)":
            # 🚀 优化 2：调整优先级，将专属业务提示下沉到本栏目最上方，排版更优雅
            st.info("💡 核心功能：基于大模型的上下文理解，自动发现并处理图谱中的同义词冗余、宏观与微观层级关系、以及机制捷径边。")
            st.write("点击下方按钮，将当前图谱的拓扑结构与文献证据发送给大模型进行诊断。")

            col_btn, col_toggle = st.columns([1, 1])
            with col_btn:
                if st.button("🚀 开始 AI 智能诊断图谱", type="primary", use_container_width=True):
                    current_api_key = api_key.strip()

                    # 🛑 拦截没有填写 API Key 的行为
                    if not current_api_key:
                        st.error("❌ 拦截：系统检测到您未填写 API Key！AI 图谱清洗需要调用大模型，请先在侧边栏配置密钥。")
                        st.stop()

                    with st.spinner("🧠 大模型正在深度阅读文献证据并梳理图谱拓扑... (请耐心等待)"):
                        from LLM_SYS import BioBrainAgent

                        agent = BioBrainAgent(api_key=current_api_key)
                        suggestions = agent.diagnose_graph(st.session_state.master_entities,
                                                           st.session_state.master_relations)

                        st.session_state.ai_suggestions = suggestions
                        st.toast("✅ 大模型诊断完成！", icon="🤖")
                        st.rerun()

            with col_toggle:
                # 💡 优化 3：抛弃上一轮残留的旧 st.toggle 开关，统一改为文字提示
                st.info("💡 诊断完成后，请直接在上方【图谱显示控制面板】灵活开启或关闭捷径边的显示。")

            # -----------------------------------------
            # 📋 渲染真实的审查清单并执行
            # -----------------------------------------
            if hasattr(st.session_state, "ai_suggestions") and st.session_state.ai_suggestions:
                st.markdown("### 📋 智能修改审查清单")

                with st.form("ai_prune_review_form"):
                    selected_actions = []

                    for i, sug in enumerate(st.session_state.ai_suggestions):
                        action = sug.get("action")
                        reason = sug.get("reason", "未提供原因")

                        if action == "MERGE":
                            target = sug.get("target_node")
                            removes = sug.get("nodes_to_remove", [])
                            label = f"🧲 **合并同义词**: 将 `{removes}` 合并入 `{target}` (原因: {reason})"
                        elif action == "HIERARCHY":
                            parent = sug.get("parent")
                            child = sug.get("child")
                            label = f"🌳 **建立层级**: 建立 `{parent}` ─[包含]▶ `{child}` (原因: {reason})"
                        elif action == "DOWNGRADE":
                            src = sug.get("source")
                            tgt = sug.get("target")
                            rel = sug.get("relation")
                            label = f"📉 **降级捷径边**: 将连线 `{src} ─[{rel}]▶ {tgt}` 降级为推导虚线 (原因: {reason})"
                        elif action == "REMOVE":
                            src = sug.get("source")
                            tgt = sug.get("target")
                            rel = sug.get("relation")
                            label = f"✂️ **删除越级连线**: 彻底移除 `{src} ─[{rel}]▶ {tgt}` (原因: {reason})"
                        else:
                            continue

                        # 渲染勾选框
                        if st.checkbox(label, value=True, key=f"sug_{i}"):
                            selected_actions.append(sug)

                    st.markdown("---")
                    if st.form_submit_button("💾 确认执行选中的优化", type="primary", use_container_width=True):

                        # 核心执行引擎
                        for act in selected_actions:
                            # 1. 执行合并
                            if act["action"] == "MERGE":
                                target = act.get("target_node")
                                removes = act.get("nodes_to_remove", [])
                                for r in st.session_state.master_relations:
                                    if r.get("source") in removes: r["source"] = target
                                    if r.get("target") in removes: r["target"] = target
                                st.session_state.master_entities = [e for e in st.session_state.master_entities if
                                                                    e.get("standard_name") not in removes]

                            # 2. 执行建立层级
                            elif act["action"] == "HIERARCHY":
                                parent = act.get("parent")
                                child = act.get("child")

                                merged_evidence = "AI 智能逻辑推导"
                                merged_doc_source = "AI 分析"

                                for i in range(len(st.session_state.master_relations) - 1, -1, -1):
                                    r = st.session_state.master_relations[i]
                                    is_match = ((r.get("source") == parent and r.get("target") == child) or
                                                (r.get("source") == child and r.get("target") == parent))

                                    if is_match and r.get("relation") == "相关":
                                        merged_evidence = r.get("evidence", merged_evidence)
                                        merged_doc_source = r.get("doc_source", merged_doc_source)
                                        st.session_state.master_relations.pop(i)

                                st.session_state.master_relations.append({
                                    "source": parent,
                                    "target": child,
                                    "relation": "包含",
                                    "evidence": merged_evidence,
                                    "reason": act.get("reason"),
                                    "doc_source": merged_doc_source
                                })

                            # 3. 执行彻底删除
                            elif act["action"] == "REMOVE":
                                src = act.get("source")
                                tgt = act.get("target")
                                rel = act.get("relation")
                                for i in range(len(st.session_state.master_relations) - 1, -1, -1):
                                    r = st.session_state.master_relations[i]
                                    if r.get("source") == src and r.get("target") == tgt and r.get(
                                            "relation") == rel:
                                        st.session_state.master_relations.pop(i)

                            # 4. 执行降级捷径边
                            elif act["action"] == "DOWNGRADE":
                                for r in st.session_state.master_relations:
                                    if r.get("source") == act.get("source") and r.get("target") == act.get(
                                            "target") and r.get("relation") == act.get("relation"):
                                        r["is_shortcut"] = True

                        # ====================================================
                        # 🧹 洗树后的终极清理：全局关系去重与融合
                        # (因为合并同义词后，原本不重复的连线会发生重叠，必须重新融合并加粗权重)
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

                                # 1. 累加权重 (图谱连线变粗)
                                merged_rel["weight"] = merged_rel.get("weight", 1) + existing_rel.get(
                                    "weight", 1)

                                # 2. 合并证据
                                old_ev = merged_rel.get("evidence", "")
                                new_ev = existing_rel.get("evidence", "")
                                if new_ev and new_ev not in old_ev:
                                    merged_rel["evidence"] = f"{old_ev}\n---\n{new_ev}"

                                # 3. 合并文献来源
                                old_src = merged_rel.get("doc_source", "")
                                new_src = existing_rel.get("doc_source", "")
                                if new_src and new_src not in old_src:
                                    merged_rel["doc_source"] = f"{old_src} | {new_src}"

                                # 4. 合并解释
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
                        # ====================================================

                        st.session_state.ai_suggestions = []  # 清空建议表
                        st.toast("✅ 优化已完美执行！", icon="🎉")
                        redraw_and_update()
                        st.rerun()  # 🚀 优化 4：顺手在这里也加上手动 rerun()，让执行优化后的新图谱瞬间完美秒刷！

        # -----------------------------------------
        # -----------------------------------------
        # 模块二：🔍 智能拓展 (Smart Expansion)
        # -----------------------------------------
        elif ai_nav == "🔍 智能拓展 (Smart Expansion)":
            st.info("💡 选中图谱中的关键节点，系统将自动在 PubMed 中检索前沿文献，并由 AI 提取摘要知识，自动将其延伸至当前图谱。")

            # 1. 交互区：选中图谱已有节点与策略配置
            all_node_names = [e.get("standard_name") for e in st.session_state.master_entities]
            selected_nodes = st.multiselect("🎯 请选择要拓展的核心节点 (建议 1-3 个):", all_node_names)

            # 🚀 新增：三挡变速检索引擎
            search_mode = st.radio(
                "🧠 选择检索与拓展策略：",
                options=[
                    "⚡ 直接搜索 (速度极快，精准字符匹配)",
                    "🧠 智能搜索 (AI 扩充同义词与 Mesh 主题词)",
                    "🌐 背景搜索 (最强：AI 阅读图谱已知连线，智能发散机制)"
                ],
                horizontal=False
            )
            max_results = st.slider("📄 检索返回文献数量上限", min_value=5, max_value=20, value=10)

            if st.button("🔍 联网搜索相关文献", type="primary"):
                if not selected_nodes:
                    st.warning("⚠️ 请先在上方选择至少一个节点！")
                else:
                    with st.spinner("🌐 正在生成策略并呼叫 PubMed API 获取最新文献..."):
                        from WebSearcher import PubMedSearcher

                        searcher = PubMedSearcher()
                        query = ""

                        # ⚡ 模式 1：纯 Python 暴力拼接（不调大模型）
                        if "直接搜索" in search_mode:
                            query_parts = [f'("{node}"[Title/Abstract])' for node in selected_nodes]
                            query = " AND ".join(query_parts)
                            st.session_state.last_generated_query = query

                        # 🧠/🌐 模式 2 & 3：召唤大模型
                        else:
                            current_api_key = api_key.strip()
                            if not current_api_key:
                                st.error("❌ 拦截：请先在侧边栏配置 API Key 以启用 AI 搜索功能。")
                                st.stop()

                            from LLM_SYS import BioBrainAgent

                            agent = BioBrainAgent(api_key=current_api_key)

                            # 组装节点别名情报
                            selected_nodes_info = []
                            for e in st.session_state.master_entities:
                                if e.get("standard_name") in selected_nodes:
                                    selected_nodes_info.append({
                                        "name": e.get("standard_name"),
                                        "aliases": e.get("aliases", [])
                                    })

                            if "智能搜索" in search_mode:
                                query = agent.generate_pubmed_query(selected_nodes_info)
                            elif "背景搜索" in search_mode:
                                # 💡 核心逻辑：找出图谱中与选中节点相关的所有“已知关系”
                                relevant_relations = [r for r in st.session_state.master_relations
                                                      if r.get("source") in selected_nodes or r.get(
                                        "target") in selected_nodes]
                                query = agent.generate_pubmed_query(selected_nodes_info,
                                                                    context_relations=relevant_relations)

                            st.session_state.last_generated_query = query

                        # 统一执行 PubMed 搜索
                        results = searcher.search_articles(query, max_results=max_results)
                        st.session_state.pubmed_search_results = results
                        st.toast(f"✅ 成功检索到 {len(results)} 篇相关文献！", icon="🎉")
                        st.rerun()

            # 2. 勾选区：使用优雅的 st.data_editor 展示结果
            if st.session_state.pubmed_search_results:
                st.markdown("### 📑 检索结果 (请勾选需要深度分析的文献)")

                # 转换成 DataFrame 并插入一列用于打勾
                df = pd.DataFrame(st.session_state.pubmed_search_results)
                if "Include" not in df.columns:
                    df.insert(0, "Include", False)  # 默认都不勾选

                # 渲染可交互表格
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Include": st.column_config.CheckboxColumn("✅ 引入图谱", default=False),
                        "pmid": st.column_config.TextColumn("PMID", disabled=True),
                        "title": st.column_config.TextColumn("文献标题", disabled=True),
                        "year": st.column_config.TextColumn("年份", disabled=True),
                    },
                    disabled=["pmid", "title", "year", "authors", "doi"],  # 锁定文本列不让修改
                    hide_index=True,
                    use_container_width=True,
                    key="pubmed_data_editor"
                )

                st.markdown("---")
                # ==========================================
                # 3. 熔接区：初始化队列
                # ==========================================
                if st.button("📥 将勾选文献加入解析队列", type="primary", use_container_width=True):
                    selected_docs = edited_df[edited_df["Include"] == True]

                    if selected_docs.empty:
                        st.warning("⚠️ 请至少在表格中勾选一篇文献！")
                    else:
                        # 初始化任务队列状态
                        st.session_state.expansion_queue = selected_docs.to_dict('records')
                        st.session_state.expansion_idx = 0
                        st.toast("✅ 已加入队列！请在下方控制台进行单步处理。", icon="📥")
                        st.rerun()


                # ==========================================
                # 4. 队列逐篇解析控制台 (全新引入的状态机)
                # ==========================================

                # 🛠️ 修复核心：定义一个安全的回调函数，用于点击“终止”时提前重置状态
                def bg_reset_expansion_task():
                    st.session_state.expansion_queue = []
                    st.session_state.expansion_idx = 0
                    if "auto_run_expansion" in st.session_state:
                        st.session_state.auto_run_expansion = False  # 在渲染前修改，100%安全！


                if "expansion_queue" in st.session_state and st.session_state.expansion_queue:
                    queue = st.session_state.expansion_queue
                    idx = st.session_state.expansion_idx
                    total = len(queue)

                    st.markdown("---")
                    st.markdown(f"### ⚙️ 深度融合任务队列 (进度: {idx}/{total})")

                    if idx < total:
                        current_doc = queue[idx]
                        pmid = current_doc['pmid']
                        title = current_doc['title']

                        st.info(f"👉 **当前准备解析:**\n\n📄 {title}\n*(PMID: {pmid})*")

                        # 🚀 无人值守的连续自动执行开关
                        auto_run = st.toggle("🔁 开启连续自动解析 (无人值守模式)", value=False, key="auto_run_expansion")
                        if auto_run:
                            st.caption("⚠️ 自动巡航模式运行中... (若需中途强行中止，请点击页面右上角自带的 'Stop' 按钮)")

                        # 三挡控制按钮
                        col_run, col_skip, col_stop = st.columns(3)

                        btn_run = col_run.button("▶️ 解析并融合本篇", use_container_width=True, type="primary",
                                                 disabled=auto_run)
                        btn_skip = col_skip.button("⏭️ 跳过这篇", use_container_width=True, disabled=auto_run)

                        # 🛠️ 修复点 1：通过 on_click 绑定刚才写好的回调函数
                        btn_stop = col_stop.button("🛑 终止任务并清空", use_container_width=True, disabled=auto_run,
                                                   on_click=bg_reset_expansion_task)

                        # 💡 触发逻辑：只要【点了运行按钮】或者【开启了自动开关】
                        if btn_run or auto_run:
                            current_api_key = api_key.strip()
                            if not current_api_key:
                                st.error("❌ 拦截：请先在侧边栏配置 API Key。")
                                # 🛠️ 修复点 2：删掉这里强行修改 state 的报错代码。
                                # 直接 st.stop() 即可！此时开关依然是开着的，页面会停在这里。
                                # 带来的神级体验：用户在侧边栏补上 API Key 的瞬间，自动化引擎会自动检测并【继续无缝向下跑】，极其丝滑！
                                st.stop()

                            from WebSearcher import PubMedSearcher
                            from LLM_SYS import BioBrainAgent
                            import datetime
                            import os

                            searcher = PubMedSearcher()
                            agent = BioBrainAgent(api_key=current_api_key)

                            with st.spinner(f"⏳ 正在深度解析并提取 {pmid} 的知识..."):
                                abstract = searcher.fetch_abstract(pmid)
                                if len(abstract) < 50:
                                    st.toast(f"文献 {pmid} 摘要为空或过短，已自动跳过。", icon="⏭️")
                                else:
                                    new_entities = agent.extract_entities_with_reflection(abstract,
                                                                                          use_reflection=True)
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

                                    log_dir = ".expanded_logs"
                                    os.makedirs(log_dir, exist_ok=True)
                                    log_file = os.path.join(log_dir, "expansion_history.txt")
                                    with open(log_file, "a", encoding="utf-8") as f:
                                        f.write(
                                            f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] PMID: {pmid} | Title: {title}\n")

                            st.session_state.expansion_idx += 1
                            st.toast(f"✅ 文献 {pmid} 融合成功！", icon="🎉")
                            redraw_and_update()
                            st.rerun()

                        elif btn_skip:
                            st.session_state.expansion_idx += 1
                            st.rerun()

                        # 🛠️ 修复点 3：删除了原先的 elif btn_stop 逻辑块，因为它的使命已经被回调函数安全地接管了

                    else:
                        st.success(f"✅ 队列中的 {total} 篇文献已全部处理完毕！图谱已是最新形态。")
                        # 💡 提示：这里为什么没报错？因为当任务跑完进入 else 分支时，上面的 if 分支没进，
                        # st.toggle 组件在当前运行中根本没有被实例化，所以在这里关闭开关是合法的！
                        if "auto_run_expansion" in st.session_state and st.session_state.auto_run_expansion:
                            st.session_state.auto_run_expansion = False

                        if st.button("🧹 清理队列与搜索结果", type="primary"):
                            st.session_state.expansion_queue = []
                            st.session_state.pubmed_search_results = []
                            st.rerun()