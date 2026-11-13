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
        mock_resp.json.return_value = {"text": "section 80c deduction"}
        mock_requests = MagicMock()
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
        mock_resp.json.return_value = {"text": "capital gains tax"}
        mock_requests = MagicMock()
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


if __name__ == "__main__":
    unittest.main()
