"""Tests for speech I/O temp-file cleanup in stt.py and tts.py."""

import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import src.speech.stt as stt_mod
import src.speech.tts as tts_mod


def _make_temp_file(suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


class TestSTTTempFileCleanup(unittest.TestCase):

    def setUp(self):
        # Reset module-level cache so each test starts fresh
        stt_mod._model = None
        stt_mod._ever_initialized = False

    def test_transcribe_none_returns_none_no_cleanup_needed(self):
        result = stt_mod.transcribe(None)
        self.assertIsNone(result)

    def test_transcribe_deletes_wav_local_provider(self):
        wav_path = _make_temp_file(".wav")
        mock_segment = MagicMock()
        mock_segment.text = "income tax slab"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())
        mock_whisper_mod = MagicMock()
        mock_whisper_mod.WhisperModel.return_value = mock_model

        with (
            patch.dict(sys.modules, {"faster_whisper": mock_whisper_mod}),
            patch.dict(os.environ, {"STT_PROVIDER": "local"}),
        ):
            result = stt_mod.transcribe(wav_path)

        self.assertFalse(os.path.exists(wav_path), "WAV must be deleted after local transcription")
        self.assertIn("income tax slab", result)

    def test_transcribe_deletes_wav_groq_provider(self):
        wav_path = _make_temp_file(".wav")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "section 80c deduction"}
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.return_value = mock_resp

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "groq", "GROQ_API_KEY": "test-key"}),
        ):
            result = stt_mod.transcribe(wav_path)

        self.assertFalse(os.path.exists(wav_path), "WAV must be deleted after groq transcription")
        self.assertEqual(result, "section 80c deduction")

    def test_transcribe_deletes_wav_openai_provider(self):
        wav_path = _make_temp_file(".wav")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "capital gains tax"}
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.return_value = mock_resp

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}),
        ):
            stt_mod.transcribe(wav_path)

        self.assertFalse(os.path.exists(wav_path), "WAV must be deleted after openai transcription")

    def test_transcribe_deletes_wav_even_when_transcription_raises(self):
        wav_path = _make_temp_file(".wav")
        mock_whisper_mod = MagicMock()
        mock_whisper_mod.WhisperModel.side_effect = RuntimeError("GPU OOM")

        with (
            patch.dict(sys.modules, {"faster_whisper": mock_whisper_mod}),
            patch.dict(os.environ, {"STT_PROVIDER": "local"}),
        ):
            with self.assertRaises(RuntimeError):
                stt_mod.transcribe(wav_path)

        self.assertFalse(os.path.exists(wav_path), "WAV must be deleted even when transcription raises")

    def test_transcribe_tolerates_already_deleted_wav(self):
        # Edge case: file was already deleted before finally runs (e.g. OS cleanup)
        wav_path = _make_temp_file(".wav")
        os.unlink(wav_path)  # pre-delete

        mock_whisper_mod = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([MagicMock(text="hello")], MagicMock())
        mock_whisper_mod.WhisperModel.return_value = mock_model

        with (
            patch.dict(sys.modules, {"faster_whisper": mock_whisper_mod}),
            patch.dict(os.environ, {"STT_PROVIDER": "local"}),
        ):
            # Should not raise even though the file is already gone
            stt_mod.transcribe(wav_path)


