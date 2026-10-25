import json
import os
import urllib.error
import urllib.request


class LocalOllamaDirector:
    """Optional localhost-only creative enrichment. Deterministic plans remain the safe fallback."""
    def __init__(self, endpoint=None, model=None, connect_timeout=1.5, generate_timeout=65):
        self.endpoint=(endpoint or os.environ.get('SCICLOUD_OLLAMA_URL','http://127.0.0.1:11434')).rstrip('/')
        self.model=model or os.environ.get('SCICLOUD_OLLAMA_MODEL','qwen2.5:3b')
        self.connect_timeout=connect_timeout
        self.generate_timeout=generate_timeout

    def _request_json(self, url, payload=None, timeout=3):
        data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
        req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'} if data is not None else {})
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    def _installed_model(self):
        data=self._request_json(self.endpoint+'/api/tags',timeout=self.connect_timeout)
        models=data.get('models',[])
        for item in models:
            name=str(item.get('name',''))
            if name==self.model or name.split(':')[0]==self.model.split(':')[0]:
                return name
        return None

    @staticmethod
    def _text(value):
        return value.strip() if isinstance(value,str) else ''

    def enrich_plan(self, plan):
        """Mutate only creative text fields; IDs, dependencies and timing are owned by Python."""
        try:
            model=self._installed_model()
            if not model:
                return {'mode':'deterministic_fallback','provider':'local_ollama','model':self.model,'message':'本地 Ollama 未运行或未找到指定模型'}
            shots=plan.get('shots',[])
            selected=shots[:24]
            payload={
                'idea':plan.get('idea',''),
                'genre':plan.get('intent',{}).get('genre','原创短剧'),
                'target_duration_seconds':plan.get('intent',{}).get('duration_seconds',60),
                'aspect_ratio':plan.get('intent',{}).get('aspect_ratio','9:16'),
                'logline':plan.get('story',{}).get('logline',''),
                'hook':plan.get('intent',{}).get('hook',''),
                'characters':[{'id':x.get('id'),'name':x.get('name'),'description':x.get('description','')} for x in plan.get('characters',[])],
                'scenes':[{'id':x.get('id'),'name':x.get('name'),'purpose':x.get('purpose','')} for x in plan.get('scenes',[])],
                'shots':[{'index':x.get('index'),'id':x.get('id'),'duration':x.get('duration'),'type':x.get('type'),'action':x.get('action','')} for x in selected]
            }
            prompt=(
                '你是中文短剧的专业编剧和分镜导演。基于输入内容优化创意文本，保持故事因果、人物一致性、场景连续性。'
                '只输出符合给定 JSON schema 的 JSON，不要 Markdown，不要输出其他文字。'
                '不要输出或修改任何 ID 和时长。shot_items 必须与输入 shots 数量完全相同并按原顺序对应。'
                '每个 visual_prompt 要可直接用于图像生成，包含主体、动作、环境、光线、构图和风格，并严格遵循输入 aspect_ratio；'
                'dialogue 要短且自然，无对白时可为空字符串。'
                'JSON schema: {"logline":string,"hook":string,"characters":[{"id":string,"description":string}],"scenes":[{"id":string,"purpose":string}],"shot_items":[{"id":string,"visual_prompt":string,"action":string,"dialogue":string,"director_note":string}]}\n'
                'INPUT='+json.dumps(payload,ensure_ascii=False)
            )
            result=self._request_json(self.endpoint+'/api/generate',{
                'model':model,'prompt':prompt,'stream':False,'format':'json',
                'options':{'temperature':0.3,'num_ctx':4096}
            },timeout=self.generate_timeout)
            raw=result.get('response','')
            data=json.loads(raw) if isinstance(raw,str) else raw
            if not isinstance(data,dict):
                raise ValueError('模型返回不是 JSON 对象')
            items=data.get('shot_items')
            if not isinstance(items,list) or len(items)!=len(selected):
                raise ValueError('模型镜头文本数量与输入不匹配')
            shot_ids={x.get('id') for x in selected}
            returned_ids={x.get('id') for x in items if isinstance(x,dict)}
            if returned_ids != shot_ids or len(returned_ids) != len(items):
                raise ValueError('模型镜头 ID 缺失、重复或与原计划不一致')
            chars=data.get('characters',[])
            scenes=data.get('scenes',[])
            if not isinstance(chars,list) or not isinstance(scenes,list):
                raise ValueError('模型人物或场景字段不是列表')
            story=self._text(data.get('logline'))
            hook=self._text(data.get('hook'))
            char_map={x.get('id'):x for x in plan.get('characters',[]) if x.get('id')}
            scene_map={x.get('id'):x for x in plan.get('scenes',[]) if x.get('id')}
            shot_map={x.get('id'):x for x in selected}
            # All validation completes before mutating the deterministic plan.
            if story: plan.setdefault('story',{})['logline']=story
            if hook: plan.setdefault('intent',{})['hook']=hook
            for item in chars:
                target=char_map.get(item.get('id')) if isinstance(item,dict) else None
                if target and self._text(item.get('description')): target['description']=self._text(item['description'])
            for item in scenes:
                target=scene_map.get(item.get('id')) if isinstance(item,dict) else None
                if target and self._text(item.get('purpose')): target['purpose']=self._text(item['purpose'])
            for item in items:
                target=shot_map[item['id']]
                for key in ('visual_prompt','action','dialogue','director_note'):
                    value=self._text(item.get(key))
                    if value: target[key]=value
            updated=len(items)
            return {'mode':'local_ollama','provider':'ollama','model':model,'message':f'本地模型已优化 {updated} 个镜头文本'}
        except Exception as exc:
            return {'mode':'deterministic_fallback','provider':'local_ollama','model':self.model,'message':f'本地模型不可用或返回无效结果：{exc}'}


local_ollama_director=LocalOllamaDirector()
