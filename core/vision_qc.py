import json, os, shlex, subprocess
from datetime import datetime
from core.config import DATA_DIR

VISION_DIR=os.path.join(DATA_DIR,'vision')
os.makedirs(VISION_DIR,exist_ok=True)

class VisionQC:
    """Optional local vision adapter. Never invents semantic scores when no vision model is configured."""
    def __init__(self, config_dir=VISION_DIR): self.config_dir=config_dir
    def _cfg(self):
        p=os.path.join(self.config_dir,'vision_config.json')
        if not os.path.exists(p): return {'enabled':False,'command':''}
        try:
            with open(p,encoding='utf-8') as f:return json.load(f)
        except Exception:return {'enabled':False,'command':''}
    def save_config(self,cfg):
        with open(os.path.join(self.config_dir,'vision_config.json'),'w',encoding='utf-8') as f: json.dump(cfg,f,ensure_ascii=False,indent=2)
    def analyze(self,path,context=None):
        cfg=self._cfg(); context=context or {}
        if not cfg.get('enabled') or not cfg.get('command'):
            return {'available':False,'success':True,'semantic_checked':False,'message':'未配置本地视觉模型，仅执行技术级检查','path':path}
        if not os.path.isfile(path): return {'available':True,'success':False,'semantic_checked':True,'message':'视觉分析输入不存在','path':path}
        payload={'path':os.path.abspath(path),'context':context}
        try:
            cmd=shlex.split(cfg['command'])+[json.dumps(payload,ensure_ascii=False)]
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=int(cfg.get('timeout',120)))
            if p.returncode!=0: return {'available':True,'success':False,'semantic_checked':True,'message':f'视觉模型命令失败：{p.stderr.strip() or p.stdout.strip()}','path':path}
            data=json.loads(p.stdout)
            score=float(data.get('score',100))
            threshold=float(cfg.get('pass_score',70))
            data.update({'available':True,'success':score>=threshold,'semantic_checked':True,'score':score,'threshold':threshold,'path':path,'analyzed_at':datetime.now().isoformat(timespec='seconds')})
            data.setdefault('issues',[]); data.setdefault('suggestions',[])
            return data
        except Exception as e:
            return {'available':True,'success':False,'semantic_checked':True,'message':f'视觉模型解析失败：{e}','path':path}

vision_qc=VisionQC()
