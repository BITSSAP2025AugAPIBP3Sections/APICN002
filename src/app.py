"""APICN002 RAG Income Tax VoiceBot: TITO / TIVO / VITO / VIVO modes.

Modes:
  python src/app.py --mode tito          typed question -> typed answer
  python src/app.py --mode tivo          typed question -> spoken answer
  python src/app.py --mode vito          spoken question -> typed answer
  python src/app.py --mode vivo          spoken question -> spoken answer
  python src/app.py --question "..."     one-shot (handy for latency measurement)

Voice modes need: pip install faster-whisper sounddevice soundfile  (+ pyttsx3 for TTS)
"""
import argparse
import json as _json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv  # noqa: E402
from opentelemetry import trace as _otel  # noqa: E402
from rag.llm import chat  # noqa: E402
from rag.retriever import Retriever  # noqa: E402
from rag.tax_calc import (  # noqa: E402
    format_calculation,
    is_calculation_query,
    new_regime_tax_2024,
    old_regime_tax_2024,
)

load_dotenv()

try:
    from ui import console as ui
    _rich = True
except ImportError:
    ui = None  # type: ignore[assignment]
    _rich = False


def answer(ret: Retriever, question: str, history: list[dict], top_k: int) -> tuple[str, list[dict]]:
    with _otel.get_tracer("apicn002.rag").start_as_current_span("rag.answer") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("input.value", question)

        t0 = time.perf_counter()
        hits = ret.search(question, top_k=top_k)
        t1 = time.perf_counter()
        context = "\n\n".join(h["text"] + f"\n[source: {h['doc']} p.{h['page']}]" for h in hits)
        t2 = time.perf_counter()
        text = chat(question, context, history)
        t3 = time.perf_counter()

        embed_ms = getattr(ret, "_t_embed_ms", (t1 - t0) * 1000)
        search_ms = getattr(ret, "_t_search_ms", 0.0)
        context_ms = (t2 - t1) * 1000
        llm_ms = (t3 - t2) * 1000
        total_ms = (t3 - t0) * 1000
        if os.getenv("SHOW_TIMING"):
            if _rich:
                ui.print_timing(embed_ms, search_ms, context_ms, llm_ms, total_ms)
            else:
                print(
                    f"[timing]  embed {embed_ms:.0f} ms | "
                    f"retrieve {search_ms:.0f} ms | "
                    f"context {context_ms:.0f} ms | "
                    f"LLM {llm_ms:.0f} ms | "
                    f"total {total_ms:.0f} ms"
                )

        span.set_attribute("output.value", text[:2000])
        span.set_attribute("retrieval.document_count", len(hits))
        span.set_attribute("retrieval.documents", _json.dumps(
            [{"doc": h["doc"], "page": h["page"], "score": h["score"]} for h in hits]
        ))
        span.set_attribute("perf.total_ms", round(total_ms, 1))
        span.set_attribute("perf.llm_ms", round(llm_ms, 1))

        if is_calculation_query(question):
            calc_note = _reference_calculations(question)
            if calc_note:
                text = text + "\n\n" + calc_note

        return text, hits


_REALESTATE_RE = re.compile(
    r"\b(residential property|flat|plot|house.{0,20}sold|sold.{0,20}house|"
    r"land|agricultural|property.{0,20}capital gain|capital gain.{0,20}property|"
    r"bought.{0,20}property|property.{0,20}bought)\b",
    re.IGNORECASE,
)

_RESIDENCY_RE = re.compile(
    r"\b(residential status|rnor|non-?resident|days? of stay|"
    r"foreign income|outside india|returned? to india|determine.*status|"
    r"deeming provision|deemed.?resident|section 6)\b",
    re.IGNORECASE,
)


