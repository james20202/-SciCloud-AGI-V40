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


def test_prompt_qc_checks_optional_audio_timeline_without_breaking_legacy_artifacts(tmp_path):
    artifact = _write(tmp_path / "prompts_with_audio.json", {
        "prompts": [
            {"shot_id": "S1", "duration": 2, "dialogue": "你好"},
            {"shot_id": "S2", "duration": 3, "voiceover": "山门开启"},
        ],
        "timing_summary": {"actual_duration_seconds": 5},
        "audio_timeline": {
            "shot_count": 2,
            "total_duration_seconds": 5,
            "segments": [],
            "subtitle_cues": [],
        },
        "subtitle_srt_draft": "1\\n00:00:00,000 --> 00:00:02,000\\n你好\\n",
    })
    result = QCEngine().inspect_task({}, {"id": "PROMPT-AUDIO", "type": "prompt", "outputs": [artifact]})
    assert result["success"] is True
    assert result["shot_contract_checks"][0]["audio_timeline_checked"] is True


def test_prompt_qc_rejects_audio_timeline_duration_mismatch(tmp_path):
    artifact = _write(tmp_path / "prompts_bad_audio.json", {
        "prompts": [{"shot_id": "S1", "duration": 5}],
        "timing_summary": {"actual_duration_seconds": 5},
        "audio_timeline": {"shot_count": 1, "total_duration_seconds": 4},
    })
    result = QCEngine().inspect_task({}, {"id": "PROMPT-AUDIO-BAD", "type": "prompt", "outputs": [artifact]})
    assert result["success"] is False
    assert "audio_timeline 与镜头时长合计不一致" in result["shot_contract_checks"][0]["message"]


def test_prompt_qc_rejects_timeline_far_below_target_duration(tmp_path):
    artifact = _write(tmp_path / "prompts_short_episode.json", {
        "prompts": [
            {"shot_id": "S1", "duration": 5, "visual_prompt": "山门"},
            {"shot_id": "S2", "duration": 5, "visual_prompt": "剑光"},
        ],
        "timing_summary": {
            "target_duration_seconds": 60,
            "actual_duration_seconds": 10,
            "within_target_tolerance": False,
        },
    })
    result = QCEngine().inspect_task({}, {
        "id": "PROMPT-SHORT", "type": "prompt", "outputs": [artifact]
    })
    assert result["success"] is False
    assert result["shot_contract_checks"][0]["success"] is False
    assert "与目标 60s 不匹配" in result["shot_contract_checks"][0]["message"]


def test_prompt_qc_accepts_timeline_within_target_tolerance(tmp_path):
    artifact = _write(tmp_path / "prompts_on_target.json", {
        "prompts": [
            {"shot_id": "S1", "duration": 30, "visual_prompt": "山门"},
            {"shot_id": "S2", "duration": 29.8, "visual_prompt": "剑光"},
        ],
        "timing_summary": {
            "target_duration_seconds": 60,
            "actual_duration_seconds": 59.8,
            "within_target_tolerance": True,
        },
    })
    result = QCEngine().inspect_task({}, {
        "id": "PROMPT-ON-TARGET", "type": "prompt", "outputs": [artifact]
    })
    assert result["success"] is True


def test_prompt_qc_rejects_duration_drift_that_legacy_two_percent_tolerance_allowed(tmp_path):
    artifact = _write(tmp_path / "prompts_slightly_short.json", {
        "prompts": [
            {"shot_id": "S1", "duration": 30, "visual_prompt": "山门"},
            {"shot_id": "S2", "duration": 29.5, "visual_prompt": "剑光"},
        ],
        "timing_summary": {
            "target_duration_seconds": 60,
            "actual_duration_seconds": 59.5,
            "within_target_tolerance": True,
        },
    })
    result = QCEngine().inspect_task({}, {
        "id": "PROMPT-SLIGHT-DRIFT", "type": "prompt", "outputs": [artifact]
    })
    assert result["success"] is False
    assert result["shot_contract_checks"][0]["success"] is False
    assert "允许误差 ±0.3s" in result["shot_contract_checks"][0]["message"]
