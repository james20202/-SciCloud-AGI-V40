import json, math, os, tempfile
from datetime import datetime
from core.config import PROJECT_DIR
from core.episode_engine import episode_engine
from core.director_plan import director_plan_engine
from core.shot_production_engine import shot_production_engine
from core.production_engine import production_engine
from core.local_media_engine import local_media_engine
from core.episode_timeline import build_episode_timeline
from core.publish_pack_engine import publish_pack_engine
from core.episode_audio_engine import episode_audio_engine
from core.otio_export import export_canonical_to_otio, save_otio_file
from core.shot_consistency import shot_consistency_engine
from core.media_quality_engine import media_quality_engine
from core.character_reference_engine import character_reference_engine
from core.script_asset_extractor import script_asset_extractor

class EpisodePipeline:
    """Durable episode pipeline; unavailable media capabilities remain blocked."""
    STAGES = ['plan','shots','media','assemble','qc','publish']
    def __init__(self, project_dir=PROJECT_DIR):
        self.project_dir=project_dir
        self.root=os.path.join(project_dir,'episode_pipelines')
        os.makedirs(self.root,exist_ok=True)
    def _now(self): return datetime.now().isoformat(timespec='seconds')
    def _path(self,eid):
        if not isinstance(eid, str) or not eid.strip() or eid in {'.', '..'}:
            raise ValueError('episode_id 无效')
        if '/' in eid or chr(92) in eid or chr(0) in eid:
            raise ValueError('episode_id 不允许包含路径分隔符或空字符')
        return os.path.join(self.root,eid+'.json')
    def _save(self,d):
        if not isinstance(d, dict) or not isinstance(d.get('episode_id'), str) or not d['episode_id'].strip():
            raise ValueError('episode_id 无效，无法保存生产流水线')
        path=self._path(d['episode_id'])
        d['updated_at']=self._now()
        fd,tmp_path=tempfile.mkstemp(prefix='.episode-pipeline-',suffix='.tmp',dir=os.path.dirname(path))
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path,path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return d
    def load(self,eid):
        with open(self._path(eid),encoding='utf-8') as f: return json.load(f)
    def create(self,idea,title=None,duration=60,ratio='9:16'):
        if not str(idea or '').strip(): raise ValueError('请先填写剧情创意')
        ep=episode_engine.create_episode(idea,title,duration,ratio)
        plan=next((p for p in director_plan_engine.load_plans() if p.get('plan_id')==ep.get('plan_id')),None)
        if plan is None: raise RuntimeError(f"Director Plan {ep.get('plan_id')} was not found after episode creation")
        asset_extraction = script_asset_extractor.extract(plan, project_id=ep['episode_id'])
        d={'episode_id':ep['episode_id'],'plan_id':ep['plan_id'],'workflow_id':ep['workflow_id'],'title':ep['title'],'idea':idea,'duration_seconds':ep.get('duration_seconds',duration),'aspect_ratio':ratio,'status':'ready','stage':'plan','stages':{x:{'status':'pending','result':None} for x in self.STAGES},'shot_run_id':None,'final_video':None,'publish_package':None,'created_at':self._now(),'updated_at':self._now()}
        d['asset_extraction']=asset_extraction
        d['stages']['plan']={'status':'done','result':{'plan_id':plan.get('plan_id'),'shot_count':len(plan.get('shots',[])),'asset_extraction':asset_extraction}}
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
    @staticmethod
    def _validate_plan_shots(plan, target_duration=None):
        """Reject malformed shot plans and duration drift before creating production state."""
        if not isinstance(plan, dict):
            raise ValueError('plan 必须是对象')
        shots = plan.get('shots')
        if not isinstance(shots, list) or not shots:
            raise ValueError('shots 必须是非空列表')
        seen = set()
        total = 0.0
        for index, shot in enumerate(shots, 1):
            if not isinstance(shot, dict):
                raise ValueError(f'第 {index} 个镜头必须是对象')
            shot_id = shot.get('shot_id') or shot.get('id')
            if not isinstance(shot_id, str) or not shot_id.strip():
                raise ValueError(f'第 {index} 个镜头缺少有效 ID')
            if shot_id in seen:
                raise ValueError(f'镜头 ID 重复：{shot_id}')
            seen.add(shot_id)
            raw_duration = shot.get('duration_seconds', shot.get('duration', 5))
            try:
                duration = float(raw_duration)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f'镜头 {shot_id} 时长无效') from exc
            if not math.isfinite(duration) or duration <= 0 or duration > 3600:
                raise ValueError(f'镜头 {shot_id} 时长必须是有限正数且不超过 3600 秒')
            total += duration
        if not math.isfinite(total):
            raise ValueError('镜头总时长不是有限数值')
        if target_duration is not None:
            try:
                target = float(target_duration)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError('剧集目标时长无效') from exc
            if not math.isfinite(target) or target <= 0:
                raise ValueError('剧集目标时长必须是有限正数')
            tolerance = max(0.1, target * 0.005)
            if abs(total - target) > tolerance:
                raise ValueError(
                    f'镜头总时长 {total:.3f}s 与目标 {target:.3f}s 不匹配，'
                    f'允许误差 ±{tolerance:.3f}s'
                )
        return {'shot_count': len(shots), 'planned_duration_seconds': round(total, 3)}

    def prepare_shots(self,eid):
        d=self.load(eid)
        plan=next((p for p in director_plan_engine.load_plans() if p.get('plan_id')==d['plan_id']),None)
        if not plan: return {'success':False,'message':'Director Plan 不存在'}
        if d.get('shot_run_id'): return {'success':True,'shot_run_id':d['shot_run_id'],'reused':True}
        # Validate the director plan before persisting a resumable media job.
        # This catches duration drift before expensive generation begins.
        try:
            self._validate_plan_shots(plan, d.get('duration_seconds'))
        except ValueError as exc:
            return {'success':False,'message':f'导演计划镜头契约校验失败：{exc}'}
        bible=shot_consistency_engine.build_bible(plan)
        shots=[]
        for i, original in enumerate(plan.get('shots',[]),1):
            shot=dict(original,shot_id=original.get('shot_id') or original.get('id') or f'SHOT-{i:03d}')
            enriched=shot_consistency_engine.enrich_shot(shot,bible)
            enriched=character_reference_engine.bind_shot_references(enriched,project_id=eid)
            shots.append(enriched)
        if not shots: return {'success':False,'message':'导演计划没有镜头，无法准备生产任务'}
        job=shot_production_engine.create_run(eid,shots)
        d['shot_run_id']=job['run_id']; d['stage']='shots'
        reference_audit=character_reference_engine.audit(job['shots'])
        d['stages']['shots']={'status':'done','result':{'shot_run_id':job['run_id'],'shot_count':len(job['shots']),'character_reference_audit':reference_audit}}
        return self._save(d)
    def refresh_character_references(self,eid):
        """Rebind latest character reference assets; changed bindings invalidate shot caches."""
        d=self.load(eid)
        run_id=d.get('shot_run_id')
        if not run_id:
            return {'success':True,'reused':False,'message':'镜头任务尚未准备，后续准备时会绑定参考图'}
        job=shot_production_engine.load(run_id)
        for shot in job.get('shots',[]):
            spec=shot.get('spec') or {}
            shot['spec']=character_reference_engine.bind_shot_references(spec,project_id=eid)
        shot_production_engine._save(job)
        refreshed=shot_production_engine.status(run_id)
        audit=character_reference_engine.audit([x.get('spec') or {} for x in refreshed.get('shots',[])])
        d.setdefault('stages', {}).setdefault('shots', {}).setdefault('result', {})['character_reference_audit']=audit
        self._save(d)
        return {'success':True,'run_id':run_id,'audit':audit,'status':refreshed.get('status')}

    def run_media(self,eid,max_shots=100):
        d=self.load(eid)
        if not d.get('shot_run_id'):
            prepared=self.prepare_shots(eid)
            if not prepared.get('success',True): return self._block(self.load(eid),'shots',prepared.get('message','无法准备镜头'))
            d=self.load(eid)
        self.refresh_character_references(eid)
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
            start_seconds=round(sum(float(x.get('duration_seconds') or 0) for x in clip_records),3)
            clips.append(path)
            clip_records.append({'shot_id':shot.get('shot_id'),'scene_id':spec.get('scene_id'),
                                 'path':path,'source_kind':source_kind,'duration_seconds':duration,
                                 'target_duration_seconds':target_duration,'start_seconds':start_seconds,'spec':spec})
        if not clips:
            return self._block(d,'assemble','没有真实视频或可转换为视频的分镜图片')
        total_duration=sum(float(x.get('duration_seconds') or 0) for x in clip_records)
        expected_raw=d.get('duration_seconds')
        if expected_raw is not None:
            try:
                expected_duration=float(expected_raw)
            except (TypeError, ValueError, OverflowError):
                return self._block(d,'assemble','剧集目标时长无效，拒绝生成成片')
            if not math.isfinite(expected_duration) or expected_duration <= 0:
                return self._block(d,'assemble','剧集目标时长必须是有限正数，拒绝生成成片')
            tolerance=max(3.0,expected_duration*0.08)
            if not math.isfinite(total_duration) or abs(total_duration-expected_duration)>tolerance:
                return self._block(
                    d,'assemble',
                    f'镜头时长合计与剧集目标不匹配：目标 {expected_duration:.1f}s，镜头合计 {total_duration:.1f}s，允许误差 ±{tolerance:.1f}s',
                    {'expected_duration_seconds':expected_duration,'actual_duration_seconds':total_duration,
                     'tolerance_seconds':tolerance,'shot_count':len(clip_records)}
                )
        audio_assets=episode_audio_engine.prepare(job,clip_records,os.path.join(self.root,eid,'audio'),total_duration)
        if not audio_assets.get('success'):
            return self._block(d,'assemble',audio_assets.get('message','对白/字幕准备失败'),audio_assets)
        r=production_engine.assemble(clips,audio=audio_assets.get('audio_path'),
                                     subtitles=audio_assets.get('subtitle_path'),
                                     run_id='RUN-'+d['episode_id'].replace('EP-',''))
        if not r.get('success'):
            return self._block(d,'assemble',r.get('message','FFmpeg 组装失败'),r)
        r['dialogue_audio']=audio_assets.get('audio_path')
        r['subtitle_file']=audio_assets.get('subtitle_path')
        r['subtitle_count']=audio_assets.get('subtitle_count',0)
        r['audio_clip_count']=audio_assets.get('audio_clip_count',0)
        d['subtitle_path']=audio_assets.get('subtitle_path')
        d['final_video']=r.get('final_output')
        timeline_path=os.path.join(self.root,eid,'canonical_timeline.json')
        timeline_result=build_episode_timeline(d,job,clip_records,timeline_path,d['final_video'])
        r['canonical_timeline']=timeline_result.get('path')
        r['timeline_summary']=timeline_result.get('timeline',{}).get('summary',{})
        otio_path=os.path.join(self.root,eid,'canonical_timeline.otio')
        otio_data=export_canonical_to_otio(timeline_result.get('timeline') or {})
        r['otio_timeline']=save_otio_file(otio_data,otio_path)
        d['stages']['assemble']={'status':'done','result':r}
        d['stage']='qc'
        return self.status(self._save(d)['episode_id'])
    def qc(self,eid):
        d=self.load(eid); p=d.get('final_video')
        expected=float(d.get('duration_seconds') or 0)
        report=media_quality_engine.inspect(p,expected_duration=expected)
        basic=bool(p and os.path.isfile(p) and os.path.getsize(p)>0)
        probe=local_media_engine.probe(p) if basic else {'success':False,'message':'成片文件不存在或为空'}
        actual=float(report.get('duration_seconds') or probe.get('duration_seconds') or 0)
        tolerance=max(3.0,expected*0.08)
        duration_ok=bool(probe.get('success') and (expected<=0 or abs(actual-expected)<=tolerance))
        has_video_stream=bool(report.get('has_video_stream') or (probe.get('success') and any(
            s.get('codec_type')=='video' for s in (probe.get('data') or {}).get('streams', []))))
        ok=bool(basic and probe.get('success') and has_video_stream and duration_ok and report.get('passed',False))
        message='基础媒体质检通过' if ok else (
            report.get('message') if not report.get('passed',False) else
            ('成片没有可识别的视频流' if not has_video_stream else
             f'成片时长与目标不符：目标 {expected:.1f}s，实际 {actual:.1f}s，允许误差 ±{tolerance:.1f}s'))
        timeline_path=os.path.join(self.root,eid,'canonical_timeline.json')
        d['stages']['qc']={'status':'done' if ok else 'blocked','result':{
            'success':ok,'path':p,'size':os.path.getsize(p) if basic else 0,
            'probe':probe.get('data') if probe.get('success') else None,
            'duration_seconds':actual,'expected_duration_seconds':expected,
            'duration_tolerance_seconds':tolerance,'duration_ok':duration_ok,'has_video_stream':has_video_stream,
            'timeline_path':timeline_path if os.path.isfile(timeline_path) else None,
            'quality_report':report,'warnings':report.get('warnings',[]),'errors':report.get('errors',[]),
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
