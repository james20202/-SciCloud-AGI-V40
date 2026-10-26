"""Canonical episode timeline and provenance manifest.

The timeline contract is inspired by the MIT-licensed Comic-drama project:
https://github.com/tccnnd/Comic-drama (docs/canonical_timeline.md).
This module is an independent implementation adapted to SciCloud's episode schema.
"""
import json
import math
import os
import tempfile
from datetime import datetime


def _number(value, fallback=0.0):
    try:
        number = float(value)
        return max(0.0, number) if math.isfinite(number) else float(fallback)
    except (TypeError, ValueError, OverflowError):
        return float(fallback)


def build_episode_timeline(episode, shot_job, clip_records, output_path, final_video=None, audio_assets=None):
    """Write a stable, inspectable timeline with real/fallback media provenance."""
    if not isinstance(episode, dict):
        raise ValueError("episode 必须是对象")
    if not isinstance(output_path, str) or not output_path.strip():
        raise ValueError("output_path 必须是非空路径")
    if shot_job is not None and not isinstance(shot_job, dict):
        raise ValueError("shot_job 必须是对象")
    if not isinstance(clip_records, list) or not clip_records:
        raise ValueError("时间轴必须至少包含一个镜头媒体记录")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cursor = 0.0
    seen_shot_ids = set()
    picture = []
    scene_index = []
    real_video_count = 0
    fallback_count = 0
    for order, record in enumerate(clip_records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"第 {order} 个镜头媒体记录不是对象")
        raw_path = record.get("path")
        if not isinstance(raw_path, str) or not raw_path or not os.path.isfile(raw_path) or os.path.getsize(raw_path) <= 0:
            raise ValueError(f"第 {order} 个镜头媒体文件不存在或为空")
        duration = _number(record.get("duration_seconds"), 0)
        spec = record.get("spec") if isinstance(record.get("spec"), dict) else {}
        if duration <= 0:
            duration = _number(spec.get("duration_seconds", spec.get("duration", 5)), 5)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError(f"第 {order} 个镜头时长必须是有限正数")
        source = os.path.abspath(raw_path)
        is_real_video = record.get("source_kind") == "video"
        if is_real_video:
            real_video_count += 1
        else:
            fallback_count += 1
        shot_id = str(record.get("shot_id") or f"SHOT-{order:03d}").strip()
        if not shot_id or shot_id in seen_shot_ids:
            raise ValueError(f"镜头 ID 为空或重复：{shot_id or '(empty)'}")
        seen_shot_ids.add(shot_id)
        scene_id = str(record.get("scene_id") or spec.get("scene_id") or "")
        clip = {
            "item_type": "clip",
            "clip_id": f"{shot_id}_picture",
            "scene_id": scene_id,
            "shot_id": shot_id,
            "scene_order": order,
            "name": str(record.get("name") or shot_id),
            "start_seconds": round(cursor, 3),
            "duration_seconds": round(duration, 3),
            "end_seconds": round(cursor + duration, 3),
            "source_range": {"start_seconds": 0.0, "duration_seconds": round(duration, 3)},
            "media_reference": {"path": source},
            "metadata": {
                "generation": {
                    "provider_id": str(record.get("provider_id") or ("local_ffmpeg" if not is_real_video else "comfyui_or_external")),
                    "is_real_video": is_real_video,
                    "fallback_used": not is_real_video,
                    "source_kind": str(record.get("source_kind") or "unknown"),
                    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                },
                "visual_prompt": str(spec.get("visual_prompt") or spec.get("prompt") or ""),
                "camera_movement": str(spec.get("camera_movement") or ""),
                "dialogue": str(spec.get("dialogue") or ""),
                "voiceover": str(spec.get("voiceover") or spec.get("narration") or ""),
                "character_ids": spec.get("character_ids") or [],
                "location_id": str(spec.get("location_id") or ""),
                "target_duration_seconds": _number(record.get("target_duration_seconds"), duration),
            },
        }
        picture.append(clip)
        scene_index.append({"order": order, "shot_id": shot_id, "scene_id": scene_id,
                            "start_seconds": clip["start_seconds"], "end_seconds": clip["end_seconds"],
                            "path": source, "source_kind": clip["metadata"]["generation"]["source_kind"]})
        cursor += duration

    audio_assets = audio_assets if isinstance(audio_assets, dict) else {}
    audio_children = []
    # Prefer the exact mix that was passed into final assembly. Raw per-shot audio
    # artifacts are only provenance inputs; exporting them as if they were the final
    # timeline track would misrepresent what users actually hear.
    mixed_audio_path = audio_assets.get("audio_path")
    if (isinstance(mixed_audio_path, str) and mixed_audio_path
            and os.path.isfile(mixed_audio_path) and os.path.getsize(mixed_audio_path) > 0):
        audio_children.append({
            "item_type": "clip",
            "clip_id": "episode_dialogue_mix",
            "shot_id": "",
            "start_seconds": 0.0,
            "duration_seconds": round(cursor, 3),
            "media_reference": {"path": os.path.abspath(mixed_audio_path)},
            "metadata": {"generation": {"source_kind": "assembled_dialogue_mix"},
                         "audio_clip_count": _number(audio_assets.get("audio_clip_count"), 0)},
        })
    else:
        # Backward-compatible path for older callers that do not provide assembly
        # audio metadata. Only use real files and preserve their shot alignment.
        shots = (shot_job or {}).get("shots", [])
        if not isinstance(shots, list):
            raise ValueError("shot_job.shots 必须是列表")
        by_id = {}
        for index, shot in enumerate(shots, 1):
            if not isinstance(shot, dict):
                raise ValueError(f"shot_job 第 {index} 个镜头必须是对象")
            shot_id = shot.get("shot_id")
            if shot_id is None or not str(shot_id).strip():
                raise ValueError(f"shot_job 第 {index} 个镜头缺少 shot_id")
            key = str(shot_id)
            if key in by_id:
                raise ValueError(f"shot_job 镜头 ID 重复：{key}")
            artifacts = shot.get("artifacts", [])
            if not isinstance(artifacts, list):
                raise ValueError(f"镜头 {key} artifacts 必须是列表")
            if any(not isinstance(item, dict) for item in artifacts):
                raise ValueError(f"镜头 {key} artifacts 包含非对象记录")
            by_id[key] = shot
        for clip in picture:
            shot = by_id.get(clip["shot_id"], {})
            for artifact in shot.get("artifacts", []):
                path = artifact.get("path")
                if artifact.get("kind") == "audio" and path and os.path.isfile(path) and os.path.getsize(path) > 0:
                    audio_children.append({
                        "item_type": "clip",
                        "clip_id": f"{clip['shot_id']}_audio_{len(audio_children)+1}",
                        "shot_id": clip["shot_id"],
                        "start_seconds": clip["start_seconds"],
                        "duration_seconds": clip["duration_seconds"],
                        "media_reference": {"path": os.path.abspath(path)},
                        "metadata": {"generation": {"source_kind": "audio_artifact"}},
                    })

    subtitle_path = audio_assets.get("subtitle_path")
    subtitle_asset = None
    if (isinstance(subtitle_path, str) and subtitle_path
            and os.path.isfile(subtitle_path) and os.path.getsize(subtitle_path) > 0):
        subtitle_asset = {
            "path": os.path.abspath(subtitle_path),
            "format": "srt",
            "subtitle_count": int(_number(audio_assets.get("subtitle_count"), 0)),
            "embedded_in_final_video": True,
        }

    timeline = {
        "version": 1,
        "kind": "canonical_timeline",
        "schema": "otio-inspired",
        "project_id": str(episode.get("episode_id") or ""),
        "title": str(episode.get("title") or ""),
        "frame_rate": 24,
        "resolution": {"width": 1080, "height": 1920} if episode.get("aspect_ratio", "9:16") == "9:16" else {"width": 1920, "height": 1080},
        "duration_seconds": round(cursor, 3),
        "summary": {
            "scene_count": len({x["scene_id"] for x in picture if x["scene_id"]}) or len(picture),
            "shot_count": len(picture),
            "transition_count": 0,
            "real_video_scene_count": real_video_count,
            "fallback_scene_count": fallback_count,
            "audio_clip_count": len(audio_children),
            "subtitle_count": int(_number(audio_assets.get("subtitle_count"), 0)),
        },
        "tracks": [
            {"track_id": "picture", "track_type": "video", "children": picture},
            {"track_id": "dialogue_audio", "track_type": "audio", "children": audio_children},
        ],
        "transitions": [],
        "scene_index": scene_index,
        "final_video": os.path.abspath(final_video) if final_video else None,
        "subtitles": subtitle_asset,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    fd, temp_path = tempfile.mkstemp(prefix=".canonical-timeline-", suffix=".tmp",
                                     dir=os.path.dirname(os.path.abspath(output_path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, output_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return {"success": True, "path": os.path.abspath(output_path), "timeline": timeline}
