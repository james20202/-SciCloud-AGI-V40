"""Build a real local FFmpeg edit command from completed workflow artifacts."""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def _existing_outputs(task: dict[str, Any]) -> list[str]:
    # Stale files may remain on disk after a failed or interrupted task. Only
    # consume artifacts explicitly committed by the workflow state machine.
    if not isinstance(task, dict) or task.get("status") != "done":
        return []
    paths = []
    for output in task.get("outputs") or []:
        path = output.get("path") if isinstance(output, dict) else output
        if isinstance(path, str) and os.path.isfile(path) and os.path.getsize(path) > 0:
            paths.append(os.path.abspath(path))
    return paths


def _srt_time_to_seconds(value: str) -> float:
    match = re.fullmatch(r"(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})", value.strip())
    if not match:
        raise ValueError(f"字幕时间码无效：{value}")
    hours, minutes, seconds, milliseconds = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0


def _seconds_to_srt_time(value: float) -> str:
    total_ms = max(0, int(round(value * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _retime_srt(srt: str, offset_seconds: float = 0.0, scale: float = 1.0,
                target_duration: float | None = None) -> str:
    """Shift and scale subtitle cues to match the title-card and episode timeline."""
    if not isinstance(srt, str):
        raise ValueError("字幕内容必须是字符串")
    if not math.isfinite(offset_seconds) or offset_seconds < 0:
        raise ValueError("字幕偏移必须是有限非负数")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("字幕时间缩放比例必须是有限正数")
    if target_duration is not None and (not math.isfinite(target_duration) or target_duration <= 0):
        raise ValueError("字幕目标时长必须是有限正数")
    blocks = re.split(r"\r?\n(?:[ \t]*\r?\n)+", srt.strip()) if srt.strip() else []
    rewritten = []
    timing_pattern = re.compile(
        r"^\s*(\d{2,}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
        r"(\d{2,}:\d{2}:\d{2}[,.]\d{3})(.*)$"
    )
    for block in blocks:
        lines = block.splitlines()
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        match = timing_pattern.match(lines[timing_index])
        if not match:
            raise ValueError("字幕时间轴包含无法解析的时间范围")
        start = offset_seconds + _srt_time_to_seconds(match.group(1)) * scale
        end = offset_seconds + _srt_time_to_seconds(match.group(2)) * scale
        if end <= start:
            raise ValueError("字幕结束时间必须晚于开始时间")
        if target_duration is not None:
            if start >= target_duration:
                continue
            end = min(end, target_duration)
        if end <= start:
            continue
        lines[timing_index] = (
            f"{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}{match.group(3)}"
        )
        if lines and re.fullmatch(r"\s*\d+\s*", lines[0]):
            lines[0] = str(len(rewritten) + 1)
        else:
            lines.insert(0, str(len(rewritten) + 1))
        rewritten.append("\n".join(lines))
    return "\n\n".join(rewritten) + ("\n" if rewritten else "")


def _write_subtitle_draft(workflow: dict[str, Any], output_dir: str,
                          offset_seconds: float = 0.0, scale: float = 1.0,
                          target_duration: float | None = None) -> str | None:
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
            retimed_srt = _retime_srt(
                srt, offset_seconds=offset_seconds, scale=scale,
                target_duration=target_duration,
            )
            if not retimed_srt.strip():
                continue
            subtitle_path = os.path.join(output_dir, "subtitle_draft.srt")
            fd, temporary = tempfile.mkstemp(prefix=".subtitle-", suffix=".tmp", dir=output_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                    handle.write(retimed_srt)
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

    video_records = []
    seen_video_paths = set()
    ordered_tasks = sorted(
        [task for task in tasks if isinstance(task, dict) and task.get("type") in {"title_card", "video"}],
        key=lambda task: 0 if task.get("type") == "title_card" else 1,
    )
    for task in ordered_tasks:
        task_type = task.get("type")
        for path in _existing_outputs(task):
            if Path(path).suffix.lower() not in VIDEO_EXTENSIONS or path in seen_video_paths:
                continue
            seen_video_paths.add(path)
            record = {"path": path, "kind": task_type}
            if task_type == "title_card":
                raw_card_duration = task.get(
                    "title_card_duration_seconds",
                    task.get("duration_seconds", task.get("target_duration_seconds", 3.0)),
                )
                try:
                    card_duration = float(raw_card_duration)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValueError("片头时长必须是有限正数") from exc
                if not math.isfinite(card_duration) or card_duration <= 0:
                    raise ValueError("片头时长必须是有限正数")
                record["duration_seconds"] = card_duration
            video_records.append(record)

    video_paths = [record["path"] for record in video_records]
    title_card_duration = sum(
        record["duration_seconds"] for record in video_records if record["kind"] == "title_card"
    )
    has_title_card = title_card_duration > 0
    main_video_count = sum(record["kind"] == "video" for record in video_records)
    if not video_paths:
        raise ValueError("没有可用的视频片段或片头，不能执行最终剪辑")
    if has_title_card and not main_video_count:
        raise ValueError("存在片头但没有可用的正片视频片段，拒绝生成只有片头的成片")
    if title_card_duration >= target_duration:
        raise ValueError("片头时长必须小于最终剪辑目标时长")
    main_content_budget = target_duration - title_card_duration
    video_content_speed_factor = main_content_budget / target_duration if has_title_card else 1.0

    audio_records = []
    seen_audio_paths = set()
    for task in tasks:
        if not isinstance(task, dict) or task.get("type") not in {"voice", "sound"}:
            continue
        for path in _existing_outputs(task):
            if Path(path).suffix.lower() in AUDIO_EXTENSIONS and path not in seen_audio_paths:
                seen_audio_paths.add(path)
                audio_records.append({"path": path, "kind": task.get("type")})
    audio_paths = [record["path"] for record in audio_records]

    if not audio_paths:
        raise ValueError("没有可用的配音/音效文件，拒绝输出无音轨成片")

    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    subtitle_path = _write_subtitle_draft(
        workflow, output_dir, offset_seconds=title_card_duration,
        scale=video_content_speed_factor, target_duration=target_duration,
    )

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
    for index, record in enumerate(video_records):
        label = f"v{index}"
        common = (
            f"[{index}:v:0]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,"
        )
        if record["kind"] == "title_card":
            card_duration = record["duration_seconds"]
            filters.append(
                f"{common}trim=duration={card_duration:g},setpts=PTS-STARTPTS,"
                f"tpad=stop_mode=clone:stop_duration={card_duration:g},"
                f"trim=duration={card_duration:g},format=yuv420p[{label}]"
            )
        else:
            setpts = (
                "setpts=PTS-STARTPTS"
                if not has_title_card
                else f"setpts={video_content_speed_factor:.8g}*(PTS-STARTPTS)"
            )
            filters.append(f"{common}{setpts},format=yuv420p[{label}]")
        video_labels.append(f"[{label}]")
    # Reserve the title-card time inside the requested final duration. The full
    # planned episode is sped proportionally into the remaining budget instead of
    # being cut off at the tail by the final trim.
    filters.append(f"{''.join(video_labels)}concat=n={len(video_paths)}:v=1:a=0[vcat]")
    filters.append(
        f"[vcat]tpad=stop_mode=clone:stop_duration={target_duration:g},"
        f"trim=duration={target_duration:g},setpts=PTS-STARTPTS[vout]"
    )

    audio_labels = []
    for offset, record in enumerate(audio_records):
        input_index = audio_start + offset
        label = f"a{offset}"
        chain = (
            f"[{input_index}:a:0]aresample=48000,"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
        )
        if record["kind"] == "voice" and has_title_card:
            tempo = 1.0 / video_content_speed_factor
            delay_ms = int(round(title_card_duration * 1000))
            chain += f"atempo={tempo:.8g},adelay={delay_ms}|{delay_ms},"
        chain += f"apad=pad_dur={target_duration:g}[{label}]"
        filters.append(chain)
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
        "audio_input_types": [record["kind"] for record in audio_records],
        "target_duration_seconds": target_duration,
        "title_card_duration_seconds": round(title_card_duration, 3),
        "main_content_duration_budget_seconds": round(main_content_budget, 3),
        "video_content_speed_factor": round(video_content_speed_factor, 8),
    }
