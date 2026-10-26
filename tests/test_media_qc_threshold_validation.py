import json
import os
import tempfile
from types import SimpleNamespace

import pytest

from core.media_quality_engine import MediaQualityEngine


@pytest.mark.parametrize(
    ("parameter", "value", "error"),
    [
        ("black_warning_seconds", 0, "invalid_black_warning_threshold"),
        ("black_warning_seconds", float("nan"), "invalid_black_warning_threshold"),
        ("black_warning_seconds", float("inf"), "invalid_black_warning_threshold"),
        ("black_warning_seconds", "not-a-number", "invalid_black_warning_threshold"),
        ("silence_warning_seconds", -1, "invalid_silence_warning_threshold"),
        ("silence_warning_seconds", float("nan"), "invalid_silence_warning_threshold"),
        ("silence_warning_seconds", float("inf"), "invalid_silence_warning_threshold"),
        ("silence_warning_seconds", None, "invalid_silence_warning_threshold"),
    ],
)
def test_invalid_scan_thresholds_fail_closed_before_running_ffprobe(tmp_path, parameter, value, error):
    media = tmp_path / "episode.mp4"
    media.write_bytes(b"media")
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"duration": "10"},
            "streams": [{"codec_type": "video"}],
        }), stderr="")

    engine = MediaQualityEngine(runner=runner, which=lambda name: "/usr/bin/" + name)
    report = engine.inspect(str(media), **{parameter: value})

    assert report["passed"] is False
    assert error in report["errors"]
    assert calls == []


def test_valid_scan_thresholds_are_passed_to_ffmpeg(tmp_path):
    media = tmp_path / "episode.mp4"
    media.write_bytes(b"media")
    commands = []

    def runner(command, **kwargs):
        commands.append(command)
        if command[0] == "ffprobe":
            payload = {"format": {"duration": "10"}, "streams": [{"codec_type": "video"}]}
            return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    engine = MediaQualityEngine(runner=runner, which=lambda name: "/usr/bin/" + name)
    report = engine.inspect(str(media), black_warning_seconds=2.25, silence_warning_seconds=4.5)

    assert report["passed"] is True
    ffmpeg = next(command for command in commands if command[0] == "ffmpeg")
    assert "blackdetect=d=2.25:pix_th=0.10:pic_th=0.98" in ffmpeg
    assert "silencedetect=n=-50dB:d=4.5" in ffmpeg
