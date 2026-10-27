"""ComfyUI auto-start for SciCloud (stdlib only).

Design, agreed with the user after the manual-start period:
- On SciCloud startup, probe ComfyUI at 127.0.0.1:8188 /system_stats
  (2s timeout). If it answers, do nothing.
- Only when it does not answer, start ComfyUI in the background from a
  directory OUTSIDE the packaged .app bundle (the packaged app does not
  bundle ComfyUI), and never block SciCloud startup on it.
- Starting ComfyUI is best-effort: any failure is reported in the return
  value and must never raise out of ensure_comfyui_running() into the
  caller in a way that stops SciCloud. Callers additionally wrap the
  call in try/except.
- The one-click preflight (core/one_click.py) remains the gate that
  tells the user ComfyUI is still not reachable; autostart does not
  replace it, it only removes the manual double-click in the common case.

Configuration (environment variables only, no new settings UI):
- SCICLOUD_COMFYUI_AUTOSTART: enabled by default. Only the values
  0 / false / no / off (case-insensitive) disable it.
- SCICLOUD_COMFYUI_DIR: ComfyUI directory. Default is the user's
  existing install on macOS:
  /Volumes/修仙漫剧/SciCloud AGI V40/ComfyUI
- SCICLOUD_COMFYUI_START_COMMAND: start script. Default is
  <SCICLOUD_COMFYUI_DIR>/start.command, which activates the ComfyUI
  venv and runs ComfyUI/main.py --listen 127.0.0.1 --port 8188.
- SCICLOUD_COMFYUI_LOG_DIR (optional): where the background process
  log goes. Default is <data-dir>/logs, resolved like core/config.py:
  SCICLOUD_HOME/logs when set, ~/SciCloud AGI V40/logs for a frozen
  build, otherwise <comfyui-dir>/../logs (the install directory's
  logs folder for a source run).

Start order:
1. If start.command exists, run it with /bin/bash, detached.
2. Otherwise, if <dir>/.venv/bin/python and <dir>/ComfyUI/main.py
   both exist, run them directly with --listen 127.0.0.1 --port 8188.
3. Otherwise report that nothing could be started.

A module-level flag prevents a second launch inside the same process,
but every call re-probes first: if the previously started server has
died, the flag is cleared and a new launch is attempted.
"""
import os
import subprocess
import sys
import threading
from urllib import request

DEFAULT_ENDPOINT = "http://127.0.0.1:8188"
DEFAULT_COMFYUI_DIR = "/Volumes/修仙漫剧/SciCloud AGI V40/ComfyUI"
_DISABLED_VALUES = {"0", "false", "no", "off"}

_started = False
_started_lock = threading.Lock()


def autostart_enabled():
    """True unless SCICLOUD_COMFYUI_AUTOSTART is 0/false/no/off."""
    raw = os.environ.get("SCICLOUD_COMFYUI_AUTOSTART")
    if raw is None:
        return True
    return raw.strip().lower() not in _DISABLED_VALUES


def resolve_comfyui_dir():
    raw = os.environ.get("SCICLOUD_COMFYUI_DIR")
    if raw and raw.strip():
        return os.path.abspath(os.path.expanduser(raw.strip()))
    return DEFAULT_COMFYUI_DIR


def resolve_start_command(comfyui_dir=None):
    raw = os.environ.get("SCICLOUD_COMFYUI_START_COMMAND")
    if raw and raw.strip():
        return os.path.abspath(os.path.expanduser(raw.strip()))
    base = comfyui_dir or resolve_comfyui_dir()
    return os.path.join(base, "start.command")


def resolve_endpoint():
    raw = os.environ.get("SCICLOUD_COMFYUI_ENDPOINT")
    if raw and raw.strip():
        return raw.strip()
    return DEFAULT_ENDPOINT


def resolve_log_path(comfyui_dir=None):
    """Absolute path of logs/comfyui_autostart.log for this run mode."""
    override = os.environ.get("SCICLOUD_COMFYUI_LOG_DIR")
    if override and override.strip():
        log_dir = os.path.abspath(os.path.expanduser(override.strip()))
    else:
        home = os.environ.get("SCICLOUD_HOME")
        if home and home.strip():
            log_dir = os.path.join(os.path.abspath(os.path.expanduser(home.strip())), "logs")
        elif getattr(sys, "frozen", False):
            log_dir = os.path.join(os.path.expanduser("~"), "SciCloud AGI V40", "logs")
        else:
            base = comfyui_dir or resolve_comfyui_dir()
            log_dir = os.path.join(os.path.dirname(base), "logs")
    return os.path.join(log_dir, "comfyui_autostart.log")


