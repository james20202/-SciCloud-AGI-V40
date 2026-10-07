import json, os
from datetime import datetime
from uuid import uuid4
from core.config import DATA_DIR

BIBLE_DIR = os.path.join(DATA_DIR, 'bibles')
CHAR_DIR = os.path.join(BIBLE_DIR, 'characters')
SCENE_DIR = os.path.join(BIBLE_DIR, 'scenes')
for p in (BIBLE_DIR, CHAR_DIR, SCENE_DIR): os.makedirs(p, exist_ok=True)

class BibleManager:
    """Character/Scene Bible: persistent creative constraints with explicit versions."""
    def __init__(self):
        self.char_dir, self.scene_dir = CHAR_DIR, SCENE_DIR

    def _dir(self, kind): return self.char_dir if kind == 'character' else self.scene_dir
    def _new_id(self, kind): return ('CHAR-' if kind == 'character' else 'SCENE-') + uuid4().hex[:8].upper()
    def _path(self, kind, entity_id): return os.path.join(self._dir(kind), entity_id + '.json')

    def _load(self, kind, entity_id):
        p = self._path(kind, entity_id)
        if not os.path.exists(p): return None
        try:
            with open(p, encoding='utf-8') as f: return json.load(f)
        except Exception: return None

    def _save(self, kind, data):
        data = dict(data)
        data['updated_at'] = datetime.now().isoformat(timespec='seconds')
        with open(self._path(kind, data['entity_id']), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def create_character(self, name, **fields):
        entity_id = fields.pop('entity_id', None) or self._new_id('character')
        data = {
            'entity_id': entity_id, 'type': 'character', 'name': name,
            'version': 1, 'status': 'active',
            'identity': fields.pop('identity', ''),
            'appearance': fields.pop('appearance', ''),
            'personality': fields.pop('personality', ''),
            'costume': fields.pop('costume', ''),
            'signature_items': fields.pop('signature_items', []),
            'voice': fields.pop('voice', ''),
            'visual_style': fields.pop('visual_style', ''),
            'reference_assets': fields.pop('reference_assets', []),
            'prompt_constraints': fields.pop('prompt_constraints', []),
            'negative_constraints': fields.pop('negative_constraints', []),
            'notes': fields.pop('notes', ''),
            'created_at': datetime.now().isoformat(timespec='seconds'),
        }
        data.update(fields)
        return self._save('character', data)

    def create_scene(self, name, **fields):
        entity_id = fields.pop('entity_id', None) or self._new_id('scene')
        data = {
            'entity_id': entity_id, 'type': 'scene', 'name': name,
            'version': 1, 'status': 'active',
            'location': fields.pop('location', ''),
            'architecture': fields.pop('architecture', ''),
            'time': fields.pop('time', ''),
            'weather': fields.pop('weather', ''),
            'lighting': fields.pop('lighting', ''),
            'palette': fields.pop('palette', ''),
            'props': fields.pop('props', []),
            'atmosphere': fields.pop('atmosphere', ''),
            'reference_assets': fields.pop('reference_assets', []),
            'prompt_constraints': fields.pop('prompt_constraints', []),
            'negative_constraints': fields.pop('negative_constraints', []),
            'notes': fields.pop('notes', ''),
            'created_at': datetime.now().isoformat(timespec='seconds'),
        }
        data.update(fields)
        return self._save('scene', data)

    def update(self, kind, entity_id, changes, bump_version=True):
        data = self._load(kind, entity_id)
        if not data: return None
        if bump_version: data['version'] = int(data.get('version', 1)) + 1
        data.update(changes)
        return self._save(kind, data)

    def get(self, kind, entity_id): return self._load(kind, entity_id)

    def list(self, kind=None):
        kinds = [kind] if kind else ['character', 'scene']
        out=[]
        for k in kinds:
            for n in sorted(os.listdir(self._dir(k))):
                if n.endswith('.json'):
                    x=self._load(k, n[:-5])
                    if x: out.append(x)
        return sorted(out, key=lambda x: x.get('updated_at',''), reverse=True)

    def context(self, character_ids=None, scene_ids=None):
        chars=[self.get('character', x) for x in (character_ids or [])]
        scenes=[self.get('scene', x) for x in (scene_ids or [])]
        return {'characters':[x for x in chars if x], 'scenes':[x for x in scenes if x]}

    def prompt_constraints(self, character_ids=None, scene_ids=None):
        ctx=self.context(character_ids, scene_ids)
        positive=[]; negative=[]
        for c in ctx['characters']:
            positive += [c.get('appearance',''), c.get('costume',''), c.get('visual_style','')] + c.get('prompt_constraints',[])
            negative += c.get('negative_constraints',[])
        for s in ctx['scenes']:
            positive += [s.get('architecture',''), s.get('lighting',''), s.get('palette',''), s.get('atmosphere','')] + s.get('prompt_constraints',[])
            negative += s.get('negative_constraints',[])
        return {'positive':[x for x in positive if x], 'negative':[x for x in negative if x]}

bible_manager = BibleManager()
