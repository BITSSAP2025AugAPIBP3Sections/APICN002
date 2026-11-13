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
- Automated tests: passing unit tests (ingestion pipeline, retrieval (TF-IDF and embedding mode), history management, speech cleanup, STT transcription behaviour, STT recording reliability, Rich CLI helpers, app orchestration, LLM provider selection)

## External data used

- None. All source documents are official Indian government publications included in `data/`.
- Income Tax Act 1961 (~171 MB) is distributed via GitHub Release assets due to file-size limits; all other PDFs are committed to the repository.

## AI coding assistant disclosure

- Claude Code (Anthropic, claude-sonnet-4-6)
    - Streamlined configuration updates when adapting the LLM integration to use Ollama's native /api/chat endpoint for llama3.2.
    - Improved ingestion pipeline — atomic index writes, embedding retry/validation, memory-optimised page-by-page PDF extraction, comprehensive test suite (44 tests), .gitignore corpus strategy.
    - Improved STT reliability — timeout on recording loop queue get (prevents indefinite block when audio callback stops), early catch for audio device errors, temp-file cleanup on sf.write failure, minimum recording duration guard (0.3 s), drain of pre-start audio, early API-key validation with descriptive error, single retry on transient API errors (429/5xx/ConnectionError/Timeout) without retrying permanent 4xx, API response structure validation; fixed fixed-duration recording (seconds= mode) so frames are collected during the deadline rather than after running=False; handle stream __enter__ failure; inspect and log callback status warnings; test suite now at 96 tests.
    - Added Rich-based CLI improvements — `src/ui/` package with styled console helpers (welcome banner, coloured chat bubbles, filename truncation in source citations, timing hidden behind `SHOW_TIMING=1` env var); dim Rich styling for retriever startup messages; README updated with exit-command and `SHOW_TIMING` documentation.
    - Generated automated tests for previously uncovered code paths: `test_console.py` (Rich helper rendering and `print_sources` deduplication), `test_retriever.py` (embedding-mode search ordering, corrupt-index detection, `_embed_query` edge cases), `test_app.py` (`answer()` orchestration, `cite_sources()` deduplication in both Rich and plain paths), and `TestLLMProviderSelection` added to `test_llm.py` (provider/model defaults, unknown-provider `SystemExit`, API key lookup); test suite now at ~162 tests.

- ChatGPT (OpenAI)
    - Used as a reference to understand different chunking strategies and their potential trade-offs.

## Rubric discrepancy note

The grading rubric's base components (TITO 30 + Structure 10 + RAG 15 + Modes 15 + Latency 10 + Docs 5 + Demo 5 + Integrity 5) sum to 95, not the stated total of 100. The source of the remaining 5 marks is not specified in the rubric as provided. This discrepancy is flagged for instructor clarification.

## One-line claim to fame

Single RAG app supporting all four interaction modes (TITO, TIVO, VITO, VIVO) with a hardened, atomic ingestion pipeline, reliable STT with retry and resource cleanup, swappable LLM/STT/TTS providers, Rich-styled CLI, and automated tests.
