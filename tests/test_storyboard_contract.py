import tempfile

from core.storyboard_engine import StoryboardDirector


def test_storyboard_preserves_duration_prompt_and_dialogue():
    with tempfile.TemporaryDirectory() as directory:
        director = StoryboardDirector(directory=directory)
        plan = {
            "plan_id": "PLAN-TEST",
            "title": "Contract test",
            "characters": [{"id": "CHAR-1", "name": "主角"}],
            "scenes": [{"id": "SCENE-1", "name": "山门"}],
            "shots": [
                {
                    "id": "SHOT-0001",
                    "index": 1,
                    "duration_seconds": 7.5,
                    "scene_id": "SCENE-1",
                    "visual_prompt": "月下山门，主角拔剑，冷色电影光",
                    "dialogue": "你终于来了。",
                },
                {
                    "id": "SHOT-0002",
                    "index": 2,
                    "duration": 12.5,
                    "scene_id": "SCENE-1",
                    "visual_prompt": "剑光划破夜空",
                    "dialogue": "这一剑，了结因果。",
                },
            ],
        }

        storyboard = director.create_from_plan(plan)

        assert [shot["duration"] for shot in storyboard["shots"]] == [7.5, 12.5]
        assert sum(shot["duration"] for shot in storyboard["shots"]) == 20
        assert storyboard["shots"][0]["visual_prompt"] == "月下山门，主角拔剑，冷色电影光"
        assert storyboard["shots"][0]["prompt"] == "月下山门，主角拔剑，冷色电影光"
        assert storyboard["shots"][0]["dialogue"] == "你终于来了。"
        assert storyboard["shots"][1]["dialogue"] == "这一剑，了结因果。"
