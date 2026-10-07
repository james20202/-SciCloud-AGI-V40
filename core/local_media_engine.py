import os, json, shutil, subprocess
from datetime import datetime
from core.config import OUTPUT_DIR, PROJECT_DIR

class LocalMediaEngine:
    """Real local media operations. Never reports success unless an output file exists."""
    def _run(self, command, timeout=1800):
        if not command or not isinstance(command, list): return {'success':False,'message':'command 必须是参数列表'}
        if not shutil.which(command[0]): return {'success':False,'message':f'找不到可执行文件：{command[0]}'}
        try:
            p=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
            return {'success':p.returncode==0,'message':'执行成功' if p.returncode==0 else '执行失败','stdout':p.stdout[-4000:],'stderr':p.stderr[-4000:]}
        except Exception as e: return {'success':False,'message':f'执行异常：{e}'}

    def probe(self, path):
        if not path or not os.path.isfile(path): return {'success':False,'message':'媒体文件不存在'}
        r=self._run(['ffprobe','-v','error','-show_entries','format=duration,size,format_name','-of','json',path],60)
        if r['success']:
            try: r['data']=json.loads(r['stdout'])
            except Exception: pass
        return r

    def concat_videos(self, inputs, output, transition=None):
        inputs=[p for p in inputs if os.path.isfile(p)]
        if not inputs: return {'success':False,'message':'没有可拼接的视频文件'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR,exist_ok=True)
        if len(inputs)==1:
            cmd=['ffmpeg','-y','-i',inputs[0],'-c','copy',output]
        else:
            # concat demuxer avoids re-encoding when codecs match; fallback can be done by caller.
            manifest=output+'.concat.txt'
            with open(manifest,'w',encoding='utf-8') as f:
                for p in inputs: f.write("file '"+os.path.abspath(p).replace("'","'\\''")+"'\n")
            cmd=['ffmpeg','-y','-f','concat','-safe','0','-i',manifest,'-c','copy',output]
        r=self._run(cmd,1800); r['output']=output
        r['success']=bool(r['success'] and os.path.isfile(output) and os.path.getsize(output)>0)
        return r

    def mux_audio(self, video, audio, output):
        if not os.path.isfile(video) or not os.path.isfile(audio): return {'success':False,'message':'视频或音频不存在'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR,exist_ok=True)
        r=self._run(['ffmpeg','-y','-i',video,'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-shortest',output],1800)
        r['output']=output; r['success']=bool(r['success'] and os.path.isfile(output) and os.path.getsize(output)>0); return r

    def burn_subtitles(self, video, subtitle, output):
        if not os.path.isfile(video) or not os.path.isfile(subtitle): return {'success':False,'message':'视频或字幕文件不存在'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR,exist_ok=True)
        # ffmpeg subtitles filter; escape path for filter syntax.
        sub=os.path.abspath(subtitle).replace('\\','/').replace(':','\\:').replace("'","\\'")
        r=self._run(['ffmpeg','-y','-i',video,'-vf',f"subtitles='{sub}'",'-c:a','copy',output],1800)
        r['output']=output; r['success']=bool(r['success'] and os.path.isfile(output) and os.path.getsize(output)>0); return r

    def normalize_audio(self, audio, output):
        if not os.path.isfile(audio): return {'success':False,'message':'音频不存在'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR,exist_ok=True)
        r=self._run(['ffmpeg','-y','-i',audio,'-af','loudnorm','-c:a','aac',output],900)
        r['output']=output; r['success']=bool(r['success'] and os.path.isfile(output) and os.path.getsize(output)>0); return r

    def export_mp4(self, video, output, crf='20'):
        if not os.path.isfile(video): return {'success':False,'message':'输入视频不存在'}
        os.makedirs(os.path.dirname(output) or OUTPUT_DIR,exist_ok=True)
        r=self._run(['ffmpeg','-y','-i',video,'-c:v','libx264','-preset','medium','-crf',str(crf),'-c:a','aac','-movflags','+faststart',output],1800)
        r['output']=output; r['success']=bool(r['success'] and os.path.isfile(output) and os.path.getsize(output)>0); return r

local_media_engine=LocalMediaEngine()
