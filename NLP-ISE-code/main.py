import os
import time
# 使用独立的 LLM 实现
from llm.hk_llm_independent import HKGAIModel

from dataset.metadata_store import init_db
from agents import create_tool_agent
from config.language_settings import (
    SUPPORTED_LANGUAGES,
    describe_supported_languages,
    get_language_preference,
    set_language_preference,
)
from utils.translation_utils import TranslateModel
from rag.upload import update as upload_document
from rag.upload import handle_code_upload as code_upload
from rag.upload import handle_image_upload as image_upload

from utils.context_manager import ConversationContext

# 检查是否有多模态模块
try:
    from multimodal.parse_pdf import parse_and_index  # type: ignore

    MULTIMODAL_AVAILABLE = True
    print("Multimodal module available")
except ImportError as e:
    MULTIMODAL_AVAILABLE = False
    print(f"Multimodal module not available: {e}")

# 尝试导入 Chroma
try:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

    CHROMA_AVAILABLE = True
    print("Chroma available")
except ImportError as e:
    CHROMA_AVAILABLE = False
    print(f"Chroma not available: {e}")

PERSIST_DIR = "chroma_db"
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_rag():
    if not CHROMA_AVAILABLE:
        return None

    if not os.path.exists(PERSIST_DIR):
        print("Run rag_builder.py first.")
        return None

    try:
        emb = HuggingFaceEmbeddings(model_name=EMB_MODEL)
        db = Chroma(
            persist_directory=PERSIST_DIR, 
            embedding_function=emb
        )
        retriever = db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        return retriever
    except Exception as e:
        print(f"Error loading RAG: {e}")
        return None

def main():
    init_db()
    llm = HKGAIModel()
    translator = TranslateModel()
    retriever = load_rag()
    agent = create_tool_agent(llm, retriever)
    context_manager = ConversationContext(max_history=15)
    # 默认语言为英文
    language_preference = "english"


    if retriever is None and CHROMA_AVAILABLE:
        print("RAG system not available. Please run rag_builder.py first.")
    elif not CHROMA_AVAILABLE:
        print("RAG features disabled due to missing dependencies")

    print("ISE System Ready! (Multi-Agent System)")
    print("Available commands:")
    print("  - <your question> (direct input - ask anything!)")
    print("  - upload <file_path> (upload documents to knowledge base)")
    if MULTIMODAL_AVAILABLE:
        print("  - multimodal upload <file_path>")
    print("  - history (show conversation history)")
    print("  - clear (clear conversation history)")
    print("  - status (show system status)")
    print("  - language [english|cantonese|chinese] (set display/input language)")
    print("  - exit")
    print(f"Current language mode: {language_preference.capitalize()}")

    while True:
        try:
            cmd = input("\n> ").strip()
            if cmd in ("exit", "quit", "q"):
                break

            if cmd.lower().startswith("language"):
                parts = cmd.split()
                if len(parts) == 1:
                    print("Language command usage: language <english|cantonese|chinese>")
                    print("Supported:")
                    print(describe_supported_languages())
                else:
                    choice = parts[1].lower()
                    if choice in SUPPORTED_LANGUAGES:
                        set_language_preference(choice)
                        language_preference = choice
                        print(f"Language preference updated to {choice} ({SUPPORTED_LANGUAGES[choice]}).")
                    else:
                        print(f"Unsupported language '{choice}'. Supported options:")
                        print(describe_supported_languages())
                continue

            if cmd.startswith("upload "):
                f = cmd.split(" ", 1)[1]
                try:
                    if os.path.exists(f):
                        if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                            # 如果是图片文件，处理图片
                            chunk_count = image_upload(f)
                        elif f.lower().endswith(('.py', '.js', '.java')):  # 代码文件
                            chunk_count = code_upload(f)
                        else:
                            chunk_count = upload_document(f)
                        print(f"Successfully uploaded '{f}' - Generated {chunk_count} text chunks")
                        print("Tip: You can now ask questions about this document!")
                    else:
                        print(f"File not found: {f}")
                except Exception as e:
                    print(f"Upload failed: {e}")
                    print("Supported formats: PDF, CSV, TXT, MD, JPG,JPRG, PNG, PY, PY, JS, JAVA")
                continue
            
            if cmd.startswith("multimodal ") and MULTIMODAL_AVAILABLE:
                parts = cmd.split(" ", 2)
                if len(parts) >= 3 and parts[1] == "upload":
                    f = parts[2]
                    if os.path.exists(f):
                        n = parse_and_index(f)
                        print(f"Indexed {n} chunks from {f}")
                    else:
                        print("File not found.")
                continue
            elif cmd.startswith("multimodal "):
                print("Multimodal features not available")
                continue

            # 新增命令：显示对话历史
            if cmd == "history":
                print("\nConversation History:")
                print(context_manager.get_history_summary())
                if context_manager.history:
                    print("\nRecent exchanges:")
                    for i, exchange in enumerate(context_manager.history[-3:], 1):
                        print(f"\n{i}. User: {exchange['user']}")
                        print(f"   Assistant: {exchange['assistant'][:150]}{'...' if len(exchange['assistant']) > 150 else ''}")
                        print(f"   Time: {exchange['timestamp'][:19]}")
                else:
                    print("No conversation history available.")
                continue
            
            # 新增命令：清空对话历史
            if cmd == "clear":
                context_manager.clear_history()
                continue
            
            # 新增命令：显示系统状态
            if cmd == "status":
                print("\nSystem Status:")
                print(f"Multi-Agent System: Weather, Finance, Traffic, RAG")
                print(f"RAG System: {'Available' if retriever else 'Not available'}")
                print(f"Multimodal: {'Available' if MULTIMODAL_AVAILABLE else 'Not available'}")
                print(f"Context: {len(context_manager.history)} conversations stored")
                language_preference = get_language_preference()
                print(f"Language mode: {language_preference} ({SUPPORTED_LANGUAGES.get(language_preference, 'Unknown')})")
                avg = context_manager.get_average_response_time()
                if avg is not None:
                    print(f"Average response time: {avg:.3f} s")
                continue

            # 直接处理用户问题
            q = cmd
            # 所有输入都翻译为英文
            english_query = translator.translate_text(q, language_preference, "english")

            # 获取上下文并调用代理
            context_str = context_manager.get_context_for_agent(use_english=True)
            input_data = {
                "user_query": q,
                "input": english_query,
                "context": context_str,
                "has_history": bool(context_str)
            }

            print(f"\nRouting to appropriate agent...")
            # measure agent invocation time
            start = time.time()
            result = agent.invoke(input_data)
            duration = time.time() - start
            out_en = result.get("output", "")
            # 输出始终为英文
            answer = out_en
            print("Answer:", answer)
            print(f"(Handled in {duration:.3f}s)")

            # 保存这轮对话到上下文（包含耗时）
            context_manager.add_exchange(q, answer, user_en=english_query, assistant_en=out_en, duration_seconds=duration)

            # 每隔几轮对话显示提示
            if len(context_manager.history) % 5 == 0 and len(context_manager.history) > 0:
                print(f"\nTip: {len(context_manager.history)} conversations saved. Type 'history' to view or 'clear' to reset.")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            # 在出错时也保存用户输入，但标记为错误
            if 'q' in locals():
                english_query = locals().get("english_query", q)
                error_message = f"Error occurred: {str(e)}"
                context_manager.add_exchange(q, error_message, user_en=english_query, assistant_en=error_message)
            print("Tip: Type 'status' to check system status or 'clear' to reset context.")
            import traceback
            print(f"Debug info: {traceback.format_exc()[:200]}...")


if __name__ == "__main__":
    main()