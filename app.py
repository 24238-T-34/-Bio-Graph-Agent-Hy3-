import streamlit as st
import tempfile
import os
from PyPDF2 import PdfReader
from back_logic import BioGraphPipeline,GraphVisualizer
import streamlit.components.v1 as components
import gc
import fitz  # 🚀 优化：把 PyMuPDF 移到文件顶部，规范代码结构
import json
import pandas as pd


# ==========================================
# 页面全局配置
# ==========================================
st.set_page_config(page_title="Bio-Graph Agent", page_icon="🧬", layout="wide")
st.title("🧬 混元 Hy3 生物知识图谱自动生成引擎")
st.markdown("---")

# 初始化全局图谱记忆中枢
if "master_entities" not in st.session_state:
    st.session_state.master_entities = []
if "master_relations" not in st.session_state:
    st.session_state.master_relations = []

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
            st.warning("⚠️ 注意：关闭追加模式，将会【清空】现有图谱，从零开始！")

        # 🔥 智能页码联动：开启摘要模式默认只切 1-2 页；关闭则默认加载全文
        default_end = min(2, total_pages) if is_summary_only else total_pages

        st.markdown("#### 🎯 设定解析范围")
        col_inputs1, col_inputs2 = st.columns(2)
        with col_inputs1:
            start_page = st.number_input("起始页码", min_value=1, max_value=total_pages, value=1)
        with col_inputs2:
            end_page = st.number_input("结束页码", min_value=start_page, max_value=total_pages, value=default_end)

        # 摘要模式下的安全阈值温柔提示
        if is_summary_only and (end_page - start_page > 2):
            st.warning("💡 提示：摘要通常在文献前两页。为了保证极速提取，建议缩小页码范围！")

        st.divider()
        # 核心启动按钮：移至左侧最下方，拉宽加大，极其醒目
        start_button = st.button("🚀 开始解析 & 生成图谱", use_container_width=True, type="primary")

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
# 核心引擎触发与结果渲染区（全览画布排版）
# ==========================================
if uploaded_file and start_button:
    if not api_key:
        st.error("请先在左侧输入 API Key！")
    else:
        # 渲染在双栏下方，让最终的巨幅知识图谱能占满整张屏幕，视觉极其震撼
        st.markdown("---")
        with st.spinner(f"🧠 智能体正在解析第 {start_page} 到 {end_page} 页..."):
            try:
                # 实例化 Pipeline 并传入动态模型
                pipeline = BioGraphPipeline(api_key=api_key, model=selected_model_id)

                # 1. 跑当前这篇文献，拿到新数据
                new_entities, new_relations = pipeline.run(
                    tmp_path,
                    start_page=start_page - 1,
                    end_page=end_page,
                    is_summary_only=is_summary_only,
                    use_reflection=use_reflection
                )

                # 🔥 核心升级 3：跨文献智能对齐与融合 (Entity Alignment)
                if append_mode and len(st.session_state.master_entities) > 0:
                    with st.spinner("🔗 正在进行跨文献 AI 语义对齐与图谱融合..."):
                        # 1. 呼叫大模型裁判，获取同义词映射表 (如: {"TP53": "p53"})
                        alignment_map = pipeline.agent.align_global_entities(
                            st.session_state.master_entities,
                            new_entities
                        )

                        if alignment_map:
                            st.success(f"🧬 AI 识别到 {len(alignment_map)} 个跨文献同义实体，正在自动打通图谱脉络！")

                        # 2. 遍历新实体，执行融合手术
                        aligned_new_entities = []
                        for new_ent in new_entities:
                            new_name = new_ent.get("standard_name")

                            # 如果这个新实体其实是旧知识库里的某个实体
                            if new_name in alignment_map:
                                master_name = alignment_map[new_name]

                                # 去全局记忆库里把本体找出来，更新它的属性
                                for master_ent in st.session_state.master_entities:
                                    if master_ent.get("standard_name") == master_name:
                                        # 💡 完善版：不仅把新实体的标准名变成别名，还要把新实体自带的别名全盘接收！
                                        aliases = master_ent.setdefault("aliases", [])

                                        # 1. 新本体变成别名
                                        if new_name not in aliases:
                                            aliases.append(new_name)

                                        # 2. 接收新实体附带的所有其他别名
                                        for new_alias in new_ent.get("aliases", []):
                                            if new_alias not in aliases and new_alias != master_name:
                                                aliases.append(new_alias)

                                        # 拼接多篇文献来源！(例如: "a.pdf | b.pdf")
                                        old_source = master_ent.get("doc_source", "")
                                        new_source = new_ent.get("doc_source", "")
                                        if new_source and new_source not in old_source:
                                            master_ent["doc_source"] = f"{old_source} | {new_source}"
                                        break
                            else:
                                # 如果大模型认为这是一个完全没见过的新实体，则保留
                                aligned_new_entities.append(new_ent)

                        # 3. 移花接木：将新文献抽出的【关系网】强行接入全局标准节点
                        for rel in new_relations:
                            # 替换起点
                            if rel.get("source") in alignment_map:
                                rel["source"] = alignment_map[rel["source"]]
                            # 替换终点
                            if rel.get("target") in alignment_map:
                                rel["target"] = alignment_map[rel["target"]]

                        # 4. 将处理后的“干净”数据并入全局中枢
                        st.session_state.master_entities.extend(aligned_new_entities)
                        st.session_state.master_relations.extend(new_relations)

                elif append_mode:
                    # 如果是第一次运行，直接写入记忆库
                    st.session_state.master_entities.extend(new_entities)
                    st.session_state.master_relations.extend(new_relations)
                else:
                    # 如果未开启追加，直接覆盖清洗
                    st.session_state.master_entities = new_entities
                    st.session_state.master_relations = new_relations

                # 🔥 核心修正：先实例化你的绘图类，再调用它的绘图方法，彻底解决 AttributeError！
                visualizer = GraphVisualizer()
                html_file = "bio_knowledge_graph.html"
                visualizer.generate_html(
                    st.session_state.master_entities,
                    st.session_state.master_relations,
                    output_file=html_file
                )

                if os.path.exists(html_file):
                    st.success("🎉 图谱生成与数据融合成功！")
                    with open(html_file, "r", encoding="utf-8") as f:
                        html_data = f.read()

                    # ==========================================
                    # 📥 结果多元化导出下载区（全部换成 master 记忆库数据）
                    # ==========================================
                    st.markdown("### 📥 4. 知识图谱结果导出")

                    # 1. 转换数据为标准 JSON 格式 (读取 master)
                    entities_json = json.dumps(st.session_state.master_entities, ensure_ascii=False, indent=2)
                    relations_json = json.dumps(st.session_state.master_relations, ensure_ascii=False, indent=2)

                    # 2. 转换数据为 CSV 格式 (读取 master)
                    df_entities = pd.DataFrame(st.session_state.master_entities)
                    if 'aliases' in df_entities.columns:
                        df_entities['aliases'] = df_entities['aliases'].apply(
                            lambda x: ", ".join(x) if isinstance(x, list) else x)
                    csv_entities = df_entities.to_csv(index=False).encode('utf-8')

                    df_relations = pd.DataFrame(st.session_state.master_relations)
                    csv_relations = df_relations.to_csv(index=False).encode(
                        'utf-8') if not df_relations.empty else b""

                    # 3. 创建 4 横列并排排版的精美下载按钮
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                    with btn_col1:
                        st.download_button(
                            label="📄 导出实体 (JSON)",
                            data=entities_json,
                            file_name="bio_entities_merged.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    with btn_col2:
                        st.download_button(
                            label="📊 导出实体 (CSV)",
                            data=csv_entities,
                            file_name="bio_entities_merged.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with btn_col3:
                        st.download_button(
                            label="🔗 导出关系 (CSV)",
                            data=csv_relations,
                            file_name="bio_relations_merged.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    with btn_col4:
                        st.download_button(
                            label="🕸️ 导出交互图谱 (HTML)",
                            data=html_data,
                            file_name="bio_knowledge_graph_merged.html",
                            mime="text/html",
                            use_container_width=True
                        )

                    st.markdown("---")  # 分割线，下方展示全宽交互画布

                    # 🛡️ 使用专用组件渲染交互图谱
                    components.html(html_data, height=800, scrolling=True)

                    # 🛡️ 阅后即焚，释放内存
                    del html_data
                    gc.collect()
                else:
                    st.error("❌ 图谱文件未生成。")
            except Exception as e:
                st.error(f"处理过程中发生错误：{e}")