import os, shutil, subprocess
from core.adapters.base import BaseAdapter, AdapterResult
from core.media_tools import find_tool
from core.config import OUTPUT_DIR

class FFmpegAdapter(BaseAdapter):
    key='ffmpeg'
    def test(self, model):
        path=model.get('command','ffmpeg') or 'ffmpeg'
        found=find_tool(path)
        return AdapterResult(bool(found), f'FFmpeg: {found or "未找到"}', data={'path':found})

    def execute(self, model, task, context):
        # V40.3 only performs concrete media commands. No fake generation.
        command=task.get('command') or context.get('command')
        if not command:
            return AdapterResult(False, 'FFmpeg 适配器需要具体 command；当前任务没有媒体命令，未执行。')
        if not isinstance(command,list):
            return AdapterResult(False, 'FFmpeg command 必须是参数列表。')
        resolved=find_tool(command[0])
        if not resolved:
            return AdapterResult(False, f'找不到可执行文件：{command[0]}')
        command=[resolved]+list(command[1:])
        os.makedirs(OUTPUT_DIR,exist_ok=True)
        try:
            p=subprocess.run(command, capture_output=True, text=True, timeout=int(task.get('timeout',1800)))
            if p.returncode==0:
                # FFmpeg normally writes its output to the final positional argument.
                # Only report it as a production artifact after verifying a non-empty file.
                candidate = command[-1] if len(command) > 1 else None
                outputs = []
                if isinstance(candidate, str) and not candidate.startswith('-') and os.path.isfile(candidate):
                    if os.path.getsize(candidate) > 0:
                        outputs = [os.path.abspath(candidate)]
                return AdapterResult(
                    True,
                    'FFmpeg 执行成功' if outputs else 'FFmpeg 命令成功，但未发现可验证的非空输出文件。',
                    outputs=outputs,
                    data={'stdout':p.stdout[-2000:], 'output_verified':bool(outputs)},
                )
            return AdapterResult(False, 'FFmpeg 执行失败', data={'stderr':p.stderr[-4000:]})
        except Exception as e:
            return AdapterResult(False, f'FFmpeg 异常：{e}')
