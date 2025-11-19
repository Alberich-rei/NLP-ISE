"""
金融相关工具集
"""
import yfinance as yf


def _get_stock(symbol):
    """Internal stock price function"""
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if hist.empty:
            return f"No data for {symbol}"

        close = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2]
        change = (close - prev)/prev*100
        return f"{symbol} close: {close:.2f} ({change:.2f}%)"
    except Exception as e:
        return f"Stock error: {e}"


class FinanceTools:
    """金融相关工具集"""
    
    @staticmethod
    def get_stock_price(symbol: str) -> str:
        """获取股票价格"""
        try:
            return _get_stock(symbol)
        except Exception as e:
            return f"获取股票 {symbol} 数据失败: {e}"
    
    @staticmethod
    def get_forex_rate(from_currency: str = "USD", to_currency: str = "HKD") -> str:
        """获取汇率（模拟）"""
        # 这里可以接入真实的汇率API，如 exchangerate-api.com
        rates = {
            ("USD", "HKD"): 7.82,
            ("USD", "CNY"): 7.25,
            ("EUR", "HKD"): 8.45,
            ("GBP", "HKD"): 9.95,
            ("JPY", "HKD"): 0.052
        }
        
        rate = rates.get((from_currency, to_currency))
        if rate:
            return f"汇率 {from_currency}/{to_currency}: {rate}"
        else:
            return f"暂无 {from_currency} 到 {to_currency} 的汇率数据"
    
    @staticmethod
    def get_market_index(index: str = "HSI") -> str:
        """获取市场指数（使用yfinance获取真实数据）"""
        # 指数符号映射
        symbol_map = {
            "HSI": "^HSI",      # 恒生指数
            "HSTECH": "^HSTECH", # 恒生科技指数
            "SSE": "000001.SS", # 上证指数
            "SZSE": "399001.SZ", # 深证成指
            "NASDAQ": "^IXIC",   # 纳斯达克
            "DOW": "^DJI",      # 道琼斯
            "SPX": "^GSPC",     # 标普500
            "NIKKEI": "^N225"   # 日经225
        }
        
        try:
            symbol = symbol_map.get(index.upper(), "^HSI")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            
            if hist.empty:
                return f"无法获取 {index} 指数数据"
            
            current = hist['Close'].iloc[-1]
            previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
            change = current - previous
            percent_change = (change / previous) * 100
            
            # 中文名称映射
            chinese_names = {
                "HSI": "恒生指数",
                "HSTECH": "恒生科技指数",
                "SSE": "上证指数",
                "SZSE": "深证成指",
                "NASDAQ": "纳斯达克指数",
                "DOW": "道琼斯指数",
                "SPX": "标普500指数",
                "NIKKEI": "日经225指数"
            }
            
            name = chinese_names.get(index.upper(), index)
            sign = "+" if change >= 0 else ""
            
            return f"{name}: {current:.2f} ({sign}{change:.2f}, {percent_change:+.2f}%)"
            
        except Exception as e:
            # 如果真实数据获取失败，使用模拟数据
            fallback_data = {
                "HSI": {"恒生指数": {"value": 19250, "change": "+125.6", "percent": "+0.66%"}},
                "SSE": {"上证指数": {"value": 3325, "change": "-15.2", "percent": "-0.45%"}},
                "NASDAQ": {"纳斯达克": {"value": 15420, "change": "+85.3", "percent": "+0.56%"}},
                "DOW": {"道琼斯": {"value": 35680, "change": "+120.8", "percent": "+0.34%"}}
            }
            
            if index.upper() in fallback_data:
                for name, data in fallback_data[index.upper()].items():
                    return f"{name}: {data['value']} ({data['change']} {data['percent']}) [模拟数据]"
            
            return f"获取 {index} 数据失败: {e}"
    
    @staticmethod
    def get_crypto_price(symbol: str = "BTC") -> str:
        """获取加密货币价格（模拟）"""
        crypto_data = {
            "BTC": {"price": 42500, "change": "+2.3%"},
            "ETH": {"price": 2850, "change": "-1.2%"},
            "ADA": {"price": 0.85, "change": "+5.6%"},
            "DOT": {"price": 28.5, "change": "+3.1%"}
        }
        
        data = crypto_data.get(symbol.upper(), {"price": 0, "change": "N/A"})
        return f"{symbol} 价格: ${data['price']} ({data['change']})"
    
    @staticmethod
    def get_economic_news() -> str:
        """获取经济新闻摘要（模拟）"""
        import random
        news_items = [
            "最新经济动态：美联储维持利率不变，香港恒指收涨0.66%，人民币汇率稳定。",
            "亚太股市今日收盘涨跌不一，科技股表现强劲，金融股有所回调。",
            "国际油价今日上涨2.5%，黄金价格稳中有升，美元指数有所回落。"
        ]
        return random.choice(news_items)
        
    @staticmethod
    def get_portfolio_summary() -> str:
        """获取投资组合摘要（模拟）"""
        return "模拟投资组合：股票 60%，债券 30%，现金 10%，总收益率 +8.5%"
        
    @staticmethod
    def get_commodity_prices() -> str:
        """获取大宗商品价格（模拟）"""
        commodities = {
            "黄金": "$1,950/盎司 (+0.8%)",
            "原油": "$85.6/桶 (+2.1%)",
            "铜": "$8,250/吨 (-0.5%)",
            "银": "$24.8/盎司 (+1.2%)"
        }
        return "; ".join([f"{k}: {v}" for k, v in commodities.items()])
    
    @staticmethod
    def get_hsi_details() -> str:
        """获取恒生指数详细信息"""
        try:
            hsi = yf.Ticker("^HSI")
            hist = hsi.history(period="5d")
            
            if hist.empty:
                return "无法获取恒生指数数据"
            
            current = hist['Close'].iloc[-1]
            previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
            high = hist['High'].iloc[-1]
            low = hist['Low'].iloc[-1]
            volume = hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
            
            change = current - previous
            percent_change = (change / previous) * 100
            
            return f"""恒生指数 (HSI) 详情：
现价：{current:.2f}
涨跌：{change:+.2f} ({percent_change:+.2f}%)
今日最高：{high:.2f}
今日最低：{low:.2f}
成交量：{volume:,.0f} 股"""
            
        except Exception as e:
            return f"获取恒生指数详情失败: {e}"
    
    @staticmethod
    def analyze_market_sentiment(query: str) -> str:
        """分析市场情绪和特定问题"""
        # 检查是否问的是恒生指数的升跌
        if any(word in query for word in ["恒生指数", "恒指", "hsi", "hang seng"]):
            if any(word in query for word in ["升跌", "百分比", "涨跌", "收市"]):
                return FinanceTools.get_hsi_details()
        
        # 检查是否问的是香港股市整体
        if any(word in query for word in ["香港股市", "港股", "港交所"]):
            return FinanceTools.get_hk_market_summary()
        
        # 默认返回恒生指数信息
        return FinanceTools.get_market_index("HSI")
    
    @staticmethod
    def get_hk_market_summary() -> str:
        """获取香港股市概况"""
        try:
            # 获取主要指数
            indices = ["^HSI", "^HSTECH"]
            results = []
            
            for symbol in indices:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    change = current - previous
                    percent = (change / previous) * 100
                    
                    name = "恒生指数" if symbol == "^HSI" else "恒生科技指数"
                    results.append(f"{name}: {current:.2f} ({percent:+.2f}%)")
            
            if results:
                return f"香港股市概况：\n" + "\n".join(results)
            else:
                return "无法获取香港股市数据"
                
        except Exception as e:
            return f"获取香港股市数据失败: {e}"