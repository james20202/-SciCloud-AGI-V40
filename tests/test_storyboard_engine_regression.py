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


def test_storyboard_path_rejects_traversal_ids(tmp_path):
    import pytest

    director = StoryboardDirector(directory=str(tmp_path))
    for storyboard_id in ("../outside", "nested/storyboard", r"nested\storyboard", ""):
        with pytest.raises(ValueError):
            director._path(storyboard_id)


def test_storyboard_load_handles_unsafe_id_without_reading_outside_directory(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))

    assert director.load("../outside") is None



def test_create_from_plan_rejects_invalid_shot_schema_and_duration(tmp_path):
    import pytest

    director = StoryboardDirector(directory=str(tmp_path))
    with pytest.raises(ValueError, match="必须是对象"):
        director.create_from_plan({"shots": ["not-a-shot"]})
    with pytest.raises(ValueError, match="时长必须是数字"):
        director.create_from_plan({"shots": [{"id": "S1", "duration": "long"}]})
    with pytest.raises(ValueError, match="时长必须大于 0"):
        director.create_from_plan({"shots": [{"id": "S1", "duration": 0}]})
    with pytest.raises(ValueError, match="不超过 3600"):
        director.create_from_plan({"shots": [{"id": "S1", "duration": 3601}]})


def test_create_from_plan_rejects_duplicate_shot_ids(tmp_path):
    import pytest

    director = StoryboardDirector(directory=str(tmp_path))
    with pytest.raises(ValueError, match="镜头 ID 重复"):
        director.create_from_plan({"shots": [{"id": "S1"}, {"id": "S1"}]})


def test_storyboard_save_is_atomic_and_replaces_valid_json(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    storyboard = director.create_from_plan({
        "plan_id": "PLAN-ATOMIC",
        "shots": [{"id": "SHOT-1", "duration": 3}],
    })
    path = tmp_path / (storyboard["storyboard_id"] + ".json")
    storyboard["title"] = "更新后标题"
    director.save(storyboard)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["title"] == "更新后标题"
    assert not list(tmp_path.glob(".storyboard-*.tmp"))


def test_build_prompt_resolves_source_plan_when_ui_omits_plan(tmp_path, monkeypatch):
    import core.storyboard_engine as module

    director = StoryboardDirector(directory=str(tmp_path))
    plan = {
        "plan_id": "PLAN-AUTO-LINK",
        "idea": "仙门夜雨",
        "intent": {"genre": "修仙"},
        "characters": [{"id": "CHAR-1", "name": "沈砚", "description": "白发剑修"}],
        "scenes": [{"id": "SCENE-1", "name": "废弃仙门", "purpose": "发现异象"}],
        "shots": [{
            "id": "SHOT-1", "scene_id": "SCENE-1", "character_ids": ["CHAR-1"],
            "duration": 5, "visual_prompt": "雨夜石阶上，剑刃泛起青光",
        }],
    }
    storyboard = director.create_from_plan(plan)
    captured = {}
    monkeypatch.setattr(module, "prompt_engine", type("PromptStub", (), {
        "generate_for_shot": staticmethod(lambda shot, received_plan, model: (
            captured.update(plan=received_plan, shot=shot) or {
                "prompt_id": "PROMPT-1", "prompt": "雨夜石阶"
            }
        ))
    })())
    monkeypatch.setattr(module, "continuity_engine", type("ContinuityStub", (), {
        "build_prompt_constraints": staticmethod(lambda *_: [])
    })())
    monkeypatch.setattr(module, "director_plan_engine", type("PlanStub", (), {
        "load_plans": staticmethod(lambda: [plan])
    })())

    record = director.build_prompt(storyboard["storyboard_id"], 0)
    assert captured["plan"]["plan_id"] == "PLAN-AUTO-LINK"
    assert captured["plan"]["characters"][0]["name"] == "沈砚"
    assert record["prompt_id"] == "PROMPT-1"


def test_build_prompt_rejects_out_of_range_shot_index(tmp_path):
    import pytest

    director = StoryboardDirector(directory=str(tmp_path))
    storyboard = director.create_from_plan({"plan_id": "PLAN-INDEX", "shots": [{"id": "SHOT-1"}]})
    with pytest.raises(ValueError, match="镜头索引越界"):
        director.build_prompt(storyboard["storyboard_id"], 1)
    with pytest.raises(ValueError, match="镜头索引越界"):
        director.build_prompt(storyboard["storyboard_id"], -1)
