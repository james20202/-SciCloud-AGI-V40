import json, math, os
from datetime import datetime
from core.workflow_engine import workflow_engine, STATUS_DONE
from core.vision_qc import vision_qc
from core.media_quality_engine import media_quality_engine
from core.shot_contract import normalize_shots, timeline_duration

MEDIA_EXT={'.mp4','.mov','.mkv','.webm','.avi','.m4v','.mp3','.wav','.m4a','.aac','.flac','.png','.jpg','.jpeg','.webp'}
JSON_TASKS={'story','character','scene','storyboard','prompt'}

class QCEngine:
    """V40.9 deterministic production QC. Never claims visual quality without a real vision model."""
    def __init__(self): self.last_result=None

    def _file_check(self,path):
        if not path or not isinstance(path,str): return False, '未提供产物路径'
        path=os.path.abspath(path)
        if not os.path.isfile(path): return False, f'产物不存在：{path}'
        size=os.path.getsize(path)
        if size<=0: return False, f'产物为空：{path}'
        ext=os.path.splitext(path)[1].lower()
        if ext in MEDIA_EXT:
            return True, f'媒体文件存在，大小 {size} bytes'
        if ext=='.json':
            try:
                with open(path,encoding='utf-8') as f: json.load(f)
                return True, 'JSON 结构可读取'
            except Exception as e: return False, f'JSON 无法解析：{e}'
        return True, f'文件存在，大小 {size} bytes'

    def inspect_task(self,wf,task):
        outputs=task.get('outputs') or []
        if not isinstance(outputs, (list, tuple)):
            return {'success':False,'code':'INVALID_OUTPUTS','message':'任务产物必须是路径列表','task_id':task.get('id'),'checks':[]}
        if not outputs:
            return {'success':False,'code':'NO_OUTPUT','message':f"任务 {task.get('id')} 没有登记有效的产物路径列表",'task_id':task.get('id'),'checks':[]}
        checks=[]; ok=True; vision_results=[]; media_results=[]
        expected_duration=None
        if task.get('type') == 'edit':
            raw_expected=task.get('expected_duration_seconds', task.get('target_duration_seconds'))
            if raw_expected is not None:
                try:
                    candidate=float(raw_expected)
                    if math.isfinite(candidate) and candidate > 0:
                        expected_duration=candidate
                except (TypeError, ValueError, OverflowError):
                    expected_duration=None
        for item in outputs:
            path=item.get('path') if isinstance(item,dict) else item
            good,msg=self._file_check(path)
            checks.append({'path':path,'success':good,'message':msg})
            ok=ok and good
            ext=os.path.splitext(path)[1].lower() if isinstance(path,str) else ''
            if good and ext in {'.mp4','.mov','.mkv','.webm','.avi','.m4v'}:
                media_result=media_quality_engine.inspect(path, expected_duration=expected_duration)
                media_results.append(media_result)
                checks[-1]['media_quality']=media_result
                if not media_result.get('passed'):
                    checks[-1]['success']=False
                    checks[-1]['message']='媒体技术质检未通过：'+str(media_result.get('message') or ', '.join(media_result.get('errors') or []))
                    ok=False
                elif task.get('type') == 'edit' and media_result.get('has_audio_stream') is False:
                    audio_source_exists = any(
                        isinstance(source_task, dict)
                        and source_task.get('type') in {'voice', 'sound'}
                        and source_task.get('status') == STATUS_DONE
                        and any(
                            isinstance(source_path, str)
                            and os.path.isfile(source_path)
                            and os.path.getsize(source_path) > 0
                            and os.path.splitext(source_path)[1].lower() in {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.opus'}
                            for source_item in (source_task.get('outputs') or [])
                            for source_path in [source_item.get('path') if isinstance(source_item, dict) else source_item]
                        )
                        for source_task in (wf.get('tasks') or [])
                    )
                    if audio_source_exists:
                        checks[-1]['success']=False
                        checks[-1]['message']='最终成片缺少音轨，但工作流已有配音/音效源文件'
                        ok=False
            elif good and ext in {'.mp3','.wav','.m4a','.aac','.flac','.ogg','.opus'}:
                media_result=media_quality_engine.inspect_audio(path, expected_duration=expected_duration)
                media_results.append(media_result)
                checks[-1]['media_quality']=media_result
                if not media_result.get('passed'):
                    checks[-1]['success']=False
                    checks[-1]['message']='音频技术质检未通过：'+str(media_result.get('message') or ', '.join(media_result.get('errors') or []))
                    ok=False
            if good and ext in {'.png','.jpg','.jpeg','.webp'}:
                vr=vision_qc.analyze(path, {'task_id':task.get('id'),'task_type':task.get('type'),'name':task.get('name','')})
                vision_results.append(vr)
                if vr.get('semantic_checked') and not vr.get('success'): ok=False
        contract_checks=[]
        # Prompt-stage artifacts are the hand-off boundary for shot metadata. Validate
        # their actual JSON payload, not only that the file exists and parses.
        if task.get('type') == 'prompt':
            for item in outputs:
                path=item.get('path') if isinstance(item,dict) else item
                if not isinstance(path,str) or os.path.splitext(path)[1].lower() != '.json' or not os.path.isfile(path):
                    continue
                try:
                    with open(path,encoding='utf-8') as handle:
                        payload=json.load(handle)
                    shots=payload.get('prompts') if isinstance(payload,dict) else None
                    canonical=normalize_shots(shots)
                    measured=timeline_duration(canonical)
                    timing=payload.get('timing_summary',{})
                    reported=timing.get('actual_duration_seconds') if isinstance(timing,dict) else None
                    if reported is not None and abs(float(reported)-measured)>0.05:
                        raise ValueError('timing_summary 与镜头时长合计不一致')
                    target_duration=timing.get('target_duration_seconds') if isinstance(timing,dict) else None
                    if target_duration is not None:
                        target_duration=float(target_duration)
                        if not math.isfinite(target_duration) or target_duration <= 0:
                            raise ValueError('目标时长必须是大于 0 的有限数值')
                        allowed_delta=max(1.0,target_duration*0.02)
                        delta=measured-target_duration
                        if abs(delta)>allowed_delta:
                            raise ValueError(
                                f'镜头总时长 {measured:g}s 与目标 {target_duration:g}s 不匹配，'
                                f'相差 {delta:+g}s，允许误差 ±{allowed_delta:g}s'
                            )
                    audio_timeline=payload.get('audio_timeline')
                    if audio_timeline is not None:
                        if not isinstance(audio_timeline,dict):
                            raise ValueError('audio_timeline 必须是对象')
                        audio_total=float(audio_timeline.get('total_duration_seconds'))
                        if abs(audio_total-measured)>0.05:
                            raise ValueError('audio_timeline 与镜头时长合计不一致')
                        if audio_timeline.get('shot_count') != len(canonical):
                            raise ValueError('audio_timeline 镜头数量与 prompts 不一致')
                        if not isinstance(payload.get('subtitle_srt_draft',''),str):
                            raise ValueError('subtitle_srt_draft 必须是字符串')
                    contract_checks.append({'path':path,'success':True,'shot_count':len(canonical),'duration_seconds':measured,'audio_timeline_checked':audio_timeline is not None})
                except Exception as exc:
                    ok=False
                    contract_checks.append({'path':path,'success':False,'message':f'镜头生产契约检查失败：{exc}'})
        return {'success':ok,'code':'OK' if ok else 'INVALID_OUTPUT','message':'产物与视觉审核通过' if ok and vision_results and any(v.get('semantic_checked') for v in vision_results) else ('产物级检查通过（未配置视觉模型）' if ok else '发现产物或视觉异常'),'task_id':task.get('id'),'checks':checks,'shot_contract_checks':contract_checks,'vision':vision_results,'media_quality':media_results}

    def _structural_check(self, wf):
        tasks=wf.get('tasks', [])
        if not isinstance(tasks, list):
            return {'success':False,'code':'INVALID_TASKS','message':'工作流 tasks 必须是列表'}
        if any(not isinstance(task, dict) for task in tasks):
            return {'success':False,'code':'INVALID_TASKS','message':'工作流包含非对象任务'}
        for task in tasks:
            if not isinstance(task.get('type'), str) or not task.get('type').strip():
                return {'success':False,'code':'INVALID_TASK_TYPE','message':f"任务 {task.get('id')} 缺少有效 type"}
            if not isinstance(task.get('depends_on', []), list) or any(not isinstance(dep, str) for dep in task.get('depends_on', [])):
                return {'success':False,'code':'INVALID_DEPENDENCIES','message':f"任务 {task.get('id')} 的 depends_on 格式无效"}
        ids=[task.get('id') for task in tasks]
        if any(not isinstance(task_id, str) or not task_id.strip() for task_id in ids):
            return {'success':False,'code':'INVALID_TASK_IDS','message':'工作流任务 ID 缺失或格式无效'}
        if len(set(ids)) != len(ids):
            return {'success':False,'code':'INVALID_TASK_IDS','message':'工作流任务 ID 重复'}

        workflow_storyboard_id=wf.get('storyboard_id')
        for task in tasks:
            task_storyboard_id=task.get('storyboard_id')
            if task_storyboard_id and workflow_storyboard_id and task_storyboard_id != workflow_storyboard_id:
                return {'success':False,'code':'STORYBOARD_LINK_MISMATCH','message':f"任务 {task.get('id')} 的 storyboard_id 与工作流不一致"}

        # Guard against stale/corrupt persisted states where a downstream task
        # was marked done even though another task in a required stage is not.
        for task in tasks:
            if task.get('status') != STATUS_DONE or task.get('type') == 'qc':
                continue
            for dependency_type in task.get('depends_on', []):
                prerequisites=[candidate for candidate in tasks if candidate.get('type') == dependency_type]
                if not prerequisites or not all(candidate.get('status') == STATUS_DONE for candidate in prerequisites):
                    return {
                        'success':False,
                        'code':'DEPENDENCY_INCOMPLETE',
                        'message':f"任务 {task.get('id')} 已标记完成，但依赖阶段 {dependency_type} 缺失或尚未全部完成",
                        'task_id':task.get('id'),
                    }
        return {'success':True,'code':'STRUCTURE_OK','message':'任务 ID、分镜关联和阶段依赖结构有效'}

    def inspect_workflow(self,wid):
        try:
            wf=workflow_engine.load(wid)
        except Exception as exc:
            final={
                'success':False,
                'workflow_id':wid,
                'message':f'无法读取工作流，QC 中止：{exc}',
                'failed_check':{'success':False,'code':'WORKFLOW_LOAD_FAILED'},
                'results':[],
                'checked_at':datetime.now().isoformat(timespec='seconds'),
            }
            self.last_result=final
            return final
        failed=[task for task in wf.get('tasks',[]) if isinstance(task,dict) and task.get('status')=='failed' and task.get('type')!='qc']
        if failed:
            task=failed[0]
            final={'success':False,'workflow_id':wid,'message':f"工作流存在失败任务：{task.get('name') or task.get('id')}；{task.get('error') or '执行失败'}",'failed_task_id':task.get('id'),'failed_task_type':task.get('type'),'results':[],'checked_at':datetime.now().isoformat(timespec='seconds')}
            self.last_result=final
            return final
        structure=self._structural_check(wf)
        if not structure.get('success'):
            final={'success':False,'workflow_id':wid,'message':structure['message'],'failed_check':structure,'results':[],'checked_at':datetime.now().isoformat(timespec='seconds')}
            self.last_result=final
            return final
        done=[t for t in wf.get('tasks',[]) if t.get('status')==STATUS_DONE and t.get('type')!='qc']
        results=[]
        # QC all completed executable tasks; planning artifacts are real JSON outputs too.
        for task in done:
            r=self.inspect_task(wf,task); results.append(r)
            if not r['success']:
                final={'success':False,'workflow_id':wid,'message':r['message'],'failed_task_id':task.get('id'),'failed_task_type':task.get('type'),'results':results,'checked_at':datetime.now().isoformat(timespec='seconds')}
                self.last_result=final; return final
        # Structural workflow checks.
        if not done:
            final={'success':False,'workflow_id':wid,'message':'没有已完成任务可供 QC','results':[],'checked_at':datetime.now().isoformat(timespec='seconds')}
            self.last_result=final; return final
        semantic=any(v.get('semantic_checked') for r in results for v in r.get('vision',[]))
        final={'success':True,'workflow_id':wid,'message':'QC 通过：包含视觉模型审核' if semantic else 'QC 通过：真实产物存在且可读取；未执行主观视觉质量判断','results':results,'checked_at':datetime.now().isoformat(timespec='seconds'),'vision_enabled':semantic}
        self.last_result=final; return final

qc_engine=QCEngine()
