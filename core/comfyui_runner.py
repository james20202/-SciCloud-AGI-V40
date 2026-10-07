import json, os, time, urllib.parse, urllib.request
from pathlib import Path
from core.model_hub import model_hub
from core.comfyui_workflow import build_sd15_txt2img_workflow


class ComfyUIRunner:
    def __init__(self):
        self.model_key = 'MODEL-COMFYUI'

    def _model(self):
        return model_hub.get(self.model_key)

    def _url(self, model, path):
        return model.get('endpoint', 'http://127.0.0.1:8188').rstrip('/') + path

    def test(self):
        model = self._model()
        if not model or not model.get('enabled'):
            return {'success': False, 'blocked': True, 'message': 'ComfyUI 未启用'}
        try:
            with urllib.request.urlopen(self._url(model, '/system_stats'), timeout=5) as r:
                return {'success': r.status == 200, 'message': 'ComfyUI 已连接'}
        except Exception as e:
            return {'success': False, 'blocked': True, 'message': f'ComfyUI 未连接：{e}'}

    def submit_and_wait(self, workflow, timeout=1800, poll=2):
        model = self._model()
        if not model or not model.get('enabled'):
            return {'success': False, 'blocked': True, 'message': 'ComfyUI 未启用'}
        if not workflow:
            return {'success': False, 'message': '缺少 ComfyUI workflow JSON'}
        payload = {'prompt': workflow}
        try:
            req = urllib.request.Request(self._url(model, '/prompt'), data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as r:
                submitted = json.loads(r.read().decode())
            pid = submitted.get('prompt_id')
            if not pid:
                return {'success': False, 'message': 'ComfyUI 没有返回 prompt_id'}
            started = time.time()
            while time.time() - started < timeout:
                with urllib.request.urlopen(self._url(model, '/history/' + pid), timeout=10) as r:
                    history = json.loads(r.read().decode())
                item = history.get(pid)
                if item:
                    status = item.get('status', {})
                    if status.get('completed') or item.get('outputs'):
                        return {'success': True, 'prompt_id': pid, 'history': item, 'outputs': item.get('outputs', {})}
                    if status.get('status_str') == 'error':
                        return {'success': False, 'message': 'ComfyUI 工作流执行失败', 'history': item, 'prompt_id': pid}
                time.sleep(poll)
            return {'success': False, 'message': 'ComfyUI 执行超时', 'prompt_id': pid}
        except Exception as e:
            return {'success': False, 'message': f'ComfyUI 执行异常：{e}'}

    def download_output(self, output, destination):
        model = self._model()
        if not model or not model.get('enabled'):
            return None
        filename = output.get('filename')
        if not filename:
            return None
        params = urllib.parse.urlencode({
            'filename': filename,
            'subfolder': output.get('subfolder', ''),
            'type': output.get('type', 'output'),
        })
        url = self._url(model, '/view?' + params)
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as r:
            data = r.read()
        destination.write_bytes(data)
        return str(destination)

    def generate_image(self, prompt, negative_prompt='', destination=None, **kwargs):
        workflow = build_sd15_txt2img_workflow(prompt, negative_prompt, **kwargs)
        result = self.submit_and_wait(workflow)
        if not result.get('success'):
            return result
        images = []
        for node in (result.get('outputs') or {}).values():
            for image in node.get('images', []) if isinstance(node, dict) else []:
                images.append(image)
        if not images:
            return {'success': False, 'message': 'ComfyUI 完成但没有返回图片', 'prompt_id': result.get('prompt_id')}
        if destination is None:
            return {'success': True, 'prompt_id': result.get('prompt_id'), 'images': images}
        saved = self.download_output(images[0], destination)
        return {'success': bool(saved), 'prompt_id': result.get('prompt_id'), 'path': saved, 'image': images[0]}


comfyui_runner = ComfyUIRunner()
