import os

from core.local_media_engine import LocalMediaEngine


def test_normalize_video_clip_uses_target_duration_and_preserves_audio_when_present(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    engine = LocalMediaEngine()
    calls = []

    def fake_probe(path):
        if str(path) == str(source):
            return {"success": True, "duration_seconds": 3.2,
                    "data": {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}}
        return {"success": True, "duration_seconds": 5.0,
                "data": {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}}

    def fake_run(command, timeout=1800):
        calls.append(command)
        output = command[-1]
        with open(output, "wb") as stream:
            stream.write(b"normalized")
        return {"success": True, "message": "mock ffmpeg success"}

    monkeypatch.setattr(engine, "probe", fake_probe)
    monkeypatch.setattr(engine, "_run", fake_run)
    output = tmp_path / "normalized.mp4"
    result = engine.normalize_video_clip(str(source), str(output), duration_seconds=5.0)

    assert result["success"] is True
    assert result["duration_seconds"] == 5.0
    assert result["target_duration_seconds"] == 5.0
    assert result["has_audio"] is True
    command = calls[0]
    assert "-af" in command
    assert "apad,atrim=duration=5.0,asetpts=PTS-STARTPTS" in command
    assert any("trim=duration=5.0" in item for item in command)


def test_normalize_video_clip_rejects_missing_source(tmp_path):
    engine = LocalMediaEngine()
    result = engine.normalize_video_clip(str(tmp_path / "missing.mp4"),
                                         str(tmp_path / "out.mp4"), duration_seconds=5)
    assert result["success"] is False
    assert "不存在" in result["message"]
