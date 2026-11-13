# APICN002 - RAG VoiceBot

RAG chatbot for Indian Income Tax corpus with 4 interaction modes:
- TITO: text input -> text output
- TIVO: text input -> voice output
- VITO: voice input -> text output
- VIVO: voice input -> voice output

## Team
| Member | Role | Email |
|--------|------|-------|
| Antika Burman | RAG pipeline development and embedding-based retrieval | 2023sl70005@wilp.bits-pilani.ac.in |
| Rishav Raj Singh | --- | 2023sl70004@wilp.bits-pilani.ac.in |
| Abhishek Gupta | --- | 2023sl70036@wilp.bits-pilani.ac.in |
| Subhadip Jana | RAG pipeline development and embedding-based retrieval | 2023sl70031@wilp.bits-pilani.ac.in |
| Karan Banjade | Speech I/O integration (STT & TTS) | 2023sl70034@wilp.bits-pilani.ac.in |

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
	`pip install -r requirements.txt`
3. Create env file:
	`cp .env.example .env`
4. Configure at least these variables in `.env`:
	- `LLM_PROVIDER` = `slm` (or `groq`, `openai`, `anthropic`, `openrouter`)
	- `LLM_MODEL` (optional, defaults are already coded)
5. Build the retrieval index:
	`python src/rag/ingest.py`

## Run

### 1) TITO (text in, text out)
`python src/app.py --mode tito`

### 2) TIVO (text in, voice out)
`python src/app.py --mode tivo`

### 3) VITO (voice in, text out)
`python src/app.py --mode vito`

### 4) VIVO (voice in, voice out)
`python src/app.py --mode vivo`

### One-shot query
`python src/app.py --mode tito --question "What is section 80C deduction limit?"`

## Speech Features

### Speech input (STT)
- Recording flow: press Enter to start recording, then Enter again to stop.
- Provider selection via `STT_PROVIDER`:
  - `local` (default): uses `faster-whisper`
  - `groq`: uses Groq Whisper API
  - `openai`: uses OpenAI Whisper API
- Optional model override: `STT_MODEL=base` (or other faster-whisper models)

### Speech output (TTS)
- Provider selection via `TTS_PROVIDER`:
  - `pyttsx3` (default, local/offline)
  - `piper` (requires `piper` binary and `TTS_VOICE` model path)
  - `edge` (requires `edge-tts`, default voice `en-IN-NeerjaNeural`)
- Optional controls:
  - `TTS_RATE` for speaking speed
  - `TTS_VOICE` for provider-specific voice/model

## Quick env examples

### Local LLM + local STT + pyttsx3 TTS
`LLM_PROVIDER=slm`
`STT_PROVIDER=local`
`TTS_PROVIDER=pyttsx3`

### Groq STT + pyttsx3 TTS
`LLM_PROVIDER=slm`
`STT_PROVIDER=groq`
`GROQ_API_KEY=...`
`TTS_PROVIDER=pyttsx3`

## Test
`python -m pytest tests/ -q`

## Notes
- Voice modes depend on microphone access and OS audio playback.
- In voice-input modes, saying or dictating `quit`, `exit`, or `stop` will end the app loop.