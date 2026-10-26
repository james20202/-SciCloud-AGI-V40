import json
import os

import pytest

from core.episode_timeline import build_episode_timeline


def _media(path, payload=b"media"):
    path.write_bytes(payload)
    return str(path)


def test_timeline_preserves_dialogue_voiceover_and_character_metadata(tmp_path):
    clip = _media(tmp_path / "shot.mp4")
    output = tmp_path / "timeline.json"
    result = build_episode_timeline(
        {"episode_id": "EP-META"},
        {"shots": []},
        [{
            "shot_id": "SHOT-1",
            "path": clip,
            "source_kind": "video",
            "duration_seconds": 4.5,
            "target_duration_seconds": 5,
            "spec": {
                "visual_prompt": "月下山门",
                "dialogue": "来者何人？",
                "narration": "夜色渐深",
                "character_ids": ["CHAR-1"],
                "location_id": "LOC-1",
            },
        }],
        str(output),
    )
    metadata = result["timeline"]["tracks"][0]["children"][0]["metadata"]
    assert metadata["visual_prompt"] == "月下山门"
    assert metadata["dialogue"] == "来者何人？"
    assert metadata["voiceover"] == "夜色渐深"
    assert metadata["character_ids"] == ["CHAR-1"]
    assert metadata["location_id"] == "LOC-1"
    assert metadata["target_duration_seconds"] == 5
    assert json.loads(output.read_text(encoding="utf-8"))["duration_seconds"] == 4.5


def test_timeline_rejects_empty_clip_records(tmp_path):
    with pytest.raises(ValueError, match="至少包含一个镜头媒体记录"):
        build_episode_timeline({"episode_id": "EP-EMPTY"}, {"shots": []}, [], str(tmp_path / "timeline.json"))


def test_timeline_rejects_duplicate_shot_ids_without_overwriting_existing_file(tmp_path):
    clip = _media(tmp_path / "shot.mp4")
    output = tmp_path / "timeline.json"
    output.write_text('{"existing": true}', encoding="utf-8")
    records = [
        {"shot_id": "SAME", "path": clip, "duration_seconds": 2, "spec": {}},
        {"shot_id": "SAME", "path": clip, "duration_seconds": 3, "spec": {}},
    ]
    with pytest.raises(ValueError, match="重复"):
        build_episode_timeline({"episode_id": "EP-DUP"}, {"shots": []}, records, str(output))
    assert json.loads(output.read_text(encoding="utf-8")) == {"existing": True}
    assert list(tmp_path.glob(".canonical-timeline-*.tmp")) == []


def test_timeline_rejects_missing_or_empty_media(tmp_path):
    missing = str(tmp_path / "missing.mp4")
    empty = _media(tmp_path / "empty.mp4", b"")
    for path in (missing, empty):
        with pytest.raises(ValueError, match="不存在或为空"):
            build_episode_timeline(
                {"episode_id": "EP-BAD"},
                {"shots": []},
                [{"shot_id": "S1", "path": path, "duration_seconds": 2, "spec": {}}],
                str(tmp_path / "timeline.json"),
            )
