import json
import math
import os
import re
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
STOP = set("the a an and or of to in for on is are be with by from as at that this it".split())
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
EMBED_BASE_URL = os.getenv("SLM_BASE_URL", "http://localhost:11434/api")


def _stem(t: str) -> str:
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in TOKEN_RE.findall(text.lower()) if t not in STOP]


class Retriever:
    def __init__(self, index_dir: str | Path = "index"):
        index_dir = Path(index_dir)
        self.records = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))

        emb_path = index_dir / "embeddings.npy"
        if emb_path.exists():
            emb = np.load(emb_path)
            norms = np.linalg.norm(emb, axis=1, keepdims=True)
            self.embeddings = emb / (norms + 1e-9)
            self.use_embeddings = True
            print(f"[retriever] embedding mode ({len(self.records)} chunks)")
        else:
            self.use_embeddings = False
            self._build_tfidf()
            print(f"[retriever] TF-IDF mode ({len(self.records)} chunks)")

    def _build_tfidf(self) -> None:
        postings: dict[str, dict[int, int]] = {}
        for i, rec in enumerate(self.records):
            for term in tokenize(rec["text"]):
                postings.setdefault(term, {})[i] = postings.get(term, {}).get(i, 0) + 1
        n = len(self.records)
        idf = {term: math.log(n / len(docs)) for term, docs in postings.items()}
        doc_len = np.array([sum(1 for _ in tokenize(r["text"])) for r in self.records], dtype=float) + 1e-9
        for term, docs in postings.items():
            for i, tf in docs.items():
                postings[term][i] = tf * idf[term] / doc_len[i]
        self.postings = postings

    def _embed_query(self, query: str) -> np.ndarray:
        resp = requests.post(
            f"{EMBED_BASE_URL}/embed",
            json={"model": EMBED_MODEL, "input": query},
            timeout=30,
        )
        resp.raise_for_status()
        vec = np.array(resp.json()["embeddings"][0], dtype=np.float32)
        return vec / (np.linalg.norm(vec) + 1e-9)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.use_embeddings:
            q = self._embed_query(query)
            scores = self.embeddings @ q
            best = np.argsort(scores)[::-1][:top_k]
            return [{**self.records[i], "score": round(float(scores[i]), 4)} for i in best]

        scores: dict[int, float] = {}
        for term in set(tokenize(query)):
            for i, w in self.postings.get(term, {}).items():
                scores[i] = scores.get(i, 0.0) + w * w
        best = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        return [{**self.records[i], "score": round(score, 4)} for i, score in best]


if __name__ == "__main__":
    for hit in Retriever().search("How is long term capital gain on listed shares taxed?", top_k=3):
        print(f"[{hit['doc']} p.{hit['page']} score={hit['score']}]\n{hit['text'][:200]}\n---")
