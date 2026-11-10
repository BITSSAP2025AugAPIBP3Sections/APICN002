# Submission — APICN001

- Team ID: APICN001
- Attack vector used for evaluation: this repo
- App entry point: `python src/app.py`
- Default provider: SLM (Ollama + <model name>)          # or groq/openai/anthropic/openrouter
- STT engine: <name>   TTS engine: <name>

## External data used
- (list any documents beyond the assignment corpus, or "none")

## AI coding assistant disclosure
- Claude Code (Anthropic, claude-sonnet-4-6) was used as a coding assistant during development. Specific uses: 

    - llm.py was hardcoded to use Ollama's OpenAI-compatible /v1/chat/completions endpoint, but the project required the native /api/chat endpoint for llama3.2. Added _ollama_native() to src/rag/llm.py to handle Ollama's native request/response format, and updated the routing logic in chat() to select the correct path based on the configured base URL.

## One-line claim to fame
- (the thing you are proudest of)