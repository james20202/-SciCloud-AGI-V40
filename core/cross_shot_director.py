import json, os
from datetime import datetime
from uuid import uuid4
from core.config import PROJECT_DIR
from core.continuity_engine import continuity_engine
from core.storyboard_engine import storyboard_director

DIR=os.path.join(PROJECT_DIR,'director_repairs'); os.makedirs(DIR,exist_ok=True)

class CrossShotDirector:
    """V40.12-40.14: turn continuity findings into bounded multi-shot repair plans."""
    def analyze(self, storyboard):
        report=continuity_engine.check_storyboard(storyboard)
        groups=[]
        for item in report.get('issues',[])+report.get('warnings',[]):
            idx=int(item.get('shot_index',0)); code=item.get('code','')
            if code in ('direction_break','visual_change','character_change','scene_change'):
                start=max(0,idx-1); end=min(len(storyboard.get('shots',[]))-1,idx+1)
                groups.append({'group_id':'REPAIR-'+uuid4().hex[:8].upper(),'reason':item.get('title'),'code':code,'shot_indexes':list(range(start,end+1)),'message':item.get('message')})
        # de-duplicate overlapping groups while preserving coverage.
        merged=[]
        for g in groups:
            overlap=next((x for x in merged if set(x['shot_indexes']) & set(g['shot_indexes']) and x['code']==g['code']),None)
            if overlap:
                overlap['shot_indexes']=sorted(set(overlap['shot_indexes'])|set(g['shot_indexes']))
            else: merged.append(g)
        return {'analysis_id':'CROSS-'+uuid4().hex[:8].upper(),'storyboard_id':storyboard.get('storyboard_id'),'continuity_score':report.get('score',0),'groups':merged,'checked_at':datetime.now().isoformat(timespec='seconds')}

    def build_repair(self, storyboard, analysis, reason='director_review'):
        actions=[]
        for g in analysis.get('groups',[]):
            for idx in g['shot_indexes']:
                shot=storyboard['shots'][idx]
                changes={}
                if g['code']=='direction_break':
                    prev=storyboard['shots'][max(0,idx-1)]
                    if prev.get('screen_direction'):
                        changes['screen_direction']=prev.get('screen_direction')
                    changes['continuity_note']='保持与前一镜运动方向一致；如需跳轴，增加过渡镜头。'
                elif g['code']=='visual_change':
                    prev=storyboard['shots'][max(0,idx-1)]
                    for k in ('lighting','camera_angle'):
                        if prev.get(k): changes[k]=prev[k]
                    changes['continuity_note']='恢复关键视觉参数连续性。'
                elif g['code']=='character_change':
                    prev=storyboard['shots'][max(0,idx-1)]
                    if prev.get('character_ids'): changes['character_ids']=list(prev['character_ids'])
                    changes['continuity_note']='保持人物身份与造型连续，除非剧情明确要求换人。'
                elif g['code']=='scene_change':
                    prev=storyboard['shots'][max(0,idx-1)]
                    if prev.get('scene_id'): changes['scene_id']=prev['scene_id']
                    changes['continuity_note']='保持空间连续，除非该镜头承担明确转场。'
                actions.append({'shot_index':idx,'shot_id':shot.get('id'),'changes':changes,'reason':g['reason'],'regenerate_prompt':True})
        plan={'repair_id':'RPR-'+uuid4().hex[:8].upper(),'storyboard_id':storyboard.get('storyboard_id'),'reason':reason,'actions':actions,'created_at':datetime.now().isoformat(timespec='seconds'),'status':'planned'}
        path=os.path.join(DIR,plan['repair_id']+'.json')
        with open(path,'w',encoding='utf-8') as f: json.dump(plan,f,ensure_ascii=False,indent=2)
        plan['path']=path
        return plan

    def apply_repair(self, plan):
        sb=storyboard_director.load(plan.get('storyboard_id',''))
        if not sb: return {'success':False,'message':'找不到分镜板'}
        changed=[]
        for a in plan.get('actions',[]):
            idx=a.get('shot_index')
            if isinstance(idx,int) and 0<=idx<len(sb.get('shots',[])):
                sb['shots'][idx].update(a.get('changes',{})); sb['shots'][idx]['prompt_status']='pending'; changed.append(sb['shots'][idx].get('id'))
        sb['version']=int(sb.get('version',1))+1
        storyboard_director.save(sb)
        plan['status']='applied'; plan['applied_shots']=changed; plan['applied_at']=datetime.now().isoformat(timespec='seconds')
        with open(plan['path'],'w',encoding='utf-8') as f: json.dump(plan,f,ensure_ascii=False,indent=2)
        return {'success':True,'message':f'已联动修复 {len(changed)} 个镜头，并标记 Prompt 重新生成','repair_id':plan['repair_id'],'shot_ids':changed}

cross_shot_director=CrossShotDirector()
