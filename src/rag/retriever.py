import json
import math
import re
from pathlib import Path

import numpy as np

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")
STOP = set("the a an and or of to in for on is are be with by from as at that this it".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP]


class Retriever:
    """TF-IDF retriever over an ingest.py index. Zero heavy dependencies."""

    def __init__(self, index_dir: str | Path = "index"):
        records = json.loads((Path(index_dir) / "chunks.json").read_text(encoding="utf-8"))
        self.records = records
        postings: dict[str, dict[int, int]] = {}
        for i, rec in enumerate(records):
            for term in tokenize(rec["text"]):
                postings.setdefault(term, {})[i] = postings.get(term, {}).get(i, 0) + 1
        n = len(records)
        idf = {term: math.log(n / len(docs)) for term, docs in postings.items()}
        doc_len = np.array([sum(1 for t in tokenize(r["text"])) for r in records], dtype=float) + 1e-9
        for term, docs in postings.items():
            for i, tf in docs.items():
                postings[term][i] = tf * idf[term] / doc_len[i]
        self.postings = postings

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        scores: dict[int, float] = {}
        for term in set(tokenize(query)):
            for i, w in self.postings.get(term, {}).items():
                scores[i] = scores.get(i, 0.0) + w * w
        best = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        out = []
        for i, score in best:
            rec = self.records[i]
            out.append({**rec, "score": round(score, 4)})
        return out


if __name__ == "__main__":
    for hit in Retriever().search("How is long term capital gain on listed shares taxed?", top_k=3):
        print(f"[{hit['doc']} p.{hit['page']} score={hit['score']}]\n{hit['text'][:200]}\n---")
