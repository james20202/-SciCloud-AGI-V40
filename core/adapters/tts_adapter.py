import os, shlex, shutil, subprocess
from core.media_tools import find_tool
from core.adapters.base import BaseAdapter, AdapterResult


class TTSCommandAdapter(BaseAdapter):
    key = 'tts_command'

    def test(self, model):
        cmd = (model.get('command') or '').strip()
        if not cmd:
            return AdapterResult(False, '尚未配置 TTS command')
        executable = shlex.split(cmd)[0] if shlex.split(cmd) else ''
        found = find_tool(executable) if executable else None
        return AdapterResult(bool(found), f'TTS command: {found or "未找到可执行文件"}', data={'path': found})

    def execute(self, model, task, context):
        cmd = task.get('command') or context.get('command') or model.get('command')
        if not cmd:
            return AdapterResult(False, '未配置 TTS command，未执行。')
        try:
            args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd) if isinstance(cmd, (list, tuple)) else None
            if not args or not all(isinstance(arg, str) for arg in args):
                return AdapterResult(False, 'TTS command 必须是非空字符串或字符串参数列表。')
            if not find_tool(args[0]):
                return AdapterResult(False, f'找不到 TTS 可执行文件：{args[0]}')

            text_input = task.get('text') or task.get('input_text') or task.get('script')
            has_text_placeholder = any('{text}' in arg for arg in args)
            if has_text_placeholder and (not isinstance(text_input, str) or not text_input.strip()):
                return AdapterResult(False, 'TTS 命令使用了 {text}，但任务没有可朗读文本。')
            if isinstance(text_input, str) and text_input.strip() and not has_text_placeholder:
                return AdapterResult(False, 'TTS 任务已有朗读文本，但命令未包含 {text}；拒绝生成空内容配音。')

            output_path = task.get('output_path') or task.get('output_file')
            if not isinstance(output_path, str) or not output_path.strip():
                return AdapterResult(
                    False,
                    'TTS 任务缺少 output_path/output_file；为避免把“命令执行成功”误报为已生成配音，任务未完成。'
                )
            output_path = os.path.abspath(os.path.expanduser(output_path))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            has_output_placeholder = any('{output}' in arg for arg in args)
            args = [arg.replace('{output}', output_path).replace('{text}', text_input or '') for arg in args]
            if not has_output_placeholder and output_path not in args:
                # For simple CLI TTS tools that accept the destination as their last argument.
                args.append(output_path)

            timeout = int(task.get('timeout', 900))
            if timeout <= 0 or timeout > 7200:
                return AdapterResult(False, 'TTS timeout 必须在 1 到 7200 秒之间。')
            # macOS say cannot write .wav directly ("Opening output file failed: fmt?").
            # Only for say + .wav: write a native .aiff first, then convert with FFmpeg.
            # All other commands keep their original behaviour.
            is_say_wav = os.path.basename(args[0]) == 'say' and output_path.lower().endswith('.wav')
            if is_say_wav:
                aiff_path = output_path[:-4] + '.aiff'
                say_args = [aiff_path if arg == output_path else arg for arg in args]
                say_process = subprocess.run(say_args, capture_output=True, text=True, timeout=timeout)
                if say_process.returncode != 0:
                    return AdapterResult(False, 'TTS 执行失败', data={
                        'returncode': say_process.returncode,
                        'stdout': say_process.stdout[-2000:],
                        'stderr': say_process.stderr[-4000:],
                    })
                ffmpeg = find_tool('ffmpeg')
                if not ffmpeg:
                    return AdapterResult(False, 'say 已生成 .aiff，但未找到 FFmpeg，无法转为 .wav。')
                convert_process = subprocess.run(
                    [ffmpeg, '-y', '-i', aiff_path, '-c:a', 'pcm_s16le', output_path],
                    capture_output=True, text=True, timeout=timeout)
                try:
                    if os.path.isfile(aiff_path):
                        os.remove(aiff_path)
                except OSError:
                    pass
                if convert_process.returncode != 0:
                    return AdapterResult(False, 'TTS .aiff 转 .wav 失败', data={
                        'returncode': convert_process.returncode,
                        'stdout': convert_process.stdout[-2000:],
                        'stderr': convert_process.stderr[-4000:],
                    })
                process = convert_process
            else:
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
