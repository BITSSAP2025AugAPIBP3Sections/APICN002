"""RAG document ingestion: build index/chunks.json and index/embeddings.npy from data/*.pdf."""
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
INDEX_PATH = Path(os.getenv("INDEX_DIR", "index"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 900))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text:latest")
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://localhost:11434/api")
EMBED_BATCH = int(os.getenv("EMBED_BATCH", 32))
EMBED_TIMEOUT = int(os.getenv("EMBED_TIMEOUT", 120))

# Mandatory corpus — ingestion fails if any of these is missing or fails to process.
# The Income Tax Act must be downloaded from the repository's Release assets.
MANDATORY_CORPUS: frozenset[str] = frozenset({
    "Income-tax-Act-1961_2026_2026-06-18_02-47-37_b9326c_en.pdf",
    "E-Book-Guidance-Note-Crypto-Asset-Reporting-Obligations.pdf",
    "FAQs-on-BIS-Exemption.pdf",
    "FAQs-on-FIIs-Exemption.pdf",
    "FAQs-on-Transition-Provisions.pdf",
    "Updated-FQAs-on-Interplay&Transitions.pdf",
    "bs202223.pdf",
    "bs2023_24.pdf",
    "bs2024_25(I).pdf",
    "bs2024_25.pdf",
    "bs2025_26.pdf",
})

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_EMBED_RETRIES = 3


def _validate_config() -> None:
    """Raise ValueError listing all configuration problems found."""
    errors: list[str] = []

    if CHUNK_SIZE <= 0:
        errors.append(f"CHUNK_SIZE must be > 0, got {CHUNK_SIZE}")
    if CHUNK_OVERLAP < 0:
        errors.append(f"CHUNK_OVERLAP must be >= 0, got {CHUNK_OVERLAP}")
    if CHUNK_OVERLAP >= CHUNK_SIZE:
        errors.append(
            f"CHUNK_OVERLAP ({CHUNK_OVERLAP}) must be < CHUNK_SIZE ({CHUNK_SIZE})"
        )
    if EMBED_BATCH <= 0:
        errors.append(f"EMBED_BATCH must be > 0, got {EMBED_BATCH}")
    if not EMBED_MODEL:
        errors.append("EMBED_MODEL must not be empty")

    try:
        parsed = urlparse(EMBED_BASE_URL)
        if not parsed.scheme or not parsed.netloc:
            errors.append(f"EMBED_BASE_URL is not a valid URL: {EMBED_BASE_URL!r}")
    except Exception as exc:
        errors.append(f"EMBED_BASE_URL could not be parsed: {exc}")

    if not DATA_DIR.exists():
        errors.append(f"DATA_DIR does not exist: {DATA_DIR}")
    elif not any(DATA_DIR.glob("*.pdf")):
        errors.append(f"DATA_DIR contains no PDF files: {DATA_DIR}")

    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))


def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    text = " ".join(text.split())  # normalise whitespace

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        # Move end boundary back to a word boundary
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Advance start by (chunk_size - overlap), snapping to a word boundary
        next_start = max(start + 1, end - CHUNK_OVERLAP)
        space = text.find(" ", next_start, end)
        start = space + 1 if space != -1 else next_start

    return chunks


