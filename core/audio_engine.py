import os
from core.local_media_engine import local_media_engine

class AudioEngine:
    def normalize(self, audio, output): return local_media_engine.normalize_audio(audio,output)
    def mix(self, voice, music, output):
        if not os.path.isfile(voice) or not os.path.isfile(music): return {'success':False,'message':'人声或音乐不存在'}
        os.makedirs(os.path.dirname(output) or '.',exist_ok=True)
        return local_media_engine._run(['ffmpeg','-y','-i',voice,'-i',music,'-filter_complex','[0:a]volume=1.0[a0];[1:a]volume=0.25[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=2[a]','-map','[a]','-c:a','aac',output],900)
audio_engine=AudioEngine()
