import math

import pytest

from core.episode_pipeline import EpisodePipeline


def plan_with_durations(durations):
    return {"shots": [
        {"id": f"SHOT-{index:03d}", "duration": duration}
        for index, duration in enumerate(durations, 1)
    ]}


def test_plan_contract_accepts_exact_target_duration():
    result = EpisodePipeline._validate_plan_shots(plan_with_durations([10, 10, 10, 10, 10, 10]), 60)
    assert result == {"shot_count": 6, "planned_duration_seconds": 60.0}


def test_plan_contract_rejects_duration_drift_before_generation():
    with pytest.raises(ValueError, match="不匹配"):
        EpisodePipeline._validate_plan_shots(plan_with_durations([5] * 6), 60)


@pytest.mark.parametrize("duration", [0, -1, math.nan, math.inf, "not-a-number"])
def test_plan_contract_rejects_invalid_shot_duration(duration):
    with pytest.raises(ValueError):
        EpisodePipeline._validate_plan_shots(plan_with_durations([duration]), 5)


def test_plan_contract_rejects_duplicate_shot_ids():
    plan = {"shots": [
        {"id": "SHOT-1", "duration": 2},
        {"id": "SHOT-1", "duration": 3},
    ]}
    with pytest.raises(ValueError, match="重复"):
        EpisodePipeline._validate_plan_shots(plan, 5)


@pytest.mark.parametrize("target", [0, -1, math.nan, math.inf, "invalid"])
def test_plan_contract_rejects_invalid_episode_target(target):
    with pytest.raises(ValueError, match="目标时长"):
        EpisodePipeline._validate_plan_shots(plan_with_durations([5]), target)
