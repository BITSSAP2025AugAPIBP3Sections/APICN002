# Submission — APICN002

- Team ID: APICN002
- GitHub repository: https://github.com/BITSSAP2025AugAPIBP3Sections/APICN002
- App entry point: `python src/app.py`
- Default LLM provider: SLM (Ollama, `llama3.2:latest` via `http://localhost:11434/v1`)
- Embedding model: `nomic-embed-text:latest` via Ollama (`http://localhost:11434/api`)
- STT engine: faster-whisper (default local, model: base) with Groq/OpenAI Whisper API options
- TTS engine: pyttsx3 (default local) with Piper and Edge TTS options

## Feature completion

- TITO: text question → RAG retrieval → LLM answer with source citations
- TIVO: TITO + text-to-speech synthesis via configurable TTS provider
- VITO: microphone → faster-whisper transcription → TITO
- VIVO: VITO + TIVO; multi-turn conversation history maintained in session
- RAG ingestion: atomic index writes; embedding retry with exponential backoff; validates count, dimension, and numeric correctness
- Automated tests: 131+ passing unit tests (ingestion pipeline, retrieval (TF-IDF and embedding mode), history management, speech cleanup, STT transcription behaviour, STT recording reliability, deterministic tax calculator FY 2024-25, calculator extraction guards and ₹-prefix handling, Rich CLI helpers, app orchestration, LLM provider selection)

## External data used

- None. All source documents are official Indian government publications included in `data/`.
- Income Tax Act 1961 (~171 MB) is distributed via GitHub Release assets due to file-size limits; all other PDFs are committed to the repository.

## AI coding assistant disclosure

