"""Deterministic per-shot generation manifest for resumable video production.

This module is intentionally dependency-free. It converts canonical storyboard prompts into
stable task specifications; execution adapters can consume these records without re-parsing
the director plan or losing shot identity and timing.
"""
from __future__ import annotations

import re
from typing import Any

from core.shot_contract import normalize_shots, build_shot_manifest


def _safe_component(value: Any, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "")).strip("_")
    return text or fallback


def build_shot_batch_manifest(
    prompts: list[dict[str, Any]],
    *,
    workflow_id: str,
    target_duration: float | None = None,
    workflow_registry_id: str | None = None,
    workflow_capability: str = "video.image2video",
) -> dict[str, Any]:
    """Build stable per-shot records with isolated output paths and retry identity."""
    normalized = normalize_shots(prompts)
    if not normalized:
        raise ValueError("镜头批次不能为空")
    safe_workflow = _safe_component(workflow_id, "workflow")
    if not isinstance(workflow_capability, str) or not workflow_capability.strip():
        raise ValueError("workflow_capability 必须是非空字符串")
    manifest = build_shot_manifest(normalized, target_duration=target_duration)
    jobs = []
    for shot in normalized:
        safe_shot = _safe_component(shot["shot_id"], f"shot-{shot['shot_index']:04d}")
        visual = shot.get("visual_prompt") or shot.get("prompt") or ""
        generated = shot.get("prompt") or visual
        if not isinstance(visual, str) or not visual.strip():
            raise ValueError(f"镜头 {shot['shot_id']} 缺少 visual_prompt")
        if not isinstance(generated, str) or not generated.strip():
            raise ValueError(f"镜头 {shot['shot_id']} 缺少生成提示词")
        job = {
            "job_id": f"{safe_workflow}__{safe_shot}",
            "workflow_id": workflow_id,
            "task_type": "video",
            "shot_id": shot["shot_id"],
            "shot_index": shot["shot_index"],
            "duration_seconds": shot["duration"],
            "visual_prompt": visual,
            "prompt": generated,
            "dialogue": shot.get("dialogue", ""),
            "voiceover": shot.get("voiceover", ""),
            "scene_id": shot.get("scene_id", ""),
            "character_ids": list(shot.get("character_ids", [])),
            "output_path": f"output/shots/{safe_workflow}/{safe_shot}.mp4",
            "status": "planned",
            "attempt": 0,
        }
        if workflow_registry_id:
            job["workflow_registry_id"] = workflow_registry_id
        job["workflow_capability"] = workflow_capability
        jobs.append(job)
    return {
        "schema_version": 1,
        "workflow_id": workflow_id,
        "workflow_registry_id": workflow_registry_id,
        "workflow_capability": workflow_capability,
        "shot_count": len(jobs),
        "planned_duration_seconds": manifest["planned_duration_seconds"],
        "target_duration_seconds": manifest["target_duration_seconds"],
        "duration_matches_target": manifest["duration_matches_target"],
        "jobs": jobs,
    }
