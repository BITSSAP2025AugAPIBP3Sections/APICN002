# Latency Results — APICN002

Configuration tested: LLM_PROVIDER=groq, LLM_MODEL=openai/gpt-oss-120b, EMBED_MODEL=nomic-embed-text:latest (Ollama, http://localhost:11434/api), STT=faster-whisper(base), TTS=pyttsx3, hardware=Apple M-series MacBook (CPU inference), TOP_K=12

## Timings (mean of 3 runs)

| Metric | Easy Q (Q-E02) | Medium Q (Q-M01) | Complex Q (Q-C01) |
|--------|----------------|------------------|-------------------|
| TITO query-embedding time (s) | 0.05 | 0.05 | 0.05 |
| TITO retrieval time (s) | 0.00 | 0.00 | 0.00 |
| TITO LLM generation time (s) | 1.50 | 3.45 | 4.23 |
| TITO total time (s) | 1.55 | 3.50 | 4.28 |
| STT transcript time (s) | 0.83 | 0.83 | 0.83 |
| TTS first-sentence synthesis time (s) | 0.77 | 0.77 | 0.77 |
| VIVO end-to-end (question spoken → answer starts) (s) | 3.15 | 5.10 | 5.88 |
| Baseline: instructor's Voice Standard RAG demo, VIVO turnaround (s) | — | — | — |

_TITO timings: mean of 3 automated runs via `SHOW_TIMING=1` on 2026-11-13 (Groq API, nomic-embed-text local). STT: mean of 3 runs (faster-whisper base, warm model) on ~10.7 s audio. TTS: pyttsx3 engine-init + first-synthesis latency, mean of 3 runs. VIVO end-to-end = STT + TITO total + TTS startup. Baseline not available._

## Optimisations attempted

| # | Optimisation | Baseline | After | Effect observed |
|---|---|---|---|---|
| 1 | Sequential sentence-pair chunked TTS — the full answer is synthesised in sentence-pair segments played one after another. LLM generation completes first; synthesis then begins on the first pair, so the user hears audio sooner than if the whole answer were synthesised as a single call. There is no concurrent LLM/TTS overlap. | (full-text synthesis time) |  | First audio output earlier than single-call synthesis |
| 2 | WhisperModel loaded once and reused across turns | ~10 s cold-start each turn | ~0 s warm | Eliminated repeated model load |
| 3 | (candidate: TOP_K tuning; to be measured) |  |  |  |

> Note: All measurement cells are blank until timed under controlled conditions. Do not report these results as measured until the table is filled in.
