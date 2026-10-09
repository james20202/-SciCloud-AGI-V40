from core.workflow_engine import STATUS_DONE, STATUS_FAILED, STATUS_READY, STATUS_RUNNING, WorkflowEngine


def test_status_flow_moves_to_done(tmp_path):
    engine = WorkflowEngine(project_dir=str(tmp_path))
    wf = engine.create_from_plan({
        'plan_id': 'PLAN-STATE-1',
        'title': 'workflow state test',
        'tasks': [
            {'id': 'T1', 'type': 'story', 'name': 'story'},
        ],
    })

    assert wf['tasks'][0]['status'] == STATUS_READY
    engine.start_task(wf['workflow_id'], 'T1')
    assert engine.load(wf['workflow_id'])['tasks'][0]['status'] == STATUS_RUNNING

    engine.complete_task(wf['workflow_id'], 'T1')
    finished = engine.load(wf['workflow_id'])
    assert finished['tasks'][0]['status'] == STATUS_DONE


def test_failed_task_can_retry(tmp_path):
    engine = WorkflowEngine(project_dir=str(tmp_path))
    wf = engine.create_from_plan({
        'plan_id': 'PLAN-STATE-2',
        'title': 'retry test',
        'tasks': [
            {'id': 'T2', 'type': 'prompt', 'name': 'prompt'},
        ],
    })

    engine.fail_task(wf['workflow_id'], 'T2', 'temporary failure')
    failed = engine.load(wf['workflow_id'])
    assert failed['tasks'][0]['status'] == STATUS_FAILED

    engine.retry_task(wf['workflow_id'], 'T2')
    retried = engine.load(wf['workflow_id'])
    assert retried['tasks'][0]['status'] == STATUS_READY
    assert retried['tasks'][0]['error'] is None
    assert retried['tasks'][0]['outputs'] == []
