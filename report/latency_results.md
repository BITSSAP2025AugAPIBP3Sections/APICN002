# Latency Results — APICN002

Configuration tested: LLM_PROVIDER=slm, LLM_MODEL=llama3.2:latest, SLM_BASE_URL=http://localhost:11434/v1, STT=faster-whisper(base), TTS=pyttsx3, hardware=\<CPU/RAM/GPU to be filled in\>

## Timings (mean of 3 runs)

| Metric | Easy Q (Q-E02) | Medium Q (Q-M01) | Complex Q (Q-C01) |
|--------|----------------|------------------|-------------------|
| TITO query-embedding time (s) |  |  |  |
| TITO retrieval time (s) |  |  |  |
| TITO LLM generation time (s) |  |  |  |
| TITO total time (s) |  |  |  |
| STT transcript time (s) |  |  |  |
| TTS first-sentence synthesis time (s) |  |  |  |
| VIVO end-to-end (question spoken → answer starts) (s) |  |  |  |
| Baseline: instructor's Voice Standard RAG demo, VIVO turnaround (s) |  |  |  |

## Optimisations attempted

| # | Optimisation | Baseline | After | Effect observed |
|---|---|---|---|---|
| 1 | Sequential sentence-pair chunked TTS — the full answer is synthesised in sentence-pair segments played one after another. LLM generation completes first; synthesis then begins on the first pair, so the user hears audio sooner than if the whole answer were synthesised as a single call. There is no concurrent LLM/TTS overlap. | (full-text synthesis time) |  | First audio output earlier than single-call synthesis |
| 2 | WhisperModel loaded once and reused across turns | ~10 s cold-start each turn | ~0 s warm | Eliminated repeated model load |
| 3 | (candidate: TOP_K tuning; to be measured) |  |  |  |

> Note: All measurement cells are blank until timed under controlled conditions. Do not report these results as measured until the table is filled in.
