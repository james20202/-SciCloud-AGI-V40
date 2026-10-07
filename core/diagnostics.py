from core.model_runtime import model_runtime
from core.model_hub import model_hub

class Diagnostics:
    def run(self):
        s=model_runtime.summary()
        actions=[]
        for row in s['models']:
            if row.get('enabled') and not row['probe']['ready']:
                actions.append({'model_id':row['model_id'],'action':'配置或启动该模型后重新检测','reason':row['probe']['reason']})
        return {'success':s['blocked']==0 or s['ready']>0,'summary':s,'actions':actions}

diagnostics=Diagnostics()
