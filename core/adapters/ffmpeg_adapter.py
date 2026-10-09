import os
import shlex
import shutil
import subprocess

from core.adapters.base import AdapterResult, BaseAdapter
from core.config import OUTPUT_DIR


class FFmpegAdapter(BaseAdapter):
    key = 'ffmpeg'

    def test(self, model):
        path = model.get('command', 'ffmpeg') or 'ffmpeg'
        found = shutil.which(path)
        return AdapterResult(bool(found), f'FFmpeg: {found or "未找到"}', data={'path': found})

    def _build_command_from_template(self, task, context=None):
        context = context or {}
        template = task.get('command_template') or task.get('template') or context.get('command_template')
        if not template:
            return None

        if isinstance(template, list):
            return template

        if not isinstance(template, dict):
            return None

        name = str(template.get('name') or template.get('type') or '').lower()
        inputs = template.get('inputs') or {}
        output = template.get('output') or inputs.get('output') or context.get('output')

        if name in {'concat','concat_video'}:
            parts = [
                'ffmpeg', '-y',
            ]
            for input_path in inputs.get('inputs') or []:
                parts.extend(['-i', str(input_path)])
            parts.extend([
                '-filter_complex',
                f"concat=n={len(inputs.get('inputs') or [])}:v=1:a=1",
                '-movflags', '+faststart',
                str(output or os.path.join(OUTPUT_DIR, 'concat_output.mp4')),
            ])
            return parts

        if name in {'trim','clip'}:
            src = inputs.get('input') or context.get('input')
            start = inputs.get('start', 0)
            duration = inputs.get('duration')
            out = output or context.get('output') or os.path.join(OUTPUT_DIR, 'trim_output.mp4')
            parts = ['ffmpeg', '-y', '-i', str(src), '-ss', str(start)]
            if duration is not None:
                parts.extend(['-t', str(duration)])
            parts.extend(['-c:v', 'libx264', '-c:a', 'aac', str(out)])
            return parts

        if name == 'subtitles':
            src = inputs.get('input') or context.get('input')
            srt = inputs.get('srt') or context.get('srt')
            out = output or context.get('output') or os.path.join(OUTPUT_DIR, 'subtitle_output.mp4')
            return ['ffmpeg', '-y', '-i', str(src), '-vf', f"subtitles={srt}", '-c:v', 'libx264', '-c:a', 'aac', str(out)]

        return None

    def execute(self, model, task, context):
        command = task.get('command') or context.get('command')
        if not command:
            command = self._build_command_from_template(task, context)
        if not command:
            return AdapterResult(False, 'FFmpeg 适配器需要具体 command；当前任务没有媒体命令，未执行。')
        if isinstance(command, str):
            command = shlex.split(command)
        if not isinstance(command, list):
            return AdapterResult(False, 'FFmpeg command 必须是参数列表。')
        if not command:
            return AdapterResult(False, 'FFmpeg command 为空，未执行。')
        if not shutil.which(command[0]):
            return AdapterResult(False, f'找不到可执行文件：{command[0]}')

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        try:
            p = subprocess.run(command, capture_output=True, text=True, timeout=int(task.get('timeout', 1800)))
            if p.returncode == 0:
                return AdapterResult(True, 'FFmpeg 执行成功', data={'stdout': p.stdout[-2000:]})
            return AdapterResult(False, 'FFmpeg 执行失败', data={'stderr': p.stderr[-4000:]})
        except Exception as exc:
            return AdapterResult(False, f'FFmpeg 异常：{exc}')
