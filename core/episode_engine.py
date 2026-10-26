import json, os, time
from datetime import datetime
from core.config import PROJECT_DIR
from core.director_plan import director_plan_engine
from core.workflow_engine import workflow_engine
from core.auto_director import auto_director

class EpisodeEngine:
    """V40.31-40.40 one-click episode production orchestrator.

    It creates a durable episode record, a Director Plan and a Workflow, then
    delegates real execution to the existing Auto Director. No generation is
    fabricated: unavailable model adapters fail explicitly.
    """
    def __init__(self, project_dir=PROJECT_DIR):
        self.project_dir = project_dir
        self.root = os.path.join(project_dir, 'episodes')
        os.makedirs(self.root, exist_ok=True)

    def _now(self):
        return datetime.now().isoformat(timespec='seconds')

    def _path(self, episode_id):
        return os.path.join(self.root, f'{episode_id}.json')

    def _save(self, episode):
        episode['updated_at'] = self._now()
        with open(self._path(episode['episode_id']), 'w', encoding='utf-8') as f:
            json.dump(episode, f, ensure_ascii=False, indent=2)
        return episode

    def load(self, episode_id):
        with open(self._path(episode_id), encoding='utf-8') as f:
            return json.load(f)

    def create_episode(self, idea, title=None, duration=60, ratio='9:16'):
        plan = director_plan_engine.create_plan(idea, title=title, duration=duration, ratio=ratio)
        wf = workflow_engine.create_from_plan(plan)
        eid = 'EP-' + plan['plan_id'].replace('PLAN-', '')
        episode = {
            'episode_id': eid,
            'title': plan['title'],
            'idea': idea,
            'duration_seconds': plan.get('intent', {}).get('duration_seconds', duration),
            'aspect_ratio': ratio,
            'plan_id': plan['plan_id'],
            'workflow_id': wf['workflow_id'],
            'status': 'planned',
            'created_at': self._now(),
            'updated_at': self._now(),
            'attempt': 0,
            'last_result': None,
            'resume_safe': True,
        }
        return self._save(episode)

    def status(self, episode_id):
        ep = self.load(episode_id)
        wf = workflow_engine.load(ep['workflow_id'])
        ep['workflow_status'] = wf.get('status')
        ep['progress'] = workflow_engine.progress(wf)
        ep['task_count'] = len(wf.get('tasks', []))
        ep['done_count'] = sum(1 for t in wf.get('tasks', []) if t.get('status') == 'done')
        ep['failed_count'] = sum(1 for t in wf.get('tasks', []) if t.get('status') == 'failed')
        if wf.get('status') == 'completed': ep['status'] = 'completed'
        elif wf.get('paused'): ep['status'] = 'paused'
        elif ep.get('failed_count', 0): ep['status'] = 'failed'
        elif ep.get('last_result') and not ep['last_result'].get('success', True): ep['status'] = 'blocked'
        else: ep['status'] = 'running' if ep.get('attempt', 0) else 'planned'
        return self._save(ep)

    def run(self, episode_id, max_steps=50):
        ep = self.load(episode_id)
        ep['attempt'] = int(ep.get('attempt', 0)) + 1
        ep['status'] = 'running'
        self._save(ep)
        result = auto_director.run(ep['workflow_id'], max_steps=max_steps)
        ep['last_result'] = result
        self._save(ep)
        return self.status(episode_id)

    def pause(self, episode_id):
        ep = self.load(episode_id)
        workflow_engine.pause(ep['workflow_id'])
        ep['status'] = 'paused'
        return self._save(ep)

    def resume(self, episode_id, max_steps=50):
        ep = self.load(episode_id)
        workflow_engine.resume(ep['workflow_id'])
        return self.run(episode_id, max_steps=max_steps)

    def retry_failed(self, episode_id):
        ep = self.load(episode_id)
        wf = workflow_engine.load(ep['workflow_id'])
        failed = [t for t in wf.get('tasks', []) if t.get('status') == 'failed']
        ready = [t for t in wf.get('tasks', []) if t.get('status') == 'ready']
        for task in failed:
            workflow_engine.retry_task(ep['workflow_id'], task['id'])
        retried = [t['id'] for t in failed] + [t['id'] for t in ready]
        ep['status'] = 'ready'
        ep['last_result'] = {'success': True, 'retried_tasks': retried, 'note': 'ready/failed tasks remain executable after capability is enabled'}
        return self._save(ep)

    def list_episodes(self):
        result = []
        for name in sorted(os.listdir(self.root), reverse=True):
            if name.endswith('.json'):
                try: result.append(self.status(name[:-5]))
                except Exception: pass
        return result

episode_engine = EpisodeEngine()