def _iter_pages(path: Path):
    """Yield (page_no, text) from a PDF one page at a time.

    Closes the underlying document on completion, error, or generator close.
    Prefers pymupdf; falls back to pypdf when pymupdf is unavailable.
    Raises RuntimeError for documents that cannot be opened.
    Individual unreadable pages yield an empty string and a stderr warning.
    """
    try:
        import pymupdf as _pymupdf  # noqa: PLC0415
    except ImportError:
        _pymupdf = None

    if _pymupdf is not None:
        try:
            doc = _pymupdf.open(str(path))
        except Exception as exc:
            raise RuntimeError(f"pymupdf could not open {path.name}: {exc}") from exc
        try:
            for page_no, page in enumerate(doc, start=1):
                try:
                    yield page_no, page.get_text() or ""
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"  WARNING: {path.name} p{page_no}: {exc}",
                        file=sys.stderr,
                    )
                    yield page_no, ""
        finally:
            doc.close()
        return

    # pypdf fallback
    try:
        from pypdf import PdfReader as _PdfReader  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            f"Cannot extract {path.name}: install pymupdf or pypdf"
        ) from exc

    try:
        reader = _PdfReader(str(path))
    except Exception as exc:
        raise RuntimeError(f"pypdf could not open {path.name}: {exc}") from exc

    for page_no, page in enumerate(reader.pages, start=1):
        try:
            yield page_no, page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            print(f"  WARNING: {path.name} p{page_no}: {exc}", file=sys.stderr)
            yield page_no, ""


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Return embeddings for *texts* with retry and structural validation.

    Retries on transient network and 5xx / 429 errors with exponential backoff.
    Raises immediately on permanent 4xx client errors.
    Raises ValueError if the response structure or dimensions are invalid.
    Raises RuntimeError after all retry attempts are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_EMBED_RETRIES):
        if attempt:
            wait = 2 ** (attempt - 1)  # 1 s, 2 s
            print(
                f"  Retry {attempt}/{_MAX_EMBED_RETRIES - 1} in {wait}s "
                f"(last error: {last_exc})",
                file=sys.stderr,
            )
            time.sleep(wait)

        try:
            resp = requests.post(
                f"{EMBED_BASE_URL}/embed",
                json={"model": EMBED_MODEL, "input": texts},
                timeout=EMBED_TIMEOUT,
            )
            resp.raise_for_status()

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in _RETRYABLE_STATUS:
                raise  # permanent client error — no retry
            last_exc = exc
            continue
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_exc = exc
            continue

        # --- 2xx response received ---
        try:
            data = resp.json()
        except Exception as exc:
            raise ValueError(f"Embedding response is not valid JSON: {exc}") from exc

        embeddings = data.get("embeddings")
        if embeddings is None:
            raise ValueError(
                f"Embedding response missing 'embeddings' key; got keys: {list(data)}"
            )
        if len(embeddings) != len(texts):
            raise ValueError(
                f"Embedding count mismatch: sent {len(texts)} texts, "
                f"got {len(embeddings)} embeddings"
            )

        first_dim: int | None = None
        for idx, emb in enumerate(embeddings):
            if not isinstance(emb, (list, tuple)) or len(emb) == 0:
                raise ValueError(f"Embedding[{idx}] is not a non-empty sequence")
            if not all(isinstance(v, (int, float)) for v in emb):
                raise ValueError(f"Embedding[{idx}] contains non-numeric values")
            if first_dim is None:
                first_dim = len(emb)
            elif len(emb) != first_dim:
                raise ValueError(
                    f"Inconsistent embedding dimensions within response: "
                    f"embedding[0] has {first_dim} dims, "
                    f"embedding[{idx}] has {len(emb)} dims"
                )

        return embeddings

    raise RuntimeError(
        f"Embedding failed after {_MAX_EMBED_RETRIES} attempts. "
        f"Last error: {last_exc}"
    )


