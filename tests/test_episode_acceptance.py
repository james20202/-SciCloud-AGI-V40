from core.episode_acceptance import validate_episode_timeline


def timeline(clips, duration):
    return {"duration_seconds": duration, "tracks": [
        {"track_type": "video", "children": clips},
        {"track_type": "audio", "children": []},
    ]}


def clip(start, duration, end=None):
    return {"start_seconds": start, "duration_seconds": duration,
            "end_seconds": start + duration if end is None else end}


def test_accepts_contiguous_timeline_within_target_tolerance():
    report = validate_episode_timeline(timeline([clip(0, 30), clip(30, 30)], 60), 60)
    assert report["passed"] is True
    assert report["shot_count"] == 2
    assert report["duration_seconds"] == 60


def test_rejects_gap_or_overlap():
    report = validate_episode_timeline(timeline([clip(0, 10), clip(11, 10)], 21), 21)
    assert report["passed"] is False
    assert "timeline_gap_or_overlap" in {e["code"] for e in report["errors"]}


def test_rejects_mismatched_clip_end_and_declared_duration():
    report = validate_episode_timeline(timeline([clip(0, 10, 12)], 10), 10)
    codes = {e["code"] for e in report["errors"]}
    assert "clip_end_mismatch" in codes
    assert "declared_timeline_duration_mismatch" in codes


def test_rejects_empty_picture_track():
    report = validate_episode_timeline(timeline([], 0), 60)
    assert report["passed"] is False
    assert "missing_picture_clips" in {e["code"] for e in report["errors"]}
