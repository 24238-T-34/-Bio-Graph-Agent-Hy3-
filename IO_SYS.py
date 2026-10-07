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

    def extract_figures(self, pdf_path, start_page=0, end_page=None, mode="off", keyword="", min_size=200):
        """
        从选定页码中提取目标插图及关联图注
        :param mode: 'off' | 'match' | 'all'
        :param keyword: 精准匹配词（如 'Fig 4', 'Figure 2', 'pathway'）
        :param min_size: 最小像素宽高过滤阀值，避免图标与分割线
        :return: List[dict] [{'image_bytes': b'...', 'ext': 'png', 'page': 5, 'caption': '...', 'label': 'Fig 4'}]
        """
        if mode == "off" or not os.path.exists(pdf_path):
            return []

        matched_figures = []
        try:
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            if end_page is None or end_page > total_pages:
                end_page = total_pages

            kw_clean = keyword.strip() if keyword else ""
            # 模式 2：精准匹配
            if mode == "match" and kw_clean:
                # 智能识别数字编号（如 "Fig 4", "Fig. 4", "Figure 4", "4"）或普通关键词（如 "pathway"）
                kw_num_match = re.search(r"(?:fig(?:ure)?\.?\s*)?(\d+[a-zA-Z]?)", kw_clean, re.IGNORECASE)
                if kw_num_match and kw_num_match.group(1):
                    fig_num = kw_num_match.group(1)
                    pattern_str = rf"(?:fig(?:ure)?\.?\s*{re.escape(fig_num)}\b|{re.escape(kw_clean)})"
                else:
                    pattern_str = re.escape(kw_clean)

                kw_pattern = re.compile(pattern_str, re.IGNORECASE)

                for page_idx in range(start_page, end_page):
                    page = doc[page_idx]
                    page_num = page_idx + 1
                    page_text = page.get_text()

                    captions = list(kw_pattern.finditer(page_text))
                    is_single_page = (total_pages == 1)
                    if captions or is_single_page:
                        matched_caption = captions[0].group(0).strip() if captions else (kw_clean or f"Page {page_num} Diagram")
                        img_list = page.get_images()
                        for img_info in img_list:
                            xref = img_info[0]
                            base_img = doc.extract_image(xref)
                            w, h = base_img["width"], base_img["height"]
                            if (w >= min_size and h >= min_size) or (w * h >= 60000):
                                matched_figures.append({
                                    "image_bytes": base_img["image"],
                                    "ext": base_img["ext"],
                                    "page": page_num,
                                    "caption": matched_caption,
                                    "label": kw_clean or f"Page{page_num}_Fig"
                                })
                                break

                        # 💡 矢量通路图/单页海报兜底：若命中了关键词或为单页海报，但未找到光栅位图，且页面包含矢量绘图
                        if not matched_figures and (len(page.get_drawings()) >= 10 or is_single_page):
                            print(f"📐 [PDFProcessor] 页面 {page_num} 检测到矢量绘图 ({len(page.get_drawings())} 个路径)，自动执行 150-DPI 高清机制图渲染...")
                            pix = page.get_pixmap(dpi=150)
                            matched_figures.append({
                                "image_bytes": pix.tobytes("png"),
                                "ext": "png",
                                "page": page_num,
                                "caption": matched_caption,
                                "label": kw_clean or f"Page{page_num}_VectorFig"
                            })

                        if matched_figures:
                            break

            # 模式 3：全开模式 (过滤掉微型图标和公式位图)
            elif mode == "all":
                for page_idx in range(start_page, end_page):
                    page = doc[page_idx]
                    page_num = page_idx + 1
                    img_list = page.get_images()
                    found_raster = False
                    for idx, img_info in enumerate(img_list):
                        xref = img_info[0]
                        base_img = doc.extract_image(xref)
                        w, h = base_img["width"], base_img["height"]
                        if (w >= min_size and h >= min_size) or (w * h >= 60000):
                            matched_figures.append({
                                "image_bytes": base_img["image"],
                                "ext": base_img["ext"],
                                "page": page_num,
                                "caption": f"Page {page_num} Figure {idx + 1}",
                                "label": f"Page{page_num}_Fig{idx + 1}"
                            })
                            found_raster = True

                    # 💡 矢量机制图/单页海报兜底：若本页无符合尺寸的光栅图，但包含显著矢量绘图或为单页海报
                    if not found_raster and (len(page.get_drawings()) >= 20 or total_pages == 1):
                        print(f"📐 [PDFProcessor] 页面 {page_num} 检测到矢量绘图 ({len(page.get_drawings())} 个路径)，自动执行 150-DPI 高清机制图渲染...")
                        pix = page.get_pixmap(dpi=150)
                        matched_figures.append({
                            "image_bytes": pix.tobytes("png"),
                            "ext": "png",
                            "page": page_num,
                            "caption": f"Page {page_num} 机制通路图 (矢量渲染)",
                            "label": f"Page{page_num}_VectorFig"
                        })

            doc.close()
        except Exception as e:
            print(f"⚠️ [PDFProcessor] 机制图提取遇到异常: {e}")

        return matched_figures


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