def _reference_calculations(question: str) -> str:
    """Return programmatic tax calculation(s) when the question asks to compute income tax."""
    # Real-estate capital gains: different tax rules, indexation, no equity calculator applicable.
    if _REALESTATE_RE.search(question):
        return ""

    # Residential-status questions: cannot determine Indian vs foreign income split from text.
    if _RESIDENCY_RE.search(question):
        return ""

    q_lower = question.lower()
    needs_new = "new" in q_lower or "new regime" in q_lower or "both" in q_lower or ("regime" not in q_lower)
    needs_old = "old" in q_lower or "both" in q_lower or "compare" in q_lower or "which regime" in q_lower

    # Extract the largest income-like number from the question as the primary salary.
    # Accepts: "18 lakh", "18L", "18,00,000" (Indian full-rupee format)
    all_amounts: list[float] = []
    for mtch in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:lakh|L\b|,00,000)", question, re.IGNORECASE):
        all_amounts.append(float(mtch.group(1)) * 100_000)
    # Bare Indian format like "18,00,000" not already captured above
    for mtch in re.finditer(r"\b(\d{1,2}),(\d{2}),(\d{3})\b", question):
        val = float(mtch.group(1)) * 100_000 + float(mtch.group(2)) * 1000 + float(mtch.group(3))
        all_amounts.append(val)
    # Sub-lakh amounts like "75,000" (for 80D etc.)
    for mtch in re.finditer(r"\b(\d{2,3}),(\d{3})\b", question):
        val = float(mtch.group(1)) * 1000 + float(mtch.group(2))
        all_amounts.append(val)
    if not all_amounts:
        return ""
    salary = max(all_amounts)

    # Extract LTCG, STCG if mentioned.
    ltcg = 0.0
    stcg = 0.0
    m_ltcg = re.search(r"long[- ]term capital gains?[^₹\d]*₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|L\b|,00,000)", question, re.IGNORECASE)
    if m_ltcg:
        ltcg = float(m_ltcg.group(1)) * 100_000
    m_stcg = re.search(r"short[- ]term capital gains?[^₹\d]*₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|L\b|,00,000)", question, re.IGNORECASE)
    if m_stcg:
        stcg = float(m_stcg.group(1)) * 100_000

    # Extract other income components (interest income, if stated).
    other_income = 0.0
    m_interest = re.search(
        r"interest income[^₹\d]*₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|L\b|,00,000)"
        r"|interest income[^₹\d]*₹?\s*(\d{1,3}),(\d{3})",
        question, re.IGNORECASE,
    )
    if m_interest:
        if m_interest.group(1):
            other_income = float(m_interest.group(1)) * 100_000
        else:
            other_income = float(m_interest.group(2)) * 1000 + float(m_interest.group(3))

    # Extract 80C and 80D for old-regime computation.
    # Handle both orderings: "amount in PPF" and "PPF ... amount" (within a tight window).
    sec80c = 0.0
    m_ppf_before = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:lakh|L\b|,00,000)\s+in\s+(?:ppf|elss|nsc|80c\b)",
        question, re.IGNORECASE,
    )
    m_ppf_after = re.search(
        r"(?:ppf|80c)\b[^.;\n]{0,10}(\d+(?:\.\d+)?)\s*(?:lakh|L\b|,00,000)",
        question, re.IGNORECASE,
    )
    if m_ppf_before:
        sec80c = float(m_ppf_before.group(1)) * 100_000
    elif m_ppf_after:
        sec80c = float(m_ppf_after.group(1)) * 100_000

    sec80d = 0.0
    m_80d_before = re.search(
        r"(\d{2,3}),(\d{3})\s+(?:medical insurance|80d\b)"
        r"|(\d+(?:\.\d+)?)\s*(?:lakh|L\b)\s+(?:medical insurance|80d\b)",
        question, re.IGNORECASE,
    )
    m_80d_after = re.search(
        r"(?:medical insurance|80d)\b[^.;\n]{0,30}?(\d{2,3}),(\d{3})\b"
        r"|(?:medical insurance|80d\b)[^.;\n]{0,10}(\d+(?:\.\d+)?)\s*(?:lakh|L\b)",
        question, re.IGNORECASE,
    )
    if m_80d_before:
        if m_80d_before.group(1):
            sec80d = float(m_80d_before.group(1)) * 1000 + float(m_80d_before.group(2))
        else:
            sec80d = float(m_80d_before.group(3)) * 100_000
    elif m_80d_after:
        if m_80d_after.group(1):
            sec80d = float(m_80d_after.group(1)) * 1000 + float(m_80d_after.group(2))
        else:
            sec80d = float(m_80d_after.group(3)) * 100_000

    parts: list[str] = []
    if needs_new or not needs_old:
        r = new_regime_tax_2024(gross_salary=salary, ltcg_equity=ltcg, stcg_equity=stcg, other_income=other_income)
        parts.append(format_calculation(r))
    if needs_old:
        # Extract house loan interest if mentioned (handles "2,00,000" and "2 lakh" formats).
        house_int = 0.0
        m_hl = re.search(
            r"(?:home|house)[- \s]*loan[- \s]*interest[^₹\d]*₹?\s*(\d+(?:\.\d+)?)\s*(?:lakh|L\b|,00,000)",
            question, re.IGNORECASE
        )
        if m_hl:
            house_int = float(m_hl.group(1)) * 100_000
        r_old = old_regime_tax_2024(gross_salary=salary, house_loan_interest=house_int, ltcg_equity=ltcg, stcg_equity=stcg, other_income=other_income, sec80c=sec80c, sec80d=sec80d)
        parts.append(format_calculation(r_old))

    return "\n\n".join(parts) if parts else ""


def cite_sources(hits: list[dict]) -> None:
    if _rich:
        ui.print_sources(hits)
    else:
        seen = []
        for h in hits:
            key = f"{h['doc']} p.{h['page']}"
            if key not in seen:
                seen.append(key)
        print("Sources: " + "; ".join(seen))


def voice_question() -> str | None:
    from speech import stt

    return stt.transcribe(stt.record_to_wav())


def main() -> None:
    from tracing import setup as _phoenix_setup
    _phoenix_setup()

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["tito", "tivo", "vito", "vivo"], default="tito")
    parser.add_argument("--question", help="one-shot question and exit")
    args = parser.parse_args()

    ret = Retriever(os.getenv("INDEX_DIR", "index"))
    history: list[dict] = []

    if not args.question and _rich:
        ui.print_startup(args.mode)
    if args.question:
        text, hits = answer(ret, args.question, history, int(os.getenv("TOP_K", 7)))
        print(text)
        cite_sources(hits)
        if args.mode in ("tivo", "vivo"):
            from speech import tts

            tts.speak(text)
        return

    while True:
        if args.mode in ("vito", "vivo"):
            question = voice_question()
            if not question:
                continue
            if question.strip().lower() in {"quit", "exit", "stop"}:
                break
        else:
            if _rich:
                ui.print_rule()
                question = ui.ask_user()
            else:
                question = input("\nYou> ").strip()
            if not question:
                break
            if question.lower() in {"quit", "exit"}:
                break
        text, hits = answer(ret, question, history, int(os.getenv("TOP_K", 7)))
        if _rich:
            ui.print_bot(text)
        else:
            print(f"\nBot> {text}")
        cite_sources(hits)
        history += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": text[:1800]},
        ]
        if args.mode in ("tivo", "vivo"):
            from speech import tts

            tts.speak(text)


if __name__ == "__main__":
    main()
