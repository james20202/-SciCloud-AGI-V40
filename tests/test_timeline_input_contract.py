import pytest

from core.episode_timeline import build_episode_timeline


def _clip(path):
    path.write_bytes(b"video")
    return {"shot_id": "S1", "path": str(path), "duration_seconds": 2, "spec": {}}


@pytest.mark.parametrize("shot_job", [[], "invalid", 7])
def test_timeline_rejects_non_object_shot_job(tmp_path, shot_job):
    with pytest.raises(ValueError, match="shot_job 必须是对象"):
        build_episode_timeline(
            {"episode_id": "EP-1"}, shot_job,
            [_clip(tmp_path / "shot.mp4")], str(tmp_path / "timeline.json"),
        )


def test_timeline_rejects_non_list_job_shots(tmp_path):
    with pytest.raises(ValueError, match="shots 必须是列表"):
        build_episode_timeline(
            {"episode_id": "EP-1"}, {"shots": {}},
            [_clip(tmp_path / "shot.mp4")], str(tmp_path / "timeline.json"),
        )


@pytest.mark.parametrize("shots, message", [
    ([None], "必须是对象"),
    ([{"artifacts": []}], "缺少 shot_id"),
    ([{"shot_id": "S1", "artifacts": {}}], "artifacts 必须是列表"),
    ([{"shot_id": "S1", "artifacts": [None]}], "非对象记录"),
    ([{"shot_id": "S1", "artifacts": []}, {"shot_id": "S1", "artifacts": []}], "ID 重复"),
])
def test_timeline_rejects_malformed_job_shot_artifacts(tmp_path, shots, message):
    with pytest.raises(ValueError, match=message):
        build_episode_timeline(
            {"episode_id": "EP-1"}, {"shots": shots},
            [_clip(tmp_path / "shot.mp4")], str(tmp_path / "timeline.json"),
        )


def test_timeline_rejects_empty_output_path(tmp_path):
    with pytest.raises(ValueError, match="output_path"):
        build_episode_timeline(
            {"episode_id": "EP-1"}, {"shots": []},
            [_clip(tmp_path / "shot.mp4")], "",
        )


def test_non_object_spec_falls_back_without_crashing(tmp_path):
    clip = _clip(tmp_path / "shot.mp4")
    clip["spec"] = "legacy malformed spec"
    result = build_episode_timeline(
        {"episode_id": "EP-1"}, {"shots": []},
        [clip], str(tmp_path / "timeline.json"),
    )
    assert result["timeline"]["tracks"][0]["children"][0]["scene_id"] == ""
