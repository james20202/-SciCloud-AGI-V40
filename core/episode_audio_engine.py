"""Prepare time-aligned subtitles and optional genuinely synthesized local speech."""
import os
from core.subtitle_engine import subtitle_engine
from core.local_media_engine import local_media_engine
from core.local_tts_engine import local_tts_engine, strip_non_dialogue_brackets


class EpisodeAudioEngine:
    def __init__(self, tts=None):
        self.tts = tts or local_tts_engine

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
        tts_dir = os.path.join(output_dir, "tts")
        by_id = {str(s.get("shot_id")): s for s in (shot_job or {}).get("shots", [])}
        subtitle_segments, audio_inputs, tts_errors = [], [], []
        tts_status = self.tts.status()
        for record in clip_records:
            shot_id = str(record.get("shot_id") or "")
            spec = record.get("spec") or {}
            start = max(0.0, float(record.get("start_seconds", 0) or 0))
            duration = max(0.0, float(record.get("duration_seconds", 0) or 0))
            end = min(float(total_duration), start + duration)
            if end <= start:
                continue
            items = self._dialogue_items(spec.get("dialogue"))
            # Narration/voiceover is a separate canonical shot field. Previously only
            # dialogue was scheduled, so generated narration vanished before subtitles
            # and local TTS even though the storyboard preserved it.
            voiceover_items = self._dialogue_items(spec.get("voiceover", spec.get("narration")))
            for item in voiceover_items:
                item = dict(item)
                item.setdefault("speaker", "旁白")
                items.append(item)
            shot = by_id.get(shot_id, {})
            existing_audio = next((a for a in shot.get("artifacts", [])
                if a.get("kind") == "audio" and a.get("path") and os.path.isfile(a["path"])
                and os.path.getsize(a["path"]) > 0), None)
            if existing_audio:
                audio_inputs.append({"path": os.path.abspath(existing_audio["path"]),
                                     "start": start, "duration": end - start})
            cursor = start
            total_chars = sum(max(1, len(strip_non_dialogue_brackets(x.get("text", "")))) for x in items)
            for index, item in enumerate(items, 1):
                spoken = strip_non_dialogue_brackets(str(item.get("text", "")))
                if not spoken:
                    continue
                speaker = str(item.get("speaker") or item.get("character") or "").strip()
                subtitle_text = f"{speaker}：{spoken}" if speaker else spoken
                weight = max(1, len(spoken)) / max(1, total_chars)
                allocated = max(0.25, duration * weight)
                audio_path = None
                speech_duration = None
                if tts_status.get("available") and not existing_audio:
                    os.makedirs(tts_dir, exist_ok=True)
                    safe_shot = "".join(c if c.isalnum() or c in "-_" else "_" for c in shot_id)[:48] or "shot"
                    extension = ".aiff" if tts_status.get("backend") == "say" else ".wav"
                    candidate = os.path.join(tts_dir, f"{safe_shot}_{index:02d}{extension}")
                    synthesized = self.tts.synthesize(spoken, candidate)
                    if synthesized.get("success"):
                        probed = local_media_engine.probe(candidate)
                        if probed.get("success") and any(
                            s.get("codec_type") == "audio" for s in (probed.get("data") or {}).get("streams", [])
                        ):
                            audio_path = os.path.abspath(candidate)
                            speech_duration = float(probed.get("duration_seconds") or 0)
                        else:
                            tts_errors.append({"shot_id": shot_id, "message": "合成音频未通过 FFprobe 校验"})
                    else:
                        tts_errors.append({"shot_id": shot_id, "message": synthesized.get("message", "本地配音失败")})
                if audio_path and speech_duration and cursor < end:
                    available = max(0.0, end - cursor)
                    mix_duration = min(speech_duration, available)
                    if mix_duration > 0.05:
                        audio_inputs.append({"path": audio_path, "start": cursor, "duration": mix_duration})
                        subtitle_end = min(end, cursor + max(0.25, speech_duration))
                        subtitle_segments.append({"start": cursor, "end": subtitle_end, "text": subtitle_text})
                        cursor += mix_duration
                        continue
                # Captions still work when no local Chinese voice is installed.
                segment_end = min(end, cursor + allocated)
                if segment_end > cursor:
                    subtitle_segments.append({"start": cursor, "end": segment_end, "text": subtitle_text})
                    cursor = segment_end

        subtitle_path = os.path.join(output_dir, "dialogue.srt")
        written = subtitle_engine.to_srt(subtitle_segments, subtitle_path)
        if not written:
            return {"success": False, "message": "无法生成对白字幕文件"}
        audio_path = None
        if audio_inputs:
            audio_path = os.path.join(output_dir, "dialogue_mix.m4a")
            mixed = local_media_engine.mix_audio_tracks(audio_inputs, audio_path, float(total_duration))
            if not mixed.get("success"):
                return {"success": False, "message": "对白音轨混音失败", "detail": mixed,
                        "subtitle_path": os.path.abspath(subtitle_path) if subtitle_segments else None}
        return {
            "success": True,
            "subtitle_path": os.path.abspath(subtitle_path) if subtitle_segments else None,
            "subtitle_count": len(subtitle_segments),
            "audio_path": os.path.abspath(audio_path) if audio_path else None,
            "audio_clip_count": len(audio_inputs),
            "tts_backend": tts_status.get("backend") if tts_status.get("available") else None,
            "tts_status": tts_status,
            "tts_errors": tts_errors,
            "total_duration_seconds": float(total_duration),
        }


episode_audio_engine = EpisodeAudioEngine()
