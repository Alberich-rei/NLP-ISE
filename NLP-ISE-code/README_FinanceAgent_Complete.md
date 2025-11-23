# FinanceAgent 完整工作流实现

## 三步工作流程 ✅

### Step 1: 接收用户查询，生成工作流JSON
- **输入**: 用户金融查询
- **处理**: 通过LLM和工作流提示词生成结构化JSON
- **输出**: 工具调用工作流

### Step 2: 遍历工作流JSON，调用对应tools
- **输入**: 工作流JSON
- **处理**: 解析每个步骤，调用FinanceTools中对应的方法
- **输出**: 工具执行结果列表

### Step 3: 收集结果作为tokens，给LLM处理返回用户
- **输入**: 工具执行结果
- **处理**: 格式化为LLM可理解的tokens，通过响应提示词生成最终答案
- **输出**: 用户友好的综合响应

## 核心方法

```python
class FinanceAgent:
    def run(self, query: str) -> str:
        """Complete 3-step workflow execution"""
        # Step 1: Generate workflow
        workflow_data = self._generate_workflow(query)
        
        # Step 2: Execute tools
        execution_results = self._execute_workflow(workflow_data)
        
        # Step 3: Process through LLM
        formatted_results = self._format_results_for_llm(execution_results)
        final_response = self._call_llm_for_response(query, formatted_results)
        
        return final_response
```

## 双提示词系统

### 工作流生成提示词 (workflow_prompt)
- 专门用于生成工具调用工作流
- 定义可用工具和参数
- 提供JSON格式示例

### 响应生成提示词 (response_prompt)
- 专门用于生成用户友好的最终响应
- 基于收集的金融数据
- 提供专业且易懂的回答

## 使用示例

```python
# 初始化
agent = FinanceAgent(llm)

# 完整工作流
response = agent.run("Get Apple stock price and USD to HKD rate")

# 调试版本（显示所有中间步骤）
debug_info = agent.run_debug("Get Apple stock price")
```

## 工作流程图

```
用户查询 → Step 1 (LLM+工作流提示词) → 工作流JSON
    ↓
工作流JSON → Step 2 (解析+工具调用) → 执行结果
    ↓  
执行结果 → Step 3 (格式化+LLM+响应提示词) → 最终响应 → 用户
```

## 支持的功能

- ✅ 智能工作流生成
- ✅ 多工具协调执行
- ✅ 结果智能汇总
- ✅ 中英文支持
- ✅ 错误处理
- ✅ 调试模式

## 技术特点

- **英文注释**: 符合代码规范
- **简化架构**: 减少冗余鲁棒性代码
- **工作流驱动**: 基于JSON的灵活架构
- **双LLM调用**: 分离工作流生成和响应生成逻辑