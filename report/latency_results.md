# Latency Results — APICN000

Configuration tested: provider=slm, model=llama3.1:8b, STT=faster-whisper(base), TTS=pyttsx3, hardware=<CPU/RAM/GPU>

## Timings (mean of 3 runs)

| Metric | Easy Q (Q-E02) | Medium Q (Q-M01) | Complex Q (Q-C01) |
|--------|----------------|------------------|-------------------|
| TITO time-to-first-token (s) |  |  |  |
| TITO full answer time (s) |  |  |  |
| STT transcript time (s) |  |  |  |
| TTS first audible output (s) |  |  |  |
| VIVO end-to-end (question spoken → answer starts) (s) |  |  |  |
| Baseline: instructor's Voice Standard RAG demo, VIVO turnaround on same machine (s) |  |  |  |

## Optimizations attempted

| # | Optimization | Effect observed |
|---|--------------|-----------------|
| 1 | sentence-chunked TTS (src/speech/tts.py) | first audio arrives before generation finishes |
| 2 | (e.g. switch to qwen2.5:3b, quantize, cache index in memory) |  |
