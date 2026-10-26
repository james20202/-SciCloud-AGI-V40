import json

import pytest

from core.episode_render_engine import build_episode_edit_command


def _workflow(tmp_path):
    title = tmp_path / "title.mp4"
    clip = tmp_path / "clip.mp4"
    voice = tmp_path / "voice.wav"
    sound = tmp_path / "music.mp3"
    prompt = tmp_path / "prompt.json"
    for path in (title, clip, voice, sound):
        path.write_bytes(b"test-media")
    prompt.write_text(json.dumps({
        "subtitle_srt_draft": "1\n00:00:00,000 --> 00:00:02,000\n御剑！\n"
    }), encoding="utf-8")
    return {
        "workflow_id": "WF-EDIT-TEST",
        "tasks": [
            {"id": "CARD", "type": "title_card", "status": "done", "outputs": [str(title)]},
            {"id": "VIDEO", "type": "video", "status": "done", "outputs": [str(clip)]},
            {"id": "VOICE", "type": "voice", "status": "done", "outputs": [str(voice)]},
            {"id": "SOUND", "type": "sound", "status": "done", "outputs": [str(sound)]},
            {"id": "PROMPT", "type": "prompt", "status": "done", "outputs": [str(prompt)]},
            {"id": "EDIT", "type": "edit", "status": "ready", "expected_duration_seconds": 60},
        ],
    }


def test_episode_edit_builder_maps_video_audio_and_subtitles(tmp_path):
    workflow = _workflow(tmp_path)
    output = tmp_path / "final.mp4"

    result = build_episode_edit_command(workflow, str(output), ffmpeg="/usr/bin/ffmpeg")

    command = result["command"]
    assert result["video_inputs"][0].endswith("title.mp4")
    assert result["video_inputs"][1].endswith("clip.mp4")
    assert len(result["audio_inputs"]) == 2
    assert result["subtitle_path"].endswith("subtitle_draft.srt")
    assert "concat=n=2:v=1:a=0[vcat]" in command[command.index("-filter_complex") + 1]
    assert "tpad=stop_mode=clone:stop_duration=60" in command[command.index("-filter_complex") + 1]
    assert "trim=duration=60" in command[command.index("-filter_complex") + 1]
    assert "[aout]" in command[command.index("-filter_complex") + 1]
    assert "-c:s" in command
    assert command[-1] == str(output.resolve())
    assert result["target_duration_seconds"] == 60


def test_episode_edit_builder_rejects_missing_video(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"] = [task for task in workflow["tasks"] if task["type"] != "video" and task["type"] != "title_card"]
    with pytest.raises(ValueError, match="没有可用的视频片段"):
        build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))


def test_episode_edit_builder_rejects_missing_audio(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"] = [task for task in workflow["tasks"] if task["type"] not in {"voice", "sound"}]
    with pytest.raises(ValueError, match="没有可用的配音/音效"):
        build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))


def test_episode_edit_builder_requires_valid_target_duration(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][-1]["expected_duration_seconds"] = float("nan")
    with pytest.raises(ValueError, match="目标时长"):
        build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))


def test_episode_edit_builder_pads_short_video_to_target_duration(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][-1]["expected_duration_seconds"] = 90
    result = build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))
    filter_graph = result["command"][result["command"].index("-filter_complex") + 1]
    assert "tpad=stop_mode=clone:stop_duration=90" in filter_graph
    assert "trim=duration=90" in filter_graph
    assert result["target_duration_seconds"] == 90


def test_episode_edit_ignores_stale_video_from_failed_task(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][1]["status"] = "failed"
    result = build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))
    assert result["video_inputs"] == [str((tmp_path / "title.mp4").resolve())]
    assert str((tmp_path / "clip.mp4").resolve()) not in result["video_inputs"]


def test_episode_edit_ignores_stale_audio_from_incomplete_tasks(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][2]["status"] = "failed"
    workflow["tasks"][3]["status"] = "pending"
    with pytest.raises(ValueError, match="没有可用的配音/音效"):
        build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))


def test_episode_edit_does_not_use_subtitles_from_pending_prompt_task(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][4]["status"] = "pending"
    result = build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))
    assert result["subtitle_path"] is None
    assert "-c:s" not in result["command"]
