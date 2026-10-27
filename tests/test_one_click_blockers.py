import os
import subprocess
import sys

from core.final_video import find_final_video
from core.media_tools import find_tool
import core.media_tools as media_tools
from core.model_hub import ModelHub
from core.one_click import preflight_workflow


def test_find_tool_searches_homebrew_dirs_when_path_misses(tmp_path, monkeypatch):
    fake = tmp_path / "mytool123"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setattr(media_tools, "_EXTRA_DIRS", (str(tmp_path),))
    assert find_tool("mytool123") == str(fake)
    assert find_tool("no-such-tool-xyz") is None


def test_voice_skill_resolves_to_tts_model(tmp_path):
    hub = ModelHub(model_dir=str(tmp_path))
    assert hub.find_for_skill("voice") is None
    hub.set_enabled("MODEL-LOCAL-TTS", True)
    found = hub.find_for_skill("voice")
    assert found is not None and found["model_id"] == "MODEL-LOCAL-TTS"


def test_find_final_video_prefers_done_edit_output(tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"video")
    workflow = {
        "workflow_id": "WF-TEST",
        "tasks": [
            {"id": "TASK-10", "type": "edit", "status": "done", "outputs": [str(video)]},
            {"id": "TASK-07", "type": "video", "status": "done", "outputs": []},
        ],
    }
    assert find_final_video(workflow, project_dir=str(tmp_path)) == str(video.resolve())
    assert find_final_video({"workflow_id": "WF-EMPTY", "tasks": []}, project_dir=str(tmp_path)) is None


def test_preflight_reports_missing_tts_and_ffmpeg():
    workflow = {
        "workflow_id": "WF-TEST",
        "tasks": [
            {"id": "TASK-08", "type": "voice", "status": "ready"},
        ],
    }
    blockers = preflight_workflow(
        workflow,
        model_finder=lambda skill: None,
        tool_finder=lambda name: None,
    )
    assert any("TTS" in item for item in blockers)
    assert any("FFmpeg" in item for item in blockers)
    assert any("ffprobe" in item for item in blockers)


def test_tts_say_wav_converts_via_aiff(tmp_path, monkeypatch):
    from core.adapters.tts_adapter import TTSCommandAdapter

    output = tmp_path / "voice.wav"
    aiff = tmp_path / "voice.aiff"

    def fake_run(args, capture_output=True, text=True, timeout=900):
        class Proc:
            returncode = 0
            stdout = ""
            stderr = ""
        if args[0] == "say":
            target = args[args.index("-o") + 1]
            assert target == str(aiff)
            aiff.write_bytes(b"aiff")
        elif args[0] == "ffmpeg":
            assert args[args.index("-i") + 1] == str(aiff)
            output.write_bytes(b"wav")
        else:  # pragma: no cover - test only uses say + ffmpeg
            raise AssertionError(args)
        return Proc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("core.adapters.tts_adapter.find_tool", lambda name: "ffmpeg" if name == "ffmpeg" else "say")
    result = TTSCommandAdapter().execute(
        {"command": ""},
        {"command": ["say", "-v", "Ting-Ting", "-o", "{output}", "{text}"], "output_path": str(output), "text": "你好"},
        {},
    )
    assert result.success is True
    assert output.read_bytes() == b"wav"
    assert not aiff.exists()
