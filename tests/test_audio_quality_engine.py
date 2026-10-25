import json
from types import SimpleNamespace

from core.media_quality_engine import MediaQualityEngine


def test_audio_inspection_requires_real_audio_stream(tmp_path):
    audio = tmp_path / "dialogue.wav"
    audio.write_bytes(b"fixture")

    def runner(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"duration": "2.5", "size": "7", "format_name": "wav"},
            "streams": [{"codec_type": "audio", "codec_name": "pcm_s16le",
                         "sample_rate": "44100", "channels": 2}],
        }), stderr="")

    result = MediaQualityEngine(runner=runner, which=lambda _: True).inspect_audio(str(audio), 2.5)
    assert result["passed"] is True
    assert result["has_audio_stream"] is True
    assert result["duration_seconds"] == 2.5
    assert result["errors"] == []


def test_audio_inspection_rejects_file_without_audio_stream(tmp_path):
    audio = tmp_path / "fake.wav"
    audio.write_bytes(b"fixture")

    def runner(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"duration": "2.5"},
            "streams": [{"codec_type": "video", "codec_name": "h264"}],
        }), stderr="")

    result = MediaQualityEngine(runner=runner, which=lambda _: True).inspect_audio(str(audio))
    assert result["passed"] is False
    assert "missing_audio_stream" in result["errors"]


def test_audio_inspection_fails_when_ffprobe_is_unavailable(tmp_path):
    audio = tmp_path / "dialogue.wav"
    audio.write_bytes(b"fixture")
    result = MediaQualityEngine(which=lambda _: False).inspect_audio(str(audio))
    assert result["passed"] is False
    assert result["errors"] == ["probe_failed"]
