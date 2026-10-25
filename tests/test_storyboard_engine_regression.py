import json

from core.storyboard_engine import StoryboardDirector


def test_create_from_plan_preserves_explicit_scene_character_prompt_and_dialogue(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    plan = {
        "plan_id": "PLAN-REGRESSION",
        "title": "Storyboard mapping regression",
        "characters": [{"id": "CHAR-DEFAULT", "name": "Fallback character"}],
        # Intentionally no scenes array: explicit scene_id must still survive.
        "shots": [
            {
                "id": "SHOT-0001",
                "scene_id": "SCENE-EXPLICIT",
                "character_ids": ["CHAR-2", "CHAR-3"],
                "duration": 7,
                "visual_prompt": "A cultivator raises a glowing sword in the rain",
                "dialogue": "此剑出鞘，必见分晓。",
            }
        ],
    }

    storyboard = director.create_from_plan(plan)
    shot = storyboard["shots"][0]

    assert shot["scene_id"] == "SCENE-EXPLICIT"
    assert shot["character_ids"] == ["CHAR-2", "CHAR-3"]
    assert shot["visual_prompt"] == "A cultivator raises a glowing sword in the rain"
    assert shot["prompt"] == shot["visual_prompt"]
    assert shot["dialogue"] == "此剑出鞘，必见分晓。"
    assert shot["duration"] == 7

    saved = json.loads((tmp_path / (storyboard["storyboard_id"] + ".json")).read_text(encoding="utf-8"))
    assert saved["shots"][0]["character_ids"] == ["CHAR-2", "CHAR-3"]


def test_create_from_plan_uses_scene_fallback_when_explicit_scene_is_missing(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    plan = {
        "plan_id": "PLAN-FALLBACK",
        "scenes": [{"id": "SCENE-1"}, {"id": "SCENE-2"}],
        "shots": [{"id": "SHOT-1"}, {"id": "SHOT-2"}, {"id": "SHOT-3"}, {"id": "SHOT-4"}],
    }

    storyboard = director.create_from_plan(plan)

    assert [shot["scene_id"] for shot in storyboard["shots"]] == [
        "SCENE-1", "SCENE-1", "SCENE-1", "SCENE-2"
    ]
