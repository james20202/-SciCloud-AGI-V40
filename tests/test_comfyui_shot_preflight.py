import json

from core.adapters.comfyui_adapter import ComfyUIAdapter


def _write_manifest(folder, *, capability="video.image2video"):
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "test-video",
        "version": 1,
        "capability": capability,
        "runner": "comfyui",
        "graph": {
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "placeholder"}},
            "2": {"class_type": "KSampler", "inputs": {"steps": 20}},
        },
        "params": [
            {"name": "positive_prompt", "inject": {"type": "scalar", "to": [["1", "text"]]}},
            {"name": "steps", "inject": {"type": "scalar", "to": [["2", "steps"]]}},
        ],
    }
    (folder / "test-video.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_shot_batch_preflight_accepts_declared_prompt_mapping(tmp_path, monkeypatch):
    builtin, user = tmp_path / "builtin", tmp_path / "user"
    _write_manifest(builtin)
    monkeypatch.setattr("core.adapters.comfyui_adapter.BUILTIN_WORKFLOW_DIR", str(builtin))
    monkeypatch.setattr("core.adapters.comfyui_adapter.USER_WORKFLOW_DIR", str(user))
    result = ComfyUIAdapter().preflight_shot_batch(
        {"workflow_registry_id": "test-video", "workflow_params": {"steps": 24}},
        {"visual_prompt": "positive_prompt"},
    )
    assert result["success"] is True
    assert result["workflow_id"] == "test-video"
    assert result["shot_bindings"] == {"visual_prompt": "positive_prompt"}


def test_shot_batch_preflight_rejects_unknown_parameter_before_render(tmp_path, monkeypatch):
    builtin, user = tmp_path / "builtin", tmp_path / "user"
    _write_manifest(builtin)
    monkeypatch.setattr("core.adapters.comfyui_adapter.BUILTIN_WORKFLOW_DIR", str(builtin))
    monkeypatch.setattr("core.adapters.comfyui_adapter.USER_WORKFLOW_DIR", str(user))
    result = ComfyUIAdapter().preflight_shot_batch(
        {"workflow_registry_id": "test-video"},
        {"prompt": "not_declared"},
    )
    assert result["success"] is False
    assert "未声明参数" in result["message"]


def test_shot_batch_preflight_rejects_non_video_workflow(tmp_path, monkeypatch):
    builtin, user = tmp_path / "builtin", tmp_path / "user"
    _write_manifest(builtin, capability="image.text2image")
    monkeypatch.setattr("core.adapters.comfyui_adapter.BUILTIN_WORKFLOW_DIR", str(builtin))
    monkeypatch.setattr("core.adapters.comfyui_adapter.USER_WORKFLOW_DIR", str(user))
    result = ComfyUIAdapter().preflight_shot_batch(
        {"workflow_registry_id": "test-video"},
        {"prompt": "positive_prompt"},
    )
    assert result["success"] is False
    assert "不能使用" in result["message"]


def test_shot_batch_preflight_requires_a_prompt_binding(tmp_path, monkeypatch):
    builtin, user = tmp_path / "builtin", tmp_path / "user"
    _write_manifest(builtin)
    monkeypatch.setattr("core.adapters.comfyui_adapter.BUILTIN_WORKFLOW_DIR", str(builtin))
    monkeypatch.setattr("core.adapters.comfyui_adapter.USER_WORKFLOW_DIR", str(user))
    result = ComfyUIAdapter().preflight_shot_batch(
        {"workflow_registry_id": "test-video"},
        {"duration_seconds": "steps"},
    )
    assert result["success"] is False
    assert "prompt" in result["message"]
