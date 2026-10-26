import json

import pytest

from core.comfyui_workflow_registry import (
    WorkflowManifestError,
    WorkflowRegistry,
    compile_workflow,
    import_api_workflow,
    validate_manifest,
)


def manifest():
    return {
        "id": "local-video",
        "version": 1,
        "capability": "video.reference2video",
        "runner": "comfyui",
        "displayName": "Local video",
        "output": {"mediaType": "video", "hasAudio": True},
        "assets": {"checkpoint": {"kind": "checkpoint"}},
        "graph": {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "$assets.checkpoint"}},
            "2": {"class_type": "KSampler", "inputs": {"steps": 20, "cfg": 7}},
        },
        "params": [
            {"name": "steps", "inject": {"type": "scalar", "to": [["2", "steps"]]}},
            {"name": "guidance", "inject": {"type": "scalar", "to": [["2", "cfg"]]}},
        ],
    }


def test_compile_workflow_injects_parameters_and_assets_without_mutating_manifest():
    source = manifest()
    graph = compile_workflow(
        source,
        params={"steps": 28, "guidance": 5.5},
        assets={"checkpoint": "local-model.safetensors"},
    )
    assert graph["1"]["inputs"]["ckpt_name"] == "local-model.safetensors"
    assert graph["2"]["inputs"] == {"steps": 28, "cfg": 5.5}
    assert source["graph"]["2"]["inputs"]["steps"] == 20


def test_compile_workflow_rejects_undeclared_parameters_and_missing_assets():
    with pytest.raises(WorkflowManifestError, match="未声明"):
        compile_workflow(manifest(), params={"unknown": 1})
    with pytest.raises(WorkflowManifestError, match="缺少工作流资产"):
        compile_workflow(manifest(), assets={})


def test_manifest_rejects_injection_target_that_does_not_exist():
    broken = manifest()
    broken["params"][0]["inject"]["to"] = [["404", "steps"]]
    with pytest.raises(WorkflowManifestError, match="注入目标无效"):
        validate_manifest(broken)


def test_import_api_workflow_preserves_graph_and_requires_manual_binding():
    graph = {"5": {"class_type": "CLIPTextEncode", "inputs": {"text": "hello"}}}
    imported = import_api_workflow(graph, "imported-flow", "image.text2image")
    assert imported["graph"] == graph
    assert imported["params"] == []
    assert imported["importNotes"]
    graph["5"]["inputs"]["text"] = "changed"
    assert imported["graph"]["5"]["inputs"]["text"] == "hello"


def test_registry_user_manifest_overrides_builtin_and_invalid_files_are_not_deleted(tmp_path):
    builtins = tmp_path / "builtins"
    user = tmp_path / "user"
    builtins.mkdir()
    user.mkdir()
    (builtins / "local-video.json").write_text(json.dumps(manifest()), encoding="utf-8")
    replacement = manifest()
    replacement["displayName"] = "User override"
    (user / "local-video.json").write_text(json.dumps(replacement), encoding="utf-8")
    invalid_path = user / "bad.json"
    invalid_path.write_text("{ broken", encoding="utf-8")

    registry = WorkflowRegistry(builtins, user)
    assert registry.get("local-video")["displayName"] == "User override"
    assert [item["id"] for item in registry.list()] == ["local-video"]
    assert invalid_path.exists()


def test_registry_rejects_path_like_workflow_ids(tmp_path):
    registry = WorkflowRegistry(tmp_path / "builtins", tmp_path / "user")
    with pytest.raises(WorkflowManifestError, match="id 无效"):
        registry.get("../secret")


def test_manifest_rejects_unsupported_capability():
    broken = manifest()
    broken["capability"] = "video.magic_remote_runner"
    with pytest.raises(WorkflowManifestError, match="不支持的工作流 capability"):
        validate_manifest(broken)

def test_comfyui_adapter_resolves_registry_id_and_binds_task_params(tmp_path, monkeypatch):
    import core.adapters.comfyui_adapter as adapter_module
    from core.adapters.comfyui_adapter import ComfyUIAdapter

    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()
    source = manifest()
    (user_dir / "local-video.json").write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(adapter_module, "BUILTIN_WORKFLOW_DIR", str(builtin_dir))
    monkeypatch.setattr(adapter_module, "USER_WORKFLOW_DIR", str(user_dir))

    graph, error = ComfyUIAdapter()._workflow({
        "workflow_registry_id": "local-video",
        "workflow_params": {"steps": 28, "guidance": 5.5},
        "workflow_assets": {"checkpoint": "local-model.safetensors"},
    }, {})

    assert error is None
    assert graph["1"]["inputs"]["ckpt_name"] == "local-model.safetensors"
    assert graph["2"]["inputs"] == {"steps": 28, "cfg": 5.5}


def test_comfyui_adapter_reports_missing_registry_workflow(tmp_path, monkeypatch):
    import core.adapters.comfyui_adapter as adapter_module
    from core.adapters.comfyui_adapter import ComfyUIAdapter

    monkeypatch.setattr(adapter_module, "BUILTIN_WORKFLOW_DIR", str(tmp_path / "builtin"))
    monkeypatch.setattr(adapter_module, "USER_WORKFLOW_DIR", str(tmp_path / "user"))
    graph, error = ComfyUIAdapter()._workflow({"workflow_registry_id": "missing-flow"}, {})

    assert graph is None
    assert "未能加载已登记的 ComfyUI 工作流" in error

