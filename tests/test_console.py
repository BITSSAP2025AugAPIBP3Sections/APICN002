"""Tests for src/ui/console.py — Rich output helpers."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import ui.console as console_mod
from ui.console import _console


# ---------------------------------------------------------------------------
# _short_doc — filename truncation helper
# ---------------------------------------------------------------------------

class TestShortDoc:
    def test_short_name_unchanged(self):
        assert console_mod._short_doc("bs2024_25.pdf") == "bs2024_25"

    def test_long_name_truncated(self):
        long = "Income-tax-Act-1961_2026_2026-06-18_02-47-37_b9326c_en.pdf"
        result = console_mod._short_doc(long)
        assert len(result) <= console_mod._MAX_DOC_LEN
        assert result.endswith("…")

    def test_exactly_max_len_not_truncated(self):
        name = "a" * console_mod._MAX_DOC_LEN + ".pdf"
        result = console_mod._short_doc(name)
        assert "…" not in result
        assert len(result) == console_mod._MAX_DOC_LEN

    def test_one_over_max_truncated(self):
        name = "a" * (console_mod._MAX_DOC_LEN + 1) + ".pdf"
        result = console_mod._short_doc(name)
        assert result.endswith("…")

    def test_no_pdf_extension_handled(self):
        result = console_mod._short_doc("myfile.txt")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# print_sources — deduplication
# ---------------------------------------------------------------------------

class TestPrintSourcesDeduplication:
    def _sources_text(self, hits: list[dict]) -> str:
        with patch.object(_console, "print") as mock_print:
            console_mod.print_sources(hits)
        if not mock_print.called:
            return ""
        arg = mock_print.call_args[0][0]
        return str(arg)

    def test_empty_hits_prints_nothing(self):
        with patch.object(_console, "print") as mock_print:
            console_mod.print_sources([])
        mock_print.assert_not_called()

    def test_single_hit_shown(self):
        hits = [{"doc": "bs2024_25.pdf", "page": 1}]
        text = self._sources_text(hits)
        assert "bs2024_25" in text
        assert "1" in text

    def test_duplicate_doc_page_shown_once(self):
        hits = [
            {"doc": "a.pdf", "page": 5},
            {"doc": "a.pdf", "page": 5},
        ]
        with patch.object(_console, "print") as mock_print:
            console_mod.print_sources(hits)
        # deduplicated to 1 unique source → exactly 1 combined print call
        assert mock_print.call_count == 1

    def test_different_pages_of_same_doc_both_shown(self):
        hits = [
            {"doc": "a.pdf", "page": 1},
            {"doc": "a.pdf", "page": 2},
        ]
        text = self._sources_text(hits)
        assert "p.1" in text
        assert "p.2" in text

    def test_different_docs_both_shown(self):
        hits = [
            {"doc": "a.pdf", "page": 1},
            {"doc": "b.pdf", "page": 1},
        ]
        text = self._sources_text(hits)
        assert "a" in text
        assert "b" in text

    def test_mixed_duplicates_and_uniques(self):
        hits = [
            {"doc": "a.pdf", "page": 1},
            {"doc": "b.pdf", "page": 3},
            {"doc": "a.pdf", "page": 1},  # duplicate
            {"doc": "c.pdf", "page": 7},
        ]
        with patch.object(_console, "print") as mock_print:
            console_mod.print_sources(hits)
        mock_print.assert_called_once()  # printed exactly once


# ---------------------------------------------------------------------------
# All helpers run without raising
# ---------------------------------------------------------------------------

class TestHelpersDoNotRaise:
    def test_print_user(self):
        with patch.object(_console, "print"):
            console_mod.print_user("What is section 80C?")

    def test_print_bot(self):
        with patch.object(_console, "print"):
            console_mod.print_bot("Section 80C allows a deduction of ₹1.5 lakh.")

    def test_print_bot_multiline(self):
        with patch.object(_console, "print"):
            console_mod.print_bot("Line 1\nLine 2\nLine 3")

    def test_print_timing(self):
        with patch.object(_console, "print"):
            console_mod.print_timing(600.0, 2.0, 0.5, 4172.0, 4781.0)

    def test_print_rule(self):
        with patch.object(_console, "print"):
            console_mod.print_rule()

    def test_print_startup(self):
        with patch.object(_console, "print"):
            console_mod.print_startup("tito")

    def test_print_startup_all_modes(self):
        for mode in ("tito", "tivo", "vito", "vivo"):
            with patch.object(_console, "print"):
                console_mod.print_startup(mode)

    def test_ask_user_returns_string(self):
        with patch.object(_console, "input", return_value="hello"):
            result = console_mod.ask_user()
        assert result == "hello"

    def test_print_bot_wraps_in_panel(self):
        from rich.panel import Panel
        captured = []
        with patch.object(_console, "print", side_effect=lambda x: captured.append(x)):
            console_mod.print_bot("The answer.")
        assert len(captured) == 1
        assert isinstance(captured[0], Panel)

    def test_print_bot_panel_contains_answer(self):
        from rich.panel import Panel
        captured = []
        with patch.object(_console, "print", side_effect=lambda x: captured.append(x)):
            console_mod.print_bot("Capital gains tax applies.")
        assert "Capital gains tax applies." in str(captured[0].renderable)

    def test_print_startup_panel_mentions_mode(self):
        from rich.panel import Panel
        captured = []
        with patch.object(_console, "print", side_effect=lambda x: captured.append(x)):
            console_mod.print_startup("vivo")
        assert len(captured) == 1
        assert isinstance(captured[0], Panel)
        assert "vivo" in str(captured[0].renderable)
