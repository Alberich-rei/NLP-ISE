"""
Financial Tools Collection
"""
import requests


class FinanceTools:
    """Financial tools for stock, forex and market index data"""
    
    @staticmethod
    def get_stock_price(symbol: str = "AAPL") -> str:
        """Get latest stock price using Alpha Vantage API"""
        api_key = "N50G8IJCU4XHVNA3"
        if not api_key:
            return "Error: Alpha Vantage API key not configured"

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": api_key,
            "datatype": "json"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        global_quote = data["Global Quote"]
        
        symbol_name = global_quote["01. symbol"]
        current_price = global_quote["05. price"]
        change = global_quote["09. change"]
        change_percent = global_quote["10. change percent"]
        trading_day = global_quote["07. latest trading day"]
        
        return f"""Stock: {symbol_name}
Current Price: ${current_price}
Daily Change: {change} ({change_percent})
Last Trading Day: {trading_day}"""
    
    @staticmethod
    def get_forex_rate(from_currency: str = "USD", to_currency: str = "HKD") -> str:
        """Get exchange rate using Alpha Vantage API"""
        api_key = "N50G8IJCU4XHVNA3"
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "FX_DAILY",
            "from_symbol": from_currency,
            "to_symbol": to_currency,
            "apikey": api_key,
            "datatype": "json"
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            time_series = data["Time Series FX (Daily)"]
            latest_date = max(time_series.keys())
            latest_data = time_series[latest_date]
            
            rate = float(latest_data["4. close"])
            
            return f"""Exchange Rate {from_currency} to {to_currency}:
Rate: 1 {from_currency} = {rate:.4f} {to_currency}
Last Update: {latest_date}"""
        
        except Exception as e:
            return f"Error retrieving forex rate for {from_currency}/{to_currency}: {str(e)}"
    
    @staticmethod
    def get_market_index(index: str = "HSI") -> str:
        """Get market index data using Alpha Vantage API"""
        api_key = "N50G8IJCU4XHVNA3"
        
        symbol_map = {
            "HSI": "HSIC",
            "NASDAQ 100": "QQQ",
            "DOW": "DOW",
            "SPX": "SPY",
            "NIKKEI": "EWJ"
        }
        
        symbol = symbol_map[index.upper()]
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": api_key,
            "datatype": "json"
        }
        try:
            response = requests.get(url, params=params,timeout=60)
            data = response.json()

            global_quote = data["Global Quote"]

            symbol_name = global_quote["01. symbol"]
            current_price = global_quote["05. price"]
            change = global_quote["09. change"]
            change_percent = global_quote["10. change percent"]

            index_names = {
                "HSIC": "Hang Seng Index",
                "QQQ": "NASDAQ Composite",
                "DOW": "Dow Jones Industrial Average",
                "SPY": "S&P 500 Index",
                "EWJ": "Nikkei 225"
            }

            name = index_names[symbol]
        except Exception as e:
            print(f"ERROR:{e}")
        
        return f"{name}: {current_price} ({change}, {change_percent})"
    
    @staticmethod
    def get_hsi_details() -> str:
        """Get detailed Hang Seng Index information using Alpha Vantage API"""
        api_key = "N50G8IJCU4XHVNA3"
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": "HSIC",
            "apikey": api_key,
            "datatype": "json"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        global_quote = data["Global Quote"]
        
        symbol = global_quote["01. symbol"]
        open_price = global_quote["02. open"]
        high_price = global_quote["03. high"]
        low_price = global_quote["04. low"]
        current_price = global_quote["05. price"]
        volume = global_quote["06. volume"]
        trading_day = global_quote["07. latest trading day"]
        previous_close = global_quote["08. previous close"]
        change = global_quote["09. change"]
        change_percent = global_quote["10. change percent"]
        
        return f"""Hang Seng Index ({symbol}) Details:
Current Price: {current_price}
Open: {open_price} | High: {high_price} | Low: {low_price}
Previous Close: {previous_close}
Change: {change} ({change_percent})
Volume: {volume}
Trading Day: {trading_day}"""

    @staticmethod
    def get_news(symbol: str = "AAPL") -> str:
        """Get latest company news using Alpha Vantage API"""
        api_key = "N50G8IJCU4XHVNA3"
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": api_key,
            "datatype": "json",
            "limit": 5
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            feed = data["feed"]
            
            news_items = []
            for item in feed:
                title = item["title"]
                summary = item["summary"]
                source = item["source"]
                time_published = item["time_published"]
                url = item["url"]
                
                news_items.append(f"""Title: {title}
Source: {source}
Time: {time_published}
Summary: {summary}
URL: {url}
---""")
            
            return f"Latest News for {symbol}:\n\n" + "\n\n".join(news_items)
        
        except Exception as e:
            return f"Error retrieving news for {symbol}: {str(e)}"

    @staticmethod
    def get_financial_reports(symbol: str = "AAPL") -> str:
        """Get financial reports (Income Statement, Balance Sheet, Cash Flow) using Alpha Vantage API"""
        api_key = "N50G8IJCU4XHVNA3"
        
        reports = {}
        
        # Get Income Statement
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "INCOME_STATEMENT",
                "symbol": symbol,
                "apikey": api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            annual_reports = data["annualReports"][:5]
            
            income_data = []
            for report in annual_reports:
                year = report["fiscalDateEnding"]
                revenue = report["totalRevenue"]
                net_income = report["netIncome"]
                eps = report["reportedEPS"]
                
                income_data.append(f"{year}: Revenue=${revenue}, Net Income=${net_income}, EPS=${eps}")
            
            reports["Income Statement"] = "\n".join(income_data)
            
        except Exception as e:
            reports["Income Statement"] = f"Error retrieving income statement: {str(e)}"
        
        # Get Balance Sheet
        try:
            params = {
                "function": "BALANCE_SHEET",
                "symbol": symbol,
                "apikey": api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            annual_reports = data["annualReports"][:5]
            
            balance_data = []
            for report in annual_reports:
                year = report["fiscalDateEnding"]
                total_assets = report["totalAssets"]
                total_liabilities = report["totalLiabilities"]
                shareholders_equity = report["totalShareholderEquity"]
                
                balance_data.append(f"{year}: Assets=${total_assets}, Liabilities=${total_liabilities}, Equity=${shareholders_equity}")
            
            reports["Balance Sheet"] = "\n".join(balance_data)
            
        except Exception as e:
            reports["Balance Sheet"] = f"Error retrieving balance sheet: {str(e)}"
        
        # Get Cash Flow
        try:
            params = {
                "function": "CASH_FLOW",
                "symbol": symbol,
                "apikey": api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            annual_reports = data["annualReports"][:5]
            
            cashflow_data = []
            for report in annual_reports:
                year = report["fiscalDateEnding"]
                operating_cashflow = report["operatingCashflow"]
                investing_cashflow = report["cashflowFromInvestment"]
                financing_cashflow = report["cashflowFromFinancing"]
                
                cashflow_data.append(f"{year}: Operating=${operating_cashflow}, Investing=${investing_cashflow}, Financing=${financing_cashflow}")
            
            reports["Cash Flow"] = "\n".join(cashflow_data)
            
        except Exception as e:
            reports["Cash Flow"] = f"Error retrieving cash flow: {str(e)}"
        
        # Format final output
        result = f"Financial Reports for {symbol} (Last 5 Years):\n\n"
        
        for report_type, data in reports.items():
            result += f"{report_type}:\n{data}\n\n"
        
        return result
    
if __name__ == "__main__":
    tool = FinanceTools()
    print(tool.get_stock_price("IBM"))

