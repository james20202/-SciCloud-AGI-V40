import json, math, os, tempfile
from datetime import datetime
from core.config import PROJECT_DIR
from core.storyboard_engine import storyboard_director

STATUS_PENDING='pending'
STATUS_READY='ready'
STATUS_RUNNING='running'
STATUS_PAUSED='paused'
STATUS_DONE='done'
STATUS_FAILED='failed'

class WorkflowEngine:
    """Persistent workflow state engine with validated plans and explicit storyboard linkage."""
    def __init__(self, project_dir=PROJECT_DIR, event_publisher=None):
        self.project_dir=project_dir
        self.workflow_dir=os.path.join(project_dir,'workflows')
        os.makedirs(self.workflow_dir,exist_ok=True)
        self.current=None
        # Optional event sink keeps the engine usable in isolation and in legacy tests.
        self.event_publisher=event_publisher
        self.last_event_error=None
        self.last_event_result=None

    def _path(self,wid):
        # Workflow IDs are used as filenames; reject traversal and path separators.
        if not isinstance(wid, str) or not wid.strip() or wid in {'.', '..'}:
            raise ValueError('workflow_id 无效')
        if '/' in wid or chr(92) in wid or chr(0) in wid:
            raise ValueError('workflow_id 不允许包含路径分隔符或空字符')
        return os.path.join(self.workflow_dir, f'{wid}.json')

    def _now(self): return datetime.now().isoformat(timespec='seconds')

    def _emit(self, event_type, wf, task=None):
        if self.event_publisher is None:
            return
        payload={'workflow_id':wf.get('workflow_id'),'plan_id':wf.get('plan_id')}
        if task is not None:
            payload.update({'task_id':task.get('id'),'task_type':task.get('type'),'task_status':task.get('status')})
        try:
            if hasattr(self.event_publisher,'publish'):
                result=self.event_publisher.publish(event_type,payload,source='workflow_engine')
            else:
                result=self.event_publisher(event_type,payload)
            self.last_event_error=None
            self.last_event_result=result
            return result
        except Exception as exc:
            # Event reporting must not roll back an already persisted production state.
            self.last_event_error=f'{event_type}: {exc}'
            self.last_event_result=None
            return None

    def create_from_plan(self, plan):
        if not isinstance(plan,dict): raise ValueError('导演计划必须是对象')
        plan_id=plan.get('plan_id')
        if not plan_id: raise ValueError('导演计划缺少 plan_id，无法创建工作流')
        raw_tasks=plan.get('tasks')
        if not isinstance(raw_tasks,list) or not raw_tasks:
            raise ValueError('导演计划缺少有效的 tasks 列表，未创建工作流')
        task_ids=[t.get('id') for t in raw_tasks if isinstance(t,dict)]
        if len(task_ids)!=len(raw_tasks) or any(not x for x in task_ids):
            raise ValueError('生产任务必须是对象且包含 id')
        if len(set(task_ids))!=len(task_ids):
            raise ValueError('生产任务 ID 重复，拒绝创建工作流')
        for t in raw_tasks:
            if not t.get('type'):
                raise ValueError(f"任务 {t['id']} 缺少 type")
        storyboard=storyboard_director.create_from_plan(plan)
        if not isinstance(storyboard, dict):
            raise RuntimeError('分镜引擎未返回有效分镜对象')
        storyboard_id=storyboard.get('storyboard_id')
        if not storyboard_id: raise RuntimeError('分镜引擎未返回 storyboard_id')
        storyboard_shots=storyboard.get('shots')
        if not isinstance(storyboard_shots, list) or not storyboard_shots:
            raise ValueError('分镜没有有效镜头，拒绝创建工作流')
        # Validate the canonical shot contract before persisting a workflow. This
        # prevents a plan with empty/malformed storyboard data from creating a
        # workflow whose downstream prompt/media stages can never succeed.
        from core.shot_contract import normalize_shots
        try:
            normalized_shots=normalize_shots(storyboard_shots)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'分镜镜头数据无效：{exc}') from exc
        if len(normalized_shots) != len(storyboard_shots):
            raise ValueError('分镜镜头数量校验失败')
        deps={
            'story':[], 'character':['story'], 'scene':['story'], 'storyboard':['character','scene'],
            'prompt':['storyboard'], 'image':['prompt'], 'video':['image'], 'voice':['story'],
            'sound':['video','voice'], 'title_card':['story'], 'edit':['video','sound','voice','title_card'], 'qc':['edit'], 'publish':['qc']
        }
        tasks=[]
        for t in raw_tasks:
            task=dict(t)
            task_type=task.get('type')
            if not task_type: raise ValueError(f"任务 {task['id']} 缺少 type")
            # The final edit artifact represents the whole episode, so carry the
            # director's duration target into media QC as an explicit contract.
            if task_type == 'edit':
                intent=plan.get('intent',{}) if isinstance(plan.get('intent'),dict) else {}
                raw_target=intent.get('duration_seconds',intent.get('target_duration_seconds'))
                if raw_target is not None:
                    try:
                        target=float(raw_target)
                        if math.isfinite(target) and target > 0:
                            task.setdefault('expected_duration_seconds',round(target,3))
                    except (TypeError,ValueError,OverflowError):
                        pass
            task['status']=STATUS_READY if not deps.get(task_type) else STATUS_PENDING
            task['progress']=0
            dependencies=list(deps.get(task_type,[]))
            # The title card is an optional packaging stage for legacy/custom plans.
            # When present, final editing waits for it; when absent, old plans remain runnable.
            if task_type == 'edit' and not any(candidate.get('type') == 'title_card' for candidate in raw_tasks):
                dependencies=[dependency for dependency in dependencies if dependency != 'title_card']
            task['depends_on']=dependencies
            task['started_at']=None; task['finished_at']=None; task['error']=None
            task['storyboard_id']=storyboard_id
            if task_type == 'title_card':
                intent=plan.get('intent',{}) if isinstance(plan.get('intent'),dict) else {}
                task.setdefault('title',plan.get('title') or '章节标题')
                task.setdefault('subtitle','片头')
                task.setdefault('duration_seconds',2.0)
                task.setdefault('aspect_ratio',intent.get('aspect_ratio','9:16'))
                task.setdefault('style','xianxia')
            tasks.append(task)
        wf={'workflow_id':'WF-'+str(plan_id).replace('PLAN-',''),'plan_id':plan_id,'title':plan.get('title','未命名项目'),'storyboard_id':storyboard_id,'status':'ready','created_at':self._now(),'updated_at':self._now(),'paused':False,'tasks':tasks}
        self._refresh_ready(wf); self.save(wf); self.current=wf; self._emit('workflow.ready',wf); return wf

    def save(self,wf):
        if not isinstance(wf, dict) or not wf.get('workflow_id'):
            raise ValueError('工作流缺少有效 workflow_id')
        path=self._path(wf['workflow_id'])
        wf['updated_at']=self._now()
        fd,tmp_path=tempfile.mkstemp(prefix='.workflow-',suffix='.tmp',dir=self.workflow_dir)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(wf,f,ensure_ascii=False,indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path,path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return path

    def load(self,wid):
        with open(self._path(wid),encoding='utf-8') as f: wf=json.load(f)
        self._refresh_ready(wf); self.current=wf; return wf

    def list_workflows(self):
        out=[]
        for n in sorted(os.listdir(self.workflow_dir),reverse=True):
            if n.endswith('.json'):
                try:
                    with open(os.path.join(self.workflow_dir,n),encoding='utf-8') as f: out.append(json.load(f))
                except Exception: pass
        return out

    def _refresh_ready(self,wf):
        tasks=wf.get('tasks',[])
        # Dependencies are declared by task type for backward compatibility, but
        # a type is satisfied only when every task in that stage is complete.
        # Checking only whether one task of a type is done lets later stages
        # start while sibling shots/assets are still pending.
        for task in tasks:
            if task.get('status') not in (STATUS_PENDING, STATUS_READY):
                continue
            dependencies_ready = True
            for dependency_type in task.get('depends_on', []):
                prerequisites = [
                    candidate for candidate in tasks
                    if candidate.get('type') == dependency_type
                ]
                # Missing prerequisite stages are not implicitly satisfied.
                # This prevents partial plans from bypassing required production steps.
                if not prerequisites or not all(
                    candidate.get('status') == STATUS_DONE
                    for candidate in prerequisites
                ):
                    dependencies_ready = False
                    break
            task['status'] = STATUS_READY if dependencies_ready else STATUS_PENDING
        if tasks and all(t.get('status')==STATUS_DONE for t in tasks): wf['status']='completed'
        elif wf.get('paused'): wf['status']='paused'
        elif any(t.get('status')==STATUS_RUNNING for t in tasks): wf['status']='running'
        elif any(t.get('status')==STATUS_FAILED for t in tasks): wf['status']='failed'
        else: wf['status']='ready'

    def start_task(self,wid,task_id):
        wf=self.load(wid)
        if wf.get('paused'): return wf
        task=next((t for t in wf['tasks'] if t['id']==task_id),None)
        if not task: raise ValueError(f'任务不存在：{task_id}')
        if task['status']!=STATUS_READY: return wf
        task['status']=STATUS_RUNNING; task['progress']=1; task['started_at']=self._now(); self._refresh_ready(wf); self.save(wf); self._emit('task.started',wf,task); return wf

    def complete_task(self,wid,task_id):
        wf=self.load(wid); task=next((t for t in wf['tasks'] if t['id']==task_id),None)
        if not task: raise ValueError(f'任务不存在：{task_id}')
        if task['status'] not in (STATUS_RUNNING,STATUS_READY): return wf
        task['status']=STATUS_DONE; task['progress']=100; task['finished_at']=self._now(); self._refresh_ready(wf); self.save(wf); self._emit('task.completed',wf,task); return wf

    def fail_task(self,wid,task_id,error='执行失败'):
        wf=self.load(wid); task=next((t for t in wf['tasks'] if t['id']==task_id),None)
        if not task: raise ValueError(f'任务不存在：{task_id}')
        task['status']=STATUS_FAILED; task['error']=error; self._refresh_ready(wf); self.save(wf); self._emit('task.failed',wf,task); return wf

    def retry_task(self,wid,task_id):
        wf=self.load(wid)
        task=next((t for t in wf['tasks'] if t['id']==task_id),None)
        if not task: raise ValueError(f'任务不存在：{task_id}')
        if task.get('status') not in (STATUS_FAILED, STATUS_DONE, STATUS_PENDING, STATUS_READY):
            raise ValueError(f"任务当前状态 {task.get('status')} 不允许重试")

        # A retry invalidates every downstream stage transitively. Otherwise a
        # downstream task may remain "done" while still pointing at stale outputs.
        reset_types={task.get('type')}
        changed=True
        while changed:
            changed=False
            for candidate in wf.get('tasks', []):
                if candidate.get('type') in reset_types:
                    continue
                dependencies=candidate.get('depends_on', [])
                if any(dep in reset_types for dep in dependencies):
                    reset_types.add(candidate.get('type'))
                    changed=True

        reset=[]
        for candidate in wf.get('tasks', []):
            if candidate.get('id') == task_id or candidate.get('type') in reset_types:
                candidate['status']=STATUS_PENDING
                candidate['progress']=0
                candidate['error']=None
                candidate['started_at']=None
                candidate['finished_at']=None
                candidate['outputs']=[]
                candidate.pop('result', None)
                reset.append(candidate)
        wf['retry_invalidated_task_ids']=[candidate.get('id') for candidate in reset]
        self._refresh_ready(wf)
        self.save(wf)
        self._emit('task.retried',wf,task)
        return wf

    def pause(self,wid):
        wf=self.load(wid); wf['paused']=True; self._refresh_ready(wf); self.save(wf); self._emit('workflow.paused',wf); return wf
    def resume(self,wid):
        wf=self.load(wid); wf['paused']=False; self._refresh_ready(wf); self.save(wf); self._emit('workflow.resumed',wf); return wf

    def progress(self,wf):
        total=len(wf.get('tasks',[])); return int(sum(t.get('progress',0) for t in wf.get('tasks',[]))/total) if total else 0

workflow_engine=WorkflowEngine()
