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
    """V40.1 persistent workflow state engine. Execution adapters can be attached later."""
    def __init__(self, project_dir=PROJECT_DIR):
        self.project_dir=project_dir
        self.workflow_dir=os.path.join(project_dir,'workflows')
        os.makedirs(self.workflow_dir,exist_ok=True)
        self.current=None

    def _path(self,wid): return os.path.join(self.workflow_dir,f'{wid}.json')
    def _now(self): return datetime.now().isoformat(timespec='seconds')

    def create_from_plan(self, plan):
        # Persist one storyboard artifact and link it to downstream workflow tasks.
        storyboard = storyboard_director.create_from_plan(plan)
        storyboard_id = storyboard.get('storyboard_id')
        tasks=[]
        deps={
            'story':[], 'character':['story'], 'scene':['story'], 'storyboard':['character','scene'],
            'prompt':['storyboard'], 'image':['prompt'], 'video':['image'], 'voice':['story'],
            'sound':['video','voice'], 'edit':['video','sound','voice'], 'qc':['edit'], 'publish':['qc']
        }
        for i,t in enumerate(plan.get('tasks',[]),1):
            task=dict(t); task['status']=STATUS_READY if not deps.get(task['type']) else STATUS_PENDING
            task['progress']=0; task['depends_on']=deps.get(task['type'],[]); task['started_at']=None; task['finished_at']=None; task['error']=None
            if task.get('type') in ('storyboard', 'prompt', 'image', 'video'):
                task['storyboard_id'] = storyboard_id
            tasks.append(task)
        wf={'workflow_id':'WF-'+plan['plan_id'].replace('PLAN-',''),'plan_id':plan['plan_id'],'title':plan['title'],'storyboard_id':storyboard_id,'status':'ready','created_at':self._now(),'updated_at':self._now(),'paused':False,'tasks':tasks}
        self._refresh_ready(wf); self.save(wf); self.current=wf; return wf

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
        done_types={t['type'] for t in wf['tasks'] if t['status']==STATUS_DONE}
        for t in wf['tasks']:
            if t['status'] in (STATUS_PENDING,STATUS_READY) and all(d in done_types for d in t.get('depends_on',[])):
                t['status']=STATUS_READY
        if all(t['status']==STATUS_DONE for t in wf['tasks']): wf['status']='completed'
        elif wf.get('paused'): wf['status']='paused'
        else: wf['status']='running' if any(t['status']==STATUS_RUNNING for t in wf['tasks']) else 'ready'

    def start_task(self,wid,task_id):
        wf=self.load(wid)
        if wf.get('paused'): return wf
        task=next(t for t in wf['tasks'] if t['id']==task_id)
        if task['status']!=STATUS_READY: return wf
        task['status']=STATUS_RUNNING; task['progress']=1; task['started_at']=self._now(); self._refresh_ready(wf); self.save(wf); return wf

    def complete_task(self,wid,task_id):
        wf=self.load(wid); task=next(t for t in wf['tasks'] if t['id']==task_id)
        if task['status'] not in (STATUS_RUNNING,STATUS_READY): return wf
        task['status']=STATUS_DONE; task['progress']=100; task['finished_at']=self._now(); self._refresh_ready(wf); self.save(wf); return wf

    def fail_task(self,wid,task_id,error='执行失败'):
        wf=self.load(wid); task=next(t for t in wf['tasks'] if t['id']==task_id); task['status']=STATUS_FAILED; task['error']=error; self._refresh_ready(wf); self.save(wf); return wf

    def retry_task(self,wid,task_id):
        wf=self.load(wid); task=next(t for t in wf['tasks'] if t['id']==task_id)
        task['status']=STATUS_PENDING; task['progress']=0; task['error']=None; task['started_at']=None; task['finished_at']=None
        self._refresh_ready(wf); self.save(wf); return wf

    def pause(self,wid):
        wf=self.load(wid); wf['paused']=True; self._refresh_ready(wf); self.save(wf); return wf
    def resume(self,wid):
        wf=self.load(wid); wf['paused']=False; self._refresh_ready(wf); self.save(wf); return wf

    def progress(self,wf):
        total=len(wf['tasks']); return int(sum(t.get('progress',0) for t in wf['tasks'])/total) if total else 0

workflow_engine=WorkflowEngine()
