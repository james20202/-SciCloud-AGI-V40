"""Local media QC using ffprobe and FFmpeg's blackdetect/silencedetect filters."""
import json
import os
import re
import shutil
import subprocess


class MediaQualityEngine:
    def __init__(self, runner=None, which=None):
        self.runner = subprocess.run if runner is None else runner
        self.which = shutil.which if which is None else which

    def _run(self, command, timeout=180):
        if not self.which(command[0]):
            return {"success": False, "message": f"找不到可执行文件：{command[0]}"}
        try:
            proc = self.runner(command, capture_output=True, text=True, timeout=timeout)
            return {"success": proc.returncode == 0, "stdout": proc.stdout or "",
                    "stderr": proc.stderr or "", "returncode": proc.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "媒体质量分析超时"}
        except Exception as exc:
            return {"success": False, "message": f"媒体质量分析异常：{exc}"}

    def inspect(self, path, expected_duration=None, black_warning_seconds=1.5, silence_warning_seconds=5.0):
        if not path or not os.path.isfile(path) or os.path.getsize(path) <= 0:
            return {"success": False, "passed": False, "message": "成片文件不存在或为空", "warnings": [], "errors": ["missing_file"]}
        probe = self._run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size,format_name:stream=codec_type,codec_name,width,height,sample_rate,channels",
            "-of", "json", path
        ], 60)
        if not probe.get("success"):
            return {"success": False, "passed": False, "message": probe.get("message") or probe.get("stderr") or "ffprobe 失败",
                    "warnings": [], "errors": ["probe_failed"]}
        try:
            data = json.loads(probe["stdout"])
            fmt = data.get("format") or {}
            duration = float(fmt.get("duration") or 0)
            streams = data.get("streams") or []
        except (ValueError, TypeError, json.JSONDecodeError):
            return {"success": False, "passed": False, "message": "ffprobe 返回的数据无法解析", "warnings": [], "errors": ["invalid_probe"]}
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        errors = []
        warnings = []
        if duration <= 0:
            errors.append("invalid_duration")
        if not has_video:
            errors.append("missing_video_stream")
        if expected_duration is not None and float(expected_duration) > 0:
            tolerance = max(3.0, float(expected_duration) * 0.08)
            if abs(duration - float(expected_duration)) > tolerance:
                errors.append("duration_mismatch")
        diagnostics = {"success": False, "message": "未执行黑帧/静音检测"}
        if self.which("ffmpeg"):
            diagnostics = self._run([
                "ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vf",
                f"blackdetect=d={float(black_warning_seconds)}:pix_th=0.10:pic_th=0.98",
                "-af", f"silencedetect=n=-50dB:d={float(silence_warning_seconds)}",
                "-f", "null", "-"
            ], 300)
        log = (diagnostics.get("stderr") or "") if diagnostics.get("success") else ""
        black = [{"start": float(a), "end": float(b), "duration": float(c)}
                 for a, b, c in re.findall(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", log)]
        silence = [{"start": float(a), "end": float(b)}
                   for a, b in re.findall(r"silence_start:([\d.]+).*?silence_end:([\d.]+)", log)]
        if black:
            warnings.append({"code": "black_frames", "count": len(black), "segments": black,
                             "message": "检测到长黑帧区间；可能是有意转场，请人工复核"})
        if silence:
            warnings.append({"code": "long_silence", "count": len(silence), "segments": silence,
                             "message": "检测到长静音区间；无对白镜头可能属于正常情况"})
        if not diagnostics.get("success"):
            warnings.append({"code": "deep_scan_unavailable", "message": diagnostics.get("message") or "FFmpeg 黑帧/静音检测未能完成"})
        passed = not errors
        return {"success": passed, "passed": passed, "message": "基础媒体质检通过" if passed else "基础媒体质检未通过",
                "path": os.path.abspath(path), "size_bytes": os.path.getsize(path), "duration_seconds": duration,
                "expected_duration_seconds": expected_duration, "has_video_stream": has_video, "has_audio_stream": has_audio,
                "streams": streams, "black_segments": black, "silence_segments": silence,
                "warnings": warnings, "errors": errors, "deep_scan_success": bool(diagnostics.get("success"))}


media_quality_engine = MediaQualityEngine()
