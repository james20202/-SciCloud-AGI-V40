import os, shutil, subprocess
from core.adapters.base import BaseAdapter, AdapterResult

class TTSCommandAdapter(BaseAdapter):
    key='tts_command'
    def test(self, model):
        cmd=(model.get('command') or '').strip()
        if not cmd: return AdapterResult(False,'尚未配置 TTS command')
        return AdapterResult(bool(shutil.which(cmd.split()[0])), f'TTS command: {cmd}')
    def execute(self, model, task, context):
        cmd=task.get('command') or context.get('command') or model.get('command')
        if not cmd: return AdapterResult(False,'未配置 TTS command，未执行。')
        if isinstance(cmd,str): cmd=cmd.split()
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=int(task.get('timeout',900)))
            return AdapterResult(p.returncode==0,'TTS 执行成功' if p.returncode==0 else 'TTS 执行失败',data={'stdout':p.stdout[-2000:],'stderr':p.stderr[-4000:]})
        except Exception as e: return AdapterResult(False,f'TTS 异常：{e}')
