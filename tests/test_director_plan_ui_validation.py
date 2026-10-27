import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
import pytest

from ui.pages.director_plan import DirectorPlanPage


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def valid_plan():
    return {
        "intent": {"duration_seconds": 10},
        "story": {},
        "characters": [{"id": "CHAR-1", "name": "主角"}],
        "scenes": [{"id": "SCENE-1", "name": "山门"}],
        "shots": [{
            "id": "SHOT-1", "scene_id": "SCENE-1",
            "character_ids": ["CHAR-1"], "visual_prompt": "夜雨中的山门",
            "duration": 10,
        }],
        "tasks": [],
    }


def test_ui_plan_validation_accepts_valid_contract(qt_app):
    page = DirectorPlanPage()
    plan = page._validate_plan(valid_plan())
    assert plan["intent"]["duration_seconds"] == 10
    page.close()


@pytest.mark.parametrize("bad_duration", [math.nan, math.inf, -math.inf, 0, -1])
def test_ui_plan_validation_rejects_nonfinite_or_nonpositive_shot_duration(qt_app, bad_duration):
    plan = valid_plan()
    plan["shots"][0]["duration"] = bad_duration
    page = DirectorPlanPage()
    with pytest.raises(ValueError):
        page._validate_plan(plan)
    page.close()


def test_ui_plan_validation_rejects_dangling_scene_reference(qt_app):
    plan = valid_plan()
    plan["shots"][0]["scene_id"] = "SCENE-MISSING"
    page = DirectorPlanPage()
    with pytest.raises(ValueError, match="场景引用"):
        page._validate_plan(plan)
    page.close()


def test_ui_plan_validation_rejects_target_duration_nan(qt_app):
    plan = valid_plan()
    plan["intent"]["duration_seconds"] = math.nan
    page = DirectorPlanPage()
    with pytest.raises(ValueError, match="目标时长"):
        page._validate_plan(plan)
    page.close()
