
import math
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import numpy as np

try:
    from sentence_transformers import CrossEncoder
    CE_OK = True
except:
    CE_OK = False

SOURCE_PRIORITY = {"official":0.9, "local":0.8, "news":0.7, "forum":0.5}

def normalize(ar):
    ar = np.array(ar).reshape(-1,1)
    scaler = MinMaxScaler()
    return scaler.fit_transform(ar).flatten()

def rerank(query, docs):
    texts = [d.page_content for d in docs]

    if CE_OK:
        ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        sem = ce.predict([(query, t) for t in texts])
    else:
        sem = [len(t) for t in texts]

    sem = normalize(sem)

    scored = []
    for i, d in enumerate(docs):
        cred = d.metadata.get("cred", 0.5)
        date = d.metadata.get("date", None)

        days = 365
        if date:
            try:
                days = (datetime.now().date() -
                        datetime.fromisoformat(date).date()).days
            except:
                pass

        fresh = math.exp(-0.01 * days)
        src_pri = SOURCE_PRIORITY.get(d.metadata.get("source_type","local"), 0.5)

        score = 0.6*sem[i] + 0.25*cred + 0.1*fresh + 0.05*src_pri
        scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored]
