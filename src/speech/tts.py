import os
import platform
import re
import subprocess
import tempfile
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


def _play_audio(path: str) -> None:
    system = platform.system().lower()
    if system == "darwin":
        subprocess.run(["afplay", path], check=False)
    elif system == "windows":
        subprocess.run(["cmd", "/c", "start", "", path], check=False)
    else:
        subprocess.run(["aplay", path], check=False)


def _speak_piper(text: str) -> None:
    """Synthesize with piper CLI and play with the system audio player."""
    model = os.getenv("TTS_VOICE", "")
    if not model:
        raise RuntimeError("TTS_VOICE must be set to a piper model path when TTS_PROVIDER=piper")
    fd, output = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    proc = subprocess.run(
        ["piper", "--model", model, "--output_file", output],
        input=text.encode("utf-8"),
        check=False,
    )
    if proc.returncode == 0:
        _play_audio(output)


def _speak_edge(text: str) -> None:
    import edge_tts

    async def run():
        path = os.path.join(tempfile.gettempdir(), f"out_{datetime.now().strftime('%H%M%S')}.mp3")
        await edge_tts.Communicate(text, os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")).save(path)
        _play_audio(path)

    import asyncio

    asyncio.run(run())


_SENTENCE = re.compile(r"[^.!?]+[.!?]")


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
