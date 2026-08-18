"""Simple policy search (RAG) over a few Navy Federal demo documents."""

from __future__ import annotations

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import KNOWLEDGE_DIR, ROOT

INDEX_PATH = ROOT / "data" / "models" / "rag_index.joblib"


def _docs() -> list[dict]:
    docs = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        docs.append({"title": path.stem.replace("_", " "), "file": path.name, "text": text})
    return docs


def build_index() -> int:
    docs = _docs()
    if not docs:
        raise FileNotFoundError(f"No policy files in {KNOWLEDGE_DIR}")
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([d["text"] for d in docs])
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix, "docs": docs}, INDEX_PATH)
    return len(docs)


def ask(question: str, k: int = 2) -> dict:
    if not INDEX_PATH.exists():
        build_index()
    bundle = joblib.load(INDEX_PATH)
    q = bundle["vectorizer"].transform([question])
    scores = cosine_similarity(q, bundle["matrix"]).ravel()
    order = scores.argsort()[::-1][:k]
    hits = []
    for i in order:
        hits.append({**bundle["docs"][i], "score": float(scores[i])})
    answer = hits[0]["text"][:900] if hits else "No matching policy found."
    return {"question": question, "answer": answer, "sources": hits}
