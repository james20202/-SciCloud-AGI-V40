import json, os
from datetime import datetime
from core.config import PROJECT_DIR
from core.continuity_engine import continuity_engine
from core.workflow_engine import workflow_engine

DIR=os.path.join(PROJECT_DIR,'story_qc'); os.makedirs(DIR,exist_ok=True)

class StoryQCEngine:
    """V40.15 story-level QC: deterministic structure/continuity checks; no fake visual judgment."""
    def review(self, wid):
        wf=workflow_engine.load(wid)
        done={t.get('type'):t for t in wf.get('tasks',[]) if t.get('status')=='done'}
        checks=[]; score=100
        required=['story','character','scene','storyboard','prompt']
        for typ in required:
            ok=typ in done and bool(done[typ].get('outputs'))
            checks.append({'code':'REQUIRED_'+typ.upper(),'success':ok,'message':f'{typ} 产物存在' if ok else f'{typ} 产物缺失'})
            if not ok: score-=15
        storyboard_path=None
        for p in (done.get('storyboard') or {}).get('outputs',[]):
            if str(p).endswith('.json'): storyboard_path=p; break
        continuity=None
        if storyboard_path and os.path.isfile(storyboard_path):
            try:
                with open(storyboard_path,encoding='utf-8') as f: sb=json.load(f)
                continuity=continuity_engine.check_storyboard(sb)
                score=min(score,continuity.get('score',100))
                checks.append({'code':'CONTINUITY','success':continuity.get('score',0)>=70,'message':f"跨镜头连续性 {continuity.get('score',0)} 分",'report':continuity})
            except Exception as e:
                score-=20; checks.append({'code':'STORYBOARD_READ','success':False,'message':str(e)})
        passed=score>=70 and all(c['success'] for c in checks if c['code'].startswith('REQUIRED_'))
        result={'review_id':'STORYQC-'+datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3],'workflow_id':wid,'success':passed,'score':max(0,score),'checks':checks,'message':'故事级审核通过' if passed else '故事级审核发现问题，需要导演修复','created_at':datetime.now().isoformat(timespec='seconds')}
        path=os.path.join(DIR,result['review_id']+'.json')
        with open(path,'w',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
        result['path']=path; return result

story_qc_engine=StoryQCEngine()
