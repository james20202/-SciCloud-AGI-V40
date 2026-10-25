"""Canonical shot-level production contract shared by storyboard, prompt, media and edit stages.

This module intentionally has no model, GUI, network, or heavy dependency. It normalizes
existing SciCloud dictionaries without replacing the workflow engine or stored project format.
"""
from __future__ import annotations

import math
from typing import Any, Iterable


SHOT_FIELDS = (
    "shot_id", "shot_index", "duration", "visual_prompt", "dialogue",
    "voiceover", "scene_id", "character_ids",
)


def normalize_shot(raw: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """Return a validated, backward-compatible canonical shot record."""
    if not isinstance(raw, dict):
        raise ValueError("shot 必须是对象")
    shot_id = raw.get("shot_id") or raw.get("id")
    if not isinstance(shot_id, str) or not shot_id.strip():
        raise ValueError("shot_id 缺失")
    shot_id = shot_id.strip()
    try:
        duration = float(raw.get("duration", raw.get("duration_seconds", 5.0)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"镜头 {shot_id} duration 无效") from exc
    if not math.isfinite(duration) or duration <= 0 or duration > 3600:
        raise ValueError(f"镜头 {shot_id} duration 必须大于 0 且不超过 3600 秒")

    raw_characters = raw.get("character_ids", [])
    if raw_characters is None:
        raw_characters = []
    if not isinstance(raw_characters, list):
        raise ValueError(f"镜头 {shot_id} character_ids 必须是列表")
    character_ids = []
    for item in raw_characters:
        value = item.get("id") if isinstance(item, dict) else item
        if isinstance(value, str) and value.strip() and value.strip() not in character_ids:
            character_ids.append(value.strip())

    scene_id = raw.get("scene_id", "")
    if isinstance(scene_id, dict):
        scene_id = scene_id.get("id", "")
    if scene_id is None:
        scene_id = ""
    if not isinstance(scene_id, str):
        raise ValueError(f"镜头 {shot_id} scene_id 必须是字符串")

    prompt = raw.get("visual_prompt")
    if prompt is None or not str(prompt).strip():
        prompt = raw.get("prompt", "")
    dialogue = raw.get("dialogue", "")
    voiceover = raw.get("voiceover", raw.get("narration", ""))
    for name, value in (("visual_prompt", prompt), ("dialogue", dialogue), ("voiceover", voiceover)):
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError(f"镜头 {shot_id} {name} 必须是字符串")
        if name == "visual_prompt":
            prompt = value
        elif name == "dialogue":
            dialogue = value
        else:
            voiceover = value

    try:
        shot_index = int(raw.get("shot_index", raw.get("index", index + 1)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"镜头 {shot_id} shot_index 无效") from exc
    if shot_index < 1:
        raise ValueError(f"镜头 {shot_id} shot_index 必须从 1 开始")

    result = dict(raw)
    result.update({
        "shot_id": shot_id, "shot_index": shot_index, "duration": duration,
        "visual_prompt": prompt, "prompt": prompt, "dialogue": dialogue,
        "voiceover": voiceover, "scene_id": scene_id, "character_ids": character_ids,
    })
    return result


def normalize_shots(shots: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize a shot sequence and reject duplicate IDs."""
    if not isinstance(shots, (list, tuple)):
        raise ValueError("shots 必须是列表")
    normalized = [normalize_shot(shot, index) for index, shot in enumerate(shots)]
    ids = [shot["shot_id"] for shot in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("shot_id 重复")
    return normalized


def timeline_duration(shots: Iterable[dict[str, Any]]) -> float:
    """Return total planned duration from canonical or legacy shot records."""
    return round(sum(shot["duration"] for shot in normalize_shots(list(shots))), 3)


def build_shot_manifest(shots: Iterable[dict[str, Any]], *, target_duration: float | None = None) -> dict[str, Any]:
    """Create a deterministic timeline manifest without silently stretching shots."""
    normalized = normalize_shots(list(shots))
    total = timeline_duration(normalized)
    if target_duration is not None:
        try:
            target = float(target_duration)
        except (TypeError, ValueError) as exc:
            raise ValueError("target_duration 无效") from exc
        if not math.isfinite(target) or target <= 0 or target > 86400:
            raise ValueError("target_duration 必须大于 0 且不超过 86400 秒")
    else:
        target = None
    return {
        "schema_version": 1,
        "shots": normalized,
        "shot_count": len(normalized),
        "planned_duration_seconds": total,
        "target_duration_seconds": target,
        "duration_delta_seconds": round(total - target, 3) if target is not None else None,
        "duration_matches_target": abs(total - target) <= 0.05 if target is not None else None,
    }
