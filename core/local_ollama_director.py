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

    def diagnose(self):
        """Distinguish why Ollama cannot be used, without guessing.

        Returns a dict with a stable ``status`` code:
        - ``ok``: Ollama answered and the configured model is installed.
        - ``ollama_not_running``: the localhost connection was refused or
          timed out (Ollama app not running, wrong port, firewall).
        - ``model_not_loaded``: Ollama answered, but the model is not in
          its model list (``detail`` names the models it did report).
        - ``ollama_error``: Ollama answered with an HTTP error, or its
          model list was not a usable response.
        This is a read-only probe: it never downloads or pulls a model.
        """
        try:
            data=self._request_json(self.endpoint+'/api/tags',timeout=self.connect_timeout)
        except urllib.error.HTTPError as exc:
            return {'status':'ollama_error','detail':f'Ollama 返回 HTTP {exc.code}，请检查本机 Ollama 服务状态'}
        except urllib.error.URLError as exc:
            reason=getattr(exc,'reason',exc)
            if isinstance(reason,(ConnectionRefusedError,TimeoutError)) or 'refused' in str(reason).lower() or 'timed out' in str(reason).lower():
                return {'status':'ollama_not_running','detail':'无法连接本机 Ollama（连接被拒绝或超时），请确认 Ollama 已启动且地址为 %s' % self.endpoint}
            return {'status':'ollama_not_running','detail':f'无法连接本机 Ollama：{reason}'}
        except Exception as exc:
            return {'status':'ollama_error','detail':f'检查本机 Ollama 时出错：{exc}'}
        if not isinstance(data,dict) or not isinstance(data.get('models'),list):
            return {'status':'ollama_error','detail':'Ollama 返回的模型列表不是可用格式'}
        models=data['models']
        for item in models:
            name=str(item.get('name','')) if isinstance(item,dict) else ''
            if name==self.model or (name and name.split(':')[0]==self.model.split(':')[0]):
                return {'status':'ok','model':name,'detail':f'已找到模型 {name}'}
        available=[str(item.get('name','')) for item in models if isinstance(item,dict) and item.get('name')][:5]
        return {'status':'model_not_loaded','detail':'Ollama 已运行，但未找到模型 %s；已安装模型：%s' % (self.model, '、'.join(available) if available else '无')}

    def _installed_model(self):
        result=self.diagnose()
        return result.get('model') if result.get('status')=='ok' else None

    @staticmethod
    def _text(value):
        return value.strip() if isinstance(value,str) else ''

    def _fallback_enrich_plan(self, plan, reason, diagnosis=None, diagnosis_detail=''):
        """Create usable, varied shot descriptions when local inference is unavailable.

        The returned dict always carries ``diagnosis`` (a stable code such
        as ollama_not_running / model_not_loaded / invalid_json /
        invalid_schema / ollama_error / no_shots) and ``fallback_reason``,
        so a plan marked 本地规则兜底 can always say WHY it fell back.
        The fallback itself is unchanged: it never fabricates dialogue.
        """
        base={'mode':'deterministic_fallback','provider':'local_ollama','model':self.model,
              'diagnosis':diagnosis or 'ollama_error','diagnosis_detail':diagnosis_detail or str(reason),
              'fallback_reason':str(reason)}
        if not isinstance(plan, dict):
            return dict(base, shot_count=0, message=str(reason))
        shots=plan.get('shots')
        if not isinstance(shots,list) or not shots:
            return dict(base, shot_count=0, message=str(reason))
        intent=plan.get('intent') if isinstance(plan.get('intent'),dict) else {}
        genre=str(intent.get('genre') or '原创短剧')
        ratio=str(intent.get('aspect_ratio') or '9:16')
        idea=str(plan.get('idea') or '核心剧情')
        hook=str(intent.get('hook') or '')
        scenes={item.get('id'):item for item in plan.get('scenes',[])
                if isinstance(item,dict) and item.get('id')}
        characters=[item for item in plan.get('characters',[]) if isinstance(item,dict)]
        beats={
            'Hook特写':('以异常细节抓住观众视线','极近景呈现最关键的异常细节，背景压暗，主体纹理清晰，形成开场悬念'),
            '环境建立':('建立空间与气氛','先展示环境纵深、天气、主光方向与前景遮挡，明确人物所在空间和危险来源'),
            '人物进入':('交代人物与行动目标','人物从画面边缘进入并朝目标移动，服装轮廓与标志性道具清楚，保持轴线连续'),
            '异常发现':('让人物发现关键异常','通过人物视线、手部动作和异常物体形成明确视觉引导，异常细节必须可辨认'),
            '冲突升级':('强化对抗与压迫感','用前后景关系和低机位强化力量差，动作方向清晰，环境反馈体现冲突升级'),
            '核心动作':('呈现关键动作结果','完整展示动作起势、接触点和结果，主体不出框，运动方向与上一镜头一致'),
            '反转信息':('揭示与前文不同的信息','将关键线索置于视觉中心，以人物反应和线索特写共同表达反转，不额外引入无关角色'),
            '悬念收尾':('留下未解问题','主体停在决定性瞬间，保留明确的视觉线索和未完成动作，构图留出压迫性的负空间'),
        }
        updated=0
        for index,shot in enumerate(shots,1):
            if not isinstance(shot,dict):
                continue
            shot_type=str(shot.get('type') or list(beats)[(index-1)%len(beats)])
            beat,visual=beats.get(shot_type,('推进剧情并交代信息','用清楚的主体动作和空间关系推进剧情，保证画面可读'))
            scene=scenes.get(shot.get('scene_id'),{})
            scene_name=str(scene.get('name') or '核心故事场景')
            scene_purpose=str(scene.get('purpose') or '')
            assigned=shot.get('character_ids')
            if isinstance(assigned,list) and assigned:
                selected=[item for item in characters if item.get('id') in assigned]
            else:
                selected=characters[:1]
            character_text='、'.join(str(item.get('name') or '角色') for item in selected) or '主角'
            character_desc='；'.join('，'.join(str(item.get(key)) for key in ('name','description','costume') if item.get(key)) for item in selected)
            action=str(shot.get('action') or '').strip()
            generic_actions={'推动剧情并强化镜头信息','剧情动作','原始动作'}
            if not action or action in generic_actions or action.startswith('原始动作'):
                action=f'{character_text}执行“{beat}”的具体动作，动作目标与结果清晰可见'
                shot['action']=action
            existing=str(shot.get('visual_prompt') or shot.get('prompt') or '').strip()
            generic_markers=('电影级构图','画面连续且人物一致','核心故事场景')
            is_generic=not existing or (('镜头' in existing) and any(marker in existing for marker in generic_markers))
            if is_generic:
                parts=[
                    f'{genre}题材，{ratio}画幅',
                    f'剧情核心：{idea}',
                    f'场景：{scene_name}' + (f'，场景目的：{scene_purpose}' if scene_purpose else ''),
                    f'人物：{character_desc or character_text}',
                    f'镜头任务：{shot_type}，{beat}',
                    f'画面内容：{visual}',
                    f'具体动作：{action}',
                    '电影级布光，主体轮廓清晰，前中后景分离，材质细节可见',
                    '保持人物面部、发型、服装、道具和屏幕方向与相邻镜头一致',
                ]
                if index==1 and hook:
                    parts.insert(2,f'开场钩子：{hook}')
                shot['visual_prompt']='；'.join(parts)
                shot['prompt']=shot['visual_prompt']
            if not str(shot.get('director_note') or '').strip():
                shot['director_note']=f'连续性检查：{character_text}外观与道具保持一致；镜头目的为{beat}。'
            updated+=1
        return dict(base, shot_count=updated,
            message=f'本地模型不可用或输出校验失败，已为 {updated} 个镜头生成规则化分镜提示词；对白不会伪造。原因：{reason}'
        )

    def _generate_batch(self, model, prompt, batch, batch_index):
        """One generate call plus strict schema validation for one batch."""
        result=self._request_json(self.endpoint+'/api/generate',{
            'model':model,'prompt':prompt,'stream':False,'format':'json',
            'options':{'temperature':0.3,'num_ctx':4096}
        },timeout=self.generate_timeout)
        raw=result.get('response','') if isinstance(result,dict) else ''
        try:
            data=json.loads(raw) if isinstance(raw,str) else raw
        except Exception as exc:
            raise ValueError(f'第 {batch_index} 批模型返回不是合法 JSON：{exc}') from exc
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
        return data

    def enrich_plan(self, plan):
        """Enrich every shot in bounded batches; commit text changes only if all batches validate.

        A batch whose model output is invalid JSON or fails schema
        validation gets exactly one retry with a stricter prompt before
        the plan falls back to deterministic rules, and the fallback
        records which of those cases happened (see diagnose() codes).
        """
        try:
            diagnosis=self.diagnose()
            if diagnosis.get('status')!='ok':
                return self._fallback_enrich_plan(plan, diagnosis.get('detail','本地 Ollama 不可用'),
                                                 diagnosis=diagnosis.get('status'), diagnosis_detail=diagnosis.get('detail',''))
            model=diagnosis['model']
            if not isinstance(plan,dict):
                return self._fallback_enrich_plan(plan, '导演计划不是对象', diagnosis='no_shots')
            shots=plan.get('shots',[])
            if not isinstance(shots,list) or not shots:
                return self._fallback_enrich_plan(plan, '导演计划没有可优化的镜头', diagnosis='no_shots')
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
                strict_prompt=(
                    '只输出 JSON，严禁任何解释、标题、Markdown 代码块或额外文字。'
                    'shot_items 必须恰好 %d 条，id 必须与输入 shots 的 id 按原顺序一一对应，不得增删、重复或改写 id。' % len(batch)
                    + prompt
                )
                last_error=None
                data=None
                for attempt_prompt in (prompt, strict_prompt):
                    try:
                        data=self._generate_batch(model, attempt_prompt, batch, batch_index)
                        break
                    except (ValueError, json.JSONDecodeError) as exc:
                        last_error=exc
                        continue
                if data is None:
                    raise last_error
                items=data['shot_items']
                if not story:
                    story=self._text(data.get('logline'))
                if not hook:
                    hook=self._text(data.get('hook'))
                for item in data.get('characters',[]):
                    if isinstance(item,dict) and item.get('id') and self._text(item.get('description')):
                        char_updates.setdefault(item['id'],self._text(item['description']))
                for item in data.get('scenes',[]):
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
                'diagnosis':'ok','diagnosis_detail':diagnosis.get('detail',''),
                'message':f'本地模型已优化全部 {len(all_shot_updates)} 个镜头文本（{len(batches)} 批）',
                'shot_count':len(all_shot_updates),'batch_count':len(batches)
            }
        except Exception as exc:
            if isinstance(exc, urllib.error.HTTPError):
                code='ollama_error'
            elif isinstance(exc, urllib.error.URLError):
                reason=getattr(exc,'reason',exc)
                code='ollama_not_running' if isinstance(reason,(ConnectionRefusedError,TimeoutError)) or 'refused' in str(reason).lower() or 'timed out' in str(reason).lower() else 'ollama_error'
            elif isinstance(exc, json.JSONDecodeError) or '不是合法 JSON' in str(exc):
                code='invalid_json'
            elif isinstance(exc, ValueError):
                code='invalid_schema'
            else:
                code='ollama_error'
            return self._fallback_enrich_plan(plan, f'本地模型不可用或返回无效结果：{exc}',
                                             diagnosis=code, diagnosis_detail=str(exc))


local_ollama_director=LocalOllamaDirector()
