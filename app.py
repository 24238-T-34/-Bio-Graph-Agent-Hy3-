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

        # 智能提示：告诉用户当前库里有没有东西
        if append_mode and len(st.session_state.master_entities) > 0:
            st.info(f"📦 记忆库就绪：当前已有 {len(st.session_state.master_entities)} 个节点。新知识将与之融合！")
        elif not append_mode and len(st.session_state.master_entities) > 0:
            st.warning("⚠️ 注意：关闭追加模式，将会【清空】现有图谱，从零开始！历史文献也会清空")

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
                    source_name=uploaded_file.name
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

    # 🛡️ 渲染图谱
    components.html(st.session_state.html_data, height=800, scrolling=True)

# ==========================================
# 💡 核心修复 2：在所有解析逻辑跑完后，如果有数据，就用真按钮替换假按钮
# ==========================================
# 🛡️ 增加门卫：只有当记忆库里真的有实体数据时，才执行替换！
if len(st.session_state.master_entities) > 0:
    with export_placeholder:
        project_data = {
            "version": "1.0",
            "entities": st.session_state.master_entities,
            "relations": st.session_state.master_relations,
            "analyzed_files": st.session_state.analyzed_files
        }
        json_bytes = json.dumps(project_data, ensure_ascii=False).encode('utf-8')

        # 使用真正的下载按钮覆盖那个假按钮
        # ⚠️ 这里最好加上 key="real_export_btn"，与假按钮彻底区分
        st.download_button(
            label="📤 导出工程 (.biokg)",
            data=json_bytes,
            file_name="我的图谱工程.biokg",
            mime="application/json",
            use_container_width=True,
            key="real_export_btn"
        )