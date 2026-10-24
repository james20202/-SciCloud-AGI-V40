import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
import pytest
from core.director_plan import DirectorPlanEngine
from core.storyboard_engine import StoryboardDirector
from ui.pages.director_plan import DirectorPlanPage

_APP = QApplication.instance() or QApplication([])


@pytest.mark.parametrize("duration", [10, 30, 59, 60, 73, 120, 600])
def test_director_plan_shot_durations_sum_to_target(tmp_path, duration):
    engine = DirectorPlanEngine(project_dir=str(tmp_path))
    plan = engine.create_plan("玄幻修仙主角觉醒", duration=duration)
    assert round(sum(float(s["duration"]) for s in plan["shots"]), 1) == duration
    assert all(s.get("visual_prompt") for s in plan["shots"])


def test_storyboard_conversion_preserves_visual_prompt_dialogue_and_duration(tmp_path):
    director = StoryboardDirector(directory=str(tmp_path))
    plan = {
        "plan_id": "PLAN-TEST", "title": "测试计划",
        "characters": [{"id": "CHAR-1", "name": "主角"}],
        "scenes": [{"id": "SCENE-1", "name": "山门"}],
        "shots": [{
            "id": "SHOT-0001", "duration": 7.5, "scene_id": "SCENE-1",
            "visual_prompt": "月光下的仙门，雾气翻涌",
            "dialogue": "此地不对劲。", "action": "缓慢推门"
        }]
    }
    storyboard = director.create_from_plan(plan)
    shot = storyboard["shots"][0]
    assert shot["id"] == "SHOT-0001"
    assert shot["duration"] == 7.5
    assert shot["visual_prompt"] == "月光下的仙门，雾气翻涌"
    assert shot["prompt"] == "月光下的仙门，雾气翻涌"
    assert shot["dialogue"] == "此地不对劲。"
    assert shot["action"] == "缓慢推门"


def test_director_page_rejects_malformed_shot_duration():
    page = DirectorPlanPage()
    bad = {"intent": {"duration_seconds": 60}, "story": {},
           "characters": [], "scenes": [], "shots": [{"duration": 5}], "tasks": []}
    with pytest.raises(ValueError, match="总时长"):
        page._validate_plan(bad)
    page.close()
