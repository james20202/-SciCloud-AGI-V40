import os, json
from datetime import datetime
from core.config import PROJECT_DIR
from core.episode_engine import episode_engine
from core.shot_production_engine import shot_production_engine

class AutopilotEngine:
    def __init__(self): self.root=os.path.join(PROJECT_DIR,'autopilot'); os.makedirs(self.root,exist_ok=True)
    def run(self, episode_id, max_cycles=20):
        ep=episode_engine.status(episode_id); log=[]
        # Episode workflow is still the source of truth. Run it first.
        for _ in range(max_cycles):
            if ep.get('status') in ('completed','blocked','failed','paused'): break
            ep=episode_engine.run(episode_id,max_steps=50); log.append({'time':datetime.now().isoformat(timespec='seconds'),'episode_status':ep.get('status'),'progress':ep.get('progress')})
            if ep.get('status')!='running': break
        return {'success':ep.get('status')=='completed','episode':ep,'cycles':len(log),'log':log,'message':'自动驾驶完成' if ep.get('status')=='completed' else '自动驾驶已停止：需要模型能力或人工处理阻塞项'}
autopilot_engine=AutopilotEngine()
