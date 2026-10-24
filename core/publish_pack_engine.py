import os, json, shutil, zipfile, hashlib
from datetime import datetime
from core.config import PROJECT_DIR, OUTPUT_DIR


class PublishPackEngine:
    """Create a portable episode package with timeline and checksummed provenance."""
    def _sha256(self, path):
        digest=hashlib.sha256()
        with open(path,'rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def build(self, episode_id, final_video=None):
        src=os.path.join(PROJECT_DIR,'episodes',episode_id+'.json')
        if not os.path.exists(src):
            return {'success':False,'message':'Episode 不存在'}
        outdir=os.path.join(OUTPUT_DIR,'publish',episode_id)
        os.makedirs(outdir,exist_ok=True)
        copied=[]
        def copy_asset(path, label=None):
            if not path or not os.path.isfile(path) or os.path.getsize(path)<=0:
                return None
            name=label or os.path.basename(path)
            target=os.path.join(outdir,name)
            if os.path.abspath(path)!=os.path.abspath(target):
                shutil.copy2(path,target)
            copied.append(target)
            return target

        episode_copy=copy_asset(src,'episode.json')
        pipeline_path=os.path.join(PROJECT_DIR,'episode_pipelines',episode_id+'.json')
        pipeline_copy=copy_asset(pipeline_path,'episode_pipeline.json')
        timeline_path=os.path.join(PROJECT_DIR,'episode_pipelines',episode_id,'canonical_timeline.json')
        timeline_copy=copy_asset(timeline_path,'canonical_timeline.json')
        video_copy=copy_asset(final_video) if final_video else None
        audio_dir=os.path.join(PROJECT_DIR,'episode_pipelines',episode_id,'audio')
        subtitle_copy=copy_asset(os.path.join(audio_dir,'dialogue.srt'),'dialogue.srt')
        dialogue_audio_copy=copy_asset(os.path.join(audio_dir,'dialogue_mix.m4a'),'dialogue_mix.m4a')
        manifest={
            'episode_id':episode_id,
            'created_at':datetime.now().astimezone().isoformat(timespec='seconds'),
            'final_video':os.path.basename(video_copy) if video_copy else None,
            'canonical_timeline':os.path.basename(timeline_copy) if timeline_copy else None,
            'subtitles':os.path.basename(subtitle_copy) if subtitle_copy else None,
            'dialogue_audio':os.path.basename(dialogue_audio_copy) if dialogue_audio_copy else None,
            'assets':[]
        }
        for path in copied:
            manifest['assets'].append({
                'filename':os.path.basename(path),
                'size_bytes':os.path.getsize(path),
                'sha256':self._sha256(path)
            })
        manifest_path=os.path.join(outdir,'manifest.json')
        with open(manifest_path,'w',encoding='utf-8') as f:
            json.dump(manifest,f,ensure_ascii=False,indent=2)
        zip_path=os.path.join(OUTPUT_DIR,episode_id+'_publish.zip')
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
            for name in sorted(os.listdir(outdir)):
                path=os.path.join(outdir,name)
                if os.path.isfile(path):
                    z.write(path,name)
        if not os.path.isfile(zip_path) or os.path.getsize(zip_path)<=0:
            return {'success':False,'message':'发布包创建失败或为空','directory':outdir}
        return {'success':True,'package':zip_path,'directory':outdir,'manifest':manifest}

publish_pack_engine=PublishPackEngine()
