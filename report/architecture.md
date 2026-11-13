# Architecture — APICN002

## System Overview

APICN002 is a Retrieval-Augmented Generation (RAG) chatbot that answers Indian Income Tax queries using official government documents. It supports four interaction modes: TITO (text in, text out), TIVO (text in, voice out), VITO (voice in, text out), and VIVO (voice in, voice out).

## Ingestion Pipeline — `src/rag/ingest.py`

PDF extraction uses PyMuPDF (`pymupdf`) with a `pypdf` fallback. Text is extracted one page at a time to limit peak memory usage. The PDF document handle is released in a `try/finally` block after each file, regardless of errors. Malformed or unreadable pages yield an empty string and a warning rather than aborting the run.

Chunking uses a fixed-size sliding window: CHUNK_SIZE = 900 characters, CHUNK_OVERLAP = 150 characters. Boundaries are snapped to word edges. Each chunk stores the source filename and page number.

Embedding calls `nomic-embed-text:latest` through Ollama's `/api/embed` endpoint in batches of 32. Failed requests are retried up to three times with 1 s / 2 s exponential backoff. The response is validated for embedding count, numeric content, and dimension consistency across all batches.

Index persistence uses atomic writes: JSON and NumPy data are written to `.tmp` files, validated by reading them back, and then moved into place with `os.replace()`. Each file replacement is individually atomic. The two replacements are not a single transaction — a crash between them could leave `chunks.json` and `embeddings.npy` from different runs — but the retriever validates count consistency at load time and will report an error rather than silently serving mismatched data.

The index consists of `index/chunks.json` (text, document name, page number) and `index/embeddings.npy` (float32 matrix, one row per chunk).

## Retrieval — `src/rag/retriever.py`

At query time, the user's question is embedded with the same `nomic-embed-text:latest` model. Cosine similarity is computed between the normalised query vector and all pre-normalised corpus embeddings via a single NumPy matrix multiply. The top-k chunks (default k = 5, set via `TOP_K`) are returned with source document and page metadata.

Index integrity is validated at load time: embedding count must match chunk count; NaN and infinite values are rejected; zero-norm rows are flagged. The query embedding dimension is checked against the corpus dimension before search.

If `embeddings.npy` is absent, the retriever falls back to a lightweight TF-IDF inverted index, preserving functionality while the index is being built.

## Answer Generation — `src/rag/llm.py`

Retrieved chunks are assembled into a source-labelled context block: each chunk is followed by a `[source: filename p.page]` label and separated from the next by a blank line. A system prompt instructs the LLM to answer only from the provided context and to cite sources. The conversation history from previous turns is prepended to give the model follow-up question awareness.

Supported providers: Ollama (`llama3.2:latest`, default), Groq, OpenAI, Anthropic, and OpenRouter. Provider, model, and credentials are set via environment variables.

## Interaction Modes — `src/app.py`

TITO: typed question → retrieval → LLM → printed answer with source citations.
TIVO: TITO pipeline + sentence-chunked text-to-speech synthesis.
VITO: press-Enter microphone recording → Whisper transcription → TITO.
VIVO: VITO + TIVO; in-memory history is carried across turns for multi-turn conversations.

## Speech Components

STT (`src/speech/stt.py`): `faster-whisper` for local offline transcription, with Groq and OpenAI Whisper API options. The WhisperModel is loaded once and reused across turns. Temporary WAV files are deleted after transcription.

TTS (`src/speech/tts.py`): `pyttsx3` for offline synthesis; `piper` CLI and `edge-tts` are supported as alternatives. Long answers are split into sentence pairs and each pair is synthesised and played sequentially. Synthesis does not begin until LLM generation is complete; the sentence-pair splitting only reduces the per-synthesis-call duration, it does not overlap with LLM generation. Temporary audio files are deleted after playback.

## Configuration

All parameters are environment-variable–driven via `.env`: LLM provider, model, API keys, embedding model and URL, batch size, STT model and provider, TTS provider and voice, chunk size, overlap, and top-k retrieval count.

## Observability — `src/tracing.py`

Every query is traced end-to-end using OpenTelemetry and exported to Arize Phoenix (`PHOENIX_COLLECTOR_ENDPOINT`, default `http://localhost:6006/v1/traces`). Two spans are emitted per request:

- **`rag.answer`** (kind: CHAIN) — parent span covering retrieval + generation; records `input.value`, `output.value`, `retrieval.documents` (JSON array with doc/page/score), `retrieval.document_count`, `perf.total_ms`, and `perf.llm_ms`.
- **`llm.chat`** (kind: LLM) — child span for the LLM call; records `llm.model_name`, `llm.provider`, `input.value`, and `output.value`.

The tracer setup is a no-op when `arize-phoenix-otel` is not installed, so the app runs without Phoenix in environments where it is not needed.

![Phoenix trace — Q-M04 (3.4 s total, 2.8 s LLM)](images/phoenix_trace_qm04.png)
