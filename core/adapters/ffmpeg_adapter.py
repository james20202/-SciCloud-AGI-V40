import os, shutil, subprocess
from core.adapters.base import BaseAdapter, AdapterResult
from core.config import OUTPUT_DIR

class FFmpegAdapter(BaseAdapter):
    key='ffmpeg'
    def test(self, model):
        path=model.get('command','ffmpeg') or 'ffmpeg'
        found=shutil.which(path)
        return AdapterResult(bool(found), f'FFmpeg: {found or "未找到"}', data={'path':found})

    def execute(self, model, task, context):
        # V40.3 only performs concrete media commands. No fake generation.
        command=task.get('command') or context.get('command')
        if not command:
            return AdapterResult(False, 'FFmpeg 适配器需要具体 command；当前任务没有媒体命令，未执行。')
        if not isinstance(command,list):
            return AdapterResult(False, 'FFmpeg command 必须是参数列表。')
        if not shutil.which(command[0]):
            return AdapterResult(False, f'找不到可执行文件：{command[0]}')
        os.makedirs(OUTPUT_DIR,exist_ok=True)
        try:
            p=subprocess.run(command, capture_output=True, text=True, timeout=int(task.get('timeout',1800)))
            if p.returncode==0:
                return AdapterResult(True, 'FFmpeg 执行成功', data={'stdout':p.stdout[-2000:]})
            return AdapterResult(False, 'FFmpeg 执行失败', data={'stderr':p.stderr[-4000:]})
        except Exception as e:
            return AdapterResult(False, f'FFmpeg 异常：{e}')
