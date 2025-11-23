"""Finance agent handling stock, forex, and market queries with workflow."""
from __future__ import annotations
import json

from tools.finance_tools import FinanceTools


class FinanceAgent:
    """Agent responsible for finance related questions."""
    system_prompt = """
        You are a financial intelligent assistant. Your task is to classify the user’s question into one of the following financial intents and output structured JSON.

        Supported intent categories:
        1. get_stock_price —— query stock prices
        2. get_market_index —— query market indices
        3. fund —— query funds or ETFs
        4. financial_report —— query company financial reports
        5. get_news —— query company or market news

        Output requirements:
        - Must use JSON format
        - Fields include:
          - "intent": one of the categories above
          - "entities": the companies, indices, or funds involved (e.g., NVIDIA, AMD, S&P500)
          - "tickerSymbol": the stock/index/fund code (e.g., NVDA, AMD, SPX), leave empty if not applicable
          - "stockExchangePrefix": the market where the stock or index is listed (e.g., NASDAQ, NYSE), leave empty if not applicable
          - "extra": other supplementary information (e.g., comparison targets, time range)

        Examples:
        User input: "What is NVIDIA’s stock price? Compare with AMD."
        Output:
        {
          "intent": "stock",
          "entities": ["NVIDIA", "AMD"],
          "tickerSymbol": "NVDA",
          "stockExchangePrefix": "NASDAQ",
          "extra": {
            "comparison": ["AMD"]
          }
        }

        User input: "Latest S&P500 index level"
        Output:
        {
          "intent": "index",
          "entities": ["S&P500"],
          "tickerSymbol": "SPX",
          "stockExchangePrefix": null
        }

        User input: "Check Tesla’s latest financial report"
        Output:
        {
          "intent": "financial_report",
          "entities": ["Tesla"],
          "tickerSymbol": "TSLA",
          "stockExchangePrefix": "NASDAQ"
        }

        User input: "Recent news about Apple"
        Output:
        {
          "intent": "news",
          "entities": ["Apple"],
          "tickerSymbol": "AAPL",
          "stockExchangePrefix": "NASDAQ"
        }
    """

    def __init__(self, llm):
        self.llm = llm
        self.name = "FinanceAgent"
        self.tools = FinanceTools()
        self.system_prompt = self.system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)

    def _extract_symbol(self, query: str) -> str:
        """从查询中提取股票代码或相关符号"""
        query_upper = query.upper()

        # 常见股票代码
        common_stocks = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BABA", "TCEHY"]
        for stock in common_stocks:
            if stock in query_upper:
                return stock

        # 中文股票名称映射
        chinese_stocks = {
            "腾讯": "TCEHY",
            "阿里巴巴": "BABA",
            "苹果": "AAPL",
            "特斯拉": "TSLA",
            "微软": "MSFT",
            "谷歌": "GOOGL",
        }

        for chinese_name, symbol in chinese_stocks.items():
            if chinese_name in query:
                return symbol

        # 排除常见非股票词汇
        excluded_words = [
            "FROM",
            "TO",
            "AND",
            "OR",
            "THE",
            "IS",
            "ARE",
            "WAS",
            "WERE",
            "WHAT",
            "HOW",
            "WHY",
            "WHEN",
            "WHERE",
            "WHICH",
            "ABOUT",
            "TODAY",
            "PRICE",
            "STOCK",
            "SHARE",
            "MARKET",
            "INDEX",
        ]

        # 从查询中提取可能的股票代码
        words = query_upper.split()
        for word in words:
            if len(word) >= 2 and len(word) <= 5 and word.isalpha() and word not in excluded_words:
                return word

        return "AAPL"  # 默认

    def run(self, query: str) -> str:
        query_lower = query.lower()
        results = []

        # 恒生指数专门处理
        if any(term in query for term in ["恒生指数", "恒指", "HSI"]) and any(
            term in query for term in ["升跌", "百分比", "涨跌", "收市"]
        ):
            hsi_info = self.tools.analyze_market_sentiment(query)
            results.append(f"恒生指数分析：{hsi_info}")

        # 香港股市整体查询
        elif any(term in query for term in ["香港股市", "港股", "港交所"]):
            hk_market = self.tools.get_hk_market_summary()
            results.append(f"香港市场摘要：{hk_market}")

        # 股票查询
        elif any(term in query_lower for term in ["stock", "share", "股票", "股价"]):
            symbol = self._extract_symbol(query)
            stock_info = self.tools.get_stock_price(symbol)
            results.append(f"股票信息：\n{stock_info}")

        # 汇率查询
        elif any(term in query_lower for term in ["exchange", "rate", "汇率", "currency"]):
            # 简单的汇率提取逻辑
            if "usd" in query_lower and "hkd" in query_lower:
                forex = self.tools.get_forex_rate("USD", "HKD")
            elif "eur" in query_lower:
                forex = self.tools.get_forex_rate("EUR", "HKD")
            else:
                forex = self.tools.get_forex_rate()
            results.append(f"汇率：{forex}")

        # 市场指数查询
        elif any(term in query_lower for term in ["index", "market", "指数", "市场"]):
            if "hsi" in query_lower or "恒指" in query:
                index_info = self.tools.get_market_index("HSI")
            elif "hstech" in query_lower or "科技" in query:
                index_info = self.tools.get_market_index("HSTECH")
            elif "nasdaq" in query_lower:
                index_info = self.tools.get_market_index("NASDAQ")
            elif "dow" in query_lower:
                index_info = self.tools.get_market_index("DOW")
            else:
                index_info = self.tools.get_market_index("HSI")
            results.append(f"指数信息：{index_info}")

        # 加密货币查询
        elif any(term in query_lower for term in ["crypto", "bitcoin", "btc", "ethereum", "eth", "加密", "比特币", "以太坊"]):
            if "btc" in query_lower or "bitcoin" in query_lower or "比特币" in query:
                crypto = self.tools.get_crypto_price("BTC")
            elif "eth" in query_lower or "ethereum" in query_lower or "以太坊" in query:
                crypto = self.tools.get_crypto_price("ETH")
            else:
                crypto = self.tools.get_crypto_price("BTC")
            results.append(f"加密货币：{crypto}")

        # 经济新闻
        elif any(term in query_lower for term in ["news", "economic", "新闻", "经济"]):
            news = self.tools.get_economic_news()
            results.append(f"新闻：{news}")

        # 如果没有匹配到具体类型，智能分析查询内容
        else:
            # 尝试智能分析
            analysis = self.tools.analyze_market_sentiment(query)
            results.append(f"分析：{analysis}")
            results.append("如需具体股票或指数，请在问题中包含名称或代码。")

        combined_result = "\n\n".join(results)
        prompt = (
            f"Finance query: {query}\nFinancial information:\n{combined_result}\n"
            "Provide a comprehensive financial response."
        )
        return self._call_llm(prompt)
