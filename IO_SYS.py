import os
import webbrowser
import pypdf
from pyvis.network import Network
import re
from pypdf import PdfReader

# =====================================================================
# 1. PDF 处理器类
# =====================================================================
import os
import webbrowser
import pypdf
from pyvis.network import Network
import re
from pypdf import PdfReader


# =====================================================================
# 1. PDF 处理器类 (双引擎增强版)
# =====================================================================
class PDFProcessor:
    def __init__(self, chunk_size=1200, overlap=200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def extract_chunks(self, pdf_path, start_page=0, end_page=None):
        """读取PDF指定页码范围并切块"""
        print(f"📄 [PDFProcessor] 正在读取文献: {pdf_path}")
        text = ""

        # 🌟 首选引擎：尝试使用容错率极高的 PyMuPDF (fitz)
        try:
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            if end_page is None or end_page > total_pages:
                end_page = total_pages

            print(f"📌 [PDFProcessor] (PyMuPDF引擎) 计划解析第 {start_page + 1} 页 到 第 {end_page} 页...")
            for page_num in range(start_page, end_page):
                page = doc[page_num]
                extracted = page.get_text()
                if extracted:
                    text += extracted + "\n"
            doc.close()

        except Exception as fitz_err:
            print(f"⚠️ [PDFProcessor] PyMuPDF 解析受阻，自动降级至 pypdf 引擎... ({fitz_err})")

            # 🌟 备用引擎：Fallback 回 pypdf
            try:
                with open(pdf_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    total_pages = len(reader.pages)

                    if end_page is None or end_page > total_pages:
                        end_page = total_pages

                    print(f"📌 [PDFProcessor] (pypdf引擎) 计划解析第 {start_page + 1} 页 到 第 {end_page} 页...")
                    for page_num in range(start_page, end_page):
                        page = reader.pages[page_num]
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
            except Exception as e:
                print(f"❌ [PDFProcessor] 双引擎读取均告失败: {e}")
                return []

        # 清理多余空格并切块
        text = " ".join(text.split())
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += (self.chunk_size - self.overlap)

        print(f"✅ [PDFProcessor] 文献切分完成，共 {len(chunks)} 个片段。")
        return chunks

    def get_raw_text(self, pdf_path, start_page, end_page):
        """直接获取指定页码的纯文本，不进行分块，用于寻找摘要"""
        text = ""
        # 摘要提取区同样配置双引擎
        try:
            import fitz
            doc = fitz.open(pdf_path)
            for i in range(start_page, min(end_page, len(doc))):
                text += doc[i].get_text() + "\n"
            doc.close()
        except Exception:
            try:
                reader = PdfReader(pdf_path)
                for i in range(start_page, min(end_page, len(reader.pages))):
                    text += reader.pages[i].extract_text() + "\n"
            except Exception as e:
                print(f"❌ [PDFProcessor] 获取原文本失败: {e}")
        return text

    def extract_abstract_regex(self, text):
        """第一道防线：正则捕获摘要 (中英双语增强版)"""
        pattern = re.compile(
            r'(?i)(?:abstract|summary|摘要)\s*[:：\.\n]*\s*(.*?)(?=(?:\n\s*keywords|\bintroduction\b|1\.\s*introduction|\bbackground\b|关键词|引言|背景|1\.\s*引言))',
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(text)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 50:
                return extracted
        return None



# =====================================================================
# 3. 图谱可视化类
# =====================================================================
class GraphVisualizer:
    def __init__(self, bgcolor="#1a1a1a", font_color="white"):
        self.bgcolor = bgcolor
        self.font_color = font_color

    def generate_html(self, global_entities, global_relations, output_file="bio_knowledge_graph.html",
                      show_shortcuts=False,
                      empower_ontology=False, alpha_ontology=0.5,
                      empower_node=False, beta_node=0.2,
                      empower_edge=False, gamma_edge=0.1,
                      output_lang="zh"):
        print(f"🎨 [GraphVisualizer] 正在绘制动态网络拓扑图...")
        from pyvis.network import Network
        from collections import Counter
        import os

        # 🌐 悬停面板双语词典
        is_en = "en" in output_lang.lower()
        lbl_std_name = "🏷️ Standard Name" if is_en else "🏷️ 标准名称"
        lbl_aliases = "📚 Aliases" if is_en else "📚 别名"
        lbl_source = "📄 Source" if is_en else "📄 来源文献"
        lbl_heat = "🔥 Overall Heat" if is_en else "🔥 综合热度"
        lbl_weight = "🔥 Merge Count" if is_en else "🔥 证据合并次数"
        lbl_times = "times" if is_en else "次"
        lbl_rel = "🔍 Relation Type" if is_en else "🔍 关系类型"
        lbl_evi = "📝 Evidence" if is_en else "📝 证据"
        lbl_doc_src = "📄 Source" if is_en else "📄 源自"
        lbl_shortcut = "⚠️ [AI judged as mechanism shortcut]" if is_en else "⚠️ [AI 判定为机制捷径]"

        # 🔥 绝杀修复 1 & 2：保持 CDN 和网络配置不变
        net = Network(
            height="750px",
            width="100%",
            bgcolor=self.bgcolor,
            font_color=self.font_color,
            directed=True,
            cdn_resources="remote"
        )
        net.force_atlas_2based()

        # ==========================================
        # 1. 构建超强的信息映射字典 (包含别名和来源)
        # ==========================================
        entity_info_map = {}
        for ent in global_entities:
            std_name = ent.get("standard_name", "未知实体")
            entity_info_map[std_name] = {
                "aliases": ent.get("aliases", []),
                "doc_source": ent.get("doc_source", "未知文献")
            }

        # ==========================================
        # 2. 🧮 赋权引擎 Phase 0：统计基础节点热度 (保留原有的 weight 机制)
        # ==========================================
        base_heat = Counter()
        for item in global_relations:
            weight = item.get("weight", 1)
            base_heat[item.get("source")] += weight
            base_heat[item.get("target")] += weight

        final_heat = Counter(base_heat)  # 创建快照字典，后续操作在此累加

        # ==========================================
        # 🌟 赋权引擎 Phase 1 & 2：本体聚合与互相辐射
        # ==========================================
        for item in global_relations:
            source = item.get("source")
            target = item.get("target")
            rel_type = item.get("relation", "相关")  # 注意这里使用原来的 key

            # 🛡️ 致命 Bug 修复：拦截自环线！
            if source == target:
                continue

            # 🛡️ 强转洗净捷径参数，判断该线是否被隐藏
            raw_shortcut = item.get("is_shortcut", False)
            is_shortcut = (str(raw_shortcut).lower() == "true") or (raw_shortcut is True)
            safe_show = (str(show_shortcuts).lower() == "true") or (show_shortcuts is True)
            is_hidden = is_shortcut and not safe_show

            # 【开关 A】：包含关系反哺 (父节点变大)
            if empower_ontology and rel_type == "包含":
                final_heat[target] += base_heat[source] * alpha_ontology

            # 【开关 B】：节点互相辐射 (普通连线两端互相做大，排除隐藏线和包含关系)
            if empower_node and rel_type != "包含" and not is_hidden:
                final_heat[source] += base_heat[target] * beta_node
                final_heat[target] += base_heat[source] * beta_node

        # ==========================================
        # 3. 🎨 统一绘制节点 (应用计算好的 final_heat)
        # ==========================================
        for std_name, info in entity_info_map.items():
            heat_val = final_heat[std_name]
            node_title = f"{lbl_std_name} {std_name}\n{lbl_aliases} {', '.join(info['aliases'])}\n{lbl_source} {info['doc_source']}\n{lbl_heat} {heat_val:.1f}"

            # 动态调整大小 (保留原有的缩放比例逻辑)
            node_size = 20 + heat_val * 3
            net.add_node(std_name, label=std_name, title=node_title, color="#4da6ff", size=node_size)

        # ==========================================
        # 4. 🎨 绘制关系连线 (保留所有防御与颜色逻辑，加入加粗引擎)
        # ==========================================
        for item in global_relations:
            source = item.get("source")
            target = item.get("target")

            # 🛡️ 再次拦截自环线
            if source == target:
                continue

            rel_type = item.get("relation", "相关")
            evidence = item.get("evidence", "无")
            doc_source = item.get("doc_source", "未知文献")


            # 🛡️ 终极安全强转 (保持原样)
            raw_shortcut = item.get("is_shortcut", False)
            is_shortcut = (str(raw_shortcut).lower() == "true") or (raw_shortcut is True)
            safe_show = (str(show_shortcuts).lower() == "true") or (show_shortcuts is True)

            # 拦截被隐藏的捷径
            if is_shortcut and not safe_show:
                continue

            # 🌟 基础连线宽度 (保留你原有的缩放系数)
            rel_weight = item.get("weight", 1)
            scale_factor = 0.5
            display_width = 1 + (rel_weight * scale_factor)

            # 🔗 【开关 C】：核心主干加粗 (高热度节点间的非包含线变粗)
            if empower_edge and rel_type != "包含":
                display_width += gamma_edge * (final_heat[source] + final_heat[target])

            # 🛡️ 防御性编程：幻觉节点探测 (保持原样)
            for node in [source, target]:
                if node not in entity_info_map:
                    net.add_node(node, label=node, color="#ff9999", size=20,
                                 title=f"⚠️ 模型幻觉节点\n📄 来源: {doc_source}")
                    entity_info_map[node] = {"aliases": [], "doc_source": doc_source}


            # 强化悬停提示框
            edge_title = f"{lbl_weight}: {rel_weight} {lbl_times}\n{lbl_rel}: {rel_type}\n{lbl_evi}: {evidence}\n{lbl_doc_src}: {doc_source}"

            if is_shortcut:
                edge_title = f"{lbl_shortcut}\n" + edge_title

            # ==========================================
            # 🎨 视觉分支判断：保持你原有的颜色、虚线与箭头处理
            # ==========================================
            shortcut_color = "#555555"
            force_dashed = True if is_shortcut else False

            if rel_type == "正作用":
                final_color = shortcut_color if is_shortcut else "#00ff00"
                net.add_edge(source, target, title=edge_title, color=final_color, arrows="to",
                             width=display_width, dashes=force_dashed)

            elif rel_type == "负作用":
                final_color = shortcut_color if is_shortcut else "#ff3333"
                net.add_edge(source, target, title=edge_title, color=final_color, arrows="to",
                             width=display_width + 1, dashes=force_dashed)

            elif rel_type == "包含":
                final_color = shortcut_color if is_shortcut else "#9b59b6"
                net.add_edge(source, target, title=edge_title, color=final_color, arrows="to",
                             width=display_width, dashes=force_dashed)

            else:
                final_color = shortcut_color if is_shortcut else "#aaaaaa"
                net.add_edge(source, target, title=edge_title, color=final_color, arrows="",
                             dashes=True, width=display_width)

        net.save_graph(output_file)
        print(f"✨ [GraphVisualizer] 拓扑图已成功保存至: {output_file}")
