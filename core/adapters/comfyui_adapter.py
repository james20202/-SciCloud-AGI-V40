import json, uuid, time
from urllib import request
from core.adapters.base import BaseAdapter, AdapterResult
from core.comfyui_workflow import validate_workflow

class ComfyUIAdapter(BaseAdapter):
    key='comfyui'
    def _url(self, model, path): return model.get('endpoint','http://127.0.0.1:8188').rstrip('/')+path
    def test(self, model):
        try:
            with request.urlopen(self._url(model,'/system_stats'), timeout=3) as r:
                return AdapterResult(r.status==200, 'ComfyUI 已连接', data=json.loads(r.read().decode('utf-8')))
        except Exception as e: return AdapterResult(False, f'ComfyUI 未连接：{e}')
    def execute(self, model, task, context):
        workflow=task.get('workflow') or context.get('workflow')
        if isinstance(workflow,str):
            try: workflow=json.loads(workflow)
            except Exception: return AdapterResult(False,'ComfyUI workflow JSON 无法解析。')
        if not workflow: return AdapterResult(False,'ComfyUI 任务缺少 workflow JSON，未执行。')

        validation = validate_workflow(workflow)
        if not validation['valid']:
            return AdapterResult(False, 'ComfyUI workflow 校验失败：' + '; '.join(validation['errors']), data={'validation': validation})

        payload={'prompt':workflow,'client_id':'scicloud-'+uuid.uuid4().hex[:8]}
        try:
            req=request.Request(self._url(model,'/prompt'),data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with request.urlopen(req,timeout=10) as r: result=json.loads(r.read().decode())
            pid=result.get('prompt_id')
            if not pid:return AdapterResult(False,'ComfyUI 未返回 prompt_id。',data=result)
            return AdapterResult(True,'ComfyUI 工作流已提交',data={'prompt_id':pid,'queued':True,'validation':validation})
        except Exception as e:return AdapterResult(False,f'ComfyUI 提交失败：{e}')
    def wait(self,model,prompt_id,timeout=1800,interval=2):
        end=time.time()+timeout
        while time.time()<end:
            try:
                with request.urlopen(self._url(model,'/history/'+prompt_id),timeout=5) as r:
                    data=json.loads(r.read().decode())
                item=data.get(prompt_id)
                if item:
                    status=item.get('status',{})
                    if status.get('completed') or item.get('outputs'):
                        return AdapterResult(True,'ComfyUI 工作流完成',data=item)
                    if status.get('status_str')=='error':return AdapterResult(False,'ComfyUI 工作流失败',data=item)
            except Exception: pass
            time.sleep(interval)
        return AdapterResult(False,'ComfyUI 等待超时。')
