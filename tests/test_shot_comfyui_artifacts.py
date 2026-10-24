import tempfile
from unittest.mock import patch

from core.shot_production_engine import ShotProductionEngine


def test_queued_or_empty_comfy_result_does_not_mark_shot_done():
    with tempfile.TemporaryDirectory() as root:
        engine = ShotProductionEngine()
        engine.root = root
        run = engine.create_run('EP-TEST', [{'shot_id': 'SHOT-1', 'comfy_workflow': {'1': {}}}])
        with patch('core.shot_production_engine.production_engine.submit_comfy',
                   return_value={'success': True, 'outputs': [], 'message': 'queued'}):
            result = engine.produce_shot(run['run_id'], 'SHOT-1')
        assert result['status'] == 'blocked'
        assert result['done_count'] == 0
        assert result['blocked_count'] == 1