class TestTTSTempFileCleanup(unittest.TestCase):

    def test_piper_deletes_wav_after_successful_playback(self):
        deleted = []

        real_unlink = os.unlink

        def tracking_unlink(path):
            deleted.append(path)
            try:
                real_unlink(path)
            except OSError:
                pass

        with (
            patch("subprocess.run", return_value=MagicMock(returncode=0)),
            patch.object(tts_mod, "_play_audio"),
            patch.dict(os.environ, {"TTS_VOICE": "/models/en.onnx"}),
            patch("os.unlink", side_effect=tracking_unlink),
        ):
            tts_mod._speak_piper("Section 80C limit is 1.5 lakh.")

        self.assertEqual(len(deleted), 1, "os.unlink must be called exactly once for piper WAV")
        self.assertTrue(deleted[0].endswith(".wav"), "deleted path must be a WAV file")

    def test_piper_deletes_wav_even_when_piper_fails(self):
        deleted = []

        def tracking_unlink(path):
            deleted.append(path)

        with (
            patch("subprocess.run", return_value=MagicMock(returncode=1)),
            patch.object(tts_mod, "_play_audio") as mock_play,
            patch.dict(os.environ, {"TTS_VOICE": "/models/en.onnx"}),
            patch("os.unlink", side_effect=tracking_unlink),
        ):
            tts_mod._speak_piper("hello")

        mock_play.assert_not_called()
        self.assertEqual(len(deleted), 1, "os.unlink must still be called when piper exits non-zero")

    def test_piper_raises_when_no_voice_set(self):
        with patch.dict(os.environ, {"TTS_VOICE": ""}):
            with self.assertRaises(RuntimeError):
                tts_mod._speak_piper("hello")

    def test_edge_deletes_mp3_after_playback(self):
        deleted = []

        def tracking_unlink(path):
            deleted.append(path)

        mock_communicate_instance = MagicMock()
        mock_communicate_instance.save = AsyncMock()
        mock_edge_tts = MagicMock()
        mock_edge_tts.Communicate.return_value = mock_communicate_instance

        with (
            patch.dict(sys.modules, {"edge_tts": mock_edge_tts}),
            patch.object(tts_mod, "_play_audio"),
            patch("os.unlink", side_effect=tracking_unlink),
        ):
            tts_mod._speak_edge("LTCG on listed equity is taxed at 12.5%.")

        self.assertEqual(len(deleted), 1, "os.unlink must be called once for edge-tts MP3")
        self.assertTrue(deleted[0].endswith(".mp3"), "deleted path must be an MP3 file")

    def test_edge_deletes_mp3_even_when_save_raises(self):
        deleted = []

        def tracking_unlink(path):
            deleted.append(path)

        mock_communicate_instance = MagicMock()
        mock_communicate_instance.save = AsyncMock(side_effect=RuntimeError("network error"))
        mock_edge_tts = MagicMock()
        mock_edge_tts.Communicate.return_value = mock_communicate_instance

        with (
            patch.dict(sys.modules, {"edge_tts": mock_edge_tts}),
            patch.object(tts_mod, "_play_audio"),
            patch("os.unlink", side_effect=tracking_unlink),
        ):
            with self.assertRaises(RuntimeError):
                tts_mod._speak_edge("hello")

        self.assertEqual(len(deleted), 1, "os.unlink must be called even when save() raises")