def ingest() -> None:
    """Build index/chunks.json and index/embeddings.npy from all PDFs in DATA_DIR.

    Fails with RuntimeError if any mandatory corpus PDF is missing or cannot be
    processed. Writes output atomically so a failed run never replaces a valid index.
    """
    _validate_config()

    t_start = time.time()
    INDEX_PATH.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(DATA_DIR.glob("*.pdf"))
    present_names = {p.name for p in pdf_paths}

    # Fail fast if any mandatory corpus file is absent from DATA_DIR
    missing = sorted(MANDATORY_CORPUS - present_names)
    if missing:
        raise RuntimeError(
            f"Mandatory corpus PDF(s) not found in {DATA_DIR}:\n"
            + "\n".join(f"  - {n}" for n in missing)
            + "\nPlace all PDFs in data/ before running ingestion "
            "(the Income Tax Act is available from the repository's Release assets)."
        )

    records: list[dict] = []
    failed_docs: list[dict] = []
    total_pages = 0

    for pdf_path in pdf_paths:
        page_count = 0
        chunks_before = len(records)
        try:
            for page_no, text in _iter_pages(pdf_path):
                page_count += 1
                for chunk in chunk_text(text):
                    records.append({"text": chunk, "doc": pdf_path.name, "page": page_no})
            total_pages += page_count
            print(
                f"  {pdf_path.name}: {page_count} pages, "
                f"{len(records) - chunks_before} chunks"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: failed to process {pdf_path.name}: {exc}", file=sys.stderr)
            failed_docs.append({"file": pdf_path.name, "error": str(exc)})

    # Fail if any mandatory PDF could not be processed
    if failed_docs:
        mandatory_failures = [d for d in failed_docs if d["file"] in MANDATORY_CORPUS]
        if mandatory_failures:
            lines = "\n".join(f"  - {d['file']}: {d['error']}" for d in mandatory_failures)
            raise RuntimeError(
                f"Ingestion aborted: {len(mandatory_failures)} mandatory PDF(s) failed:\n"
                + lines
                + "\nThe existing index has NOT been modified."
            )

    if not records:
        raise RuntimeError(
            "No chunks generated from any document; aborting to preserve existing index."
        )

    print(f"\nEmbedding {len(records)} chunks in batches of {EMBED_BATCH} "
          f"using {EMBED_MODEL}...")

    embeddings: list[list[float]] = []
    expected_dim: int | None = None
    batch_count = 0

    for i in range(0, len(records), EMBED_BATCH):
        batch_texts = [r["text"] for r in records[i : i + EMBED_BATCH]]
        batch_embs = _embed_batch(batch_texts)

        batch_dim = len(batch_embs[0])
        if expected_dim is None:
            expected_dim = batch_dim
        elif batch_dim != expected_dim:
            raise ValueError(
                f"Embedding dimension changed between batches: "
                f"expected {expected_dim}, got {batch_dim} at batch {batch_count + 1}"
            )

        embeddings.extend(batch_embs)
        batch_count += 1
        print(f"  {min(i + EMBED_BATCH, len(records))}/{len(records)} chunks embedded")

    # Write to temp files, validate, then atomically replace the live index
    tmp_chunks = INDEX_PATH / "chunks.json.tmp"
    tmp_embeddings = INDEX_PATH / "embeddings.npy.tmp"
    try:
        tmp_chunks.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        with open(tmp_embeddings, "wb") as fh:
            np.save(fh, np.array(embeddings, dtype=np.float32))

        # Read back and verify before replacing the live index
        written_records = json.loads(tmp_chunks.read_text(encoding="utf-8"))
        with open(tmp_embeddings, "rb") as fh:
            written_emb = np.load(fh)

        if len(written_records) != len(records):
            raise RuntimeError(
                f"Index validation failed: wrote {len(records)} records, "
                f"read back {len(written_records)}"
            )
        expected_shape = (len(embeddings), expected_dim)
        if written_emb.shape != expected_shape:
            raise RuntimeError(
                f"Index validation failed: embedding shape is {written_emb.shape}, "
                f"expected {expected_shape}"
            )

        os.replace(str(tmp_chunks), str(INDEX_PATH / "chunks.json"))
        os.replace(str(tmp_embeddings), str(INDEX_PATH / "embeddings.npy"))

    except Exception:
        tmp_chunks.unlink(missing_ok=True)
        tmp_embeddings.unlink(missing_ok=True)
        raise

    elapsed = time.time() - t_start
    print(f"\n=== Ingestion complete ===")
    print(f"  PDFs processed:       {len(pdf_paths) - len(failed_docs)} / {len(pdf_paths)}")
    print(f"  Pages processed:      {total_pages}")
    print(f"  Chunks generated:     {len(records)}")
    print(f"  Embedding batches:    {batch_count}")
    print(f"  Embedding dimensions: {expected_dim}")
    print(f"  Total time:           {elapsed:.1f}s")
    if failed_docs:
        print(f"\n  Failed documents ({len(failed_docs)}):")
        for f in failed_docs:
            print(f"    - {f['file']}: {f['error']}")


if __name__ == "__main__":
    try:
        ingest()
    except (ValueError, RuntimeError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
