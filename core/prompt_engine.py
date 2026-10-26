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
        """Generate an image prompt without dropping canonical shot/story context."""
        plan = plan if isinstance(plan, dict) else {}
        shot = shot if isinstance(shot, dict) else {}
        intent = plan.get('intent') if isinstance(plan.get('intent'), dict) else {}
        idea = str(plan.get('idea') or '')
        genre = str(intent.get('genre') or '原创短剧')
        scene = '核心故事场景'
        scene_record = {}
        for candidate in plan.get('scenes', []) if isinstance(plan.get('scenes'), list) else []:
            if isinstance(candidate, dict) and candidate.get('id') == shot.get('scene_id'):
                scene_record = candidate
                scene = str(candidate.get('name') or scene)
                break

        characters = plan.get('characters') if isinstance(plan.get('characters'), list) else []
        raw_character_ids = shot.get('character_ids', [])
        if not isinstance(raw_character_ids, list):
            raw_character_ids = []
        if not raw_character_ids and shot.get('character_id'):
            raw_character_ids = [shot.get('character_id')]
        character_ids = [
            item.get('id') if isinstance(item, dict) else item
            for item in raw_character_ids
        ]
        character_ids = [item for item in character_ids if isinstance(item, str) and item]
        character_records = [
            item for item in characters
            if isinstance(item, dict) and item.get('id') in character_ids
        ]
        character_descriptions = [
            '：'.join(str(value) for value in (item.get('name'), item.get('description'), item.get('costume')) if value)
            for item in character_records
        ]
        character_context = '；'.join(character_descriptions) or str(shot.get('character_description') or '主角')
        visual_description = str(shot.get('visual_prompt') or shot.get('prompt') or '').strip()
        action = str(shot.get('action') or shot.get('type') or '剧情动作').strip()
        expression = str(shot.get('expression') or '符合剧情情绪').strip()
        variables = {
          'subject': visual_description or character_context or '主角与核心冲突',
          'action': action,
          'scene': '，'.join(filter(None, [scene, str(scene_record.get('description') or scene_record.get('purpose') or '')])),
          'camera': str(shot.get('camera') or 'medium shot, cinematic camera movement'),
          'lighting': str(shot.get('lighting') or 'dramatic cinematic lighting'),
          'style': f'{genre}, 东方影视风格',
          'character': character_context,
          'costume': '；'.join(str(item.get('costume')) for item in character_records if item.get('costume')) or '符合世界观的服装',
          'expression': expression,
          'time': str(shot.get('time') or ('夜晚' if ('恐怖' in genre or '灵异' in genre) else '适合剧情的时间')),
          'weather': str(shot.get('weather') or '自然环境'),
          'visual_prompt': visual_description,
          'dialogue': str(shot.get('dialogue') or ''),
          'voiceover': str(shot.get('voiceover') or shot.get('narration') or ''),
          'director_note': str(shot.get('director_note') or ''),
          'shot_type': str(shot.get('type') or ''),
          'shot_id': str(shot.get('shot_id') or shot.get('id') or ''),
        }
        scene_ids = shot.get('scene_ids', []) or ([shot.get('scene_id')] if shot.get('scene_id') else [])
        constraints = bible_manager.prompt_constraints(character_ids, scene_ids)
        result = self.render('cinematic_shot', variables, model)
        # Keep the image prompt grounded in the actual visual description even when
        # a user's saved template does not expose the optional {{visual_prompt}} slot.
        prompt_parts = [result.get('prompt', ''), visual_description, character_context, action, expression]
        result['prompt'] = ', '.join(dict.fromkeys(part.strip() for part in prompt_parts if isinstance(part, str) and part.strip()))
        if constraints.get('positive'):
            result['prompt'] += ', ' + ', '.join(constraints['positive'])
        if constraints.get('negative'):
            result['negative_prompt'] += ', ' + ', '.join(constraints['negative'])
        result['source_shot_id'] = variables['shot_id'] or None
        result['character_ids'] = character_ids
        result['scene_ids'] = scene_ids
        result['bible_context'] = bible_manager.context(character_ids, scene_ids)
        result['idea'] = idea
        # Dialogue and narration are production metadata, not text to render into an image.
        result['dialogue'] = variables['dialogue']
        result['voiceover'] = variables['voiceover']
        result['director_note'] = variables['director_note']
        result['shot_context'] = {
            'visual_prompt': visual_description, 'action': action, 'expression': expression,
            'scene_id': shot.get('scene_id'), 'scene_name': scene,
            'character_ids': character_ids, 'duration_seconds': shot.get('duration_seconds', shot.get('duration')),
            'dialogue': variables['dialogue'], 'voiceover': variables['voiceover'],
        }
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
