import json, os, time
from datetime import datetime
from core.config import PROJECT_DIR
from core.workflow_engine import workflow_engine, STATUS_READY, STATUS_RUNNING, STATUS_DONE, STATUS_FAILED
from core.execution_engine import execution_engine
from core.auto_fix_engine import auto_fix_engine

class AutoDirector:
    """V40.8 automatic director executor: repeatedly executes ready workflow tasks."""
    def __init__(self, engine=workflow_engine, executor=execution_engine):
        self.engine=engine; self.executor=executor
        self.log_dir=os.path.join(PROJECT_DIR,'execution_logs'); os.makedirs(self.log_dir,exist_ok=True)
        self._stop=False

    def _log(self,wid,entry):
        path=os.path.join(self.log_dir,f'{wid}.jsonl')
        with open(path,'a',encoding='utf-8') as f:
            f.write(json.dumps(entry,ensure_ascii=False)+'\n')

    def stop(self): self._stop=True

    def run(self,wid,max_steps=50,delay=0.15):
        self._stop=False; steps=0; results=[]
        while steps < max_steps and not self._stop:
            wf=self.engine.load(wid)
            if wf.get('paused') or wf.get('status')=='paused':
                return {'success':False,'stopped':True,'message':'工作流已暂停','steps':steps,'results':results}
            ready=[t for t in wf.get('tasks',[]) if t.get('status')==STATUS_READY]
            if not ready:
                done=all(t.get('status')==STATUS_DONE for t in wf.get('tasks',[]))
                failed=[t for t in wf.get('tasks',[]) if t.get('status')==STATUS_FAILED]
                msg='工作流已完成' if done else ('存在失败任务，自动执行已停止' if failed else '当前没有可执行任务')
                return {'success':done,'stopped':False,'message':msg,'steps':steps,'results':results}
            task=ready[0]
            started=datetime.now().isoformat(timespec='seconds')
            self._log(wid,{'event':'task_start','task_id':task['id'],'type':task.get('type'),'at':started})
            result=self.executor.execute(wid,task['id'])
            results.append({'task_id':task['id'],'result':result})
            self._log(wid,{'event':'task_finish','task_id':task['id'],'success':result.get('success',False),'message':result.get('message',''),'at':datetime.now().isoformat(timespec='seconds')})
            steps+=1
            if not result.get('success'):
                # V40.9: QC failure enters a bounded auto-fix loop instead of immediately ending production.
                if task.get('type') == 'qc':
                    fix=auto_fix_engine.fix(wid,result)
                    results.append({'qc_fix':fix})
                    self._log(wid,{'event':'qc_auto_fix','success':fix.get('success',False),'message':fix.get('message',''),'at':datetime.now().isoformat(timespec='seconds')})
                    if fix.get('success'):
                        if delay: time.sleep(delay)
                        continue
                return {'success':False,'stopped':True,'message':f"任务 {task['id']} 执行失败，已停止以保护生产链：{result.get('message','')}",'steps':steps,'results':results}
            if delay: time.sleep(delay)
        return {'success':False,'stopped':True,'message':'达到本次自动执行步数上限','steps':steps,'results':results}

auto_director=AutoDirector()
