"""Honest dashboard data for ProductionDashboard.

The old dashboard hard-coded its numbers ("分镜进行中 65%",
"AI 导演中枢 98%/75%/62%/48%", "热门模板 12.8万次使用",
"最近项目" with fixed names). This module derives every number
from real workflow records instead, and says "暂无" when there is
nothing to show. It never invents a percentage.

Workflows here are the plain dicts produced by WorkflowEngine
(list_workflows / load): workflow_id, title, status, created_at,
tasks[{type, status, progress}].
"""
import os

STATUS_TEXT = {
    "ready": "待执行",
    "running": "执行中",
    "paused": "已暂停",
    "completed": "已完成",
    "failed": "失败",
}

PIPELINE_STAGES = [
    ("剧本", ("story",)),
    ("分镜", ("storyboard",)),
    ("角色", ("character",)),
    ("场景", ("scene",)),
    ("生成视频", ("video", "edit")),
]


def status_text(status):
    return STATUS_TEXT.get(status, status or "未知")


def stage_status(tasks, types):
    """Stage status from real tasks: done only when every task of the
    stage is done; running when any is running; otherwise pending."""
    stage = [t for t in tasks if t.get("type") in types]
    if not stage:
        return "待处理"
    if all(t.get("status") == "done" for t in stage):
        return "已完成"
    if any(t.get("status") == "running" for t in stage):
        return "进行中"
    return "待处理"


def summarize_workflows(workflows):
    """Summarize a list of workflow dicts (newest first, as
    WorkflowEngine.list_workflows returns them)."""
    workflows = [w for w in (workflows or []) if isinstance(w, dict)]
    if not workflows:
        return {
            "latest": None,
            "pipeline": [{"name": name, "status": "待处理"} for name, _ in PIPELINE_STAGES],
            "recent": [],
        }
    latest = workflows[0]
    tasks = latest.get("tasks") or []
    done = sum(1 for t in tasks if t.get("status") == "done")
    total = len(tasks)
    progress = int(round(done / total * 100)) if total else 0
    recent = []
    for wf in workflows[:4]:
        created = wf.get("created_at") or ""
        recent.append({
            "title": wf.get("title") or wf.get("workflow_id") or "未命名项目",
            "created": created[:10] if created else "未知时间",
            "status_text": status_text(wf.get("status")),
        })
    return {
        "latest": {
            "title": latest.get("title") or latest.get("workflow_id") or "未命名项目",
            "workflow_id": latest.get("workflow_id"),
            "status": latest.get("status"),
            "status_text": status_text(latest.get("status")),
            "done": done,
            "total": total,
            "progress": progress,
        },
        "pipeline": [
            {"name": name, "status": stage_status(tasks, types)}
            for name, types in PIPELINE_STAGES
        ],
        "recent": recent,
    }
