import json, os
from datetime import datetime
from core.config import PROJECT_DIR, OUTPUT_DIR
from core.local_media_engine import local_media_engine

class MediaPipeline:
    """Persistent real-media pipeline. Never fabricates successful artifacts."""
    STAGES=('image','video','tts','sound','subtitle','edit','qc')
    def __init__(self):
        self.root=os.path.join(PROJECT_DIR,'media_pipelines'); os.makedirs(self.root,exist_ok=True)
    def _path(self,pid): return os.path.join(self.root,pid+'.json')
    def _save(self,s):
        with open(self._path(s['pipeline_id']),'w',encoding='utf-8') as f: json.dump(s,f,ensure_ascii=False,indent=2)
        return s
    def create(self, episode_id, shots=None, options=None):
        shots=shots or []; options=options or {}
        pid='MEDIA-'+datetime.now().strftime('%Y%m%d%H%M%S%f')
        state={'pipeline_id':pid,'episode_id':episode_id,'created_at':datetime.now().isoformat(timespec='seconds'),'status':'ready','options':options,'shots':[],'events':[]}
        for i,shot in enumerate(shots,1):
            state['shots'].append({'shot_id':shot.get('shot_id') or f'SHOT-{i:04d}','index':i,'plan':shot,'artifacts':{},'status':'pending'})
        return self._save(state)
    def status(self,pid):
        p=self._path(pid)
        if not os.path.isfile(p): return None
        with open(p,encoding='utf-8') as f:return json.load(f)
    def _event(self,s,msg): s['events'].append({'time':datetime.now().isoformat(timespec='seconds'),'message':msg})
    def register_artifact(self,pid,shot_id,kind,path):
        s=self.status(pid)
        if not s:return {'success':False,'message':'pipeline不存在'}
        for shot in s['shots']:
            if shot['shot_id']==shot_id:
                if not os.path.isfile(path) or os.path.getsize(path)<=0:return {'success':False,'message':'真实产物不存在或为空'}
                shot['artifacts'][kind]=os.path.abspath(path); shot['status']='ready'; self._event(s,f'{shot_id}: registered {kind}')
                self._save(s); return {'success':True,'shot':shot}
        return {'success':False,'message':'shot不存在'}
    def assemble(self,pid,output=None):
        s=self.status(pid)
        if not s:return {'success':False,'message':'pipeline不存在'}
        videos=[x['artifacts'].get('video') for x in s['shots'] if x['artifacts'].get('video')]
        if not videos:return {'success':False,'blocked':True,'message':'没有真实视频产物，无法剪辑'}
        output=output or os.path.join(OUTPUT_DIR,pid+'_draft.mp4')
        r=local_media_engine.concat_videos(videos,output)
        if r.get('success'): s['final_video']=output; s['status']='assembled'; self._event(s,'assembled real video'); self._save(s)
        return r
    def add_audio(self,pid,audio,output=None):
        s=self.status(pid)
        if not s:return {'success':False,'message':'pipeline不存在'}
        if not s.get('final_video'):return {'success':False,'message':'请先assemble'}
        output=output or os.path.join(OUTPUT_DIR,pid+'_audio.mp4')
        r=local_media_engine.mux_audio(s['final_video'],audio,output)
        if r.get('success'): s['final_video']=output; self._event(s,'audio muxed'); self._save(s)
        return r
    def burn_subtitles(self,pid,subtitle,output=None):
        s=self.status(pid)
        if not s:return {'success':False,'message':'pipeline不存在'}
        if not s.get('final_video'):return {'success':False,'message':'请先assemble'}
        output=output or os.path.join(OUTPUT_DIR,pid+'_sub.mp4')
        r=local_media_engine.burn_subtitles(s['final_video'],subtitle,output)
        if r.get('success'): s['final_video']=output; self._event(s,'subtitles burned'); self._save(s)
        return r
    def export(self,pid,output=None):
        s=self.status(pid)
        if not s:return {'success':False,'message':'pipeline不存在'}
        if not s.get('final_video'):return {'success':False,'message':'没有最终视频'}
        output=output or os.path.join(OUTPUT_DIR,pid+'_final.mp4')
        r=local_media_engine.export_mp4(s['final_video'],output)
        if r.get('success'): s['final_video']=output; s['status']='done'; self._event(s,'final MP4 exported'); self._save(s)
        return r
    def validate(self,pid):
        s=self.status(pid)
        if not s:return {'success':False,'message':'pipeline不存在'}
        path=s.get('final_video')
        r=local_media_engine.probe(path) if path else {'success':False,'message':'没有最终视频'}
        r['pipeline_id']=pid; r['final_video']=path
        return r
media_pipeline=MediaPipeline()
