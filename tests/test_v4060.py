from core.consistency_engine import consistency_engine
from core.publish_pack_engine import publish_pack_engine
assert consistency_engine.lock('CHAR-TEST','character',{'hair':'black'})['fingerprint']
print('V40.60_CORE_OK')
