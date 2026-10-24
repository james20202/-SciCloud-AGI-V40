"""Offline text-to-speech adapters for macOS say and an optional local Piper CLI.

No model is downloaded and no cloud endpoint is contacted. A speech clip is only
registered when the selected local executable produces a non-empty file.
"""
import os
import re
import shutil
import subprocess


def strip_non_dialogue_brackets(text):
    """Keep spoken words; remove parenthetical stage/sound directions.

    Adapted from the MIT-licensed tv-series-pipeline/lib/text-control.ts.
    """
    value = (text or "").replace("\r", "").strip()
    if not value:
        return ""
    value = re.sub(r"[（(][^（()）]*[)）]", "", value)
    value = re.sub(r"\s{2,}", " ", value).strip()
    return re.sub(r"^[\s,，、:：;；…—-]+", "", value).strip()


def sanitize_dialogue_for_prompt(dialogue, speaker_name=None):
    """Describe speaking motion without leaking dialogue text into image prompts.

    Adapted from the MIT-licensed tv-series-pipeline/lib/text-control.ts.
    """
    spoken = strip_non_dialogue_brackets(dialogue)
    if not spoken:
        return ""
    pace = "a brief phrase" if len(spoken) <= 10 else ("a sentence" if len(spoken) <= 30 else "an extended speech")
    speaker = str(speaker_name or "").strip() or "character"
    return f"{speaker} is speaking {pace} with natural lip movement, mid-utterance"


def find_cjk_font():
    """Find a usable CJK subtitle font, preferring open-license font paths."""
    candidates = []
    override = os.environ.get("CJK_FONT_FILE") or os.environ.get("SUBTITLE_FONT_FILE")
    if override:
        candidates.append(override)
    home = os.path.expanduser("~")
    candidates.extend([
        os.path.join(os.getcwd(), "data", "fonts", "NotoSansCJK-Regular.otf"),
        os.path.join(os.getcwd(), "data", "fonts", "cjk.ttf"),
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/Library/Fonts/NotoSansCJKsc-Regular.otf",
        "/Library/Fonts/SourceHanSansCN-Regular.otf",
        os.path.join(home, "Library/Fonts/NotoSansCJKsc-Regular.otf"),
        os.path.join(home, "Library/Fonts/SourceHanSansCN-Regular.otf"),
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ])
    return next((p for p in candidates if p and os.path.isfile(p)), None)


class LocalTTSEngine:
    """Local-only speech synthesis; macOS 'say' first, optional Piper second."""

    def __init__(self, environ=None, which=None, run=None):
        self.environ = os.environ if environ is None else environ
        self.which = shutil.which if which is None else which
        self.run = subprocess.run if run is None else run

    def _piper_model(self):
        return str(self.environ.get("SCICLOUD_PIPER_MODEL", "")).strip()

    def _say_voice(self):
        return str(self.environ.get("SCICLOUD_TTS_VOICE", "")).strip()

    def status(self):
        backend = str(self.environ.get("SCICLOUD_TTS_BACKEND", "auto")).strip().lower()
        say_path = self.which("say")
        piper_path = self.which("piper")
        model = self._piper_model()
        if backend not in ("auto", "say", "piper", "off"):
            return {"available": False, "backend": None, "message": "SCICLOUD_TTS_BACKEND 只支持 auto/say/piper/off"}
        if backend == "off":
            return {"available": False, "backend": None, "message": "本地配音已关闭"}
        if backend in ("auto", "piper") and piper_path and model and os.path.isfile(model):
            return {"available": True, "backend": "piper", "executable": piper_path, "model": model,
                    "message": "本机 Piper 与模型文件已就绪"}
        if backend == "piper":
            return {"available": False, "backend": "piper", "message": "未找到 piper 命令或 SCICLOUD_PIPER_MODEL 模型文件"}
        if backend in ("auto", "say") and say_path:
            return {"available": True, "backend": "say", "executable": say_path,
                    "voice": self._say_voice() or None,
                    "message": "检测到 macOS say；中文发音取决于系统是否已安装中文语音"}
        return {"available": False, "backend": None,
                "message": "未发现可用的本地 TTS；可使用 macOS say 或配置本地 Piper，未调用云端服务"}

    def synthesize(self, text, output_path):
        spoken = strip_non_dialogue_brackets(text)
        if not spoken:
            return {"success": False, "message": "对白为空或只有括号内舞台指示"}
        status = self.status()
        if not status.get("available"):
            return {"success": False, "message": status.get("message", "本地 TTS 不可用")}
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        backend = status["backend"]
        try:
            if backend == "say":
                command = [status["executable"]]
                voice = self._say_voice()
                if voice:
                    command += ["-v", voice]
                command += ["-o", output_path, spoken]
                result = self.run(command, capture_output=True, text=True, timeout=300)
            else:
                command = [status["executable"], "--model", status["model"], "--output_file", output_path]
                result = self.run(command, input=spoken, capture_output=True, text=True, timeout=300)
            if getattr(result, "returncode", 1) != 0:
                return {"success": False, "backend": backend,
                        "message": (getattr(result, "stderr", "") or "本地语音合成失败")[-1500:]}
            if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 0:
                return {"success": False, "backend": backend, "message": "TTS 命令未生成有效音频文件"}
            return {"success": True, "backend": backend, "path": os.path.abspath(output_path),
                    "size_bytes": os.path.getsize(output_path), "message": "本地语音合成完成"}
        except subprocess.TimeoutExpired:
            return {"success": False, "backend": backend, "message": "本地语音合成超时"}
        except Exception as exc:
            return {"success": False, "backend": backend, "message": f"本地语音合成异常：{exc}"}


local_tts_engine = LocalTTSEngine()
