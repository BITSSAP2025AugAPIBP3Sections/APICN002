import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
INDEX_PATH = Path(os.getenv("INDEX_DIR", "index"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 900))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))


def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    text = " ".join(text.split())
    while start < len(text):
        chunk = text[start : start + CHUNK_SIZE]
        if chunk.strip():
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
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


def ingest() -> None:
    INDEX_PATH.mkdir(parents=True, exist_ok=True)
    records = []
    for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
        pages, n = open_pdf(pdf_path)
        for page_no, text in enumerate(pages, start=1):
            for chunk in chunk_text(text):
                records.append({"text": chunk, "doc": pdf_path.name, "page": page_no})
        print(f"{pdf_path.name}: {n} pages ingested")
    out = INDEX_PATH / "chunks.json"
    out.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    print(f"Index built: {len(records)} chunks -> {out}")


if __name__ == "__main__":
    ingest()
