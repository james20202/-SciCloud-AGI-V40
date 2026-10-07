import os, tempfile
from core.model_router import model_router
from core.production_orchestrator import ProductionOrchestrator
p=model_router.plan(['image','video','tts','sound','edit','vision'])
assert set(p['routes'])=={'image','video','tts','sound','edit','vision'}
o=ProductionOrchestrator(); old=o.root; o.root=tempfile.mkdtemp(prefix='v4160_')
st=o.create('EP-TEST-160',shots=[{'shot_id':'SHOT-001'}])
assert st['status'] in ('ready','blocked') and st['run_id'].startswith('RUN-')
assert os.path.exists(os.path.join(o.root,st['run_id']+'.json'))
o.root=old
print('V40.160_MODEL_ROUTER_OK')
