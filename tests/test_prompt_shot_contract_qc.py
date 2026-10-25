import json

from core.qc_engine import QCEngine


def _write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_prompt_qc_checks_canonical_shot_manifest(tmp_path):
    artifact = _write(tmp_path / "prompts.json", {
        "prompts": [
            {"shot_id": "S1", "shot_index": 1, "duration": 3, "visual_prompt": "夜雨山门"},
            {"shot_id": "S2", "shot_index": 2, "duration": 4, "visual_prompt": "剑光破空"},
        ],
        "timing_summary": {"actual_duration_seconds": 7},
    })
    result = QCEngine().inspect_task({}, {"id": "PROMPT-1", "type": "prompt", "outputs": [artifact]})
    assert result["success"] is True
    assert result["shot_contract_checks"][0]["shot_count"] == 2
    assert result["shot_contract_checks"][0]["duration_seconds"] == 7


def test_prompt_qc_rejects_duplicate_shot_ids(tmp_path):
    artifact = _write(tmp_path / "prompts.json", {
        "prompts": [{"shot_id": "S1"}, {"shot_id": "S1"}],
        "timing_summary": {"actual_duration_seconds": 10},
    })
    result = QCEngine().inspect_task({}, {"id": "PROMPT-2", "type": "prompt", "outputs": [artifact]})
    assert result["success"] is False
    assert result["shot_contract_checks"][0]["success"] is False


def test_prompt_qc_rejects_mismatched_reported_duration(tmp_path):
    artifact = _write(tmp_path / "prompts.json", {
        "prompts": [{"shot_id": "S1", "duration": 5}],
        "timing_summary": {"actual_duration_seconds": 30},
    })
    result = QCEngine().inspect_task({}, {"id": "PROMPT-3", "type": "prompt", "outputs": [artifact]})
    assert result["success"] is False
    assert "时长合计不一致" in result["shot_contract_checks"][0]["message"]
