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
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "tpad=stop_mode=clone:stop_duration=60" in filter_graph
    assert "tpad=stop_mode=clone:stop_duration=3" in filter_graph
    assert "setpts=0.95*(PTS-STARTPTS)" in filter_graph
    assert "trim=duration=60" in filter_graph
    assert "adelay=3000|3000" in filter_graph
    assert "atempo=1.0526316" in filter_graph
    assert "[aout]" in filter_graph
    assert "-c:s" in command
    assert command[-1] == str(output.resolve())
    assert result["target_duration_seconds"] == 60
    assert result["title_card_duration_seconds"] == 3.0
    assert result["main_content_duration_budget_seconds"] == 57.0
    assert result["video_content_speed_factor"] == 0.95
    subtitle = open(result["subtitle_path"], encoding="utf-8").read()
    assert "00:00:03,000 --> 00:00:04,900" in subtitle


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


def test_episode_edit_rejects_title_card_when_all_episode_video_tasks_failed(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][1]["status"] = "failed"
    with pytest.raises(ValueError, match="没有可用的正片视频片段"):
        build_episode_edit_command(workflow, str(tmp_path / "final.mp4"))


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



def test_episode_edit_custom_title_card_duration_retimes_full_subtitle_timeline(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][0]["title_card_duration_seconds"] = 4
    result = build_episode_edit_command(workflow, str(tmp_path / "custom-final.mp4"))
    assert result["title_card_duration_seconds"] == 4.0
    assert result["main_content_duration_budget_seconds"] == 56.0
    assert result["video_content_speed_factor"] == pytest.approx(56 / 60)
    filter_graph = result["command"][result["command"].index("-filter_complex") + 1]
    assert "tpad=stop_mode=clone:stop_duration=4" in filter_graph
    subtitle = open(result["subtitle_path"], encoding="utf-8").read()
    assert "00:00:04,000 --> 00:00:05,867" in subtitle


def test_episode_edit_without_title_card_keeps_original_content_and_subtitle_timing(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"] = [task for task in workflow["tasks"] if task["type"] != "title_card"]
    result = build_episode_edit_command(workflow, str(tmp_path / "no-card-final.mp4"))
    assert result["title_card_duration_seconds"] == 0.0
    assert result["video_content_speed_factor"] == 1.0
    filter_graph = result["command"][result["command"].index("-filter_complex") + 1]
    assert "adelay=" not in filter_graph
    assert "atempo=" not in filter_graph
    subtitle = open(result["subtitle_path"], encoding="utf-8").read()
    assert "00:00:00,000 --> 00:00:02,000" in subtitle


def test_episode_edit_rejects_title_card_that_consumes_entire_target_duration(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][0]["title_card_duration_seconds"] = 60
    with pytest.raises(ValueError, match="片头时长必须小于最终剪辑目标时长"):
        build_episode_edit_command(workflow, str(tmp_path / "invalid-final.mp4"))


def test_episode_edit_drops_subtitles_that_fall_after_final_duration(tmp_path):
    workflow = _workflow(tmp_path)
    prompt = tmp_path / "prompt.json"
    prompt.write_text(json.dumps({
        "subtitle_srt_draft": (
            "1\n00:00:58,000 --> 00:01:00,000\n结尾字幕\n\n"
            "2\n00:01:01,000 --> 00:01:02,000\n超出字幕\n"
        )
    }), encoding="utf-8")
    workflow["tasks"][4]["outputs"] = [str(prompt)]
    result = build_episode_edit_command(workflow, str(tmp_path / "clipped-final.mp4"))
    subtitle = open(result["subtitle_path"], encoding="utf-8").read()
    assert "结尾字幕" in subtitle
    assert "超出字幕" not in subtitle
    assert "00:00:58,100 --> 00:01:00,000" in subtitle
