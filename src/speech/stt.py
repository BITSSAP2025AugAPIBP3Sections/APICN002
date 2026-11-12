import os
import queue
import tempfile
import threading
import time

from dotenv import load_dotenv

load_dotenv()

_ever_initialized = False
_model = None


def record_to_wav(seconds: float | None = None) -> str | None:
    """Press-Enter-to-start, press-Enter-to-stop recording (or fixed `seconds`)."""
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        print("Voice modes need: pip install sounddevice soundfile faster-whisper")
        return None
    sr = 16_000
    audio_q: queue.Queue = queue.Queue()

    def callback(indata, frames, t, status):
        audio_q.put(indata.copy())

    def wait_stop() -> None:
        input("  REC> press Enter to stop...")
        nonlocal running
        running = False

    running = True
    print("  REC> press Enter to start speaking...")
    with sd.InputStream(samplerate=sr, channels=1, dtype="int16", callback=callback):
        input()
        stopper = threading.Thread(target=wait_stop, daemon=True)
        stopper.start()
        if seconds:
            time.sleep(seconds)
            running = False
        frames = []
        while running:
            frames.append(audio_q.get())
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    path = tmp.name
    tmp.close()
    sf.write(path, np_stack(frames), sr)
    return path


def np_stack(frames):
    import numpy as np

    return np.concatenate(frames, axis=0) if frames else np.zeros((0, 1), dtype="int16")


def transcribe(wav_path: str | None) -> str | None:
    provider = os.getenv("STT_PROVIDER", "local")
    if wav_path is None:
        return None
    if provider in ("groq", "openai"):
        import requests

        url = (
            "https://api.groq.com/openai/v1/audio/transcriptions"
            if provider == "groq"
            else "https://api.openai.com/v1/audio/transcriptions"
        )
        label = "whisper-large-v3-turbo" if provider == "groq" else "whisper-1"
        with open(wav_path, "rb") as audio_file:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY' if provider == 'groq' else 'OPENAI_API_KEY', '')}"},
                files={"file": audio_file},
                data={"model": label},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()["text"]
    from faster_whisper import WhisperModel

    global _ever_initialized, _model
    t0 = time.time()
    if _model is None:
        _model = WhisperModel(os.getenv("STT_MODEL", "base"), device="auto", compute_type="auto")
    first = "" if _ever_initialized else f" (load {time.time()-t0:.1f}s)"
    _ever_initialized = True
    segments, _info = _model.transcribe(wav_path)
    text = " ".join(s.text for s in segments)
    print(f"  [stt{first}] {text}")
    return text
