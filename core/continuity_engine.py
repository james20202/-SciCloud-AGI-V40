import json, os
from datetime import datetime
from uuid import uuid4
from core.config import PROJECT_DIR
from core.bible_manager import bible_manager

CONTINUITY_DIR = os.path.join(PROJECT_DIR, 'continuity_reports')
os.makedirs(CONTINUITY_DIR, exist_ok=True)

class ContinuityEngine:
    """检查连续镜头中的人物、场景、方向和视觉状态，并生成可注入 Prompt 的约束。"""
    def _bible(self, kind, item_id):
        try:
            return bible_manager.get(kind, item_id) or {}
        except Exception:
            return {}

    def _constraints_for_shot(self, shot):
        constraints=[]
        for cid in shot.get('character_ids', []):
            c=self._bible('character', cid)
            if c:
                constraints += [x for x in [c.get('appearance'), c.get('hair'), c.get('costume'), c.get('weapon'), c.get('personality'), c.get('positive_constraints')] if x]
        for sid in [shot.get('scene_id')]:
            if sid:
                s=self._bible('scene', sid)
                if s:
                    constraints += [x for x in [s.get('architecture'), s.get('time'), s.get('weather'), s.get('lighting'), s.get('atmosphere'), s.get('positive_constraints')] if x]
        return constraints

    def check_storyboard(self, storyboard):
        shots=storyboard.get('shots', [])
        issues=[]; warnings=[]
        for i, shot in enumerate(shots):
            if i == 0: continue
            prev=shots[i-1]
            if prev.get('character_ids') and shot.get('character_ids') and prev.get('character_ids') != shot.get('character_ids'):
                warnings.append(self._item('character_change', i, '人物连续性变化', f"上一镜人物 {prev.get('character_ids')} → 本镜 {shot.get('character_ids')}，请确认是否为有意切换。"))
            if prev.get('scene_id') and shot.get('scene_id') and prev.get('scene_id') != shot.get('scene_id'):
                warnings.append(self._item('scene_change', i, '场景切换', f"上一镜场景 {prev.get('scene_id')} → 本镜 {shot.get('scene_id')}。"))
            # 轴线/运动方向：用显式 screen_direction 字段承载，缺失不判错
            pd, cd = prev.get('screen_direction'), shot.get('screen_direction')
            if pd and cd and pd != cd and not shot.get('axis_break'):
                issues.append(self._item('direction_break', i, '人物方向可能跳轴', f"上一镜方向 {pd}，本镜方向 {cd}。若非刻意跳轴，请调整机位或增加过渡镜头。"))
            # 核心视觉字段突变
            for field, label in [('shot_size','景别'),('camera_angle','机位'),('lighting','光线')]:
                a,b=prev.get(field),shot.get(field)
                if a and b and a != b and shot.get('continuity_sensitive', True):
                    warnings.append(self._item('visual_change', i, f'{label}发生变化', f"{label}: {a} → {b}。建议确认节奏与剪辑意图。"))
            # 镜头过短却承担核心动作
            try:
                if float(shot.get('duration',0)) < 1.2 and shot.get('action') and len(str(shot.get('action'))) > 18:
                    warnings.append(self._item('duration', i, '镜头信息过载', '镜头时长偏短，但动作描述较复杂，可能影响生成与剪辑。'))
            except Exception:
                pass
        return {'checked_at': datetime.now().isoformat(timespec='seconds'), 'storyboard_id': storyboard.get('storyboard_id'), 'issues': issues, 'warnings': warnings, 'score': max(0, 100-len(issues)*18-len(warnings)*4)}

    def _item(self, code, index, title, message):
        return {'id':f'CONT-{uuid4().hex[:8].upper()}', 'shot_index':index, 'code':code, 'title':title, 'message':message}

    def build_prompt_constraints(self, storyboard, shot_index):
        shots=storyboard.get('shots', []); shot=shots[shot_index]
        parts=[]
        if shot_index > 0:
            prev=shots[shot_index-1]
            if prev.get('character_ids') and shot.get('character_ids'):
                parts.append(f"保持人物身份与外观连续：{', '.join(prev.get('character_ids',[]))} → {', '.join(shot.get('character_ids',[]))}")
            if prev.get('scene_id') == shot.get('scene_id') and shot.get('scene_id'):
                parts.append(f"保持场景空间连续：{shot.get('scene_id')}")
            if prev.get('screen_direction') and shot.get('screen_direction') and prev.get('screen_direction') == shot.get('screen_direction'):
                parts.append(f"保持屏幕运动方向连续：{shot.get('screen_direction')}")
        parts += self._constraints_for_shot(shot)
        return list(dict.fromkeys(parts))

    def save_report(self, report):
        path=os.path.join(CONTINUITY_DIR, report.get('storyboard_id','UNKNOWN')+'.json')
        with open(path,'w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2)
        return path

continuity_engine=ContinuityEngine()
