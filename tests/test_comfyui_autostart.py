"""Tests for core/comfyui_autostart.py.

Runnable without pytest: `python3 tests/test_comfyui_autostart.py`
runs every test_* function and exits non-zero on any failure.
Under pytest the same test_* functions run as plain tests (no
fixtures), so CI keeps working either way.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import comfyui_autostart as autostart


def _clean_env(monkey_env):
    for key in (
        "SCICLOUD_COMFYUI_AUTOSTART",
        "SCICLOUD_COMFYUI_DIR",
        "SCICLOUD_COMFYUI_START_COMMAND",
        "SCICLOUD_COMFYUI_ENDPOINT",
        "SCICLOUD_COMFYUI_LOG_DIR",
        "SCICLOUD_HOME",
    ):
        monkey_env.pop(key, None)


def test_probe_success_does_not_start():
    autostart.reset_started_flag()
    _clean_env(os.environ)
    calls = []

    def fake_launcher(command, log_path, cwd):
        calls.append(command)

    result = autostart.ensure_comfyui_running(
        probe=lambda endpoint, timeout=2: True,
        launcher=fake_launcher,
    )
    assert result["already_running"] is True
    assert result["started"] is False
    assert calls == []


def test_opt_out_does_not_start_even_when_down():
    autostart.reset_started_flag()
    _clean_env(os.environ)
    os.environ["SCICLOUD_COMFYUI_AUTOSTART"] = "0"
    calls = []

    def fake_launcher(command, log_path, cwd):
        calls.append(command)

    try:
        result = autostart.ensure_comfyui_running(
            probe=lambda endpoint, timeout=2: False,
            launcher=fake_launcher,
        )
    finally:
        del os.environ["SCICLOUD_COMFYUI_AUTOSTART"]
    assert result["enabled"] is False
    assert result["started"] is False
    assert calls == []


def test_disabled_values_are_parsed():
    _clean_env(os.environ)
    for value in ("0", "false", "no", "off", "OFF", " False "):
        os.environ["SCICLOUD_COMFYUI_AUTOSTART"] = value
        assert autostart.autostart_enabled() is False, value
    for value in ("1", "true", "yes", "on", ""):
        os.environ["SCICLOUD_COMFYUI_AUTOSTART"] = value
        assert autostart.autostart_enabled() is True, value
    del os.environ["SCICLOUD_COMFYUI_AUTOSTART"]
    assert autostart.autostart_enabled() is True


def test_start_command_is_preferred_over_direct_python(tmp_path):
    autostart.reset_started_flag()
    _clean_env(os.environ)
    comfyui_dir = os.path.join(tmp_path, "ComfyUI")
    os.makedirs(comfyui_dir, exist_ok=True)
    start_command = os.path.join(comfyui_dir, "start.command")
    with open(start_command, "w", encoding="utf-8") as handle:
        handle.write("#!/bin/bash\n")
    os.environ["SCICLOUD_COMFYUI_DIR"] = comfyui_dir
    os.environ["SCICLOUD_COMFYUI_LOG_DIR"] = os.path.join(tmp_path, "logs")
    calls = []

    def fake_launcher(command, log_path, cwd):
        calls.append(command)
        return None

    try:
        result = autostart.ensure_comfyui_running(
            probe=lambda endpoint, timeout=2: False,
            launcher=fake_launcher,
        )
    finally:
        del os.environ["SCICLOUD_COMFYUI_DIR"]
        del os.environ["SCICLOUD_COMFYUI_LOG_DIR"]
    assert result["started"] is True
    assert result["method"] == "start_command"
    assert calls == [["/bin/bash", start_command]]


def test_missing_start_command_falls_back_to_direct_python(tmp_path):
    autostart.reset_started_flag()
    _clean_env(os.environ)
    comfyui_dir = os.path.join(tmp_path, "ComfyUI")
    venv_bin = os.path.join(comfyui_dir, ".venv", "bin")
    inner = os.path.join(comfyui_dir, "ComfyUI")
    os.makedirs(venv_bin, exist_ok=True)
    os.makedirs(inner, exist_ok=True)
    venv_python = os.path.join(venv_bin, "python")
    main_py = os.path.join(inner, "main.py")
    for path in (venv_python, main_py):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("")
    os.environ["SCICLOUD_COMFYUI_DIR"] = comfyui_dir
    os.environ["SCICLOUD_COMFYUI_LOG_DIR"] = os.path.join(tmp_path, "logs")
    calls = []

    def fake_launcher(command, log_path, cwd):
        calls.append(command)
        return None

    try:
        result = autostart.ensure_comfyui_running(
            probe=lambda endpoint, timeout=2: False,
            launcher=fake_launcher,
        )
    finally:
        del os.environ["SCICLOUD_COMFYUI_DIR"]
        del os.environ["SCICLOUD_COMFYUI_LOG_DIR"]
    assert result["started"] is True
    assert result["method"] == "direct_python"
    assert calls == [[
        venv_python, "-u", main_py,
        "--listen", "127.0.0.1", "--port", "8188",
    ]]


def test_missing_everything_reports_without_starting(tmp_path):
    autostart.reset_started_flag()
    _clean_env(os.environ)
    comfyui_dir = os.path.join(tmp_path, "empty")
    os.makedirs(comfyui_dir, exist_ok=True)
    os.environ["SCICLOUD_COMFYUI_DIR"] = comfyui_dir
    os.environ["SCICLOUD_COMFYUI_LOG_DIR"] = os.path.join(tmp_path, "logs")
    calls = []

    def fake_launcher(command, log_path, cwd):
        calls.append(command)

    try:
        result = autostart.ensure_comfyui_running(
            probe=lambda endpoint, timeout=2: False,
            launcher=fake_launcher,
        )
    finally:
        del os.environ["SCICLOUD_COMFYUI_DIR"]
        del os.environ["SCICLOUD_COMFYUI_LOG_DIR"]
    assert result["started"] is False
    assert result["method"] is None
    assert calls == []
    assert "start.command" in result["message"] or "未找到" in result["message"]


def test_second_call_in_same_process_does_not_relaunch(tmp_path):
    autostart.reset_started_flag()
    _clean_env(os.environ)
    comfyui_dir = os.path.join(tmp_path, "ComfyUI")
    os.makedirs(comfyui_dir, exist_ok=True)
    start_command = os.path.join(comfyui_dir, "start.command")
    with open(start_command, "w", encoding="utf-8") as handle:
        handle.write("#!/bin/bash\n")
    os.environ["SCICLOUD_COMFYUI_DIR"] = comfyui_dir
    os.environ["SCICLOUD_COMFYUI_LOG_DIR"] = os.path.join(tmp_path, "logs")
    calls = []

    def fake_launcher(command, log_path, cwd):
        calls.append(command)
        return None

    try:
        first = autostart.ensure_comfyui_running(
            probe=lambda endpoint, timeout=2: False,
            launcher=fake_launcher,
        )
        # Server came up after the first launch: second call must not
        # launch again, it must report already_running.
        second = autostart.ensure_comfyui_running(
            probe=lambda endpoint, timeout=2: True,
            launcher=fake_launcher,
        )
    finally:
        del os.environ["SCICLOUD_COMFYUI_DIR"]
        del os.environ["SCICLOUD_COMFYUI_LOG_DIR"]
        autostart.reset_started_flag()
    assert first["started"] is True
    assert second["already_running"] is True
    assert second["started"] is False
    assert len(calls) == 1


def test_env_dir_and_start_command_override_defaults(tmp_path):
    _clean_env(os.environ)
    os.environ["SCICLOUD_COMFYUI_DIR"] = str(tmp_path)
    os.environ["SCICLOUD_COMFYUI_START_COMMAND"] = "/tmp/custom-start.command"
    try:
        assert autostart.resolve_comfyui_dir() == str(tmp_path)
        assert autostart.resolve_start_command() == "/tmp/custom-start.command"
    finally:
        del os.environ["SCICLOUD_COMFYUI_DIR"]
        del os.environ["SCICLOUD_COMFYUI_START_COMMAND"]
    assert autostart.resolve_comfyui_dir() == autostart.DEFAULT_COMFYUI_DIR


def test_preflight_blocks_video_without_video_workflow():
    """WF-559D10EB regression: image-only registry + a pending video
    task must block before any task runs, not fail at TASK-07."""
    from core.one_click import preflight_workflow

    workflow = {
        "workflow_id": "WF-TEST",
        "tasks": [
            {"id": "TASK-06", "type": "image", "status": "ready"},
            {"id": "TASK-07", "type": "video", "status": "ready"},
        ],
    }
    blockers = preflight_workflow(
        workflow,
        model_finder=lambda skill: {"endpoint": "http://127.0.0.1:8188"} if skill == "image" else None,
        tool_finder=lambda name: "/opt/homebrew/bin/" + name,
        capabilities={"image.text2image"},
    )
    video_blockers = [item for item in blockers if "video.image2video" in item]
    assert len(video_blockers) == 1
    assert "没有 AI 视频模型/节点" in video_blockers[0]
    assert "FFmpeg 动态镜头" in video_blockers[0]
    # The video blocker must not be disguised as a ComfyUI-down error.
    assert "ComfyUI 未运行" not in video_blockers[0]
    assert "不是 AI 视频" in video_blockers[0]


def test_preflight_no_video_blocker_for_image_only():
    from core.one_click import preflight_workflow

    workflow = {
        "workflow_id": "WF-TEST",
        "tasks": [
            {"id": "TASK-06", "type": "image", "status": "ready"},
        ],
    }
    blockers = preflight_workflow(
        workflow,
        model_finder=lambda skill: {"endpoint": "http://127.0.0.1:8188"} if skill == "image" else None,
        tool_finder=lambda name: "/opt/homebrew/bin/" + name,
        capabilities={"image.text2image"},
    )
    assert not any("video.image2video" in item for item in blockers)


def test_preflight_no_video_blocker_when_video_workflow_registered():
    from core.one_click import preflight_workflow

    workflow = {
        "workflow_id": "WF-TEST",
        "tasks": [
            {"id": "TASK-06", "type": "image", "status": "ready"},
            {"id": "TASK-07", "type": "video", "status": "ready"},
        ],
    }
    blockers = preflight_workflow(
        workflow,
        model_finder=lambda skill: {"endpoint": "http://127.0.0.1:8188"} if skill == "image" else None,
        tool_finder=lambda name: "/opt/homebrew/bin/" + name,
        capabilities={"image.text2image", "video.image2video"},
    )
    assert not any("video.image2video" in item for item in blockers)


def _run_all():
    import traceback

    tests = [
        test_probe_success_does_not_start,
        test_opt_out_does_not_start_even_when_down,
        test_disabled_values_are_parsed,
        test_start_command_is_preferred_over_direct_python,
        test_missing_start_command_falls_back_to_direct_python,
        test_missing_everything_reports_without_starting,
        test_second_call_in_same_process_does_not_relaunch,
        test_env_dir_and_start_command_override_defaults,
        test_preflight_blocks_video_without_video_workflow,
        test_preflight_no_video_blocker_for_image_only,
        test_preflight_no_video_blocker_when_video_workflow_registered,
    ]
    failures = 0
    for test in tests:
        tmp = tempfile.mkdtemp(prefix="comfyui-autostart-test-")
        try:
            if "tmp_path" in test.__code__.co_varnames:
                test(tmp)
            else:
                test()
            print("PASS", test.__name__)
        except Exception:
            failures += 1
            print("FAIL", test.__name__)
            traceback.print_exc()
        finally:
            autostart.reset_started_flag()
            _clean_env(os.environ)
    print("%d passed, %d failed" % (len(tests) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
