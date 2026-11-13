# APICN002 — Indian Income Tax RAG VoiceBot

A Retrieval-Augmented Generation (RAG) chatbot that answers Indian Income Tax questions from a corpus of official government PDFs. Supports four interaction modes:

| Mode | Input | Output |
|------|-------|--------|
| **TITO** | Typed text | Printed text |
| **TIVO** | Typed text | Spoken voice |
| **VITO** | Spoken voice | Printed text |
| **VIVO** | Spoken voice | Spoken voice |

---

## Team

| Member | Role | Email |
|--------|------|-------|
| Antika Burman | RAG pipeline development, refinement and embedding-based retrieval | 2023sl70005@wilp.bits-pilani.ac.in |
| Rishav Raj Singh | LLM provider integration and multi-backend support | 2023sl70004@wilp.bits-pilani.ac.in |
| Abhishek Gupta | CLI interface design and implementation | 2023sl70036@wilp.bits-pilani.ac.in |
| Subhadip Jana | RAG pipeline development, refinement and embedding-based retrieval | 2023sl70031@wilp.bits-pilani.ac.in |
| Karan Banjade | Speech I/O integration (STT & TTS) | 2023sl70034@wilp.bits-pilani.ac.in |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.10+** | The codebase uses union type syntax (`str \| None`) introduced in 3.10. Python 3.11 is recommended. |
| **Git** | To clone the repository. |
| **Ollama** | Always required for embeddings (`nomic-embed-text:latest`), regardless of which LLM provider is selected. Also used as the default local LLM. Install from [ollama.com](https://ollama.com). |
| **Embedding model** | Pull before building the index: `ollama pull nomic-embed-text:latest` |
| **Microphone** | Required for VITO and VIVO modes only. |
| **Audio output** | Required for TIVO and VIVO modes only (system speakers). |

---

## 1. Clone the Repository

```bash
git clone https://github.com/BITSSAP2025AugAPIBP3Sections/APICN002.git
cd APICN002
```

All subsequent commands must be run from this repository root.

---

## 2. Set Up the Python Environment

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Windows:**
```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Copy the template and edit it:

```bash
cp .env.example .env
```

### Key variables

| Variable | Default (code) | Description |
|----------|---------------|-------------|
| `LLM_PROVIDER` | `slm` | LLM backend: `slm` (Ollama), `groq`, `openai`, `anthropic`, `openrouter` |
| `LLM_MODEL` | provider-specific† | Model name for the selected provider. **Note:** `.env.example` sets this to `llama3.2:latest`; clear or override it when switching to a non-Ollama provider. |
| `SLM_BASE_URL` | `http://localhost:11434/api` | Ollama API base URL for the local LLM. Code default uses the native Ollama path (`/api`). **`.env.example` sets this to `/v1`** (OpenAI-compatible path) — both work but route differently inside the app. |
| `SLM_API_KEY` | `ollama` | Ollama does not require a real key; leave as-is |
| `GROQ_API_KEY` | — | Required when `LLM_PROVIDER=groq` |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `OPENROUTER_API_KEY` | — | Required when `LLM_PROVIDER=openrouter` |
| `EMBED_MODEL` | `nomic-embed-text:latest` | Ollama embedding model |
| `EMBED_BASE_URL` | `http://localhost:11434/api` | Ollama API base URL for embeddings |
| `EMBED_BATCH` | `32` | Chunks per embedding API call |
| `STT_PROVIDER` | `local` | STT backend: `local` (faster-whisper), `groq`, `openai` |
| `STT_MODEL` | `base` | faster-whisper model size (used when `STT_PROVIDER=local`) |
| `STT_GROQ_MODEL` | `whisper-large-v3-turbo` | Groq Whisper model (used when `STT_PROVIDER=groq`) |
| `TTS_PROVIDER` | `pyttsx3` | TTS backend: `pyttsx3`, `piper`, `edge` |
| `TTS_VOICE` | — | Voice/model for TTS. **Required** for `piper` (model file path). Optional for `pyttsx3` and `edge`. |
| `TTS_RATE` | `185` | Speaking rate (words per minute) for `pyttsx3` |
| `TOP_K` | `7` (code); **`5` via `.env.example`** | Number of corpus chunks retrieved per query. `.env.example` sets this to 5, which takes effect when `.env` is copied from it. |
| `CHUNK_SIZE` | `900` | Characters per chunk during ingestion |
| `CHUNK_OVERLAP` | `150` | Overlap between consecutive chunks |

† **LLM_MODEL defaults per provider** (used only when `LLM_MODEL` is not set in `.env`):

> **Important:** `.env.example` sets `LLM_MODEL=llama3.2:latest`. Copying it as-is applies this Ollama model regardless of provider. Remove or override `LLM_MODEL` in your `.env` when using Groq, OpenAI, Anthropic, or OpenRouter.

| Provider | Coded default model |
|----------|---------------------|
| `slm` (Ollama) | `llama3.1:8b` |
| `groq` | `llama-3.3-70b-versatile` ‡ |
| `openai` | `gpt-4o-mini` |
| `anthropic` | `claude-3-5-haiku-20241022` |
| `openrouter` | `meta-llama/llama-3.1-8b-instruct` |

‡ This is the fallback hard-coded in `src/rag/llm.py`. Current availability on Groq's API depends on their model catalogue and may change. The evaluation used `openai/gpt-oss-120b` (shown in the Groq example below).

### Example: local Ollama (default)

```env
LLM_PROVIDER=slm
LLM_MODEL=llama3.1:8b
STT_PROVIDER=local
TTS_PROVIDER=pyttsx3
```

### Example: Groq cloud (used in evaluation)

```env
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=<your-groq-api-key>
STT_PROVIDER=local
TTS_PROVIDER=pyttsx3
```

> **Note:** Set `OTEL_SDK_DISABLED=true` in your shell (or in `.env`) if you are not running an Arize Phoenix instance. Without it the app still works, but prints a tracing banner on startup and logs connection-retry errors in the background.

---

## 4. Prepare the Income Tax Corpus

The `data/` directory contains ten PDF files committed to the repository. One large file (~171 MB) exceeds GitHub's limit and must be downloaded manually:

**File:** `Income-tax-Act-1961_2026_2026-06-18_02-47-37_b9326c_en.pdf`

**Steps:**
1. Open the [Releases page](https://github.com/BITSSAP2025AugAPIBP3Sections/VoiceBotAssignment/releases) of the faculty assignment repository (`VoiceBotAssignment`) — this is separate from the project repository and is where the large PDF asset is hosted.
2. Download the asset with the exact filename above.
3. Place it in the `data/` folder — **the filename must match exactly**.

> The ingestion script (`src/rag/ingest.py`) enforces a mandatory corpus check and will abort if any of the 11 required PDFs is missing. Without the Income Tax Act file, questions about Sections 80C, 112A, 115BBH, 194S, 206C, and residential status will not be answered correctly.

---

## 5. Build the RAG Index

Start Ollama and ensure the embedding model is available:

```bash
ollama serve          # if not already running as a background service
ollama pull nomic-embed-text:latest
```

Then build the index:

```bash
python src/rag/ingest.py
```

This reads every `*.pdf` from `data/`, chunks and embeds them, and writes the index to `index/chunks.json` and `index/embeddings.npy`. Re-run this command whenever the corpus changes.

---

## 6. Run the Chatbot

### TITO — typed question, printed answer (default)

```bash
python src/app.py --mode tito
```

Type your question at the `You>` prompt. Press **Enter** on an empty line, or type `quit` / `exit`, to stop.

### TIVO — typed question, spoken answer

```bash
OTEL_SDK_DISABLED=true python src/app.py --mode tivo
```

Requires system audio output and `pyttsx3` (installed via `requirements.txt`).

### VITO — spoken question, printed answer

```bash
OTEL_SDK_DISABLED=true python src/app.py --mode vito
```

Requires a working microphone. Install audio extras if not already present:

```bash
pip install sounddevice soundfile
```

When prompted, press **Enter** to start recording, speak your question, then press **Enter** again to stop. Say `quit`, `exit`, or `stop` to end the session.

### VIVO — spoken question, spoken answer

```bash
OTEL_SDK_DISABLED=true python src/app.py --mode vivo
```

Requires both a microphone and audio output. Same recording flow as VITO.

### One-shot query

The `--question` flag bypasses the interactive loop and exits after one answer. It works with all four modes — recording is skipped for VITO and VIVO, and TTS fires for TIVO and VIVO:

```bash
python src/app.py --mode tito --question "What is the Section 80C deduction limit?"
python src/app.py --mode tivo --question "What are the new regime slab rates for FY 2024-25?"
python src/app.py --mode vivo --question "What is the VDA tax rate under Section 115BBH?"
```

### Latency breakdown

Set `SHOW_TIMING=1` in your shell to display per-request latency (embed, search, LLM, total):

```bash
SHOW_TIMING=1 python src/app.py --mode tito
```

---

## 7. Speech Configuration

### STT (Speech-to-Text)

| Provider | `STT_PROVIDER` | Requirements |
|----------|---------------|-------------|
| faster-whisper (offline) | `local` | `STT_MODEL=base` (or `small`, `medium`, `large-v3`) — runs locally, no API key |
| Groq Whisper | `groq` | `GROQ_API_KEY`, `STT_GROQ_MODEL=whisper-large-v3-turbo` |
| OpenAI Whisper | `openai` | `OPENAI_API_KEY` |

### TTS (Text-to-Speech)

| Provider | `TTS_PROVIDER` | Requirements |
|----------|---------------|-------------|
| pyttsx3 (offline) | `pyttsx3` | No extras; `TTS_VOICE` and `TTS_RATE` optional |
| Piper | `piper` | `piper` binary on PATH; `TTS_VOICE` must be set to a `.onnx` model path |
| Edge TTS | `edge` | `pip install edge-tts`; default voice `en-IN-NeerjaNeural`, override with `TTS_VOICE` |

---

## 8. Running Tests

```bash
python -m pytest tests/ -q
```

---

## 9. Troubleshooting

**Ollama not running**
```
ConnectionRefusedError … http://localhost:11434
```
Start Ollama: `ollama serve` (or launch the Ollama desktop app).

**Embedding model missing**
```
model "nomic-embed-text:latest" not found
```
Pull it: `ollama pull nomic-embed-text:latest`

**Missing corpus files**
```
Mandatory corpus PDF(s) not found in data/
```
The ingestion script requires all 11 PDFs. Download the large Income Tax Act file from the repository's Releases page and place it in `data/` with the exact filename.

**Missing or stale index**
```
FileNotFoundError: index/chunks.json
```
Run `python src/rag/ingest.py` to build the index. Re-run after any corpus change.

**Missing API key**
```
RuntimeError: LLM_PROVIDER=groq requires GROQ_API_KEY to be set
```
Set the appropriate key in `.env` for the chosen provider.

**Microphone permission denied (macOS)**
Go to **System Settings → Privacy & Security → Microphone** and grant access to Terminal (or your IDE).

**Audio playback silent (TIVO / VIVO)**
Confirm `pyttsx3` is installed and system volume is on. On Linux, `aplay` must be available (`sudo apt install alsa-utils`). For alternatives, switch to `TTS_PROVIDER=edge`.

**OpenTelemetry / Phoenix banner on startup**
Set `OTEL_SDK_DISABLED=true` in your shell or `.env`. The app runs normally without a Phoenix instance — this variable only suppresses the startup banner and background retry errors.
