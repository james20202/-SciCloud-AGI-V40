"""Create a deterministic, verifiable episode handoff ZIP from existing workflow artifacts."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


def _safe_name(value: Any, fallback: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or fallback)).strip("._")
    return name or fallback


def build_episode_package(workflow: dict[str, Any], output_path: str) -> dict[str, Any]:
    """Package completed production outputs without regenerating or mutating source files."""
    if not isinstance(workflow, dict) or not isinstance(workflow.get("tasks"), list):
        raise ValueError("工作流结构无效，无法打包")
    tasks = workflow["tasks"]
    completed_types = {task.get("type") for task in tasks if isinstance(task, dict) and task.get("status") == "done"}
    if "edit" not in completed_types:
        raise ValueError("最终剪辑任务尚未完成，拒绝生成成片交付包")
    if "qc" not in completed_types:
        raise ValueError("质检任务尚未完成，拒绝生成成片交付包")

    workflow_id = str(workflow.get("workflow_id") or "workflow")
    plan_id = str(workflow.get("plan_id") or "")
    title = str(workflow.get("title") or workflow_id)
    files: list[tuple[str, str]] = []
    missing: list[str] = []
    seen: set[str] = set()
    subtitles: list[tuple[str, str]] = []
    qc_payloads: list[dict[str, Any]] = []
    qc_report_found = False
    qc_failed = False
    final_video_found = False
    ignored_incomplete_outputs: list[dict[str, Any]] = []
    video_suffixes = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = _safe_name(task.get("id"), "task")
        outputs = task.get("outputs") or []
        if task.get("status") != "done":
            if outputs:
                ignored_incomplete_outputs.append({
                    "task_id": task_id,
                    "task_type": task.get("type"),
                    "status": task.get("status"),
                    "output_count": len(outputs) if isinstance(outputs, (list, tuple)) else 1,
                })
            continue
        for output in outputs:
            source = output.get("path") if isinstance(output, dict) else output
            if not isinstance(source, str) or not os.path.isfile(source) or os.path.getsize(source) <= 0:
                if source:
                    missing.append(str(source))
                continue
            absolute = os.path.abspath(source)
            suffix = Path(absolute).suffix.lower()
            if task.get("type") == "edit" and suffix in video_suffixes:
                final_video_found = True
            if absolute in seen:
                continue
            seen.add(absolute)
            folder = "media" if suffix in video_suffixes | {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".png", ".jpg", ".jpeg", ".webp"} else "artifacts"
            base_name = _safe_name(Path(absolute).name, "artifact")
            archive_name = f"{folder}/{task_id}/{base_name}"
            collision_index = 2
            existing_names = {name for _, name in files}
            while archive_name in existing_names:
                stem, extension = os.path.splitext(base_name)
                archive_name = f"{folder}/{task_id}/{stem}_{collision_index}{extension}"
                collision_index += 1
            files.append((absolute, archive_name))
            if task.get("type") == "qc" and suffix == ".json":
                try:
                    with open(absolute, encoding="utf-8") as handle:
                        payload = json.load(handle)
                    if isinstance(payload, dict):
                        if payload.get("success") is False:
                            qc_failed = True
                        if isinstance(payload.get("success"), bool):
                            qc_report_found = qc_report_found or payload.get("success") is True
                            qc_payloads.append(payload)
                except (OSError, ValueError):
                    pass
            if task.get("type") == "prompt" and suffix == ".json":
                try:
                    with open(absolute, encoding="utf-8") as handle:
                        payload = json.load(handle)
                    srt = payload.get("subtitle_srt_draft") if isinstance(payload, dict) else None
                    if isinstance(srt, str) and srt.strip():
                        subtitles.append((task_id, srt))
                except (OSError, ValueError):
                    pass

    if qc_failed:
        raise ValueError("质检报告未通过，拒绝生成成片交付包")
    if not qc_report_found:
        raise ValueError("没有找到明确通过的质检报告，拒绝生成成片交付包")
    if not final_video_found:
        raise ValueError("最终剪辑任务没有可用的非空最终视频文件，拒绝生成成片交付包")
    if not files:
        raise ValueError("没有可验证的非空生产制品，无法生成交付包")

    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    manifest_files = []
    for source, archive_name in files:
        digest = hashlib.sha256()
        with open(source, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        manifest_files.append({
            "archive_path": archive_name,
            "source_name": os.path.basename(source),
            "size_bytes": os.path.getsize(source),
            "sha256": digest.hexdigest(),
        })

    manifest = {
        "schema_version": 1,
        "package_type": "scicloud_episode_handoff",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "workflow_id": workflow_id,
        "plan_id": plan_id,
        "title": title,
        "completed_task_types": sorted(str(item) for item in completed_types if item),
        "file_count": len(manifest_files),
        "missing_or_invalid_outputs": missing,
        "ignored_incomplete_task_outputs": ignored_incomplete_outputs,
        "files": manifest_files,
        "qc_reports": qc_payloads,
        "limitations": [
            "Package includes only existing non-empty files; it does not fabricate missing media.",
            "Subtitle draft timing is planned-shot timing unless an upstream audio-alignment stage replaced it.",
        ],
    }

    fd, temp_path = tempfile.mkstemp(prefix=".episode-package-", suffix=".tmp", dir=os.path.dirname(output_path))
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for source, archive_name in files:
                archive.write(source, archive_name)
            for task_id, srt in subtitles:
                archive.writestr(f"subtitles/{task_id}_draft.srt", srt)
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("README.txt", (
                f"{title} - SciCloud AGI episode handoff package\n"
                f"Workflow: {workflow_id}\nPlan: {plan_id}\n"
                "See manifest.json for file hashes and validation scope.\n"
            ))
        if not os.path.isfile(temp_path) or os.path.getsize(temp_path) <= 0:
            raise RuntimeError("交付包 ZIP 生成失败或文件为空")
        with zipfile.ZipFile(temp_path, "r") as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise RuntimeError(f"交付包 ZIP 校验失败：{bad_member}")
        os.replace(temp_path, output_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "success": True,
        "output_path": output_path,
        "file_count": len(manifest_files),
        "subtitle_drafts": len(subtitles),
        "missing_or_invalid_outputs": missing,
        "manifest": manifest,
    }
