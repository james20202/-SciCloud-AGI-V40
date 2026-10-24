import json
import os

from core.episode_audio_engine import EpisodeAudioEngine
from core.local_media_engine import LocalMediaEngine


def test_episode_audio_engine_places_dialogue_on_absolute_shot_timeline(tmp_path, monkeypatch):
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"audio")
    engine = EpisodeAudioEngine()
    mixed_calls = []

    def fake_mix(clips, output, total_duration):
        mixed_calls.append((clips, output, total_duration))
        with open(output, "wb") as stream:
            stream.write(b"mix")
        return {"success": True, "duration_seconds": total_duration}

    monkeypatch.setattr("core.episode_audio_engine.local_media_engine.mix_audio_tracks", fake_mix)
    result = engine.prepare(
        {"shots": [{"shot_id": "S2", "artifacts": [{"kind": "audio", "path": str(audio)}]}]},
        [{"shot_id": "S1", "start_seconds": 0, "duration_seconds": 4,
          "spec": {"dialogue": "第一句对白"}},
         {"shot_id": "S2", "start_seconds": 4, "duration_seconds": 5,
          "spec": {"dialogue": {"speaker": "主角", "text": "第二句对白"}}}],
        str(tmp_path / "audio"), 9,
    )
    assert result["success"] is True
    assert result["subtitle_count"] == 2
    assert result["audio_clip_count"] == 1
    assert mixed_calls[0][0][0]["start"] == 4
    assert mixed_calls[0][2] == 9
    subtitle_text = open(result["subtitle_path"], encoding="utf-8").read()
    assert "00:00:04,000 --> 00:00:09,000" in subtitle_text
    assert "主角：第二句对白" in subtitle_text


def test_mix_audio_tracks_builds_delay_and_duration_filters(tmp_path, monkeypatch):
    source = tmp_path / "voice.wav"
    source.write_bytes(b"voice")
    engine = LocalMediaEngine()
    commands = []

    monkeypatch.setattr(engine, "probe", lambda path: {
        "success": True, "duration_seconds": 2,
        "data": {"streams": [{"codec_type": "audio"}]},
    })

    def fake_run(command, timeout=1800):
        commands.append(command)
        with open(command[-1], "wb") as stream:
            stream.write(b"mixed")
        return {"success": True, "message": "mock"}

    monkeypatch.setattr(engine, "_run", fake_run)
    result = engine.mix_audio_tracks(
        [{"path": str(source), "start": 4.25, "duration": 5}],
        str(tmp_path / "mix.m4a"), 9,
    )
    assert result["success"] is True
    filters = commands[0][commands[0].index("-filter_complex") + 1]
    assert "adelay=4250|4250" in filters
    assert "atrim=duration=9.0" in filters
    assert "amix=inputs=1" in filters


def test_mix_audio_with_video_preserves_existing_audio(tmp_path, monkeypatch):
    video, audio = tmp_path / "video.mp4", tmp_path / "dialogue.m4a"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")
    engine = LocalMediaEngine()
    commands = []

    def fake_probe(path):
        streams = [{"codec_type": "video"}]
        if str(path) == str(video):
            streams.append({"codec_type": "audio"})
        else:
            streams = [{"codec_type": "audio"}]
        return {"success": True, "duration_seconds": 9, "data": {"streams": streams}}

    def fake_run(command, timeout=1800):
        commands.append(command)
        with open(command[-1], "wb") as stream:
            stream.write(b"output")
        return {"success": True, "message": "mock"}

    monkeypatch.setattr(engine, "probe", fake_probe)
    monkeypatch.setattr(engine, "_run", fake_run)
    result = engine.mix_audio_with_video(str(video), str(audio), str(tmp_path / "final.mp4"), 9)
    assert result["success"] is True
    command = commands[0]
    assert "-filter_complex" in command
    assert "amix=inputs=2" in command[command.index("-filter_complex") + 1]
    assert "[0:a:0]volume=0.75[base]" in command[command.index("-filter_complex") + 1]
