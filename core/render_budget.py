"""Resource-aware render planning for small local machines.
This module never downloads models or changes the user's ComfyUI installation.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
import math

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
    if not math.isfinite(ram) or ram <= 0:
        raise ValueError("total_ram_gb must be a finite positive number")
    if available_ram_gb is not None:
        try:
            available = float(available_ram_gb)
        except (TypeError, ValueError) as exc:
            raise ValueError("available_ram_gb must be a finite non-negative number") from exc
        if not math.isfinite(available) or available < 0:
            raise ValueError("available_ram_gb must be a finite non-negative number")
    if model_memory_gb is not None:
        try:
            model_memory = float(model_memory_gb)
        except (TypeError, ValueError) as exc:
            raise ValueError("model_memory_gb must be a finite non-negative number") from exc
        if not math.isfinite(model_memory) or model_memory < 0:
            raise ValueError("model_memory_gb must be a finite non-negative number")
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
    if model_memory_gb is not None and model_memory > ram * 0.70:
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

def _detect_available_ram_gb() -> float | None:
    """Best-effort available-memory estimate across macOS and Linux."""
    import platform
    import subprocess
    import re

    try:
        import psutil
        available = float(psutil.virtual_memory().available) / (1024 ** 3)
        if math.isfinite(available) and available >= 0:
            return available
    except Exception:
        pass

    system = platform.system()
    if system == "Linux":
        try:
            with open("/proc/meminfo", encoding="ascii") as stream:
                for line in stream:
                    if line.startswith("MemAvailable:"):
                        return max(0.0, float(line.split()[1]) / (1024 ** 2))
        except (OSError, ValueError, IndexError):
            pass
    elif system == "Darwin":
        try:
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=2, check=False
            )
            if result.returncode == 0:
                page_size = 4096
                header = result.stdout.splitlines()[0] if result.stdout else ""
                match = re.search(r"page size of (\d+) bytes", header)
                if match:
                    page_size = int(match.group(1))
                pages = {}
                for line in result.stdout.splitlines()[1:]:
                    match = re.match(r"([^:]+):\s*([0-9.]+)", line)
                    if match:
                        pages[match.group(1).strip().lower()] = float(match.group(2).replace(".", ""))
                reclaimable = sum(
                    pages.get(key, 0.0)
                    for key in ("pages free", "pages inactive", "pages speculative", "pages purgeable")
                )
                if reclaimable >= 0:
                    return reclaimable * page_size / (1024 ** 3)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return None


def detect_local_device_budget(**overrides: Any) -> RenderBudget:
    """Best-effort local RAM/backend detection; never downloads or installs anything."""
    import os
    import platform
    total_ram_gb = None
    try:
        total_ram_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
    except (ValueError, OSError, AttributeError):
        pass
    if not total_ram_gb or total_ram_gb <= 0:
        raise ValueError("无法自动检测系统内存，请手动填写 total_ram_gb")
    backend = "unknown"
    try:
        import torch
        if getattr(torch, "cuda", None) and torch.cuda.is_available():
            backend = "cuda"
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            backend = "mps"
        else:
            backend = "cpu"
    except Exception:
        backend = "mps" if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"} else "unknown"
    options = dict(overrides)
    options.pop("auto_detect", None)
    options.setdefault("total_ram_gb", total_ram_gb)
    options.setdefault("backend", backend)
    if "available_ram_gb" not in options:
        available = _detect_available_ram_gb()
        if available is not None:
            options["available_ram_gb"] = available
    return recommend_render_budget(**options)


def budget_from_task(task: dict[str, Any]) -> dict[str, Any] | None:
    """Build a budget only when the caller explicitly opts in."""
    config = task.get("resource_budget")
    if config is None: return None
    if not isinstance(config, dict): raise ValueError("resource_budget must be an object")
    options = dict(config)
    if options.pop("auto_detect", False):
        return detect_local_device_budget(**options).to_dict()
    return recommend_render_budget(**options).to_dict()



def apply_budget_to_graph(graph: dict[str, Any], budget: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Clamp common video/image node inputs to budget limits, preserving graph shape."""
    import copy
    result = copy.deepcopy(graph)
    report = {"profile": budget["profile"], "recommended_tier": budget["recommended_tier"],
              "warnings": list(budget["warnings"]), "adjustments": []}
    for node_id, node in result.items():
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
            continue
        inputs = node["inputs"]
        width, height = inputs.get("width"), inputs.get("height")
        if (isinstance(width, (int, float)) and not isinstance(width, bool)
                and isinstance(height, (int, float)) and not isinstance(height, bool)
                and width > 0 and height > 0
                and (width > budget["max_width"] or height > budget["max_height"])):
            scale = min(budget["max_width"] / width, budget["max_height"] / height)
            new_width = max(64, int(round((width * scale) / 64)) * 64)
            new_height = max(64, int(round((height * scale) / 64)) * 64)
            for key, old_value, new_value in (("width", width, new_width), ("height", height, new_height)):
                if old_value != new_value:
                    report["adjustments"].append({
                        "node_id": str(node_id), "input": key,
                        "from": old_value, "to": new_value,
                    })
                    inputs[key] = new_value
        elif isinstance(width, (int, float)) and not isinstance(width, bool) and width > budget["max_width"]:
            report["adjustments"].append({"node_id": str(node_id), "input": "width", "from": width, "to": budget["max_width"]})
            inputs["width"] = budget["max_width"]
        elif isinstance(height, (int, float)) and not isinstance(height, bool) and height > budget["max_height"]:
            report["adjustments"].append({"node_id": str(node_id), "input": "height", "from": height, "to": budget["max_height"]})
            inputs["height"] = budget["max_height"]
        for key, ceiling in (("length", budget["max_frames_per_job"]),
                             ("num_frames", budget["max_frames_per_job"]),
                             ("batch_size", budget["batch_size"])):
            value = inputs.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if value > ceiling:
                report["adjustments"].append({
                    "node_id": str(node_id), "input": key,
                    "from": value, "to": ceiling,
                })
                inputs[key] = ceiling
    if report["adjustments"]:
        report["warnings"].append("已自动收紧工作流中的常见尺寸/帧数/批量输入；请检查工作流语义并先做短片段测试。")
    return result, report
