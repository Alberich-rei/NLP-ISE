
import json
from llm.hk_llm_independent import HKGAIModel

planner = HKGAIModel(system_prompt="Output JSON tasks only.")

def plan_workflow(query):
    prompt = f'''
Break user query into tasks.
Format: [{{"name", "type"(tool|rag|internal), "tool", "args"}}]
Query: {query}
'''
    out = planner(prompt)
    try:
        return json.loads(out)
    except:
        return [{"name":"rag_query","type":"rag","args":{"q":query}}]

def execute_workflow(tasks, tools, retriever, llm):
    ctx = {}

    for t in tasks:
        ttype = t.get("type")

        if ttype == "tool":
            tool = t.get("tool")
            func = tools.get(tool)
            args = t.get("args", {})
            ctx[t["name"]] = func(**args) if func else f"Unknown tool {tool}"

        elif ttype == "rag":
            q = t.get("args",{}).get("q","")
            try:
                if retriever:
                    docs = retriever.invoke(q)
                    ctx[t["name"]] = "\n".join([d.page_content for d in docs[:3]])
                else:
                    ctx[t["name"]] = "RAG system not available"
            except Exception as e:
                ctx[t["name"]] = f"RAG error: {e}"

        else:
            ctx[t["name"]] = "Unsupported"

    summary_prompt = f"Use context: {ctx}\nSummarize the answer."
    return llm(summary_prompt)