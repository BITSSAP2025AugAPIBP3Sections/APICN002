"""APICN002 RAG Income Tax VoiceBot: TITO / TIVO / VITO / VIVO modes.

Modes:
  python src/app.py --mode tito          typed question -> typed answer
  python src/app.py --mode tivo          typed question -> spoken answer
  python src/app.py --mode vito          spoken question -> typed answer
  python src/app.py --mode vivo          spoken question -> spoken answer
  python src/app.py --question "..."     one-shot (handy for latency measurement)

Voice modes need: pip install faster-whisper sounddevice soundfile  (+ pyttsx3 for TTS)
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv  # noqa: E402
from rag.llm import chat  # noqa: E402
from rag.retriever import Retriever  # noqa: E402

load_dotenv()

try:
    from ui import console as ui
    _rich = True
except ImportError:
    ui = None  # type: ignore[assignment]
    _rich = False


def answer(ret: Retriever, question: str, history: list[dict], top_k: int) -> tuple[str, list[dict]]:
    t0 = time.perf_counter()
    hits = ret.search(question, top_k=top_k)
    t1 = time.perf_counter()
    context = "\n\n".join(h["text"] + f"\n[source: {h['doc']} p.{h['page']}]" for h in hits)
    t2 = time.perf_counter()
    text = chat(question, context, history)
    t3 = time.perf_counter()

    embed_ms = getattr(ret, "_t_embed_ms", (t1 - t0) * 1000)
    search_ms = getattr(ret, "_t_search_ms", 0.0)
    context_ms = (t2 - t1) * 1000
    llm_ms = (t3 - t2) * 1000
    total_ms = (t3 - t0) * 1000
    if os.getenv("SHOW_TIMING"):
        if _rich:
            ui.print_timing(embed_ms, search_ms, context_ms, llm_ms, total_ms)
        else:
            print(
                f"[timing]  embed {embed_ms:.0f} ms | "
                f"retrieve {search_ms:.0f} ms | "
                f"context {context_ms:.0f} ms | "
                f"LLM {llm_ms:.0f} ms | "
                f"total {total_ms:.0f} ms"
            )
    return text, hits


def cite_sources(hits: list[dict]) -> None:
    if _rich:
        ui.print_sources(hits)
    else:
        seen = []
        for h in hits:
            key = f"{h['doc']} p.{h['page']}"
            if key not in seen:
                seen.append(key)
        print("Sources: " + "; ".join(seen))


def voice_question() -> str | None:
    from speech import stt

    return stt.transcribe(stt.record_to_wav())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["tito", "tivo", "vito", "vivo"], default="tito")
    parser.add_argument("--question", help="one-shot question and exit")
    args = parser.parse_args()

    ret = Retriever(os.getenv("INDEX_DIR", "index"))
    history: list[dict] = []

    if not args.question and _rich:
        ui.print_startup(args.mode)
    if args.question:
        text, hits = answer(ret, args.question, history, int(os.getenv("TOP_K", 5)))
        print(text)
        cite_sources(hits)
        if args.mode in ("tivo", "vivo"):
            from speech import tts

            tts.speak(text)
        return

    while True:
        if args.mode in ("vito", "vivo"):
            question = voice_question()
            if not question:
                continue
            if question.strip().lower() in {"quit", "exit", "stop"}:
                break
        else:
            if _rich:
                ui.print_rule()
                question = ui.ask_user()
            else:
                question = input("\nYou> ").strip()
            if not question:
                break
            if question.lower() in {"quit", "exit"}:
                break
        text, hits = answer(ret, question, history, int(os.getenv("TOP_K", 5)))
        if _rich:
            ui.print_bot(text)
        else:
            print(f"\nBot> {text}")
        cite_sources(hits)
        history += [
            {"role": "user", "content": question},
            {"role": "assistant", "content": text[:1800]},
        ]
        if args.mode in ("tivo", "vivo"):
            from speech import tts

            tts.speak(text)


if __name__ == "__main__":
    main()
