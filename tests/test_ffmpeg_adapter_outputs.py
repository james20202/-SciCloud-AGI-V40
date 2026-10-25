from types import SimpleNamespace

import core.adapters.ffmpeg_adapter as ffmpeg_module
from core.adapters.ffmpeg_adapter import FFmpegAdapter


def test_ffmpeg_adapter_returns_only_verified_nonempty_output(tmp_path, monkeypatch):
    output = tmp_path / "episode.mp4"
    output.write_bytes(b"rendered-video")
    monkeypatch.setattr(ffmpeg_module.shutil, "which", lambda command: "/usr/bin/ffmpeg")
    monkeypatch.setattr(
        ffmpeg_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    result = FFmpegAdapter().execute(
        {"command": "ffmpeg"},
        {"command": ["ffmpeg", "-i", "input.mp4", str(output)]},
        {},
    )

    assert result.success is True
    assert result.outputs == [str(output.resolve())]
    assert result.data["output_verified"] is True


def test_ffmpeg_adapter_does_not_claim_output_when_file_missing(tmp_path, monkeypatch):
    output = tmp_path / "missing.mp4"
    monkeypatch.setattr(ffmpeg_module.shutil, "which", lambda command: "/usr/bin/ffmpeg")
    monkeypatch.setattr(
        ffmpeg_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    result = FFmpegAdapter().execute(
        {"command": "ffmpeg"},
        {"command": ["ffmpeg", "-i", "input.mp4", str(output)]},
        {},
    )

    assert result.success is True
    assert result.outputs == []
    assert result.data["output_verified"] is False
