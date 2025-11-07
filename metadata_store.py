
import sqlite3

DB_PATH = "metadata.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_id TEXT UNIQUE,
        source TEXT,
        source_type TEXT,
        date TEXT,
        cred REAL
    )""")

    conn.commit()
    conn.close()

def upsert_doc(doc_id, metadata):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "INSERT OR REPLACE INTO docs (doc_id, source, source_type, date, cred) VALUES (?,?,?,?,?)",
        (
            doc_id,
            metadata.get("source",""),
            metadata.get("source_type","local"),
            metadata.get("date",""),
            metadata.get("cred",0.5)
        )
    )

    conn.commit()
    conn.close()
