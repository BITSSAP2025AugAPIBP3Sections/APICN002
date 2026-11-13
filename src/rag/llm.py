import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URLS = {
    "slm": os.getenv("SLM_BASE_URL", "http://localhost:11434/api"),
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "anthropic": "https://api.anthropic.com/v1",
}

SYSTEM_PROMPT = (
    "You are an Indian Income Tax assistant for a student assignment. "
    "Answer ONLY from the provided context. If the context does not contain the answer, say you cannot find it in the corpus. "
    "Cite the source document name (and page if present) for key claims.\n\n"
    "IMPORTANT DOMAIN RULES:\n"
    "1. The 'old tax regime' and 'new tax regime' are two income-tax filing options for individual taxpayers "
    "(governed by Section 115BAC). They are entirely separate from residential status (Resident, NRI, RNOR). "
    "Never conflate the two.\n"
    "2. Income tax is always computed on progressive slabs — apply each rate only to the income within that "
    "slab band, never apply a single flat rate to the full taxable income.\n"
    "3. Under the new tax regime, deductions under Chapter VI-A (Sections 80C, 80CCC, 80D, 80E, 80EE, etc.) "
    "are NOT available, with the sole exception of the standard deduction for salaried employees (₹75,000) "
    "and the employer NPS contribution under Section 80CCD(2). If you state a deduction is not allowed in a "
    "regime, do NOT subtract it in your calculation.\n"
    "4. Always add 4% Health and Education Cess on the income-tax (after surcharge) as the final step.\n"
    "5. Capital gains exemptions under Section 54, 54B, 54EC, or 54F require explicit reinvestment. "
    "These exemptions apply ONLY when the question explicitly states that the taxpayer has purchased "
    "or constructed a new residential house within the time limits of Section 54, invested in capital "
    "gains bonds, or otherwise met the specific reinvestment condition. If the question asks to compute "
    "capital gains tax without mentioning any such reinvestment, compute tax at the applicable rate and "
    "state that no exemption applies because no reinvestment was mentioned. Do NOT assume reinvestment occurred.\n"
    "6. Long-term capital gains on listed equity shares and equity-oriented mutual funds are taxed under "
    "Section 112A at 12.5% on gains exceeding ₹1,25,000 per year (post July 23, 2024) — NOT under the "
    "general Section 112. Always cite Section 112A for equity LTCG.\n"
    "7. Under the old tax regime, the basic exemption limit is: ₹2,50,000 for individuals below 60 years; "
    "₹3,00,000 for senior citizens (60–80 years); ₹5,00,000 for super senior citizens (above 80 years). "
    "This is settled law even if not stated explicitly in every retrieved document.\n"
    "8. For Virtual Digital Assets (VDA/cryptocurrency): Section 115BBH sets the INCOME TAX rate at "
    "30% flat. Section 194S is a COMPLETELY SEPARATE provision that sets the TDS (tax deducted at "
    "source) rate at 1% — this is a withholding tax the PAYER deducts before transferring payment. "
    "These two sections have different rates for different purposes: 115BBH = 30% income tax; "
    "194S = 1% TDS. Never say the TDS rate under Section 194S is 30%."
)


def _ollama_native(base: str, model: str, messages: list[dict], max_tokens: int) -> str:
    resp = requests.post(
        f"{base}/chat",
        json={"model": model, "messages": messages, "stream": False, "options": {"num_predict": max_tokens, "temperature": 0.2}},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _openai_compatible(base: str, api_key: str, model: str, messages: list[dict], max_tokens: int) -> str:
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _anthropic(api_key: str, model: str, messages: list[dict], max_tokens: int) -> str:
    system_text = "\n".join(m["content"] for m in messages if m["role"] == "system")
    chat = [m for m in messages if m["role"] != "system"]
    resp = requests.post(
        f"{BASE_URLS['anthropic']}/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        json={"model": model, "system": system_text, "messages": chat, "max_tokens": max_tokens},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def llm() -> tuple[str, str, str]:
    provider = os.getenv("LLM_PROVIDER", "slm")
    if provider not in BASE_URLS:
        raise SystemExit(f"LLM_PROVIDER={provider!r} not in {sorted(BASE_URLS)}")
    model = os.getenv("LLM_MODEL") or {
        "slm": "llama3.1:8b",
        "groq": "llama-3.3-70b-versatile",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-20241022",
        "openrouter": "meta-llama/llama-3.1-8b-instruct",
    }[provider]
    keys = {"slm": "SLM_API_KEY", "groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
    return provider, model, os.getenv(keys[provider], "")


def chat(question: str, context: str, history: list[dict] | None = None, max_tokens: int = 1500) -> str:
    provider, model, api_key = llm()
    # Build a new list — never mutate the caller's history.
    # Order: system prompt first, then prior turns, then current context+question.
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + list(history or [])
        + [{"role": "user", "content": f"Context from corpus:\n{context}\n\nQuestion: {question}"}]
    )
    if provider == "anthropic":
        return _anthropic(api_key, model, messages, max_tokens)
    base = BASE_URLS[provider]
    if base.rstrip("/").endswith("/api"):
        return _ollama_native(base, model, messages, max_tokens)
    return _openai_compatible(base, api_key or "ollama", model, messages, max_tokens)
