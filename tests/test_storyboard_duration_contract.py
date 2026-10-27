import pytest

from core.storyboard_engine import StoryboardDirector


def test_storyboard_rejects_empty_shot_list(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    with pytest.raises(ValueError, match="没有镜头"):
        director.create_from_plan({"plan_id": "PLAN-EMPTY", "shots": []})
    assert list(tmp_path.glob("*.json")) == []


def test_storyboard_rejects_plan_duration_mismatch_before_saving(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    plan = {
        "plan_id": "PLAN-DURATION-MISMATCH",
        "intent": {"duration_seconds": 60},
        "scenes": [{"id": "SCENE-1", "name": "山门"}],
        "characters": [{"id": "CHAR-1", "name": "主角"}],
        "shots": [{"id": f"SHOT-{i}", "scene_id": "SCENE-1", "character_ids": ["CHAR-1"], "visual_prompt": f"画面{i}", "duration": 5} for i in range(1, 7)],
    }
    with pytest.raises(ValueError, match="总时长"):
        director.create_from_plan(plan)
    assert list(tmp_path.glob("*.json")) == []


def test_storyboard_accepts_plan_with_matching_duration(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    plan = {
        "plan_id": "PLAN-DURATION-OK",
        "intent": {"duration_seconds": 60},
        "scenes": [{"id": "SCENE-1", "name": "山门"}],
        "characters": [{"id": "CHAR-1", "name": "主角"}],
        "shots": [{"id": f"SHOT-{i}", "scene_id": "SCENE-1", "character_ids": ["CHAR-1"], "visual_prompt": f"画面{i}", "duration": 10} for i in range(1, 7)],
    }
    storyboard = director.create_from_plan(plan)
    assert sum(shot["duration"] for shot in storyboard["shots"]) == 60
