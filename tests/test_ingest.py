"""Comprehensive tests for the improved RAG ingestion pipeline.

Covers:
  1.  chunk_text with normal text
  2.  chunk_text with empty text
  3.  chunk_text overlap behaviour
  4.  _validate_config with invalid configurations
  5.  _iter_pages resource management (document closed on success and error)
  6.  _embed_batch success path
  7.  _embed_batch response count mismatch
  8.  _embed_batch dimension inconsistency within a batch
  9.  _embed_batch retry on transient failures
  10. ingest() produces a valid, consistent index
  11. ingest() preserves an existing index when ingestion fails
  12. _validate_config with missing DATA_DIR
  13. _validate_config with empty EMBED_MODEL and invalid EMBED_BASE_URL

No real Ollama API calls or PDF files are required.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import rag.ingest as ingest_mod
from rag.ingest import _embed_batch, _iter_pages, _validate_config, chunk_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_success_response(embeddings: list[list[float]]) -> MagicMock:
    """Build a mock requests.Response that returns *embeddings*."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"embeddings": embeddings}
    return resp


def _make_http_error(status_code: int) -> requests.exceptions.HTTPError:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    return requests.exceptions.HTTPError(response=mock_resp)


# ---------------------------------------------------------------------------
# 1. chunk_text — normal text
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_normal_text_produces_chunks(self):
        text = "word " * 300  # 1 500 chars > default CHUNK_SIZE=900
        chunks = chunk_text(text)
        assert len(chunks) >= 2
        assert all(isinstance(c, str) and len(c) > 0 for c in chunks)

    # 2. chunk_text — empty text
    def test_empty_text_returns_empty_list(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert chunk_text("   \n\t  ") == []

    # 3. chunk_text — overlap behaviour
    def test_overlap_shares_content(self):
        with (
            patch.object(ingest_mod, "CHUNK_SIZE", 20),
            patch.object(ingest_mod, "CHUNK_OVERLAP", 5),
        ):
            # Re-import to pick up patched module-level values at call time
            from rag.ingest import chunk_text as _ct
            text = "alpha beta gamma delta epsilon zeta"
            chunks = _ct(text)
        assert len(chunks) >= 2
        # The first word of chunk[1] must appear somewhere in chunk[0]
        first_word_of_second = chunks[1].split()[0]
        assert first_word_of_second in chunks[0]

    def test_short_text_produces_single_chunk(self):
        text = "short"
        chunks = chunk_text(text)
        assert chunks == ["short"]

    def test_no_empty_chunks(self):
        """chunk_text must never append empty strings."""
        text = "a b c d e f g h"
        with (
            patch.object(ingest_mod, "CHUNK_SIZE", 5),
            patch.object(ingest_mod, "CHUNK_OVERLAP", 2),
        ):
            from rag.ingest import chunk_text as _ct
            chunks = _ct(text)
        assert all(c.strip() for c in chunks)

    def test_metadata_preserved_by_caller(self):
        """chunk_text itself is stateless; callers attach doc/page metadata."""
        chunks = chunk_text("Section 80C allows a deduction of one lakh fifty thousand.")
        assert len(chunks) == 1
        assert "80C" in chunks[0]


# ---------------------------------------------------------------------------
# 4. _validate_config — invalid configurations
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def _with_valid_data_dir(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "sample.pdf").touch()
        return data_dir

    def test_valid_config_does_not_raise(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with patch.object(ingest_mod, "DATA_DIR", data_dir):
            _validate_config()  # must not raise

    def test_chunk_size_zero(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "CHUNK_SIZE", 0),
        ):
            with pytest.raises(ValueError, match="CHUNK_SIZE"):
                _validate_config()

    def test_chunk_size_negative(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "CHUNK_SIZE", -1),
        ):
            with pytest.raises(ValueError, match="CHUNK_SIZE"):
                _validate_config()

    def test_chunk_overlap_negative(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "CHUNK_OVERLAP", -1),
        ):
            with pytest.raises(ValueError, match="CHUNK_OVERLAP"):
                _validate_config()

    def test_chunk_overlap_equals_chunk_size(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "CHUNK_SIZE", 100),
            patch.object(ingest_mod, "CHUNK_OVERLAP", 100),
        ):
            with pytest.raises(ValueError, match="CHUNK_OVERLAP"):
                _validate_config()

    def test_embed_batch_zero(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "EMBED_BATCH", 0),
        ):
            with pytest.raises(ValueError, match="EMBED_BATCH"):
                _validate_config()

    # 13. missing/invalid embedding configuration
    def test_embed_model_empty(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "EMBED_MODEL", ""),
        ):
            with pytest.raises(ValueError, match="EMBED_MODEL"):
                _validate_config()

    def test_invalid_embed_base_url(self, tmp_path):
        data_dir = self._with_valid_data_dir(tmp_path)
        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "EMBED_BASE_URL", "not-a-url"),
        ):
            with pytest.raises(ValueError, match="EMBED_BASE_URL"):
                _validate_config()

    # 12. missing DATA_DIR
    def test_missing_data_dir(self, tmp_path):
        with patch.object(ingest_mod, "DATA_DIR", tmp_path / "does_not_exist"):
            with pytest.raises(ValueError, match="DATA_DIR"):
                _validate_config()

    def test_data_dir_exists_but_no_pdfs(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "README.md").write_text("no pdfs here")
        with patch.object(ingest_mod, "DATA_DIR", data_dir):
            with pytest.raises(ValueError, match="no PDF"):
                _validate_config()

    def test_multiple_errors_reported_together(self, tmp_path):
        """All errors should be collected into one ValueError, not raised one at a time."""
        with (
            patch.object(ingest_mod, "DATA_DIR", tmp_path / "missing"),
            patch.object(ingest_mod, "CHUNK_SIZE", 0),
            patch.object(ingest_mod, "EMBED_MODEL", ""),
        ):
            with pytest.raises(ValueError) as exc_info:
                _validate_config()
        msg = str(exc_info.value)
        assert "CHUNK_SIZE" in msg
        assert "EMBED_MODEL" in msg
        assert "DATA_DIR" in msg


