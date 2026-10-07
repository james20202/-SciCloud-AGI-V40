import json, os
from datetime import datetime
from core.config import DATA_DIR

SKILL_DIR=os.path.join(DATA_DIR,'skills')
os.makedirs(SKILL_DIR,exist_ok=True)

DEFAULT_SKILLS=[
 {'skill_id':'SKILL-STORY','name':'故事生成','type':'content','description':'生成或完善剧本结构','provider':'builtin','enabled':True},
 {'skill_id':'SKILL-PROMPT','name':'Prompt生成','type':'prompt','description':'根据镜头、人物、场景生成模型Prompt','provider':'builtin','enabled':True},
 {'skill_id':'SKILL-IMAGE','name':'关键画面生成','type':'image','description':'调用图像模型/工作流生成关键帧','provider':'adapter','enabled':True},
 {'skill_id':'SKILL-VIDEO','name':'动态镜头生成','type':'video','description':'调用视频模型/工作流生成镜头','provider':'adapter','enabled':True},
 {'skill_id':'SKILL-TTS','name':'配音生成','type':'audio','description':'调用本地TTS/Voice Clone','provider':'adapter','enabled':True},
 {'skill_id':'SKILL-SOUND','name':'音效与BGM','type':'audio','description':'生成或匹配音效、BGM','provider':'adapter','enabled':True},
 {'skill_id':'SKILL-EDIT','name':'视频剪辑','type':'media','description':'调用FFmpeg/MoviePy完成媒体处理','provider':'builtin','enabled':True},
 {'skill_id':'SKILL-QC','name':'视频质检','type':'qc','description':'检查画面、音频、字幕和连续性','provider':'builtin','enabled':True},
]

class SkillRegistry:
    def __init__(self): self.ensure_defaults()
    def _path(self,sid): return os.path.join(SKILL_DIR,sid+'.json')
    def ensure_defaults(self):
        for s in DEFAULT_SKILLS:
            if not os.path.exists(self._path(s['skill_id'])):
                self.register(s)
    def register(self,skill):
        skill=dict(skill); skill.setdefault('version','1.0.0'); skill['updated_at']=datetime.now().isoformat(timespec='seconds')
        with open(self._path(skill['skill_id']),'w',encoding='utf-8') as f: json.dump(skill,f,ensure_ascii=False,indent=2)
        return skill
    def list(self):
        out=[]
        for n in sorted(os.listdir(SKILL_DIR)):
            if n.endswith('.json'):
                try:
                    with open(os.path.join(SKILL_DIR,n),encoding='utf-8') as f: out.append(json.load(f))
                except Exception: pass
        return out
    def get(self,sid):
        p=self._path(sid)
        if not os.path.exists(p): return None
        with open(p,encoding='utf-8') as f:return json.load(f)
    def set_enabled(self,sid,enabled):
        s=self.get(sid)
        if not s:return None
        s['enabled']=bool(enabled); return self.register(s)

skill_registry=SkillRegistry()
