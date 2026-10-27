import json, os
from datetime import datetime
from uuid import uuid4
from core.config import DATA_DIR

MODEL_DIR = os.path.join(DATA_DIR, 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

DEFAULT_MODELS = [
    {'model_id':'MODEL-LOCAL-FFMPEG','name':'FFmpeg 本地媒体引擎','type':'media','provider':'local','adapter':'ffmpeg','enabled':True,'description':'本地视频/音频封装、裁剪、拼接等媒体处理。','command':'ffmpeg'},
    {'model_id':'MODEL-COMFYUI','name':'ComfyUI 本地图像/视频','type':'image_video','provider':'local','adapter':'comfyui','enabled':False,'description':'连接本机 ComfyUI API，具体模型由 ComfyUI 工作流决定。','endpoint':'http://127.0.0.1:8188'},
    {'model_id':'MODEL-LOCAL-TTS','name':'本地 TTS 命令适配器','type':'tts','provider':'local','adapter':'tts_command','enabled':False,'description':'调用本机 TTS 命令；不绑定特定厂商。','command':''},
    {'model_id':'MODEL-LOCAL-VISION','name':'本地视觉导演审核','type':'vision','provider':'local','adapter':'vision_command','enabled':False,'description':'可接本地视觉模型命令，对人物一致性、构图、镜头、光影、动作等返回结构化评分；未配置时不虚构视觉评分。','command':''},
]

class ModelHub:
    def __init__(self, model_dir=MODEL_DIR):
        self.model_dir=model_dir
        os.makedirs(model_dir, exist_ok=True)
        self._ensure_defaults()

    def _path(self, model_id):
        return os.path.join(self.model_dir, f'{model_id}.json')

    def _ensure_defaults(self):
        for model in DEFAULT_MODELS:
            path=self._path(model['model_id'])
            if not os.path.exists(path):
                model=dict(model); model['created_at']=datetime.now().isoformat(timespec='seconds')
                self.save(model)

    def save(self, model):
        model=dict(model)
        model.setdefault('model_id','MODEL-'+uuid4().hex[:8].upper())
        model['updated_at']=datetime.now().isoformat(timespec='seconds')
        with open(self._path(model['model_id']),'w',encoding='utf-8') as f:
            json.dump(model,f,ensure_ascii=False,indent=2)
        return model

    def list(self):
        out=[]
        for n in sorted(os.listdir(self.model_dir)):
            if n.endswith('.json'):
                try:
                    with open(os.path.join(self.model_dir,n),encoding='utf-8') as f: out.append(json.load(f))
                except Exception: pass
        return out

    def get(self, model_id):
        path=self._path(model_id)
        if not os.path.exists(path): return None
        with open(path,encoding='utf-8') as f: return json.load(f)

    def set_enabled(self, model_id, enabled):
        model=self.get(model_id)
        if not model: raise KeyError(model_id)
        model['enabled']=bool(enabled)
        return self.save(model)

    def find_for_skill(self, skill_type, preferred=None):
        if preferred:
            m=self.get(preferred)
            if m and m.get('enabled'): return m
        mapping={'image':'image_video','video':'image_video','tts':'tts','voice':'tts','sound':'media','edit':'media','qc':'media','vision':'vision'}
        wanted=mapping.get(skill_type)
        for m in self.list():
            if m.get('enabled') and (m.get('type')==wanted or m.get('adapter')==skill_type): return m
        return None

model_hub=ModelHub()