# ---------------------------------------------------------------------------
# 5. _iter_pages — PDF resource management
# ---------------------------------------------------------------------------

class TestIterPages:
    def _make_mock_pymupdf(self, page_texts: list[str]) -> tuple[MagicMock, MagicMock]:
        """Return (mock_pymupdf_module, mock_doc) pre-wired with page_texts."""
        pages = []
        for text in page_texts:
            p = MagicMock()
            p.get_text.return_value = text
            pages.append(p)

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(pages))
        mock_doc.__len__ = MagicMock(return_value=len(pages))

        mock_pymupdf = MagicMock()
        mock_pymupdf.open.return_value = mock_doc
        return mock_pymupdf, mock_doc

    def test_yields_page_number_and_text(self):
        mock_pymupdf, _ = self._make_mock_pymupdf(["hello world", "income tax"])
        with patch.dict(sys.modules, {"pymupdf": mock_pymupdf}):
            result = list(_iter_pages(Path("dummy.pdf")))
        assert result == [(1, "hello world"), (2, "income tax")]

    def test_document_closed_after_exhaustion(self):
        mock_pymupdf, mock_doc = self._make_mock_pymupdf(["page one", "page two"])
        with patch.dict(sys.modules, {"pymupdf": mock_pymupdf}):
            list(_iter_pages(Path("dummy.pdf")))  # exhaust the generator
        mock_doc.close.assert_called_once()

    def test_document_closed_when_generator_not_fully_consumed(self):
        """close() must be called even if the caller abandons the generator early."""
        mock_pymupdf, mock_doc = self._make_mock_pymupdf(["p1", "p2", "p3"])
        with patch.dict(sys.modules, {"pymupdf": mock_pymupdf}):
            gen = _iter_pages(Path("dummy.pdf"))
            next(gen)   # consume only the first page
            gen.close() # caller closes early
        mock_doc.close.assert_called_once()

    def test_document_closed_when_page_get_text_raises(self):
        """A bad page must produce an empty string, not crash, and doc must close."""
        mock_page = MagicMock()
        mock_page.get_text.side_effect = Exception("corrupt page")

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        mock_pymupdf = MagicMock()
        mock_pymupdf.open.return_value = mock_doc

        with patch.dict(sys.modules, {"pymupdf": mock_pymupdf}):
            result = list(_iter_pages(Path("dummy.pdf")))

        assert result == [(1, "")]
        mock_doc.close.assert_called_once()

    def test_malformed_pdf_raises_runtime_error(self):
        """An unreadable PDF must raise RuntimeError with a helpful message."""
        mock_pymupdf = MagicMock()
        mock_pymupdf.open.side_effect = Exception("cannot open PDF: bad header")
        with patch.dict(sys.modules, {"pymupdf": mock_pymupdf}):
            with pytest.raises(RuntimeError, match="cannot open PDF"):
                list(_iter_pages(Path("corrupt.pdf")))

    def test_none_get_text_yields_empty_string(self):
        """pymupdf may return None; _iter_pages must convert it to ''."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = None

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        mock_pymupdf = MagicMock()
        mock_pymupdf.open.return_value = mock_doc

        with patch.dict(sys.modules, {"pymupdf": mock_pymupdf}):
            result = list(_iter_pages(Path("dummy.pdf")))
        assert result == [(1, "")]


# ---------------------------------------------------------------------------
# 6-9. _embed_batch
# ---------------------------------------------------------------------------

class TestEmbedBatch:
    # 6. success path
    def test_success_returns_embeddings(self):
        resp = _make_success_response([[0.1, 0.2, 0.3]])
        with patch("requests.post", return_value=resp):
            result = _embed_batch(["Section 80C deduction"])
        assert result == [[0.1, 0.2, 0.3]]

    def test_success_multiple_texts(self):
        embs = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        resp = _make_success_response(embs)
        with patch("requests.post", return_value=resp):
            result = _embed_batch(["a", "b", "c"])
        assert result == embs

    # 7. response count mismatch
    def test_count_mismatch_raises(self):
        resp = _make_success_response([[0.1, 0.2]])  # 1 embedding for 2 texts
        with patch("requests.post", return_value=resp):
            with pytest.raises(ValueError, match="count mismatch"):
                _embed_batch(["text one", "text two"])

    def test_missing_embeddings_key_raises(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"result": "something_else"}
        with patch("requests.post", return_value=resp):
            with pytest.raises(ValueError, match="missing 'embeddings' key"):
                _embed_batch(["text"])

    # 8. embedding dimension inconsistency within one batch
    def test_inconsistent_dims_within_batch_raises(self):
        resp = _make_success_response([[0.1, 0.2, 0.3], [0.1, 0.2]])  # dim 3 then 2
        with patch("requests.post", return_value=resp):
            with pytest.raises(ValueError, match="Inconsistent embedding dimensions"):
                _embed_batch(["text one", "text two"])

    def test_non_numeric_values_raises(self):
        resp = _make_success_response([["a", "b", "c"]])
        with patch("requests.post", return_value=resp):
            with pytest.raises(ValueError, match="non-numeric"):
                _embed_batch(["text"])

    def test_empty_embedding_list_raises(self):
        resp = _make_success_response([[]])  # empty embedding vector
        with patch("requests.post", return_value=resp):
            with pytest.raises(ValueError, match="non-empty"):
                _embed_batch(["text"])

    # 9. retry behaviour
    def test_retry_on_connection_error_then_success(self):
        success_resp = _make_success_response([[0.5, 0.6]])
        side_effects = [
            requests.exceptions.ConnectionError("server down"),
            success_resp,
        ]
        with patch("requests.post", side_effect=side_effects):
            with patch("rag.ingest.time.sleep") as mock_sleep:
                result = _embed_batch(["text"])
        assert result == [[0.5, 0.6]]
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1 s

    def test_retry_on_timeout_then_success(self):
        success_resp = _make_success_response([[0.1, 0.2]])
        side_effects = [
            requests.exceptions.Timeout("timed out"),
            success_resp,
        ]
        with patch("requests.post", side_effect=side_effects):
            with patch("rag.ingest.time.sleep"):
                result = _embed_batch(["text"])
        assert result == [[0.1, 0.2]]

    def test_retry_on_503_then_success(self):
        error_resp = MagicMock()
        error_resp.status_code = 503
        error_resp.raise_for_status.side_effect = _make_http_error(503)

        success_resp = _make_success_response([[0.7, 0.8]])
        side_effects = [error_resp, success_resp]
        with patch("requests.post", side_effect=side_effects):
            with patch("rag.ingest.time.sleep"):
                result = _embed_batch(["text"])
        assert result == [[0.7, 0.8]]

    def test_permanent_400_does_not_retry(self):
        error_resp = MagicMock()
        error_resp.status_code = 400
        error_resp.raise_for_status.side_effect = _make_http_error(400)
        with patch("requests.post", return_value=error_resp) as mock_post:
            with pytest.raises(requests.exceptions.HTTPError):
                _embed_batch(["text"])
        assert mock_post.call_count == 1

    def test_exhausted_retries_raises_runtime_error(self):
        with patch(
            "requests.post",
            side_effect=requests.exceptions.ConnectionError("always down"),
        ):
            with patch("rag.ingest.time.sleep"):
                with pytest.raises(RuntimeError, match="3 attempts"):
                    _embed_batch(["text"])


# ---------------------------------------------------------------------------
# 10-11. ingest() integration tests
# ---------------------------------------------------------------------------

def _setup_ingest_env(tmp_path: Path) -> tuple[Path, Path]:
    """Create data/ and index/ dirs under tmp_path; plant a stub PDF."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "stub.pdf").touch()  # existence check only; _iter_pages is mocked

    index_dir = tmp_path / "index"
    index_dir.mkdir()
    return data_dir, index_dir