class TestSTTTranscription(unittest.TestCase):
    """Tests for transcription behaviour beyond cleanup (content, retry, error paths)."""

    def setUp(self):
        stt_mod._model = None
        stt_mod._ever_initialized = False

    # --- local provider ---

    def test_transcribe_local_returns_correct_text(self):
        wav_path = _make_temp_file(".wav")
        mock_segment = MagicMock()
        mock_segment.text = "deduction under section 80c"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())
        mock_whisper_mod = MagicMock()
        mock_whisper_mod.WhisperModel.return_value = mock_model

        with (
            patch.dict(sys.modules, {"faster_whisper": mock_whisper_mod}),
            patch.dict(os.environ, {"STT_PROVIDER": "local"}),
        ):
            result = stt_mod.transcribe(wav_path)

        self.assertEqual(result, "deduction under section 80c")

    def test_transcribe_local_model_reused_on_second_call(self):
        wav1 = _make_temp_file(".wav")
        wav2 = _make_temp_file(".wav")
        mock_segment = MagicMock(text="hello")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())
        mock_whisper_mod = MagicMock()
        mock_whisper_mod.WhisperModel.return_value = mock_model

        with (
            patch.dict(sys.modules, {"faster_whisper": mock_whisper_mod}),
            patch.dict(os.environ, {"STT_PROVIDER": "local"}),
        ):
            stt_mod.transcribe(wav1)
            stt_mod.transcribe(wav2)

        mock_whisper_mod.WhisperModel.assert_called_once()

    def test_transcribe_local_empty_segments_returns_empty_string(self):
        wav_path = _make_temp_file(".wav")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], MagicMock())
        mock_whisper_mod = MagicMock()
        mock_whisper_mod.WhisperModel.return_value = mock_model

        with (
            patch.dict(sys.modules, {"faster_whisper": mock_whisper_mod}),
            patch.dict(os.environ, {"STT_PROVIDER": "local"}),
        ):
            result = stt_mod.transcribe(wav_path)

        self.assertEqual(result, "")

    # --- API key validation ---

    def test_transcribe_missing_groq_key_raises_runtime_error(self):
        wav_path = _make_temp_file(".wav")
        with patch.dict(os.environ, {"STT_PROVIDER": "groq", "GROQ_API_KEY": ""}):
            with self.assertRaises(RuntimeError, msg="missing GROQ_API_KEY must raise"):
                stt_mod.transcribe(wav_path)
        self.assertFalse(os.path.exists(wav_path))

    def test_transcribe_missing_openai_key_raises_runtime_error(self):
        wav_path = _make_temp_file(".wav")
        with patch.dict(os.environ, {"STT_PROVIDER": "openai", "OPENAI_API_KEY": ""}):
            with self.assertRaises(RuntimeError, msg="missing OPENAI_API_KEY must raise"):
                stt_mod.transcribe(wav_path)
        self.assertFalse(os.path.exists(wav_path))

    # --- API response validation ---

    def test_transcribe_malformed_api_response_raises_value_error(self):
        wav_path = _make_temp_file(".wav")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": "ok"}  # missing "text"
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.return_value = mock_resp

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "groq", "GROQ_API_KEY": "k"}),
        ):
            with self.assertRaises(ValueError):
                stt_mod.transcribe(wav_path)

        self.assertFalse(os.path.exists(wav_path))

    # --- retry logic ---

    def test_transcribe_retries_on_429_then_raises(self):
        wav_path = _make_temp_file(".wav")
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.raise_for_status.side_effect = Exception("429")
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.return_value = mock_resp

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "groq", "GROQ_API_KEY": "k"}),
            patch("time.sleep"),
        ):
            with self.assertRaises(Exception):
                stt_mod.transcribe(wav_path)

        self.assertEqual(mock_requests.post.call_count, 2, "should retry once on 429")
        self.assertFalse(os.path.exists(wav_path))

    def test_transcribe_retries_on_5xx_then_raises(self):
        wav_path = _make_temp_file(".wav")
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.raise_for_status.side_effect = Exception("503")
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.return_value = mock_resp

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "openai", "OPENAI_API_KEY": "k"}),
            patch("time.sleep"),
        ):
            with self.assertRaises(Exception):
                stt_mod.transcribe(wav_path)

        self.assertEqual(mock_requests.post.call_count, 2, "should retry once on 5xx")
        self.assertFalse(os.path.exists(wav_path))

    def test_transcribe_does_not_retry_on_permanent_4xx(self):
        wav_path = _make_temp_file(".wav")
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = Exception("401")
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.return_value = mock_resp

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "groq", "GROQ_API_KEY": "k"}),
        ):
            with self.assertRaises(Exception):
                stt_mod.transcribe(wav_path)

        self.assertEqual(mock_requests.post.call_count, 1, "must not retry on 401")
        self.assertFalse(os.path.exists(wav_path))

    def test_transcribe_retries_on_connection_error_then_raises(self):
        wav_path = _make_temp_file(".wav")
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.side_effect = ConnectionError("network unreachable")

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "groq", "GROQ_API_KEY": "k"}),
            patch("time.sleep"),
        ):
            with self.assertRaises(ConnectionError):
                stt_mod.transcribe(wav_path)

        self.assertEqual(mock_requests.post.call_count, 2, "should retry once on ConnectionError")
        self.assertFalse(os.path.exists(wav_path))

    def test_transcribe_succeeds_on_retry_after_transient_error(self):
        wav_path = _make_temp_file(".wav")
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 429
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = {"text": "hra exemption"}
        mock_requests = MagicMock()
        mock_requests.ConnectionError = ConnectionError
        mock_requests.Timeout = TimeoutError
        mock_requests.post.side_effect = [mock_resp_fail, mock_resp_ok]

        with (
            patch.dict(sys.modules, {"requests": mock_requests}),
            patch.dict(os.environ, {"STT_PROVIDER": "groq", "GROQ_API_KEY": "k"}),
            patch("time.sleep"),
        ):
            result = stt_mod.transcribe(wav_path)

        self.assertEqual(result, "hra exemption")
        self.assertEqual(mock_requests.post.call_count, 2)
        self.assertFalse(os.path.exists(wav_path))


