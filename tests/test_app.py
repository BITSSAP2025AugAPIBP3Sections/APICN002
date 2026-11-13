"""Tests for src/app.py: answer() orchestration and cite_sources() deduplication."""
import sys
from pathlib import Path
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import app as app_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HITS = [
    {"text": "Section 80C allows 1.5 lakh deduction.", "doc": "bs2024_25.pdf", "page": 12, "score": 0.9},
    {"text": "80C investments include PPF and ELSS.", "doc": "bs2024_25.pdf", "page": 13, "score": 0.8},
    {"text": "Capital gains on equity.", "doc": "bs2023_24.pdf", "page": 5, "score": 0.6},
]


def _run_answer(question="What is 80C?", history=None, top_k=3, llm_reply="The limit is 1.5 lakh."):
    mock_ret = MagicMock()
    mock_ret.search.return_value = _HITS
    mock_ret._t_embed_ms = 100.0
    mock_ret._t_search_ms = 2.0
    with (
        patch.object(app_mod, "chat", return_value=llm_reply),
        patch.object(app_mod, "_rich", False),
        patch("builtins.print"),
    ):
        text, hits = app_mod.answer(mock_ret, question, history or [], top_k)
    return text, hits, mock_ret


# ---------------------------------------------------------------------------
# answer()
# ---------------------------------------------------------------------------

class TestAnswer:
    def test_returns_llm_text(self):
        text, _, _ = _run_answer(llm_reply="Section 80C allows 1.5 lakh.")
        assert text == "Section 80C allows 1.5 lakh."

    def test_returns_hits_from_retriever(self):
        _, hits, mock_ret = _run_answer()
        assert hits is mock_ret.search.return_value

    def test_calls_search_with_correct_top_k(self):
        _, _, mock_ret = _run_answer(top_k=7)
        mock_ret.search.assert_called_once_with("What is 80C?", top_k=7)

    def test_calls_search_with_question(self):
        _, _, mock_ret = _run_answer(question="What is HRA exemption?")
        call_args = mock_ret.search.call_args
        assert call_args[0][0] == "What is HRA exemption?"

    def test_passes_history_to_chat(self):
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]
        mock_ret = MagicMock()
        mock_ret.search.return_value = _HITS
        mock_ret._t_embed_ms = 0.0
        mock_ret._t_search_ms = 0.0
        with (
            patch.object(app_mod, "chat", return_value="answer") as mock_chat,
            patch.object(app_mod, "_rich", False),
            patch("builtins.print"),
        ):
            app_mod.answer(mock_ret, "Q2", history, 3)
        called_history = mock_chat.call_args[0][2]
        assert called_history == history

    def test_does_not_mutate_history(self):
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]
        before = [dict(m) for m in history]
        _run_answer(history=history)
        assert history == before

    def test_empty_history_allowed(self):
        text, hits, _ = _run_answer(history=[])
        assert isinstance(text, str)
        assert isinstance(hits, list)

    def test_context_built_from_hits(self):
        """chat() must receive context that includes text and source info from all hits."""
        mock_ret = MagicMock()
        mock_ret.search.return_value = _HITS
        mock_ret._t_embed_ms = 0.0
        mock_ret._t_search_ms = 0.0
        with (
            patch.object(app_mod, "chat", return_value="ok") as mock_chat,
            patch.object(app_mod, "_rich", False),
            patch("builtins.print"),
        ):
            app_mod.answer(mock_ret, "q", [], 3)
        context_arg = mock_chat.call_args[0][1]
        assert "80C" in context_arg
        assert "bs2024_25.pdf" in context_arg


# ---------------------------------------------------------------------------
# cite_sources() — deduplication (plain fallback path)
# ---------------------------------------------------------------------------

class TestCiteSourcesFallback:
    def _capture(self, hits):
        buf = StringIO()
        with (
            patch.object(app_mod, "_rich", False),
            patch("builtins.print", side_effect=lambda msg: buf.write(msg + "\n")),
        ):
            app_mod.cite_sources(hits)
        return buf.getvalue()

    def test_single_source_shown(self):
        hits = [{"doc": "a.pdf", "page": 1, "text": "t", "score": 0.9}]
        out = self._capture(hits)
        assert "a.pdf p.1" in out

    def test_duplicate_shown_once(self):
        hits = [
            {"doc": "a.pdf", "page": 1, "text": "t", "score": 0.9},
            {"doc": "a.pdf", "page": 1, "text": "t2", "score": 0.8},
        ]
        out = self._capture(hits)
        assert out.count("a.pdf p.1") == 1

    def test_different_pages_both_shown(self):
        hits = [
            {"doc": "a.pdf", "page": 1, "text": "t", "score": 0.9},
            {"doc": "a.pdf", "page": 2, "text": "t2", "score": 0.7},
        ]
        out = self._capture(hits)
        assert "a.pdf p.1" in out
        assert "a.pdf p.2" in out

    def test_empty_hits_shows_empty_sources(self):
        out = self._capture([])
        assert "Sources:" in out

    def test_preserves_insertion_order(self):
        hits = [
            {"doc": "z.pdf", "page": 9, "text": "t", "score": 0.9},
            {"doc": "a.pdf", "page": 1, "text": "t2", "score": 0.8},
        ]
        out = self._capture(hits)
        assert out.index("z.pdf") < out.index("a.pdf")


# ---------------------------------------------------------------------------
# cite_sources() — rich path delegates to ui.print_sources
# ---------------------------------------------------------------------------

class TestCiteSourcesRichPath:
    def test_delegates_to_ui_print_sources(self):
        hits = [{"doc": "a.pdf", "page": 1, "text": "t", "score": 0.9}]
        mock_ui = MagicMock()
        with (
            patch.object(app_mod, "_rich", True),
            patch.object(app_mod, "ui", mock_ui),
        ):
            app_mod.cite_sources(hits)
        mock_ui.print_sources.assert_called_once_with(hits)
