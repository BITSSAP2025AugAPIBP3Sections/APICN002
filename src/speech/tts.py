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
    try:
        proc = subprocess.run(
            ["piper", "--model", model, "--output_file", output],
            input=text.encode("utf-8"),
            check=False,
        )
        if proc.returncode == 0:
            _play_audio(output)
    finally:
        try:
            os.unlink(output)
        except OSError:
            pass


def _speak_edge(text: str) -> None:
    import edge_tts

    async def run():
        path = os.path.join(tempfile.gettempdir(), f"out_{datetime.now().strftime('%H%M%S')}.mp3")
        try:
            await edge_tts.Communicate(text, os.getenv("TTS_VOICE", "en-IN-NeerjaNeural")).save(path)
            _play_audio(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    import asyncio

    asyncio.run(run())


_SENTENCE = re.compile(r"[^.!?]+[.!?]")
_MD_TABLE_LINE = re.compile(r"^\s*\|")


def _table_block_to_speech(table_lines: list[str]) -> str:
    """Convert a markdown table block into readable spoken sentences."""
    headers: list[str] = []
    rows: list[list[str]] = []
    for line in table_lines:
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells:
            continue
        if all(re.match(r"^[-: ]+$", c) for c in cells):
            continue  # separator row — skip
        if not headers:
            headers = cells
        else:
            rows.append(cells)
    if not rows:
        return ""
    parts = []
    for row in rows:
        if len(row) == 1:
            parts.append(row[0] + ".")
        elif len(row) == 2:
            parts.append(f"{row[0]}: {row[1]}.")
        else:
            parts.append(f"{row[0]}: {', '.join(row[1:])}.")
    return " ".join(parts)


def _strip_markdown(text: str) -> str:
    """Convert markdown to speech-friendly plain text."""
    lines = text.split("\n")
    out: list[str] = []
    table_buf: list[str] = []

    def flush_table() -> None:
        if table_buf:
            out.append(_table_block_to_speech(table_buf))
            table_buf.clear()

    for line in lines:
        if _MD_TABLE_LINE.match(line):
            table_buf.append(line)
        else:
            flush_table()
            out.append(line)
    flush_table()

    text = "\n".join(out)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)         # italic
    text = re.sub(r"#+\s*", "", text)                 # headings
    text = re.sub(r"₹\s*", "rupees ", text)           # rupee sign
    text = re.sub(r"\s*%", " percent", text)          # percent sign
    text = re.sub(r"\s*[–—]\s*", " to ", text)        # en/em dash ranges
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def speak(text: str, sentence_chunked: bool = True) -> None:
    """Speak the answer. Split long text into sentence pairs so TTS starts early."""
    text = _strip_markdown(text)
    provider = os.getenv("TTS_PROVIDER", "pyttsx3")
    fn = {"pyttsx3": _speak_pyttsx3, "piper": _speak_piper, "edge": _speak_edge}[provider]
    if not sentence_chunked or len(text) < 200:
        fn(text)
        return
    parts = _SENTENCE.findall(text)
    if not parts:
        fn(text)
        return
    tail = text[len("".join(parts)) :]
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        fn(text)
        return
    for i in range(0, len(parts), 2):
        fn(" ".join(parts[i : i + 2]) + (" " + tail if i + 2 >= len(parts) else ""))
