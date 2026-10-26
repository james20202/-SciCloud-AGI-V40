"""E5 Ollama diagnosis + Q4 plan/storyboard validation.

Only the dependency-free validator and the stdlib-only Ollama director
are imported here, so these tests do not need PySide6, ComfyUI, or a
running Ollama server; Ollama HTTP calls are monkeypatched.
"""

import json
import urllib.error

import pytest

from core.local_ollama_director import LocalOllamaDirector
from core.plan_validation import (
    validate_plan,
    validate_plan_or_raise,
    validate_storyboard,
    validate_storyboard_or_raise,
)


def base_plan():
    return {
        "plan_id": "PLAN-TEST",
        "title": "测试",
        "idea": "白衣修仙者山间竹林御剑飞行",
        "intent": {"genre": "修仙", "duration_seconds": 10, "aspect_ratio": "9:16"},
        "story": {"logline": "测试故事"},
        "characters": [
            {"id": "CHAR-00001", "name": "主角", "description": "白衣修仙者"},
        ],
        "scenes": [
            {"id": "SCENE-00001", "name": "山间竹林", "purpose": "建立空间"},
        ],
        "shots": [
            {"id": "SHOT-0001", "index": 1, "duration": 5, "scene_id": "SCENE-00001",
             "character_ids": ["CHAR-00001"], "visual_prompt": "白衣修仙者竹林御剑"},
            {"id": "SHOT-0002", "index": 2, "duration": 5, "scene_id": "SCENE-00001",
             "character_ids": ["CHAR-00001"], "visual_prompt": "白衣修仙者落剑回眸"},
        ],
    }


# ---- Q4: plan validation ----

def test_valid_plan_passes():
    assert validate_plan(base_plan()) == []
    assert validate_plan_or_raise(base_plan()) is True


def test_unknown_scene_ref_fails():
    plan = base_plan()
    plan["shots"][0]["scene_id"] = "SCENE-99999"
    errors = validate_plan(plan)
    assert any("SCENE-99999" in e for e in errors)


def test_unknown_character_ref_fails():
    plan = base_plan()
    plan["shots"][1]["character_ids"] = ["CHAR-99999"]
    errors = validate_plan(plan)
    assert any("CHAR-99999" in e for e in errors)


def test_shot_without_characters_and_no_plan_characters_fails():
    plan = base_plan()
    plan["characters"] = []
    plan["shots"][0].pop("character_ids")
    errors = validate_plan(plan)
    assert errors


def test_shot_without_character_ids_falls_back_to_first_character():
    plan = base_plan()
    plan["shots"][0].pop("character_ids")
    assert validate_plan(plan) == []


def test_empty_prompt_fails():
    plan = base_plan()
    plan["shots"][0]["visual_prompt"] = "   "
    plan["shots"][0].pop("prompt", None)
    errors = validate_plan(plan)
    assert any("提示词" in e for e in errors)


def test_duration_sum_mismatch_fails():
    plan = base_plan()
    plan["shots"][0]["duration"] = 4
    errors = validate_plan(plan)
    assert any("总时长" in e for e in errors)


def test_duplicate_shot_id_fails():
    plan = base_plan()
    plan["shots"][1]["id"] = "SHOT-0001"
    assert any("重复" in e for e in validate_plan(plan))


def test_storyboard_validation_uses_plan_refs():
    plan = base_plan()
    storyboard = {"storyboard_id": "STORYBOARD-TEST", "shots": [
        dict(plan["shots"][0], prompt="白衣修仙者竹林御剑"),
        dict(plan["shots"][1], prompt="白衣修仙者落剑回眸"),
    ]}
    assert validate_storyboard(storyboard, plan) == []
    assert validate_storyboard_or_raise(storyboard, plan) is True
    storyboard["shots"][1]["character_ids"] = ["CHAR-99999"]
    assert validate_storyboard(storyboard, plan)


# ---- E5: Ollama diagnosis ----

def _tags_with(model_name):
    return {"models": [{"name": model_name}]} if model_name else {"models": []}


def test_diagnose_ollama_not_running(monkeypatch):
    director = LocalOllamaDirector()

    def fake_request(self, url, payload=None, timeout=3):
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr(LocalOllamaDirector, "_request_json", fake_request)
    result = director.diagnose()
    assert result["status"] == "ollama_not_running"
    fallback = director.enrich_plan(base_plan())
    assert fallback["mode"] == "deterministic_fallback"
    assert fallback["diagnosis"] == "ollama_not_running"


def test_diagnose_model_not_loaded(monkeypatch):
    director = LocalOllamaDirector()

    def fake_request(self, url, payload=None, timeout=3):
        return _tags_with(None)

    monkeypatch.setattr(LocalOllamaDirector, "_request_json", fake_request)
    result = director.diagnose()
    assert result["status"] == "model_not_loaded"
    fallback = director.enrich_plan(base_plan())
    assert fallback["diagnosis"] == "model_not_loaded"


def test_diagnose_ok(monkeypatch):
    director = LocalOllamaDirector()

    def fake_request(self, url, payload=None, timeout=3):
        return _tags_with("qwen2.5:3b")

    monkeypatch.setattr(LocalOllamaDirector, "_request_json", fake_request)
    result = director.diagnose()
    assert result["status"] == "ok"
    assert result["model"] == "qwen2.5:3b"


def _valid_generate_response(plan):
    return {
        "logline": "优化后故事",
        "hook": "优化后钩子",
        "characters": [{"id": "CHAR-00001", "description": "白衣修仙者，优化描述"}],
        "scenes": [{"id": "SCENE-00001", "purpose": "优化场景目的"}],
        "shot_items": [
            {"id": "SHOT-0001", "visual_prompt": "优化镜头1", "action": "御剑",
             "dialogue": "", "director_note": "注意1"},
            {"id": "SHOT-0002", "visual_prompt": "优化镜头2", "action": "回眸",
             "dialogue": "", "director_note": "注意2"},
        ],
    }


def test_enrich_retries_invalid_json_once_then_succeeds(monkeypatch):
    director = LocalOllamaDirector()
    calls = {"generate": 0}

    def fake_request(self, url, payload=None, timeout=3):
        if "/api/tags" in url:
            return _tags_with("qwen2.5:3b")
        calls["generate"] += 1
        if calls["generate"] == 1:
            return {"response": "这不是 JSON"}
        return {"response": json.dumps(_valid_generate_response(base_plan()), ensure_ascii=False)}

    monkeypatch.setattr(LocalOllamaDirector, "_request_json", fake_request)
    plan = base_plan()
    result = director.enrich_plan(plan)
    assert result["mode"] == "local_ollama"
    assert result["diagnosis"] == "ok"
    assert calls["generate"] == 2
    assert plan["shots"][0]["visual_prompt"] == "优化镜头1"


def test_enrich_invalid_schema_twice_falls_back_with_diagnosis(monkeypatch):
    director = LocalOllamaDirector()

    def fake_request(self, url, payload=None, timeout=3):
        if "/api/tags" in url:
            return _tags_with("qwen2.5:3b")
        bad = _valid_generate_response(base_plan())
        bad["shot_items"] = bad["shot_items"][:1]
        return {"response": json.dumps(bad, ensure_ascii=False)}

    monkeypatch.setattr(LocalOllamaDirector, "_request_json", fake_request)
    result = director.enrich_plan(base_plan())
    assert result["mode"] == "deterministic_fallback"
    assert result["diagnosis"] == "invalid_schema"
    assert "fallback_reason" in result
