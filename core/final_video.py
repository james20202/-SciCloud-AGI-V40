"""Locate the finished episode video for in-app preview.

The finished video is easy to miss in Finder because the packaged app keeps
its data in ~/SciCloud AGI V40, not in the old install folder, and the
episode lives several folders deep. This helper gives the UI one place to
look, in priority order, so the preview button never asks the user to hunt.

Priority:
1. A done edit task's verified .mp4 output.
2. Any other done video task's .mp4 output.
3. The newest .mp4 under output/episodes/<workflow_id>/.
Returns an absolute path, or None when no finished video exists.
"""
import os

from core.config import PROJECT_DIR

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def _is_video_file(path):
    return (
        isinstance(path, str)
        and os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS
        and os.path.isfile(path)
        and os.path.getsize(path) > 0
    )


def _task_outputs(task):
    outputs = []
    for item in task.get("outputs") or []:
        if isinstance(item, dict):
            path = item.get("path")
        else:
            path = item
        if isinstance(path, str):
            outputs.append(path)
    return outputs


def find_final_video(workflow, project_dir=None):
    if not isinstance(workflow, dict):
        return None
    tasks = workflow.get("tasks") or []
    # Done edit tasks first: the edit output is the finished episode.
    for task_type in ("edit", "video"):
        for task in tasks:
            if task.get("type") != task_type or task.get("status") != "done":
                continue
            for path in _task_outputs(task):
                if _is_video_file(path):
                    return os.path.abspath(path)
    # Fall back to any done task's video output, then to the episodes folder.
    for task in tasks:
        if task.get("status") != "done":
            continue
        for path in _task_outputs(task):
            if _is_video_file(path):
                return os.path.abspath(path)
    base = project_dir or PROJECT_DIR
    episodes_dir = os.path.join(base, "output", "episodes", str(workflow.get("workflow_id") or ""))
    if os.path.isdir(episodes_dir):
        candidates = [
            os.path.join(episodes_dir, name)
            for name in os.listdir(episodes_dir)
            if _is_video_file(os.path.join(episodes_dir, name))
        ]
        if candidates:
            candidates.sort(key=lambda path: os.path.getmtime(path), reverse=True)
            return os.path.abspath(candidates[0])
    return None
