import json, os
from datetime import datetime
from core.config import PROJECT_DIR

class ProductionManifest:
    def __init__(self): self.root=os.path.join(PROJECT_DIR,'manifests'); os.makedirs(self.root,exist_ok=True)
    def create(self, episode_id, shots, output=None):
        path=os.path.join(self.root,episode_id+'.json')
        data={'episode_id':episode_id,'created_at':datetime.now().isoformat(timespec='seconds'),'output':output,'shots':shots}
        with open(path,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
        return data
    def load(self, episode_id):
        with open(os.path.join(self.root,episode_id+'.json'),encoding='utf-8') as f: return json.load(f)
    def validate(self, episode_id):
        d=self.load(episode_id); problems=[]
        for s in d.get('shots',[]):
            for a in s.get('artifacts',[]):
                p=a.get('path')
                if not p or not os.path.isfile(p) or os.path.getsize(p)<=0: problems.append({'shot_id':s.get('shot_id'),'path':p})
        return {'success':not problems,'problems':problems,'shot_count':len(d.get('shots',[]))}
production_manifest=ProductionManifest()
