import json, os, re
from datetime import datetime
from uuid import uuid4
from core.config import DATA_DIR
from core.bible_manager import bible_manager

PROMPT_DIR=os.path.join(DATA_DIR,'prompts')
os.makedirs(PROMPT_DIR,exist_ok=True)

DEFAULT_TEMPLATES={
 'cinematic_shot': {
   'name':'电影感镜头',
   'template':'{{subject}}, {{action}}, {{scene}}, {{camera}}, {{lighting}}, {{style}}, cinematic composition, detailed, consistent character',
   'negative':'deformed hands, extra fingers, duplicate person, distorted face, blurry, low quality, text, watermark'
 },
 'character': {
   'name':'人物设定',
   'template':'{{character}}, {{costume}}, {{expression}}, full body character design, consistent face, {{style}}, detailed',
   'negative':'different face, different costume, extra limbs, deformed hands, blurry, watermark'
 },
 'scene': {
   'name':'场景设定',
   'template':'{{scene}}, {{time}}, {{weather}}, {{lighting}}, cinematic environment design, {{style}}, detailed',
   'negative':'people, text, watermark, low quality, distorted architecture'
 }
}

class PromptEngine:
    def __init__(self, prompt_dir=PROMPT_DIR):
        self.prompt_dir=prompt_dir
        os.makedirs(prompt_dir,exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self):
        for key,val in DEFAULT_TEMPLATES.items():
            path=os.path.join(self.prompt_dir,f'{key}.json')
            if not os.path.exists(path):
                self.save_template({'id':'PROMPT-'+uuid4().hex[:8].upper(),'key':key,'version':1,**val})

    def _path(self,key): return os.path.join(self.prompt_dir,f'{key}.json')

    def save_template(self,tpl):
        with open(self._path(tpl['key']),'w',encoding='utf-8') as f: json.dump(tpl,f,ensure_ascii=False,indent=2)
        return tpl

    def list_templates(self):
        out=[]
        for n in sorted(os.listdir(self.prompt_dir)):
            if n.endswith('.json'):
                try:
                    with open(os.path.join(self.prompt_dir,n),encoding='utf-8') as f: out.append(json.load(f))
                except Exception: pass
        return out

    def render(self, template_key, variables, model='generic'):
        path=self._path(template_key)
        if os.path.exists(path):
            with open(path,encoding='utf-8') as f: tpl=json.load(f)
        else: tpl=DEFAULT_TEMPLATES.get(template_key,DEFAULT_TEMPLATES['cinematic_shot'])
        def repl(m): return str(variables.get(m.group(1),m.group(0)))
        prompt=re.sub(r'\{\{\s*([\w]+)\s*\}\}',repl,tpl['template'])
        negative=re.sub(r'\{\{\s*([\w]+)\s*\}\}',repl,tpl.get('negative',''))
        return {'prompt_id':'PROMPT-'+uuid4().hex[:8].upper(),'template_id':tpl.get('id'),'template_key':template_key,'version':tpl.get('version',1),'model':model,'prompt':prompt,'negative_prompt':negative,'variables':variables,'created_at':datetime.now().isoformat(timespec='seconds')}

    def generate_for_shot(self, shot, plan=None, model='generic'):
        idea=(plan or {}).get('idea','')
        genre=(plan or {}).get('intent',{}).get('genre','原创短剧')
        scene='核心故事场景'
        if plan:
            for s in plan.get('scenes',[]):
                if s.get('id')==shot.get('scene_id'): scene=s.get('name',scene)
        variables={
          'subject':'主角与核心冲突',
          'action':shot.get('type','剧情动作'),
          'scene':scene,
          'camera':'medium shot, cinematic camera movement',
          'lighting':'dramatic cinematic lighting',
          'style':f'{genre}, 东方影视风格',
          'character':'主角',
          'costume':'符合世界观的服装',
          'expression':'紧张而警觉',
          'time':'夜晚' if ('恐怖' in genre or '灵异' in genre) else '适合剧情的时间',
          'weather':'自然环境'
        }
        character_ids = shot.get('character_ids', []) or ([shot.get('character_id')] if shot.get('character_id') else [])
        scene_ids = shot.get('scene_ids', []) or ([shot.get('scene_id')] if shot.get('scene_id') else [])
        constraints = bible_manager.prompt_constraints(character_ids, scene_ids)
        result=self.render('cinematic_shot',variables,model)
        if constraints['positive']:
            result['prompt'] += ', ' + ', '.join(constraints['positive'])
        if constraints['negative']:
            result['negative_prompt'] += ', ' + ', '.join(constraints['negative'])
        result['source_shot_id']=shot.get('id')
        result['character_ids']=character_ids
        result['scene_ids']=scene_ids
        result['bible_context']=bible_manager.context(character_ids, scene_ids)
        result['idea']=idea
        return result

    def optimize(self,prompt_record, extra=''):
        prompt_record=dict(prompt_record)
        additions=[]
        if extra: additions.append(extra.strip())
        additions.append('maintain character identity and visual continuity')
        additions.append('clear foreground, midground and background separation')
        prompt_record['prompt']=prompt_record.get('prompt','')+', '+', '.join(additions)
        prompt_record['version']=int(prompt_record.get('version',1))+1
        prompt_record['optimized']=True
        prompt_record['optimized_at']=datetime.now().isoformat(timespec='seconds')
        return prompt_record

prompt_engine=PromptEngine()