# =====================================================================
# 3. 文献学术标题提取与安全命名工具集
# =====================================================================
def sanitize_paper_filename(name: str, max_len: int = 160) -> str:
    """过滤操作系统非法字符并规范化学术文献文件名"""
    if not name:
        return ""
    # 替换 Windows / Linux / macOS 文件系统非法字符
    clean = re.sub(r'[\\/*?:"<>|]', " - ", str(name))
    # 规范化多余空白与连字符
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = clean.strip(" ._-")
    # 长度截断控制（避免文件名超长无法保存，尽量在完整单词处截断）
    if len(clean) > max_len:
        truncated = clean[:max_len]
        if " " in truncated:
            clean = truncated.rsplit(" ", 1)[0]
        else:
            clean = truncated
    return clean.strip(" ._-")


def extract_paper_title_and_pmid(pdf_path: str, max_pages: int = 3, agent=None):
    """
    智能提取文献的真实学术标题与 PMID
    流水线策略：
    1. 前 1~3 页扫描 PMID / DOI -> 优先联网查询 PubMed 官方权威标题；
    2. 若未检索到 -> 解析第 1 页至第 3 页排版（最大字号与逐句后读），提取候选标题；
    3. 若提供了大模型 agent -> 调用大模型进行深度学术审校过滤噪音；
    4. 所有兜底失败时返回 None。
    :return: (sanitized_title, pmid_str, method_tag)
    """
    if not os.path.exists(pdf_path):
        return None, None, "file_not_found"

    doc = None
    page_texts = []
    try:
        import fitz
        doc = fitz.open(pdf_path)
        scan_pages = min(max_pages, len(doc))
        for pno in range(scan_pages):
            page_texts.append(doc[pno].get_text())
    except Exception as e:
        # Fallback to pypdf
        try:
            reader = PdfReader(pdf_path)
            scan_pages = min(max_pages, len(reader.pages))
            for pno in range(scan_pages):
                page_texts.append(reader.pages[pno].extract_text() or "")
        except Exception:
            if doc:
                doc.close()
            return None, None, "pdf_open_error"

    combined_text = "\n".join(page_texts)

    # ----------------------------------------------------
    # 阶段一：识别 PMID 与 DOI 并尝试 PubMed 官方权威检索
    # ----------------------------------------------------
    pmid = None
    pmid_m = re.search(r"\b(?:PMID|PubMed\s*(?:ID)?)[:\s#]*(\d{6,9})\b", combined_text, re.I)
    if not pmid_m:
        # 兼容文件名自带 PMID 的情况 (如 PMID_12345678.pdf 或 12345678.pdf)
        pmid_m = re.search(r"(?:pmid[_\-\s:]*)?(\d{6,9})", os.path.basename(pdf_path), re.I)
    if pmid_m:
        pmid = pmid_m.group(1)

    doi = None
    doi_m = re.search(r"\b(?:doi\.org/|doi:\s*)(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", combined_text, re.I)
    if doi_m:
        doi = doi_m.group(1).rstrip(" .;")

    if pmid:
        try:
            from WebSearcher import PubMedSearcher
            ps = PubMedSearcher()
            res = ps.session.get(f"{ps.base_url}esummary.fcgi", params={
                "db": "pubmed", "id": str(pmid), "retmode": "json", "email": ps.email
            }, timeout=6).json()
            t_official = res.get("result", {}).get(str(pmid), {}).get("title")
            if t_official:
                clean_t = sanitize_paper_filename(t_official.rstrip("."))
                if clean_t and len(clean_t) >= 6:
                    if doc:
                        doc.close()
                    return clean_t, pmid, "pubmed_pmid"
        except Exception as err:
            print(f"⚠️ [extract_paper_title] PMID 在线检索受阻: {err}")

    if doi:
        try:
            from WebSearcher import PubMedSearcher
            ps = PubMedSearcher()
            res = ps.search_articles(doi, max_results=1)
            if res and res[0].get("title"):
                clean_t = sanitize_paper_filename(res[0]["title"].rstrip("."))
                ret_pmid = res[0].get("pmid") or pmid
                if clean_t and len(clean_t) >= 6:
                    if doc:
                        doc.close()
                    return clean_t, ret_pmid, "pubmed_doi"
        except Exception as err:
            print(f"⚠️ [extract_paper_title] DOI 在线检索受阻: {err}")

    # ----------------------------------------------------
    # 阶段二：排版字体块分析 (Font Span 与逐句后读)
    # ----------------------------------------------------
    blacklist = [
        r"^(?:https?://|www\.)",
        r"^(?:doi:|issn:|isbn:)",
        r"^(?:volume|vol\.|issue|no\.|pages?|pp\.)\b",
        r"^(?:received|accepted|published|revised)[:\s]",
        r"^(?:copyright|©|all rights reserved|open access|creative commons)",
        r"^(?:article|research article|review article|review|brief report|short communication|perspective|editorial)\b",
        r"^(?:abstract|summary|graphical abstract|highlights|keywords|introduction)\b",
        r"^\d{1,4}$",
    ]

    candidate_title = ""

    if doc:
        try:
            scan_pages = min(max_pages, len(doc))
            for pno in range(scan_pages):
                page = doc[pno]
                blocks = page.get_text("dict").get("blocks", [])
                candidate_blocks = []
                for b in blocks:
                    if "lines" not in b:
                        continue
                    block_text = ""
                    sizes = []
                    for line in b["lines"]:
                        line_str = "".join([span.get("text", "") for span in line.get("spans", [])]).strip()
                        if line_str:
                            block_text += line_str + " "
                            sizes.extend([span.get("size", 10.0) for span in line.get("spans", [])])
                    block_text = block_text.strip()
                    if block_text and sizes:
                        candidate_blocks.append((max(sizes), block_text))

                candidate_blocks.sort(key=lambda x: x[0], reverse=True)
                for max_sz, btext in candidate_blocks:
                    b_low = btext.lower()
                    if len(b_low) < 6:
                        continue
                    is_junk = False
                    for bp in blacklist:
                        if re.search(bp, b_low):
                            is_junk = True
                            break
                    if not is_junk and 10 <= len(btext) <= 350 and "@" not in btext:
                        candidate_title = btext.rstrip(".")
                        break
                if candidate_title:
                    break
        except Exception as e:
            print(f"⚠️ [extract_paper_title] 排版字号分析出错: {e}")
        finally:
            doc.close()

    # 兜底逐句后读（针对无结构字体信息的文本）
    if not candidate_title and page_texts:
        for p_txt in page_texts:
            lines = [l.strip() for l in p_txt.split("\n") if l.strip()]
            for l in lines:
                l_low = l.lower()
                if len(l) < 10 or len(l) > 300:
                    continue
                is_junk = any(re.search(bp, l_low) for bp in blacklist)
                if not is_junk and "@" not in l and not l.isdigit():
                    candidate_title = l.rstrip(".")
                    break
            if candidate_title:
                break

    # ----------------------------------------------------
    # 阶段三：大模型审核 (若提供了 agent)
    # ----------------------------------------------------
    if agent and hasattr(agent, "review_paper_title"):
        try:
            reviewed = agent.review_paper_title(combined_text[:3000], candidate_title)
            if reviewed and len(reviewed) >= 6:
                clean_reviewed = sanitize_paper_filename(reviewed)
                if clean_reviewed:
                    return clean_reviewed, pmid, "llm_reviewed"
        except Exception as err:
            print(f"⚠️ [extract_paper_title] 大模型审校异常: {err}")

    # ----------------------------------------------------
    # 阶段四：启发式候选与全链路兜底判定
    # ----------------------------------------------------
    if candidate_title and len(candidate_title) >= 8:
        clean_cand = sanitize_paper_filename(candidate_title)
        if clean_cand:
            return clean_cand, pmid, "heuristic"

    return None, pmid, "unrecognized"

