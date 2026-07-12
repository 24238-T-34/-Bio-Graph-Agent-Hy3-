import requests
import xml.etree.ElementTree as ET
import time
import re



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


class SemanticScholarSearcher:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper"
        self.session = requests.Session()

        # 🛡️ 伪装术：换上真实的 Chrome 浏览器身份，摆脱 python-requests 的原罪
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json"
        })
        self.abstract_cache = {}

    def _clean_query(self, query: str):
        q = re.sub(r'\[.*?\]', '', query)
        q = q.replace('(', '').replace(')', '').replace('"', '')
        q = q.replace(' AND ', ' ').replace(' OR ', ' ').replace(' NOT ', ' ')
        q = re.sub(r'\s+', ' ', q).strip()
        return q

    def search_articles(self, query: str, max_results: int = 10):
        clean_q = self._clean_query(query)
        print(f"🔍 [WebSearcher] S2 正在查询: {clean_q} ...")

        search_url = f"{self.base_url}/search"
        params = {
            "query": clean_q,
            "limit": max_results,
            "fields": "title,year,authors,externalIds,abstract,tldr"
        }

        try:
            res = None
            # 延长退避时间，给服务器喘息的空间
            for attempt in range(3):
                res = self.session.get(search_url, params=params, timeout=10)
                if res.status_code == 200:
                    break
                if res.status_code == 429:
                    wait_time = 2.0 * (attempt + 1)
                    print(f"⚠️ [API 限流] 触发 S2 限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    break

            # 🚀 降级触发点：如果重试 3 次还是 429，抛出异常，让外部切回 PubMed！
            if res.status_code == 429:
                raise Exception("Semantic Scholar 限流过于严重。")

            if res.status_code != 200:
                print(f"⚠️ [WebSearcher] S2 API 异常: {res.status_code}")
                return []

            data = res.json().get("data", [])
            if not data:
                return []

            results = []
            for item in data:
                authors_list = item.get("authors", [])
                authors = ", ".join([a.get("name", "") for a in authors_list[:3]])
                if len(authors_list) > 3:
                    authors += " et al."
                elif not authors_list:
                    authors = "未知作者"

                doi = item.get("externalIds", {}).get("DOI", "")
                paper_id = item.get("paperId")

                abstract = item.get("abstract", "")
                if not abstract and item.get("tldr"):
                    abstract = f"[AI 极简摘要] {item['tldr'].get('text', '')}"

                self.abstract_cache[paper_id] = abstract if abstract else "无可用摘要。"

                results.append({
                    "pmid": paper_id,
                    "title": item.get("title", "未知标题"),
                    "year": str(item.get("year", "未知年份")),
                    "authors": authors,
                    "doi": doi
                })
            return results

        except Exception as e:
            # 向外抛出特定错误，触发 PubMed 兜底机制
            print(f"❌ [WebSearcher] S2 检索彻底失败: {e}")
            raise e

    def fetch_abstract(self, pmid: str):
        return self.abstract_cache.get(pmid, "无可用摘要。")


# ==========================================
# 🚀 统一路由工厂 (带智能降级兜底)
# ==========================================
# 我们在外部包装一个代理类，来实现无缝降级！
class SmartSearchRouter:
    def __init__(self, preferred_db="PubMed"):
        self.preferred_db = preferred_db
        self.pubmed = PubMedSearcher()
        self.s2 = SemanticScholarSearcher()
        self.current_engine = self.s2 if "Semantic Scholar" in preferred_db else self.pubmed

    def search_articles(self, query: str, max_results: int = 10):
        try:
            # 尝试用首选引擎搜索
            return self.current_engine.search_articles(query, max_results)
        except Exception as e:
            if self.current_engine == self.s2:
                print("🔄 [容灾系统] Semantic Scholar 崩溃或限流，正在紧急自动降级至 PubMed 检索！")
                self.current_engine = self.pubmed  # 永久切换本轮实例的引擎为 PubMed
                return self.current_engine.search_articles(query, max_results)
            return []

    def fetch_abstract(self, pmid: str):
        # 使用当前正在服役的引擎去拿摘要
        return self.current_engine.fetch_abstract(pmid)


def get_searcher(database_name="PubMed"):
    """
    返回带自动降级功能的智能路由实例。
    """
    return SmartSearchRouter(database_name)

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