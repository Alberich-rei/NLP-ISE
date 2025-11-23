import datetime
import hashlib
from pathlib import Path
from typing import Iterable, List, Sequence

from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader ,WebBaseLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

import config.config as config
from dataset.metadata_store import init_db, upsert_doc

import easyocr
from PIL import Image

import requests
import base64
from google.cloud import vision
import io
import os

DEFAULT_PERSIST_DIR = Path("chroma_db")

def load_embeddings(model_name: str | None = None) -> HuggingFaceBgeEmbeddings:
    """Return a HuggingFace embedding model for vector storage."""
    name = model_name or config.DEFAULT_EMBEDDING_MODEL
    return HuggingFaceBgeEmbeddings(model_name=name)


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF using LangChain's PyPDFLoader."""
    loader = PyPDFLoader(str(path))
    pages = loader.load()
    text_parts = [page.page_content for page in pages if page.page_content]
    return "\n".join(text_parts).strip()


def _read_csv(path: Path) -> str:
    """Extract text from CSV files using LangChain's CSVLoader."""
    loader = CSVLoader(str(path))
    documents = loader.load()
    text_parts = [doc.page_content for doc in documents if doc.page_content]
    return "\n".join(text_parts).strip()


def _load_text(path: Path) -> str:
    """Extract text from plain text files using LangChain's TextLoader."""
    loader = TextLoader(str(path), encoding="utf-8")
    documents = loader.load()
    text_parts = [doc.page_content for doc in documents if doc.page_content]
    return "\n".join(text_parts).strip()


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".csv":
        return _read_csv(path)
    if suffix in {".txt", ".md"}:
        return _load_text(path)
    raise ValueError(f"Unsupported file type: {suffix}")

#处理图片
def extract_text_from_image(image_path: str) -> str:
    """使用 Google Cloud Vision API 和 API 密钥从图片中提取文本"""
    
    # 设置 API 密钥作为请求参数
    url = "https://vision.googleapis.com/v1/images:annotate?key=" + config.VISION_KEY

    # 读取图片内容并转换为Base64编码
    with io.open(image_path, 'rb') as image_file:
        image_content = image_file.read()
        base64_image = base64.b64encode(image_content).decode("utf-8")  # 转为Base64字符串

    # 构建请求体
    json_data = {
        "requests": [
            {
                "image": {
                    "content": base64_image  # 传递Base64编码后的图片内容
                },
                "features": [
                    {
                        "type": "TEXT_DETECTION"  # 使用文本检测功能
                    }
                ]
            }
        ]
    }

    # 发送 POST 请求到 Vision API
    response = requests.post(url, json=json_data)

    # 打印响应的内容
    #print("API Response:", response.json())  # 打印 API 返回的完整响应内容

    # 解析返回结果
    result = response.json()
    if "responses" in result:
        texts = result["responses"][0].get("textAnnotations", [])
        if texts:
            return texts[0]["description"].strip()  # 返回第一个识别的文本块
    return "未从图片中提取到文本"

#处理图片上传
def handle_image_upload(file_path: str) -> int:
    """处理图片上传并将其文本存入Chroma"""
    try:
        # 处理图片并提取文本
        text = extract_text_from_image(file_path)  # 使用EasyOCR从图片中提取文本
        if not text:
            raise ValueError("图片中未能提取到文本。")
        
        # 将提取的文本分块并存入Chroma数据库
        chunk_count = update(file_path)  # 调用更新函数将文本存储到Chroma
        print(f"图片'{file_path}'成功上传，生成了 {chunk_count} 个文本块。")
        return chunk_count
    except Exception as e:
        print(f"图片上传失败: {e}")
        return 0
    
#代码上传
def extract_text_from_code(file_path: str) -> str:
    code_file = open(file_path, 'r', encoding='utf-8')
    code_text = code_file.read()

    if not code_text:
            raise ValueError("代码文件为空或未能提取到有效文本。")

    print(f"成功读取代码文件: {file_path}")  # 调试信息
    return code_text
        
def handle_code_upload(file_path: str) -> int:
    """处理代码文件上传并将其内容存入Chroma"""
    try:
        # 处理图片并提取文本
        text = extract_text_from_code(file_path)  # 使用EasyOCR从图片中提取文本
        if not text:
            raise ValueError("代码中未能提取到文本。")
        
        # 将提取的文本分块并存入Chroma数据库
        chunk_count = update(file_path)  # 调用更新函数将文本存储到Chroma
        print(f"代码'{file_path}'成功上传，生成了 {chunk_count} 个文本块。")
        return chunk_count
    except Exception as e:
        print(f"代码上传失败: {e}")
        return 0




def _build_chunks(text: str) -> Sequence[str]:
    splitter = CharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    return splitter.split_text(text)


def _chunk_metadata(path: Path, chunk_count: int, base_hash: str) -> Iterable[dict]:
    today = datetime.date.today().isoformat()
    for index in range(chunk_count):
        doc_id = f"{base_hash}_{index}"
        yield {
            "doc_id": doc_id,
            "source": path.name,
            "source_type": "uploaded",
            "date": today,
            "cred": 0.6,
            "chunk_id": index,
        }


def update(file_path: str, persist_directory: Path | None = None, model_name: str | None = None) -> int:
    """Parse, embed, and persist the supplied document into Chroma."""

    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    # 判断文件类型
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:  # 图片文件
        text = extract_text_from_image(path)  # 从图片提取文本
    elif suffix in {".py", ".js", ".java"}:  # 图片文件
        text = extract_text_from_code(path)  # 从图片提取文本
    else:
        text = _extract_text(path)  # 普通文件的提取方法

    if not text:
        raise ValueError("The supplied file does not contain extractable text.")

    chunks = list(_build_chunks(text))
    if not chunks:
        raise ValueError("No text chunks were generated from the document.")

    text_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
    metadatas = list(_chunk_metadata(path, len(chunks), text_hash))
    ids = [meta["doc_id"] for meta in metadatas]

    persist_dir = persist_directory or DEFAULT_PERSIST_DIR
    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = load_embeddings(model_name=model_name)
    vector_store = Chroma(persist_directory=str(persist_dir), embedding_function=embeddings)

    vector_store.delete(where={"source": path.name})
    vector_store.add_texts(texts=chunks, metadatas=metadatas, ids=ids)
    vector_store.persist()

    init_db()
    for meta in metadatas:
        upsert_doc(meta["doc_id"], meta)

    return len(chunks)