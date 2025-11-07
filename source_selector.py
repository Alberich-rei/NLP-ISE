
from hk_llm import HKGAIModel
import json

llm = HKGAIModel(system_prompt="You route queries. Only output JSON.")

def select_sources(query):
    prompt = f'''
Classify the user query into sources.
Output JSON:
{{"intent":"...","sources":["rag","weather_tool"...]}}
Query: {query}
'''
    out = llm(prompt)

    try:
        return json.loads(out)
    except:
        q = query.lower()
        if "weather" in q:
            return {"intent":"weather", "sources":["weather_tool"]}
        if "stock" in q or "price" in q:
            return {"intent":"finance", "sources":["finance_tool","local_rag"]}
        return {"intent":"rag", "sources":["local_rag"]}
