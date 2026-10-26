import pytest

from core.shot_batch import build_shot_batch_manifest


def test_shot_batch_preserves_identity_prompt_duration_and_references():
    manifest = build_shot_batch_manifest([
        {
            "shot_id": "SHOT-0001", "shot_index": 1, "duration": 4.5,
            "visual_prompt": "青云山门夜景", "prompt": "cinematic xianxia mountain gate",
            "dialogue": "何人闯山？", "voiceover": "天劫将至",
            "scene_id": "SCENE-1", "character_ids": ["CHAR-1", "CHAR-2"],
        },
        {
            "shot_id": "SHOT-0002", "shot_index": 2, "duration": 5.5,
            "visual_prompt": "主角拔剑", "prompt": "hero draws sword",
        },
    ], workflow_id="WF-123", target_duration=10, workflow_registry_id="video-local")
    assert manifest["shot_count"] == 2
    assert manifest["planned_duration_seconds"] == 10
    assert manifest["duration_matches_target"] is True
    first = manifest["jobs"][0]
    assert first["job_id"] == "WF-123__SHOT-0001"
    assert first["duration_seconds"] == 4.5
    assert first["prompt"] == "cinematic xianxia mountain gate"
    assert first["visual_prompt"] == "青云山门夜景"
    assert first["dialogue"] == "何人闯山？"
    assert first["character_ids"] == ["CHAR-1", "CHAR-2"]
    assert first["output_path"] == "output/shots/WF-123/SHOT-0001.mp4"
    assert first["workflow_registry_id"] == "video-local"


def test_shot_batch_sanitizes_paths_and_reports_duration_mismatch():
    manifest = build_shot_batch_manifest([
        {"id": "../bad/name", "duration": 3, "visual_prompt": "scene", "prompt": "scene"}
    ], workflow_id="../WF", target_duration=8)
    assert manifest["jobs"][0]["output_path"] == "output/shots/WF/bad_name.mp4"
    assert manifest["duration_matches_target"] is False


def test_shot_batch_rejects_missing_visual_prompt_and_empty_batch():
    with pytest.raises(ValueError, match="不能为空"):
        build_shot_batch_manifest([], workflow_id="WF")
    with pytest.raises(ValueError, match="visual_prompt"):
        build_shot_batch_manifest([{"id": "S1", "prompt": ""}], workflow_id="WF")


def test_shot_batch_rejects_duplicate_shot_ids():
    with pytest.raises(ValueError, match="重复"):
        build_shot_batch_manifest([
            {"id": "S1", "visual_prompt": "a", "prompt": "a"},
            {"id": "S1", "visual_prompt": "b", "prompt": "b"},
        ], workflow_id="WF")
