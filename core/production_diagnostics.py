"""Read-only local production environment diagnostics.

This module never installs software, downloads models, or contacts cloud APIs.
"""
import os
import shutil
import urllib.error
import urllib.request
from urllib.parse import urlparse
from pathlib import Path

from core.config import BASE_DIR, DATA_DIR, OUTPUT_DIR, PROJECT_DIR, LOG_DIR, BACKUP_DIR


def _http_check(url, timeout=1.5):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        return {"ok": False, "message": "为避免访问外部服务，诊断仅允许 localhost/127.0.0.1/::1"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SciCloud-Local-Diagnostics/1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return {"ok": 200 <= response.status < 500, "status_code": response.status, "message": "可连接"}
    except urllib.error.HTTPError as exc:
        # A responding service can return 4xx when its root route is not implemented.
        return {"ok": True, "status_code": exc.code, "message": "服务已响应"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:240]}


def _directory_check(path):
    try:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".scicloud_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return {"ok": True, "path": str(p), "message": "可写"}
    except Exception as exc:
        return {"ok": False, "path": str(path), "message": str(exc)[:240]}


def run_diagnostics(base_dir=None, which=shutil.which, http_check=_http_check):
    """Return a machine-readable, read-only environment report."""
    base = Path(base_dir or BASE_DIR)
    dirs = {
        "application": base,
        "data": Path(DATA_DIR) if base_dir is None else base / "data",
        "projects": Path(PROJECT_DIR) if base_dir is None else base / "projects",
        "output": Path(OUTPUT_DIR) if base_dir is None else base / "output",
        "logs": Path(LOG_DIR) if base_dir is None else base / "logs",
        "backups": Path(BACKUP_DIR) if base_dir is None else base / "backups",
    }
    tools = {}
    for name in ("ffmpeg", "ffprobe"):
        path = which(name)
        tools[name] = {"ok": bool(path), "path": path, "message": "已安装" if path else "未找到"}
    services = {
        "ollama": {"url": os.environ.get("SCICLOUD_OLLAMA_URL", "http://127.0.0.1:11434"), "check": None},
        "comfyui": {"url": os.environ.get("SCICLOUD_COMFYUI_URL", "http://127.0.0.1:8188"), "check": None},
    }
    for key, service in services.items():
        service["check"] = http_check(service["url"])
        service["ok"] = bool(service["check"].get("ok"))
    directory_checks = {key: _directory_check(path) for key, path in dirs.items()}
    checks = list(tools.values()) + [v["check"] for v in services.values()] + list(directory_checks.values())
    failed = sum(1 for item in checks if not item.get("ok"))
    return {
        "schema_version": 1,
        "mode": "read_only_local",
        "summary": {"check_count": len(checks), "passed": len(checks) - failed, "failed": failed,
                    "ready": failed == 0},
        "tools": tools,
        "services": services,
        "directories": directory_checks,
        "notes": [
            "诊断不会安装依赖或下载模型。",
            "ComfyUI/Ollama 服务可连接不代表相应模型或工作流已经可用。",
            "本机诊断不会调用云端 AI API。",
        ],
    }
