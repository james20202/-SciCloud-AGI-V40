import json, os
from datetime import datetime
from core.model_hub import model_hub
from core.model_runtime import model_runtime

class ModelRouter:
    """Routes production skills to real enabled+ready local capabilities; never fabricates a provider."""
    def candidates(self, skill):
        mapping={'image':'image_video','video':'image_video','tts':'tts','vision':'vision','sound':'media','edit':'media'}
        wanted=mapping.get(skill, skill)
        rows=[]
        for m in model_hub.list():
            if not m.get('enabled') or m.get('type')!=wanted: continue
            probe=model_runtime.probe(m)
            rows.append((m,probe))
        rows.sort(key=lambda x: (not x[1].get('ready'), x[0].get('model_id','')))
        return rows
    def route(self, skill, preferred=None):
        if preferred:
            m=model_hub.get(preferred)
            if m and m.get('enabled'):
                p=model_runtime.probe(m)
                if p.get('ready'): return {'success':True,'skill':skill,'model':m,'probe':p}
        rows=self.candidates(skill)
        if rows and rows[0][1].get('ready'):
            return {'success':True,'skill':skill,'model':rows[0][0],'probe':rows[0][1]}
        enabled=[m for m in model_hub.list() if m.get('enabled')]
        return {'success':False,'blocked':True,'skill':skill,'message':f'没有可用的本地 {skill} 能力','enabled_models':len(enabled), 'checked':len(rows)}
    def plan(self, skills):
        return {'created_at':datetime.now().isoformat(timespec='seconds'),'routes':{s:self.route(s) for s in skills}}
model_router=ModelRouter()
