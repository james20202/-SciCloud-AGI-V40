import json, os
from datetime import datetime
from core.config import PROJECT_DIR
from core.model_hub import model_hub
from core.skill_registry import skill_registry
from core.workflow_engine import workflow_engine, STATUS_DONE
from core.adapters import FFmpegAdapter, ComfyUIAdapter, TTSCommandAdapter
from core.asset_manager import asset_manager
from core.director_plan import director_plan_engine
from core.storyboard_engine import storyboard_director
from core.qc_engine import qc_engine

ADAPTERS={'ffmpeg':FFmpegAdapter(),'comfyui':ComfyUIAdapter(),'tts_command':TTSCommandAdapter()}
TASK_TO_SKILL={'story':'SKILL-STORY','character':'SKILL-STORY','scene':'SKILL-STORY','storyboard':'SKILL-STORY','prompt':'SKILL-PROMPT','image':'SKILL-IMAGE','video':'SKILL-VIDEO','voice':'SKILL-TTS','sound':'SKILL-SOUND','edit':'SKILL-EDIT','qc':'SKILL-QC'}

class ExecutionEngine:
    def __init__(self): self.last_result=None

    def _artifact(self,wf,task,kind,data):
        d=os.path.join(PROJECT_DIR,'execution',wf['workflow_id']); os.makedirs(d,exist_ok=True)
        path=os.path.join(d,f"{task['id']}_{kind}.json")
        with open(path,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        return path

    def execute(self,wid,task_id):
        wf=workflow_engine.load(wid)
        task=next((x for x in wf['tasks'] if x['id']==task_id),None)
        if not task: return {'success':False,'message':'任务不存在'}
        if task.get('status')!='ready': return {'success':False,'message':f"任务当前状态为 {task.get('status')}，不可执行。"}
        skill_id=TASK_TO_SKILL.get(task.get('type'))
        skill=skill_registry.get(skill_id) if skill_id else None
        if not skill or not skill.get('enabled'):
            return {'success':False,'message':f'Skill 未启用：{skill_id}'}
        if task.get('type') == 'qc':
            workflow_engine.start_task(wid,task_id)
            result=qc_engine.inspect_workflow(wid)
            # Store QC report as a real local artifact.
            path=self._artifact(wf,task,'qc_report',result)
            task2=workflow_engine.load(wid)
            t2=next(t for t in task2['tasks'] if t['id']==task_id)
            t2['outputs']=[path]
            if result.get('success'):
                workflow_engine.complete_task(wid,task_id)
            else:
                workflow_engine.fail_task(wid,task_id,result.get('message','QC failed'))
            out=dict(result); out['outputs']=[path]; self.last_result=out; return out
        model=model_hub.find_for_skill(task.get('type'),task.get('model_id'))
        # Planning / prompt tasks have a real local artifact action; media tasks require an actual adapter.
        if task.get('type') in {'story','character','scene','storyboard','prompt'}:
            workflow_engine.start_task(wid,task_id)
            if task.get('type') == 'storyboard':
                storyboard_id = task.get('storyboard_id') or wf.get('storyboard_id')
                storyboard = storyboard_director.load(storyboard_id) if storyboard_id else None
                if not storyboard:
                    message = f'分镜资产不存在或无法读取：{storyboard_id or "缺少 storyboard_id"}'
                    workflow_engine.fail_task(wid, task_id, message)
                    return {'success': False, 'message': message}
                storyboard_payload = {
                    'mode': 'storyboard-production-input',
                    'storyboard_id': storyboard_id,
                    'plan_id': storyboard.get('plan_id') or wf.get('plan_id'),
                    'title': storyboard.get('title') or wf.get('title'),
                    'shot_count': len(storyboard.get('shots', [])),
                    'duration_seconds': sum(float(shot.get('duration', shot.get('duration_seconds', 0)) or 0) for shot in storyboard.get('shots', [])),
                    'storyboard': storyboard,
                    'executed_at': datetime.now().isoformat(timespec='seconds'),
                }
                path=self._artifact(wf,task,'storyboard',storyboard_payload)
            else:
                path=self._artifact(wf,task,'execution',{'task':task,'executed_at':datetime.now().isoformat(timespec='seconds'),'mode':'local-planning-artifact'})
            task['outputs']=[path]
            wf_saved=workflow_engine.load(wid)
            next(t for t in wf_saved['tasks'] if t['id']==task_id)['outputs']=[path]
            workflow_engine.save(wf_saved)
            registered=[]
            if task.get('type') in {'character','scene'}:
                plans=director_plan_engine.load_plans()
                plan=next((p for p in plans if p.get('plan_id')==wf.get('plan_id')),None)
                if plan:
                    entities=plan.get('characters' if task.get('type')=='character' else 'scenes',[])
                    for entity in entities:
                        registered.append(asset_manager.register_plan_entity(entity, task.get('type'), wf.get('plan_id')))
            registered += asset_manager.register_execution(task,[path],project_id=wf.get('plan_id'))
            workflow_engine.complete_task(wid,task_id)
            result={'success':True,'message':'本地规划任务执行完成，结果已登记到资产中心','outputs':[path],'assets':registered}
            self.last_result=result; return result
        if not model:
            return {'success':False,'message':f"没有可用的本地模型/适配器：{task.get('type')}。请到 Model Hub 启用。"}
        adapter=ADAPTERS.get(model.get('adapter'))
        if not adapter: return {'success':False,'message':f"未注册适配器：{model.get('adapter')}"}
        workflow_engine.start_task(wid,task_id)
        result=adapter.execute(model,task,{'workflow':task.get('workflow'),'command':task.get('command')})
        if result.success:
            workflow_engine.complete_task(wid,task_id)
        else:
            workflow_engine.fail_task(wid,task_id,result.message)
        out=result.to_dict(); out['model_id']=model.get('model_id'); out['adapter']=model.get('adapter')
        wf_saved=workflow_engine.load(wid)
        next(t for t in wf_saved['tasks'] if t['id']==task_id)['outputs']=list(result.outputs or [])
        workflow_engine.save(wf_saved)
        registered=asset_manager.register_execution(task, result.outputs, project_id=wf.get('plan_id'), data=result.data)
        out['assets']=registered
        self.last_result=out; return out

    def test_model(self,model_id):
        model=model_hub.get(model_id)
        if not model: return {'success':False,'message':'模型不存在'}
        adapter=ADAPTERS.get(model.get('adapter'))
        if not adapter: return {'success':False,'message':f"适配器不存在：{model.get('adapter')}"}
        return adapter.test(model).to_dict()

execution_engine=ExecutionEngine()
