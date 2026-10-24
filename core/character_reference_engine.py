"""Versioned local character-reference assets and shot binding.

The image remains on the user's machine. Only a local ComfyUI adapter may upload
it to the local ComfyUI process when a workflow explicitly declares a reference
placeholder. This module never calls a cloud image service.
"""
import hashlib
import os
import re
import shutil
from pathlib import Path

from core.asset_manager import asset_manager
from core.config import DATA_DIR

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
REFERENCE_ROOT = os.path.join(DATA_DIR, "assets", "character_references")


def _safe(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip())[:80] or "character"


class CharacterReferenceEngine:
    def __init__(self, root=REFERENCE_ROOT, registry=asset_manager):
        self.root = os.path.abspath(root)
        self.registry = registry
        os.makedirs(self.root, exist_ok=True)

    def _image_info(self, path):
        path = os.path.abspath(os.path.expanduser(str(path or "")))
        if not os.path.isfile(path) or os.path.getsize(path) <= 0:
            raise ValueError("参考图文件不存在或为空")
        if Path(path).suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError("参考图仅支持 PNG/JPG/JPEG/WEBP/BMP")
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            header = stream.read(32)
            digest.update(header)
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        info = {"sha256": digest.hexdigest(), "size_bytes": os.path.getsize(path)}
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                info.update({"width": int(image.width), "height": int(image.height), "format": image.format})
        except ImportError:
            info["image_decode"] = "Pillow not installed; extension and non-empty file checked"
        except Exception as exc:
            raise ValueError(f"参考图无法解码：{exc}") from exc
        return path, info

    def register_reference(self, character_id, character_name, image_path, project_id=None, copy_file=True):
        character_id = str(character_id or "").strip()
        character_name = str(character_name or character_id).strip()
        if not character_id:
            raise ValueError("角色 ID 不能为空")
        source, info = self._image_info(image_path)
        existing = self.registry.list_assets(asset_type="character_reference", entity_id=character_id)
        version = max([int(item.get("version", 0) or 0) for item in existing] or [0]) + 1
        if copy_file:
            target_dir = os.path.join(self.root, _safe(character_id))
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, f"v{version:03d}_{_safe(character_name)}{Path(source).suffix.lower()}")
            shutil.copy2(source, target)
            if not os.path.isfile(target) or os.path.getsize(target) != info["size_bytes"]:
                try:
                    os.remove(target)
                except OSError:
                    pass
                raise IOError("复制参考图后校验失败")
            source = os.path.abspath(target)
        metadata = {
            "character_id": character_id, "character_name": character_name,
            "reference_image_path": source, "sha256": info["sha256"],
            "size_bytes": info["size_bytes"], "width": info.get("width"),
            "height": info.get("height"), "format": info.get("format"),
            "reference_version": version, "project_id": project_id,
        }
        item = self.registry.register(
            "character_reference", f"{character_name} · 参考图 v{version}",
            source=source, entity_id=character_id, metadata=metadata,
            project_id=project_id, version=version,
        )
        return item

    def list_references(self, character_id=None, project_id=None):
        items = self.registry.list_assets(asset_type="character_reference", entity_id=character_id)
        if project_id:
            items = [x for x in items if x.get("project_id") in (None, project_id)]
        return [x for x in items if self._valid_registered_file(x)]

    def _valid_registered_file(self, item):
        path = (item.get("metadata") or {}).get("reference_image_path") or item.get("source")
        return bool(path and os.path.isfile(path) and os.path.getsize(path) > 0)

    def latest_for_character(self, character_id=None, character_name=None, project_id=None):
        candidates = self.list_references(character_id=character_id, project_id=project_id) if character_id else self.list_references(project_id=project_id)
        if character_name:
            candidates = [x for x in candidates if
                          (x.get("metadata") or {}).get("character_name") == character_name or x.get("name", "").startswith(character_name + " ·")]
        return max(candidates, key=lambda x: int(x.get("version", 0) or 0), default=None)

    def bind_shot_references(self, shot, project_id=None):
        result = dict(shot or {})
        consistency = dict(result.get("consistency") or {})
        character_refs = []
        missing = []
        anchors = consistency.get("character_anchors") or []
        for anchor in anchors:
            if not isinstance(anchor, dict):
                continue
            asset = self.latest_for_character(anchor.get("id"), anchor.get("name"), project_id)
            if not asset:
                continue
            meta = asset.get("metadata") or {}
            path = meta.get("reference_image_path") or asset.get("source")
            if not path or not os.path.isfile(path):
                missing.append({"character_id": anchor.get("id"), "character_name": anchor.get("name")})
                continue
            character_refs.append({
                "character_id": str(anchor.get("id") or asset.get("entity_id") or ""),
                "character_name": str(anchor.get("name") or meta.get("character_name") or asset.get("name") or ""),
                "path": os.path.abspath(path), "asset_id": asset.get("asset_id"),
                "version": int(asset.get("version", 1) or 1), "sha256": meta.get("sha256", ""),
            })
        result["character_reference_assets"] = character_refs
        result["character_reference_count"] = len(character_refs)
        result["character_reference_warnings"] = missing
        if character_refs:
            result["reference_prompt"] = "；".join(
                f"角色参考图锁定：{item['character_name']}（角色 ID {item['character_id']}，参考版本 v{item['version']}），优先保持面部、发型、服装主色和标志性配饰一致"
                for item in character_refs
            )
            prompt = str(result.get("visual_prompt") or result.get("prompt") or "").strip()
            if result["reference_prompt"] not in prompt:
                result["visual_prompt"] = "；".join(x for x in [prompt, result["reference_prompt"]] if x)
        return result

    def audit(self, shots):
        total = len(shots or [])
        bound = sum(bool((shot or {}).get("character_reference_assets")) for shot in (shots or []))
        missing = []
        for shot in shots or []:
            for character in (shot or {}).get("character_reference_warnings", []):
                missing.append({"shot_id": (shot or {}).get("shot_id"), **character})
        return {"shot_count": total, "shots_with_reference": bound,
                "shots_without_reference": max(0, total - bound),
                "reference_coverage_percent": round(bound / total * 100, 1) if total else 0,
                "missing_reference_bindings": missing}


character_reference_engine = CharacterReferenceEngine()
