import json, os, uuid
from datetime import datetime
from core.config import PROJECT_DIR
from core.production_engine import production_engine
from core.subtitle_engine import subtitle_engine
from core.local_media_engine import local_media_engine
from core.model_hub import model_hub

class ShotProductionEngine:
    """Real shot-level production coordinator. Missing capabilities are blocked, never fabricated."""
    def __init__(self):
        self.root=os.path.join(PROJECT_DIR,'shot_runs'); os.makedirs(self.root,exist_ok=True)

    def _now(self): return datetime.now().isoformat(timespec='seconds')
    def _path(self, run_id): return os.path.join(self.root, run_id+'.json')
    def _save(self, data):
        with open(self._path(data['run_id']),'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        return data

    def create_run(self, episode_id, shots):
        rid='SHOTRUN-'+uuid.uuid4().hex[:10].upper()
        data={'run_id':rid,'episode_id':episode_id,'created_at':self._now(),'updated_at':self._now(),'status':'ready','shots':[]}
        for i,s in enumerate(shots or [],1):
            sid=s.get('shot_id') or f'SHOT-{i:03d}'
            data['shots'].append({'shot_id':sid,'index':i,'spec':s,'status':'ready','attempts':0,'artifacts':[],'last_result':None})
        return self._save(data)

    def load(self, run_id):
        with open(self._path(run_id),encoding='utf-8') as f: return json.load(f)

    def _blocked(self, message, capability):
        return {'success':False,'blocked':True,'capability':capability,'message':message}

    def status(self, run_id):
        d=self.load(run_id); shots=d['shots']; total=len(shots)
        done=sum(x['status']=='done' for x in shots)
        failed=sum(x['status']=='failed' for x in shots)
        blocked=sum(x['status']=='blocked' for x in shots)
        running=sum(x['status']=='running' for x in shots)
        ready=sum(x['status']=='ready' for x in shots)
        d['progress']=round(done/total*100,1) if total else 0
        d['done_count']=done; d['failed_count']=failed; d['blocked_count']=blocked
        d['ready_count']=ready; d['remaining_count']=max(0,total-done-failed)
        if total and done==total: d['status']='completed'
        elif failed: d['status']='failed'
        elif running or ready: d['status']='running' if done or running else 'ready'
        elif blocked: d['status']='blocked'
        else: d['status']='ready'
        d['updated_at']=self._now(); return self._save(d)

    def _register(self, shot, output, kind):
        if output and os.path.isfile(output) and os.path.getsize(output)>0:
            shot['artifacts'].append({'kind':kind,'path':output,'size':os.path.getsize(output)})
            return True
        return False

    def produce_shot(self, run_id, shot_id):
        d=self.load(run_id); shot=next((x for x in d['shots'] if x['shot_id']==shot_id),None)
        if not shot: return {'success':False,'message':'找不到镜头'}
        shot['attempts']+=1; shot['status']='running'; self._save(d)
        spec=shot['spec']; result={'success':True,'steps':[]}
        image=spec.get('image_path'); video=spec.get('video_path'); audio=spec.get('audio_path')
        if image and os.path.isfile(image): self._register(shot,image,'image'); result['steps'].append('existing_image')
        elif spec.get('comfy_workflow'):
            r=production_engine.submit_comfy(spec['comfy_workflow'],'shot_image',run_id); result['steps'].append(r)
            if not r.get('success'): result['success']=False; shot['status']='blocked' if r.get('message','').find('未启用')>=0 else 'failed'
        elif not image:
            result['success']=False; result.update(self._blocked('没有镜头图片，也没有 ComfyUI workflow。','image_generation')); shot['status']='blocked'
        if result['success'] and video and os.path.isfile(video): self._register(shot,video,'video')
        elif result['success'] and spec.get('video_path_required'):
            result['success']=False; result.update(self._blocked('没有真实视频文件可供后续处理。','video_generation')); shot['status']='blocked'
        if result['success'] and audio and os.path.isfile(audio): self._register(shot,audio,'audio')
        if result['success']:
            shot['status']='done'; result['message']='镜头已有真实素材并完成登记。'
        shot['last_result']=result; self._save(d); return self.status(run_id)

    def run_ready(self, run_id, max_shots=100):
        d=self.load(run_id); count=0
        for shot in d['shots']:
            if count>=max_shots: break
            if shot['status'] in ('ready','blocked'):
                r=self.produce_shot(run_id,shot['shot_id']); count+=1
                if r.get('status')=='failed': break
        return self.status(run_id)

    def retry_blocked(self, run_id):
        d=self.load(run_id)
        for s in d['shots']:
            if s['status']=='blocked': s['status']='ready'
        return self._save(d)

shot_production_engine=ShotProductionEngine()
