"""Build time-aligned dialogue subtitles and a local dialogue audio stem.

The output is an edit-ready sidecar; it never fabricates speech audio. Only
registered, non-empty per-shot audio artifacts are mixed into the stem.
"""
import os
from core.subtitle_engine import subtitle_engine
from core.local_media_engine import local_media_engine


class EpisodeAudioEngine:
    def _dialogue_items(self, value):
        if isinstance(value, str):
            text = value.strip()
            return [{"text": text}] if text else []
        if isinstance(value, dict):
            return [value] if str(value.get("text", "")).strip() else []
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict) and str(x.get("text", "")).strip()]
        return []

    def prepare(self, shot_job, clip_records, output_dir, total_duration):
        os.makedirs(output_dir, exist_ok=True)
        by_id = {str(s.get("shot_id")): s for s in (shot_job or {}).get("shots", [])}
        subtitle_segments = []
        audio_inputs = []
        for record in clip_records:
            shot_id = str(record.get("shot_id") or "")
            spec = record.get("spec") or {}
            start = float(record.get("start_seconds", 0) or 0)
            duration = max(0.0, float(record.get("duration_seconds", 0) or 0))
            end = min(float(total_duration), start + duration)
            for item in self._dialogue_items(spec.get("dialogue")):
                text = str(item.get("text", "")).strip()
                speaker = str(item.get("speaker") or item.get("character") or "").strip()
                if speaker and not text.startswith(speaker + "："):
                    text = f"{speaker}：{text}"
                if text and end > start:
                    subtitle_segments.append({"start": start, "end": end, "text": text})
            shot = by_id.get(shot_id, {})
            for artifact in shot.get("artifacts", []):
                path = artifact.get("path")
                if artifact.get("kind") == "audio" and path and os.path.isfile(path) and os.path.getsize(path) > 0:
                    audio_inputs.append({"path": os.path.abspath(path), "start": start, "duration": duration})
                    break

        subtitle_path = os.path.join(output_dir, "dialogue.srt")
        written = subtitle_engine.to_srt(subtitle_segments, subtitle_path)
        if not written:
            return {"success": False, "message": "无法生成对白字幕文件"}
        audio_path = None
        if audio_inputs:
            audio_path = os.path.join(output_dir, "dialogue_mix.m4a")
            mixed = local_media_engine.mix_audio_tracks(audio_inputs, audio_path, float(total_duration))
            if not mixed.get("success"):
                return {"success": False, "message": "对白音轨混音失败", "detail": mixed}
        return {
            "success": True,
            "subtitle_path": os.path.abspath(subtitle_path) if subtitle_segments else None,
            "subtitle_count": len(subtitle_segments),
            "audio_path": os.path.abspath(audio_path) if audio_path else None,
            "audio_clip_count": len(audio_inputs),
            "total_duration_seconds": float(total_duration),
        }


episode_audio_engine = EpisodeAudioEngine()
