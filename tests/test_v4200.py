import tempfile
from pathlib import Path
from core.local_executor import LocalExecutor
from core.production_executor import ProductionExecutor

def main():
    with tempfile.TemporaryDirectory() as d:
        ex=ProductionExecutor(d); run=ex.create_run('EP-1',[{'id':'SHOT-1'}]); assert run['status']=='ready'
        r=ex.execute_shot(run['run_id'],'SHOT-1',None); assert r['status']=='blocked' and r['error']=='workflow_missing'
    print('V40.200_EXECUTOR_CONTRACT_OK')
if __name__=='__main__': main()
