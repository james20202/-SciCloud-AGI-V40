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
        """Enrich every shot in bounded batches; commit text changes only if all batches validate."""
        try:
            model=self._installed_model()
            if not model:
                return {'mode':'deterministic_fallback','provider':'local_ollama','model':self.model,'message':'本地 Ollama 未运行或未找到指定模型'}
            shots=plan.get('shots',[])
            if not isinstance(shots,list) or not shots:
                return {'mode':'deterministic_fallback','provider':'local_ollama','model':self.model,'message':'导演计划没有可优化的镜头'}
            batch_size=24
            batches=[shots[i:i+batch_size] for i in range(0,len(shots),batch_size)]
            all_shot_updates={}
            char_updates={}
            scene_updates={}
            story=''
            hook=''
            common={
                'idea':plan.get('idea',''),
                'genre':plan.get('intent',{}).get('genre','原创短剧'),
                'target_duration_seconds':plan.get('intent',{}).get('duration_seconds',60),
                'aspect_ratio':plan.get('intent',{}).get('aspect_ratio','9:16'),
                'logline':plan.get('story',{}).get('logline',''),
                'hook':plan.get('intent',{}).get('hook',''),
                'characters':[{'id':x.get('id'),'name':x.get('name'),'description':x.get('description','')} for x in plan.get('characters',[]) if isinstance(x,dict)],
                'scenes':[{'id':x.get('id'),'name':x.get('name'),'purpose':x.get('purpose','')} for x in plan.get('scenes',[]) if isinstance(x,dict)],
            }
            for batch_index,batch in enumerate(batches,1):
                payload=dict(common)
                payload['batch_index']=batch_index
                payload['batch_count']=len(batches)
                payload['shots']=[{'index':x.get('index'),'id':x.get('id'),'duration':x.get('duration'),'type':x.get('type'),'action':x.get('action','')} for x in batch]
                prompt=(
                    '你是中文短剧的专业编剧和分镜导演。基于输入内容优化创意文本，保持故事因果、人物一致性、场景连续性。'
                    '只输出符合给定 JSON schema 的 JSON，不要 Markdown，不要输出其他文字。'
                    '不要输出或修改任何 ID 和时长。shot_items 必须与本批输入 shots 数量完全相同并按原顺序对应。'
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
                    raise ValueError(f'第 {batch_index} 批模型返回不是 JSON 对象')
                items=data.get('shot_items')
                if not isinstance(items,list) or len(items)!=len(batch):
                    raise ValueError(f'第 {batch_index} 批镜头文本数量与输入不匹配')
                expected_ids=[x.get('id') for x in batch]
                returned_ids=[x.get('id') for x in items if isinstance(x,dict)]
                if len(returned_ids)!=len(items) or returned_ids!=expected_ids:
                    raise ValueError(f'第 {batch_index} 批镜头 ID 缺失、重复、乱序或与原计划不一致')
                chars=data.get('characters',[])
                scenes=data.get('scenes',[])
                if not isinstance(chars,list) or not isinstance(scenes,list):
                    raise ValueError(f'第 {batch_index} 批人物或场景字段不是列表')
                if not story:
                    story=self._text(data.get('logline'))
                if not hook:
                    hook=self._text(data.get('hook'))
                for item in chars:
                    if isinstance(item,dict) and item.get('id') and self._text(item.get('description')):
                        char_updates.setdefault(item['id'],self._text(item['description']))
                for item in scenes:
                    if isinstance(item,dict) and item.get('id') and self._text(item.get('purpose')):
                        scene_updates.setdefault(item['id'],self._text(item['purpose']))
                for item in items:
                    all_shot_updates[item['id']]={key:self._text(item.get(key)) for key in ('visual_prompt','action','dialogue','director_note')}

            # Validation for every batch has completed. Only now mutate the plan.
            if story:
                plan.setdefault('story',{})['logline']=story
            if hook:
                plan.setdefault('intent',{})['hook']=hook
            char_map={x.get('id'):x for x in plan.get('characters',[]) if isinstance(x,dict) and x.get('id')}
            scene_map={x.get('id'):x for x in plan.get('scenes',[]) if isinstance(x,dict) and x.get('id')}
            shot_map={x.get('id'):x for x in shots if isinstance(x,dict) and x.get('id')}
            for key,value in char_updates.items():
                if key in char_map: char_map[key]['description']=value
            for key,value in scene_updates.items():
                if key in scene_map: scene_map[key]['purpose']=value
            for shot_id,updates in all_shot_updates.items():
                target=shot_map[shot_id]
                for key,value in updates.items():
                    if value: target[key]=value
            return {
                'mode':'local_ollama','provider':'ollama','model':model,
                'message':f'本地模型已优化全部 {len(all_shot_updates)} 个镜头文本（{len(batches)} 批）',
                'shot_count':len(all_shot_updates),'batch_count':len(batches)
            }
        except Exception as exc:
            return {'mode':'deterministic_fallback','provider':'local_ollama','model':self.model,'message':f'本地模型不可用或返回无效结果：{exc}'}

local_ollama_director=LocalOllamaDirector()
