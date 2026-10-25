import json, os
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

    def _path(self,wid): return os.path.join(self.workflow_dir,f'{wid}.json')
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
            return result
        except Exception as exc:
            # Event reporting must not roll back an already persisted production state.
            self.last_event_error=f'{event_type}: {exc}'
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
        storyboard_id=storyboard.get('storyboard_id')
        if not storyboard_id: raise RuntimeError('分镜引擎未返回 storyboard_id')
        deps={
            'story':[], 'character':['story'], 'scene':['story'], 'storyboard':['character','scene'],
            'prompt':['storyboard'], 'image':['prompt'], 'video':['image'], 'voice':['story'],
            'sound':['video','voice'], 'edit':['video','sound','voice'], 'qc':['edit'], 'publish':['qc']
        }
        tasks=[]
        for t in raw_tasks:
            task=dict(t)
            task_type=task.get('type')
            if not task_type: raise ValueError(f"任务 {task['id']} 缺少 type")
            task['status']=STATUS_READY if not deps.get(task_type) else STATUS_PENDING
            task['progress']=0; task['depends_on']=deps.get(task_type,[])
            task['started_at']=None; task['finished_at']=None; task['error']=None
            task['storyboard_id']=storyboard_id
            tasks.append(task)
        wf={'workflow_id':'WF-'+str(plan_id).replace('PLAN-',''),'plan_id':plan_id,'title':plan.get('title','未命名项目'),'storyboard_id':storyboard_id,'status':'ready','created_at':self._now(),'updated_at':self._now(),'paused':False,'tasks':tasks}
        self._refresh_ready(wf); self.save(wf); self.current=wf; self._emit('workflow.ready',wf); return wf

    def save(self,wf):
        wf['updated_at']=self._now()
        with open(self._path(wf['workflow_id']),'w',encoding='utf-8') as f: json.dump(wf,f,ensure_ascii=False,indent=2)
        return self._path(wf['workflow_id'])

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
        done_types={t.get('type') for t in wf.get('tasks',[]) if t.get('status')==STATUS_DONE}
        for t in wf.get('tasks',[]):
            if t.get('status') in (STATUS_PENDING,STATUS_READY) and all(d in done_types for d in t.get('depends_on',[])):
                t['status']=STATUS_READY
        tasks=wf.get('tasks',[])
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
        wf=self.load(wid); task=next((t for t in wf['tasks'] if t['id']==task_id),None)
        if not task: raise ValueError(f'任务不存在：{task_id}')
        task['status']=STATUS_PENDING; task['progress']=0; task['error']=None; task['started_at']=None; task['finished_at']=None
        self._refresh_ready(wf); self.save(wf); self._emit('task.retried',wf,task); return wf

    def pause(self,wid):
        wf=self.load(wid); wf['paused']=True; self._refresh_ready(wf); self.save(wf); self._emit('workflow.paused',wf); return wf
    def resume(self,wid):
        wf=self.load(wid); wf['paused']=False; self._refresh_ready(wf); self.save(wf); self._emit('workflow.resumed',wf); return wf

    def progress(self,wf):
        total=len(wf.get('tasks',[])); return int(sum(t.get('progress',0) for t in wf.get('tasks',[]))/total) if total else 0

workflow_engine=WorkflowEngine()
