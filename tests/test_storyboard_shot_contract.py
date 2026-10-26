import pytest

from core.storyboard_engine import StoryboardDirector


def test_create_from_plan_emits_canonical_shot_fields(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    result = director.create_from_plan({
        "plan_id": "PLAN-TEST",
        "title": "青云夜雨",
        "scenes": [{"id": "SCENE-1"}],
        "characters": [{"id": "CHAR-1"}],
        "shots": [{
            "id": "SHOT-1", "duration": 4,
            "prompt": "雨夜山门，青衣剑客持剑",
            "dialogue": "来者何人？",
            "narration": "山门之外风雨大作",
            "character_ids": [{"id": "CHAR-1"}],
        }],
    })
    shot = result["shots"][0]
    assert shot["shot_id"] == "SHOT-1"
    assert shot["visual_prompt"] == shot["prompt"] == "雨夜山门，青衣剑客持剑"
    assert shot["dialogue"] == "来者何人？"
    assert shot["voiceover"] == "山门之外风雨大作"
    assert shot["character_ids"] == ["CHAR-1"]
    assert shot["duration"] == 4


def test_save_normalizes_legacy_shots_without_dropping_extra_fields(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    result = director.save({
        "storyboard_id": "STORYBOARD-LEGACY",
        "shots": [{
            "id": "SHOT-1", "duration": 5, "prompt": "旧提示词",
            "dialogue": "旧对白", "custom_extension": {"keep": True},
        }],
    })
    shot = result["shots"][0]
    assert shot["shot_id"] == "SHOT-1"
    assert shot["visual_prompt"] == "旧提示词"
    assert shot["custom_extension"] == {"keep": True}


def test_save_rejects_duplicate_shot_ids(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    with pytest.raises(ValueError, match="重复"):
        director.save({
            "storyboard_id": "STORYBOARD-DUPLICATE",
            "shots": [{"id": "S1"}, {"shot_id": "S1"}],
        })
