import json, os, tempfile, uuid
from datetime import datetime
from core.config import PROJECT_DIR
from core.production_engine import production_engine
from core.shot_consistency import shot_fingerprint, valid_artifacts
from core.persistent_job_store import PersistentJobStore
from core.character_reference_comfyui import bind_character_references
from core.reference_image_quality import reference_image_quality_engine
from core.shot_retry_policy import prepare_retry

_JOB_STORE_PATH = os.path.join(PROJECT_DIR, 'task_jobs.sqlite3')
_job_store = PersistentJobStore(_JOB_STORE_PATH)
_job_store.recover_interrupted_jobs()

class ShotProductionEngine:
    """Resumable shot coordinator; completed outputs are reused only if valid."""
    def __init__(self):
        self.root=os.path.join(PROJECT_DIR,'shot_runs'); os.makedirs(self.root,exist_ok=True)
    def _now(self): return datetime.now().isoformat(timespec='microseconds')
    def _path(self, run_id):
        if not isinstance(run_id, str) or not run_id.strip() or run_id in {'.', '..'}:
            raise ValueError('run_id 无效')
        if '/' in run_id or chr(92) in run_id or chr(0) in run_id:
            raise ValueError('run_id 不允许包含路径分隔符或空字符')
        return os.path.join(self.root,run_id+'.json')
    def _save(self, data):
        if any(s.get('status') == 'running' for s in data.get('shots', [])):
            data['status'] = 'running'
        data['updated_at']=self._now()
        # Keep the human-readable JSON snapshot for compatibility while making
        # SQLite the durable recovery source for task state and result payloads.
        path = self._path(data['run_id'])
        os.makedirs(self.root, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix='.shot-run-', suffix='.tmp', dir=self.root)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        _job_store[data['run_id']] = {
            'kind': 'shot_run',
            'status': data.get('status', 'ready'),
            'progress': float(data.get('progress', 0) or 0),
            'message': str(data.get('message') or ''),
            'result': data,
            'params': {'episode_id': data.get('episode_id'), 'run_id': data['run_id']},
            'error': data.get('error'),
        }
        return data
    def create_run(self, episode_id, shots):
        if not isinstance(episode_id, str) or not episode_id.strip() or episode_id in {'.', '..'}:
            raise ValueError('episode_id 无效')
        if '/' in episode_id or chr(92) in episode_id or chr(0) in episode_id:
            raise ValueError('episode_id 不允许包含路径分隔符或空字符')
        if shots is None:
            shots = []
        if not isinstance(shots, list):
            raise ValueError('shots 必须是列表')
        if any(not isinstance(item, dict) for item in shots):
            raise ValueError('每个镜头必须是对象')
        ids = []
        for i, item in enumerate(shots, 1):
            sid = item.get('shot_id') or f'SHOT-{i:03d}'
            if not isinstance(sid, str) or not sid.strip() or sid in {'.', '..'}:
                raise ValueError(f'第 {i} 个镜头的 shot_id 无效')
            if '/' in sid or chr(92) in sid or chr(0) in sid:
                raise ValueError(f'镜头 shot_id 不允许包含路径分隔符或空字符：{sid!r}')
            ids.append(sid)
        if len(set(ids)) != len(ids):
            raise ValueError('镜头 shot_id 重复，拒绝创建生产任务')
        rid='SHOTRUN-'+uuid.uuid4().hex[:10].upper()
        data={'run_id':rid,'episode_id':episode_id,'created_at':self._now(),'updated_at':self._now(),'status':'ready','shots':[]}
        for i,s in enumerate(shots,1):
            sid=s.get('shot_id') or f'SHOT-{i:03d}'
            spec=dict(s)
            data['shots'].append({'shot_id':sid,'index':i,'spec':spec,'input_fingerprint':shot_fingerprint(spec),'status':'ready','attempts':0,'artifacts':[],'last_result':None})
        return self._save(data)
    def load(self, run_id):
        # SQLite is the normal durable store, but a process can stop between
        # writing the JSON snapshot and committing the SQLite update. Compare
        # both copies so recovery never silently prefers an older state.
        record = _job_store.get(run_id)
        db_data = record.get('result') if isinstance(record, dict) else None
        file_data = None
        try:
            with open(self._path(run_id), encoding='utf-8') as f:
                candidate = json.load(f)
            if isinstance(candidate, dict):
                file_data = candidate
        except (OSError, ValueError, TypeError):
            file_data = None
        if isinstance(db_data, dict) and isinstance(file_data, dict):
            db_updated = str(db_data.get('updated_at') or '')
            file_updated = str(file_data.get('updated_at') or '')
            data = file_data if file_updated > db_updated else db_data
        elif isinstance(file_data, dict):
            data = file_data
        elif isinstance(db_data, dict):
            data = db_data
        else:
            raise FileNotFoundError(f'找不到有效的镜头生产任务记录：{run_id}')
        # SQLite startup recovery marks an interrupted outer task. Re-queue
        # in-flight shots instead of leaving a permanent fake spinner.
        if isinstance(record, dict) and record.get('status') == 'interrupted':
            for shot in data.get('shots', []):
                if shot.get('status') == 'running':
                    shot['status'] = 'ready'
                    shot['last_result'] = {
                        'success': False,
                        'message': '应用上次退出时镜头正在运行，已恢复为待处理任务。'
                    }
            data['status'] = 'ready'
            data['message'] = '检测到上次运行中断；可继续生产。'
            self._save(data)
        return data
    def _blocked(self, message, capability):
        return {'success':False,'blocked':True,'capability':capability,'message':message}
    def status(self, run_id):
        d=self.load(run_id); shots=d['shots']; total=len(shots)
        # Re-check files every time: a deleted/empty artifact must not leave a shot falsely complete.
        for shot in shots:
            shot['artifacts']=valid_artifacts(shot.get('artifacts',[]))
            current=shot_fingerprint(shot.get('spec') or {})
            # Backward compatibility: adopt fingerprints for legacy completed shots only
            # when their existing media still passes the on-disk validity check.
            if not shot.get('input_fingerprint') and shot.get('status')=='done' and shot['artifacts']:
                shot['input_fingerprint']=current
            if shot.get('input_fingerprint') != current:
                shot['input_fingerprint']=current
                shot['status']='ready'
                shot['artifacts']=[]
                shot['last_result']={'success':False,'message':'镜头输入已变化，旧缓存失效，等待重新生成。'}
            elif shot.get('status')=='done' and not shot['artifacts']:
                shot['status']='ready'
                shot['last_result']={'success':False,'message':'已完成镜头的素材文件丢失或为空，已重新加入待处理队列。'}
        done=sum(x['status']=='done' for x in shots); failed=sum(x['status']=='failed' for x in shots)
        blocked=sum(x['status']=='blocked' for x in shots); running=sum(x['status']=='running' for x in shots)
        ready=sum(x['status']=='ready' for x in shots)
        d['progress']=round(done/total*100,1) if total else 0
        d['done_count']=done; d['failed_count']=failed; d['blocked_count']=blocked
        d['ready_count']=ready; d['remaining_count']=max(0,total-done)
        d['retryable_count']=failed+blocked
        if total and done==total: d['status']='completed'
        elif running: d['status']='running'
        elif ready: d['status']='running' if done else 'ready'
        elif failed: d['status']='failed'
        elif blocked: d['status']='blocked'
        else: d['status']='ready'
        return self._save(d)
    def _register(self, shot, output, kind=None):
        path=output.get('path') if isinstance(output,dict) else output
        kind=(kind or (output.get('kind') if isinstance(output,dict) else None) or 'media')
        if path and os.path.isfile(path) and os.path.getsize(path)>0:
            absolute=os.path.abspath(path)
            if not any(a.get('path')==absolute for a in shot['artifacts']):
                shot['artifacts'].append({'kind':kind,'path':absolute,'size':os.path.getsize(absolute)})
            return True
        return False
    def produce_shot(self, run_id, shot_id):
        d=self.load(run_id); shot=next((x for x in d['shots'] if x['shot_id']==shot_id),None)
        if not shot: return {'success':False,'message':'找不到镜头'}
        shot['artifacts']=valid_artifacts(shot.get('artifacts',[]))
        fingerprint=shot_fingerprint(shot.get('spec') or {})
        if not shot.get('input_fingerprint') and shot.get('status')=='done' and shot['artifacts']:
            shot['input_fingerprint']=fingerprint
        if shot.get('input_fingerprint') != fingerprint:
            shot['input_fingerprint']=fingerprint
            shot['artifacts']=[]
            shot['status']='ready'
        elif shot.get('status')=='done' and shot['artifacts']:
            return self.status(run_id)
        shot['attempts']=int(shot.get('attempts') or 0)+1; shot['status']='running'; self._save(d)
        spec=shot['spec']; result={'success':True,'steps':[]}; image=spec.get('image_path'); video=spec.get('video_path'); audio=spec.get('audio_path')
        if image and os.path.isfile(image):
            self._register(shot,image,'image'); result['steps'].append('existing_image')
        elif spec.get('comfy_workflow'):
            r=production_engine.submit_comfy(spec['comfy_workflow'],'shot_media',run_id,character_references=spec.get('character_reference_assets',[]))
            result['steps'].append(r)
            if not r.get('success'):
                result['success']=False; shot['status']='blocked' if r.get('blocked') or '未启用' in r.get('message','') or '没有发现' in r.get('message','') else 'failed'
            else:
                for artifact in r.get('outputs',[]): self._register(shot,artifact)
        else:
            result['success']=False; result.update(self._blocked('没有镜头图片，也没有 ComfyUI API workflow。','image_generation')); shot['status']='blocked'
        if result['success'] and video and os.path.isfile(video): self._register(shot,video,'video')
        if result['success'] and audio and os.path.isfile(audio): self._register(shot,audio,'audio')
        shot['artifacts']=valid_artifacts(shot.get('artifacts',[]))
        has_video=any(a.get('kind')=='video' for a in shot['artifacts'])
        if result['success'] and spec.get('video_path_required') and not has_video:
            result['success']=False; result.update(self._blocked('本次工作流未产出真实视频文件；已有图片不能代替视频。','video_generation')); shot['status']='blocked'
        elif result['success'] and not shot['artifacts']:
            result['success']=False; result.update(self._blocked('工作流没有产生可验证的本地媒体文件。','media_output')); shot['status']='blocked'
        if result['success']:
            shot['status']='done'; result['message']='真实媒体文件已保存并登记。'
            references = spec.get('character_reference_assets') or []
            generated_images = [a.get('path') for a in shot['artifacts'] if a.get('kind') == 'image']
            checks = []
            for generated in generated_images:
                for reference in references:
                    reference_path = reference.get('path')
                    if not reference_path:
                        continue
                    checks.append(reference_image_quality_engine.compare(
                        generated, reference_path, character_name=reference.get('character_name', '')))
            if checks:
                result['reference_image_checks'] = checks
                result['reference_image_check_note'] = '仅为颜色/结构相似度启发式检查，不等同于人脸识别；请人工复核低分镜头。'
        shot['input_fingerprint']=fingerprint
        shot['last_result']=result; self._save(d); return self.status(run_id)
    def run_ready(self, run_id, max_shots=100):
        d=self.load(run_id); count=0
        for shot in d['shots']:
            if count>=max_shots: break
            if shot['status'] in ('ready','blocked','failed'):
                r=self.produce_shot(run_id,shot['shot_id']); count+=1
                if r.get('status')=='failed': break
        return self.status(run_id)
    def retry_failed_shots(self, run_id, shot_ids=None):
        """Retry only failed/blocked shots; completed shots and their outputs are untouched."""
        d = self.load(run_id)
        result = prepare_retry(d, requested_ids=shot_ids)
        self._save(result['run'])
        status = self.status(run_id)
        status['retry_count'] = result['retry_count']
        status['retry_shot_ids'] = result['retry_shot_ids']
        status['message'] = (
            f"已重新排队 {result['retry_count']} 个失败镜头；已完成镜头保留。"
            if result['retry_count'] else "没有匹配的失败/阻塞镜头，无需重试。"
        )
        return self._save(status)

    def retry_blocked(self, run_id):
        """Backward-compatible alias for retrying all failed/blocked shots."""
        return self.retry_failed_shots(run_id)
shot_production_engine=ShotProductionEngine()
