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

    text = _extract_text(path)
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