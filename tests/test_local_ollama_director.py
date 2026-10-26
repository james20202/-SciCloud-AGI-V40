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


def test_invalid_ollama_response_uses_complete_deterministic_fallback(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: "qwen2.5:3b")
    malformed = {"logline": "不应被写入", "hook": "不应被写入", "shot_items": [{"id": "WRONG-ID"}]}
    monkeypatch.setattr(engine, "_request_json", lambda url, payload=None, timeout=3: {"response": json.dumps(malformed)})
    plan = sample_plan()
    status = engine.enrich_plan(plan)
    assert status["mode"] == "deterministic_fallback"
    assert plan["story"]["logline"] == "原始梗概"
    assert all("不应被写入" not in shot.get("visual_prompt", "") for shot in plan["shots"])
    assert all(shot.get("director_note") for shot in plan["shots"])
    assert all("原始动作" not in shot.get("action", "") for shot in plan["shots"])
    assert status["shot_count"] == 2


def test_missing_ollama_model_returns_clear_fallback(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: None)
    plan = sample_plan()
    status = engine.enrich_plan(plan)
    assert status["mode"] == "deterministic_fallback"
    assert "未运行" in status["message"]


def test_local_ollama_enriches_shots_beyond_first_batch(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: "qwen2.5:3b")
    plan = sample_plan()
    plan["shots"] = [
        {"id": f"SHOT-{index:04d}", "index": index, "duration": 1, "type": "镜头",
         "visual_prompt": f"原始画面{index}", "action": "原始动作", "dialogue": ""}
        for index in range(1, 27)
    ]
    calls = []

    def respond(url, payload=None, timeout=3):
        request_data = json.loads(payload["prompt"].split("INPUT=", 1)[1])
        calls.append(request_data)
        return {"response": json.dumps({
            "logline": "批次化优化后的梗概",
            "hook": "优化后的钩子",
            "characters": [],
            "scenes": [],
            "shot_items": [
                {"id": shot["id"], "visual_prompt": f"具体画面：{shot['id']}",
                 "action": f"具体动作：{shot['id']}", "dialogue": f"对白：{shot['id']}",
                 "director_note": "保持连续性"}
                for shot in request_data["shots"]
            ],
        }, ensure_ascii=False)}

    monkeypatch.setattr(engine, "_request_json", respond)
    result = engine.enrich_plan(plan)

    assert result["mode"] == "local_ollama"
    assert result["shot_count"] == 26
    assert result["batch_count"] == 2
    assert [len(call["shots"]) for call in calls] == [24, 2]
    assert plan["shots"][23]["visual_prompt"] == "具体画面：SHOT-0024"
    assert plan["shots"][24]["visual_prompt"] == "具体画面：SHOT-0025"
    assert plan["shots"][25]["dialogue"] == "对白：SHOT-0026"
    assert [shot["duration"] for shot in plan["shots"]] == [1] * 26


def test_local_ollama_later_batch_failure_does_not_partially_mutate_plan(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: "qwen2.5:3b")
    plan = sample_plan()
    plan["shots"] = [
        {"id": f"SHOT-{index:04d}", "index": index, "duration": 1, "visual_prompt": f"原始{index}"}
        for index in range(1, 26)
    ]
    before = copy.deepcopy(plan)
    calls = 0

    def respond(url, payload=None, timeout=3):
        nonlocal calls
        calls += 1
        request_data = json.loads(payload["prompt"].split("INPUT=", 1)[1])
        items = [
            {"id": shot["id"], "visual_prompt": f"不应写入{shot['id']}", "action": "动作"}
            for shot in request_data["shots"]
        ]
        if calls == 2:
            items[0]["id"] = "WRONG-ID"
        return {"response": json.dumps({
            "logline": "不应写入", "hook": "不应写入",
            "characters": [], "scenes": [], "shot_items": items,
        }, ensure_ascii=False)}

    monkeypatch.setattr(engine, "_request_json", respond)
    result = engine.enrich_plan(plan)

    assert result["mode"] == "deterministic_fallback"
    assert calls == 2
    assert plan == before


def test_missing_ollama_replaces_generic_plan_prompts_with_shot_specific_visuals(monkeypatch):
    engine = LocalOllamaDirector()
    monkeypatch.setattr(engine, "_installed_model", lambda: None)
    plan = sample_plan()
    plan["intent"]["aspect_ratio"] = "9:16"
    plan["shots"] = [
        {"id": "SHOT-1", "index": 1, "duration": 5, "type": "Hook特写",
         "scene_id": "SCENE-1", "visual_prompt": "玄幻修仙；镜头1，电影级构图，9:16画幅，画面连续且人物一致",
         "action": "推动剧情并强化镜头信息"},
        {"id": "SHOT-2", "index": 2, "duration": 5, "type": "悬念收尾",
         "scene_id": "SCENE-1", "visual_prompt": "玄幻修仙；镜头2，电影级构图，9:16画幅，画面连续且人物一致",
         "action": "推动剧情并强化镜头信息"},
    ]

    result = engine.enrich_plan(plan)

    first, last = plan["shots"]
    assert result["mode"] == "deterministic_fallback"
    assert result["shot_count"] == 2
    assert first["visual_prompt"] != last["visual_prompt"]
    assert "人物：主角，原始人物" in first["visual_prompt"]
    assert "场景：山门" in first["visual_prompt"]
    assert "9:16画幅" in first["visual_prompt"]
    assert "悬念收尾" in last["visual_prompt"]
    assert first["director_note"]
    assert [shot["duration"] for shot in plan["shots"]] == [5, 5]
