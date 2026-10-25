"""Canonical episode timeline and provenance manifest.

The timeline contract is inspired by the MIT-licensed Comic-drama project:
https://github.com/tccnnd/Comic-drama (docs/canonical_timeline.md).
This module is an independent implementation adapted to SciCloud's episode schema.
"""
import json
import math
import os
from datetime import datetime


def _number(value, fallback=0.0):
    """Return a finite, non-negative timeline number.

    JSON's default encoder permits NaN and Infinity even though they are not
    valid JSON numbers. Normalize both the requested value and fallback so
    malformed model/metadata values cannot poison every subsequent timecode.
    """
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = math.nan
    if not math.isfinite(number):
        try:
            number = float(fallback)
        except (TypeError, ValueError, OverflowError):
            number = 0.0
    if not math.isfinite(number):
        number = 0.0
    return max(0.0, number)


def build_episode_timeline(episode, shot_job, clip_records, output_path, final_video=None):
    """Write a stable, inspectable timeline with real/fallback media provenance."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cursor = 0.0
    picture = []
    scene_index = []
    real_video_count = 0
    fallback_count = 0
    for order, record in enumerate(clip_records, 1):
        duration = _number(record.get("duration_seconds"), 0)
        if duration <= 0:
            spec = record.get("spec") or {}
            # Prefer the first positive finite duration, falling through when a
            # higher-priority field exists but contains NaN/Infinity/zero.
            duration = 0.0
            for candidate in (spec.get("duration_seconds"), spec.get("duration"), 5):
                candidate_duration = _number(candidate, 0)
                if candidate_duration > 0:
                    duration = candidate_duration
                    break
        source = os.path.abspath(record.get("path", ""))
        is_real_video = record.get("source_kind") == "video"
        if is_real_video:
            real_video_count += 1
        else:
            fallback_count += 1
        shot_id = str(record.get("shot_id") or f"SHOT-{order:03d}")
        scene_id = str(record.get("scene_id") or (record.get("spec") or {}).get("scene_id") or "")
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
                "visual_prompt": str((record.get("spec") or {}).get("visual_prompt") or ""),
                "camera_movement": str((record.get("spec") or {}).get("camera_movement") or ""),
            },
        }
        picture.append(clip)
        scene_index.append({"order": order, "shot_id": shot_id, "scene_id": scene_id,
                            "start_seconds": clip["start_seconds"], "end_seconds": clip["end_seconds"],
                            "path": source, "source_kind": clip["metadata"]["generation"]["source_kind"]})
        cursor += duration

    audio_children = []
    shots = (shot_job or {}).get("shots", [])
    by_id = {str(s.get("shot_id")): s for s in shots}
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
        },
        "tracks": [
            {"track_id": "picture", "track_type": "video", "children": picture},
            {"track_id": "dialogue_audio", "track_type": "audio", "children": audio_children},
        ],
        "transitions": [],
        "scene_index": scene_index,
        "final_video": os.path.abspath(final_video) if final_video else None,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2, allow_nan=False)
    return {"success": True, "path": os.path.abspath(output_path), "timeline": timeline}
