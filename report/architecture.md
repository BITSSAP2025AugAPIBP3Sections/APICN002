# Architecture — APICN000

(paste a hexbin-styled architecture description here)

## Pipelines

- TITO: UI/CLI (src/app.py) → retriever (TF-IDF top-k, src/rag/retriever.py) → llm.chat (provider switch, src/rag/llm.py) → stdout.
- TIVO: TITO + tts.speak (sentence-chunked playback, src/speech/tts.py).
- VITO: record_to_wav (src/speech/stt.py) → transcribe (faster-whisper) → TITO.
- VIVO: chained VITO → TIVO.

## What I would improve next

- replace TF-IDF with embeddings + Chroma/FAISS; 200-word limit — keep it under that.
