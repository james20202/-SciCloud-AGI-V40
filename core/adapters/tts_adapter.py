import os, shlex, shutil, subprocess
from core.adapters.base import BaseAdapter, AdapterResult


class TTSCommandAdapter(BaseAdapter):
    key = 'tts_command'

    def test(self, model):
        cmd = (model.get('command') or '').strip()
        if not cmd:
            return AdapterResult(False, '尚未配置 TTS command')
        executable = shlex.split(cmd)[0] if shlex.split(cmd) else ''
        found = shutil.which(executable) if executable else None
        return AdapterResult(bool(found), f'TTS command: {found or "未找到可执行文件"}', data={'path': found})

    def execute(self, model, task, context):
        cmd = task.get('command') or context.get('command') or model.get('command')
        if not cmd:
            return AdapterResult(False, '未配置 TTS command，未执行。')
        try:
            args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd) if isinstance(cmd, (list, tuple)) else None
            if not args or not all(isinstance(arg, str) for arg in args):
                return AdapterResult(False, 'TTS command 必须是非空字符串或字符串参数列表。')
            if not shutil.which(args[0]):
                return AdapterResult(False, f'找不到 TTS 可执行文件：{args[0]}')

            output_path = task.get('output_path') or task.get('output_file')
            if not isinstance(output_path, str) or not output_path.strip():
                return AdapterResult(
                    False,
                    'TTS 任务缺少 output_path/output_file；为避免把“命令执行成功”误报为已生成配音，任务未完成。'
                )
            output_path = os.path.abspath(os.path.expanduser(output_path))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            args = [arg.replace('{output}', output_path) for arg in args]
            if not any('{output}' in arg for arg in (cmd if isinstance(cmd, (list, tuple)) else [])):
                # String commands have already been tokenized; check the parsed arguments
                # before replacement so ordinary CLI tools can receive an explicit path.
                if not any(arg == output_path for arg in args):
                    args.append(output_path)

            timeout = int(task.get('timeout', 900))
            if timeout <= 0 or timeout > 7200:
                return AdapterResult(False, 'TTS timeout 必须在 1 到 7200 秒之间。')
            process = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            if process.returncode != 0:
                return AdapterResult(False, 'TTS 执行失败', data={
                    'returncode': process.returncode,
                    'stdout': process.stdout[-2000:],
                    'stderr': process.stderr[-4000:],
                })
            if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 0:
                return AdapterResult(False, 'TTS 命令已退出，但指定的配音文件不存在或为空。', data={
                    'output_path': output_path,
                    'stdout': process.stdout[-2000:],
                    'stderr': process.stderr[-4000:],
                })
            return AdapterResult(True, '配音文件已生成并通过非空文件检查', outputs=[output_path], data={
                'output_path': output_path,
                'size_bytes': os.path.getsize(output_path),
                'stdout': process.stdout[-2000:],
                'stderr': process.stderr[-4000:],
            })
        except subprocess.TimeoutExpired as exc:
            return AdapterResult(False, 'TTS 执行超时', data={
                'timeout': task.get('timeout', 900),
                'stdout': str(exc.stdout or '')[-2000:],
                'stderr': str(exc.stderr or '')[-4000:],
            })
        except Exception as exc:
            return AdapterResult(False, f'TTS 异常：{exc}')
