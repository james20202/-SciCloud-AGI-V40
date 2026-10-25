import json
import os
import tempfile
from unittest.mock import patch

from core.adapters.comfyui_adapter import ComfyUIAdapter


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode('utf-8')
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def test_render_waits_for_completion_and_downloads_real_output():
    adapter = ComfyUIAdapter()
    model = {'endpoint': 'http://127.0.0.1:8188'}
    def fake_urlopen(req, timeout=0):
        url = req.full_url if hasattr(req, 'full_url') else req
        if url.endswith('/prompt'):
            return FakeResponse({'prompt_id': 'prompt-test'})
        if '/history/prompt-test' in url:
            return FakeResponse({'prompt-test': {
                'status': {'completed': True, 'status_str': 'success'},
                'outputs': {'9': {'images': [{'filename': 'shot.png', 'subfolder': '', 'type': 'output'}]}}
            }})
        if '/view?' in url:
            return FakeResponse(b'actual-image-bytes')
        raise AssertionError('unexpected URL: ' + str(url))
    with tempfile.TemporaryDirectory() as outdir, patch('core.adapters.comfyui_adapter.request.urlopen', side_effect=fake_urlopen):
        result = adapter.render(model, {'workflow': {'1': {'class_type': 'SaveImage', 'inputs': {}}}, 'output_dir': outdir})
        assert result.success
        assert len(result.outputs) == 1
        path = result.outputs[0]['path']
        assert os.path.isfile(path)
        assert open(path, 'rb').read() == b'actual-image-bytes'
        assert result.data['prompt_id'] == 'prompt-test'


def test_render_refuses_non_loopback_endpoint_without_network_call():
    adapter = ComfyUIAdapter()
    with patch('core.adapters.comfyui_adapter.request.urlopen') as urlopen:
        result = adapter.render({'endpoint': 'https://example.com'}, {'workflow': {'1': {}}}, {})
    assert not result.success
    assert '本机回环地址' in result.message
    urlopen.assert_not_called()


def test_completed_workflow_without_media_is_not_success():
    adapter = ComfyUIAdapter()
    model = {'endpoint': 'http://localhost:8188'}
    def fake_urlopen(req, timeout=0):
        url = req.full_url if hasattr(req, 'full_url') else req
        if url.endswith('/prompt'):
            return FakeResponse({'prompt_id': 'prompt-empty'})
        if '/history/prompt-empty' in url:
            return FakeResponse({'prompt-empty': {'status': {'completed': True}, 'outputs': {}}})
        raise AssertionError('unexpected URL: ' + str(url))
    with tempfile.TemporaryDirectory() as outdir, patch('core.adapters.comfyui_adapter.request.urlopen', side_effect=fake_urlopen):
        result = adapter.render(model, {'workflow': {'1': {}}, 'output_dir': outdir})
    assert not result.success
    assert '没有发现可下载' in result.message


def test_adapter_compiles_manifest_into_api_graph():
    adapter = ComfyUIAdapter()
    manifest = {
        'id': 'test-txt2img',
        'version': 1,
        'capability': 'image.text2image',
        'runner': 'comfyui',
        'graph': {
            '4': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': '$assets.checkpoint'}},
            '3': {'class_type': 'KSampler', 'inputs': {'steps': 15, 'cfg': 7.0}},
        },
        'params': [
            {'name': 'steps', 'inject': {'type': 'scalar', 'to': [['3', 'steps']]}},
        ],
    }
    workflow, error = adapter._workflow(
        {'workflow_manifest': manifest, 'workflow_params': {'steps': 24},
         'workflow_assets': {'checkpoint': 'local-checkpoint.safetensors'}},
        {},
    )
    assert error is None
    assert workflow['3']['inputs']['steps'] == 24
    assert workflow['4']['inputs']['ckpt_name'] == 'local-checkpoint.safetensors'
    assert manifest['graph']['3']['inputs']['steps'] == 15


def test_adapter_rejects_invalid_manifest_before_submission():
    adapter = ComfyUIAdapter()
    workflow, error = adapter._workflow(
        {'workflow_manifest': {'id': '../bad'}},
        {},
    )
    assert workflow is None
    assert '工作流清单无效' in error
