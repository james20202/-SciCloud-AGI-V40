from core.prompt_engine import PromptEngine


def test_generate_for_shot_preserves_visual_action_dialogue_and_voiceover(tmp_path):
    engine = PromptEngine(prompt_dir=str(tmp_path / "templates"))
    plan = {
        "idea": "废弃仙门中，失忆剑修发现自己的剑在滴血",
        "intent": {"genre": "修仙"},
        "characters": [
            {"id": "CHAR-1", "name": "沈砚", "description": "白发剑修", "costume": "破损白袍"}
        ],
        "scenes": [
            {"id": "SCENE-1", "name": "废弃仙门", "purpose": "揭示异常"}
        ],
    }
    shot = {
        "shot_id": "SHOT-1",
        "scene_id": "SCENE-1",
        "character_ids": ["CHAR-1"],
        "duration": 5,
        "visual_prompt": "雨夜石阶上，沈砚握着滴血长剑，远处山门亮起青色符火",
        "action": "沈砚低头看向剑刃，符火突然熄灭",
        "expression": "压抑震惊",
        "dialogue": "这把剑……为何认得我？",
        "voiceover": "三百年前，仙门一夜覆灭",
        "director_note": "剑刃血迹需与下一镜头保持一致",
    }

    result = engine.generate_for_shot(shot, plan)

    assert "雨夜石阶上" in result["prompt"]
    assert "符火突然熄灭" in result["prompt"]
    assert "白发剑修" in result["prompt"]
    assert result["dialogue"] == "这把剑……为何认得我？"
    assert result["voiceover"] == "三百年前，仙门一夜覆灭"
    assert result["director_note"] == "剑刃血迹需与下一镜头保持一致"
    assert result["shot_context"]["duration_seconds"] == 5
    assert result["source_shot_id"] == "SHOT-1"


def test_generate_for_shot_accepts_legacy_prompt_and_narration_fields(tmp_path):
    engine = PromptEngine(prompt_dir=str(tmp_path / "templates"))
    result = engine.generate_for_shot({
        "id": "SHOT-OLD",
        "prompt": "山门石兽在雷光中睁眼",
        "narration": "雷声撕裂长夜",
    }, {"intent": {"genre": "玄幻"}})

    assert "山门石兽在雷光中睁眼" in result["prompt"]
    assert result["voiceover"] == "雷声撕裂长夜"
    assert result["source_shot_id"] == "SHOT-OLD"
