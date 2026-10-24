"""Stable character/scene anchors and resumable-shot fingerprints.

The data contract is independently implemented for SciCloud. It is inspired by
MIT-licensed LocalMiniDrama's reusable character/scene assets and workflow retry
concepts; no third-party source files are copied into this module.
"""
import hashlib
import json
import os
import re


def _text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def _id(item):
    if not isinstance(item, dict):
        return ""
    return str(item.get("id") or item.get("character_id") or item.get("scene_id") or "").strip()


class ShotConsistencyEngine:
    """Attach canonical visual anchors without requiring a cloud model."""

    def build_bible(self, plan):
        characters = []
        for item in (plan or {}).get("characters", []) or []:
            if not isinstance(item, dict):
                continue
            cid = _id(item)
            if cid:
                characters.append({
                    "id": cid,
                    "name": _text(item.get("name")) or cid,
                    "description": _text(item.get("visual_description") or item.get("appearance") or item.get("description")),
                    "costume": _text(item.get("costume") or item.get("outfit")),
                    "signature": _text(item.get("signature_features") or item.get("features")),
                })
        scenes = []
        for item in (plan or {}).get("scenes", []) or []:
            if not isinstance(item, dict):
                continue
            sid = _id(item)
            if sid:
                scenes.append({
                    "id": sid,
                    "name": _text(item.get("name")) or sid,
                    "visual_anchor": _text(item.get("visual_description") or item.get("visual_anchor") or item.get("description")),
                    "lighting": _text(item.get("lighting")),
                    "palette": _text(item.get("palette") or item.get("color_palette")),
                })
        intent = (plan or {}).get("intent") or {}
        style = _text((plan or {}).get("visual_style") or (plan or {}).get("style") or intent.get("visual_style"))
        if not style:
            genre = _text(intent.get("genre"))
            style = (genre + "，电影级构图，统一光影与色彩，角色外观跨镜头保持一致").strip("，")
        return {"schema_version": 1, "style_anchor": style, "characters": characters, "scenes": scenes}

    def enrich_shot(self, shot, bible):
        """Return a copy of a shot with stable IDs and reusable visual anchors."""
        result = dict(shot or {})
        character_map = {x["id"]: x for x in bible.get("characters", [])}
        scene_map = {x["id"]: x for x in bible.get("scenes", [])}
        spec_chars = result.get("character_ids") or result.get("characters") or result.get("character_id")
        if isinstance(spec_chars, str):
            refs = [x.strip() for x in re.split(r"[,，;；|]", spec_chars) if x.strip()]
        elif isinstance(spec_chars, list):
            refs = [str(x.get("id") or x.get("character_id") or x.get("name") or "") if isinstance(x, dict) else str(x) for x in spec_chars]
        elif spec_chars:
            refs = [str(spec_chars)]
        else:
            refs = []
        # Resolve names as well as stable IDs, but never guess a character when the
        # storyboard does not identify one.
        anchors = []
        for ref in refs:
            found = character_map.get(ref) or next((x for x in character_map.values() if x["name"] == ref), None)
            if found and found not in anchors:
                anchors.append(found)
        scene_ref = str(result.get("scene_id") or "")
        scene = scene_map.get(scene_ref) or next((x for x in scene_map.values() if x["name"] == scene_ref), None)
        result["consistency"] = {
            "schema_version": 1,
            "style_anchor": bible.get("style_anchor", ""),
            "character_ids": [x["id"] for x in anchors],
            "character_anchors": anchors,
            "scene_id": scene["id"] if scene else scene_ref,
            "scene_anchor": scene or {},
        }
        visual = _text(result.get("visual_prompt") or result.get("prompt"))
        anchor_text = [x["name"] + "：" + "；".join(v for v in [x["description"], x["costume"], x["signature"]] if v) for x in anchors]
        scene_text = "；".join(v for v in [scene.get("name"), scene.get("visual_anchor"), scene.get("lighting"), scene.get("palette")] if v) if scene else ""
        result["visual_prompt"] = "；".join(x for x in [
            visual,
            ("角色统一锚点：" + "；".join(anchor_text)) if anchor_text else "",
            ("场景统一锚点：" + scene_text) if scene_text else "",
            "统一视觉风格：" + bible.get("style_anchor", "") if bible.get("style_anchor") else "",
        ] if x)
        return result


def shot_fingerprint(spec):
    """Stable hash for inputs that affect a shot; ignores transient status fields."""
    payload = dict(spec or {})
    for key in ("status", "progress", "updated_at", "created_at", "last_result", "attempts", "artifacts"):
        payload.pop(key, None)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def valid_artifacts(artifacts):
    """Filter artifacts whose files still exist and are non-empty."""
    result = []
    seen = set()
    for item in artifacts or []:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not path or not os.path.isfile(path) or os.path.getsize(path) <= 0:
            continue
        absolute = os.path.abspath(path)
        if absolute in seen:
            continue
        seen.add(absolute)
        normalized = dict(item)
        normalized["path"] = absolute
        normalized["size"] = os.path.getsize(absolute)
        result.append(normalized)
    return result


shot_consistency_engine = ShotConsistencyEngine()
