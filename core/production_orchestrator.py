import json, os
from datetime import datetime
from core.config import PROJECT_DIR
from core.model_router import model_router

class ProductionOrchestrator:
    """Turns an episode production plan into executable capability decisions."""
    STAGES=('image','video','tts','sound','edit','vision')
    def __init__(self): self.root=os.path.join(PROJECT_DIR,'production_runs'); os.makedirs(self.root,exist_ok=True)
    def create(self, episode_id, shots=None, options=None):
        shots=shots or []; options=options or {}
        run_id='RUN-'+datetime.now().strftime('%Y%m%d%H%M%S%f')
        plan=self._plan(options)
        state={'run_id':run_id,'episode_id':episode_id,'created_at':datetime.now().isoformat(timespec='seconds'),'status':'ready' if all(x['ready'] for x in plan.values()) else 'blocked','stages':plan,'shots':shots,'results':[]}
        self._save(state); return state
    def _plan(self, options):
        out={}
        for s in self.STAGES:
            if s=='vision' and not options.get('vision',False):
                out[s]={'ready':True,'optional':True,'message':'未启用视觉审核，不阻塞生产'}; continue
            r=model_router.route(s, options.get(s+'_model'))
            out[s]={'ready':bool(r.get('success')),'blocked':bool(r.get('blocked')),'model_id':(r.get('model') or {}).get('model_id'),'message':r.get('message','ready')}
        return out
    def status(self, run_id):
        p=os.path.join(self.root,run_id+'.json')
        if not os.path.exists(p): return None
        with open(p,encoding='utf-8') as f:return json.load(f)
    def _save(self,state):
        with open(os.path.join(self.root,state['run_id']+'.json'),'w',encoding='utf-8') as f: json.dump(state,f,ensure_ascii=False,indent=2)
        return state
    def refresh(self,run_id):
        st=self.status(run_id)
        if not st:return None
        for skill in self.STAGES:
            if st['stages'].get(skill,{}).get('optional'):continue
            r=model_router.route(skill)
            st['stages'][skill].update({'ready':bool(r.get('success')),'blocked':bool(r.get('blocked')),'model_id':(r.get('model') or {}).get('model_id'),'message':r.get('message','ready')})
        st['status']='ready' if all(v.get('ready') for v in st['stages'].values()) else 'blocked'
        return self._save(st)
production_orchestrator=ProductionOrchestrator()
