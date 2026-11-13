import json
import math
import os
import re
import time
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
STOP = set("the a an and or of to in for on is are be with by from as at that this it".split())
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://localhost:11434/api")

try:
    from rich.console import Console as _Con
    _con = _Con()
    def _info(msg: str) -> None:
        _con.print(f"[dim]{msg}[/dim]")
except ImportError:
    _info = print  # type: ignore[assignment]


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
            if emb.ndim != 2:
                raise ValueError(
                    f"Index corrupt: expected 2-D embedding matrix, got shape {emb.shape}"
                )
            if emb.shape[0] != len(self.records):
                raise ValueError(
                    f"Index corrupt: {emb.shape[0]} embeddings but {len(self.records)} chunks"
                )
            if not np.isfinite(emb).all():
                raise ValueError("Index corrupt: embeddings contain NaN or Inf values")
            norms = np.linalg.norm(emb, axis=1)
            zero_rows = np.where(norms < 1e-9)[0]
            if len(zero_rows):
                raise ValueError(
                    f"Index corrupt: {len(zero_rows)} zero-norm embedding row(s) at indices "
                    f"{zero_rows[:5].tolist()} — re-run ingestion to rebuild the index"
                )
            self.embeddings = emb / (norms.reshape(-1, 1) + 1e-9)
            self.use_embeddings = True
            _info(f"[retriever] embedding mode  {len(self.records):,} chunks")
        else:
            self.use_embeddings = False
            self._build_tfidf()
            _info(f"[retriever] TF-IDF mode  {len(self.records):,} chunks")

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
        t0 = time.perf_counter()
        resp = requests.post(
            f"{EMBED_BASE_URL}/embed",
            json={"model": EMBED_MODEL, "input": query},
            timeout=30,
        )
        resp.raise_for_status()
        vec = np.array(resp.json()["embeddings"][0], dtype=np.float32)
        self._t_embed_ms = (time.perf_counter() - t0) * 1000
        if not np.isfinite(vec).all():
            raise ValueError("Query embedding contains NaN or Inf values")
        norm = np.linalg.norm(vec)
        if norm < 1e-9:
            raise ValueError("Query embedding is a zero vector; cannot compute cosine similarity")
        return vec / norm

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        self._t_embed_ms = 0.0
        self._t_search_ms = 0.0
        if self.use_embeddings:
            q = self._embed_query(query)  # sets _t_embed_ms
            if q.shape[0] != self.embeddings.shape[1]:
                raise ValueError(
                    f"Query embedding dimension {q.shape[0]} does not match "
                    f"corpus dimension {self.embeddings.shape[1]}"
                )
            t_s = time.perf_counter()
            scores = self.embeddings @ q
            # Temporal year boost: recent budget documents rank above older ones for current-year queries.
            _YEAR_BOOST: dict[str, float] = {
                "bs2025_26.pdf": 0.00,
                "bs2024_25.pdf": 0.06,
                "bs2023_24.pdf": -0.02,
                "bs202223.pdf": -0.06,
                "bs202122.pdf": -0.07,
            }
            boosted = scores.copy()
            for _idx, _rec in enumerate(self.records):
                _delta = _YEAR_BOOST.get(_rec["doc"], 0.0)
                if _delta != 0.0:
                    boosted[_idx] = scores[_idx] + _delta
            best = np.argsort(boosted)[::-1][:top_k]
            self._t_search_ms = (time.perf_counter() - t_s) * 1000
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
