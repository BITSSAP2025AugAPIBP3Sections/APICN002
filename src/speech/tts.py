import os
import re
import subprocess
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def _speak_pyttsx3(text: str) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    voice = os.getenv("TTS_VOICE")
    if voice:
        engine.setProperty("voice", voice)
    rate = int(os.getenv("TTS_RATE", 185))
    engine.setProperty("rate", rate)
    engine.say(text)
    engine.runAndWait()


def _speak_piper(text: str) -> None:
    """Stream to the piper CLI: piper --model <TTS_VOICE.wav> --output_file - | aplay."""
    proc = subprocess.Popen(
        ["piper", "--model", os.getenv("TTS_VOICE", "")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    proc.communicate(text.encode())
    subprocess.run(
        # aplay on linux, ffplay as fallback
        ["aplay", "-"],
        input=proc.stdout,
        check=False,
    )


def _speak_edge(text: str) -> None:
    import edge_tts

    async def run():
        path = f"out_{datetime.now().strftime('%H%M%S')}.mp3"
        await edge_tts.Communicate(text, os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")).save(path)
        subprocess.run(["start", path], shell=True, check=False)  # windows default player

    import asyncio

    asyncio.run(run())


_SENTENCE = re.compile(r"[^.!?]+\.[^.!?]*\.")


def speak(text: str, sentence_chunked: bool = True) -> None:
    """Speak the answer. Split long text into sentence pairs so TTS starts early."""
    provider = os.getenv("TTS_PROVIDER", "pyttsx3")
    fn = {"pyttsx3": _speak_pyttsx3, "piper": _speak_piper, "edge": _speak_edge}[provider]
    if not sentence_chunked or len(text) < 200:
        fn(text)
        return
    parts = _SENTENCE.findall(text)
    tail = text[len("".join(parts)) :]
    parts = [p.strip() for p in parts if p.strip()]
    for i in range(0, len(parts), 2):
        fn(" ".join(parts[i : i + 2]) + (" " + tail if i + 2 >= len(parts) else ""))
