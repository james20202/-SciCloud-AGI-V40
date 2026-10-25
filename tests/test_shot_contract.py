import pytest

from core.shot_contract import build_shot_manifest, normalize_shot, normalize_shots, timeline_duration


def test_legacy_storyboard_fields_normalize_without_losing_shot_context():
    shot = normalize_shot({
        "id": "SHOT-1", "index": 1, "duration": 5,
        "prompt": "青云剑宗，夜雨中的山门", "dialogue": "你终于来了",
        "narration": "风雨将至", "scene_id": "SCENE-2",
        "character_ids": [{"id": "CHAR-1"}, "CHAR-2", "CHAR-1"],
    })
    assert shot["shot_id"] == "SHOT-1"
    assert shot["visual_prompt"] == shot["prompt"] == "青云剑宗，夜雨中的山门"
    assert shot["dialogue"] == "你终于来了"
    assert shot["voiceover"] == "风雨将至"
    assert shot["scene_id"] == "SCENE-2"
    assert shot["character_ids"] == ["CHAR-1", "CHAR-2"]


def test_manifest_reports_duration_gap_instead_of_silently_stretching():
    manifest = build_shot_manifest([
        {"id": "S1", "duration": 5},
        {"shot_id": "S2", "duration_seconds": 5},
    ], target_duration=60)
    assert manifest["shot_count"] == 2
    assert manifest["planned_duration_seconds"] == 10
    assert manifest["duration_delta_seconds"] == -50
    assert manifest["duration_matches_target"] is False


def test_manifest_accepts_exact_duration_target():
    manifest = build_shot_manifest([{"id": "S1", "duration": 30}, {"id": "S2", "duration": 30}], target_duration=60)
    assert manifest["duration_matches_target"] is True
    assert timeline_duration(manifest["shots"]) == 60


@pytest.mark.parametrize("shot", [
    {"id": "S", "duration": 0},
    {"id": "S", "duration": float("nan")},
    {"id": "S", "duration": 3601},
    {"id": "S", "duration": "not-a-number"},
    {"id": "", "duration": 1},
])
def test_invalid_shot_contract_is_rejected(shot):
    with pytest.raises(ValueError):
        normalize_shot(shot)


def test_duplicate_shot_ids_are_rejected():
    with pytest.raises(ValueError, match="重复"):
        normalize_shots([{"id": "S1"}, {"shot_id": "S1"}])


def test_invalid_character_or_prompt_types_are_rejected():
    with pytest.raises(ValueError):
        normalize_shot({"id": "S1", "character_ids": "CHAR-1"})
    with pytest.raises(ValueError):
        normalize_shot({"id": "S1", "visual_prompt": ["not", "text"]})
