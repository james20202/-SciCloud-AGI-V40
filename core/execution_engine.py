import json
import os
from abc import ABC, abstractmethod
from datetime import datetime

from core.adapters import ComfyUIAdapter, FFmpegAdapter, TTSCommandAdapter
from core.asset_manager import asset_manager
from core.config import PROJECT_DIR
from core.director_plan import director_plan_engine
from core.model_hub import model_hub
from core.qc_engine import qc_engine
from core.skill_registry import skill_registry
from core.workflow_engine import workflow_engine

ADAPTERS = {
    'ffmpeg': FFmpegAdapter(),
    'comfyui': ComfyUIAdapter(),
    'tts_command': TTSCommandAdapter(),
}

TASK_TO_SKILL = {
    'story': 'SKILL-STORY',
    'character': 'SKILL-STORY',
    'scene': 'SKILL-STORY',
    'storyboard': 'SKILL-STORY',
    'prompt': 'SKILL-PROMPT',
    'image': 'SKILL-IMAGE',
    'video': 'SKILL-VIDEO',
    'voice': 'SKILL-TTS',
    'sound': 'SKILL-SOUND',
    'edit': 'SKILL-EDIT',
    'qc': 'SKILL-QC',
    'publish': 'SKILL-QC',
}


class BaseTaskExecutor(ABC):
    """Task strategy interface for execution tasks."""

    key = 'base'

    @abstractmethod
    def can_handle(self, task_type):
        raise NotImplementedError

    @abstractmethod
    def execute(self, engine, wid, wf, task):
        raise NotImplementedError


class PlanningTaskExecutor(BaseTaskExecutor):
    key = 'planning'

    def can_handle(self, task_type):
        return task_type in {'story', 'character', 'scene', 'storyboard', 'prompt'}

    def execute(self, engine, wid, wf, task):
        workflow_engine.start_task(wid, task['id'])
        path = engine._artifact(
            wf,
            task,
            'execution',
            {
                'task': task,
                'executed_at': datetime.now().isoformat(timespec='seconds'),
                'mode': 'local-planning-artifact',
            },
        )

        task['outputs'] = [path]
        wf_saved = workflow_engine.load(wid)
        current_task = next((t for t in wf_saved['tasks'] if t['id'] == task['id']), None)
        if current_task is not None:
            current_task['outputs'] = [path]
        workflow_engine.save(wf_saved)

        registered = []
        if task.get('type') in {'character', 'scene'}:
            plans = director_plan_engine.load_plans()
            plan = next((p for p in plans if p.get('plan_id') == wf.get('plan_id')), None)
            if plan:
                entity_key = 'characters' if task.get('type') == 'character' else 'scenes'
                for entity in plan.get(entity_key, []):
                    registered.append(asset_manager.register_plan_entity(entity, task.get('type'), wf.get('plan_id')))

        registered += asset_manager.register_execution(task, [path], project_id=wf.get('plan_id'))
        workflow_engine.complete_task(wid, task['id'])

        return {
            'success': True,
            'message': '本地规划任务执行完成，结果已登记到资产中心',
            'outputs': [path],
            'assets': registered,
        }


class QCTaskExecutor(BaseTaskExecutor):
    key = 'qc'

    def can_handle(self, task_type):
        return task_type == 'qc'

    def execute(self, engine, wid, wf, task):
        workflow_engine.start_task(wid, task['id'])
        result = qc_engine.inspect_workflow(wid)
        path = engine._artifact(wf, task, 'qc_report', result)

        task_snapshot = workflow_engine.load(wid)
        current_task = next((t for t in task_snapshot['tasks'] if t['id'] == task['id']), None)
        if current_task is not None:
            current_task['outputs'] = [path]

        if result.get('success'):
            workflow_engine.complete_task(wid, task['id'])
        else:
            workflow_engine.fail_task(wid, task['id'], result.get('message', 'QC failed'))

        out = dict(result)
        out['outputs'] = [path]
        return out


class AdapterTaskExecutor(BaseTaskExecutor):
    key = 'adapter'

    def can_handle(self, task_type):
        planning_types = {'story', 'character', 'scene', 'storyboard', 'prompt', 'qc'}
        return task_type not in planning_types

    def execute(self, engine, wid, wf, task):
        model = model_hub.find_for_skill(task.get('type'), task.get('model_id'))
        if not model:
            return {'success': False, 'message': f"没有可用的本地模型/适配器：{task.get('type')}。请到 Model Hub 启用。"}

        adapter = ADAPTERS.get(model.get('adapter'))
        if not adapter:
            return {'success': False, 'message': f"未注册适配器：{model.get('adapter')}"}

        workflow_engine.start_task(wid, task['id'])
        result = adapter.execute(model, task, {'workflow': task.get('workflow'), 'command': task.get('command')})

        if result.success:
            workflow_engine.complete_task(wid, task['id'])
        else:
            workflow_engine.fail_task(wid, task['id'], result.message)

        out = result.to_dict()
        out['model_id'] = model.get('model_id')
        out['adapter'] = model.get('adapter')

        wf_saved = workflow_engine.load(wid)
        current_task = next((t for t in wf_saved['tasks'] if t['id'] == task['id']), None)
        if current_task is not None:
            current_task['outputs'] = list(result.outputs or [])
        workflow_engine.save(wf_saved)

        registered = asset_manager.register_execution(task, result.outputs, project_id=wf.get('plan_id'), data=result.data)
        out['assets'] = registered
        return out


class ExecutionEngine:
    def __init__(self):
        self.last_result = None
        self.executors = [
            PlanningTaskExecutor(),
            QCTaskExecutor(),
            AdapterTaskExecutor(),
        ]

    def _artifact(self, wf, task, kind, data):
        d = os.path.join(PROJECT_DIR, 'execution', wf['workflow_id'])
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{task['id']}_{kind}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def _resolve_executor(self, task):
        for executor in self.executors:
            if executor.can_handle(task.get('type')):
                return executor
        return AdapterTaskExecutor()

    def execute(self, wid, task_id):
        wf = workflow_engine.load(wid)
        task = next((x for x in wf['tasks'] if x['id'] == task_id), None)
        if not task:
            return {'success': False, 'message': '任务不存在'}
        if task.get('status') != 'ready':
            return {'success': False, 'message': f"任务当前状态为 {task.get('status')}，不可执行。"}

        skill_id = TASK_TO_SKILL.get(task.get('type'))
        skill = skill_registry.get(skill_id) if skill_id else None
        if not skill or not skill.get('enabled'):
            return {'success': False, 'message': f'Skill 未启用：{skill_id}'}

        executor = self._resolve_executor(task)
        result = executor.execute(self, wid, wf, task)
        self.last_result = result
        return result

    def test_model(self, model_id):
        model = model_hub.get(model_id)
        if not model:
            return {'success': False, 'message': '模型不存在'}
        adapter = ADAPTERS.get(model.get('adapter'))
        if not adapter:
            return {'success': False, 'message': f"适配器不存在：{model.get('adapter')}"}
        return adapter.test(model).to_dict()


execution_engine = ExecutionEngine()

__all__ = ['ExecutionEngine', 'execution_engine']
