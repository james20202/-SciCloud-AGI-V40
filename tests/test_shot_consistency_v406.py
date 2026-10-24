import json
from core.shot_consistency import ShotConsistencyEngine, shot_fingerprint, valid_artifacts


def test_consistency_bible_enriches_character_costume_scene_and_style():
    engine = ShotConsistencyEngine()
    bible = engine.build_bible({
        "intent": {"genre": "玄幻"},
        "characters": [{"id": "CHAR-1", "name": "林渊", "appearance": "黑发金瞳", "costume": "玄黑长袍"}],
        "scenes": [{"id": "SCENE-1", "name": "青云山", "visual_description": "云海与古松", "lighting": "冷月光"}],
    })
    shot = engine.enrich_shot({"scene_id": "SCENE-1", "character_ids": ["CHAR-1"], "visual_prompt": "御剑登山"}, bible)
    assert shot["consistency"]["character_ids"] == ["CHAR-1"]
    assert shot["consistency"]["scene_anchor"]["id"] == "SCENE-1"
    assert "黑发金瞳" in shot["visual_prompt"]
    assert "玄黑长袍" in shot["visual_prompt"]
    assert "云海与古松" in shot["visual_prompt"]
    assert "统一视觉风格" in shot["visual_prompt"]


def test_fingerprint_is_stable_but_prompt_changes_invalidate_cache():
    original = {"visual_prompt": "御剑", "duration": 5, "status": "planned"}
    same = {"duration": 5, "status": "done", "visual_prompt": "御剑"}
    changed = {"visual_prompt": "御剑破阵", "duration": 5}
    assert shot_fingerprint(original) == shot_fingerprint(same)
    assert shot_fingerprint(original) != shot_fingerprint(changed)


def test_valid_artifacts_filters_missing_and_empty_files(tmp_path):
    good = tmp_path / "image.png"
    empty = tmp_path / "empty.png"
    good.write_bytes(b"image")
    empty.write_bytes(b"")
    result = valid_artifacts([
        {"kind": "image", "path": str(good)},
        {"kind": "image", "path": str(good)},
        {"kind": "image", "path": str(empty)},
        {"kind": "video", "path": str(tmp_path / "missing.mp4")},
    ])
    assert len(result) == 1
    assert result[0]["size"] == 5
