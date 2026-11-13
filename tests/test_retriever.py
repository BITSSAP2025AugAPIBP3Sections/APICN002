"""Tests for Retriever: embedding mode, corrupt index detection, _embed_query edge cases."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag.retriever import Retriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RECORDS = [
    {"text": "Section 80C deduction provident fund ELSS", "doc": "a.pdf", "page": 1},
    {"text": "Capital gains on listed equity shares exchange", "doc": "b.pdf", "page": 2},
    {"text": "TDS provisions section 194 salary income", "doc": "c.pdf", "page": 3},
]

# Orthogonal unit vectors — cosine similarity to self = 1, to others = 0.
_EMBEDDINGS = np.eye(3, dtype=np.float32)


def _write_index(tmp_path: Path, records: list, embeddings: np.ndarray) -> None:
    (tmp_path / "chunks.json").write_text(json.dumps(records), encoding="utf-8")
    np.save(str(tmp_path / "embeddings.npy"), embeddings.astype(np.float32))


def _make_embed_response(vec: list[float]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"embeddings": [vec]}
    return resp


# ---------------------------------------------------------------------------
# Embedding mode: basic search behaviour
# ---------------------------------------------------------------------------

class TestRetrieverEmbeddingMode:
    def _make(self, tmp_path: Path) -> Retriever:
        _write_index(tmp_path, _RECORDS, _EMBEDDINGS)
        return Retriever(tmp_path)

    def test_embedding_mode_detected(self, tmp_path, capsys):
        self._make(tmp_path)
        assert "embedding mode" in capsys.readouterr().out

    def test_search_returns_top_k_results(self, tmp_path):
        ret = self._make(tmp_path)
        with patch.object(ret, "_embed_query", return_value=np.array([1.0, 0.0, 0.0])):
            hits = ret.search("80C", top_k=2)
        assert len(hits) == 2

    def test_search_returns_most_similar_first(self, tmp_path):
        ret = self._make(tmp_path)
        # Query aligns with record 0 (embedding = [1, 0, 0])
        with patch.object(ret, "_embed_query", return_value=np.array([1.0, 0.0, 0.0])):
            hits = ret.search("Section 80C", top_k=1)
        assert hits[0]["doc"] == "a.pdf"

    def test_search_second_record(self, tmp_path):
        ret = self._make(tmp_path)
        with patch.object(ret, "_embed_query", return_value=np.array([0.0, 1.0, 0.0])):
            hits = ret.search("capital gains", top_k=1)
        assert hits[0]["doc"] == "b.pdf"

    def test_search_includes_score(self, tmp_path):
        ret = self._make(tmp_path)
        with patch.object(ret, "_embed_query", return_value=np.array([1.0, 0.0, 0.0])):
            hits = ret.search("query", top_k=3)
        assert all("score" in h for h in hits)

    def test_best_score_is_one_for_identical_vector(self, tmp_path):
        ret = self._make(tmp_path)
        with patch.object(ret, "_embed_query", return_value=np.array([1.0, 0.0, 0.0])):
            hits = ret.search("query", top_k=1)
        assert hits[0]["score"] == pytest.approx(1.0, abs=0.01)

    def test_top_k_zero_raises(self, tmp_path):
        ret = self._make(tmp_path)
        with pytest.raises(ValueError, match="top_k"):
            ret.search("query", top_k=0)

    def test_top_k_negative_raises(self, tmp_path):
        ret = self._make(tmp_path)
        with pytest.raises(ValueError, match="top_k"):
            ret.search("query", top_k=-1)

    def test_query_dim_mismatch_raises(self, tmp_path):
        ret = self._make(tmp_path)
        wrong_dim = np.array([1.0, 0.0])  # dim 2, corpus is dim 3
        with patch.object(ret, "_embed_query", return_value=wrong_dim):
            with pytest.raises(ValueError, match="dimension"):
                ret.search("query", top_k=1)

    def test_hits_contain_text_doc_page(self, tmp_path):
        ret = self._make(tmp_path)
        with patch.object(ret, "_embed_query", return_value=np.array([1.0, 0.0, 0.0])):
            hits = ret.search("query", top_k=2)
        for h in hits:
            assert "text" in h
            assert "doc" in h
            assert "page" in h


# ---------------------------------------------------------------------------
# Corrupt index detection
# ---------------------------------------------------------------------------

class TestCorruptIndex:
    def test_1d_embeddings_raises(self, tmp_path):
        (tmp_path / "chunks.json").write_text(
            json.dumps([{"text": "t", "doc": "a.pdf", "page": 1}]), encoding="utf-8"
        )
        np.save(str(tmp_path / "embeddings.npy"), np.array([0.1, 0.2, 0.3], dtype=np.float32))
        with pytest.raises(ValueError, match="2-D"):
            Retriever(tmp_path)

    def test_count_mismatch_raises(self, tmp_path):
        records = [
            {"text": "a", "doc": "a.pdf", "page": 1},
            {"text": "b", "doc": "b.pdf", "page": 2},
        ]
        (tmp_path / "chunks.json").write_text(json.dumps(records), encoding="utf-8")
        np.save(str(tmp_path / "embeddings.npy"), np.array([[0.1, 0.2]], dtype=np.float32))
        with pytest.raises(ValueError, match="corrupt"):
            Retriever(tmp_path)

    def test_nan_in_embeddings_raises(self, tmp_path):
        records = [{"text": "t", "doc": "a.pdf", "page": 1}]
        (tmp_path / "chunks.json").write_text(json.dumps(records), encoding="utf-8")
        emb = np.array([[float("nan"), 0.2, 0.3]], dtype=np.float32)
        np.save(str(tmp_path / "embeddings.npy"), emb)
        with pytest.raises(ValueError, match="NaN"):
            Retriever(tmp_path)

    def test_zero_vector_raises(self, tmp_path):
        records = [{"text": "t", "doc": "a.pdf", "page": 1}]
        (tmp_path / "chunks.json").write_text(json.dumps(records), encoding="utf-8")
        emb = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
        np.save(str(tmp_path / "embeddings.npy"), emb)
        with pytest.raises(ValueError, match="zero-norm"):
            Retriever(tmp_path)

    def test_inf_in_embeddings_raises(self, tmp_path):
        records = [{"text": "t", "doc": "a.pdf", "page": 1}]
        (tmp_path / "chunks.json").write_text(json.dumps(records), encoding="utf-8")
        emb = np.array([[float("inf"), 0.2, 0.3]], dtype=np.float32)
        np.save(str(tmp_path / "embeddings.npy"), emb)
        with pytest.raises(ValueError, match="NaN"):
            Retriever(tmp_path)


# ---------------------------------------------------------------------------
# _embed_query
# ---------------------------------------------------------------------------

class TestEmbedQuery:
    def _make(self, tmp_path: Path) -> Retriever:
        _write_index(tmp_path, _RECORDS, _EMBEDDINGS)
        return Retriever(tmp_path)

    def test_returns_normalized_vector(self, tmp_path):
        ret = self._make(tmp_path)
        resp = _make_embed_response([3.0, 4.0, 0.0])  # norm = 5
        with patch("requests.post", return_value=resp):
            q = ret._embed_query("any query")
        assert np.linalg.norm(q) == pytest.approx(1.0, abs=1e-5)

    def test_http_error_raises(self, tmp_path):
        ret = self._make(tmp_path)
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.HTTPError("503")
        with patch("requests.post", return_value=resp):
            with pytest.raises(requests.HTTPError):
                ret._embed_query("query")

    def test_nan_in_response_raises(self, tmp_path):
        ret = self._make(tmp_path)
        resp = _make_embed_response([float("nan"), 0.1, 0.2])
        with patch("requests.post", return_value=resp):
            with pytest.raises(ValueError, match="NaN"):
                ret._embed_query("query")

    def test_zero_vector_response_raises(self, tmp_path):
        ret = self._make(tmp_path)
        resp = _make_embed_response([0.0, 0.0, 0.0])
        with patch("requests.post", return_value=resp):
            with pytest.raises(ValueError, match="zero vector"):
                ret._embed_query("query")

    def test_sets_embed_timing_attribute(self, tmp_path):
        ret = self._make(tmp_path)
        resp = _make_embed_response([1.0, 0.0, 0.0])
        with patch("requests.post", return_value=resp):
            ret._embed_query("query")
        assert hasattr(ret, "_t_embed_ms")
        assert ret._t_embed_ms >= 0
