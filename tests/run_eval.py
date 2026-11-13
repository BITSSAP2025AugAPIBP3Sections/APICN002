"""Run the official question bank through the TITO pipeline and write report/test_results.md.

Usage:
    python3 tests/run_eval.py
"""
import os
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from rag.llm import chat, llm
from rag.retriever import Retriever

QUESTIONS = [
    ("Q-E01", "Easy",    "What are the income tax slab rates for an individual under the new regime for FY 2024-25 (AY 2025-26)?"),
    ("Q-E02", "Easy",    "What is the maximum deduction allowed under Section 80C in a financial year, and name three eligible investments?"),
    ("Q-E03", "Easy",    "What is the basic exemption limit for a resident individual under 60 years of age under the old regime?"),
    ("Q-E04", "Easy",    "What is the standard deduction available to a salaried employee under the new tax regime for FY 2024-25?"),
    ("Q-E05", "Easy",    "What is the tax rate applicable to income from capital gains on listed equity shares held for more than 12 months (long-term capital gains) as per the latest budget?"),
    ("Q-M01", "Medium",  "A salaried individual earns ₹18,00,000 gross annual salary in FY 2024-25, contributes ₹1,50,000 to EPF, pays ₹50,000 NPS Tier-1, and has ₹25,000 health insurance premium. Compute tax under the new regime (assume no other deductions, standard deduction applies)."),
    ("Q-M02", "Medium",  "I bought a residential property for ₹80,00,000 in 2018 and sold it in FY 2024-25 for ₹1,20,00,000. Compute the capital gains tax due (you may state your assumptions on indexation clearly)."),
    ("Q-M03", "Medium",  "An individual transfers ₹12,00,000 in a financial year under the Liberalised Remittance Scheme (LRS) for foreign education. What is the TCS rate that applies after the FY 2023-24 changes to Section 206C, and what exemption applies?"),
    ("Q-M04", "Medium",  "What are the provisions for taxation of Virtual Digital Assets (cryptocurrency) under Section 115BBH, including the rate, the loss set-off rule, and the TDS under Section 194S?"),
    ("Q-M05", "Medium",  "A taxpayer has both salary income and house property income (one self-occupied house with home-loan interest of ₹2,00,000). Under which regime (old vs new) would their tax be lower, and why? Assume gross total income of ₹15,00,000, all of it except the interest deduction being salary."),
    ("Q-C01", "Complex", "Mr. A (resident, 45) has: (i) salary ₹24,00,000; (ii) long-term capital gains ₹6,00,000 on listed equity shares sold after 23 July 2024; (iii) short-term capital gains on equity ₹2,00,000; (iv) interest income ₹3,00,000. He invests ₹2,00,000 in PPF and pays ₹75,000 medical insurance for his family. Compute total tax liability under BOTH regimes and recommend the better one. Show every slab step, surcharge and cess calculation."),
    ("Q-C02", "Complex", "A non-resident FII earned ₹50,00,000 from Indian listed securities in FY 2024-25. Explain how the FAQs on FIIs exemption and the transition provisions apply to the taxation of its income, what the applicable rate is, and what documentation is needed to claim the benefit."),
    ("Q-C03", "Complex", "Compare the treatment of \"days of stay\" for determining residential status for an individual with Indian income of ₹40,00,000 who visited India for 130 days across two visits in a year, referencing the transition/deeming provisions. Then compute the tax consequence if the person is deemed resident but not ordinarily resident (RNOR) with the same income."),
]

TOP_K = int(os.getenv("TOP_K", 8))


def _cell(text: str, limit: int = 300) -> str:
    """Truncate and escape text for a markdown table cell."""
    text = text.replace("\n", " ").replace("|", "\\|").strip()
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def run_question(ret: Retriever, qid: str, question: str) -> dict:
    t0 = time.time()
    hits = ret.search(question, top_k=TOP_K)
    context = "\n\n".join(h["text"] + f"\n[source: {h['doc']} p.{h['page']}]" for h in hits)
    answer = chat(question, context, history=None)
    elapsed = (time.time() - t0) * 1000

    sources = "; ".join(
        f"{h['doc']} p.{h['page']}"
        for h in {f"{h['doc']}:{h['page']}": h for h in hits}.values()
    )

    print(f"  [{elapsed:.0f} ms] {qid} done")
    return {"qid": qid, "question": question, "answer": answer, "sources": sources, "ms": elapsed}


def build_table(results: list[dict], tier: str) -> str:
    rows = [r for r in results if r["qid"].startswith(f"Q-{tier[0]}")]
    lines = [
        "| ID | Question | Answer given | Correct? (yes/partial/no) | Evaluator note | Sources cited |",
        "|----|----------|--------------|---------------------------|----------------|---------------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['qid']} | {_cell(r['question'], 120)} | {_cell(r['answer'])} |  |  | {_cell(r['sources'], 200)} |"
        )
    return "\n".join(lines)


def build_details(results: list[dict]) -> str:
    blocks = []
    for r in results:
        blocks.append(
            f"<details><summary>{r['qid']} — full answer ({r['ms']:.0f} ms)</summary>\n\n"
            f"{r['answer']}\n\n"
            f"**Sources:** {r['sources']}\n\n"
            f"</details>"
        )
    return "\n\n".join(blocks)


def write_report(results: list[dict]) -> None:
    provider, model, _ = llm()
    out = Path(__file__).resolve().parent.parent / "report" / "test_results.md"

    vivo_rows = [
        "| demo/vivo_1.mp3 | Q-E01 |  |  | n/a |  |",
        "| demo/vivo_2.mp3 | Q-E02 |  |  | n/a |  |",
        "| demo/vivo_3.mp3 | Q-E05 |  |  | n/a |  |",
        "| demo/vivo_4.mp3 | Q-M01 |  |  | n/a |  |",
        "| demo/vivo_5.mp3 | Q-M04 |  |  | n/a |  |",
        "| demo/vivo_6.mp3 | Q-C01 |  |  | n/a |  |",
        "| demo/vivo_7.mp3 | Q-C03 |  |  | n/a |  |",
    ]

    content = f"""# TITO Test Results — APICN000

- Date tested: {date.today()}
- LLM_PROVIDER: {provider}
- LLM_MODEL: {model}
- Retrieved top-k: {TOP_K}
- Vector store: {"embedding cosine similarity (nomic-embed-text)" if (Path("index") / "embeddings.npy").exists() else "TF-IDF inverted index"}

## Easy

{build_table(results, "Easy")}

## Medium

{build_table(results, "Medium")}

## Complex

{build_table(results, "Complex")}

## Full answers

{build_details(results)}

## VIVO integration notes

| Demo file | Question ID | Transcript captured? (yes/no) | Answer audible? (yes/no/partial) | Follow-up handled? | Note |
|-----------|-------------|-------------------------------|-----------------------------------|--------------------|------|
{chr(10).join(vivo_rows)}
"""

    out.write_text(content, encoding="utf-8")
    print(f"\nReport written to {out}")


def main() -> None:
    index_dir = os.getenv("INDEX_DIR", "index")
    print(f"Loading index from '{index_dir}'...")
    ret = Retriever(index_dir)

    results = []
    for i, (qid, tier, question) in enumerate(QUESTIONS, 1):
        print(f"[{i}/{len(QUESTIONS)}] {qid} ({tier})")
        results.append(run_question(ret, qid, question))

    write_report(results)


if __name__ == "__main__":
    main()
