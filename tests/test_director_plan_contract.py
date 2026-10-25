from core.director_plan import DirectorPlanEngine


class NoEnrichment:
    def enrich_plan(self, plan):
        # Verify deterministic structure survives optional model enrichment.
        return {"mode": "test_fallback", "message": "offline"}


def test_director_plan_shot_durations_sum_to_target_and_match_ratio(tmp_path):
    engine = DirectorPlanEngine(project_dir=str(tmp_path))
    engine_enricher = engine
    import core.director_plan as module
    original = module.local_ollama_director
    module.local_ollama_director = NoEnrichment()
    try:
        plan = engine_enricher.create_plan("修仙少年在宗门大比中觉醒", duration=60, ratio="16:9")
    finally:
        module.local_ollama_director = original

    assert sum(float(shot["duration"]) for shot in plan["shots"]) == 60
    assert len(plan["shots"]) >= 10
    assert all("16:9画幅" in shot["visual_prompt"] for shot in plan["shots"])
    assert plan["intent"]["duration_seconds"] == 60


def test_director_plan_rejects_empty_idea_invalid_duration_and_ratio(tmp_path):
    engine = DirectorPlanEngine(project_dir=str(tmp_path))

    for kwargs, expected in [
        ({"idea": " "}, "剧情创意"),
        ({"idea": "修仙", "duration": 0}, "目标时长"),
        ({"idea": "修仙", "duration": "not-a-number"}, "目标时长"),
        ({"idea": "修仙", "ratio": "4:3"}, "画幅"),
    ]:
        try:
            engine.create_plan(**kwargs)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"expected validation error for {kwargs}")


def test_director_plan_handles_non_divisible_duration_exactly(tmp_path):
    engine = DirectorPlanEngine(project_dir=str(tmp_path))
    shots = engine._shots(37, [], [], "夜闯古宅", "9:16")
    assert round(sum(float(shot["duration"]) for shot in shots), 1) == 37
    assert all(shot["duration"] > 0 for shot in shots)
