"""Episode-level acceptance checks for the canonical picture timeline.

Pure validation logic: no model calls, media downloads, or filesystem writes.
"""
from __future__ import annotations

from typing import Any


def validate_episode_timeline(timeline: dict[str, Any], expected_duration: float,
                               tolerance: float | None = None) -> dict[str, Any]:
    """Validate ordered, contiguous positive-duration picture clips and target length."""
    errors: list[dict[str, Any]] = []
    if not isinstance(timeline, dict):
        return {"success": False, "passed": False, "errors": [{"code": "invalid_timeline", "message": "时间线必须是对象"}]}
    try:
        target = float(expected_duration)
    except (TypeError, ValueError):
        target = 0.0
    if target <= 0:
        errors.append({"code": "invalid_target_duration", "message": "目标时长必须大于 0"})
    if tolerance is None:
        tolerance = max(3.0, target * 0.08)
    try:
        tolerance = max(0.0, float(tolerance))
    except (TypeError, ValueError):
        tolerance = max(3.0, target * 0.08)

    tracks = timeline.get("tracks")
    picture = next((t for t in tracks if isinstance(t, dict) and t.get("track_type") == "video"), None) if isinstance(tracks, list) else None
    children = picture.get("children") if isinstance(picture, dict) else None
    if not isinstance(children, list) or not children:
        errors.append({"code": "missing_picture_clips", "message": "时间线缺少视频镜头"})
        children = []

    cursor = 0.0
    for index, clip in enumerate(children, 1):
        if not isinstance(clip, dict):
            errors.append({"code": "invalid_clip", "index": index, "message": "镜头记录格式错误"})
            continue
        try:
            start = float(clip.get("start_seconds"))
            duration = float(clip.get("duration_seconds"))
            end = float(clip.get("end_seconds"))
        except (TypeError, ValueError):
            errors.append({"code": "invalid_clip_timing", "index": index, "message": "镜头时间字段缺失或无效"})
            continue
        if duration <= 0:
            errors.append({"code": "nonpositive_clip_duration", "index": index, "message": "镜头时长必须大于 0"})
        if abs(start - cursor) > 0.02:
            errors.append({"code": "timeline_gap_or_overlap", "index": index,
                           "expected_start": round(cursor, 3), "actual_start": start,
                           "message": "镜头时间线存在间隙或重叠"})
        if abs(end - (start + duration)) > 0.02:
            errors.append({"code": "clip_end_mismatch", "index": index, "message": "镜头结束时间与起始时间/时长不一致"})
        cursor = max(cursor, end) if duration > 0 else cursor

    declared = timeline.get("duration_seconds")
    try:
        declared_duration = float(declared)
    except (TypeError, ValueError):
        declared_duration = -1.0
    if declared_duration < 0 or abs(declared_duration - cursor) > 0.02:
        errors.append({"code": "declared_timeline_duration_mismatch",
                       "calculated_duration_seconds": round(cursor, 3),
                       "declared_duration_seconds": declared_duration,
                       "message": "时间线声明总时长与镜头累计时长不一致"})
    if target > 0 and abs(cursor - target) > tolerance:
        errors.append({"code": "episode_duration_mismatch",
                       "target_duration_seconds": target,
                       "actual_duration_seconds": round(cursor, 3),
                       "tolerance_seconds": tolerance,
                       "message": "镜头时间线总时长超出单集目标允许误差"})
    return {
        "success": not errors,
        "passed": not errors,
        "shot_count": len(children),
        "duration_seconds": round(cursor, 3),
        "expected_duration_seconds": target,
        "tolerance_seconds": tolerance,
        "errors": errors,
        "message": "时间线验收通过" if not errors else "时间线验收未通过",
    }
