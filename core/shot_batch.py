"""Canonical per-shot batch manifests and resumable media execution helpers."""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
from typing import Any, Callable

from core.shot_contract import build_shot_manifest, normalize_shots


def _safe_component(value: Any, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "")).strip("_")
    return cleaned or fallback


def build_shot_batch_manifest(
    shots: list[dict[str, Any]],
    *,
    workflow_id: str,
    target_duration: float | None = None,
    workflow_registry_id: str | None = None,
    workflow_capability: str = "video.image2video",
) -> dict[str, Any]:
    """Build stable, path-safe jobs while preserving all canonical shot context."""
    if not isinstance(shots, (list, tuple)) or not shots:
        raise ValueError("镜头批次不能为空")
    normalized = normalize_shots(list(shots))
    timeline = build_shot_manifest(normalized, target_duration=target_duration)
    safe_workflow = _safe_component(workflow_id, "workflow")
    jobs = []
    for index, shot in enumerate(normalized):
        visual_prompt = shot.get("visual_prompt", "")
        prompt = shot.get("prompt") or visual_prompt
        if not isinstance(visual_prompt, str) or not visual_prompt.strip():
            raise ValueError(f"镜头 {shot['shot_id']} visual_prompt 不能为空")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"镜头 {shot['shot_id']} prompt 不能为空")
        safe_shot = _safe_component(shot["shot_id"], f"shot_{index + 1:04d}")
        jobs.append({
            "job_id": f"{safe_workflow}__{safe_shot}",
            "shot_id": shot["shot_id"],
            "shot_index": shot["shot_index"],
            "duration_seconds": round(float(shot["duration"]), 3),
            "prompt": prompt,
            "visual_prompt": visual_prompt,
            "dialogue": shot.get("dialogue", ""),
            "voiceover": shot.get("voiceover", ""),
            "scene_id": shot.get("scene_id", ""),
            "character_ids": list(shot.get("character_ids", [])),
            "workflow_registry_id": workflow_registry_id,
            "workflow_capability": workflow_capability,
            "output_path": f"output/shots/{safe_workflow}/{safe_shot}.mp4",
            "status": "planned",
            "attempt": 0,
            "outputs": [],
        })
    return {
        "schema_version": 1,
        "workflow_id": workflow_id,
        "workflow_registry_id": workflow_registry_id,
        "workflow_capability": workflow_capability,
        "shot_count": len(jobs),
        "planned_duration_seconds": timeline["planned_duration_seconds"],
        "target_duration_seconds": timeline["target_duration_seconds"],
        "duration_delta_seconds": timeline["duration_delta_seconds"],
        "duration_matches_target": timeline["duration_matches_target"],
        "status": "planned",
        "progress": {"total": len(jobs), "done": 0, "failed": 0, "pending": len(jobs)},
        "jobs": jobs,
    }


def save_shot_batch_manifest(manifest: dict[str, Any], path: str) -> str:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("jobs"), list):
        raise ValueError("镜头批次清单结构无效")
    target = os.path.abspath(path)
    parent = os.path.dirname(target)
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".shot-batch-", suffix=".tmp", dir=parent)
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


def load_or_reconcile_shot_batch_manifest(
    fresh_manifest: dict[str, Any], path: str
) -> dict[str, Any]:
    """Reuse checkpoints only when current shot identity and immutable inputs match."""
    if not isinstance(fresh_manifest, dict) or not isinstance(fresh_manifest.get("jobs"), list):
        raise ValueError("新的镜头批次清单结构无效")
    if not os.path.isfile(path):
        return fresh_manifest
    try:
        with open(path, encoding="utf-8") as handle:
            previous = json.load(handle)
    except (OSError, ValueError, TypeError):
        return fresh_manifest
    if not isinstance(previous, dict) or not isinstance(previous.get("jobs"), list):
        return fresh_manifest

    old_by_id = {}
    for job in previous["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("job_id"), str):
            return fresh_manifest
        if job["job_id"] in old_by_id:
            return fresh_manifest
        old_by_id[job["job_id"]] = job

    new_jobs = fresh_manifest["jobs"]
    new_ids = [job.get("job_id") for job in new_jobs if isinstance(job, dict)]
    if len(new_ids) != len(new_jobs) or set(new_ids) != set(old_by_id):
        return fresh_manifest

    immutable_fields = (
        "shot_id", "shot_index", "duration_seconds", "prompt", "visual_prompt",
        "dialogue", "voiceover", "scene_id", "character_ids", "output_path",
    )
    merged_jobs = []
    for new_job in new_jobs:
        old_job = old_by_id[new_job["job_id"]]
        if any(old_job.get(key) != new_job.get(key) for key in immutable_fields):
            return fresh_manifest
        merged = dict(new_job)
        merged["status"] = old_job.get("status", "planned")
        merged["attempt"] = old_job.get("attempt", 0)
        merged["outputs"] = old_job.get("outputs", [])
        if old_job.get("error"):
            merged["error"] = old_job["error"]
        merged_jobs.append(merged)
    reconciled = dict(fresh_manifest)
    reconciled["jobs"] = merged_jobs
    reconciled["status"] = previous.get("status", "planned")
    reconciled["resumed_from_checkpoint"] = True
    return reconciled


def run_shot_batch(
    manifest: dict[str, Any],
    render_job: Callable[[dict[str, Any]], list[Any]],
    manifest_path: str,
    *,
    retry_failed: bool = False,
) -> dict[str, Any]:
    """Run unfinished jobs sequentially and atomically checkpoint every transition."""
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
