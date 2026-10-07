from datetime import datetime
from core.qc_engine import qc_engine
from core.story_qc_engine import story_qc_engine
from core.director_decision import director_decision_engine
from core.repair_planner import repair_planner

class DirectorLoop:
    """V40.16-40.20 complete director loop: inspect -> decide -> repair plan -> requeue -> recheck."""
    def run_review_cycle(self,wid):
        qc=qc_engine.inspect_workflow(wid)
        story=story_qc_engine.review(wid)
        combined={'success':bool(qc.get('success') and story.get('success')),'qc':qc,'story':story}
        if combined['success']:
            return {'success':True,'stage':'approved','message':'AI导演审核通过，当前阶段无需修复','qc':qc,'story':story,'created_at':datetime.now().isoformat(timespec='seconds')}
        decision_input=qc if not qc.get('success') else {'success':False,'results':[{'vision':[],'issues':['故事级审核未通过：'+story.get('message','')]}]}
        decision=director_decision_engine.decide(wid,decision_input)
        decision['story_qc_score']=story.get('score',0)
        plan=repair_planner.plan(wid,decision)
        return {'success':False,'stage':'repair_planned','message':'AI导演已完成问题定位，并生成修复计划；修复后继续审核','qc':qc,'story':story,'decision':decision,'repair_plan':plan,'created_at':datetime.now().isoformat(timespec='seconds')}

director_loop=DirectorLoop()
