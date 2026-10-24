import json
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
        timeline = json.load(open(output, encoding="utf-8"))
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
        open(clip, "wb").write(b"media")
        out = os.path.join(root, "timeline.json")
        result = build_episode_timeline(
            {"episode_id": "EP-2"}, {"shots": []},
            [{"shot_id": "S1", "path": clip, "source_kind": "video", "duration_seconds": 0,
              "spec": {"duration": 6}}], out
        )
        assert result["timeline"]["duration_seconds"] == 6
