"""Model-agnostic ComfyUI workflow manifest registry inspired by dsh-short-video-studio.

This module adapts the workflow-manifest pattern to SciCloud's Python desktop app.
It intentionally does not vendor or execute third-party plugin code.
"""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any

CAPABILITIES = {
    "image.text2image",
    "image.image2image",
    "video.text2video",
    "video.image2video",
    "video.reference2video",
    "audio.tts",
    "audio.music",
    "video.concat",
    "video.upscale",
}
_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")
_ASSET_RE = re.compile(r"^\$assets\.([a-zA-Z0-9_.-]+)$")


class WorkflowManifestError(ValueError):
    """Raised when a workflow manifest is malformed or unsafe."""


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the stable subset of the dsh workflow contract used by SciCloud."""
    if not isinstance(manifest, dict):
        raise WorkflowManifestError("工作流清单必须是 JSON 对象")
    workflow_id = manifest.get("id")
    if not isinstance(workflow_id, str) or not _ID_RE.fullmatch(workflow_id):
        raise WorkflowManifestError("工作流 id 缺失或包含非法字符")
    if manifest.get("version") != 1:
        raise WorkflowManifestError("目前只支持 workflow manifest version=1")
    capability = manifest.get("capability")
    if not isinstance(capability, str) or not capability.strip():
        raise WorkflowManifestError("工作流缺少 capability")
    if capability not in CAPABILITIES:
        raise WorkflowManifestError(
            f"不支持的工作流 capability：{capability}；支持项：{', '.join(sorted(CAPABILITIES))}"
        )
    runner = manifest.get("runner", "comfyui")
    if runner != "comfyui":
        raise WorkflowManifestError("SciCloud 本地注册表目前只执行 ComfyUI 工作流")
    graph = manifest.get("graph")
    if not isinstance(graph, dict) or not graph:
        raise WorkflowManifestError("工作流 graph 必须是非空 ComfyUI API JSON 对象")
    for node_id, node in graph.items():
        if not isinstance(node_id, str) or not isinstance(node, dict):
            raise WorkflowManifestError("graph 节点结构无效")
        if not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs", {}), dict):
            raise WorkflowManifestError(f"graph 节点 {node_id} 缺少 class_type 或 inputs")
    params = manifest.get("params", [])
    if not isinstance(params, list):
        raise WorkflowManifestError("params 必须是数组")
    seen = set()
    for param in params:
        if not isinstance(param, dict) or not isinstance(param.get("name"), str):
            raise WorkflowManifestError("每个 params 项必须包含 name")
        name = param["name"]
        if name in seen:
            raise WorkflowManifestError(f"参数重复：{name}")
        seen.add(name)
        inject = param.get("inject", {})
        if inject.get("type") != "scalar" or not isinstance(inject.get("to"), list):
            raise WorkflowManifestError(f"参数 {name} 目前只支持 scalar 注入绑定")
        for target in inject["to"]:
            if (not isinstance(target, list) or len(target) != 2
                    or str(target[0]) not in graph or not isinstance(target[1], str)):
                raise WorkflowManifestError(f"参数 {name} 的注入目标无效")
            if target[1] not in (graph[str(target[0])].get("inputs") or {}):
                raise WorkflowManifestError(f"参数 {name} 指向不存在的输入：{target[0]}.{target[1]}")
    result = copy.deepcopy(manifest)
    result["runner"] = runner
    result["params"] = params
    return result


def _resolve_assets(value: Any, assets: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {k: _resolve_assets(v, assets) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_assets(v, assets) for v in value]
    if isinstance(value, str):
        match = _ASSET_RE.fullmatch(value)
        if match:
            key = match.group(1)
            if key not in assets:
                raise WorkflowManifestError(f"缺少工作流资产：{key}")
            return assets[key]
    return value


def compile_workflow(
    manifest: dict[str, Any],
    params: dict[str, Any] | None = None,
    assets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fresh ComfyUI API graph with manifest parameters and assets bound."""
    checked = validate_manifest(manifest)
    params = params or {}
    assets = assets or {}
    declared = {p["name"]: p for p in checked["params"]}
    unknown = set(params) - set(declared)
    if unknown:
        raise WorkflowManifestError("未声明的工作流参数：" + ", ".join(sorted(unknown)))
    graph = copy.deepcopy(checked["graph"])
    for name, value in params.items():
        for node_id, input_name in declared[name]["inject"]["to"]:
            graph[str(node_id)]["inputs"][input_name] = value
    graph = _resolve_assets(graph, assets)
    return graph


def import_api_workflow(
    api_graph: dict[str, Any],
    workflow_id: str,
    capability: str,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Wrap a ComfyUI 'Save (API Format)' graph as a manifest for user binding."""
    manifest = {
        "id": workflow_id,
        "version": 1,
        "capability": capability,
        "runner": "comfyui",
        "displayName": display_name or workflow_id,
        "output": {"mediaType": "unknown", "hasAudio": None},
        "assets": {},
        "graph": copy.deepcopy(api_graph),
        "params": [],
        "importNotes": [
            "由 ComfyUI API JSON 导入；导入后需声明 prompt、尺寸、参考图等参数注入点。",
            "模型文件及其他输入资产必须在本机 ComfyUI 中已配置。",
        ],
    }
    return validate_manifest(manifest)


class WorkflowRegistry:
    """Filesystem registry: built-ins are overridden by same-ID user manifests."""

    def __init__(self, builtin_dir: str | os.PathLike, user_dir: str | os.PathLike):
        self.builtin_dir = Path(builtin_dir)
        self.user_dir = Path(user_dir)

    @staticmethod
    def _read_dir(directory: Path) -> dict[str, dict[str, Any]]:
        items: dict[str, dict[str, Any]] = {}
        if not directory.is_dir():
            return items
        for path in sorted(directory.glob("*.json")):
            try:
                parsed = json.loads(path.read_text(encoding="utf-8"))
                checked = validate_manifest(parsed)
            except (OSError, json.JSONDecodeError, WorkflowManifestError) as exc:
                # Invalid user files are skipped from listing but not deleted.
                continue
            items[checked["id"]] = checked
        return items

    def list(self) -> list[dict[str, Any]]:
        merged = self._read_dir(self.builtin_dir)
        merged.update(self._read_dir(self.user_dir))
        return sorted(merged.values(), key=lambda item: item["id"])

    def get(self, workflow_id: str) -> dict[str, Any]:
        if not isinstance(workflow_id, str) or not _ID_RE.fullmatch(workflow_id):
            raise WorkflowManifestError("工作流 id 无效")
        user_path = self.user_dir / f"{workflow_id}.json"
        builtin_path = self.builtin_dir / f"{workflow_id}.json"
        path = user_path if user_path.is_file() else builtin_path
        if not path.is_file():
            raise WorkflowManifestError(f"未找到工作流：{workflow_id}")
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowManifestError(f"无法读取工作流 {workflow_id}：{exc}") from exc
        checked = validate_manifest(manifest)
        if checked["id"] != workflow_id:
            raise WorkflowManifestError("文件名与工作流 id 不一致")
        return checked
