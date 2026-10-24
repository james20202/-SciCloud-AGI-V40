import os, json, uuid
from datetime import datetime
from core.config import OUTPUT_DIR, PROJECT_DIR
from core.model_hub import model_hub
from core.local_media_engine import local_media_engine
from core.subtitle_engine import subtitle_engine
from core.adapters import ComfyUIAdapter, TTSCommandAdapter

class ProductionEngine:
    """Orchestrates local generation and media operations; outputs must exist on disk."""
    def __init__(self):
        self.comfy=ComfyUIAdapter(); self.tts=TTSCommandAdapter()
        self.root=os.path.join(PROJECT_DIR,'production_runs'); os.makedirs(self.root,exist_ok=True)
    def _run_dir(self, run_id):
        p=os.path.join(self.root,run_id); os.makedirs(p,exist_ok=True); return p
    def start_run(self, plan_id, title='未命名项目'):
        run_id='RUN-'+uuid.uuid4().hex[:10].upper(); p=self._run_dir(run_id)
        data={'run_id':run_id,'plan_id':plan_id,'title':title,'created_at':datetime.now().isoformat(timespec='seconds'),'status':'created','stages':[]}
        with open(os.path.join(p,'run.json'),'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        return data
    def _save(self,data):
        p=self._run_dir(data['run_id'])
        with open(os.path.join(p,'run.json'),'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        return data
    def submit_comfy(self, workflow, stage, run_id):
        model=model_hub.get('MODEL-COMFYUI')
        if not model or not model.get('enabled'): return {'success':False,'message':'ComfyUI 未启用'}
        output_dir=os.path.join(self._run_dir(run_id),'assets',stage)
        task={'workflow':workflow,'output_dir':output_dir}
        # Do not return "success" merely because the API accepted a queue item.
        r=self.comfy.render(model,task,{})
        out=r.to_dict(); out['stage']=stage; out['run_id']=run_id
        out['outputs']=[x for x in out.get('outputs',[]) if os.path.isfile(x.get('path','')) and os.path.getsize(x.get('path',''))>0]
        out['success']=bool(out.get('success') and out['outputs'])
        if not out['success'] and r.success:
            out['message']='ComfyUI 返回成功，但未产生可验证的本地媒体文件。'
        return out
    def synthesize_voice(self, command, text, output, run_id):
        model=model_hub.get('MODEL-LOCAL-TTS')
        if not model or not model.get('enabled'): return {'success':False,'message':'本地 TTS 未启用'}
        task={'command':command or model.get('command'),'text':text,'output':output}
        r=self.tts.execute(model,task,{}); out=r.to_dict(); out['output']=output; out['run_id']=run_id
        out['success']=bool(out.get('success') and os.path.isfile(output) and os.path.getsize(output)>0)
        if not out['success'] and r.success: out['message']='TTS 命令返回成功，但没有发现输出音频文件，拒绝标记为成功。'
        return out
    def create_subtitles(self, dialogue, run_id):
        out=os.path.join(self._run_dir(run_id),'subtitles.srt'); path=subtitle_engine.from_dialogue(dialogue,out)
        return {'success':bool(path),'output':path,'run_id':run_id}
    def assemble(self, videos, audio=None, subtitles=None, run_id=None):
        if not run_id: run_id='RUN-'+uuid.uuid4().hex[:10].upper()
        rd=self._run_dir(run_id); base=os.path.join(rd,'assembled.mp4')
        r=local_media_engine.concat_videos(videos,base)
        if not r['success']: return r
        current=base
        if audio:
            out=os.path.join(rd,'with_audio.mp4'); r=local_media_engine.mix_audio_with_video(current,audio,out)
            if not r['success']: return r
            current=out
        if subtitles:
            out=os.path.join(rd,'with_subtitles.mp4'); r=local_media_engine.burn_subtitles(current,subtitles,out)
            if not r['success']: return r
            current=out
        final=os.path.join(OUTPUT_DIR,f'{run_id}_final.mp4'); r=local_media_engine.export_mp4(current,final)
        r['run_id']=run_id; r['final_output']=final; return r
production_engine=ProductionEngine()
