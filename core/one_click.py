"""One-click episode production: preflight, then ordered execution.

This module does not invent a new execution engine. It reuses
ExecutionEngine.execute for every task, in dependency order, and stops at
the first failure instead of leaving the user to click through 13 tasks
and discover a blocker at step 6, 7 or 8.

Preflight catches the blockers that the 2026-10-27 golden sample hit late:
ComfyUI not running, no image.text2image workflow registered, TTS not
enabled, and ffmpeg/ffprobe invisible to a Finder-launched app. A blocker
is reported before any task starts, with the action that fixes it.

Since WF-559D10EB (2026-10-27 22:21 JST) the same rule also covers
video: a pending video task (TASK-07) needs a video.image2video
workflow registered. Without one, preflight blocks before any task
runs instead of letting one-click sail through TASK-01..06 and fail
at TASK-07 with "ComfyUI 任务缺少 API 格式 workflow JSON".
"""
import os
from urllib import request

from core.adapters.comfyui_adapter import BUILTIN_WORKFLOW_DIR, USER_WORKFLOW_DIR
from core.comfyui_workflow_registry import WorkflowRegistry
from core.execution_engine import execution_engine
from core.final_video import find_final_video
from core.media_tools import find_tool
from core.model_hub import model_hub
from core.workflow_engine import workflow_engine


def _comfyui_reachable(endpoint):
    try:
        with request.urlopen(endpoint.rstrip("/") + "/system_stats", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def preflight_workflow(workflow, model_finder=None, tool_finder=None, capabilities=None):
    """Return a list of blocker messages for a workflow dict (empty = ready).

    `capabilities` is an optional override of the registered workflow
    capabilities (used by tests so they do not depend on the local
    registry directories). When omitted, capabilities are read from
    WorkflowRegistry(BUILTIN_WORKFLOW_DIR, USER_WORKFLOW_DIR).
    """
    find_model = model_finder or model_hub.find_for_skill
    find_tool_fn = tool_finder or find_tool
    blockers = []
    if not isinstance(workflow, dict):
        return ["工作流不存在"]
    tasks = workflow.get("tasks") or []
    pending = [task for task in tasks if task.get("status") in ("ready", "pending", "running")]
    if not tasks:
        return ["工作流没有任务"]
    if any(task.get("type") in ("image", "video") for task in pending):
        image_model = find_model("image")
        if not image_model:
            blockers.append("ComfyUI 未在 Model Hub 启用：请到 Model Hub 启用 ComfyUI，并确认它已连接。")
        else:
            endpoint = image_model.get("endpoint") or "http://127.0.0.1:8188"
            if not _comfyui_reachable(endpoint):
                blockers.append(
                    "ComfyUI 未运行（%s 无响应）：请先双击 ComfyUI/start.command 启动它，保持终端窗口打开。" % endpoint
                )
        if capabilities is None:
            try:
                registry = WorkflowRegistry(BUILTIN_WORKFLOW_DIR, USER_WORKFLOW_DIR)
                capabilities = {item.get("capability") for item in registry.list()}
            except Exception:
                capabilities = set()
        if "image.text2image" not in capabilities:
            blockers.append(
                "未找到 image.text2image 工作流：请把 docs/comfyui_workflows/sd15-text2image.json "
                "复制到数据目录 data/comfyui_workflows/user/ 下（本机已有该文件时请检查数据目录是否指向打包版目录）。"
            )
        if any(task.get("type") == "video" for task in pending) and "video.image2video" not in capabilities:
            # Do NOT phrase this as "ComfyUI 未运行": ComfyUI may be up
            # and the image workflow may be fine; what is missing is a
            # video workflow/model/node. And do NOT pretend the FFmpeg
            # zoompan fallback is AI video: it is only an alternative.
            blockers.append(
                "未找到 video.image2video 工作流：本机目前没有 AI 视频模型/节点，"
                "TASK-07 无法用 ComfyUI 执行；可先用 FFmpeg 动态镜头作为替代"
                "（那是 FFmpeg 动画，不是 AI 视频），或等 AnimateDiff 装好后再跑。"
                "此 blocker 会阻止一键出片开始执行，而不是跑到一半才失败。"
            )
    if any(task.get("type") == "voice" for task in pending) and not find_model("voice"):
        blockers.append("TTS 未启用：请到 Model Hub 启用本地 TTS，并配置 say 或其他 TTS 命令。")
    if not find_tool_fn("ffmpeg"):
        blockers.append("未找到 FFmpeg：请确认已安装 Homebrew FFmpeg（/opt/homebrew/bin/ffmpeg）。")
    if not find_tool_fn("ffprobe"):
        blockers.append("未找到 ffprobe：请确认已安装 Homebrew FFmpeg（/opt/homebrew/bin/ffprobe）。")
    return blockers


def preflight(workflow_id):
    workflow = workflow_engine.load(workflow_id)
    return preflight_workflow(workflow)


def run_one_click(workflow_id, max_steps=50):
    """Run every ready task in dependency order. Stop at the first failure."""
    workflow = workflow_engine.load(workflow_id)
    blockers = preflight_workflow(workflow)
    if blockers:
        return {"success": False, "blockers": blockers, "message": "预检未通过，未开始执行。", "steps": 0}
    steps = 0
    last_result = None
    while steps < max_steps:
        workflow = workflow_engine.load(workflow_id)
        if workflow.get("status") == "completed":
            break
        ready = [task for task in workflow.get("tasks") or [] if task.get("status") == "ready"]
        if not ready:
            break
        task = ready[0]
        result = execution_engine.execute(workflow_id, task["id"])
        steps += 1
        last_result = result
        if not isinstance(result, dict) or result.get("success") is not True:
            return {
                "success": False,
                "message": (result or {}).get("message", "任务执行失败") if isinstance(result, dict) else "任务执行失败",
                "failed_task_id": task["id"],
                "steps": steps,
            }
    workflow = workflow_engine.load(workflow_id)
    final_video = find_final_video(workflow)
    if workflow.get("status") == "completed":
        return {
            "success": True,
            "message": "一键出片完成",
            "steps": steps,
            "final_video": final_video,
            "last_result": last_result,
        }
    return {
        "success": False,
        "message": "执行结束但工作流未完成，请查看未就绪任务的错误信息。",
        "steps": steps,
        "final_video": final_video,
    }
