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
        # SerpAPI 配置
        self.serpapi_key = serpapi_key
        self.serpapi_url = serpapi_url

        # 场景识别关键词（自动区分论文搜索/通用问答）
        self.scene_keywords = {
            "paper_search": {
                "zh": ["论文", "文献", "学术论文", "研究报告", "期刊文章", "论文链接"],
                "en": ["paper", "thesis", "academic paper", "research article", "journal article", "paper link"]
            },
            "general_qa": {
                "zh": ["是什么", "什么是", "怎么理解", "如何理解", "含义", "定义", "解释"],
                "en": ["what is", "what's", "how to understand", "meaning", "definition", "explain"]
            }
        }

    def _detect_language(self, query: str) -> str:
        """自动检测用户提问语言（zh/en）"""
        if any("\u4e00" <= ch <= "\u9fff" for ch in query):
            return "zh"
        return "en"

    def _classify_scene(self, query: str, lang: str) -> str:
        """自动分类请求场景（paper_search/general_qa）"""
        query_lower = query.lower()
        # 优先识别论文搜索（关键词匹配优先级更高）
        for kw in self.scene_keywords["paper_search"][lang]:
            if kw.lower() in query_lower:
                return "paper_search"
        # 其余判定为通用问答
        return "general_qa"

    def _extract_paper_num(self, query: str) -> int:
        """提取用户要求的论文数量（默认5篇，最多10篇）"""
        # 匹配中文表述（如“5个”“10篇”“3 篇”）和纯数字（如“8”）
        num_pattern = re.search(r'(\d+)\s*篇|(\d+)\s*个|(\d+)', query)
        if num_pattern:
            # 提取第一个有效匹配的数字（过滤空值）
            matched_num = [g for g in num_pattern.groups() if g][0]
            num = int(matched_num)
            # 限制最大10篇（SerpAPI 最大支持10条结果）
            return min(num, 10)
        # 未指定数量时，默认返回5篇
        return 5

    def _serpapi_search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """调用 SerpAPI 搜索，返回结构化结果"""
        params = {
            "q": query,
            "engine": "google",
            "api_key": self.serpapi_key,
            "num": num_results,
            "hl": "zh-CN" if self._detect_language(query) == "zh" else "en",  # 结果语言适配
            "gl": "cn"  # 地域偏好：中国（提升中文结果相关性）
        }

        try:
            response = requests.get(
                self.serpapi_url,
                params=params,
                timeout=15  # 超时保护
            )
            response.raise_for_status()
            data = response.json()
            return data.get("organic_results", [])[:num_results]  # 截取前N条
        except requests.exceptions.RequestException as e:
            print(f"SerpAPI 搜索失败：{e}")
            return []

    def _call_llm(self, user_prompt: str) -> str:
        """调用LLM（系统提示词+用户提示词，强化约束）"""
        final_prompt = f"{self.system_prompt}\n\n{user_prompt}"
        return self.llm(final_prompt).strip()  # 去除首尾空格

    def build_prompt(self, query: str, results: List[Dict[str, Any]], lang: str, scene: str) -> str:
        """
        模仿标准化 Prompt 格式构建提示词：
        - 自动匹配用户语言（中文/英文）
        - 结构化输出（论文链接列表/通用问答段落）
        - 自然友好，符合日常交流习惯
        """
        # 整理原始数据（论文搜索→链接列表，通用问答→参考资料）
        if scene == "paper_search":
            raw_data = "\n".join([
                f"{idx + 1}. 标题：{res.get('title', '无标题')} | 链接：{res.get('link', '无链接')}"
                for idx, res in enumerate(results)
            ]) if results else "无相关论文数据" if lang == "zh" else "No relevant paper data"
        else:
            context = results[0] if results else {"snippet": "", "title": "", "link": ""}
            raw_data = f"""
标题：{context.get('title', '无标题')}
核心摘要：{context.get('snippet', '无相关摘要信息')}
来源链接：{context.get('link', '无来源链接')}
            """.strip()

        # 统一 Prompt 框架（角色+问题+数据+指令+示例）
        return f"""
Your Role: A professional, helpful assistant that responds in the SAME LANGUAGE as the user's question.

User's Question:
{query}

Raw Search Data (DO NOT modify this data; only use it to generate responses):
{raw_data}

Key Instructions:
1. Language Matching (Critical!):
   - Respond strictly in the SAME LANGUAGE as the user's question (Chinese for Chinese queries, English for English queries).
   - Use natural, colloquial expressions (like chatting with a friend; avoid rigid formal language).
   - Keep language consistency throughout the response (no mixed languages).

2. Response Structure (Clear & Easy to Read):
   A. If the scene is PAPER SEARCH (query includes "论文" "paper" etc.):
      - For Chinese: Number the papers as "1. 2. 3. ...", include each paper's title and link (format: "标题 → 链接").
      - For English: List the papers as "1. 2. 3. ...", include each paper's title and link (format: "Title → Link").
      - Highlight the most relevant paper (judged by title/link relevance) with a brief note (e.g., "👉 最相关：" in Chinese / "👉 Most relevant: " in English).
      - If no papers found, convey politely (e.g., "很抱歉，未找到相关论文哦～" in Chinese / "Sorry, no relevant papers found." in English).

   B. If the scene is GENERAL Q&A (query asks "是什么" "what is" etc.):
      - For Chinese: Organize the answer into 1-2 complete paragraphs, integrate key information from the raw data naturally.
      - For English: Organize the answer into 1-2 complete paragraphs, seamlessly incorporate core details from the raw data.
      - Focus on explaining core concepts clearly (avoid redundant repetition; highlight key points).
      - If no valid data, respond directly (e.g., "未找到相关信息" in Chinese / "No relevant information found" in English).

3. Critical Rules (Must Follow!):
   - NEVER invent new information (e.g., fake paper titles/links, unmentioned concepts, or false data not in the raw data).
   - NEVER omit key details (e.g., paper links, core summary points for Q&A).
   - NEVER include raw data structure, instructions, or irrelevant content in the final response (only return the answer itself).
   - Keep the response length appropriate: Comprehensive but not overly long, concise but not incomplete.

Example Responses (For Reference Only):
- Example 1 (Chinese user asking for papers):
  "根据你的查询，找到以下5篇与AI教育伦理相关的论文：
  1. AI教育伦理的挑战与应对策略 → https://example.com/paper1.pdf
  2. 青少年AI素养教育中的伦理问题研究 → https://example.com/paper2
  3. 大模型时代教育AI的伦理框架构建 → https://example.com/paper3.pdf
  4. 中小学AI教育的伦理风险防控 → https://example.com/paper4
  5. 教育AI伦理审查机制研究 → https://example.com/paper5
  👉 最相关的是《AI教育伦理的挑战与应对策略》，直接点击链接即可查看～"

- Example 2 (English user asking for general Q&A):
  "An AI agent originates from the Latin word 'Agere', which means 'to do'. In the context of large language models (LLMs), it refers to an intelligent system capable of autonomously understanding tasks, making plans and decisions, and executing complex tasks independently. Unlike traditional software tools, AI agents don't require step-by-step human guidance—they can perceive environmental information, analyze needs, and complete goals based on built-in algorithms or trained models. Common applications include intelligent customer service, autonomous driving, and personalized learning assistants, all leveraging the core traits of autonomy and adaptability."

- Example 3 (No relevant data):
  中文："很抱歉，未找到与「量子计算入门论文」相关的信息哦～"
  English: "Sorry, no relevant information found about 'introductory papers on quantum computing'."

Please generate a response that meets all the above requirements!
"""

    def rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """轻量 rerank（可选）：基于关键词匹配度提升相关性，不增加额外依赖"""
        if not results:
            return []

        query_terms = set(query.lower().split())
        academic_domains = {"arxiv.org", "ieee.org", "springer.com", "sciencedirect.com", "scholar.google.com"}

        def score(result):
            """评分规则：关键词匹配度 + 学术域名权重"""
            title = result.get("title", "").lower()
            link = result.get("link", "").lower()
            # 关键词匹配分
            term_score = sum(1 for term in query_terms if term in title or term in result.get("snippet", "").lower())
            # 学术域名加分（论文搜索场景）
            domain_score = 2 if self._classify_scene(query, self._detect_language(query)) == "paper_search" and any(
                d in link for d in academic_domains) else 0
            # PDF 链接加分（论文搜索场景）
            pdf_score = 1 if "pdf" in link else 0
            return term_score + domain_score + pdf_score

        # 按评分降序排序，保留原结果数量
        return sorted(results, key=score, reverse=True)

    def run(self, user_query: str) -> str:
        """核心入口：自动处理用户请求"""
        lang = self._detect_language(user_query)
        scene = self._classify_scene(user_query, lang)

        # 配置搜索参数（论文搜索提取用户指定数量，通用问答固定1条）
        search_num = self._extract_paper_num(user_query) if scene == "paper_search" else 1
        raw_results = self._serpapi_search(user_query, search_num)

        # print(f"Raw search results: {raw_results}")

        # 调用工具类进行重排
        ranked_results = self.rerank(user_query, raw_results)

        # 构建结构化Prompt
        prompt = self.build_prompt(user_query, ranked_results, lang, scene)

        # 调用LLM生成结果
        return self._call_llm(prompt)