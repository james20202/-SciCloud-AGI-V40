"""Deterministic extraction of reusable production assets from a director plan.

This is a SciCloud-native adaptation of the script/asset pipeline concept documented
by tccnnd/Comic-drama (MIT). It deliberately extracts only entities explicitly
present in structured plan fields; it does not invent characters or props from prose.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.asset_manager import asset_manager


def _text(value: Any) -> str:
    return str(value or "").strip()


def _entity_id(entity: dict, prefix: str, index: int) -> str:
    return _text(entity.get("id") or entity.get("character_id") or entity.get("scene_id")
                 or entity.get("prop_id") or entity.get("shot_id")) or f"{prefix}-{index:04d}"


def _explicit_props(plan: dict) -> list[dict]:
    found: list[dict] = []
    for key in ("props", "objects", "key_props"):
        values = plan.get(key)
        if isinstance(values, list):
            found.extend(v for v in values if isinstance(v, dict))
    for scene in plan.get("scenes", []) if isinstance(plan.get("scenes"), list) else []:
        if not isinstance(scene, dict):
            continue
        for key in ("props", "objects", "key_props"):
            values = scene.get(key)
            if isinstance(values, list):
                found.extend(v if isinstance(v, dict) else {"name": v} for v in values if _text(v))
    for shot in plan.get("shots", []) if isinstance(plan.get("shots"), list) else []:
        if not isinstance(shot, dict):
            continue
        for key in ("props", "props_in_scene", "key_props"):
            values = shot.get(key)
            if isinstance(values, list):
                found.extend(v if isinstance(v, dict) else {"name": v} for v in values if _text(v))
    unique: dict[str, dict] = {}
    for i, prop in enumerate(found, 1):
        name = _text(prop.get("name") or prop.get("label") or prop.get("title"))
        if not name:
            continue
        pid = _entity_id(prop, "PROP", i)
        unique.setdefault(pid.casefold(), {**prop, "id": pid, "name": name})
    return list(unique.values())


class ScriptAssetExtractor:
    """Register characters, locations, explicit props and shot cards idempotently."""

    def __init__(self, registry=asset_manager):
        self.registry = registry

    def extract(self, plan: dict, project_id: str | None = None) -> dict:
        if not isinstance(plan, dict):
            raise TypeError("导演计划必须是对象")
        plan_id = _text(plan.get("plan_id"))
        if not plan_id:
            raise ValueError("导演计划缺少 plan_id")
        project_id = _text(project_id or plan_id)
        collections = (
            ("character", "characters", "CHAR"),
            ("scene", "scenes", "SCENE"),
            ("prop", None, "PROP"),
        )
        entities: list[tuple[str, dict, str]] = []
        for asset_type, field, prefix in collections:
            source = plan.get(field, []) if field else _explicit_props(plan)
            if isinstance(source, list):
                for index, entity in enumerate(source, 1):
                    if not isinstance(entity, dict):
                        continue
                    name = _text(entity.get("name") or entity.get("title") or entity.get("label"))
                    if not name:
                        continue
                    stable_id = _entity_id(entity, prefix, index)
                    entities.append((asset_type, {**entity, "id": stable_id, "name": name}, stable_id))
        for index, shot in enumerate(plan.get("shots", []) if isinstance(plan.get("shots"), list) else [], 1):
            if not isinstance(shot, dict):
                continue
            sid = _entity_id(shot, "SHOT", index)
            entities.append(("storyboard", {
                **shot, "id": sid, "name": _text(shot.get("name") or shot.get("type") or f"镜头 {index}"),
                "visual_prompt": _text(shot.get("visual_prompt") or shot.get("prompt")),
                "dialogue": deepcopy(shot.get("dialogue", "")),
                "duration_seconds": shot.get("duration_seconds", shot.get("duration", 5)),
            }, sid))

        existing = self.registry.list_assets()
        by_key = {
            _text((item.get("metadata") or {}).get("extraction_key"))
            for item in existing if isinstance(item, dict)
        }
        created, reused = [], 0
        for asset_type, entity, stable_id in entities:
            key = f"{plan_id}:{asset_type}:{stable_id}"
            if key in by_key:
                reused += 1
                continue
            metadata = deepcopy(entity)
            metadata.update({
                "source_plan_id": plan_id,
                "source_entity_id": stable_id,
                "extraction_key": key,
                "extraction_method": "structured_plan_fields",
            })
            item = self.registry.register(
                asset_type=asset_type,
                name=entity["name"],
                entity_id=stable_id,
                project_id=project_id,
                metadata=metadata,
            )
            created.append({"asset_id": item.get("asset_id"), "type": asset_type,
                            "entity_id": stable_id, "name": entity["name"]})
            by_key.add(key)
        return {
            "success": True, "plan_id": plan_id, "project_id": project_id,
            "created_count": len(created), "reused_count": reused,
            "character_count": sum(x[0] == "character" for x in entities),
            "scene_count": sum(x[0] == "scene" for x in entities),
            "prop_count": sum(x[0] == "prop" for x in entities),
            "shot_card_count": sum(x[0] == "storyboard" for x in entities),
            "created": created,
        }


script_asset_extractor = ScriptAssetExtractor()
