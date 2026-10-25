"""Local, deterministic motion-graphic cards for episode packaging.

Inspired by the MIT-licensed code-video-showcase project's deterministic timeline,
large-card composition and frame-count QA. This implementation is independent and
uses SciCloud's existing Pillow + FFmpeg stack; it does not require Node, Chromium,
network access, or a generative model.
"""
import os
import shutil
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont


class MotionGraphicsEngine:
    """Render simple animated title/section cards as verified local MP4 clips."""

    STYLES = {
        "xianxia": {"background": (15, 18, 35), "accent": (211, 174, 95), "foreground": (248, 243, 226)},
        "horror": {"background": (20, 12, 18), "accent": (183, 48, 61), "foreground": (246, 235, 231)},
        "modern": {"background": (13, 20, 29), "accent": (66, 190, 210), "foreground": (244, 248, 252)},
        "minimal": {"background": (18, 18, 18), "accent": (217, 119, 87), "foreground": (248, 246, 240)},
    }

    def _font(self, size, bold=False):
        candidates = (
            ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if bold else
            ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        )
        for path in candidates:
            if os.path.isfile(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except OSError:
                    pass
        return ImageFont.load_default()

    def create_card(self, title, output_image, subtitle="", aspect_ratio="9:16",
                    style="xianxia", width=None, height=None):
        """Create a local title card PNG. Existing files are atomically replaced."""
        if not str(title or "").strip():
            return {"success": False, "message": "标题卡缺少标题"}
        dimensions = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
        if aspect_ratio not in dimensions:
            return {"success": False, "message": "画幅仅支持 9:16、16:9 或 1:1"}
        default_w, default_h = dimensions[aspect_ratio]
        try:
            width, height = int(width or default_w), int(height or default_h)
        except (TypeError, ValueError):
            return {"success": False, "message": "标题卡尺寸无效"}
        if width < 160 or height < 160 or width > 3840 or height > 3840:
            return {"success": False, "message": "标题卡尺寸必须在 160–3840 像素之间"}
        width -= width % 2
        height -= height % 2
        palette = self.STYLES.get(style, self.STYLES["xianxia"])
        image = Image.new("RGB", (width, height))
        # Horizontal scanlines avoid a Python-level loop over every pixel,
        # keeping card generation responsive on low-memory Apple Silicon Macs.
        gradient = ImageDraw.Draw(image)
        top, bottom = palette["background"], tuple(max(0, c - 7) for c in palette["background"])
        for y in range(height):
            mix = y / max(1, height - 1)
            row = tuple(int(top[i] * (1 - mix) + bottom[i] * mix) for i in range(3))
            gradient.line((0, y, width, y), fill=row)
        draw = ImageDraw.Draw(image, "RGBA")
        margin = int(width * 0.075)
        accent = palette["accent"]
        # Framing lines and a restrained diagonal accent, avoiding external assets.
        draw.rounded_rectangle((margin, margin, width - margin, height - margin),
                               radius=max(12, int(width * 0.018)),
                               outline=(*accent, 150), width=max(2, width // 540))
        draw.rectangle((margin, int(height * 0.24), margin + max(8, width // 100),
                        int(height * 0.24) + int(height * 0.11)), fill=(*accent, 230))
        draw.line((margin, int(height * 0.78), width - margin, int(height * 0.78)),
                  fill=(*accent, 120), width=max(1, width // 720))
        title_font = self._font(max(28, int(min(width, height) * 0.075)), bold=True)
        subtitle_font = self._font(max(18, int(min(width, height) * 0.031)))
        safe_title = str(title).strip()[:80]
        max_text_width = width - 2 * margin - width // 12
        words = list(safe_title)
        lines, line = [], ""
        for char in words:
            candidate = line + char
            if line and draw.textbbox((0, 0), candidate, font=title_font)[2] > max_text_width:
                lines.append(line)
                line = char
            else:
                line = candidate
        if line:
            lines.append(line)
        line_height = int(title_font.size * 1.28)
        title_height = line_height * len(lines)
        y = int(height * 0.40) - title_height // 2
        for text_line in lines[:4]:
            draw.text((margin + width // 28, y), text_line, font=title_font,
                      fill=palette["foreground"], stroke_width=max(0, width // 900),
                      stroke_fill=palette["background"])
            y += line_height
        if subtitle:
            sub = str(subtitle).strip()[:120]
            max_sub_width = max_text_width
            while sub and draw.textbbox((0, 0), sub, font=subtitle_font)[2] > max_sub_width:
                sub = sub[:-1]
            draw.text((margin + width // 28, min(height - margin - subtitle_font.size * 2, y + line_height // 2)),
                      sub, font=subtitle_font, fill=(*palette["foreground"], 220))
        os.makedirs(os.path.dirname(os.path.abspath(output_image)), exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".motion-card-", suffix=".png",
                                          dir=os.path.dirname(os.path.abspath(output_image)))
        os.close(fd)
        try:
            image.save(temporary, format="PNG", optimize=True)
            if os.path.getsize(temporary) <= 0:
                raise RuntimeError("标题卡图片为空")
            os.replace(temporary, output_image)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
        return {"success": True, "path": os.path.abspath(output_image),
                "width": width, "height": height, "aspect_ratio": aspect_ratio, "style": style}

    def render_card(self, title, output_video, duration_seconds=2.0, subtitle="",
                    aspect_ratio="9:16", style="xianxia", fps=24):
        """Render a subtle zoom/fade title-card MP4 with FFmpeg and verify the output."""
        try:
            duration, fps = float(duration_seconds), int(fps)
        except (TypeError, ValueError):
            return {"success": False, "message": "卡片时长或帧率无效"}
        if not 0.25 <= duration <= 60 or not 12 <= fps <= 60:
            return {"success": False, "message": "卡片时长须为 0.25–60 秒，帧率须为 12–60"}
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return {"success": False, "message": "未找到 FFmpeg"}
        output_video = os.path.abspath(output_video)
        os.makedirs(os.path.dirname(output_video), exist_ok=True)
        fd, card_path = tempfile.mkstemp(prefix=".motion-card-", suffix=".png",
                                         dir=os.path.dirname(output_video))
        os.close(fd)
        try:
            card = self.create_card(title, card_path, subtitle, aspect_ratio, style)
            if not card.get("success"):
                return card
            width, height = card["width"], card["height"]
            fade = min(0.35, duration / 4)
            fade_out = max(0.0, duration - fade)
            vf = (f"scale={width}:{height},zoompan=z='min(zoom+0.00035,1.035)':d=1:"
                  f"s={width}x{height}:fps={fps},"
                  f"fade=t=in:st=0:d={fade:.3f},fade=t=out:st={fade_out:.3f}:d={fade:.3f},"
                  "setsar=1,format=yuv420p")
            command = [ffmpeg, "-y", "-loop", "1", "-framerate", str(fps), "-i", card_path,
                       "-t", f"{duration:.3f}", "-vf", vf, "-r", str(fps), "-an",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                       "-movflags", "+faststart", output_video]
            proc = subprocess.run(command, capture_output=True, text=True, timeout=max(120, int(duration * 30)))
            valid = proc.returncode == 0 and os.path.isfile(output_video) and os.path.getsize(output_video) > 0
            if not valid:
                return {"success": False, "message": "动效标题卡渲染失败或输出文件为空",
                        "stderr": (proc.stderr or "")[-2000:], "command": command}
            return {"success": True, "message": "动效标题卡已生成", "output": output_video,
                    "duration_seconds": duration, "fps": fps, "width": width, "height": height,
                    "size_bytes": os.path.getsize(output_video), "style": style}
        except subprocess.TimeoutExpired:
            return {"success": False, "message": "动效标题卡渲染超时"}
        except Exception as exc:
            return {"success": False, "message": f"动效标题卡异常：{exc}"}
        finally:
            if os.path.exists(card_path):
                try:
                    os.remove(card_path)
                except OSError:
                    pass


motion_graphics_engine = MotionGraphicsEngine()
