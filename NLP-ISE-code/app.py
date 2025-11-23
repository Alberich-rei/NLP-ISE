from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from llm.hk_llm_independent import HKGAIModel
from agents import create_tool_agent
from utils.translation_utils import TranslateModel
from config.language_settings import (
    SUPPORTED_LANGUAGES,
    get_language_preference,
    set_language_preference,
)
from dataset.metadata_store import init_db
from rag.upload import update as upload_document
from rag.upload import handle_code_upload as code_upload
from rag.upload import handle_image_upload as image_upload

import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

app = FastAPI()

# 挂载静态文件目录

# 获取绝对路径，确保静态文件挂载和FileResponse都能找到index.html
import os
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 根路由跳转到index.html
@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_path)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
llm = HKGAIModel()
translator = TranslateModel()
agent = create_tool_agent(llm, None)

# 简易上下文管理
class ConversationContext:
    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history
    def add_exchange(self, user_input, agent_output, user_en=None, assistant_en=None):
        import datetime
        user_en = user_en if user_en is not None else user_input
        assistant_en = assistant_en if assistant_en is not None else agent_output
        self.history.append({
            "user": user_input,
            "assistant": agent_output,
            "user_en": user_en,
            "assistant_en": assistant_en,
            "timestamp": datetime.datetime.now().isoformat()
        })
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    def get_context_for_agent(self, use_english=True):
        if not self.history:
            return ""
        recent_history = self.history[-3:]
        context_parts = []
        user_key = "user_en" if use_english else "user"
        assistant_key = "assistant_en" if use_english else "assistant"
        for i, exchange in enumerate(recent_history, 1):
            user_text = exchange.get(user_key) or exchange.get("user")
            assistant_text = exchange.get(assistant_key) or exchange.get("assistant")
            context_parts.append(f"Previous Q{i}: {user_text}")
            snippet = assistant_text if assistant_text is not None else ""
            context_parts.append(f"Previous A{i}: {snippet[:200]}...")
        return "\n".join(context_parts) if context_parts else ""
    def clear_history(self):
        self.history = []

context_manager = ConversationContext(max_history=15)

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

@app.post("/api/upload")
async def upload(request: Request):
    data = await request.json()
    file_path = data.get("file_path", "")
    if not file_path:
        return JSONResponse({"error": "No file_path provided."}, status_code=400)
    if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        chunk_count = image_upload(file_path)
    elif file_path.lower().endswith(('.py', '.js', '.java')):
        chunk_count = code_upload(file_path)
    else:
        chunk_count = upload_document(file_path)
    return JSONResponse({"chunks": chunk_count})

@app.post("/api/clear_history")
async def clear_history():
    context_manager.clear_history()
    return JSONResponse({"status": "cleared"})

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
