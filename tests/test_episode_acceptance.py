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


def test_rejects_nan_and_infinite_clip_timing():
    import math
    for bad in (math.nan, math.inf, -math.inf):
        report = validate_episode_timeline(timeline([clip(0, bad, bad)], bad), 60)
        codes = {e["code"] for e in report["errors"]}
        assert report["passed"] is False
        assert "nonfinite_clip_timing" in codes


def test_rejects_nonfinite_declared_duration():
    import math
    report = validate_episode_timeline(timeline([clip(0, 60)], math.nan), 60)
    assert report["passed"] is False
    assert "declared_timeline_duration_mismatch" in {e["code"] for e in report["errors"]}


def test_rejects_nonfinite_target_duration():
    import math
    report = validate_episode_timeline(timeline([clip(0, 60)], math.inf), math.inf)
    assert report["passed"] is False
    assert "invalid_target_duration" in {e["code"] for e in report["errors"]}
