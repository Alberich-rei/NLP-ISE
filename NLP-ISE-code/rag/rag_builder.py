
import os
import hashlib
import datetime
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from dataset.metadata_store import init_db, upsert_doc

DOCS_DIR = "example_docs"
PERSIST_DIR = "chroma_db"
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def load_docs():
    items = []
    for f in os.listdir(DOCS_DIR):
        p = os.path.join(DOCS_DIR, f)
        if f.endswith(".txt") or f.endswith(".md"):
            text = open(p, encoding="utf-8").read()
            items.append({
                "text": text,
                "fname": f,
                "date": datetime.date.today().isoformat(),
                "cred": 0.6
            })
    return items

def chunk_docs(items):
    splitter = CharacterTextSplitter(chunk_size=800, chunk_overlap=200)
    texts = []
    metas = []

    for it in items:
        parts = splitter.split_text(it["text"])
        for i, chunk in enumerate(parts):
            doc_id = hashlib.sha1((it["fname"]+str(i)).encode()).hexdigest()
            texts.append(chunk)
            metas.append({
                "doc_id": doc_id,
                "source": it["fname"],
                "source_type": "local",
                "date": it["date"],
                "cred": it["cred"],
                "chunk_id": i
            })
    return texts, metas

def build():
    init_db()
    items = load_docs()
    if not items:
        print("No documents found in example_docs/")
        print("Please add some .txt or .md files to the example_docs directory")
        return

    texts, metas = chunk_docs(items)
    emb = HuggingFaceEmbeddings(model_name=EMB_MODEL)

    db = Chroma.from_texts(
        texts=texts,
        embedding=emb,
        metadatas=metas,
        persist_directory=PERSIST_DIR
    )
    db.persist()

    for m in metas:
        upsert_doc(m["doc_id"], m)

    print(f"Indexed {len(texts)} chunks into Chroma.")

if __name__ == "__main__":
    build()
