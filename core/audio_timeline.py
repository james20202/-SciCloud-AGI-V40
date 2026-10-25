"""Lightweight audio/subtitle timeline derived from SciCloud's canonical shot contract.

No model downloads or new runtime dependencies. Times are planned shot boundaries, not
claimed word-level speech alignment; real TTS/transcription durations should override them.
"""
from __future__ import annotations

from typing import Any, Iterable

from core.shot_contract import normalize_shots


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{millis:03d}"


def build_audio_timeline(shots: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build deterministic per-shot audio ranges and a non-overlapping subtitle draft."""
    canonical = normalize_shots(list(shots))
    cursor = 0.0
    segments = []
    cues = []
    for shot in canonical:
        duration = float(shot["duration"])
        start = round(cursor, 3)
        end = round(cursor + duration, 3)
        dialogue = shot.get("dialogue", "")
        voiceover = shot.get("voiceover", "")
        # Normalize optional text defensively so malformed upstream payloads do not
        # crash an otherwise valid timeline build.
        if not isinstance(dialogue, str):
            dialogue = ""
        if not isinstance(voiceover, str):
            voiceover = ""
        segments.append({
            "shot_id": shot["shot_id"],
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": duration,
            "dialogue": dialogue,
            "voiceover": voiceover,
            "character_ids": list(shot.get("character_ids", [])),
        })
        # Keep the subtitle draft readable: prefer spoken dialogue; use voiceover
        # only when dialogue is absent. The full voiceover remains in the audio track.
        text = dialogue.strip() if dialogue.strip() else voiceover.strip()
        if text:
            cues.append({
                "index": len(cues) + 1,
                "shot_id": shot["shot_id"],
                "start_seconds": start,
                "end_seconds": end,
                "text": text,
                "source": "dialogue" if dialogue.strip() else "voiceover",
            })
        cursor = end
    total = round(cursor, 3)
    return {
        "schema_version": 1,
        "timebase": "seconds",
        "timing_source": "planned_shot_durations",
        "requires_audio_alignment": True,
        "shot_count": len(canonical),
        "total_duration_seconds": total,
        "segments": segments,
        "subtitle_cues": cues,
    }


def render_srt(timeline: dict[str, Any]) -> str:
    """Render timeline subtitle cues as SRT; does not claim word-level alignment."""
    if not isinstance(timeline, dict) or not isinstance(timeline.get("subtitle_cues"), list):
        raise ValueError("timeline.subtitle_cues 必须是列表")
    blocks = []
    previous_end = -1.0
    for index, cue in enumerate(timeline["subtitle_cues"], start=1):
        if not isinstance(cue, dict):
            raise ValueError("subtitle cue 必须是对象")
        try:
            start = float(cue["start_seconds"])
            end = float(cue["end_seconds"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("字幕起止时间无效") from exc
        text = cue.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("字幕文本不能为空")
        if start < 0 or end <= start:
            raise ValueError("字幕结束时间必须大于起始时间且起始时间不能小于 0")
        if start < previous_end - 0.001:
            raise ValueError("SRT 字幕时间不能重叠；请先合并或重排字幕")
        blocks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{text.strip()}")
        previous_end = end
    return "\n\n".join(blocks) + ("\n" if blocks else "")
