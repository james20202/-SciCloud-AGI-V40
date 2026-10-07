import json, time
from urllib import request
from core.model_hub import model_hub

class ComfyUIRunner:
    def __init__(self): self.model_key='MODEL-COMFYUI'
    def _url(self, model, path): return model.get('endpoint','http://127.0.0.1:8188').rstrip('/')+path
    def submit_and_wait(self, workflow, timeout=1800, poll=2):
        model=model_hub.get(self.model_key)
        if not model or not model.get('enabled'):
            return {'success':False,'blocked':True,'message':'ComfyUI 未启用'}
        if not workflow: return {'success':False,'message':'缺少 ComfyUI workflow JSON'}
        payload={'prompt':workflow}
        try:
            req=request.Request(self._url(model,'/prompt'),data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with request.urlopen(req,timeout=10) as r: submitted=json.loads(r.read().decode())
            pid=submitted.get('prompt_id')
            if not pid: return {'success':False,'message':'ComfyUI 没有返回 prompt_id'}
            started=time.time()
            while time.time()-started<timeout:
                with request.urlopen(self._url(model,'/history/'+pid),timeout=10) as r: history=json.loads(r.read().decode())
                item=history.get(pid)
                if item:
                    status=item.get('status',{})
                    if status.get('completed') or item.get('outputs'):
                        return {'success':True,'prompt_id':pid,'history':item,'outputs':item.get('outputs',{})}
                    if status.get('status_str')=='error': return {'success':False,'message':'ComfyUI 工作流执行失败','history':item,'prompt_id':pid}
                time.sleep(poll)
            return {'success':False,'message':'ComfyUI 执行超时','prompt_id':pid}
        except Exception as e: return {'success':False,'message':f'ComfyUI 执行异常：{e}'}

comfyui_runner=ComfyUIRunner()
