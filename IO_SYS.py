import os
import webbrowser
import PyPDF2
from pyvis.network import Network
import re
from PyPDF2 import PdfReader

# =====================================================================
# 1. PDF 处理器类
# =====================================================================
class PDFProcessor:
    def __init__(self, chunk_size=1200, overlap=200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def extract_chunks(self, pdf_path, start_page=0, end_page=None):
        """读取PDF指定页码范围并切块"""
        print(f"📄 [PDFProcessor] 正在读取文献: {pdf_path}")
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)

                # 如果没有指定结束页，或者结束页越界，则默认读到最后一页
                if end_page is None or end_page > total_pages:
                    end_page = total_pages

                print(f"📌 [PDFProcessor] 计划解析第 {start_page + 1} 页 到 第 {end_page} 页...")

                # 只遍历用户选择的页码范围
                for page_num in range(start_page, end_page):
                    page = reader.pages[page_num]
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            print(f"❌ [PDFProcessor] 读取 PDF 失败: {e}")
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
        reader = PdfReader(pdf_path)
        text = ""
        for i in range(start_page, min(end_page, len(reader.pages))):
            text += reader.pages[i].extract_text() + "\n"
        return text

    def extract_abstract_regex(self, text):
        """第一道防线：正则捕获摘要 (中英双语增强版)"""
        # 正则逻辑：
        # 1. 匹配起始词：Abstract, Summary, 或 摘要 (忽略大小写)
        # 2. 匹配分隔符：允许出现中英文冒号、句号、换行符和空格
        # 3. 截取正文：(.*?)
        # 4. 停止边界：遇到 Keywords, Introduction, Background, 关键词, 引言, 背景 时停止提取
        pattern = re.compile(
            r'(?i)(?:abstract|summary|摘要)\s*[:：\.\n]*\s*(.*?)(?=(?:\n\s*keywords|\bintroduction\b|1\.\s*introduction|\bbackground\b|关键词|引言|背景|1\.\s*引言))',
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(text)
        if match:
            # 如果匹配到的内容大于 50 个字符，才认为是有效提取
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

    def generate_html(self, global_entities, global_relations, output_file="bio_knowledge_graph.html"):
        print(f"🎨 [GraphVisualizer] 正在绘制动态网络拓扑图...")
        from pyvis.network import Network
        from collections import Counter
        import os

        # 🔥 绝杀修复 1：去除 notebook=True，恢复标准的网页结构
        # 🔥 绝杀修复 2：使用 remote CDN，让生成的 HTML 只有区区几十KB，极大减轻 Streamlit 负担
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
        # 2. 统计节点热度 (用于动态调整节点大小)
        # ==========================================
        node_heat = Counter()
        for item in global_relations:
            # 🌟 修改：不再盲目 +1，而是读取合并后该通路真实拥有的热度权重
            weight = item.get("weight", 1)
            node_heat[item.get("source")] += weight
            node_heat[item.get("target")] += weight

        # ==========================================
        # 🔥 绝杀修复 3：先统一、去重地添加所有实体节点
        # ==========================================
        for std_name, info in entity_info_map.items():
            node_title = f"🏷️ 标准名称: {std_name}\n📚 别名: {', '.join(info['aliases'])}\n📄 来源文献: {info['doc_source']}"
            node_size = 20 + node_heat[std_name] * 3
            # 一次性添加所有合法节点，杜绝重复渲染导致的 JS 崩溃
            net.add_node(std_name, label=std_name, title=node_title, color="#4da6ff", size=node_size)

        # ==========================================
        # 3. 再绘制关系连线
        # ==========================================
        for item in global_relations:
            source = item.get("source")
            target = item.get("target")
            rel_type = item.get("relation", "相关")
            evidence = item.get("evidence", "无")
            doc_source = item.get("doc_source", "未知文献")

            # 🌟 提取连线被提及的真实热度权重
            rel_weight = item.get("weight", 1)

            # 💡 核心视觉优化：加入缩放系数
            # 设定基础粗细为 1，每次热度增加只变粗 0.5 (你可以自由把 0.5 调成 0.3 或 0.2)
            scale_factor = 0.5
            display_width = 1 + (rel_weight * scale_factor)

            # 🛡️ 防御性编程 (保持原样)
            for node in [source, target]:
                if node not in entity_info_map:
                    net.add_node(node, label=node, color="#ff9999", size=20,
                                 title=f"⚠️ 模型幻觉节点\n📄 来源: {doc_source}")
                    entity_info_map[node] = {"aliases": [], "doc_source": doc_source}

            # 强化悬停提示框
            edge_title = f"🔥 证据热度: {rel_weight} 次提及\n🔍 关系类型: {rel_type}\n📝 证据: {evidence}\n📄 源自: {doc_source}"

            # 🌟 绝杀修改：把原来的 value 替换为受到公式严格控制的 width！
            if rel_type == "正作用":
                net.add_edge(source, target, title=edge_title, color="#00ff00", arrows="to", width=display_width)
            elif rel_type == "负作用":
                # 负作用本身就是重点，让它的基础粗细稍微再多 1 个像素
                net.add_edge(source, target, title=edge_title, color="#ff3333", arrows="to",
                             width=display_width + 1)
            else:
                net.add_edge(source, target, title=edge_title, color="#aaaaaa", dashes=True, width=display_width)

        net.save_graph(output_file)
        print(f"✨ [GraphVisualizer] 拓扑图已成功保存至: {output_file}")

