import os
import queue
import tempfile
import threading
import time

from dotenv import load_dotenv

load_dotenv()

_ever_initialized = False
_model = None

# Recordings shorter than this are discarded before transcription.
_MIN_DURATION_S = 0.3


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

    def callback(indata, n_frames, t, status):
        if status:
            print(f"  REC> audio callback warning: {status}", flush=True)
        audio_q.put(indata.copy())

    def wait_stop() -> None:
        input("  REC> press Enter to stop...")
        nonlocal running
        running = False

    try:
        stream = sd.InputStream(samplerate=sr, channels=1, dtype="int16", callback=callback)
    except Exception as exc:
        print(f"  REC> audio device error: {exc}")
        return None

    running = True
    print("  REC> press Enter to start speaking...")
    try:
        with stream:
            input()

            # Discard audio captured before the user pressed Enter to start.
            while not audio_q.empty():
                try:
                    audio_q.get_nowait()
                except queue.Empty:
                    break

            frames = []
            if seconds:
                # Fixed-duration: collect frames until the deadline elapses.
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    try:
                        frames.append(audio_q.get(timeout=0.1))
                    except queue.Empty:
                        continue
            else:
                # Interactive: collect until Enter is pressed.
                stopper = threading.Thread(target=wait_stop, daemon=True)
                stopper.start()
                while running:
                    try:
                        frames.append(audio_q.get(timeout=0.1))
                    except queue.Empty:
                        continue
    except Exception as exc:
        print(f"  REC> audio stream error: {exc}")
        return None

    audio = np_stack(frames)
    if audio.shape[0] < int(sr * _MIN_DURATION_S):
        print("  REC> recording too short, discarded")
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    path = tmp.name
    tmp.close()
    try:
        sf.write(path, audio, sr)
        return path
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        return None


def np_stack(frames):
    import numpy as np

    return np.concatenate(frames, axis=0) if frames else np.zeros((0, 1), dtype="int16")


def transcribe(wav_path: str | None, *, delete_after: bool = True) -> str | None:
    """Transcribe audio at *wav_path* and return the text.

    *delete_after* controls whether the input file is removed when done.
    Pass ``delete_after=False`` to preserve a permanent recording.
    The default (``True``) preserves the existing behaviour for the
    temporary WAV files produced by :func:`record_to_wav`.
    """
    provider = os.getenv("STT_PROVIDER", "local")
    if wav_path is None:
        return None
    try:
        if provider in ("groq", "openai"):
            import requests

            key_var = "GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY"
            api_key = os.getenv(key_var, "")
            if not api_key:
                raise RuntimeError(
                    f"STT_PROVIDER={provider} requires {key_var} to be set"
                )

            url = (
                "https://api.groq.com/openai/v1/audio/transcriptions"
                if provider == "groq"
                else "https://api.openai.com/v1/audio/transcriptions"
            )
            label = (
                os.getenv("STT_GROQ_MODEL", "whisper-large-v3-turbo")
                if provider == "groq"
                else "whisper-1"
            )

            for attempt in range(2):
                try:
                    with open(wav_path, "rb") as audio_file:
                        resp = requests.post(
                            url,
                            headers={"Authorization": f"Bearer {api_key}"},
                            files={"file": audio_file},
                            data={"model": label},
                            timeout=120,
                        )
                    if resp.status_code == 429 or resp.status_code >= 500:
                        if attempt == 0:
                            time.sleep(2)
                            continue
                        resp.raise_for_status()
                    resp.raise_for_status()
                    text = resp.json().get("text")
                    if text is None:
                        raise ValueError(
                            f"STT API ({provider}) returned unexpected response: {resp.json()}"
                        )
                    return text
                except (requests.ConnectionError, requests.Timeout):
                    if attempt == 0:
                        time.sleep(2)
                        continue
                    raise

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
    finally:
        if delete_after:
            try:
                os.unlink(wav_path)
            except OSError:
                pass
