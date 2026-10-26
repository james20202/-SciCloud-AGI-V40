"""Build a real local FFmpeg edit command from completed workflow artifacts."""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def _existing_outputs(task: dict[str, Any]) -> list[str]:
    paths = []
    for output in task.get("outputs") or []:
        path = output.get("path") if isinstance(output, dict) else output
        if isinstance(path, str) and os.path.isfile(path) and os.path.getsize(path) > 0:
            paths.append(os.path.abspath(path))
    return paths


def _write_subtitle_draft(workflow: dict[str, Any], output_dir: str) -> str | None:
    for task in workflow.get("tasks", []):
        if not isinstance(task, dict) or task.get("type") != "prompt":
            continue
        for path in _existing_outputs(task):
            if Path(path).suffix.lower() != ".json":
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, ValueError):
                continue
            srt = payload.get("subtitle_srt_draft") if isinstance(payload, dict) else None
            if not isinstance(srt, str) or not srt.strip():
                continue
            subtitle_path = os.path.join(output_dir, "subtitle_draft.srt")
            fd, temporary = tempfile.mkstemp(prefix=".subtitle-", suffix=".tmp", dir=output_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                    handle.write(srt)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, subtitle_path)
            finally:
                if os.path.exists(temporary):
                    os.remove(temporary)
            return subtitle_path
    return None


def build_episode_edit_command(
    workflow: dict[str, Any],
    output_path: str,
    ffmpeg: str = "ffmpeg",
) -> dict[str, Any]:
    """Create a video/audio/subtitle mux command; never invent missing source media."""
    if not isinstance(workflow, dict) or not isinstance(workflow.get("tasks"), list):
        raise ValueError("工作流结构无效，无法剪辑")
    tasks = workflow["tasks"]
    edit_tasks = [task for task in tasks if isinstance(task, dict) and task.get("type") == "edit"]
    if not edit_tasks:
        raise ValueError("工作流缺少 edit 任务")
    edit_task = edit_tasks[0]
    raw_target = edit_task.get("expected_duration_seconds", edit_task.get("target_duration_seconds", edit_task.get("duration_seconds")))
    try:
        target_duration = float(raw_target)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("最终剪辑缺少有效的目标时长") from exc
    if not math.isfinite(target_duration) or not 0 < target_duration <= 3600:
        raise ValueError("最终剪辑目标时长必须在 0 到 3600 秒之间")

    video_paths = []
    audio_paths = []
    # Title cards are placed before the episode's generated clips.
    ordered_tasks = sorted(
        [task for task in tasks if isinstance(task, dict) and task.get("type") in {"title_card", "video"}],
        key=lambda task: 0 if task.get("type") == "title_card" else 1,
    )
    for task in ordered_tasks:
        for path in _existing_outputs(task):
            if Path(path).suffix.lower() in VIDEO_EXTENSIONS and path not in video_paths:
                video_paths.append(path)
    for task in tasks:
        if not isinstance(task, dict) or task.get("type") not in {"voice", "sound"}:
            continue
        for path in _existing_outputs(task):
            if Path(path).suffix.lower() in AUDIO_EXTENSIONS and path not in audio_paths:
                audio_paths.append(path)

    if not video_paths:
        raise ValueError("没有可用的视频片段或片头，不能执行最终剪辑")
    if not audio_paths:
        raise ValueError("没有可用的配音/音效文件，拒绝输出无音轨成片")

    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    subtitle_path = _write_subtitle_draft(workflow, output_dir)

    command = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for path in video_paths:
        command.extend(["-i", path])
    audio_start = len(video_paths)
    for path in audio_paths:
        command.extend(["-i", path])
    subtitle_index = None
    if subtitle_path:
        subtitle_index = audio_start + len(audio_paths)
        command.extend(["-i", subtitle_path])

    filters = []
    video_labels = []
    for index in range(len(video_paths)):
        label = f"v{index}"
        filters.append(
            f"[{index}:v:0]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,setpts=PTS-STARTPTS,format=yuv420p[{label}]"
        )
        video_labels.append(f"[{label}]")
    # A target duration passed to FFmpeg's output -t alone only truncates media;
    # it does not extend a short concatenated video. Pad the final frame and trim
    # explicitly so the video stream reaches the requested duration, while QC can
    # still inspect the resulting media and report the hold-frame padding.
    filters.append(f"{''.join(video_labels)}concat=n={len(video_paths)}:v=1:a=0[vcat]")
    filters.append(
        f"[vcat]tpad=stop_mode=clone:stop_duration={target_duration:g},"
        f"trim=duration={target_duration:g},setpts=PTS-STARTPTS[vout]"
    )

    audio_labels = []
    for offset in range(len(audio_paths)):
        input_index = audio_start + offset
        label = f"a{offset}"
        filters.append(
            f"[{input_index}:a:0]aresample=48000,"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"apad=pad_dur={target_duration:g}[{label}]"
        )
        audio_labels.append(f"[{label}]")
    filters.append(
        f"{''.join(audio_labels)}amix=inputs={len(audio_paths)}:duration=longest:dropout_transition=2,"
        f"atrim=duration={target_duration:g},asetpts=PTS-STARTPTS[aout]"
    )

    command.extend(["-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]"])
    if subtitle_index is not None:
        command.extend(["-map", f"{subtitle_index}:0", "-c:s", "mov_text"])
    command.extend([
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-t", f"{target_duration:g}", output_path,
    ])
    return {
        "command": command,
        "output_path": output_path,
        "subtitle_path": subtitle_path,
        "video_inputs": video_paths,
        "audio_inputs": audio_paths,
        "target_duration_seconds": target_duration,
    }
