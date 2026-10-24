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

    def normalize_video_clip(self, source, output, duration_seconds, fps=24, width=1080, height=1920):
        """Normalize one shot to its storyboard duration and a consistent vertical frame."""
        if not source or not os.path.isfile(source) or os.path.getsize(source) <= 0:
            return {'success': False, 'message': '镜头源视频不存在或为空'}
        try:
            duration = float(duration_seconds)
            fps, width, height = int(fps), int(width), int(height)
        except (TypeError, ValueError):
            return {'success': False, 'message': '镜头标准化参数无效'}
        if duration <= 0 or duration > 3600 or fps < 1 or fps > 60 or width < 2 or height < 2:
            return {'success': False, 'message': '镜头标准化参数超出允许范围'}
        width -= width % 2
        height -= height % 2
        probe = self.probe(source)
        if not probe.get('success'):
            return {'success': False, 'message': '镜头源视频无法通过 FFprobe 校验', 'detail': probe}
        streams = (probe.get('data') or {}).get('streams', [])
        has_audio = any(s.get('codec_type') == 'audio' for s in streams)
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        vf = (f"tpad=stop_mode=clone:stop_duration={duration},trim=duration={duration},"
              f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p")
        command = ['ffmpeg', '-y', '-i', source, '-map', '0:v:0', '-vf', vf]
        if has_audio:
            command += ['-map', '0:a:0?', '-af', f'apad,atrim=duration={duration},asetpts=PTS-STARTPTS',
                        '-c:a', 'aac', '-b:a', '192k']
        else:
            command += ['-an']
        command += ['-t', str(duration), '-r', str(fps), '-c:v', 'libx264',
                    '-preset', 'veryfast', '-crf', '20', '-movflags', '+faststart', output]
        result = self._verified_output(self._run(command, 1800), output)
        if result.get('success'):
            actual = self.probe(output)
            if not actual.get('success'):
                return {'success': False, 'message': '标准化镜头生成后无法通过 FFprobe 校验', 'detail': actual}
            actual_duration = float(actual.get('duration_seconds') or 0)
            tolerance = max(0.15, 2.0 / fps)
            if abs(actual_duration - duration) > tolerance:
                return {'success': False, 'message': f'标准化镜头时长不符：目标 {duration:.3f}s，实际 {actual_duration:.3f}s'}
            result.update({'duration_seconds': actual_duration, 'target_duration_seconds': duration,
                           'source': os.path.abspath(source), 'has_audio': has_audio})
        return result

    def mix_audio_tracks(self, audio_clips, output, total_duration):
        """Place per-shot audio assets on a shared episode clock and mix them locally."""
        clips = [x for x in (audio_clips or []) if isinstance(x, dict)]
        if not clips:
            return {'success': False, 'message': '没有可混合的对白音轨'}
        try:
            total = float(total_duration)
        except (TypeError, ValueError):
            return {'success': False, 'message': '总时长无效'}
        if total <= 0 or total > 3600:
            return {'success': False, 'message': '总时长超出允许范围'}
        valid = []
        for clip in clips:
            path = clip.get('path')
            if not path or not os.path.isfile(path) or os.path.getsize(path) <= 0:
                continue
            probe = self.probe(path)
            streams = (probe.get('data') or {}).get('streams', []) if probe.get('success') else []
            if not any(s.get('codec_type') == 'audio' for s in streams):
                continue
            try:
                start = max(0.0, float(clip.get('start', 0) or 0))
                duration = float(clip.get('duration', total) or total)
            except (TypeError, ValueError):
                continue
            if start >= total or duration <= 0:
                continue
            valid.append((os.path.abspath(path), start, min(duration, total - start)))
        if not valid:
            return {'success': False, 'message': '没有可通过 FFprobe 校验的有效音轨'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        command = ['ffmpeg', '-y']
        for path, _, _ in valid:
            command += ['-i', path]
        filters = []
        labels = []
        for index, (_, start, duration) in enumerate(valid):
            delay_ms = int(round(start * 1000))
            filters.append(f'[{index}:a:0]aresample=async=1:first_pts=0,adelay={delay_ms}|{delay_ms},'
                           f'apad,atrim=duration={total},asetpts=PTS-STARTPTS[a{index}]')
            labels.append(f'[a{index}]')
        filters.append(''.join(labels) + f'amix=inputs={len(valid)}:duration=longest:'
                       f'dropout_transition=0:normalize=0,atrim=duration={total},'
                       f'asetpts=PTS-STARTPTS[aout]')
        command += ['-filter_complex', ';'.join(filters), '-map', '[aout]', '-vn',
                    '-c:a', 'aac', '-b:a', '192k', '-t', str(total), '-movflags', '+faststart', output]
        result = self._verified_output(self._run(command, 1800), output)
        if result.get('success'):
            result.update({'audio_clip_count': len(valid), 'duration_seconds': total,
                           'sources': [x[0] for x in valid]})
        return result

    def mix_audio_with_video(self, video, audio, output, total_duration=None):
        """Overlay a dialogue stem on existing shot audio without discarding it."""
        if not os.path.isfile(video) or os.path.getsize(video) <= 0:
            return {'success': False, 'message': '视频不存在或为空'}
        if not os.path.isfile(audio) or os.path.getsize(audio) <= 0:
            return {'success': False, 'message': '对白混音文件不存在或为空'}
        video_probe = self.probe(video)
        audio_probe = self.probe(audio)
        if not video_probe.get('success') or not audio_probe.get('success'):
            return {'success': False, 'message': '视频或对白混音未通过 FFprobe 校验'}
        try:
            duration = float(total_duration or video_probe.get('duration_seconds') or 0)
        except (TypeError, ValueError):
            duration = 0
        if duration <= 0:
            return {'success': False, 'message': '成片时长无效'}
        streams = (video_probe.get('data') or {}).get('streams', [])
        has_video_audio = any(s.get('codec_type') == 'audio' for s in streams)
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR, exist_ok=True)
        command = ['ffmpeg', '-y', '-i', video, '-i', audio]
        if has_video_audio:
            filter_graph = (f'[0:a:0]volume=0.75[base];[1:a:0]volume=1.0[dialogue];'
                            f'[base][dialogue]amix=inputs=2:duration=longest:'
                            f'dropout_transition=0:normalize=0,atrim=duration={duration}[aout]')
            command += ['-filter_complex', filter_graph, '-map', '0:v:0', '-map', '[aout]']
        else:
            command += ['-map', '0:v:0', '-map', '1:a:0']
        command += ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(duration),
                    '-movflags', '+faststart', output]
        return self._verified_output(self._run(command, 1800), output)

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
