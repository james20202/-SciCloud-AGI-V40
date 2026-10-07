import os,tempfile
from core.model_runtime import ModelRuntime

def test_ffmpeg_probe():
    r=ModelRuntime().probe({'model_id':'T','adapter':'ffmpeg','command':'ffmpeg'})
    assert 'ready' in r and 'reason' in r

def test_unconfigured_tts_blocked():
    r=ModelRuntime().probe({'model_id':'TTS','adapter':'tts_command','command':''})
    assert r['ready'] is False

if __name__=='__main__':
    test_ffmpeg_probe(); test_unconfigured_tts_blocked(); print('V40.130_MODEL_RUNTIME_OK')
