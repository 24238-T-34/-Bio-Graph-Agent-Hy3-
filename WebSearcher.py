import requests
import xml.etree.ElementTree as ET
import time


class PubMedSearcher:
    def __init__(self, email="zouyuhandd@126.com"):
        """
        初始化 PubMed 搜索器。
        NCBI 官方建议提供一个邮箱，以防并发过高时能联系到开发者。
        """
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.email = email
        self.session = requests.Session()  # 使用 Session 保持连接，提升请求速度

    def search_articles(self, query: str, max_results: int = 10):
        """
        根据检索词搜索 PubMed，返回前 N 篇文献的元数据（标题、年份、作者、DOI、PMID）
        """
        print(f"🔍 [WebSearcher] 正在 PubMed 中搜索: {query} ...")

        # 第一步：调用 esearch 获取文献的 PMID 列表
        search_url = f"{self.base_url}esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results,
            "email": self.email
        }

        try:
            search_res = self.session.get(search_url, params=search_params, timeout=10).json()
            pmids = search_res.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                print("⚠️ [WebSearcher] 未找到相关文献。")
                return []

            # 第二步：调用 esummary，根据这些 PMID 批量获取文献详细信息（标题、作者等）
            summary_url = f"{self.base_url}esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
                "email": self.email
            }

            summary_res = self.session.get(summary_url, params=summary_params, timeout=10).json()
            results = []

            for pmid in pmids:
                doc_info = summary_res.get("result", {}).get(pmid, {})
                title = doc_info.get("title", "未知标题")
                pubdate = doc_info.get("pubdate", "未知年份")

                # 提取作者
                authors_list = doc_info.get("authors", [])
                authors = ", ".join([a.get("name", "") for a in authors_list]) if authors_list else "未知作者"

                # 提取 DOI
                doi = ""
                for aid in doc_info.get("articleids", []):
                    if aid.get("idtype") == "doi":
                        doi = aid.get("value")
                        break

                results.append({
                    "pmid": pmid,
                    "title": title,
                    "year": pubdate[:4],  # 只取年份
                    "authors": authors,
                    "doi": doi
                })

            print(f"✅ [WebSearcher] 成功抓取到 {len(results)} 篇文献元数据。")
            return results

        except Exception as e:
            print(f"❌ [WebSearcher] 搜索 API 请求失败: {e}")
            return []

    def fetch_abstract(self, pmid: str):
        """
        根据指定的 PMID，抓取完整的文献摘要文本。
        NCBI 的 efetch 抓取摘要最好用 XML 格式解析。
        """
        # print(f"📥 [WebSearcher] 正在下载摘要 (PMID: {pmid})...")
        fetch_url = f"{self.base_url}efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "email": self.email
        }

        try:
            res = self.session.get(fetch_url, params=fetch_params, timeout=15)
            # 解析 XML
            root = ET.fromstring(res.content)

            # PubMed 的摘要通常在 <AbstractText> 标签里，有时会分为 Background, Methods 等多段
            abstract_texts = root.findall(".//AbstractText")

            if not abstract_texts:
                return "无可用摘要 (No abstract available)。"

            # 将多段摘要拼接到一起
            full_abstract = " ".join([t.text for t in abstract_texts if t.text])
            return full_abstract

        except Exception as e:
            print(f"❌ [WebSearcher] 摘要抓取失败 (PMID: {pmid}): {e}")
            return ""


# ==========================================
# 🧪 本地直接运行测试 (Test Block)
# ==========================================
if __name__ == "__main__":
    searcher = PubMedSearcher()

    # 1. 测试搜索列表
    test_query = "(\"Akt\"[Title/Abstract]) AND (\"Gastric Cancer\"[Title/Abstract])"
    articles = searcher.search_articles(test_query, max_results=3)

    print("\n--- 检索到的前 3 篇文献 ---")
    for idx, art in enumerate(articles):
        print(f"{idx + 1}. [{art['year']}] {art['title']} (PMID: {art['pmid']})")

    # 2. 测试抓取第一篇摘要
    if articles:
        first_pmid = articles[0]["pmid"]
        print(f"\n--- 正在抓取 PMID: {first_pmid} 的摘要 ---")
        abstract = searcher.fetch_abstract(first_pmid)
        print(abstract)