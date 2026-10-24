import os, json, shutil, subprocess
from core.config import OUTPUT_DIR, PROJECT_DIR


class LocalMediaEngine:
    """Local FFmpeg operations with strict input/output verification."""

    def _run(self, command, timeout=1800):
        if not command or not isinstance(command, list):
            return {'success': False, 'message': 'command 必须是参数列表'}
        if not shutil.which(command[0]):
            return {'success': False, 'message': f'找不到可执行文件：{command[0]}'}
        try:
            p = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            return {
                'success': p.returncode == 0,
                'message': '执行成功' if p.returncode == 0 else '执行失败',
                'stdout': p.stdout[-4000:],
                'stderr': p.stderr[-4000:],
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'message': f'媒体任务超时（{timeout} 秒）'}
        except Exception as e:
            return {'success': False, 'message': f'执行异常：{e}'}

    def _verified_output(self, result, output):
        result['output'] = output
        result['success'] = bool(
            result.get('success') and os.path.isfile(output) and os.path.getsize(output) > 0
        )
        if not result['success'] and not result.get('message'):
            result['message'] = '输出文件不存在或为空，未登记为成功。'
        return result

    def probe(self, path):
        if not path or not os.path.isfile(path):
            return {'success': False, 'message': '媒体文件不存在'}
        r = self._run([
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration,size,format_name:stream=codec_type,codec_name,width,height', '-of', 'json', path
        ], 60)
        if r['success']:
            try:
                data = json.loads(r['stdout'])
                fmt = data.get('format') or {}
                duration = float(fmt.get('duration') or 0)
                size = int(fmt.get('size') or 0)
                if duration <= 0 or size <= 0:
                    return {'success': False, 'message': '媒体探测失败：时长或文件大小无效', 'data': data}
                r['data'] = data
                r['duration_seconds'] = duration
                r['size_bytes'] = size
            except (ValueError, TypeError, json.JSONDecodeError):
                return {'success': False, 'message': 'ffprobe 返回的媒体信息无法解析'}
        return r

    def image_to_video(self, image, output, duration_seconds=5, fps=24, width=1080, height=1920):
        """Create a real H.264 MP4 clip from a still image for dynamic-comic fallback."""
        if not image or not os.path.isfile(image) or os.path.getsize(image) <= 0:
            return {'success': False, 'message': '分镜图片不存在或为空，无法生成镜头视频'}
        try:
            duration = float(duration_seconds)
            fps = int(fps)
            width, height = int(width), int(height)
        except (TypeError, ValueError):
            return {'success': False, 'message': '镜头时长、帧率或画面尺寸无效'}
        if duration <= 0 or duration > 3600 or fps < 1 or fps > 60 or width < 2 or height < 2:
            return {'success': False, 'message': '镜头参数超出允许范围'}
        width -= width % 2
        height -= height % 2
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
        r = self._run([
            'ffmpeg', '-y', '-loop', '1', '-framerate', str(fps), '-i', image,
            '-t', str(duration), '-vf', vf, '-r', str(fps),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
            '-an', '-movflags', '+faststart', output
        ], 900)
        r = self._verified_output(r, output)
        if r['success']:
            r['duration_seconds'] = duration
            r['fps'] = fps
            r['source_image'] = os.path.abspath(image)
        return r

    def concat_videos(self, inputs, output, transition=None):
        inputs = list(inputs or [])
        if not inputs:
            return {'success': False, 'message': '没有可拼接的视频文件'}
        missing = [p for p in inputs if not p or not os.path.isfile(p) or os.path.getsize(p) <= 0]
        if missing:
            return {'success': False, 'message': f'有 {len(missing)} 个视频输入不存在或为空；拒绝静默跳过素材。', 'missing': missing}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        if len(inputs) == 1:
            r = self._run(['ffmpeg', '-y', '-i', inputs[0], '-c', 'copy', '-movflags', '+faststart', output], 1800)
            return self._verified_output(r, output)

        manifest = output + '.concat.txt'
        try:
            with open(manifest, 'w', encoding='utf-8') as f:
                f.write('ffconcat version 1.0\n')
                for p in inputs:
                    escaped = os.path.abspath(p).replace("\\", "\\\\").replace("'", "\\'")
                    f.write("file '" + escaped + "'\n")
            # Fast path: stream copy when all clips share compatible streams.
            fast = self._run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', manifest,
                              '-c', 'copy', '-movflags', '+faststart', output], 1800)
            if fast.get('success') and os.path.isfile(output) and os.path.getsize(output) > 0:
                fast['message'] = '视频拼接成功（无损流复制）'
                return self._verified_output(fast, output)
            # Fallback: normalize video encoding if stream-copy concatenation is incompatible.
            try:
                if os.path.exists(output):
                    os.remove(output)
            except OSError:
                pass
            fallback = self._run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', manifest,
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', output
            ], 2400)
            if fallback.get('success') and os.path.isfile(output) and os.path.getsize(output) > 0:
                fallback['message'] = '视频拼接成功（兼容编码重制）'
                return self._verified_output(fallback, output)
            fallback['message'] = '视频拼接失败：无损拼接和兼容编码重制均失败。请检查视频编码、音轨布局和 FFmpeg 日志。'
            fallback['fast_path_error'] = fast.get('stderr', '')[-1500:]
            return self._verified_output(fallback, output)
        finally:
            try:
                os.remove(manifest)
            except OSError:
                pass

    def mux_audio(self, video, audio, output):
        if not os.path.isfile(video) or not os.path.isfile(audio):
            return {'success': False, 'message': '视频或音频不存在'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        r = self._run(['ffmpeg', '-y', '-i', video, '-i', audio, '-map', '0:v:0', '-map', '1:a:0',
                       '-c:v', 'copy', '-c:a', 'aac', '-shortest', '-movflags', '+faststart', output], 1800)
        return self._verified_output(r, output)

    def burn_subtitles(self, video, subtitle, output):
        if not os.path.isfile(video) or not os.path.isfile(subtitle):
            return {'success': False, 'message': '视频或字幕文件不存在'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        sub = os.path.abspath(subtitle).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        r = self._run(['ffmpeg', '-y', '-i', video, '-vf', f"subtitles='{sub}'",
                       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                       '-c:a', 'copy', '-movflags', '+faststart', output], 1800)
        return self._verified_output(r, output)

    def normalize_audio(self, audio, output):
        if not os.path.isfile(audio):
            return {'success': False, 'message': '音频不存在'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        r = self._run(['ffmpeg', '-y', '-i', audio, '-af', 'loudnorm', '-c:a', 'aac', output], 900)
        return self._verified_output(r, output)

    def export_mp4(self, video, output, crf='20'):
        if not os.path.isfile(video) or os.path.getsize(video) <= 0:
            return {'success': False, 'message': '输入视频不存在或为空'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        r = self._run(['ffmpeg', '-y', '-i', video, '-c:v', 'libx264', '-preset', 'medium',
                       '-crf', str(crf), '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                       '-movflags', '+faststart', output], 1800)
        return self._verified_output(r, output)


local_media_engine = LocalMediaEngine()
