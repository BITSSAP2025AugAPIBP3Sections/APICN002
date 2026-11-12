# Submission — APICN001

- Team ID: APICN001
- Attack vector used for evaluation: this repo
- App entry point: `python src/app.py`
- Default provider: SLM (Ollama via `http://localhost:11434/api`, default model `llama3.1:8b`)
- STT engine: faster-whisper (default local) with Groq/OpenAI Whisper API options
- TTS engine: pyttsx3 (default local) with Piper and Edge TTS options

## Feature completion
- Speech in: Implemented in `vito` and `vivo` modes (`src/speech/stt.py`)
- Speech out: Implemented in `tivo` and `vivo` modes (`src/speech/tts.py`)
- Cross-platform playback handling: Added for macOS, Windows, and Linux

## External data used
- None

## AI coding assistant disclosure
- Claude Code (Anthropic, claude-sonnet-4-6)
    - Used to streamline configuration updates when adapting the LLM integration to use Ollama's native /api/chat endpoint for llama3.2.

- ChatGPT (OpenAI)
    - Used ChatGPT as a reference to understand different chunking strategies and their potential trade-offs.

## One-line claim to fame
- Built a single RAG app that supports all four interaction modes (TITO, TIVO, VITO, VIVO) with swappable LLM/STT/TTS providers.