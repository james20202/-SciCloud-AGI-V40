import json, os
from datetime import datetime
from core.config import DATA_DIR

DECISION_DIR=os.path.join(DATA_DIR,'director_decisions')
os.makedirs(DECISION_DIR,exist_ok=True)

class DirectorDecisionEngine:
    """V40.11 shot-level director decision layer. Converts QC/Vision feedback into executable repair intent."""
    RULES={
        'character':['人物','脸','身份','服装','发型','角色','一致性'],
        'action':['动作','姿态','手势','运动','肢体'],
        'composition':['构图','主体','前景','背景','画面布局','空间'],
        'camera':['镜头','机位','推拉','摇移','跟拍','焦段','景别','轴线'],
        'lighting':['光影','曝光','阴影','高光','色温','照明'],
        'prompt':['prompt','提示词','描述','风格','细节'],
        'scene':['场景','环境','地点','建筑','道具'],
    }
    def decide(self,wid,qc_result):
        feedback=[]
        for item in qc_result.get('results',[]):
            for v in item.get('vision',[]):
                feedback += list(v.get('issues',[]) or []) + list(v.get('suggestions',[]) or [])
        text=' '.join(str(x) for x in feedback).lower()
        targets=[]
        for target,words in self.RULES.items():
            if any(w.lower() in text for w in words): targets.append(target)
        if not targets and not qc_result.get('success',False): targets=['prompt']
        targets=list(dict.fromkeys(targets))
        cascade=any(x in targets for x in ('character','scene','camera'))
        decision={
            'decision_id':'DEC-'+datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3],
            'workflow_id':wid,
            'targets':targets,
            'priority':'high' if any(x in targets for x in ('character','scene','camera')) else 'normal',
            'cascade':cascade,
            'feedback':feedback[:20],
            'action':'repair_and_recheck' if not qc_result.get('success') else 'continue',
            'created_at':datetime.now().isoformat(timespec='seconds')
        }
        path=os.path.join(DECISION_DIR,f"{decision['decision_id']}.json")
        with open(path,'w',encoding='utf-8') as f: json.dump(decision,f,ensure_ascii=False,indent=2)
        decision['path']=path
        return decision

director_decision_engine=DirectorDecisionEngine()
