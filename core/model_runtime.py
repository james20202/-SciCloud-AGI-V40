import json, os, shutil, subprocess, time
from urllib import request
from core.model_hub import model_hub

class ModelRuntime:
    """Real local capability discovery. It never reports a capability as ready without probing it."""
    def probe(self, model):
        adapter=model.get('adapter')
        if adapter=='ffmpeg':
            p=shutil.which(model.get('command') or 'ffmpeg')
            return {'model_id':model['model_id'],'ready':bool(p),'reason':p or 'ffmpeg not found','details':{'path':p}}
        if adapter=='comfyui':
            url=(model.get('endpoint') or 'http://127.0.0.1:8188').rstrip('/')+'/system_stats'
            try:
                with request.urlopen(url,timeout=2) as r:
                    return {'model_id':model['model_id'],'ready':r.status==200,'reason':'ComfyUI API reachable','details':json.loads(r.read().decode())}
            except Exception as e:
                return {'model_id':model['model_id'],'ready':False,'reason':str(e),'details':{}}
        if adapter in ('tts_command','vision_command'):
            cmd=(model.get('command') or '').strip()
            if not cmd:return {'model_id':model['model_id'],'ready':False,'reason':'command not configured','details':{}}
            exe=shutil.which(cmd.split()[0])
            return {'model_id':model['model_id'],'ready':bool(exe),'reason':exe or 'executable not found','details':{'path':exe}}
        return {'model_id':model['model_id'],'ready':False,'reason':'unknown adapter','details':{}}

    def scan(self):
        return [dict(m,**{'probe':self.probe(m)}) for m in model_hub.list()]

    def summary(self):
        rows=self.scan()
        return {'total':len(rows),'enabled':sum(bool(x.get('enabled')) for x in rows),'ready':sum(bool(x['probe']['ready']) for x in rows),'blocked':sum(not x['probe']['ready'] for x in rows),'models':rows}

model_runtime=ModelRuntime()
