import json
import math
import os
import tempfile

from core.episode_timeline import build_episode_timeline


def test_canonical_timeline_has_contiguous_order_and_provenance():
    with tempfile.TemporaryDirectory() as root:
        clip1 = os.path.join(root, "shot1.mp4")
        clip2 = os.path.join(root, "shot2.mp4")
        audio = os.path.join(root, "shot1.wav")
        for p in (clip1, clip2, audio):
            with open(p, "wb") as f:
                f.write(b"media")
        job = {"shots": [
            {"shot_id": "S1", "artifacts": [{"kind": "audio", "path": audio}]},
            {"shot_id": "S2", "artifacts": []},
        ]}
        records = [
            {"shot_id": "S1", "path": clip1, "source_kind": "video", "duration_seconds": 4,
             "spec": {"visual_prompt": "剑光"}},
            {"shot_id": "S2", "path": clip2, "source_kind": "image_to_video_fallback", "duration_seconds": 5,
             "spec": {"visual_prompt": "山门"}},
        ]
        output = os.path.join(root, "canonical_timeline.json")
        result = build_episode_timeline(
            {"episode_id": "EP-TEST", "title": "测试", "aspect_ratio": "9:16"},
            job, records, output
        )
        with open(output, encoding="utf-8") as stream:
            timeline = json.load(stream)
        picture = timeline["tracks"][0]["children"]
        assert result["success"]
        assert picture[0]["start_seconds"] == 0
        assert picture[1]["start_seconds"] == 4
        assert picture[1]["end_seconds"] == 9
        assert timeline["duration_seconds"] == 9
        assert timeline["summary"]["real_video_scene_count"] == 1
        assert timeline["summary"]["fallback_scene_count"] == 1
        assert timeline["summary"]["audio_clip_count"] == 1
        assert picture[0]["metadata"]["visual_prompt"] == "剑光"


def test_timeline_uses_fallback_duration_for_invalid_duration():
    with tempfile.TemporaryDirectory() as root:
        clip = os.path.join(root, "shot.mp4")
        with open(clip, "wb") as stream:
            stream.write(b"media")
        out = os.path.join(root, "timeline.json")
        result = build_episode_timeline(
            {"episode_id": "EP-2"}, {"shots": []},
            [{"shot_id": "S1", "path": clip, "source_kind": "video", "duration_seconds": 0,
              "spec": {"duration": 6}}], out
        )
        assert result["timeline"]["duration_seconds"] == 6


def test_timeline_normalizes_nonfinite_duration_and_rejects_nonstandard_json():
    with tempfile.TemporaryDirectory() as root:
        clip = os.path.join(root, "shot.mp4")
        with open(clip, "wb") as stream:
            stream.write(b"media")
        out = os.path.join(root, "timeline.json")
        result = build_episode_timeline(
            {"episode_id": "EP-NAN"}, {"shots": []},
            [
                {"shot_id": "S1", "path": clip, "source_kind": "video",
                 "duration_seconds": math.nan, "spec": {"duration_seconds": math.inf, "duration": 7}},
                {"shot_id": "S2", "path": clip, "source_kind": "video",
                 "duration_seconds": -math.inf, "spec": {"duration": 3}},
            ], out
        )
        timeline = result["timeline"]
        assert timeline["tracks"][0]["children"][0]["duration_seconds"] == 7
        assert timeline["tracks"][0]["children"][1]["duration_seconds"] == 3
        assert math.isfinite(timeline["duration_seconds"])
        with open(out, encoding="utf-8") as stream:
            raw = stream.read()
        assert "NaN" not in raw
        assert "Infinity" not in raw
        json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def test_timeline_uses_zero_when_value_and_fallback_are_nonfinite():
    with tempfile.TemporaryDirectory() as root:
        clip = os.path.join(root, "shot.mp4")
        with open(clip, "wb") as stream:
            stream.write(b"media")
        out = os.path.join(root, "timeline.json")
        result = build_episode_timeline(
            {"episode_id": "EP-INF"}, {"shots": []},
            [{"shot_id": "S1", "path": clip, "duration_seconds": math.inf,
              "spec": {"duration_seconds": math.nan, "duration": math.inf}}], out
        )
        assert result["timeline"]["duration_seconds"] == 0
