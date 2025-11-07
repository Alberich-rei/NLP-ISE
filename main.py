import os

# 使用独立的 LLM 实现
from hk_llm_independent import HKGAIModel

from metadata_store import init_db
from source_selector import select_sources
from reranker import rerank
from workflow_engine import plan_workflow, execute_workflow
from tools import get_weather, get_stock

# 检查是否有多模态模块
try:
    from multimodal.parse_pdf import parse_and_index

    MULTIMODAL_AVAILABLE = True
    print("✅ Multimodal module available")
except ImportError as e:
    MULTIMODAL_AVAILABLE = False
    print(f"⚠ Multimodal module not available: {e}")

# 尝试导入 Chroma
try:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

    CHROMA_AVAILABLE = True
    print("✅ Chroma available")
except ImportError as e:
    CHROMA_AVAILABLE = False
    print(f"⚠ Chroma not available: {e}")

PERSIST_DIR = "chroma_db"
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_rag():
    if not CHROMA_AVAILABLE:
        return None

    if not os.path.exists(PERSIST_DIR):
        print("❌ Run rag_builder.py first.")
        return None

    try:
        emb = HuggingFaceEmbeddings(model_name=EMB_MODEL)
        db = Chroma(persist_directory=PERSIST_DIR, embedding_function=emb)
        retriever = db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        return retriever
    except Exception as e:
        print(f"❌ Error loading RAG: {e}")
        return None


def route_query(llm, retriever, q):
    sel = select_sources(q)
    sources = sel.get("sources", [])

    print(f"🔍 Detected intent: {sel.get('intent', 'unknown')}")
    print(f"📡 Selected sources: {sources}")

    if "local_rag" in sources and retriever:
        try:
            # 手动实现 RAG：检索 + 重排序 + LLM 生成
            docs = retriever.get_relevant_documents(q)[:20]
            docs = rerank(q, docs)[:5]
            ctx = "\n---\n".join([d.page_content for d in docs])
            return llm(
                f"Use the following context to answer the question. If you don't know the answer based on the context, say so.\n\nContext:\n{ctx}\n\nQuestion: {q}\n\nAnswer:")
        except Exception as e:
            print(f"❌ RAG error: {e}")
            return llm(q)

    if "weather_tool" in sources:
        words = q.split()
        city = words[-1] if words else "Beijing"
        weather_info = get_weather(city)
        return llm(f"Question: {q}\nWeather Information:\n{weather_info}")

    if "finance_tool" in sources:
        words = q.split()
        symbol = words[-1].upper() if words else "AAPL"
        stock_info = get_stock(symbol)
        return llm(f"Question: {q}\nStock Information:\n{stock_info}")

    return llm(q)


def main():
    init_db()
    llm = HKGAIModel()
    retriever = load_rag()

    if retriever is None and CHROMA_AVAILABLE:
        print("❌ RAG system not available. Please run rag_builder.py first.")
    elif not CHROMA_AVAILABLE:
        print("⚠ RAG features disabled due to missing dependencies")

    print("🚀 ISE System Ready!")
    print("Available commands:")
    print("  - query <your question>")
    print("  - workflow <complex question>")
    if MULTIMODAL_AVAILABLE:
        print("  - upload <file_path>")
    print("  - exit")

    while True:
        try:
            cmd = input("\n> ").strip()
            if cmd in ("exit", "quit", "q"):
                break

            if cmd.startswith("upload ") and MULTIMODAL_AVAILABLE:
                f = cmd.split(" ", 1)[1]
                if os.path.exists(f):
                    n = parse_and_index(f)
                    print(f"✅ Indexed {n} chunks from {f}")
                else:
                    print("❌ File not found.")
                continue
            elif cmd.startswith("upload "):
                print("❌ Multimodal features not available")
                continue

            if cmd.startswith("workflow "):
                q = cmd.split(" ", 1)[1]
                tasks = plan_workflow(q)
                print("📋 Planned tasks:", tasks)
                out = execute_workflow(
                    tasks,
                    {
                        "weather_tool": get_weather,
                        "finance_tool": get_stock
                    },
                    retriever,
                    llm
                )
                print("🤖 Answer:", out)
                continue

            if cmd.startswith("query "):
                q = cmd.split(" ", 1)[1]
            else:
                q = cmd

            out = route_query(llm, retriever, q)
            print("🤖 Answer:", out)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()