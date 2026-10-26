"""Persistent, resumable execution helpers for per-shot media batches."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable


def save_shot_batch_manifest(manifest: dict[str, Any], path: str) -> str:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("jobs"), list):
        raise ValueError("镜头批次清单结构无效")
    target = os.path.abspath(path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".shot-batch-", suffix=".tmp", dir=os.path.dirname(target))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return target


def run_shot_batch(
    manifest: dict[str, Any],
    render_job: Callable[[dict[str, Any]], list[Any]],
    manifest_path: str,
    *,
    retry_failed: bool = False,
) -> dict[str, Any]:
    """Run unfinished jobs sequentially; checkpoint every state transition.

    render_job must return paths or {'path': path} records for real output files.
    Completed jobs with valid outputs are skipped on resume.
    """
    if not isinstance(manifest, dict) or not isinstance(manifest.get("jobs"), list) or not manifest["jobs"]:
        raise ValueError("镜头批次清单无效或为空")
    jobs = manifest["jobs"]
    seen = set()
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get("job_id"), str) or not job["job_id"]:
            raise ValueError("镜头批次包含无效 job_id")
        if job["job_id"] in seen:
            raise ValueError(f"镜头批次 job_id 重复：{job['job_id']}")
        seen.add(job["job_id"])
        job.setdefault("attempt", 0)
        job.setdefault("outputs", [])
        if job.get("status") == "done":
            valid = [item for item in job["outputs"] if _valid_output(item)]
            if valid:
                job["outputs"] = valid
                continue
            job["status"] = "pending"
            job["error"] = "之前记录的输出文件已不存在或为空"
    manifest["status"] = "running"
    save_shot_batch_manifest(manifest, manifest_path)
    for job in jobs:
        status = job.get("status")
        if status == "done":
            continue
        if status == "failed" and not retry_failed:
            continue
        if status not in {"planned", "pending", "failed", "running"}:
            job["status"] = "failed"
            job["error"] = f"不支持的任务状态：{status}"
            save_shot_batch_manifest(manifest, manifest_path)
            continue
        job["status"] = "running"
        job["attempt"] = int(job.get("attempt", 0)) + 1
        job.pop("error", None)
        save_shot_batch_manifest(manifest, manifest_path)
        try:
            outputs = render_job(dict(job))
            valid = [item for item in (outputs or []) if _valid_output(item)]
            if not valid:
                raise RuntimeError("镜头任务未生成可验证的非空媒体文件")
            job["outputs"] = valid
            job["status"] = "done"
            job.pop("error", None)
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)[:1200]
            job["outputs"] = []
        save_shot_batch_manifest(manifest, manifest_path)
    done = sum(1 for job in jobs if job.get("status") == "done")
    failed = sum(1 for job in jobs if job.get("status") == "failed")
    pending = len(jobs) - done - failed
    manifest["status"] = "done" if done == len(jobs) else ("failed" if failed else "pending")
    manifest["progress"] = {"total": len(jobs), "done": done, "failed": failed, "pending": pending}
    save_shot_batch_manifest(manifest, manifest_path)
    return manifest


def _valid_output(item: Any) -> bool:
    path = item.get("path") if isinstance(item, dict) else item
    return isinstance(path, str) and os.path.isfile(path) and os.path.getsize(path) > 0
