import pytest

from core.render_budget import budget_from_task, recommend_render_budget


def test_m1_8gb_mps_recommends_fast_single_shot_workload():
    budget = recommend_render_budget(
        total_ram_gb=8,
        available_ram_gb=1.4,
        backend="mps",
        capability="video.reference2video",
        requested_tier="quality",
        requested_width=1344,
        requested_height=768,
        requested_frames=81,
        model_memory_gb=12,
    )
    assert budget.profile == "low-memory"
    assert budget.recommended_tier == "fast"
    assert budget.batch_size == 1
    assert budget.allow_upscale is False
    assert any("统一内存" in warning for warning in budget.warnings)
    assert any("70%" in warning for warning in budget.warnings)
    assert any("超过建议上限" in warning for warning in budget.warnings)
    assert any("拆分镜头" in warning for warning in budget.warnings)


def test_cpu_backend_uses_more_conservative_budget():
    budget = recommend_render_budget(total_ram_gb=32, backend="cpu", requested_tier="quality")
    assert budget.recommended_tier == "fast"
    assert budget.max_width == 512
    assert budget.max_frames_per_job == 17
    assert any("CPU 后端" in warning for warning in budget.warnings)


def test_16gb_or_more_does_not_claim_gpu_memory_is_known():
    budget = recommend_render_budget(total_ram_gb=16, backend="mps", requested_tier="quality")
    assert budget.profile == "mid-memory"
    assert budget.recommended_tier == "balanced"
    assert any("不等于可用显存" in warning for warning in budget.warnings)


@pytest.mark.parametrize("ram", [0, -1, "not-a-number"])
def test_invalid_total_ram_is_rejected(ram):
    with pytest.raises(ValueError):
        recommend_render_budget(total_ram_gb=ram)


def test_task_budget_is_opt_in_and_serializable():
    assert budget_from_task({}) is None
    result = budget_from_task({"resource_budget": {"total_ram_gb": 8, "backend": "mps"}})
    assert result["profile"] == "low-memory"
    assert isinstance(result["warnings"], list)


def test_invalid_task_budget_type_is_rejected():
    with pytest.raises(ValueError, match="must be an object"):
        budget_from_task({"resource_budget": "8GB"})
