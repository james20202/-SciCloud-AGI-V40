"""Resource-aware render planning for small local machines.
This module never downloads models or changes the user's ComfyUI installation.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class RenderBudget:
    profile: str
    recommended_tier: str
    max_width: int
    max_height: int
    max_frames_per_job: int
    batch_size: int
    allow_upscale: bool
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["warnings"] = list(self.warnings)
        return result

def recommend_render_budget(*, total_ram_gb: float, available_ram_gb: float | None = None,
                            backend: str = "unknown", capability: str = "video.reference2video",
                            requested_tier: str = "balanced", requested_width: int | None = None,
                            requested_height: int | None = None, requested_frames: int | None = None,
                            model_memory_gb: float | None = None) -> RenderBudget:
    """Return conservative advice; this is not a guarantee that a model fits."""
    try:
        ram = float(total_ram_gb)
    except (TypeError, ValueError) as exc:
        raise ValueError("total_ram_gb must be a positive number") from exc
    if ram <= 0:
        raise ValueError("total_ram_gb must be a positive number")
    if available_ram_gb is not None and float(available_ram_gb) < 0:
        raise ValueError("available_ram_gb cannot be negative")
    backend = str(backend or "unknown").lower()
    tier = str(requested_tier or "balanced").lower()
    if tier not in {"fast", "balanced", "quality"}:
        raise ValueError("requested_tier must be fast, balanced, or quality")
    warnings: list[str] = []
    if backend == "mps":
        warnings.append("Apple MPS 使用统一内存；系统内存总量不等于可用显存。")
    elif backend in {"cpu", "unknown"}:
        warnings.append("未确认可用 GPU 后端；扩散视频生成可能极慢或无法加载模型。")
    if available_ram_gb is not None and float(available_ram_gb) < 2:
        warnings.append("当前可用内存低于 2 GiB；建议关闭其他应用，避免换页或任务崩溃。")
    if model_memory_gb is not None and float(model_memory_gb) > ram * 0.70:
        warnings.append("模型估算内存超过系统内存的 70%；本机直接加载风险高，优先选择更小/量化模型或外部生成节点。")
    if ram < 8:
        profile, max_w, max_h, frames = "constrained", 512, 512, 17
        if tier != "fast": warnings.append("内存低于 8 GiB，建议 fast 档和单镜头分段生成。")
        tier = "fast"
    elif ram < 16:
        profile, max_w, max_h, frames = "low-memory", 768, 768, 25
        if tier == "quality":
            tier = "fast"
            warnings.append("系统内存低于 16 GiB，不建议 quality 档；建议 fast 档。")
        elif tier == "balanced":
            tier = "fast"
            warnings.append("系统内存低于 16 GiB，建议 fast 档并逐镜生成。")
    elif ram < 32:
        profile, max_w, max_h, frames = "mid-memory", 1024, 1024, 49
        if tier == "quality":
            tier = "balanced"
            warnings.append("系统内存低于 32 GiB，建议 balanced 档。")
    else:
        profile, max_w, max_h, frames = "high-memory", 1344, 1344, 81
    if backend == "cpu":
        max_w, max_h, frames, tier = min(max_w, 512), min(max_h, 512), min(frames, 17), "fast"
        warnings.append("CPU 后端使用极保守尺寸与短片段预算；优先逐镜图片动画或轻量模型。")
    if requested_width and requested_width > max_w:
        warnings.append(f"请求宽度 {requested_width}px 超过建议上限 {max_w}px；需降分辨率或分阶段放大。")
    if requested_height and requested_height > max_h:
        warnings.append(f"请求高度 {requested_height}px 超过建议上限 {max_h}px；需降分辨率或分阶段放大。")
    if requested_frames and requested_frames > frames:
        warnings.append(f"请求 {requested_frames} 帧超过单任务建议上限 {frames} 帧；建议拆分镜头并保留断点。")
    if capability.startswith("video.") and ram < 16:
        warnings.append("低内存视频策略：一次只渲染一个镜头；先出低分辨率预览，确认后再超分。")
    if capability == "video.upscale" and ram < 16:
        warnings.append("低内存设备不建议整片超分；按短镜头分块处理，拼接后保留原音轨。")
    return RenderBudget(profile, tier, max_w, max_h, frames, 1, ram >= 16, tuple(dict.fromkeys(warnings)))

def budget_from_task(task: dict[str, Any]) -> dict[str, Any] | None:
    """Build a budget only when the caller explicitly supplies device data."""
    config = task.get("resource_budget")
    if config is None: return None
    if not isinstance(config, dict): raise ValueError("resource_budget must be an object")
    return recommend_render_budget(**config).to_dict()
