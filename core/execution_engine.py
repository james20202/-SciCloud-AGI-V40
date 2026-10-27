import hashlib, json, math, os, re, shutil, tempfile
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
from core.motion_graphics_engine import motion_graphics_engine
from core.shot_contract import normalize_shot, build_shot_manifest
from core.shot_batch import build_shot_batch_manifest, load_or_reconcile_shot_batch_manifest, run_shot_batch
from core.audio_timeline import build_audio_timeline, build_narration_script, render_srt
from core.episode_package import build_episode_package
from core.episode_render_engine import build_episode_edit_command
from core.media_tools import find_tool

ADAPTERS={'ffmpeg':FFmpegAdapter(),'comfyui':ComfyUIAdapter(),'tts_command':TTSCommandAdapter()}
TASK_TO_SKILL={'story':'SKILL-STORY','character':'SKILL-STORY','scene':'SKILL-STORY','storyboard':'SKILL-STORY','prompt':'SKILL-PROMPT','image':'SKILL-IMAGE','video':'SKILL-VIDEO','voice':'SKILL-TTS','sound':'SKILL-SOUND','edit':'SKILL-EDIT','qc':'SKILL-QC','title_card':'SKILL-EDIT','motion_graphics':'SKILL-EDIT','publish':'SKILL-EDIT'}

