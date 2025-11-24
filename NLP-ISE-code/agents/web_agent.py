from __future__ import annotations
import re
import requests
from typing import List, Dict, Any, Optional


class WebAgent:
    def __init__(
            self,
            llm,
            system_prompt: str | None = None,
            serpapi_key: str = "247520e58efa7b02a382ea53355b23a843dc182c8be3b6c05b0cfd139caeb807",
            serpapi_url: str = "https://serpapi.com/search"
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.serpapi_key = serpapi_key
        self.serpapi_url = serpapi_url

        # 场景识别关键词（保留推荐类+通用+论文）
        self.scene_keywords = {
            "paper_search": {
                "zh": ["论文", "文献", "学术论文", "研究报告", "期刊文章", "论文链接"],
                "en": ["paper", "thesis", "academic paper", "research article", "journal article", "paper link"]
            },
            "general_qa": {
                "zh": ["是什么", "什么是", "怎么理解", "如何理解", "含义", "定义", "解释"],
                "en": ["what is", "what's", "how to understand", "meaning", "definition", "explain"]
            },
            "recommendation": {
                "zh": ["推荐", "推荐一下", "求推荐", "好玩的", "好用的", "值得的", "热门"],
                "en": ["recommend", "suggest", "best", "top", "popular", "fun", "good"]
            }
        }

    def _detect_language(self, query: str) -> str:
        """自动检测用户提问语言（zh/en）"""
        if any("\u4e00" <= ch <= "\u9fff" for ch in query):
            return "zh"
        return "en"

    def _classify_scene(self, query: str, lang: str) -> str:
        """场景分类：推荐类→论文→通用"""
        query_lower = query.lower()
        # 优先推荐类
        for kw in self.scene_keywords["recommendation"][lang]:
            if kw.lower() in query_lower:
                return "recommendation"
        # 再论文搜索
        for kw in self.scene_keywords["paper_search"][lang]:
            if kw.lower() in query_lower:
                return "paper_search"
        # 最后通用问答
        return "general_qa"

    def _extract_paper_num(self, query: str) -> int:
        """提取论文数量（默认5篇，最多10篇）"""
        num_pattern = re.search(r'(\d+)\s*篇|(\d+)\s*个|(\d+)', query)
        if num_pattern:
            matched_num = [g for g in num_pattern.groups() if g][0]
            return min(int(matched_num), 10)
        return 5

    def _clean_query(self, query: str) -> str:
        """清理查询词：去除「联网搜索」等前缀+无关上下文，只保留核心问题"""
        # 移除常见前缀
        prefixes = ["联网搜索", "搜索", "帮我", "请", "麻烦"]
        for prefix in prefixes:
            if query.startswith(prefix):
                query = query.replace(prefix, "").strip()
        # 移除对话历史等非法字符（避免 q 参数格式错误）
        query = re.sub(r'Context from previous conversation.*?Current question:', '', query, flags=re.DOTALL)
        query = re.sub(r'[\r\n\t]', ' ', query).strip()
        # 限制查询词长度（SerpAPI 对 q 参数有长度限制）
        return query[:100]  # 截取前100字符

    def _serpapi_search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """修复 SerpAPI 参数：移除不兼容配置，确保请求合法"""
        clean_q = self._clean_query(query)
        lang = self._detect_language(clean_q)
        scene = self._classify_scene(clean_q, lang)

        # 简化参数（避免不兼容配置导致 400 错误）
        params = {
            "q": clean_q,  # 使用清理后的核心查询词
            "engine": "google",
            "api_key": self.serpapi_key,
            "num": num_results,
            "hl": "zh-CN" if lang == "zh" else "en",
            "gl": "cn",  # 固定中国地域（适合中文查询）
            "safe": "off",  # 关闭安全搜索（避免过滤过多结果）
            # 移除 google_domain=google.cn（SerpAPI 对 google.cn 支持不稳定）
        }

        try:
            response = requests.get(
                self.serpapi_url,
                params=params,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}  # 模拟浏览器请求
            )
            response.raise_for_status()  # 抛出 HTTP 错误
            data = response.json()

            # 提取有效结果（organic_results + 可能的知识图谱）
            results = data.get("organic_results", [])
            kg = data.get("knowledge_graph", {})
            if kg and "description" in kg:
                # 知识图谱结果封装成统一格式
                results.append({
                    "title": kg.get("title", clean_q),
                    "snippet": kg.get("description", ""),
                    "link": kg.get("url", "")
                })
            return results[:num_results]  # 截取指定数量
        except requests.exceptions.RequestException as e:
            print(f"SerpAPI 搜索失败：{e}")
            # 打印完整请求 URL，方便排查问题
            print(f"请求 URL：{response.url if 'response' in locals() else '未生成'}")
            return []

    def _call_llm(self, user_prompt: str) -> str:
        """调用 LLM（兼容无 system_prompt 场景）"""
        final_prompt = f"{self.system_prompt}\n\n{user_prompt}" if self.system_prompt else user_prompt
        return self.llm(final_prompt).strip()

    def build_prompt(self, query: str, results: List[Dict[str, Any]], lang: str, scene: str) -> str:
        """构建 Prompt（优化推荐类/通用问答的 raw_data）"""
        clean_q = self._clean_query(query)
        # 整理原始数据
        if scene == "paper_search":
            raw_data = "\n".join([
                f"{idx + 1}. 标题：{res.get('title', '无标题')} | 链接：{res.get('link', '无链接')}"
                for idx, res in enumerate(results)
            ]) if results else "无相关论文数据" if lang == "zh" else "No relevant paper data"
        elif scene == "recommendation":
            recom_data = []
            for idx, res in enumerate(results):
                name = res.get("title", "无名称").strip()
                desc = res.get("snippet", "无描述").strip()
                link = res.get("link", "无链接").strip()
                recom_data.append(f"{idx + 1}. 名称：{name} | 描述：{desc} | 链接：{link}")
            raw_data = "\n".join(
                recom_data) if recom_data else "无相关推荐数据" if lang == "zh" else "No relevant recommendations"
        else:  # general_qa
            combined = []
            for res in results:
                title = res.get("title", "").strip()
                snippet = res.get("snippet", "").strip()
                if title and snippet:
                    combined.append(f"标题：{title} | 摘要：{snippet}")
            raw_data = "\n".join(combined) if combined else "无相关摘要信息" if lang == "zh" else "No relevant snippets"

        # Prompt 模板（强化推荐类和通用问答的输出要求）
        return f"""
Your Role: A helpful assistant responding in the same language as the user's question.

User's Question:
{clean_q}

Raw Search Data (DO NOT modify, use only for response):
{raw_data}

Key Instructions:
1. Language: Use {lang} (same as user's question), natural and colloquial.
2. Response Structure:
   - Paper Search: List papers with "标题 → 链接", highlight the most relevant one.
   - Recommendation: List 3-5 items with "Name + Key Feature + Reason", use simple language.
   - conclude Q&A: 1-2 paragraphs integrating raw data, clear and concise.
3. Rules: Never invent info, never omit key details, keep response appropriate length.

Examples:
- 中文推荐示例（桌游）：
  "推荐3款好玩的桌游：
  1. 《大富翁》：经典经营类，2-6人玩，规则简单 → 适合家庭聚会，互动性强。
  2. 《狼人杀》：推理发言类，5-12人玩 → 适合团建，活跃气氛。
  3. 《UNO》：卡牌类，2-10人玩，节奏快 → 适合休闲娱乐，新手易上手。"
  
- Example 2 (Chinese user asking for papers):" 根据你的查询，找到以下 6 篇与 AI 教育伦理相关的论文：  
    1. **[最相关]** 【AI模型】深度解析：DeepSeek的联网搜索的实现原理与认知 → [链接](https://blog.csdn.net/arbboter/article/details/146360231)  
    2. 入坑一周，被夸克深度搜索的高搜商圈粉了 → [链接](https://developer.volcengine.com/articles/7504609992977170495)  
    3. 黄思远｜以一作身份发表4篇AI顶会论文，他有什么科研秘诀？ → [链接](https://speit.sjtu.edu.cn/about/news/37897)  
    4. DeepSeek 的联网搜索用不好就是灾难 → [链接](https://www.53ai.com/news/tishicijiqiao/2025021695160.html)  
    5. 使用Spring AI Alibaba 构建大模型联网搜索应用 → [链接](https://java2ai.com/blog/spring-ai-alibaba-module-rag/)  
    6. 清华大学出品——AMiner“沉思”AI科研助手上线 → [链接](https://ca.hit.edu.cn/info/1031/2364.htm)  

👉 从搜索结果看，当前AI联网搜索技术聚焦于原理解析（如DeepSeek）、工具应用（如Spring AI）及科研辅助（如AMiner）。若需技术细节，推荐首篇；若关注学术产出，可参考第三篇
    "

- Example 2 (English user asking for general Q&A with non-empty raw data):
"An AI agent originates from the Latin word 'Agere', 
which means 'to do'. In the context of large language models (LLMs), 
it refers to an intelligent system capable of autonomously understanding tasks, 
making plans and decisions, and executing complex tasks independently. 
Unlike traditional software tools, 
AI agents don't require step-by-step human guidance—they can perceive environmental information, 
analyze needs, and complete goals based on built-in algorithms or trained models. 
Common applications include intelligent customer service, autonomous driving, and personalized learning assistants, 
all leveraging the core traits of autonomy and adaptability."

Please generate a response strictly following the above!
"""

    def rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """结果重排（提升关键词匹配度高的结果优先级）"""
        if not results:
            return []
        clean_q = self._clean_query(query).lower()
        query_terms = set(clean_q.split())

        def score(result):
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()
            # 关键词匹配分
            term_score = sum(1 for term in query_terms if term in title or term in snippet)
            # 长度分（摘要越长信息越全）
            len_score = min(len(snippet) // 30, 2)
            return term_score + len_score

        return sorted(results, key=score, reverse=True)

    def run(self, user_query: str) -> str:
        """核心入口：优化搜索数量和流程"""
        clean_q = self._clean_query(user_query)
        lang = self._detect_language(clean_q)
        scene = self._classify_scene(clean_q, lang)

        # 配置搜索数量
        if scene == "recommendation":
            search_num = 5
        elif scene == "general_qa":
            search_num = 4
        else:
            search_num = self._extract_paper_num(clean_q)

        print(f"[WebAgent] Detected language: {lang}, scene: {scene}, search_num: {search_num}")

        # 搜索→重排→构建 Prompt→调用 LLM
        raw_results = self._serpapi_search(clean_q, search_num)
        ranked_results = self.rerank(clean_q, raw_results)
        prompt = self.build_prompt(clean_q, ranked_results, lang, scene)
        return self._call_llm(prompt)