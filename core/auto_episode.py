import json, os
from datetime import datetime
from core.episode_pipeline import episode_pipeline
from core.model_router import model_router

class AutoEpisodeDirector:
    """V40.241-300: one-command episode director.

    Planning is always allowed. Production is executed only when required
    capabilities are actually available. No fake success is returned.
    """
    def __init__(self):
        self.root=os.path.join(episode_pipeline.project_dir,'auto_runs')
        os.makedirs(self.root,exist_ok=True)

    def _now(self): return datetime.now().isoformat(timespec='seconds')
    def _path(self,eid): return os.path.join(self.root,eid+'.json')
    def _save(self,d):
        d['updated_at']=self._now()
        with open(self._path(d['episode_id']),'w',encoding='utf-8') as f:
            json.dump(d,f,ensure_ascii=False,indent=2)
        return d

    def preflight(self):
        skills=['image','video','tts','sound','edit','vision']
        plan=model_router.plan(skills)
        caps={k:bool(v.get('success')) for k,v in plan['routes'].items()}
        return {'success':True,'capabilities':caps,'routes':plan['routes'],'ready_for_media':bool(caps.get('image') or caps.get('video'))}

    def create(self, idea, title=None, duration=60, ratio='9:16'):
        d=episode_pipeline.create(idea,title,duration,ratio)
        eid=d['episode_id']
        run={'episode_id':eid,'idea':idea,'title':d.get('title'),'status':'planned',
             'auto_stage':'plan','created_at':self._now(),'updated_at':self._now(),
             'preflight':self.preflight()}
        return self._save(run)

    def run(self,eid,max_shots=100):
        run=self.load(eid)
        result=episode_pipeline.run(eid,max_shots=max_shots)
        run['pipeline_status']=result.get('status')
        run['progress']=result.get('progress',0)
        run['auto_stage']=result.get('stage')
        run['result']=result
        run['status']='completed' if result.get('status')=='completed' else result.get('status','running')
        return self._save(run)

    def load(self,eid):
        with open(self._path(eid),encoding='utf-8') as f: return json.load(f)

    def status(self,eid):
        run=self.load(eid)
        p=episode_pipeline.status(eid)
        run['pipeline_status']=p.get('status'); run['progress']=p.get('progress',0)
        run['auto_stage']=p.get('stage')
        return self._save(run)

auto_episode_director=AutoEpisodeDirector()
