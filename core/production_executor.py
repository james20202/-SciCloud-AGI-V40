import json,time,uuid
from pathlib import Path
from .local_executor import LocalExecutor

class ProductionExecutor:
    def __init__(self, base_dir=None):
        self.base_dir=Path(base_dir or Path(__file__).resolve().parents[1]); self.root=self.base_dir/'projects'/'production_runs'; self.root.mkdir(parents=True,exist_ok=True)
        self.local=LocalExecutor(self.base_dir)
    def create_run(self, episode_id, shots):
        rid='RUN-'+uuid.uuid4().hex[:10].upper(); data={'run_id':rid,'episode_id':episode_id,'status':'ready','shots':shots,'results':{},'created_at':time.time()}; self._save(data); return data
    def status(self,run_id): return self._load(run_id)
    def execute_shot(self,run_id,shot_id,workflow=None,engine='comfyui'):
        data=self._load(run_id)
        if not data: return {'status':'blocked','error':'run_not_found'}
        if engine=='comfyui':
            if not workflow: return self._update(data,shot_id,{'status':'blocked','error':'workflow_missing'})
            result=self.local.submit_comfyui(workflow)
        else: result={'status':'blocked','error':'unsupported_engine'}
        return self._update(data,shot_id,result)
    def _update(self,data,shot_id,result):
        data['results'][shot_id]=result; data['status']='running' if result.get('status') in ('submitted','running') else result.get('status','blocked'); self._save(data); return result
    def _path(self,rid): return self.root/(rid+'.json')
    def _save(self,d): self._path(d['run_id']).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    def _load(self,rid):
        p=self._path(rid)
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
