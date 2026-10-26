import json, os, time, uuid, tempfile
from pathlib import Path
from urllib import request, parse
from urllib.error import HTTPError, URLError
from core.adapters.base import BaseAdapter, AdapterResult
from core.character_reference_comfyui import bind_character_references
from core.comfyui_workflow_registry import compile_workflow, WorkflowManifestError, WorkflowRegistry
from core.config import DATA_DIR
from core.render_budget import budget_from_task, apply_budget_to_graph

BUILTIN_WORKFLOW_DIR = os.path.join(DATA_DIR, 'comfyui_workflows', 'builtin')
USER_WORKFLOW_DIR = os.path.join(DATA_DIR, 'comfyui_workflows', 'user')


class ComfyUIAdapter(BaseAdapter):
    """ComfyUI API client with real completion polling and output download."""
    key = 'comfyui'
    OUTPUT_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.webp', '.bmp',
        '.mp4', '.webm', '.mov', '.gif',
        '.wav', '.mp3', '.flac', '.ogg',
    }

    def _url(self, model, path):
        return model.get('endpoint', 'http://127.0.0.1:8188').rstrip('/') + path

    def _loopback_endpoint(self, model):
        parsed = parse.urlparse(model.get('endpoint', 'http://127.0.0.1:8188'))
        return parsed.scheme in ('http', 'https') and parsed.hostname in ('localhost', '127.0.0.1', '::1')

    def test(self, model):
        if not self._loopback_endpoint(model):
            return AdapterResult(False, '为保障本地优先和安全，ComfyUI 地址必须是 localhost/127.0.0.1/::1。')
        try:
            with request.urlopen(self._url(model, '/system_stats'), timeout=3) as r:
                return AdapterResult(r.status == 200, 'ComfyUI 已连接', data=json.loads(r.read().decode('utf-8')))
        except Exception as e:
            return AdapterResult(False, f'ComfyUI 未连接：{e}')

    def _workflow(self, task, context):
        manifest = task.get('workflow_manifest') or context.get('workflow_manifest')
        registry_id = task.get('workflow_registry_id') or context.get('workflow_registry_id')
        registry = WorkflowRegistry(BUILTIN_WORKFLOW_DIR, USER_WORKFLOW_DIR)
        if manifest is None and registry_id:
            try:
                manifest = registry.get(registry_id)
            except WorkflowManifestError as exc:
                return None, f'未能加载已登记的 ComfyUI 工作流：{exc}'
        # Allow production tasks to select a registered workflow by capability,
        # so users do not have to embed a large API graph in every task JSON.
        # Ambiguous matches are rejected instead of silently choosing the wrong model.
        if manifest is None and not registry_id and not (task.get('workflow') or context.get('workflow')):
            requested_capability = task.get('workflow_capability') or context.get('workflow_capability')
            if not requested_capability:
                requested_capability = {
                    'image': 'image.text2image',
                    'video': 'video.image2video',
                }.get(task.get('type'))
            if requested_capability:
                matches = [
                    item for item in registry.list()
                    if item.get('capability') == requested_capability
                ]
                if len(matches) == 1:
                    manifest = matches[0]
                elif len(matches) > 1:
                    return None, (
                        f'工作流能力 {requested_capability} 对应 {len(matches)} 个已登记工作流；'
                        '请在任务中指定 workflow_registry_id。'
                    )
        if manifest is not None:
            try:
                return compile_workflow(
                    manifest,
                    params=task.get('workflow_params') or context.get('workflow_params') or {},
                    assets=task.get('workflow_assets') or context.get('workflow_assets') or {},
                ), None
            except WorkflowManifestError as exc:
                return None, f'ComfyUI 工作流清单无效：{exc}'
        workflow = task.get('workflow') or context.get('workflow')
        if isinstance(workflow, str):
            try:
                workflow = json.loads(workflow)
            except Exception:
                return None, 'ComfyUI workflow JSON 无法解析。'
        if not isinstance(workflow, dict) or not workflow:
            return None, 'ComfyUI 任务缺少 API 格式 workflow JSON，未执行。'
        return workflow, None

    def preflight_shot_batch(self, task, bindings, context=None):
        """Validate a per-shot task against its registered manifest before any render starts."""
        context = context or {}
        if not isinstance(task, dict) or not isinstance(bindings, dict):
            return {"success": False, "message": "逐镜头预检查需要有效 task 和 bindings 对象。"}
        manifest = task.get("workflow_manifest") or context.get("workflow_manifest")
        registry_id = task.get("workflow_registry_id") or context.get("workflow_registry_id")
        registry = WorkflowRegistry(BUILTIN_WORKFLOW_DIR, USER_WORKFLOW_DIR)
        try:
            if manifest is None and registry_id:
                manifest = registry.get(registry_id)
            if manifest is None:
                requested = task.get("workflow_capability") or context.get("workflow_capability") or "video.image2video"
                matches = [item for item in registry.list() if item.get("capability") == requested]
                if len(matches) == 1:
                    manifest = matches[0]
                elif len(matches) > 1:
                    return {"success": False, "message": f"能力 {requested} 匹配到 {len(matches)} 个工作流，请指定 workflow_registry_id。"}
                else:
                    return {"success": False, "message": f"没有找到能力为 {requested} 的已登记工作流；逐镜头模式需要参数清单。"}
            capability = manifest.get("capability")
            if capability not in {"video.text2video", "video.image2video", "video.reference2video"}:
                return {"success": False, "message": f"逐镜头视频任务不能使用工作流能力：{capability}"}
            declared = {item.get("name") for item in manifest.get("params", []) if isinstance(item, dict)}
            base_params = task.get("workflow_params") or {}
            if not isinstance(base_params, dict):
                return {"success": False, "message": "workflow_params 必须是对象。"}
            unknown_base = set(base_params) - declared
            if unknown_base:
                return {"success": False, "message": "workflow_params 含未声明参数：" + ", ".join(sorted(unknown_base))}
            if not ({"prompt", "visual_prompt"} & set(bindings)):
                return {"success": False, "message": "逐镜头模式至少需要将 prompt 或 visual_prompt 映射到工作流参数，否则每个镜头会重复生成相同内容。"}
            for field, parameter in bindings.items():
                if field not in {"prompt", "visual_prompt", "duration_seconds", "shot_id"}:
                    return {"success": False, "message": f"不支持的镜头字段映射：{field}"}
                if not isinstance(parameter, str) or not parameter:
                    return {"success": False, "message": f"镜头字段 {field} 的参数名无效"}
                if parameter not in declared:
                    return {"success": False, "message": f"镜头字段 {field} 映射到未声明参数：{parameter}"}
            # Compile once before launching the batch to validate graph structure,
            # asset references, and the static parameters for every upcoming shot.
            compile_workflow(
                manifest,
                params=base_params,
                assets=task.get("workflow_assets") or context.get("workflow_assets") or {},
            )
            return {
                "success": True,
                "workflow_id": manifest.get("id"),
                "capability": capability,
                "declared_params": sorted(declared),
                "shot_bindings": dict(bindings),
            }
        except (WorkflowManifestError, TypeError, ValueError) as exc:
            return {"success": False, "message": f"逐镜头工作流预检查失败：{exc}"}

    def execute(self, model, task, context):
        workflow, error = self._workflow(task, context)
        if error:
            return AdapterResult(False, error)
        budget_report = None
        try:
            budget = budget_from_task(task)
            if budget is not None:
                workflow, budget_report = apply_budget_to_graph(workflow, budget)
        except (TypeError, ValueError, KeyError) as exc:
            return AdapterResult(False, f"本地资源预算配置无效：{exc}")
        reference_report = {"success": True, "bound": 0, "warnings": []}
        references = task.get("character_references") or context.get("character_references") or []
        if references:
            try:
                workflow, reference_report = bind_character_references(workflow, references, model)
            except Exception as exc:
                return AdapterResult(False, f"角色参考图绑定失败：{exc}",
                                     data={"reference_report": {"success": False, "warnings": [str(exc)]}})
        if not self._loopback_endpoint(model):
            return AdapterResult(False, 'ComfyUI 地址必须是本机回环地址。')
        payload = {'prompt': workflow, 'client_id': 'scicloud-' + uuid.uuid4().hex[:8]}
        try:
            req = request.Request(self._url(model, '/prompt'), data=json.dumps(payload).encode(),
                                  headers={'Content-Type': 'application/json'})
            with request.urlopen(req, timeout=10) as r:
                result = json.loads(r.read().decode())
            pid = result.get('prompt_id')
            if not pid:
                return AdapterResult(False, 'ComfyUI 未返回 prompt_id。', data=result)
            return AdapterResult(True, 'ComfyUI 工作流已提交', data={'prompt_id': pid, 'queued': True, 'reference_report': reference_report, 'resource_budget': budget_report})
        except Exception as e:
            detail = ''
            if isinstance(e, HTTPError):
                try: detail = e.read().decode('utf-8', errors='replace')[:1200]
                except Exception: pass
            return AdapterResult(False, f'ComfyUI 提交失败：{e}' + (f'；{detail}' if detail else ''))

    def wait(self, model, prompt_id, timeout=1800, interval=2):
        end = time.monotonic() + max(1, timeout)
        while time.monotonic() < end:
            try:
                with request.urlopen(self._url(model, '/history/' + parse.quote(str(prompt_id), safe='')), timeout=5) as r:
                    data = json.loads(r.read().decode())
                item = data.get(prompt_id)
                if item:
                    status = item.get('status') or {}
                    if status.get('status_str') == 'error' or status.get('completed') is False and status.get('status_str') == 'error':
                        return AdapterResult(False, 'ComfyUI 工作流执行失败。', data=item)
                    if status.get('completed') or item.get('outputs'):
                        outputs = item.get('outputs') or {}
                        return AdapterResult(True, 'ComfyUI 工作流完成', data=item, outputs=self._output_refs(outputs))
            except Exception:
                pass
            time.sleep(max(0.05, interval))
        return AdapterResult(False, f'ComfyUI 工作流等待超时（{timeout} 秒）。', data={'prompt_id': prompt_id})

    def _output_refs(self, outputs):
        refs = []
        for node_id, node_output in (outputs or {}).items():
            if not isinstance(node_output, dict):
                continue
            for kind in ('images', 'gifs', 'videos', 'audio'):
                for item in node_output.get(kind, []) or []:
                    if not isinstance(item, dict) or not item.get('filename'):
                        continue
                    ext = Path(str(item['filename'])).suffix.lower()
                    if ext not in self.OUTPUT_EXTENSIONS:
                        continue
                    refs.append({
                        'node_id': str(node_id),
                        'kind': 'video' if ext in ('.mp4', '.webm', '.mov', '.gif') else
                                ('audio' if ext in ('.wav', '.mp3', '.flac', '.ogg') else 'image'),
                        'filename': os.path.basename(str(item['filename'])),
                        'subfolder': str(item.get('subfolder') or ''),
                        'type': str(item.get('type') or 'output'),
                    })
        return refs

    def download_outputs(self, model, refs, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        saved = []
        for ref in refs:
            query = parse.urlencode({
                'filename': ref['filename'],
                'subfolder': ref['subfolder'],
                'type': ref['type'],
            })
            try:
                with request.urlopen(self._url(model, '/view?' + query), timeout=60) as r:
                    content = r.read()
                if not content:
                    continue
                safe_name = os.path.basename(ref['filename'])
                stem, ext = os.path.splitext(safe_name)
                target = os.path.join(output_dir, f"{stem}_{ref['node_id']}_{uuid.uuid4().hex[:6]}{ext.lower()}")
                fd, temporary = tempfile.mkstemp(prefix='.comfyui-output-', suffix=ext.lower(), dir=output_dir)
                try:
                    with os.fdopen(fd, 'wb') as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    if os.path.isfile(temporary) and os.path.getsize(temporary) > 0:
                        os.replace(temporary, target)
                    if os.path.isfile(target) and os.path.getsize(target) > 0:
                        saved.append({'path': os.path.abspath(target), 'kind': ref['kind'],
                                      'size': os.path.getsize(target), 'source_filename': safe_name})
                    else:
                        try: os.remove(target)
                        except OSError: pass
                finally:
                    if os.path.exists(temporary):
                        try: os.remove(temporary)
                        except OSError: pass
            except Exception:
                continue
        return saved

    def render(self, model, task, context=None):
        """Submit a workflow, wait for completion, then download actual media outputs."""
        context = context or {}
        if not self._loopback_endpoint(model):
            return AdapterResult(False, 'ComfyUI 地址必须是本机回环地址。')
        submitted = self.execute(model, task, context)
        if not submitted.success:
            return submitted
        prompt_id = submitted.data.get('prompt_id')
        try:
            timeout = float(task.get('timeout', 1800))
            interval = float(task.get('poll_interval', 2))
            if not (0 < timeout <= 7200):
                raise ValueError('timeout 必须大于 0 且不超过 7200 秒')
            if not (0 < interval <= 10):
                raise ValueError('poll_interval 必须大于 0 且不超过 10 秒')
        except (TypeError, ValueError) as exc:
            return AdapterResult(False, f'ComfyUI 等待参数无效：{exc}', data={'prompt_id': prompt_id})
        completed = self.wait(model, prompt_id, timeout=timeout, interval=interval)
        if not completed.success:
            return completed
        refs = completed.outputs or self._output_refs(completed.data.get('outputs') or {})
        if not refs:
            return AdapterResult(False, 'ComfyUI 工作流已结束，但没有发现可下载的图片/视频/音频输出。',
                                 data={'prompt_id': prompt_id, 'history': completed.data})
        output_dir = task.get('output_dir') or context.get('output_dir')
        if not output_dir:
            return AdapterResult(False, '缺少输出目录，拒绝将远端缓存误报为本地产物。',
                                 data={'prompt_id': prompt_id})
        saved = self.download_outputs(model, refs, output_dir)
        if not saved:
            return AdapterResult(False, 'ComfyUI 已完成，但媒体下载失败或文件为空。',
                                 data={'prompt_id': prompt_id, 'output_refs': refs})
        reference_report = submitted.data.get("reference_report") or {"success": True, "bound": 0, "warnings": []}
        message = f'ComfyUI 生成完成，已保存 {len(saved)} 个真实媒体文件。'
        if reference_report.get("warnings"):
            message += f" 角色参考图提示：{len(reference_report['warnings'])} 项未注入，请检查工作流节点标记。"
        return AdapterResult(True, message, outputs=saved,
                             data={'prompt_id': prompt_id, 'output_refs': refs,
                                   'completed': True, 'reference_report': reference_report,
                                   'resource_budget': submitted.data.get('resource_budget')})
