import json, os, re, tempfile
from datetime import datetime
from uuid import uuid4
from core.config import PROJECT_DIR
from core.local_ollama_director import local_ollama_director

class DirectorPlanEngine:
    def __init__(self, project_dir=PROJECT_DIR):
        self.project_dir = project_dir
        os.makedirs(self.project_dir, exist_ok=True)

    def _pick(self, text, words, default):
        for w in words:
            if w in text:
                return w
        return default

    def create_plan(self, idea, title=None, duration=60, ratio="9:16"):
        idea = (idea or "").strip()
        if not idea:
            raise ValueError("请先填写剧情创意")
        try:
            duration_value = float(duration)
        except (TypeError, ValueError):
            raise ValueError("目标时长必须是有效数字")
        if not 1 <= duration_value <= 3600:
            raise ValueError("目标时长必须在 1 到 3600 秒之间")
        if ratio not in {"9:16", "16:9", "1:1"}:
            raise ValueError("画幅仅支持 9:16、16:9 或 1:1")
        # Keep sub-second precision supported by _shots(); do not silently round
        # user-entered targets to whole seconds. The shot plan is quantized to 0.1s.
        duration = round(duration_value, 1)
        title = title or self._make_title(idea)
        genre = self._pick(idea, ["中式恐怖","修仙","玄幻","悬疑","推理","灵异","僵尸","科幻","都市情感","都市逆袭"], "原创短剧")
        hook = self._make_hook(idea, genre)
        characters = self._characters(idea, genre)
        scenes = self._scenes(idea, genre)
        shots = self._shots(duration, characters, scenes, idea, ratio)
        tasks = self._tasks()
        plan = {
            "plan_id": "PLAN-" + uuid4().hex[:8].upper(),
            "version": 1,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "title": title,
            "idea": idea,
            "intent": {"genre": genre, "duration_seconds": duration, "aspect_ratio": ratio, "hook": hook},
            "story": {"logline": self._logline(idea, genre), "structure": ["Hook", "建立信息", "异常/冲突", "升级", "反转", "悬念"]},
            "characters": characters,
            "scenes": scenes,
            "shots": shots,
            "tasks": tasks,
            "status": "planned"
        }
        plan['generation'] = local_ollama_director.enrich_plan(plan)
        self.save_plan(plan)
        return plan

    def _make_title(self, idea):
        if not idea: return "未命名导演项目"
        first = re.split(r'[，。,.；;\n]', idea)[0].strip()
        return first[:18] or "未命名导演项目"

    def _make_hook(self, idea, genre):
        if "凶宅" in idea: return "这栋房子已经封了三十年，今晚却有人在里面点了一盏灯。"
        if "红衣女鬼" in idea: return "道士推开门的瞬间，墙上的红衣女人睁开了眼。"
        if genre == "修仙": return "所有人都以为他只是废物，直到天劫在他头顶降临。"
        if genre == "玄幻": return "他醒来后发现，整个世界都在追杀同一个名字——他的名字。"
        return "第一句话就抛出一个无法解释的异常，让观众必须继续看下去。"

    def _logline(self, idea, genre):
        return f"围绕“{idea[:100]}”展开一段{genre}短剧，在有限时长内完成冲突建立、升级与结尾悬念。"

    def _characters(self, idea, genre):
        chars = [{"id":"CHAR-00001","name":"主角","role":"protagonist","description":"由导演根据创意进一步确定的人物。","status":"planned"}]
        if any(x in idea for x in ["鬼","僵尸","灵异","凶宅"]): chars.append({"id":"CHAR-00002","name":"异象角色","role":"antagonist","description":"负责制造核心恐惧与悬念。","status":"planned"})
        elif any(x in idea for x in ["修仙","玄幻","道士"]): chars.append({"id":"CHAR-00002","name":"对手","role":"antagonist","description":"负责推动冲突升级。","status":"planned"})
        return chars

    def _scenes(self, idea, genre):
        base = "废弃凶宅" if "凶宅" in idea else ("古宅/夜街" if genre == "中式恐怖" else "核心故事场景")
        return [
            {"id":"SCENE-00001","name":base,"purpose":"建立世界与氛围","status":"planned"},
            {"id":"SCENE-00002","name":"冲突空间","purpose":"承载主要冲突","status":"planned"},
            {"id":"SCENE-00003","name":"悬念结尾空间","purpose":"留下下一集钩子","status":"planned"}
        ]

    def _shots(self, duration, chars, scenes, idea, ratio="9:16"):
        # Keep the shot plan reasonably paced and make its duration sum exact
        # to one decimal place, including durations that do not divide evenly.
        duration = max(1.0, float(duration))
        n = max(4, min(120, int((duration + 5.999) // 6)))
        total_tenths = int(round(duration * 10))
        base, remainder = divmod(total_tenths, n)
        labels = ["Hook特写","环境建立","人物进入","异常发现","冲突升级","核心动作","反转信息","悬念收尾"]
        shots = []
        for i in range(n):
            shot_tenths = base + (1 if i < remainder else 0)
            scene_id = scenes[min(i // 3, len(scenes) - 1)]["id"] if scenes else ""
            shots.append({
                "id": f"SHOT-{i+1:04d}", "index": i+1,
                "duration": shot_tenths / 10, "scene_id": scene_id,
                "type": labels[i] if i < len(labels) else "补充镜头",
                "visual_prompt": f"{idea.strip()}；镜头{i+1}，电影级构图，{ratio}画幅，画面连续且人物一致",
                "action": "推动剧情并强化镜头信息",
                "dialogue": "", "director_note": "",
                "prompt_status": "pending", "status": "planned"
            })
        return shots

    def _tasks(self):
        names=[("TASK-01","story","生成/完善剧本"),("TASK-02","character","建立人物资产"),("TASK-03","scene","建立场景资产"),("TASK-04","storyboard","生成分镜"),("TASK-05","prompt","生成镜头Prompt"),("TASK-06","image","生成关键画面"),("TASK-07","video","生成动态镜头"),("TASK-08","voice","生成配音"),("TASK-09","sound","生成音效与BGM"),("TASK-10","edit","进入剪辑时间轴"),("TASK-11","qc","质量检查"),("TASK-12","publish","准备发布"),("TASK-13","title_card","生成片头/章节标题卡")]
        return [{"id":i,"type":t,"name":n,"status":"pending","progress":0} for i,t,n in names]

    def save_plan(self, plan):
        if not isinstance(plan, dict):
            raise ValueError('导演计划必须是对象')
        plan_id=plan.get('plan_id')
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise ValueError('导演计划缺少有效 plan_id')
        safe = re.sub(r'[^a-zA-Z0-9_-]+','_', plan_id).strip('_')
        if not safe:
            raise ValueError('导演计划 plan_id 无法生成安全文件名')
        os.makedirs(self.project_dir, exist_ok=True)
        path=os.path.join(self.project_dir, safe + '.json')
        fd,tmp_path=tempfile.mkstemp(prefix='.plan-',suffix='.tmp',dir=self.project_dir)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(plan,f,ensure_ascii=False,indent=2,allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path,path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        return path

    def load_plans(self):
        result=[]
        for name in sorted(os.listdir(self.project_dir), reverse=True):
            if name.startswith('PLAN-') and name.endswith('.json'):
                try:
                    with open(os.path.join(self.project_dir,name),encoding='utf-8') as f: result.append(json.load(f))
                except Exception: pass
        return result

director_plan_engine = DirectorPlanEngine()
