import os, json, hashlib
from datetime import datetime
from core.config import PROJECT_DIR

class ConsistencyEngine:
    """Build durable character/scene locks without pretending to generate media."""
    def __init__(self, root=None):
        self.root=root or os.path.join(PROJECT_DIR,'consistency'); os.makedirs(self.root,exist_ok=True)
    def _path(self, entity_id): return os.path.join(self.root, entity_id+'.json')
    def _fingerprint(self, data): return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]
    def lock(self, entity_id, kind, constraints=None, references=None):
        data={'entity_id':entity_id,'kind':kind,'constraints':constraints or {},'references':references or [],'locked_at':datetime.now().isoformat(timespec='seconds')}
        data['fingerprint']=self._fingerprint(data)
        with open(self._path(entity_id),'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        return data
    def load(self, entity_id):
        with open(self._path(entity_id),encoding='utf-8') as f:return json.load(f)
    def build_shot_constraints(self, character_ids=None, scene_ids=None):
        out=[]
        for eid in (character_ids or [])+(scene_ids or []):
            try:
                x=self.load(eid); out.append({'entity_id':eid,'kind':x['kind'],'fingerprint':x['fingerprint'],'constraints':x['constraints']})
            except Exception: pass
        return {'locked_entities':out,'constraint_text':'\n'.join(str(x['constraints']) for x in out)}
consistency_engine=ConsistencyEngine()
