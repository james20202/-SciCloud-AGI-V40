import os, tempfile
from core.media_pipeline import media_pipeline

def main():
    with tempfile.TemporaryDirectory() as d:
        v=os.path.join(d,'clip.mp4'); open(v,'wb').write(b'real-artifact')
        s=media_pipeline.create('EP-TEST',[{'shot_id':'SHOT-0001'}])
        r=media_pipeline.register_artifact(s['pipeline_id'],'SHOT-0001','video',v)
        assert r['success'] and os.path.isabs(r['shot']['artifacts']['video'])
        assert media_pipeline.status(s['pipeline_id'])['shots'][0]['artifacts']['video']==os.path.abspath(v)
        assert not media_pipeline.assemble(s['pipeline_id'])['success']
    print('V40.240_MEDIA_PIPELINE_OK')
if __name__=='__main__': main()
