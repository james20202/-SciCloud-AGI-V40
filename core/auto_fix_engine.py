from datetime import datetime
from core.workflow_engine import workflow_engine, STATUS_READY, STATUS_PENDING
from core.director_decision import director_decision_engine

class AutoFixEngine:
    """V40.9 bounded auto-fix: retry the concrete failed production task, then re-run QC."""
    def __init__(self,max_retries=2): self.max_retries=max_retries

    def fix(self,wid,qc_result):
        wf=workflow_engine.load(wid)
        tid=qc_result.get('failed_task_id')
        if not tid:
            return {'success':False,'message':'QC 未提供可修复任务'}
        task=next((t for t in wf.get('tasks',[]) if t.get('id')==tid),None)
        if not task:
            return {'success':False,'message':f'找不到待修复任务：{tid}'}
        decision=director_decision_engine.decide(wid,qc_result)
        attempts=int(task.get('auto_fix_attempts',0))
        if attempts>=self.max_retries:
            return {'success':False,'message':f'任务 {tid} 已达到自动修复上限 {self.max_retries} 次，转人工处理','exhausted':True}
        task['auto_fix_attempts']=attempts+1
        # Clear stale outputs before retry so QC cannot accidentally validate an old artifact.
        task['outputs']=[]
        task['auto_fix_last_at']=datetime.now().isoformat(timespec='seconds')
        task['auto_fix_reason']=qc_result.get('message','QC failed')
        task['director_decision']=decision
        task['repair_targets']=decision.get('targets',[])
        task['cascade_repair']=bool(decision.get('cascade'))
        vision_feedback=[]
        for item in qc_result.get('results',[]):
            for v in item.get('vision',[]):
                vision_feedback += list(v.get('suggestions',[]) or []) + list(v.get('issues',[]) or [])
        if vision_feedback:
            task['qc_feedback']=vision_feedback[:20]
        task['status']=STATUS_READY; task['progress']=0; task['error']=None; task['started_at']=None; task['finished_at']=None
        # Reset the failed QC task itself so the workflow can inspect the repaired artifact again.
        for qt in wf.get('tasks',[]):
            if qt.get('type') == 'qc' and qt.get('status') == 'failed':
                qt['status']=STATUS_PENDING; qt['progress']=0; qt['error']=None; qt['started_at']=None; qt['finished_at']=None; qt['outputs']=[]
        workflow_engine._refresh_ready(wf)
        workflow_engine.save(wf)
        return {'success':True,'message':f'已自动修复：重新执行 {tid}（第 {attempts+1}/{self.max_retries} 次），并重新排队 QC','task_id':tid,'attempt':attempts+1,'decision':decision}

auto_fix_engine=AutoFixEngine()
