import os, json, shutil, zipfile
from datetime import datetime
from core.config import PROJECT_DIR, OUTPUT_DIR
class PublishPackEngine:
    def build(self, episode_id, final_video=None):
        src=os.path.join(PROJECT_DIR,'episodes',episode_id+'.json')
        if not os.path.exists(src): return {'success':False,'message':'Episode 不存在'}
        outdir=os.path.join(OUTPUT_DIR,'publish',episode_id); os.makedirs(outdir,exist_ok=True)
        shutil.copy2(src,os.path.join(outdir,'episode.json'))
        manifest={'episode_id':episode_id,'created_at':datetime.now().isoformat(timespec='seconds'),'final_video':None}
        if final_video and os.path.isfile(final_video): shutil.copy2(final_video,os.path.join(outdir,os.path.basename(final_video))); manifest['final_video']=os.path.basename(final_video)
        with open(os.path.join(outdir,'manifest.json'),'w',encoding='utf-8') as f: json.dump(manifest,f,ensure_ascii=False,indent=2)
        zip_path=os.path.join(OUTPUT_DIR,episode_id+'_publish.zip')
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
            for name in os.listdir(outdir): z.write(os.path.join(outdir,name),name)
        return {'success':True,'package':zip_path,'directory':outdir,'manifest':manifest}
publish_pack_engine=PublishPackEngine()
