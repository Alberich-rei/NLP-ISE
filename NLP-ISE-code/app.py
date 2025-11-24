from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from llm.hk_llm_independent import HKGAIModel
from agents import create_tool_agent
from utils.translation_utils import TranslateModel

from dataset.metadata_store import init_db
from rag.upload import update as upload_document
from rag.upload import handle_code_upload as code_upload
from rag.upload import handle_image_upload as image_upload

import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import tempfile
import os
import chardet

from utils.context_manager import ConversationContext

app = FastAPI()


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
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

init_db()
llm = HKGAIModel()
translator = TranslateModel()
retriever = load_rag()
agent = create_tool_agent(llm, retriever)
context_manager = ConversationContext(max_history=15)

@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_path)

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("question", "")
    language_preference = data.get("language", "english")
    # 翻译为英文
    english_query = translator.translate_text(user_input, language_preference, "english")
    # 获取上下文
    context_str = context_manager.get_context_for_agent(use_english=True)
    input_data = {
        "user_query": user_input,
        "input": english_query,
        "context": context_str,
        "has_history": bool(context_str)
    }
    result = agent.invoke(input_data)
    out_en = result.get("output", "")
    answer = out_en
    # 保存历史
    context_manager.add_exchange(user_input, answer, user_en=english_query, assistant_en=out_en)
    return JSONResponse({"answer": answer})

def detect_encoding(file_path):
    """检测文件编码"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # 读取前10KB来检测编码
            result = chardet.detect(raw_data)
            return result['encoding'] if result['confidence'] > 0.7 else 'utf-8'
    except:
        return 'utf-8'

def safe_read_file(file_path):
    """安全读取文件内容，处理编码问题"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin1']
    
    # 首先尝试自动检测编码
    detected_encoding = detect_encoding(file_path)
    if detected_encoding and detected_encoding not in encodings:
        encodings.insert(0, detected_encoding)
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read(), encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # 如果所有编码都失败，使用二进制模式读取并尝试解码
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            # 尝试用UTF-8解码，忽略错误
            return raw_data.decode('utf-8', errors='ignore'), 'utf-8'
    except Exception as e:
        raise Exception(f"无法读取文件 {file_path}: {str(e)}")

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # 根据文件类型处理
            if file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                chunk_count = image_upload(temp_file_path)
            elif file.filename.lower().endswith(('.py', '.js', '.java', '.txt', '.md', '.doc', '.docx', '.pdf')):
                # 对于文本文件，先安全读取再处理
                if file.filename.lower().endswith(('.txt', '.md', '.py', '.js', '.java')):
                    try:
                        content, encoding = safe_read_file(temp_file_path)
                        # 重写文件为UTF-8编码
                        with open(temp_file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                    except Exception as e:
                        return JSONResponse({"error": f"文件编码处理失败: {str(e)}"}, status_code=400)
                
                if file.filename.lower().endswith(('.py', '.js', '.java')):
                    chunk_count = code_upload(temp_file_path)
                else:
                    chunk_count = upload_document(temp_file_path)
            else:
                chunk_count = upload_document(temp_file_path)
            
            return JSONResponse({"msg": f"文件上传成功！处理了 {chunk_count} 个数据块。", "chunks": chunk_count})
            
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
    except Exception as e:
        return JSONResponse({"error": f"上传失败: {str(e)}"}, status_code=500)

@app.post("/api/clear_history")
async def clear_history():
    context_manager.clear_history()
    return JSONResponse({"status": "cleared"})

if __name__ == "__main__":
    uvicorn.run("app:app", host="localhost", port=5000, reload=True)
