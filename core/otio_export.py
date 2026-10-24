"""OTIO export adapter.

Portions of the time/clip helper contract are adapted from:
Comic Drama Workflow, backend/timeline_export.py
Copyright (c) 2026 Comic Drama Workflow contributors
License: MIT; see THIRD_PARTY_NOTICES.md.

Source: https://github.com/tccnnd/Comic-drama/blob/main/backend/timeline_export.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OTIO_SCHEMA_VERSION = "0.15.0"


# Adapted from Comic Drama Workflow's MIT-licensed timeline_export.py.
def _rational_time(seconds: float, rate: float = 24.0) -> dict[str, Any]:
    return {"OTIO_SCHEMA": "RationalTime.1", "value": round(seconds * rate), "rate": rate}


# Adapted from Comic Drama Workflow's MIT-licensed timeline_export.py.
def _time_range(start_seconds: float, duration_seconds: float, rate: float = 24.0) -> dict[str, Any]:
    return {
        "OTIO_SCHEMA": "TimeRange.1",
        "start_time": _rational_time(start_seconds, rate),
        "duration": _rational_time(duration_seconds, rate),
    }


# Adapted from Comic Drama Workflow's MIT-licensed timeline_export.py.
def _media_reference(path: str, duration_seconds: float, rate: float = 24.0) -> dict[str, Any]:
    if not path:
        return {"OTIO_SCHEMA": "MissingReference.1", "name": "", "available_range": None, "metadata": {}}
    return {
        "OTIO_SCHEMA": "ExternalReference.1",
        "target_url": Path(path).resolve().as_uri(),
        "available_range": _time_range(0, duration_seconds, rate),
        "metadata": {},
    }


# Adapted from Comic Drama Workflow's MIT-licensed timeline_export.py.
def _clip(name: str, duration_seconds: float, media_path: str = "",
          rate: float = 24.0, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "OTIO_SCHEMA": "Clip.2",
        "name": name,
        "source_range": _time_range(0, duration_seconds, rate),
        "media_reference": _media_reference(media_path, duration_seconds, rate),
        "metadata": metadata or {},
    }


# Adapted from Comic Drama Workflow's MIT-licensed timeline_export.py.
def _gap(duration_seconds: float, rate: float = 24.0) -> dict[str, Any]:
    return {"OTIO_SCHEMA": "Gap.1", "name": "", "source_range": _time_range(0, duration_seconds, rate)}


def export_canonical_to_otio(timeline: dict[str, Any]) -> dict[str, Any]:
    """Convert SciCloud canonical_timeline.json to an OTIO Timeline.1 object."""
    title = str(timeline.get("title") or "SciCloud Episode").strip()
    fps = float(timeline.get("frame_rate") or 24)
    total = max(0.0, float(timeline.get("duration_seconds") or 0))
    tracks = timeline.get("tracks") or []
    picture_track = next((t for t in tracks if t.get("track_type") == "video"), {})
    audio_track = next((t for t in tracks if t.get("track_type") == "audio"), {})
    pictures = sorted(picture_track.get("children", []), key=lambda x: float(x.get("start_seconds") or 0))
    audios = sorted(audio_track.get("children", []), key=lambda x: float(x.get("start_seconds") or 0))

    video_children = []
    markers = []
    for index, item in enumerate(pictures, 1):
        duration = max(0.0, float(item.get("duration_seconds") or 0))
        path = str((item.get("media_reference") or {}).get("path") or "")
        meta = item.get("metadata") or {}
        video_children.append(_clip(
            name=str(item.get("name") or item.get("shot_id") or f"Shot {index}"),
            duration_seconds=duration, media_path=path, rate=fps,
            metadata={"scicloud": {
                "shot_id": item.get("shot_id"), "scene_id": item.get("scene_id"),
                "start_seconds": float(item.get("start_seconds") or 0),
                "generation": meta.get("generation") or {},
                "visual_prompt": meta.get("visual_prompt") or "",
                "camera_movement": meta.get("camera_movement") or "",
            }},
        ))
        markers.append({
            "OTIO_SCHEMA": "Marker.2",
            "name": f"Shot {index}: {item.get('shot_id') or ''}",
            "marked_range": _time_range(float(item.get("start_seconds") or 0), 0, fps),
            "color": "GREEN",
            "metadata": {"scicloud": {"scene_id": item.get("scene_id"), "shot_id": item.get("shot_id")}},
        })

    audio_children = []
    cursor = 0.0
    for item in audios:
        start = max(cursor, float(item.get("start_seconds") or 0))
        duration = max(0.0, float(item.get("duration_seconds") or 0))
        if start > cursor:
            audio_children.append(_gap(start - cursor, fps))
        path = str((item.get("media_reference") or {}).get("path") or "")
        if path and duration > 0:
            audio_children.append(_clip(
                name=str(item.get("clip_id") or item.get("shot_id") or "Dialogue"),
                duration_seconds=duration, media_path=path, rate=fps,
                metadata={"scicloud": {"shot_id": item.get("shot_id"), "start_seconds": start}},
            ))
        cursor = start + duration
    if total > cursor:
        audio_children.append(_gap(total - cursor, fps))

    return {
        "OTIO_SCHEMA": "Timeline.1",
        "name": title,
        "global_start_time": _rational_time(0, fps),
        "tracks": {
            "OTIO_SCHEMA": "Stack.1", "name": "Tracks",
            "children": [
                {"OTIO_SCHEMA": "Track.1", "name": "Video", "kind": "Video",
                 "children": video_children, "markers": markers},
                {"OTIO_SCHEMA": "Track.1", "name": "Dialogue", "kind": "Audio",
                 "children": audio_children},
            ],
        },
        "metadata": {"scicloud": {
            "project_id": str(timeline.get("project_id") or ""),
            "source_schema": timeline.get("schema") or "otio-inspired",
            "shot_count": len(pictures), "duration_seconds": total,
            "otio_schema_version": OTIO_SCHEMA_VERSION,
        }},
    }


def save_otio_file(timeline: dict[str, Any], output_path: str | Path) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path.resolve())
