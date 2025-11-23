"""Finance agent handling stock, forex, and market queries with workflow."""
from __future__ import annotations
import json

from tools.finance_tools import FinanceTools


class FinanceAgent:
    """Agent responsible for finance related questions with workflow management."""
    
    # System prompt for workflow generation
    workflow_prompt = """
        You are a financial workflow planner. Given a user's financial query, create a workflow of tool calls to answer the question.
        
        Available tools:
        1. get_stock_price(symbol: str) - Get stock price for a symbol
        2. get_forex_rate(from_currency: str, to_currency: str) - Get exchange rate
        3. get_market_index(index: str) - Get market index data (HSI, NASDAQ, DOW, etc.)
        4. get_hsi_details() - Get detailed HSI information
        5. get_news(symbol: str) - Get latest company news
        6. get_financial_reports(symbol: str) - Get financial reports (Income Statement, Balance Sheet, Cash Flow)
        
        Return a JSON workflow with this structure:
        {
            "workflow": [
                {
                    "tool": "tool_name",
                    "parameters": {"param1": "value1"},
                    "description": "what this step does"
                }
            ]
        }
        
        Examples:
        Query: "Get Apple stock price and USD to HKD rate"
        Response:
        {
            "workflow": [
                {
                    "tool": "get_stock_price",
                    "parameters": {"symbol": "AAPL"},
                    "description": "Get Apple stock price"
                },
                {
                    "tool": "get_forex_rate",
                    "parameters": {"from_currency": "USD", "to_currency": "HKD"},
                    "description": "Get USD to HKD exchange rate"
                }
            ]
        }
        
        Query: "Show me HSI index details"
        Response:
        {
            "workflow": [
                {
                    "tool": "get_hsi_details",
                    "parameters": {},
                    "description": "Get detailed HSI information"
                }
            ]
        }
        
        Query: "Tell me about Apple" or "Apple company information"
        Response:
        {
            "workflow": [
                {
                    "tool": "get_stock_price",
                    "parameters": {"symbol": "AAPL"},
                    "description": "Get Apple stock price"
                },
                {
                    "tool": "get_news",
                    "parameters": {"symbol": "AAPL"},
                    "description": "Get Apple latest news"
                },
                {
                    "tool": "get_financial_reports",
                    "parameters": {"symbol": "AAPL"},
                    "description": "Get Apple financial reports"
                }
            ]
        }
        
        Special Rule: When user asks about a company's general information (not specifically asking for stock price, news, or financial reports only), always include all three tools: get_stock_price, get_news, and get_financial_reports to provide comprehensive company information.
    """
    
    # System prompt for response generation
    response_prompt = """
        You are a professional financial assistant. Based on the user's query and the financial data collected, provide a comprehensive and helpful response.
        
        Guidelines:
        1. Answer the user's question directly and clearly
        2. Present financial data in an organized manner
        3. Provide context and insights when relevant
        4. Use professional but accessible language
        5. If multiple data points are provided, synthesize them coherently
        
        Format your response to be informative and user-friendly.
    """

    def __init__(self, llm):
        self.llm = llm
        self.name = "FinanceAgent"
        self.tools = FinanceTools()

    def _call_llm_for_workflow(self, query: str) -> str:
        """Call LLM for workflow generation"""
        combined = f"{self.workflow_prompt}\n\nUser Query: {query}\n\nGenerate workflow JSON:"
        return self.llm(combined)
    
    def _call_llm_for_response(self, query: str, results_data: str) -> str:
        """Call LLM for final response generation"""
        combined = f"{self.response_prompt}\n\nUser Query: {query}\n\nFinancial Data Collected:\n{results_data}\n\nProvide a comprehensive response:"
        return self.llm(combined)

    def _generate_workflow(self, query: str) -> dict:
        """Generate workflow JSON from user query using LLM"""
        response = self._call_llm_for_workflow(query)
        
        try:
            # Extract JSON from LLM response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                workflow_data = json.loads(json_str)
                return workflow_data
            else:
                # Fallback workflow for basic queries
                return self._create_fallback_workflow(query)
                
        except (json.JSONDecodeError, ValueError):
            # Fallback workflow if JSON parsing fails
            return self._create_fallback_workflow(query)
    
    def _create_fallback_workflow(self, query: str) -> dict:
        """Create a simple fallback workflow based on query keywords"""
        query_lower = query.lower()
        workflow = []
        
        # Company information query (comprehensive)
        if any(term in query_lower for term in ["about", "information", "company", "tell me", "关于", "信息", "公司"]):
            symbol = self._extract_symbol(query)
            # Return comprehensive company information
            workflow.extend([
                {
                    "tool": "get_stock_price",
                    "parameters": {"symbol": symbol},
                    "description": f"Get {symbol} stock price"
                },
                {
                    "tool": "get_news",
                    "parameters": {"symbol": symbol},
                    "description": f"Get {symbol} latest news"
                },
                {
                    "tool": "get_financial_reports",
                    "parameters": {"symbol": symbol},
                    "description": f"Get {symbol} financial reports"
                }
            ])
        
        # Stock price query (specific)
        elif any(term in query_lower for term in ["stock", "price", "股票", "股价"]):
            symbol = self._extract_symbol(query)
            workflow.append({
                "tool": "get_stock_price",
                "parameters": {"symbol": symbol},
                "description": f"Get stock price for {symbol}"
            })
        
        # News query
        elif any(term in query_lower for term in ["news", "新闻"]):
            symbol = self._extract_symbol(query)
            workflow.append({
                "tool": "get_news",
                "parameters": {"symbol": symbol},
                "description": f"Get latest news for {symbol}"
            })
        
        # Financial reports query
        elif any(term in query_lower for term in ["financial", "report", "财报", "财务", "income", "balance", "cash flow"]):
            symbol = self._extract_symbol(query)
            workflow.append({
                "tool": "get_financial_reports",
                "parameters": {"symbol": symbol},
                "description": f"Get financial reports for {symbol}"
            })
        
        # Market index query
        elif any(term in query_lower for term in ["index", "hsi", "nasdaq", "dow", "指数"]):
            if "hsi" in query_lower or "恒指" in query:
                workflow.append({
                    "tool": "get_hsi_details",
                    "parameters": {},
                    "description": "Get detailed HSI information"
                })
            else:
                index = "HSI"  # Default
                if "nasdaq" in query_lower:
                    index = "NASDAQ"
                elif "dow" in query_lower:
                    index = "DOW"
                    
                workflow.append({
                    "tool": "get_market_index",
                    "parameters": {"index": index},
                    "description": f"Get {index} index data"
                })
        
        # Forex query
        elif any(term in query_lower for term in ["rate", "exchange", "forex", "汇率"]):
            from_curr = "USD"
            to_curr = "HKD"
            
            if "eur" in query_lower:
                from_curr = "EUR"
            elif "gbp" in query_lower:
                from_curr = "GBP"
                
            workflow.append({
                "tool": "get_forex_rate",
                "parameters": {"from_currency": from_curr, "to_currency": to_curr},
                "description": f"Get {from_curr} to {to_curr} exchange rate"
            })
        
        # Default workflow
        if not workflow:
            workflow.append({
                "tool": "get_market_index",
                "parameters": {"index": "HSI"},
                "description": "Get HSI index as default"
            })
            
        return {"workflow": workflow}
    
    def _extract_symbol(self, query: str) -> str:
        """Extract stock symbol from query"""
        query_upper = query.upper()
        
        # Common stock symbols
        common_stocks = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BABA", "TCEHY"]
        for stock in common_stocks:
            if stock in query_upper:
                return stock
        
        # Chinese to symbol mapping
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
        
        return "AAPL"  # Default

    def _execute_workflow(self, workflow_data: dict) -> list:
        """Step 2: Execute workflow by calling corresponding tools"""
        results = []
        
        if "workflow" not in workflow_data:
            return ["Error: Invalid workflow format"]
        
        for step in workflow_data["workflow"]:
            tool_name = step.get("tool", "")
            parameters = step.get("parameters", {})
            description = step.get("description", "")
            
            try:
                # Call corresponding tool method
                if tool_name == "get_stock_price":
                    symbol = parameters.get("symbol", "AAPL")
                    result = self.tools.get_stock_price(symbol)
                
                elif tool_name == "get_forex_rate":
                    from_currency = parameters.get("from_currency", "USD")
                    to_currency = parameters.get("to_currency", "HKD")
                    result = self.tools.get_forex_rate(from_currency, to_currency)
                
                elif tool_name == "get_market_index":
                    index = parameters.get("index", "HSI")
                    result = self.tools.get_market_index(index)
                
                elif tool_name == "get_hsi_details":
                    result = self.tools.get_hsi_details()
                
                elif tool_name == "get_news":
                    symbol = parameters.get("symbol", "AAPL")
                    result = self.tools.get_news(symbol)
                
                elif tool_name == "get_financial_reports":
                    symbol = parameters.get("symbol", "AAPL")
                    result = self.tools.get_financial_reports(symbol)
                
                else:
                    result = f"Unknown tool: {tool_name}"
                
                # Store result with step info
                step_result = {
                    "step": description,
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": result
                }
                results.append(step_result)
                
            except Exception as e:
                error_result = {
                    "step": description,
                    "tool": tool_name,
                    "parameters": parameters,
                    "result": f"Error executing {tool_name}: {str(e)}"
                }
                results.append(error_result)
        
        return results
    
    def _format_results_for_llm(self, results: list) -> str:
        """Step 3: Format execution results as tokens for LLM processing"""
        formatted_data = []
        
        for result_item in results:
            step_info = f"Task: {result_item['step']}"
            tool_info = f"Tool Used: {result_item['tool']}"
            result_info = f"Result: {result_item['result']}"
            
            formatted_data.append(f"{step_info}\n{tool_info}\n{result_info}")
        
        return "\n\n".join(formatted_data)

    def run(self, user_query: str, query: str) -> str:
        """Main entry point - Complete 3-step workflow execution"""
        # Step 1: Generate workflow JSON using LLM
        workflow_data = self._generate_workflow(query)
        
        # Step 2: Execute workflow by calling tools
        execution_results = self._execute_workflow(workflow_data)
        
        # Step 3: Format results as tokens and process through LLM for final response
        formatted_results = self._format_results_for_llm(execution_results)
        final_response = self._call_llm_for_response(user_query, formatted_results)
        
        return final_response
    
    def run_debug(self, query: str) -> dict:
        """Debug version that returns all intermediate steps"""
        # Step 1: Generate workflow
        workflow_data = self._generate_workflow(query)
        
        # Step 2: Execute workflow
        execution_results = self._execute_workflow(workflow_data)
        
        # Step 3: Format and process results
        formatted_results = self._format_results_for_llm(execution_results)
        final_response = self._call_llm_for_response(query, formatted_results)
        
        return {
            "query": query,
            "step1_workflow": workflow_data,
            "step2_execution": execution_results,
            "step3_formatted": formatted_results,
            "final_response": final_response
        }