class ExecutionEngine:
    def __init__(self): self.last_result=None

    def _start_or_reject(self, wid, task_id):
        wf=workflow_engine.start_task(wid,task_id)
        task=next((item for item in wf.get('tasks',[]) if item.get('id')==task_id),None)
        if not task or task.get('status') != 'running':
            message='工作流已暂停，任务未启动' if wf.get('paused') else f"任务未能进入运行状态：{task_id}"
            result={'success':False,'message':message,'task_id':task_id,'workflow_id':wid}
            self.last_result=result
            return result
        return None

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

    def _ensure_workflow_storyboard(self, wid, wf, task, plan):
        """Resolve and persist a storyboard binding for workflow storyboard/prompt tasks."""
        storyboard_id = task.get('storyboard_id') or wf.get('storyboard_id')
        if storyboard_id:
            storyboard = storyboard_director.load(storyboard_id)
            if not storyboard or not storyboard.get('shots'):
                raise RuntimeError(f"分镜不存在或没有镜头：{storyboard_id}")
        else:
            plan_id = wf.get('plan_id') or (plan.get('plan_id') if isinstance(plan, dict) else None)
            storyboard = next(
                (item for item in storyboard_director.list()
                 if item.get('plan_id') == plan_id and item.get('shots')),
                None,
            )
            if storyboard is None:
                if not isinstance(plan, dict):
                    raise RuntimeError(f"无法自动创建分镜：找不到导演计划 {plan_id or '(未绑定)'}")
                storyboard = storyboard_director.create_from_plan(plan)
            storyboard_id = storyboard.get('storyboard_id')
            if not storyboard_id:
                raise RuntimeError('分镜创建成功但缺少 storyboard_id')

        # Persist the binding at both workflow and task level so downstream tasks
        # can resume after app restart instead of repeatedly failing on missing IDs.
        saved = workflow_engine.load(wid)
        if not isinstance(saved, dict):
            saved = dict(wf)
        saved['storyboard_id'] = storyboard_id
        saved_task = next((item for item in saved.get('tasks', [])
                           if item.get('id') == task.get('id')), None)
        if saved_task is not None:
            saved_task['storyboard_id'] = storyboard_id
        workflow_engine.save(saved)
        wf['storyboard_id'] = storyboard_id
        task['storyboard_id'] = storyboard_id
        return storyboard_id, storyboard

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
            blocked=self._start_or_reject(wid,task_id)
            if blocked:
                return blocked
            result=qc_engine.inspect_workflow(wid)
            # Store QC report as a real local artifact.
            path=self._artifact(wf,task,'qc_report',result)
            task2=workflow_engine.load(wid)
            t2=next(t for t in task2['tasks'] if t['id']==task_id)
            t2['outputs']=[path]
            workflow_engine.save(task2)
            if result.get('success'):
                workflow_engine.complete_task(wid,task_id)
            else:
                workflow_engine.fail_task(wid,task_id,result.get('message','QC failed'))
            out=dict(result); out['outputs']=[path]; self.last_result=out; return out
        if task.get('type') in {'title_card','motion_graphics'}:
            blocked=self._start_or_reject(wid,task_id)
            if blocked:
                return blocked
            try:
                safe_wid=re.sub(r'[^A-Za-z0-9_-]+','_',str(wid)).strip('_') or 'workflow'
                safe_tid=re.sub(r'[^A-Za-z0-9_-]+','_',str(task_id)).strip('_') or 'task'
                output_dir=task.get('output_dir') or os.path.join(PROJECT_DIR,'output','motion_graphics',safe_wid,safe_tid)
                output_dir=os.path.abspath(output_dir)
                os.makedirs(output_dir,exist_ok=True)
                output_path=os.path.join(output_dir,f'{safe_tid}.mp4')
                render=motion_graphics_engine.render_card(
                    title=task.get('title') or task.get('text') or task.get('name') or '章节标题',
                    output_video=output_path,
                    duration_seconds=task.get('duration_seconds',task.get('duration',2.0)),
                    subtitle=task.get('subtitle',''),
                    aspect_ratio=task.get('aspect_ratio','9:16'),
                    style=task.get('style','xianxia'),
                    fps=task.get('fps',24),
                )
                if not isinstance(render,dict) or not render.get('success'):
                    raise RuntimeError((render or {}).get('message','动效标题卡生成失败') if isinstance(render,dict) else '动效引擎返回无效结果')
                actual_path=render.get('output') or render.get('path') or output_path
                if not os.path.isfile(actual_path) or os.path.getsize(actual_path)<=0:
                    raise RuntimeError('动效标题卡引擎报告成功，但输出文件不存在或为空')
                payload={'kind':'motion_graphics','title':task.get('title') or task.get('text') or task.get('name') or '章节标题',
                         'render':render,'output_path':actual_path,'workflow_id':wid,'task_id':task_id}
                wf_saved=workflow_engine.load(wid)
                saved_task=next(t for t in wf_saved['tasks'] if t['id']==task_id)
                saved_task['outputs']=[actual_path]
                saved_task['result']=payload
                workflow_engine.save(wf_saved)
                registered=asset_manager.register_execution(task,[actual_path],project_id=wf.get('plan_id'),data=payload)
                workflow_engine.complete_task(wid,task_id)
                result={'success':True,'message':'动效标题卡已生成并登记为媒体资产','outputs':[actual_path],'assets':registered,'data':payload}
            except Exception as exc:
                try:
                    workflow_engine.fail_task(wid,task_id,str(exc))
                except Exception:
                    pass
                result={'success':False,'message':str(exc),'task_id':task_id,'workflow_id':wid,'outputs':[]}
            self.last_result=result
            return result
        if task.get('type') == 'publish':
            blocked=self._start_or_reject(wid,task_id)
            if blocked:
                return blocked
            try:
                safe_wid=re.sub(r'[^A-Za-z0-9_-]+','_',str(wid)).strip('_') or 'workflow'
                output_dir=os.path.join(PROJECT_DIR,'output','packages')
                output_path=os.path.join(output_dir,f'{safe_wid}_episode_package.zip')
                package=build_episode_package(wf,output_path)
                current=workflow_engine.load(wid)
                publish_task=next(t for t in current['tasks'] if t['id']==task_id)
                publish_task['outputs']=[package['output_path']]
                publish_task['result']={key:value for key,value in package.items() if key != 'manifest'}
                workflow_engine.save(current)
                registered=asset_manager.register_execution(publish_task,[package['output_path']],project_id=wf.get('plan_id'),data=publish_task['result'])
                workflow_engine.complete_task(wid,task_id)
                result={'success':True,'message':f"剧集交付包已生成（{package['file_count']} 个源文件，{package['subtitle_drafts']} 份字幕草稿）",'outputs':[package['output_path']],'assets':registered,'data':publish_task['result']}
            except Exception as exc:
                try:
                    workflow_engine.fail_task(wid,task_id,str(exc))
                except Exception:
                    pass
                result={'success':False,'message':str(exc),'task_id':task_id,'workflow_id':wid,'outputs':[]}
            self.last_result=result
            return result
        model=model_hub.find_for_skill(task.get('type'),task.get('model_id'))
        # Planning tasks must produce real domain artifacts, not just generic execution logs.
        if task.get('type') in {'story','character','scene','storyboard','prompt'}:
            blocked=self._start_or_reject(wid,task_id)
            if blocked:
                return blocked
            try:
                timing_contract_passed=True
                plans=director_plan_engine.load_plans()
                plan=next((p for p in plans if p.get('plan_id')==wf.get('plan_id')),None)
                if task.get('type') in {'story','character','scene'} and plan is None:
                    raise RuntimeError(f"找不到导演计划：{wf.get('plan_id')}")

                if task.get('type') == 'storyboard':
                    storyboard_id,storyboard=self._ensure_workflow_storyboard(wid,wf,task,plan)
                    path=storyboard_director._path(storyboard_id)
                    payload={'storyboard_id':storyboard_id,'shot_count':len(storyboard['shots']),'storyboard_path':path}
                    message=f"分镜已就绪：{len(storyboard['shots'])} 个镜头"
                elif task.get('type') == 'prompt':
                    storyboard_id,storyboard=self._ensure_workflow_storyboard(wid,wf,task,plan)
                    records=[]
                    for index, shot in enumerate(storyboard['shots']):
                        record=storyboard_director.build_prompt(storyboard_id,index,plan=plan,model='generic')
                        if not record or not record.get('prompt'):
                            raise RuntimeError(f"第 {index+1} 个镜头未能生成有效提示词")
                        # Bind every prompt to the source shot so downstream image/video
                        # tasks can preserve shot identity, timing, dialogue and visual intent.
                        record=dict(record)
                        generated_prompt=record.get('prompt','')
                        record.update({
                            'shot_id':shot.get('id') or f'SHOT-{index+1:04d}',
                            'shot_index':index+1,
                            'duration':shot.get('duration',5.0),
                            'visual_prompt':shot.get('visual_prompt') or shot.get('prompt',''),
                            'dialogue':shot.get('dialogue',''),
                            'voiceover':shot.get('voiceover',''),
                            'scene_id':shot.get('scene_id'),
                            'character_ids':shot.get('character_ids',[]),
                        })
                        record=normalize_shot(record,index)
                        # Keep the model-generated production prompt distinct from the
                        # storyboard's visual intent. Normalization aliases prompt to
                        # visual_prompt for legacy records, so restore the generated value.
                        if isinstance(generated_prompt,str) and generated_prompt.strip():
                            record['prompt']=generated_prompt
                        records.append(record)
                    # Timing is an explicit production contract: downstream video/edit
                    # stages need both the sum of shot durations and the plan target.
                    timeline=build_shot_manifest(records)
                    actual_duration=timeline['planned_duration_seconds']
                    intent=plan.get('intent',{}) if isinstance(plan,dict) else {}
                    target_raw=intent.get('duration_seconds', intent.get('target_duration_seconds')) if isinstance(intent,dict) else None
                    try:
                        parsed_target=float(target_raw) if target_raw is not None else None
                        target_duration=round(parsed_target,3) if parsed_target is not None and math.isfinite(parsed_target) and parsed_target>0 else None
                    except (TypeError,ValueError,OverflowError):
                        target_duration=None
                    timing_summary={
                        'target_duration_seconds':target_duration,
                        'actual_duration_seconds':actual_duration,
                        'delta_seconds':round(actual_duration-target_duration,3) if target_duration is not None else None,
                        'within_target_tolerance':abs(actual_duration-target_duration)<=max(0.1,target_duration*0.005) if target_duration is not None else None,
                        'shot_count':len(records),
                        'shot_durations_seconds':[round(float(item.get('duration',0) or 0),3) for item in records],
                    }
                    timing_contract_passed=(target_duration is None or timing_summary['within_target_tolerance'] is True)
                    audio_timeline=build_audio_timeline(records)
                    subtitle_srt_draft=render_srt(audio_timeline)
                    video_task=next((item for item in wf.get('tasks',[]) if item.get('type')=='video'),{})
                    batch_manifest=build_shot_batch_manifest(
                        records,
                        workflow_id=wid,
                        target_duration=target_duration,
                        workflow_registry_id=video_task.get('workflow_registry_id'),
                        workflow_capability=video_task.get('workflow_capability') or 'video.image2video',
                    )
                    path=self._artifact(wf,task,'prompts',{'storyboard_id':storyboard_id,'generated_at':datetime.now().isoformat(timespec='seconds'),'prompt_count':len(records),'timing_summary':timing_summary,'timeline_manifest':timeline,'shot_batch_manifest':batch_manifest,'audio_timeline':audio_timeline,'subtitle_srt_draft':subtitle_srt_draft,'prompts':records})
                    payload={'storyboard_id':storyboard_id,'prompt_count':len(records),'prompts_path':path,'timing_summary':timing_summary,'shot_batch_count':batch_manifest['shot_count'],'shot_batch_duration_seconds':batch_manifest['planned_duration_seconds']}
                    if target_duration is not None and not timing_summary['within_target_tolerance']:
                        message=f"已生成 {len(records)} 条镜头提示词；镜头总时长 {actual_duration:g}s，与目标 {target_duration:g}s 相差 {actual_duration-target_duration:+g}s"
                    else:
                        message=f"已生成 {len(records)} 条镜头提示词（总时长 {actual_duration:g}s）"
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
                if task.get('type') == 'prompt' and not timing_contract_passed:
                    blocked_message=message+'；已阻断后续镜头生产，请修正镜头时长后重试。'
                    workflow_engine.fail_task(wid,task_id,blocked_message)
                    result={'success':False,'message':blocked_message,'outputs':[path],'assets':registered,'data':payload}
                else:
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
        blocked=self._start_or_reject(wid,task_id)
        if blocked:
            return blocked
        try:
            context={'workflow':task.get('workflow'),'command':task.get('command')}
            adapter_task=task
            safe_wid=re.sub(r'[^A-Za-z0-9_-]+','_',str(wid)).strip('_') or 'workflow'
            safe_tid=re.sub(r'[^A-Za-z0-9_-]+','_',str(task_id)).strip('_') or 'task'
            if task.get('type') == 'edit' and model.get('adapter') == 'ffmpeg' and not task.get('command'):
                adapter_task=dict(task)
                output_path=task.get('output_path') or os.path.join(
                    PROJECT_DIR,'output','episodes',safe_wid,f'{safe_tid}.mp4'
                )
                edit_plan=build_episode_edit_command(
                    wf,
                    output_path,
                    ffmpeg=model.get('command') or 'ffmpeg',
                )
                adapter_task['command']=edit_plan['command']
                context['command']=edit_plan['command']
                context['edit_plan']={key:value for key,value in edit_plan.items() if key != 'command'}
            if task.get('type') == 'voice' and model.get('adapter') == 'tts_command':
                # Build one narration script from the canonical storyboard while keeping
                # the persisted workflow task backward-compatible.
                adapter_task=dict(task)
                text_input=adapter_task.get('text') or adapter_task.get('input_text') or adapter_task.get('script')
                if not isinstance(text_input,str) or not text_input.strip():
                    storyboard_id=task.get('storyboard_id') or wf.get('storyboard_id')
                    storyboard=storyboard_director.load(storyboard_id) if storyboard_id else None
                    if not storyboard or not isinstance(storyboard.get('shots'),list):
                        raise RuntimeError('配音任务缺少可用分镜，无法提取对白/旁白')
                    text_input=build_narration_script(storyboard['shots'])
                if not isinstance(text_input,str) or not text_input.strip():
                    # Rule-fallback storyboards have empty dialogue/voiceover for every
                    # shot. Do not fail the voice task for that: fall back to the plan's
                    # own logline/hook/idea, and label it as a plan fallback, never as
                    # storyboard dialogue. Only fail when even the plan has no text.
                    plan_parts = []
                    try:
                        plans = director_plan_engine.load_plans()
                        plan = next((item for item in plans if item.get('plan_id') == wf.get('plan_id')), None)
                    except Exception:
                        plan = None
                    if isinstance(plan, dict):
                        story = plan.get('story') or {}
                        if isinstance(story, dict) and isinstance(story.get('logline'), str) and story['logline'].strip():
                            plan_parts.append(story['logline'].strip())
                        intent = plan.get('intent') or {}
                        if isinstance(intent, dict) and isinstance(intent.get('hook'), str) and intent['hook'].strip():
                            plan_parts.append(intent['hook'].strip())
                        if isinstance(plan.get('idea'), str) and plan['idea'].strip():
                            plan_parts.append(plan['idea'].strip())
                    text_input = '。'.join(plan_parts)
                    if text_input:
                        text_input += '。'
                        adapter_task['narration_source'] = 'plan_fallback'
                if not isinstance(text_input,str) or not text_input.strip():
                    raise RuntimeError('分镜中没有可用于配音的对白或旁白，导演计划也没有可朗读的梗概；请先补充台词')
                adapter_task['text']=text_input
                adapter_task.setdefault(
                    'output_path',
                    os.path.join(PROJECT_DIR,'output','voice',safe_wid,f'{safe_tid}.wav')
                )
            if task.get('type') == 'sound' and model.get('adapter') == 'ffmpeg' and not task.get('command'):
                # A sound task without a concrete command used to fail in the FFmpeg
                # adapter with "需要具体 command". Generate an ambient bed (not BGM,
                # not music) at the task's duration so edit can proceed, and label it.
                adapter_task = dict(task)
                try:
                    duration = float(task.get('duration_seconds') or task.get('duration') or 60)
                except (TypeError, ValueError, OverflowError):
                    duration = 60.0
                if not duration or duration <= 0:
                    duration = 60.0
                sound_output = task.get('output_path') or os.path.join(
                    PROJECT_DIR, 'output', 'sound', safe_wid, f'{safe_tid}_sound.m4a')
                os.makedirs(os.path.dirname(os.path.abspath(sound_output)), exist_ok=True)
                ffmpeg_path = find_tool(model.get('command') or 'ffmpeg') or 'ffmpeg'
                adapter_task['command'] = [
                    ffmpeg_path, '-y', '-f', 'lavfi', '-i',
                    f'anoisesrc=color=brown:duration={duration}',
                    '-af', 'lowpass=f=400,volume=0.15', '-t', str(duration),
                    '-c:a', 'aac', '-b:a', '96k', sound_output,
                ]
                adapter_task['sound_source'] = 'ambient_fallback'
                context['command'] = adapter_task['command']
            inferred_bindings = {}
            batch_requested = (
                task.get('shot_batch_enabled') is True
                or (isinstance(task.get('shot_param_bindings'), dict) and bool(task.get('shot_param_bindings')))
            )
            if (task.get('type') == 'video' and model.get('adapter') == 'comfyui'
                    and not batch_requested
                    and callable(getattr(adapter, 'infer_shot_param_bindings', None))):
                inference = adapter.infer_shot_param_bindings(task, context)
                if isinstance(inference, dict) and inference.get('success') is True:
                    inferred_bindings = inference.get('bindings') or {}
                    if isinstance(inferred_bindings, dict) and inferred_bindings.get('prompt'):
                        batch_requested = True
                        task['shot_batch_auto_inferred'] = True
                        task['shot_param_bindings'] = dict(inferred_bindings)
            if (task.get('type') == 'video' and model.get('adapter') == 'comfyui'
                    and batch_requested
                    and callable(getattr(adapter, 'render', None))):
                # Explicit opt-in: execute each planned shot as an isolated ComfyUI
                # submission, persist per-shot checkpoints, and resume completed shots.
                prompt_task=next((item for item in wf.get('tasks',[]) if item.get('type')=='prompt'),None)
                prompt_payload=None
                if prompt_task:
                    for output in prompt_task.get('outputs') or []:
                        prompt_path=output.get('path') if isinstance(output,dict) else output
                        if not isinstance(prompt_path,str) or not os.path.isfile(prompt_path) or not prompt_path.lower().endswith('.json'):
                            continue
                        try:
                            with open(prompt_path,encoding='utf-8') as handle:
                                candidate=json.load(handle)
                            if isinstance(candidate,dict) and isinstance(candidate.get('shot_batch_manifest'),dict):
                                prompt_payload=candidate
                                break
                        except (OSError,ValueError):
                            continue
                if not prompt_payload:
                    raise RuntimeError('逐镜头模式已启用，但找不到包含 shot_batch_manifest 的提示词制品')
                batch=prompt_payload['shot_batch_manifest']
                if task.get('workflow_registry_id'):
                    batch['workflow_registry_id']=task['workflow_registry_id']
                if task.get('workflow_capability'):
                    batch['workflow_capability']=task['workflow_capability']
                bindings=task.get('shot_param_bindings') or inferred_bindings or {}
                if not isinstance(bindings,dict) or any(
                    key not in {'prompt','visual_prompt','duration_seconds','shot_id'} or not isinstance(value,str) or not value
                    for key,value in bindings.items()
                ):
                    raise RuntimeError('shot_param_bindings 仅支持 prompt、visual_prompt、duration_seconds、shot_id 到已声明参数名的映射')
                base_params=task.get('workflow_params') or {}
                if not isinstance(base_params,dict):
                    raise RuntimeError('workflow_params 必须是对象')
                batch_dir=os.path.join(PROJECT_DIR,'execution',safe_wid)
                batch_path=os.path.join(batch_dir,f'{safe_tid}_shot_batch.json')
                # Bind checkpoint reuse to the complete render configuration, not only
                # shot text. A changed workflow/model/asset/reference invalidates old media.
                signature_payload={
                    # Hash the complete selected model configuration (the manifest
                    # stores only the digest, never this payload) so changing a checkpoint
                    # or model option cannot accidentally reuse stale shot outputs.
                    'model_configuration':model,
                    'workflow_registry_id':task.get('workflow_registry_id') or batch.get('workflow_registry_id'),
                    'workflow_capability':task.get('workflow_capability') or batch.get('workflow_capability'),
                    'workflow_manifest':task.get('workflow_manifest'),
                    'workflow_graph':task.get('workflow') or context.get('workflow'),
                    'workflow_params':base_params,
                    'workflow_assets':task.get('workflow_assets') or context.get('workflow_assets') or {},
                    'shot_param_bindings':bindings,
                    'character_references':task.get('character_references') or context.get('character_references') or [],
                }
                signature_raw=json.dumps(signature_payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),default=str)
                batch['execution_signature']=hashlib.sha256(signature_raw.encode('utf-8')).hexdigest()
                # The prompt artifact is the current source of truth. Reuse previous
                # per-shot states only if shot inputs AND render configuration match.
                batch=load_or_reconcile_shot_batch_manifest(batch,batch_path)
                preflight=getattr(adapter,'preflight_shot_batch',None)
                if not callable(preflight):
                    raise RuntimeError('当前 ComfyUI 适配器不支持逐镜头工作流预检查，拒绝启动批次')
                preflight_context=dict(context)
                preflight_context['shot_batch_jobs']=batch.get('jobs') or []
                preflight_result=preflight(task,bindings,preflight_context)
                if not isinstance(preflight_result,dict) or preflight_result.get('success') is not True:
                    detail=preflight_result.get('message','未知预检查错误') if isinstance(preflight_result,dict) else '适配器返回无效预检查结果'
                    raise RuntimeError(detail)
                batch['workflow_preflight']=preflight_result
                def render_one_shot(job):
                    shot_task=dict(task)
                    shot_task['type']='video'
                    shot_task['workflow_registry_id']=task.get('workflow_registry_id') or job.get('workflow_registry_id')
                    shot_task['workflow_capability']=task.get('workflow_capability') or job.get('workflow_capability')
                    shot_task['workflow_params']=dict(base_params)
                    for field,param_name in bindings.items():
                        if param_name in shot_task['workflow_params'] or param_name:
                            shot_task['workflow_params'][param_name]=job.get(field)
                    shot_task['output_dir']=os.path.join(batch_dir,'shots',str(job['shot_id']))
                    shot_context=dict(context)
                    shot_context['output_dir']=shot_task['output_dir']
                    shot_result=adapter.render(model,shot_task,shot_context)
                    if not shot_result or not getattr(shot_result,'success',False):
                        raise RuntimeError(getattr(shot_result,'message','ComfyUI 镜头渲染失败'))
                    raw=shot_result.outputs or []
                    video_outputs=[]
                    for item in raw:
                        path=item.get('path') if isinstance(item,dict) else item
                        ext=os.path.splitext(str(path))[1].lower() if path else ''
                        if path and ext in {'.mp4','.mov','.mkv','.webm','.m4v','.gif'} and os.path.isfile(path) and os.path.getsize(path)>0:
                            video_outputs.append((path,item))
                    if len(video_outputs)!=1:
                        raise RuntimeError(f"镜头 {job.get('shot_id')} 需要且仅需要一个视频输出，实际 {len(video_outputs)} 个")
                    source,record=video_outputs[0]
                    relative=job.get('output_path')
                    target=os.path.abspath(os.path.join(PROJECT_DIR,relative))
                    root=os.path.abspath(os.path.join(PROJECT_DIR,'output','shots'))
                    if os.path.commonpath([root,target]) != root:
                        raise RuntimeError('镜头输出路径越界')
                    os.makedirs(os.path.dirname(target),exist_ok=True)
                    temporary=target+'.tmp'+os.path.splitext(target)[1]
                    try:
                        shutil.copy2(source,temporary)
                        if not os.path.isfile(temporary) or os.path.getsize(temporary)<=0:
                            raise RuntimeError('镜头输出复制后为空')
                        os.replace(temporary,target)
                    finally:
                        if os.path.exists(temporary):
                            os.remove(temporary)
                    return [{'path':target,'kind':'video','shot_id':job.get('shot_id'),'size':os.path.getsize(target)}]
                batch_result=run_shot_batch(
                    batch,render_one_shot,batch_path,
                    retry_failed=task.get('retry_failed_shots') is True,
                )
                task['shot_batch_manifest_path']=batch_path
                task['shot_batch_progress']=batch_result.get('progress',{})
                completed_outputs=[]
                for job in batch_result.get('jobs',[]):
                    if job.get('status')=='done':
                        completed_outputs.extend(job.get('outputs') or [])
                if batch_result.get('status')!='done':
                    progress=batch_result.get('progress',{})
                    raise RuntimeError(
                        f"逐镜头生成未全部完成：成功 {progress.get('done',0)}/{progress.get('total',0)}，"
                        f"失败 {progress.get('failed',0)}，待执行 {progress.get('pending',0)}。"
                        f"批次状态已保存：{batch_path}。设置 retry_failed_shots=true 可重试失败镜头。"
                    )
                result=type('ShotBatchResult',(),{
                    'success':True,
                    'message':f"逐镜头生成完成：{len(completed_outputs)} 个镜头视频",
                    'outputs':completed_outputs,
                    'data':{'shot_batch_manifest_path':batch_path,'progress':batch_result.get('progress',{})},
                    'to_dict':lambda self:{'success':True,'message':self.message,'outputs':self.outputs,'data':self.data},
                })()
            elif model.get('adapter') == 'comfyui' and task.get('type') in {'image','video','voice','sound','edit'} and callable(getattr(adapter,'render',None)):
                context['output_dir']=task.get('output_dir') or os.path.join(PROJECT_DIR,'output','comfyui',safe_wid,safe_tid)
                result=adapter.render(model,adapter_task,context)
            else:
                result=adapter.execute(model,adapter_task,context)
            if result is None or not hasattr(result, 'success') or not hasattr(result, 'outputs') or not callable(getattr(result, 'to_dict', None)):
                raise RuntimeError('适配器返回了无效结果对象')
            if not isinstance(result.success, bool):
                raise RuntimeError('适配器结果 success 必须是布尔值')
            if result.outputs is not None and not isinstance(result.outputs, (list, tuple)):
                raise RuntimeError('适配器结果 outputs 必须是列表')
            raw_outputs=list(result.outputs or [])
        except Exception as exc:
            message=f'适配器执行异常：{exc}'
            try:
                workflow_engine.fail_task(wid,task_id,message)
            except Exception:
                pass
            # Preserve partial shot-batch diagnostics even when a later shot fails.
            # Otherwise the UI loses the checkpoint location and cannot explain how
            # much work completed, despite the batch JSON already being on disk.
            failure={'success':False,'message':message,'task_id':task_id,'workflow_id':wid,'outputs':[]}
            try:
                saved_wf=workflow_engine.load(wid)
                saved_task=next(item for item in saved_wf.get('tasks',[]) if item.get('id')==task_id)
                for key in ('shot_batch_manifest_path','shot_batch_progress'):
                    if task.get(key) is not None:
                        saved_task[key]=task[key]
                        failure[key]=task[key]
                saved_task['last_error']=message
                workflow_engine.save(saved_wf)
            except Exception:
                pass
            self.last_result=failure
            return failure
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
        saved_task=next(t for t in wf_saved['tasks'] if t['id']==task_id)
        saved_task['outputs']=valid_outputs
        # Persist adapter result metadata (including shot-batch checkpoint/progress)
        # beside the workflow task so the UI can report the last production attempt.
        saved_task['result']=out
        if isinstance(result.data,dict):
            if result.data.get('shot_batch_manifest_path'):
                saved_task['shot_batch_manifest_path']=result.data['shot_batch_manifest_path']
            if isinstance(result.data.get('progress'),dict):
                saved_task['shot_batch_progress']=result.data['progress']
        workflow_engine.save(wf_saved)
        registered=asset_manager.register_execution(task,valid_outputs,project_id=wf.get('plan_id'),data=result.data) if valid_outputs else []
        out['assets']=registered
        self.last_result=out; return out

    def test_model(self,model_id):
        model=model_hub.get(model_id)
        if not model: return {'success':False,'message':'模型不存在'}
        adapter=ADAPTERS.get(model.get('adapter'))
        if not adapter: return {'success':False,'message':f"适配器不存在：{model.get('adapter')}"}
        return adapter.test(model).to_dict()

execution_engine=ExecutionEngine()
