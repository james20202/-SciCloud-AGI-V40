from core.audio_timeline import build_audio_timeline, render_srt


def test_audio_timeline_preserves_shot_ranges_and_subtitle_text():
    timeline = build_audio_timeline([
        {"shot_id": "S1", "duration": 2.5, "dialogue": "你是谁？", "voiceover": "夜幕降临"},
        {"shot_id": "S2", "duration": 3, "dialogue": "", "voiceover": "剑光一闪"},
    ])
    assert timeline["total_duration_seconds"] == 5.5
    assert timeline["segments"][1]["start_seconds"] == 2.5
    assert [cue["source"] for cue in timeline["subtitle_cues"]] == ["dialogue", "voiceover"]
    srt = render_srt(timeline)
    assert "00:00:00,000 --> 00:00:02,500" in srt
    assert "你是谁？" in srt
    assert "剑光一闪" in srt


def test_audio_timeline_does_not_claim_real_audio_alignment():
    timeline = build_audio_timeline([{"shot_id": "S1", "duration": 4, "voiceover": "旁白"}])
    assert timeline["timing_source"] == "planned_shot_durations"
    assert timeline["requires_audio_alignment"] is True


def test_srt_rejects_overlapping_or_invalid_cues():
    try:
        render_srt({"subtitle_cues": [
            {"start_seconds": 0, "end_seconds": 2, "text": "A"},
            {"start_seconds": 1, "end_seconds": 3, "text": "B"},
        ]})
    except ValueError as exc:
        assert "不能重叠" in str(exc)
    else:
        raise AssertionError("overlapping cues should be rejected")


def test_audio_timeline_rejects_duplicate_shot_ids():
    try:
        build_audio_timeline([{"shot_id": "S1"}, {"shot_id": "S1"}])
    except ValueError as exc:
        assert "重复" in str(exc)
    else:
        raise AssertionError("duplicate shot IDs should be rejected")
