import json, os, time, urllib.request, urllib.error
from pathlib import Path

class LocalExecutor:
    def __init__(self, base_dir=None, timeout=30):
        self.base_dir=Path(base_dir or Path(__file__).resolve().parents[1])
        self.state_dir=self.base_dir/'projects'/'model_runs'; self.state_dir.mkdir(parents=True,exist_ok=True)
        self.timeout=timeout
    def _url(self, base, path): return base.rstrip('/')+'/'+path.lstrip('/')
    def probe_comfyui(self, base='http://127.0.0.1:8188'):
        try:
            with urllib.request.urlopen(self._url(base,'system_stats'),timeout=self.timeout) as r:
                return {'ok':True,'status':r.status,'data':json.loads(r.read().decode())}
        except Exception as e: return {'ok':False,'error':str(e)}
    def submit_comfyui(self, workflow, base='http://127.0.0.1:8188', client_id='scicloud-v40'):
        payload={'prompt':workflow,'client_id':client_id}
        req=urllib.request.Request(self._url(base,'prompt'),data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as r: data=json.loads(r.read().decode())
            run={'run_id':data.get('prompt_id',''),'engine':'comfyui','status':'submitted','created_at':time.time()}
            self._save(run); return run
        except Exception as e: return {'status':'blocked','error':str(e)}
    def history(self,prompt_id,base='http://127.0.0.1:8188'):
        try:
            with urllib.request.urlopen(self._url(base,'history/'+prompt_id),timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e: return {'error':str(e)}
    def _save(self,run):
        if run.get('run_id'): (self.state_dir/(run['run_id']+'.json')).write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
