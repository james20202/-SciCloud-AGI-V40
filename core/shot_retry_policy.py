"""Safe selective retry policy for resumable shot production."""
from __future__ import annotations

from typing import Iterable


RETRYABLE_STATUSES = {"failed", "blocked"}


def retryable_shot_ids(run: dict, requested_ids: Iterable[str] | None = None) -> list[str]:
    """Return only failed/blocked shots; successful shots are never selected."""
    requested = {str(value) for value in requested_ids} if requested_ids is not None else None
    result = []
    for shot in run.get("shots", []) if isinstance(run, dict) else []:
        if not isinstance(shot, dict):
            continue
        shot_id = str(shot.get("shot_id") or "")
        if requested is not None and shot_id not in requested:
            continue
        if shot.get("status") in RETRYABLE_STATUSES:
            result.append(shot_id)
    return result


def prepare_retry(run: dict, requested_ids: Iterable[str] | None = None) -> dict:
    """Reset retryable shots to ready while leaving all other shot records untouched."""
    selected = set(retryable_shot_ids(run, requested_ids))
    changed = 0
    for shot in run.get("shots", []) if isinstance(run, dict) else []:
        if shot.get("shot_id") not in selected:
            continue
        shot["status"] = "ready"
        # Failed partial outputs are removed from the active artifact list so they
        # cannot accidentally satisfy a later stage; files are retained on disk.
        shot["artifacts"] = []
        shot["last_result"] = {
            "success": False,
            "message": "已将失败镜头重新排队；已完成镜头保持不变，可继续生产。",
        }
        changed += 1
    return {"success": True, "retry_count": changed, "retry_shot_ids": sorted(selected), "run": run}
