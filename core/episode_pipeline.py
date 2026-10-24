import json, os
from datetime import datetime
from core.config import PROJECT_DIR
from core.episode_engine import episode_engine
from core.director_plan import director_plan_engine
from core.shot_production_engine import shot_production_engine
from core.production_engine import production_engine
from core.local_media_engine import local_media_engine
from core.episode_timeline import build_episode_timeline
from core.publish_pack_engine import publish_pack_engine

class EpisodePipeline:
    """Durable episode pipeline; unavailable media capabilities remain blocked."""
    STAGES = ['plan','shots','media','assemble','qc','publish']
    def __init__(self, project_dir=PROJECT_DIR):
        self.project_dir=project_dir
        self.root=os.path.join(project_dir,'episode_pipelines')
        os.makedirs(self.root,exist_ok=True)
    def _now(self): return datetime.now().isoformat(timespec='seconds')
    def _path(self,eid): return os.path.join(self.root,eid+'.json')
    def _save(self,d):
        d['updated_at']=self._now()
        with open(self._path(d['episode_id']),'w',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
        return d
    def load(self,eid):
        with open(self._path(eid),encoding='utf-8') as f: return json.load(f)
    def create(self,idea,title=None,duration=60,ratio='9:16'):
        if not str(idea or '').strip(): raise ValueError('请先填写剧情创意')
        ep=episode_engine.create_episode(idea,title,duration,ratio)
        plan=next((p for p in director_plan_engine.load_plans() if p.get('plan_id')==ep.get('plan_id')),None)
        if plan is None: raise RuntimeError(f"Director Plan {ep.get('plan_id')} was not found after episode creation")
        d={'episode_id':ep['episode_id'],'plan_id':ep['plan_id'],'workflow_id':ep['workflow_id'],'title':ep['title'],'idea':idea,'duration_seconds':int(duration),'aspect_ratio':ratio,'status':'ready','stage':'plan','stages':{x:{'status':'pending','result':None} for x in self.STAGES},'shot_run_id':None,'final_video':None,'publish_package':None,'created_at':self._now(),'updated_at':self._now()}
        d['stages']['plan']={'status':'done','result':{'plan_id':plan.get('plan_id'),'shot_count':len(plan.get('shots',[]))}}
        return self._save(d)
    def status(self,eid):
        d=self.load(eid)
        completed=[k for k,v in d['stages'].items() if v.get('status')=='done']
        blocked=[k for k,v in d['stages'].items() if v.get('status')=='blocked']
        failed=[k for k,v in d['stages'].items() if v.get('status')=='failed']
        d['completed_stages']=completed; d['blocked_stages']=blocked; d['failed_stages']=failed
        fractional=0.0
        media=d['stages'].get('media',{})
        media_result=media.get('result') or {}
        if media.get('status')=='running' and media_result.get('progress') is not None:
            fractional=max(0.0,min(1.0,float(media_result['progress'])/100.0))
        d['progress']=round((len(completed)+fractional)/len(self.STAGES)*100,1)
        d['status']='completed' if 'publish' in completed else ('blocked' if blocked else ('failed' if failed else ('running' if completed and d.get('stage') not in ('plan','shots') else ('running' if len(completed)>1 else 'ready'))))
        return self._save(d)
    def prepare_shots(self,eid):
        d=self.load(eid)
        plan=next((p for p in director_plan_engine.load_plans() if p.get('plan_id')==d['plan_id']),None)
        if not plan: return {'success':False,'message':'Director Plan 不存在'}
        if d.get('shot_run_id'): return {'success':True,'shot_run_id':d['shot_run_id'],'reused':True}
        shots=[dict(s,shot_id=s.get('shot_id') or s.get('id') or f'SHOT-{i:03d}') for i,s in enumerate(plan.get('shots',[]),1)]
        if not shots: return {'success':False,'message':'导演计划没有镜头，无法准备生产任务'}
        job=shot_production_engine.create_run(eid,shots)
        d['shot_run_id']=job['run_id']; d['stage']='shots'
        d['stages']['shots']={'status':'done','result':{'shot_run_id':job['run_id'],'shot_count':len(job['shots'])}}
        return self._save(d)
    def run_media(self,eid,max_shots=100):
        d=self.load(eid)
        if not d.get('shot_run_id'):
            prepared=self.prepare_shots(eid)
            if not prepared.get('success',True): return self._block(self.load(eid),'shots',prepared.get('message','无法准备镜头'))
            d=self.load(eid)
        r=shot_production_engine.run_ready(d['shot_run_id'],max_shots=max_shots)
        if r.get('status')=='completed': stage_status='done'
        elif r.get('status')=='failed': stage_status='failed'
        elif r.get('status')=='blocked': stage_status='blocked'
        else: stage_status='running' if r.get('remaining_count',0)>0 else 'blocked'
        d['stages']['media']={'status':stage_status,'result':r}
        d['stage']='media'
        return self.status(self._save(d)['episode_id'])
    def assemble(self,eid):
        d=self.load(eid)
        if d['stages']['media']['status']!='done':
            return self._block(d,'assemble','镜头媒体尚未全部完成')
        job=shot_production_engine.load(d['shot_run_id'])
        clips=[]; clip_records=[]
        clip_dir=os.path.join(self.project_dir,'episode_pipelines',eid,'image_clips')
        os.makedirs(clip_dir,exist_ok=True)
        for shot in sorted(job.get('shots',[]),key=lambda s:s.get('index',0)):
            artifacts=shot.get('artifacts',[])
            videos=[a for a in artifacts if a.get('kind')=='video'
                    and os.path.isfile(a.get('path','')) and os.path.getsize(a.get('path',''))>0]
            source_kind='video'
            if videos:
                path=videos[0]['path']
                spec=shot.get('spec') or {}
                probe=local_media_engine.probe(path)
                duration=probe.get('duration_seconds') if probe.get('success') else (spec.get('duration_seconds') or spec.get('duration') or 5)
            else:
                images=[a for a in artifacts if a.get('kind')=='image'
                        and os.path.isfile(a.get('path','')) and os.path.getsize(a.get('path',''))>0]
                if not images:
                    return self._block(d,'assemble',f"分镜 {shot.get('shot_id')} 缺少有效视频和图片素材")
                source_kind='image_to_video_fallback'
                spec=shot.get('spec') or {}
                duration=spec.get('duration_seconds') or spec.get('duration') or 5
                path=os.path.join(clip_dir,f"{shot.get('index',0):04d}_{shot.get('shot_id','shot')}.mp4")
                fallback_width,fallback_height=(1080,1920) if d.get('aspect_ratio','9:16')=='9:16' else (1920,1080)
                rendered=local_media_engine.image_to_video(images[0]['path'],path,duration_seconds=duration,
                                                           width=fallback_width,height=fallback_height)
                if not rendered.get('success'):
                    return self._block(d,'assemble',f"分镜 {shot.get('shot_id')} 图片转视频失败：{rendered.get('message','未知错误')}",rendered)
            # Use the director's planned duration when available, then normalize every shot
            # to one frame size/rate so the final timeline matches the target episode length.
            spec=shot.get('spec') or {}
            try:
                target_duration=float(spec.get('duration_seconds') or spec.get('duration') or duration)
            except (TypeError, ValueError):
                target_duration=float(duration or 5)
            if target_duration <= 0:
                target_duration=float(duration or 5)
            target_width,target_height=(1080,1920) if d.get('aspect_ratio','9:16')=='9:16' else (1920,1080)
            normalized_path=os.path.join(clip_dir,f"{shot.get('index',0):04d}_{shot.get('shot_id','shot')}_normalized.mp4")
            normalized=local_media_engine.normalize_video_clip(path,normalized_path,duration_seconds=target_duration,
                                                               width=target_width,height=target_height)
            if not normalized.get('success'):
                return self._block(d,'assemble',f"分镜 {shot.get('shot_id')} 时长/画幅标准化失败：{normalized.get('message','未知错误')}",normalized)
            path=normalized_path
            duration=float(normalized.get('duration_seconds') or target_duration)
            clips.append(path)
            clip_records.append({'shot_id':shot.get('shot_id'),'scene_id':spec.get('scene_id'),
                                 'path':path,'source_kind':source_kind,'duration_seconds':duration,
                                 'target_duration_seconds':target_duration,'spec':spec})
        if not clips:
            return self._block(d,'assemble','没有真实视频或可转换为视频的分镜图片')
        r=production_engine.assemble(clips,run_id='RUN-'+d['episode_id'].replace('EP-',''))
        if not r.get('success'):
            return self._block(d,'assemble',r.get('message','FFmpeg 组装失败'),r)
        d['final_video']=r.get('final_output')
        timeline_path=os.path.join(self.root,eid,'canonical_timeline.json')
        timeline_result=build_episode_timeline(d,job,clip_records,timeline_path,d['final_video'])
        r['canonical_timeline']=timeline_result.get('path')
        r['timeline_summary']=timeline_result.get('timeline',{}).get('summary',{})
        d['stages']['assemble']={'status':'done','result':r}
        d['stage']='qc'
        return self.status(self._save(d)['episode_id'])
    def qc(self,eid):
        d=self.load(eid); p=d.get('final_video')
        basic=bool(p and os.path.isfile(p) and os.path.getsize(p)>0)
        probe=local_media_engine.probe(p) if basic else {'success':False,'message':'成片文件不存在或为空'}
        expected=float(d.get('duration_seconds') or 0)
        actual=float(probe.get('duration_seconds') or 0) if probe.get('success') else 0.0
        tolerance=max(3.0,expected*0.08)
        duration_ok=bool(probe.get('success') and (expected<=0 or abs(actual-expected)<=tolerance))
        has_video_stream=bool(probe.get('success') and any(s.get('codec_type')=='video' for s in (probe.get('data') or {}).get('streams', [])))
        ok=bool(basic and probe.get('success') and has_video_stream and duration_ok)
        message='成片媒体探测通过' if ok else ('成片没有可识别的视频流' if probe.get('success') and not has_video_stream else 
            probe.get('message') if not probe.get('success') else
            f'成片时长与目标不符：目标 {expected:.1f}s，实际 {actual:.1f}s，允许误差 ±{tolerance:.1f}s')
        timeline_path=os.path.join(self.root,eid,'canonical_timeline.json')
        d['stages']['qc']={'status':'done' if ok else 'blocked','result':{
            'success':ok,'path':p,'size':os.path.getsize(p) if basic else 0,
            'probe':probe.get('data') if probe.get('success') else None,
            'duration_seconds':actual,'expected_duration_seconds':expected,
            'duration_tolerance_seconds':tolerance,'duration_ok':duration_ok,'has_video_stream':has_video_stream,
            'timeline_path':timeline_path if os.path.isfile(timeline_path) else None,
            'message':message}}
        d['stage']='publish'
        return self.status(self._save(d)['episode_id'])
    def publish(self,eid):
        d=self.load(eid)
        if d['stages']['qc']['status']!='done': return self._block(d,'publish','QC 未通过')
        r=publish_pack_engine.build(eid,d.get('final_video'))
        d['stages']['publish']={'status':'done' if r.get('success') else 'failed','result':r}; d['publish_package']=r.get('package'); d['stage']='publish'
        return self.status(self._save(d)['episode_id'])
    def run(self,eid,max_shots=100):
        d=self.status(eid)
        if d['stages']['shots']['status']!='done':
            prepared=self.prepare_shots(eid)
            if not prepared.get('success',True): return self._block(self.load(eid),'shots',prepared.get('message','无法准备镜头'))
        d=self.status(eid)
        if d['stages']['media']['status']!='done':
            d=self.run_media(eid,max_shots)
            if d['stages']['media']['status']!='done': return d
        d=self.status(eid)
        if d['stages']['assemble']['status']!='done': d=self.assemble(eid)
        if d.get('status') in ('blocked','failed'): return d
        d=self.qc(eid)
        if d.get('status') in ('blocked','failed'): return d
        return self.publish(eid)
    def _block(self,d,stage,message,detail=None):
        d['stages'][stage]={'status':'blocked','result':{'success':False,'message':message,'detail':detail}}
        d['stage']=stage
        return self.status(self._save(d)['episode_id'])

episode_pipeline=EpisodePipeline()