def _fake_iter_pages_two_pages(path: Path):
    yield 1, "Section 80C deduction on provident fund contributions"
    yield 2, "Capital gains tax on equity shares listed on stock exchange"


def _fake_embed_batch_dim3(texts: list[str]) -> list[list[float]]:
    return [[0.1, 0.2, 0.3]] * len(texts)


class TestIngest:
    # 10. index persistence and validation
    def test_creates_valid_index(self, tmp_path):
        data_dir, index_dir = _setup_ingest_env(tmp_path)

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"stub.pdf"})),
            patch.object(ingest_mod, "_iter_pages", _fake_iter_pages_two_pages),
            patch.object(ingest_mod, "_embed_batch", _fake_embed_batch_dim3),
        ):
            ingest_mod.ingest()

        chunks_path = index_dir / "chunks.json"
        emb_path = index_dir / "embeddings.npy"
        assert chunks_path.exists(), "chunks.json was not created"
        assert emb_path.exists(), "embeddings.npy was not created"

        records = json.loads(chunks_path.read_text(encoding="utf-8"))
        assert len(records) >= 2
        assert all("text" in r and "doc" in r and "page" in r for r in records)
        assert records[0]["doc"] == "stub.pdf"

        emb = np.load(str(emb_path))
        assert emb.shape == (len(records), 3)
        assert emb.dtype == np.float32

    def test_no_temp_files_remain_after_success(self, tmp_path):
        data_dir, index_dir = _setup_ingest_env(tmp_path)

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"stub.pdf"})),
            patch.object(ingest_mod, "_iter_pages", _fake_iter_pages_two_pages),
            patch.object(ingest_mod, "_embed_batch", _fake_embed_batch_dim3),
        ):
            ingest_mod.ingest()

        assert not (index_dir / "chunks.json.tmp").exists()
        assert not (index_dir / "embeddings.npy.tmp").exists()

    def test_page_numbers_preserved(self, tmp_path):
        data_dir, index_dir = _setup_ingest_env(tmp_path)

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"stub.pdf"})),
            patch.object(ingest_mod, "_iter_pages", _fake_iter_pages_two_pages),
            patch.object(ingest_mod, "_embed_batch", _fake_embed_batch_dim3),
        ):
            ingest_mod.ingest()

        records = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
        pages = {r["page"] for r in records}
        assert 1 in pages
        assert 2 in pages

    # 11. preservation of existing index on failure
    def test_preserves_existing_index_when_embed_fails(self, tmp_path):
        data_dir, index_dir = _setup_ingest_env(tmp_path)

        # Plant a known-good existing index
        existing_records = [
            {"text": "old chunk", "doc": "previous.pdf", "page": 1}
        ]
        existing_emb = np.array([[0.9, 0.8, 0.7]], dtype=np.float32)
        (index_dir / "chunks.json").write_text(
            json.dumps(existing_records), encoding="utf-8"
        )
        np.save(str(index_dir / "embeddings.npy"), existing_emb)

        def failing_embed(texts):
            raise RuntimeError("Ollama server unavailable")

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"stub.pdf"})),
            patch.object(ingest_mod, "_iter_pages", _fake_iter_pages_two_pages),
            patch.object(ingest_mod, "_embed_batch", failing_embed),
        ):
            with pytest.raises(RuntimeError, match="Ollama server unavailable"):
                ingest_mod.ingest()

        # Original index must be intact
        recovered = json.loads(
            (index_dir / "chunks.json").read_text(encoding="utf-8")
        )
        assert recovered == existing_records

        recovered_emb = np.load(str(index_dir / "embeddings.npy"))
        np.testing.assert_array_equal(recovered_emb, existing_emb)

        # Temp files must be cleaned up
        assert not (index_dir / "chunks.json.tmp").exists()
        assert not (index_dir / "embeddings.npy.tmp").exists()

    def test_preserves_existing_index_when_all_pdfs_fail(self, tmp_path):
        data_dir, index_dir = _setup_ingest_env(tmp_path)

        existing_records = [{"text": "existing", "doc": "old.pdf", "page": 1}]
        (index_dir / "chunks.json").write_text(
            json.dumps(existing_records), encoding="utf-8"
        )
        np.save(str(index_dir / "embeddings.npy"), np.array([[0.1, 0.2]], dtype=np.float32))

        def always_fails(path):
            raise RuntimeError("unreadable PDF")
            yield  # make it a generator

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"stub.pdf"})),
            patch.object(ingest_mod, "_iter_pages", always_fails),
        ):
            with pytest.raises(RuntimeError, match="mandatory PDF"):
                ingest_mod.ingest()

        recovered = json.loads(
            (index_dir / "chunks.json").read_text(encoding="utf-8")
        )
        assert recovered == existing_records

    def test_dimension_mismatch_across_batches_raises(self, tmp_path):
        data_dir, index_dir = _setup_ingest_env(tmp_path)

        call_count = {"n": 0}

        def mismatched_embed(texts):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [[0.1, 0.2, 0.3]] * len(texts)
            return [[0.1, 0.2, 0.3, 0.4]] * len(texts)  # dim 4 on second batch

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"stub.pdf"})),
            patch.object(ingest_mod, "EMBED_BATCH", 1),  # one chunk per batch
            patch.object(ingest_mod, "_iter_pages", _fake_iter_pages_two_pages),
            patch.object(ingest_mod, "_embed_batch", mismatched_embed),
        ):
            with pytest.raises(ValueError, match="dimension"):
                ingest_mod.ingest()

    def test_mandatory_pdf_failure_aborts_ingestion(self, tmp_path):
        """A mandatory PDF that cannot be processed must abort ingestion."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "good.pdf").touch()
        (data_dir / "mandatory.pdf").touch()
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        def selective_iter(path):
            if "mandatory" in path.name:
                raise RuntimeError("unreadable mandatory file")
            yield 1, "good content for ingestion"

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"mandatory.pdf"})),
            patch.object(ingest_mod, "_iter_pages", selective_iter),
            patch.object(ingest_mod, "_embed_batch", _fake_embed_batch_dim3),
        ):
            with pytest.raises(RuntimeError, match="mandatory PDF"):
                ingest_mod.ingest()

        # Index must not have been created
        assert not (index_dir / "chunks.json").exists()

    def test_missing_mandatory_pdf_raises(self, tmp_path):
        """Ingestion must fail immediately if a mandatory PDF is absent from DATA_DIR."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "present.pdf").touch()
        # "required.pdf" is mandatory but absent
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"present.pdf", "required.pdf"})),
        ):
            with pytest.raises(RuntimeError, match="required.pdf"):
                ingest_mod.ingest()

    def test_missing_mandatory_pdf_preserves_existing_index(self, tmp_path):
        """Existing index must be untouched when a mandatory PDF is missing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "present.pdf").touch()
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        existing = [{"text": "old chunk", "doc": "x.pdf", "page": 1}]
        (index_dir / "chunks.json").write_text(json.dumps(existing), encoding="utf-8")
        np.save(str(index_dir / "embeddings.npy"), np.array([[0.1, 0.2]], dtype=np.float32))

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"present.pdf", "missing.pdf"})),
        ):
            with pytest.raises(RuntimeError):
                ingest_mod.ingest()

        recovered = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
        assert recovered == existing

    def test_non_mandatory_pdf_failure_does_not_abort(self, tmp_path):
        """A PDF not in MANDATORY_CORPUS that fails is reported but does not abort."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "required.pdf").touch()
        (data_dir / "extra.pdf").touch()
        index_dir = tmp_path / "index"
        index_dir.mkdir()

        def selective_iter(path):
            if "extra" in path.name:
                raise RuntimeError("optional PDF broken")
            yield 1, "required content"

        with (
            patch.object(ingest_mod, "DATA_DIR", data_dir),
            patch.object(ingest_mod, "INDEX_PATH", index_dir),
            patch.object(ingest_mod, "MANDATORY_CORPUS", frozenset({"required.pdf"})),
            patch.object(ingest_mod, "_iter_pages", selective_iter),
            patch.object(ingest_mod, "_embed_batch", _fake_embed_batch_dim3),
        ):
            ingest_mod.ingest()  # must succeed

        records = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
        assert all(r["doc"] == "required.pdf" for r in records)


# ---------------------------------------------------------------------------
# Backwards compatibility — existing smoke tests must still pass
# ---------------------------------------------------------------------------

def test_chunk_text_import():
    """chunk_text must remain importable from rag.ingest."""
    from rag.ingest import chunk_text as ct
    assert ct("hello world") == ["hello world"]