- Claude Code (Anthropic, claude-sonnet-4-6)
    - Session 1: Streamlined configuration updates when adapting the LLM integration to use Ollama's native /api/chat endpoint for llama3.2.
    - Session 2: Improved ingestion pipeline — atomic index writes, embedding retry/validation, memory-optimised page-by-page PDF extraction, comprehensive test suite (44 tests), .gitignore corpus strategy.
    - Session 4: Added mandatory corpus validation to ingestion (fail on missing/unreadable required PDFs, non-zero exit); split latency timing into embed/retrieve/context/LLM in app.py; tightened retriever validation (2D check, zero-norm raise, query NaN/zero check); fixed .gitignore to track all small corpus PDFs; corrected documentation inaccuracies in architecture.md and latency_results.md; test suite now at 77 tests.
    - Session 5: Improved STT reliability — timeout on recording loop queue get (prevents indefinite block when audio callback stops), early catch for audio device errors, temp-file cleanup on sf.write failure, minimum recording duration guard (0.3 s), drain of pre-start audio, early API-key validation with descriptive error, single retry on transient API errors (429/5xx/ConnectionError/Timeout) without retrying permanent 4xx, API response structure validation; fixed fixed-duration recording (seconds= mode) so frames are collected during the deadline rather than after running=False; handle stream __enter__ failure; inspect and log callback status warnings; test suite now at 96 tests.
    - Session 6: RAG quality improvements — temporal year boost in retriever (bs2024_25.pdf +0.06, bs2023_24.pdf −0.05, bs202223.pdf −0.06, bs202122.pdf −0.07) to fix FY2024-25 slab retrieval; expanded SYSTEM_PROMPT with four domain rules (old/new regime ≠ residential status; progressive slabs; new regime Chapter VI-A restriction; 4% cess); increased default max_tokens from 700 to 1500 to prevent answer truncation on multi-step calculations; increased default TOP_K from 5 to 7 (note: app.py change was not in the approved plan — change disclosed here). Full 13-question re-evaluation documented in report/test_results.md. 96 existing tests continue to pass.
    - Session 7: Evidence-based failure analysis across all 10 partial/wrong Stage 6 questions; three targeted improvements: (C1) reduced bs2023_24.pdf year-boost penalty from −0.05 to −0.02 to prevent LRS TCS correct chunk from being buried behind irrelevant budget paragraphs; (A) expanded SYSTEM_PROMPT from 4 to 7 rules adding Section 54 reinvestment guard, Section 112A equity LTCG specificity, and old-regime basic exemption tiers hardcoded in the system prompt; (B) new deterministic tax calculator module src/rag/tax_calc.py (FY 2024-25 new/old regime slab engine, LTCG/STCG special rates, cess, surcharge) integrated into app.py — appended as a programmatic verification block on computation queries. Additional fixes during Stage 7 re-evaluation: extended needs_new detection to include "both" keyword; extended LTCG/STCG regex to handle intervening text ("on equity") and Indian full-rupee format (6,00,000); added stcg_taxable key to return dicts so STCG line renders in format_calculation. Full Stage 7 re-evaluation: 5 correct / 6 partial / 2 wrong (vs Stage 6: 3/8/2). 19 new tax_calc tests added; test suite now 115 passing.
    - Session 8: Evidence-based Stage 8 audit fixes. (S8-A) Added _REALESTATE_RE guard in _reference_calculations() to suppress programmatic block for real-estate capital gains queries — fixes Q-M02 where the block contradicted the correct LLM answer. (S8-B) Added _RESIDENCY_RE guard to suppress programmatic block for residential-status queries — fixes Q-C03 where ₹40L foreign/Indian income was incorrectly used as salary input. (S8-C) Added rule 8 to SYSTEM_PROMPT explicitly contrasting Section 115BBH income tax 30% vs Section 194S TDS 1%, eliminating the 3B model attention failure that caused Q-M04 regression. (S8-D) Strengthened rule A1 vocabulary from "reinvestment of sale proceeds" to "purchased or constructed a new residential house" to match corpus phrasing. (S8-E) Added extraction of other_income (interest), sec80c (PPF/ELSS), sec80d (medical insurance), and sub-lakh amounts to _reference_calculations() for correct Q-C01 computation. (S8-F) Fixed ₹-prefix blocking in LTCG, STCG, interest, and house-loan regexes — amounts preceded by the ₹ symbol were silently mis-extracted. Full Stage 8 re-evaluation: 6 correct / 7 partial / 0 wrong (vs Stage 7: 5/6/2). 16 new integration tests added; test suite now 131 passing.
    - Session 9: Added Arize Phoenix observability — `src/tracing.py` registers an OpenTelemetry tracer provider pointing to Phoenix (`PHOENIX_COLLECTOR_ENDPOINT`, default `http://localhost:6006/v1/traces`); `rag.answer` CHAIN span records `input.value`, `output.value`, `retrieval.documents` (JSON array with doc/page/score), `retrieval.document_count`, and `perf.total_ms`/`perf.llm_ms`; `llm.chat` LLM span records `llm.model_name`, `llm.provider`, `input.value`, and `output.value`; gracefully no-ops when `arize-phoenix-otel` is not installed. Added `arize-phoenix>=4.0` and `arize-phoenix-otel>=0.6` to `requirements.txt`.

    - Rich CLI (teammate): Added Rich-based CLI improvements — `src/ui/` package with styled console helpers (welcome banner, coloured chat bubbles, filename truncation in source citations, timing hidden behind `SHOW_TIMING=1` env var); dim Rich styling for retriever startup messages; README updated with exit-command and `SHOW_TIMING` documentation. Generated automated tests for previously uncovered code paths: `test_console.py`, `test_retriever.py`, `test_app.py`, and `TestLLMProviderSelection` added to `test_llm.py`.

- ChatGPT (OpenAI)
    - Used as a reference to understand different chunking strategies and their potential trade-offs.

## Rubric discrepancy note

The grading rubric's base components (TITO 30 + Structure 10 + RAG 15 + Modes 15 + Latency 10 + Docs 5 + Demo 5 + Integrity 5) sum to 95, not the stated total of 100. The source of the remaining 5 marks is not specified in the rubric as provided. This discrepancy is flagged for instructor clarification.

## One-line claim to fame

Single RAG app supporting all four interaction modes (TITO, TIVO, VITO, VIVO) with a hardened, atomic ingestion pipeline, reliable STT with retry and resource cleanup, swappable LLM/STT/TTS providers, Rich-styled CLI, a deterministic tax calculator covering FY 2024-25 new/old regimes with evidence-backed guards, output validated by Arize Phoenix traceability (CHAIN + LLM spans via OpenTelemetry), and 131+ automated tests.
