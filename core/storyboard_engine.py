import json, math, os, tempfile
from datetime import datetime
from uuid import uuid4
from core.config import PROJECT_DIR
from core.bible_manager import bible_manager
from core.prompt_engine import prompt_engine
from core.continuity_engine import continuity_engine

STORYBOARD_DIR = os.path.join(PROJECT_DIR, 'storyboards')
os.makedirs(STORYBOARD_DIR, exist_ok=True)

class StoryboardDirector:
    SHOT_TYPES = ['Hook特写','环境建立','人物进入','异常发现','冲突升级','核心动作','反转信息','悬念收尾']
    SHOT_SIZES = ['大特写 ECU','特写 CU','近景 MCU','中景 MS','中近景 MCS','全景 WS','大全景 EWS']
    CAMERA_ANGLES = ['平视','低机位','高机位','俯拍','仰拍','荷兰角']
    MOVEMENTS = ['固定','缓慢推进','缓慢拉远','横移','跟拍','环绕','快速推镜','手持轻晃']
    COMPOSITIONS = ['中心构图','三分法','对称构图','前景遮挡','引导线','留白构图']
    RHYTHMS = ['慢','舒缓','正常','紧张','快速','爆发']

    def __init__(self, directory=STORYBOARD_DIR):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, storyboard_id):
        if not isinstance(storyboard_id, str) or not storyboard_id.strip() or storyboard_id in {'.', '..'}:
            raise ValueError('storyboard_id 无效')
        if '/' in storyboard_id or chr(92) in storyboard_id or chr(0) in storyboard_id:
            raise ValueError('storyboard_id 不允许包含路径分隔符或空字符')
        return os.path.join(self.directory, storyboard_id + '.json')

    def create_from_plan(self, plan):
        if not isinstance(plan, dict):
            raise ValueError('导演计划必须是对象')
        raw_shots = plan.get('shots', [])
        if not isinstance(raw_shots, list):
            raise ValueError('导演计划 shots 必须是列表')
        shots=[]
        seen_ids=set()
        characters=plan.get('characters',[]); scenes=plan.get('scenes',[])
        for i, raw in enumerate(raw_shots):
            if not isinstance(raw, dict):
                raise ValueError(f'第 {i+1} 个镜头必须是对象')
            shot_id=raw.get('id') or f'SHOT-{i+1:04d}'
            if not isinstance(shot_id, str) or not shot_id.strip():
                raise ValueError(f'第 {i+1} 个镜头 ID 无效')
            if shot_id in seen_ids:
                raise ValueError(f'镜头 ID 重复：{shot_id}')
            seen_ids.add(shot_id)
            try:
                duration=float(raw.get('duration', 5.0))
            except (TypeError, ValueError):
                raise ValueError(f'镜头 {shot_id} 时长必须是数字')
            if not math.isfinite(duration) or duration <= 0 or duration > 3600:
                raise ValueError(f'镜头 {shot_id} 时长必须大于 0 且不超过 3600 秒')
            # Keep explicit IDs from the plan. The old conditional discarded a valid
            # scene_id whenever the plan omitted its scenes array.
            scene_id = raw.get('scene_id')
            if not scene_id and scenes:
                fallback_scene = scenes[min(i // 3, len(scenes) - 1)]
                scene_id = fallback_scene.get('id', '') if isinstance(fallback_scene, dict) else ''
            # Preserve multi-character shot assignments instead of silently replacing
            # them with the first character in the plan.
            raw_character_ids = raw.get('character_ids')
            if isinstance(raw_character_ids, list):
                char_ids = [
                    item.get('id') if isinstance(item, dict) else item
                    for item in raw_character_ids
                ]
                char_ids = [item for item in char_ids if isinstance(item, str) and item]
            else:
                char_ids = [c['id'] for c in characters[:1] if isinstance(c, dict) and c.get('id')]
            shot={
                'id': shot_id, 'index': i+1,
                'duration': duration, 'type': raw.get('type', self.SHOT_TYPES[i%len(self.SHOT_TYPES)]),
                'scene_id': scene_id, 'character_ids': char_ids,
                'shot_size': self.SHOT_SIZES[min(i, len(self.SHOT_SIZES)-1)],
                'camera_angle': self.CAMERA_ANGLES[i % len(self.CAMERA_ANGLES)],
                'camera_movement': self.MOVEMENTS[i % len(self.MOVEMENTS)],
                'composition': self.COMPOSITIONS[i % len(self.COMPOSITIONS)],
                'action': raw.get('action','推动剧情并强化镜头信息'),
                'visual_prompt': raw.get('visual_prompt', raw.get('prompt', '')),
                'prompt': raw.get('prompt', raw.get('visual_prompt', '')),
                'voiceover': raw.get('voiceover', raw.get('narration', '')),
                'expression': raw.get('expression','自然且符合剧情情绪'),
                'lighting': raw.get('lighting','电影感主光，轮廓光清晰'),
                'sound': raw.get('sound','环境声 + 关键动作音效'),
                'rhythm': self.RHYTHMS[min(i, len(self.RHYTHMS)-1)],
                'transition_in': '硬切' if i else '开场', 'transition_out': '硬切',
                'dialogue': raw.get('dialogue',''), 'director_note': raw.get('director_note',''),
                'screen_direction': raw.get('screen_direction','右向'), 'axis_break': bool(raw.get('axis_break', False)),
                'continuity_sensitive': bool(raw.get('continuity_sensitive', True)),
                'status':'planned', 'prompt_status':'pending'
            }
            shots.append(shot)
        storyboard={'storyboard_id':'STORYBOARD-'+uuid4().hex[:8].upper(),'version':1,'created_at':datetime.now().isoformat(timespec='seconds'),'updated_at':datetime.now().isoformat(timespec='seconds'),'plan_id':plan.get('plan_id'),'title':plan.get('title'),'shots':shots}
        return self.save(storyboard)

    def save(self, storyboard):
        if not isinstance(storyboard, dict):
            raise ValueError('分镜必须是对象')
        storyboard=dict(storyboard)
        path=self._path(storyboard.get('storyboard_id'))
        if not isinstance(storyboard.get('shots'), list):
            raise ValueError('分镜 shots 必须是列表')
        storyboard['updated_at']=datetime.now().isoformat(timespec='seconds')
        fd,tmp_path=tempfile.mkstemp(prefix='.storyboard-',suffix='.tmp',dir=self.directory)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(storyboard,f,ensure_ascii=False,indent=2,allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path,path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return storyboard

    def load(self, storyboard_id):
        try:
            with open(self._path(storyboard_id),encoding='utf-8') as f:return json.load(f)
        except Exception:return None

    def list(self):
        out=[]
        for n in sorted(os.listdir(self.directory), reverse=True):
            if n.endswith('.json'):
                x=self.load(n[:-5])
                if x: out.append(x)
        return out

    def update_shot(self, storyboard_id, shot_index, changes):
        sb=self.load(storyboard_id)
        if not sb:return None
        if 0 <= shot_index < len(sb.get('shots',[])):
            sb['shots'][shot_index].update(changes); sb['version']=int(sb.get('version',1))+1
        return self.save(sb)

    def build_prompt(self, storyboard_id, shot_index, plan=None, model='generic'):
        sb=self.load(storyboard_id)
        if not sb:return None
        shot=sb['shots'][shot_index]
        record=prompt_engine.generate_for_shot(shot, plan, model)
        continuity=continuity_engine.build_prompt_constraints(sb, shot_index)
        record['prompt'] = ', '.join(filter(None,[record.get('prompt',''),shot.get('shot_size'),shot.get('camera_angle'),shot.get('camera_movement'),shot.get('composition'),shot.get('action'),shot.get('expression'),shot.get('lighting'),f"rhythm: {shot.get('rhythm')}"] + continuity))
        record['continuity_constraints'] = continuity
        record['director_shot_spec']={k:shot.get(k) for k in ['shot_size','camera_angle','camera_movement','composition','action','expression','lighting','rhythm','sound','transition_in','transition_out','screen_direction','axis_break','continuity_sensitive']}
        sb['shots'][shot_index]['prompt_status']='ready'; sb['shots'][shot_index]['prompt_id']=record['prompt_id']; self.save(sb)
        return record

    def check_continuity(self, storyboard_id):
        sb=self.load(storyboard_id)
        if not sb: return None
        report=continuity_engine.check_storyboard(sb)
        continuity_engine.save_report(report)
        sb['continuity_score']=report.get('score')
        sb['continuity_report']=report
        self.save(sb)
        return report

storyboard_director=StoryboardDirector()
