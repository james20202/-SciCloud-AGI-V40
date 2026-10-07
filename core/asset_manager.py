import json
import os
import shutil
from datetime import datetime
from uuid import uuid4
from core.config import DATA_DIR, PROJECT_DIR, OUTPUT_DIR

ASSET_DB = os.path.join(DATA_DIR, 'assets.json')
ASSET_ROOT = os.path.join(DATA_DIR, 'assets')
os.makedirs(ASSET_ROOT, exist_ok=True)

class AssetManager:
    """V40.4 asset registry: stable IDs, metadata, entity versions and result registration."""
    def __init__(self):
        self.root = PROJECT_DIR
        self.db = ASSET_DB
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.db):
            self._save([])

    def _load(self):
        try:
            with open(self.db, encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, assets):
        os.makedirs(os.path.dirname(self.db), exist_ok=True)
        tmp = self.db + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(assets, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.db)

    def list_assets(self, asset_type=None, entity_id=None):
        items = self._load()
        if asset_type:
            items = [a for a in items if a.get('type') == asset_type]
        if entity_id:
            items = [a for a in items if a.get('entity_id') == entity_id]
        return sorted(items, key=lambda x: x.get('created_at',''), reverse=True)

    def get(self, asset_id):
        return next((a for a in self._load() if a.get('asset_id') == asset_id), None)

    def _next_version(self, entity_id):
        versions = [int(a.get('version', 0)) for a in self._load() if a.get('entity_id') == entity_id]
        return max(versions or [0]) + 1

    def register(self, asset_type, name, source=None, entity_id=None, metadata=None, project_id=None, version=None):
        assets = self._load()
        entity_id = entity_id or f'ASSET-{uuid4().hex[:8].upper()}'
        version = int(version or self._next_version(entity_id))
        asset_id = f'ASSET-{uuid4().hex[:8].upper()}'
        now = datetime.now().isoformat(timespec='seconds')
        item = {
            'asset_id': asset_id,
            'entity_id': entity_id,
            'type': asset_type,
            'name': name or entity_id,
            'version': version,
            'status': 'ready',
            'source': source,
            'project_id': project_id,
            'metadata': metadata or {},
            'created_at': now,
            'updated_at': now,
        }
        assets.append(item)
        self._save(assets)
        return item

    def register_result_file(self, path, asset_type='result', name=None, project_id=None, metadata=None):
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            return None
        return self.register(asset_type, name or os.path.basename(path), source=path,
                             project_id=project_id, metadata=metadata or {'size': os.path.getsize(path)})

    def register_plan_entity(self, entity, entity_type, plan_id, project_id=None):
        mapping = {'character': 'character', 'scene': 'scene'}
        asset_type = mapping.get(entity_type, entity_type)
        return self.register(asset_type, entity.get('name', entity.get('id','')), entity_id=entity.get('id'),
                             project_id=project_id or plan_id, metadata=dict(entity, plan_id=plan_id))

    def register_execution(self, task, outputs, project_id=None, data=None):
        created = []
        for path in outputs or []:
            if isinstance(path, str) and os.path.isfile(path):
                created.append(self.register_result_file(path, asset_type=task.get('type','result'),
                                                         project_id=project_id,
                                                         metadata={'task_id': task.get('id'), 'data': data or {}}))
        return [x for x in created if x]

    def stats(self):
        assets = self._load()
        return {
            'total': len(assets),
            'character': sum(a.get('type') == 'character' for a in assets),
            'scene': sum(a.get('type') == 'scene' for a in assets),
            'image': sum(a.get('type') == 'image' for a in assets),
            'video': sum(a.get('type') == 'video' for a in assets),
            'voice': sum(a.get('type') == 'voice' for a in assets),
            'other': sum(a.get('type') not in {'character','scene','image','video','voice'} for a in assets),
        }

    # Backward-compatible project helpers
    def get_projects(self):
        if not os.path.exists(self.root): return []
        return [x for x in os.listdir(self.root) if os.path.isdir(os.path.join(self.root, x))]

    def get_episodes(self, project):
        path=os.path.join(self.root, project)
        if not os.path.exists(path): return []
        return [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]

    def count_assets(self, project=None):
        if not project:
            s=self.stats(); return {'剧本':0,'角色':s['character'],'分镜':0,'素材':s['image']+s['video'],'视频':s['video']}
        result={'剧本':0,'角色':0,'分镜':0,'素材':0,'视频':0}
        for a in self._load():
            if a.get('project_id') not in (project, None): continue
            if a.get('type') == 'character': result['角色'] += 1
            elif a.get('type') == 'video': result['视频'] += 1; result['素材'] += 1
            elif a.get('type') == 'image': result['素材'] += 1
            elif a.get('type') == 'storyboard': result['分镜'] += 1
        return result

asset_manager=AssetManager()
