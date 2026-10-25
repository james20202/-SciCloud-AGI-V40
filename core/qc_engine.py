import json, os
from datetime import datetime
from core.workflow_engine import workflow_engine, STATUS_DONE
from core.vision_qc import vision_qc
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
        if not isinstance(outputs, list) or not outputs:
            return {'success':False,'code':'NO_OUTPUT','message':f"任务 {task.get('id')} 没有登记有效的产物路径列表",'task_id':task.get('id'),'checks':[]}
        checks=[]; ok=True; vision_results=[]
        for item in outputs:
            path=item.get('path') if isinstance(item,dict) else item
            good,msg=self._file_check(path)
            checks.append({'path':path,'success':good,'message':msg})
            ok=ok and good
            if good and os.path.splitext(path)[1].lower() in {'.png','.jpg','.jpeg','.webp'}:
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
                    contract_checks.append({'path':path,'success':True,'shot_count':len(canonical),'duration_seconds':measured})
                except Exception as exc:
                    ok=False
                    contract_checks.append({'path':path,'success':False,'message':f'镜头生产契约检查失败：{exc}'})
        return {'success':ok,'code':'OK' if ok else 'INVALID_OUTPUT','message':'产物与视觉审核通过' if ok and vision_results and any(v.get('semantic_checked') for v in vision_results) else ('产物级检查通过（未配置视觉模型）' if ok else '发现产物或视觉异常'),'task_id':task.get('id'),'checks':checks,'shot_contract_checks':contract_checks,'vision':vision_results}

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