class TestSTTRecording(unittest.TestCase):
    """Tests for record_to_wav() reliability and resource cleanup."""

    def _make_mock_stream(self, mock_sd):
        """Return a MagicMock InputStream that behaves as a context manager."""
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_sd.InputStream.return_value = mock_stream
        return mock_stream

    def test_record_to_wav_device_error_returns_none(self):
        """PortAudio / device errors during stream creation must return None, not raise."""
        mock_sd = MagicMock()
        mock_sd.InputStream.side_effect = RuntimeError("no audio device")

        with patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": MagicMock()}):
            result = stt_mod.record_to_wav()

        self.assertIsNone(result)

    def test_record_to_wav_does_not_hang_when_callback_stops(self):
        """Recording loop must exit cleanly when no audio arrives (callback silent).

        With audio_q.get(timeout=0.1), the loop re-checks `running` every 100 ms
        even if no frames arrive, so it exits promptly when Enter is pressed.
        """
        mock_sd = MagicMock()
        mock_sf = MagicMock()
        self._make_mock_stream(mock_sd)

        with (
            patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": mock_sf}),
            patch("builtins.input", return_value=""),
        ):
            result = stt_mod.record_to_wav()

        # No audio → below minimum duration → None (not a hang or exception)
        self.assertIsNone(result)

    def test_record_to_wav_cleans_up_temp_file_on_write_failure(self):
        """sf.write failure must delete the temp WAV rather than leaking it."""
        import numpy as np_real

        mock_sd = MagicMock()
        mock_sf = MagicMock()
        mock_sf.write.side_effect = RuntimeError("disk full")
        self._make_mock_stream(mock_sd)

        sufficient_audio = np_real.zeros((16_000, 1), dtype="int16")  # 1 s

        created_paths: list[str] = []
        real_ntf = tempfile.NamedTemporaryFile

        def capturing_ntf(*args, **kwargs):
            tmp = real_ntf(*args, **kwargs)
            created_paths.append(tmp.name)
            return tmp

        with (
            patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": mock_sf}),
            patch("builtins.input", return_value=""),
            patch.object(stt_mod, "np_stack", return_value=sufficient_audio),
            patch("tempfile.NamedTemporaryFile", side_effect=capturing_ntf),
        ):
            result = stt_mod.record_to_wav()

        self.assertIsNone(result)
        self.assertEqual(len(created_paths), 1)
        self.assertFalse(
            os.path.exists(created_paths[0]),
            "temp WAV must be deleted after sf.write failure",
        )

    def test_record_to_wav_discards_short_recording(self):
        """Recordings below _MIN_DURATION_S must return None without writing a file."""
        mock_sd = MagicMock()
        mock_sf = MagicMock()
        self._make_mock_stream(mock_sd)

        with (
            patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": mock_sf}),
            patch("builtins.input", return_value=""),
        ):
            result = stt_mod.record_to_wav()

        self.assertIsNone(result)
        mock_sf.write.assert_not_called()

    def test_record_to_wav_stream_context_entry_failure(self):
        """Failure in stream.__enter__ must return None, not raise."""
        mock_sd = MagicMock()
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(side_effect=RuntimeError("device busy"))
        mock_sd.InputStream.return_value = mock_stream

        with patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": MagicMock()}):
            result = stt_mod.record_to_wav()

        self.assertIsNone(result)

    # --- fixed-duration mode ---

    def _make_capturing_stream(self, mock_sd):
        """InputStream mock that captures the callback kwarg for later injection."""
        captured = {}

        def fake_input_stream(**kwargs):
            captured["callback"] = kwargs.get("callback")
            mock_stream = MagicMock()
            mock_stream.__enter__ = MagicMock(return_value=mock_stream)
            mock_stream.__exit__ = MagicMock(return_value=False)
            return mock_stream

        mock_sd.InputStream.side_effect = fake_input_stream
        return captured

    def _make_deadline_mock(self, captured, audio_chunk, seconds=1.0):
        """Return a time.monotonic side_effect that injects one frame and exits.

        Call sequence:
          0 → 0.0           deadline = 0.0 + seconds
          1 → 0.1           inject frame, < deadline → enter loop body
          2 → seconds + 1   > deadline → exit loop
        """
        call_count = [0]

        def mock_monotonic():
            c = call_count[0]
            call_count[0] += 1
            if c == 0:
                return 0.0
            if c == 1:
                cb = captured.get("callback")
                if cb:
                    cb(audio_chunk, len(audio_chunk), None, None)
                return 0.1
            return seconds + 1.0

        return mock_monotonic

    def test_record_to_wav_fixed_duration_collects_frames(self):
        """Fixed-duration recording must collect audio frames and write a WAV file."""
        import numpy as np_real

        mock_sd = MagicMock()
        mock_sf = MagicMock()
        captured = self._make_capturing_stream(mock_sd)
        audio_chunk = np_real.ones((8000, 1), dtype="int16")  # 0.5 s at 16 kHz

        with (
            patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": mock_sf}),
            patch("builtins.input", return_value=""),
            patch("time.monotonic", side_effect=self._make_deadline_mock(captured, audio_chunk)),
        ):
            result = stt_mod.record_to_wav(seconds=1.0)

        self.assertIsNotNone(result)
        mock_sf.write.assert_called_once()
        # Verify the audio array passed to sf.write contains the injected frames.
        written_audio = mock_sf.write.call_args[0][1]
        self.assertGreater(written_audio.shape[0], 0)
        if result:
            try:
                os.unlink(result)
            except OSError:
                pass

    def test_record_to_wav_fixed_duration_too_short_returns_none(self):
        """Fixed-duration recording below _MIN_DURATION_S must return None."""
        mock_sd = MagicMock()
        mock_sf = MagicMock()
        self._make_mock_stream(mock_sd)

        # deadline expires immediately — loop body never runs, zero frames collected
        call_count = [0]

        def quick_monotonic():
            c = call_count[0]
            call_count[0] += 1
            return 0.0 if c == 0 else 10.0

        with (
            patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": mock_sf}),
            patch("builtins.input", return_value=""),
            patch("time.monotonic", side_effect=quick_monotonic),
        ):
            result = stt_mod.record_to_wav(seconds=0.1)

        self.assertIsNone(result)
        mock_sf.write.assert_not_called()

    def test_record_to_wav_callback_status_warning_continues_recording(self):
        """A truthy callback status must log a warning but still add the frame."""
        import numpy as np_real

        mock_sd = MagicMock()
        mock_sf = MagicMock()
        captured = self._make_capturing_stream(mock_sd)
        audio_chunk = np_real.ones((8000, 1), dtype="int16")

        def monotonic_with_warning():
            nonlocal call_n
            c = call_n
            call_n += 1
            if c == 0:
                return 0.0
            if c == 1:
                cb = captured.get("callback")
                if cb:
                    # Pass a truthy status string (simulates input overflow).
                    cb(audio_chunk, len(audio_chunk), None, "input overflow")
                return 0.1
            return 2.0

        call_n = 0

        with (
            patch.dict(sys.modules, {"sounddevice": mock_sd, "soundfile": mock_sf}),
            patch("builtins.input", return_value=""),
            patch("time.monotonic", side_effect=monotonic_with_warning),
        ):
            result = stt_mod.record_to_wav(seconds=1.0)

        # Recording must succeed despite the warning status.
        self.assertIsNotNone(result)
        mock_sf.write.assert_called_once()
        if result:
            try:
                os.unlink(result)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
