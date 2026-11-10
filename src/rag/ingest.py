import json
import os
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
INDEX_PATH = Path(os.getenv("INDEX_DIR", "index"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 900))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
EMBED_BASE_URL = os.getenv("SLM_BASE_URL", "http://localhost:11434/api")
EMBED_BATCH = int(os.getenv("EMBED_BATCH", 32))


def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    text = " ".join(text.split()) # Normalize whitespace

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        # Move the end boundary to avoid splitting words
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Preserve overlap while maintaining word boundaries
        next_start = max(start + 1, end - CHUNK_OVERLAP)
        space = text.find(" ", next_start, end)

        start = space + 1 if space != -1 else next_start

    return chunks


def open_pdf(path: Path):
    try:
        import pymupdf  # ~35x faster than pypdf on the 1000+ page Income Tax Act

        doc = pymupdf.open(path)
        return [page.get_text() or "" for page in doc], len(doc)
    except ImportError:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return [page.extract_text() or "" for page in reader.pages], len(reader.pages)


def _embed_batch(texts: list[str]) -> list[list[float]]:
    resp = requests.post(
        f"{EMBED_BASE_URL}/embed",
        json={"model": EMBED_MODEL, "input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def ingest() -> None:
    INDEX_PATH.mkdir(parents=True, exist_ok=True)
    records = []
    for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
        pages, n = open_pdf(pdf_path)
        for page_no, text in enumerate(pages, start=1):
            for chunk in chunk_text(text):
                records.append({"text": chunk, "doc": pdf_path.name, "page": page_no})
        print(f"{pdf_path.name}: {n} pages ingested")

    print(f"Embedding {len(records)} chunks with {EMBED_MODEL}...")
    texts = [r["text"] for r in records]
    embeddings = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        embeddings.extend(_embed_batch(batch))
        print(f"  {min(i + EMBED_BATCH, len(texts))}/{len(texts)}")

    out = INDEX_PATH / "chunks.json"
    out.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    np.save(INDEX_PATH / "embeddings.npy", np.array(embeddings, dtype=np.float32))
    print(f"Index built: {len(records)} chunks -> {out}")


if __name__ == "__main__":
    ingest()
