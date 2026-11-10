"""Smoke test for the APICN000 skeleton. Run: python -m pytest tests/ -q  (or `pip install pytest` first)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag.retriever import Retriever, tokenize  # noqa: E402


def test_tokenize_drops_stopwords() -> None:
    assert "the" not in tokenize("the capital gain")


def test_retriever(tmp_path: Path) -> None:
    records = [
        {"text": "Section 80C allows a deduction of one lakh fifty thousand for provident fund and ELSS.", "doc": "a.pdf", "page": 1},
        {"text": "TCS under section 206C applies to liberalised remittance scheme remittances above seven lakh.", "doc": "b.pdf", "page": 7},
    ]
    (tmp_path / "chunks.json").write_text(json.dumps(records), encoding="utf-8")
    ret = Retriever(tmp_path)
    hits = ret.search("80C deduction limit provident fund", top_k=1)
    assert hits[0]["doc"] == "a.pdf"
