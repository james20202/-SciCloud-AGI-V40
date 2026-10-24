import os
import tempfile

from core.director_plan import DirectorPlanEngine
from core.storyboard_engine import StoryboardDirector
from core.workflow_engine import WorkflowEngine


def test_plan_duration_sums_exactly():
    engine = DirectorPlanEngine(project_dir=tempfile.mkdtemp())
    for duration in (10, 30, 60, 61, 90, 600):
        plan = engine.create_plan("玄幻修仙主角逆袭", duration=duration)
        assert abs(sum(s["duration"] for s in plan["shots"]) - duration) <= 0.05
        assert len(plan["shots"]) >= 4
        assert all(s.get("visual_prompt") for s in plan["shots"])


def test_storyboard_preserves_prompt_and_dialogue():
    with tempfile.TemporaryDirectory() as d:
        director = StoryboardDirector(directory=d)
        plan = {
            "plan_id": "PLAN-TEST0001", "title": "测试分镜",
            "characters": [{"id": "CHAR-1", "name": "主角"}],
            "scenes": [{"id": "SCENE-1", "name": "山门"}],
            "shots": [{
                "id": "SHOT-0001", "duration": 6, "scene_id": "SCENE-1",
                "visual_prompt": "青云山门雷云翻涌", "dialogue": "此劫，我来破！",
                "action": "主角拔剑"
            }]
        }
        sb = director.create_from_plan(plan)
        shot = sb["shots"][0]
        assert shot["visual_prompt"] == "青云山门雷云翻涌"
        assert shot["prompt"] == "青云山门雷云翻涌"
        assert shot["dialogue"] == "此劫，我来破！"
        assert shot["action"] == "主角拔剑"


def test_workflow_persists_storyboard_link_and_retry_dependencies():
    with tempfile.TemporaryDirectory() as d:
        director = StoryboardDirector(directory=os.path.join(d, "storyboards"))
        import core.workflow_engine as module
        original = module.storyboard_director
        module.storyboard_director = director
        try:
            engine = WorkflowEngine(project_dir=d)
            plan = {
                "plan_id": "PLAN-TEST0002", "title": "工作流测试",
                "characters": [{"id": "CHAR-1"}], "scenes": [{"id": "SCENE-1"}],
                "shots": [{"id": "SHOT-0001", "duration": 6, "visual_prompt": "镜头提示"}],
                "tasks": [
                    {"id": "TASK-01", "type": "story", "name": "剧本"},
                    {"id": "TASK-02", "type": "character", "name": "人物"},
                    {"id": "TASK-03", "type": "scene", "name": "场景"},
                    {"id": "TASK-04", "type": "storyboard", "name": "分镜"}
                ]
            }
            wf = engine.create_from_plan(plan)
            assert wf["storyboard_id"].startswith("STORYBOARD-")
            storyboard_task = next(t for t in wf["tasks"] if t["type"] == "storyboard")
            assert storyboard_task["storyboard_id"] == wf["storyboard_id"]
            engine.fail_task(wf["workflow_id"], "TASK-02", "test")
            wf = engine.retry_task(wf["workflow_id"], "TASK-02")
            retry = next(t for t in wf["tasks"] if t["id"] == "TASK-02")
            assert retry["status"] == "pending"
        finally:
            module.storyboard_director = original