def probe_comfyui(endpoint=None, timeout=2):
    """True when ComfyUI answers /system_stats, False otherwise."""
    endpoint = endpoint or resolve_endpoint()
    try:
        with request.urlopen(endpoint.rstrip("/") + "/system_stats", timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def status():
    """Read-only status for UI labels (no side effects, never starts)."""
    comfyui_dir = resolve_comfyui_dir()
    return {
        "enabled": autostart_enabled(),
        "endpoint": resolve_endpoint(),
        "comfyui_dir": comfyui_dir,
        "start_command": resolve_start_command(comfyui_dir),
        "started": _started,
    }


def reset_started_flag():
    """Clear the in-process started flag (tests only)."""
    global _started
    with _started_lock:
        _started = False


def _default_launcher(command, log_path, cwd):
    """Start command detached; stdout/stderr go to log_path."""
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log_file = open(log_path, "a", encoding="utf-8")
    except OSError:
        log_file = subprocess.DEVNULL
    try:
        return subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            start_new_session=True,
        )
    finally:
        if log_file is not subprocess.DEVNULL:
            # The child inherits its own copy of the file descriptor;
            # closing the parent's copy does not stop the child's log.
            log_file.close()


def ensure_comfyui_running(endpoint=None, timeout=2, probe=None, launcher=None):
    """Probe, then start ComfyUI in the background only if needed.

    Never raises for an expected failure mode: start problems are
    returned in the result dict so callers can log them and continue.
    Returns a dict with keys: enabled, already_running, started,
    method, endpoint, comfyui_dir, start_command, log_path, message.
    """
    global _started
    endpoint = endpoint or resolve_endpoint()
    comfyui_dir = resolve_comfyui_dir()
    start_command = resolve_start_command(comfyui_dir)
    log_path = resolve_log_path(comfyui_dir)
    probe_fn = probe or probe_comfyui
    result = {
        "enabled": autostart_enabled(),
        "already_running": False,
        "started": False,
        "method": None,
        "endpoint": endpoint,
        "comfyui_dir": comfyui_dir,
        "start_command": start_command,
        "log_path": log_path,
        "message": "",
    }
    if not result["enabled"]:
        result["message"] = "ComfyUI 自动启动已关闭（SCICLOUD_COMFYUI_AUTOSTART），未启动。"
        return result
    try:
        reachable = bool(probe_fn(endpoint, timeout=timeout))
    except Exception:
        reachable = False
    if reachable:
        result["already_running"] = True
        result["message"] = "ComfyUI 已在运行，无需启动。"
        return result
    with _started_lock:
        if _started:
            # A previous call in this process already launched it, but
            # the probe above just failed: the server may have died.
            # Clear the flag and fall through to a fresh launch attempt.
            _started = False
    if os.path.isfile(start_command):
        command = ["/bin/bash", start_command]
        method = "start_command"
    else:
        venv_python = os.path.join(comfyui_dir, ".venv", "bin", "python")
        main_py = os.path.join(comfyui_dir, "ComfyUI", "main.py")
        if os.path.isfile(venv_python) and os.path.isfile(main_py):
            command = [
                venv_python, "-u", main_py,
                "--listen", "127.0.0.1", "--port", "8188",
            ]
            method = "direct_python"
        else:
            result["message"] = (
                "ComfyUI 未运行，且未找到启动方式：%s 不存在，"
                "<ComfyUI 目录>/.venv/bin/python 与 ComfyUI/main.py 也不完整。"
                "请手动启动 ComfyUI。" % start_command
            )
            return result
    launch = launcher or _default_launcher
    try:
        launch(command, log_path, comfyui_dir if os.path.isdir(comfyui_dir) else None)
    except Exception as exc:
        result["message"] = "ComfyUI 后台启动失败：%s" % exc
        return result
    with _started_lock:
        _started = True
    result["started"] = True
    result["method"] = method
    result["message"] = (
        "ComfyUI 正在后台启动（%s），日志：%s。"
        "若一键出片预检仍报未运行，请稍等片刻后重试。" % (method, log_path)
    )
    return result
