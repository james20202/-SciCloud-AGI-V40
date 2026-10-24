import copy
import json
from core.local_ollama_director import LocalOllamaDirector


def sample_plan():
    return {
        "idea": "玄幻修仙，废柴弟子觉醒",
        "intent": {"genre": "玄幻", "duration_seconds": 10, "hook": "原始钩子"},
        "story": {"logline": "原始梗概"},
        "characters": [{"id": "CHAR-1", "name": "主角", "description": "原始人物"}],
        "scenes": [{"id": "SCENE-1", "name": "山门", "purpose": "原始场景"}],
        "shots": [
            {"id": "SHOT-0001", "index": 1, "duration": 5, "type": "Hook特写", "visual_prompt": "原始画面", "action": "原始动作", "dialogue": ""},
            {"id": "SHOT-0002", "index": 2, "duration": 5, "type": "悬念收尾", "visual_prompt": "原始画面2", "action": "原始动作2", "dialogue": ""},
        ],
    }


def test_local_ollama_enriches_text_without_changing_ids_or_timing(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: "qwen2.5:3b")
    response = {
        "logline": "一名废柴弟子在天劫中觉醒",
        "hook": "天雷落下，废柴睁开双眼",
        "characters": [{"id": "CHAR-1", "description": "隐忍而敏锐的年轻修士"}],
        "scenes": [{"id": "SCENE-1", "purpose": "建立宗门威压和天劫异象"}],
        "shot_items": [
            {"id": "SHOT-0001", "visual_prompt": "乌云压顶，年轻修士仰望翻涌天雷，低机位电影构图", "action": "缓慢抬头", "dialogue": "天劫？", "director_note": "先压低环境声"},
            {"id": "SHOT-0002", "visual_prompt": "紫色雷光照亮修士双眼，近景，强烈轮廓光", "action": "抬手接雷", "dialogue": "来吧。", "director_note": "以雷光做转场"},
        ],
    }
    monkeypatch.setattr(engine, "_request_json", lambda url, payload=None, timeout=3: {"response": json.dumps(response, ensure_ascii=False)})
    plan = sample_plan()
    status = engine.enrich_plan(plan)
    assert status["mode"] == "local_ollama"
    assert plan["story"]["logline"] == response["logline"]
    assert [x["id"] for x in plan["shots"]] == ["SHOT-0001", "SHOT-0002"]
    assert [x["duration"] for x in plan["shots"]] == [5, 5]
    assert plan["shots"][0]["visual_prompt"] == response["shot_items"][0]["visual_prompt"]
    assert plan["shots"][1]["dialogue"] == "来吧。"


def test_invalid_ollama_response_falls_back_without_partial_mutation(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: "qwen2.5:3b")
    malformed = {"logline": "不应被写入", "hook": "不应被写入", "shot_items": [{"id": "WRONG-ID"}]}
    monkeypatch.setattr(engine, "_request_json", lambda url, payload=None, timeout=3: {"response": json.dumps(malformed)})
    plan = sample_plan()
    before = copy.deepcopy(plan)
    status = engine.enrich_plan(plan)
    assert status["mode"] == "deterministic_fallback"
    assert plan == before


def test_missing_ollama_model_returns_clear_fallback(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: None)
    plan = sample_plan()
    status = engine.enrich_plan(plan)
    assert status["mode"] == "deterministic_fallback"
    assert "未运行" in status["message"]
