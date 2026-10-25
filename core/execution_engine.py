import json, os, re, tempfile
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
        # IDs originate in plans; sanitize every path component to prevent path traversal.
        safe_workflow=re.sub(r'[^A-Za-z0-9_-]+','_',str(wf.get('workflow_id') or 'workflow')).strip('_') or 'workflow'
        safe_task=re.sub(r'[^A-Za-z0-9_-]+','_',str(task.get('id') or 'task')).strip('_') or 'task'
        safe_kind=re.sub(r'[^A-Za-z0-9_-]+','_',str(kind or 'artifact')).strip('_') or 'artifact'
        d=os.path.abspath(os.path.join(PROJECT_DIR,'execution',safe_workflow))
        root=os.path.abspath(os.path.join(PROJECT_DIR,'execution'))
        if os.path.commonpath([root,d]) != root:
            raise ValueError('执行制品目录越界')
        os.makedirs(d,exist_ok=True)
        path=os.path.join(d,f"{safe_task}_{safe_kind}.json")
        # Atomic replacement prevents a crash from leaving a truncated JSON artifact.
        fd,tmp_path=tempfile.mkstemp(prefix='.artifact-',suffix='.tmp',dir=d)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(data,f,ensure_ascii=False,indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path,path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
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
        # Planning tasks must produce real domain artifacts, not just generic execution logs.
        if task.get('type') in {'story','character','scene','storyboard','prompt'}:
            workflow_engine.start_task(wid,task_id)
            try:
                plans=director_plan_engine.load_plans()
                plan=next((p for p in plans if p.get('plan_id')==wf.get('plan_id')),None)
                if task.get('type') in {'story','character','scene'} and plan is None:
                    raise RuntimeError(f"找不到导演计划：{wf.get('plan_id')}")

                if task.get('type') == 'storyboard':
                    storyboard_id=task.get('storyboard_id') or wf.get('storyboard_id')
                    if not storyboard_id:
                        raise RuntimeError('工作流缺少 storyboard_id，无法执行分镜任务')
                    storyboard=storyboard_director.load(storyboard_id)
                    if not storyboard or not storyboard.get('shots'):
                        raise RuntimeError(f"分镜不存在或没有镜头：{storyboard_id}")
                    path=storyboard_director._path(storyboard_id)
                    payload={'storyboard_id':storyboard_id,'shot_count':len(storyboard['shots']),'storyboard_path':path}
                    message=f"分镜已就绪：{len(storyboard['shots'])} 个镜头"
                elif task.get('type') == 'prompt':
                    storyboard_id=task.get('storyboard_id') or wf.get('storyboard_id')
                    if not storyboard_id:
                        raise RuntimeError('工作流缺少 storyboard_id，无法生成镜头提示词')
                    storyboard=storyboard_director.load(storyboard_id)
                    if not storyboard or not storyboard.get('shots'):
                        raise RuntimeError(f"分镜不存在或没有镜头：{storyboard_id}")
                    records=[]
                    for index, shot in enumerate(storyboard['shots']):
                        record=storyboard_director.build_prompt(storyboard_id,index,plan=plan,model='generic')
                        if not record or not record.get('prompt'):
                            raise RuntimeError(f"第 {index+1} 个镜头未能生成有效提示词")
                        records.append(record)
                    path=self._artifact(wf,task,'prompts',{'storyboard_id':storyboard_id,'generated_at':datetime.now().isoformat(timespec='seconds'),'prompts':records})
                    payload={'storyboard_id':storyboard_id,'prompt_count':len(records),'prompts_path':path}
                    message=f"已生成 {len(records)} 条镜头提示词"
                else:
                    if task.get('type') == 'story':
                        domain_data={'plan_id':plan['plan_id'],'title':plan.get('title'),'idea':plan.get('idea'),'story':plan.get('story',{}),'intent':plan.get('intent',{}),'source':'director_plan'}
                        kind='script'
                    else:
                        domain_data=None
                        kind='execution'
                    path=self._artifact(wf,task,kind,domain_data or {'task':task,'executed_at':datetime.now().isoformat(timespec='seconds'),'mode':'local-planning-artifact'})
                    payload={'plan_id':plan['plan_id'],'artifact_path':path}
                    message='剧本大纲已保存为本地制品' if task.get('type')=='story' else '本地规划任务执行完成'
                registered=[]
                if task.get('type') in {'character','scene'}:
                    entities=plan.get('characters' if task.get('type')=='character' else 'scenes',[])
                    for entity in entities:
                        registered.append(asset_manager.register_plan_entity(entity,task.get('type'),wf.get('plan_id')))
                registered += asset_manager.register_execution(task,[path],project_id=wf.get('plan_id'),data=payload)
                wf_saved=workflow_engine.load(wid)
                saved_task=next(t for t in wf_saved['tasks'] if t['id']==task_id)
                saved_task['outputs']=[path]
                saved_task['result']=payload
                workflow_engine.save(wf_saved)
                workflow_engine.complete_task(wid,task_id)
                result={'success':True,'message':message,'outputs':[path],'assets':registered,'data':payload}
            except Exception as exc:
                workflow_engine.fail_task(wid,task_id,str(exc))
                result={'success':False,'message':str(exc),'task_id':task_id,'workflow_id':wid}
            self.last_result=result
            return result
        if not model:
            return {'success':False,'message':f"没有可用的本地模型/适配器：{task.get('type')}。请到 Model Hub 启用。"}
        adapter=ADAPTERS.get(model.get('adapter'))
        if not adapter: return {'success':False,'message':f"未注册适配器：{model.get('adapter')}"}
        workflow_engine.start_task(wid,task_id)
        result=adapter.execute(model,task,{'workflow':task.get('workflow'),'command':task.get('command')})
        raw_outputs=list(result.outputs or [])
        valid_outputs=[]
        for output in raw_outputs:
            output_path=output.get('path') if isinstance(output,dict) else output
            if output_path and os.path.isfile(output_path) and os.path.getsize(output_path)>0:
                valid_outputs.append(output)
        # A successful adapter response is not proof that media was actually written.
        # Keep media tasks running only when a verifiable, non-empty file exists.
        media_types={'image','video','voice','sound','edit'}
        effective_success=bool(result.success)
        effective_message=result.message
        if effective_success and task.get('type') in media_types and not valid_outputs:
            effective_success=False
            effective_message='适配器返回成功，但没有生成可验证的非空媒体文件；任务未标记完成。'
        if effective_success:
            workflow_engine.complete_task(wid,task_id)
        else:
            workflow_engine.fail_task(wid,task_id,effective_message or '执行失败')
        out=result.to_dict()
        out['success']=effective_success
        out['message']=effective_message
        out['outputs']=valid_outputs
        out['model_id']=model.get('model_id'); out['adapter']=model.get('adapter')
        wf_saved=workflow_engine.load(wid)
        next(t for t in wf_saved['tasks'] if t['id']==task_id)['outputs']=valid_outputs
        workflow_engine.save(wf_saved)
        registered=asset_manager.register_execution(task,valid_outputs,project_id=wf.get('plan_id'),data=result.data)
        out['assets']=registered
        self.last_result=out; return out

    def test_model(self,model_id):
        model=model_hub.get(model_id)
        if not model: return {'success':False,'message':'模型不存在'}
        adapter=ADAPTERS.get(model.get('adapter'))
        if not adapter: return {'success':False,'message':f"适配器不存在：{model.get('adapter')}"}
        return adapter.test(model).to_dict()

execution_engine=ExecutionEngine()
