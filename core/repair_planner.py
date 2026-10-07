import os, json
from datetime import datetime
from core.config import PROJECT_DIR
from core.workflow_engine import workflow_engine, STATUS_READY, STATUS_PENDING
from core.cross_shot_director import cross_shot_director
from core.storyboard_engine import storyboard_director

DIR=os.path.join(PROJECT_DIR,'repair_plans'); os.makedirs(DIR,exist_ok=True)

class RepairPlanner:
    """V40.13-40.16: convert director decisions into executable, bounded repairs."""
    def plan(self,wid,decision):
        wf=workflow_engine.load(wid)
        sb=None
        for t in wf.get('tasks',[]):
            if t.get('type')=='storyboard':
                for p in t.get('outputs',[]):
                    if str(p).endswith('.json') and os.path.isfile(p):
                        try:
                            with open(p,encoding='utf-8') as f: sb=json.load(f)
                        except Exception: pass
        plan={'repair_plan_id':'PLANREPAIR-'+datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3],'workflow_id':wid,'decision_id':decision.get('decision_id'),'targets':decision.get('targets',[]),'actions':[],'created_at':datetime.now().isoformat(timespec='seconds')}
        if sb:
            analysis=cross_shot_director.analyze(sb)
            repair=cross_shot_director.build_repair(sb,analysis,reason='director_decision')
            plan['cross_shot_analysis']=analysis; plan['cross_shot_repair']=repair
        # Requeue the smallest useful task chain. Media is not fabricated; real adapters must execute it.
        targets=set(decision.get('targets',[]))
        mapping=[]
        if targets & {'character','scene'}: mapping += ['character','scene','storyboard','prompt']
        elif targets & {'camera','composition','lighting','action','prompt'}: mapping += ['storyboard','prompt']
        else: mapping += ['prompt']
        mapping=list(dict.fromkeys(mapping))
        for t in wf.get('tasks',[]):
            if t.get('type') in mapping and t.get('status') in ('done','failed'):
                t['status']=STATUS_READY if not t.get('depends_on') else STATUS_PENDING; t['progress']=0; t['error']=None; t['outputs']=[]; t['repair_required']=True; t['repair_reason']=decision.get('feedback',[])
        workflow_engine._refresh_ready(wf); workflow_engine.save(wf)
        plan['requeued_types']=mapping; plan['status']='ready'
        path=os.path.join(DIR,plan['repair_plan_id']+'.json')
        with open(path,'w',encoding='utf-8') as f: json.dump(plan,f,ensure_ascii=False,indent=2)
        plan['path']=path
        return plan

repair_planner=RepairPlanner()
