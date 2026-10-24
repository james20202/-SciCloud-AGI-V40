import json

from core.otio_export import export_canonical_to_otio, save_otio_file


def test_canonical_timeline_exports_otio_video_audio_gaps_and_provenance(tmp_path):
    video = tmp_path / "shot.mp4"
    audio = tmp_path / "voice.wav"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")
    timeline = {
        "project_id": "EP-TEST", "title": "测试剧集", "frame_rate": 24,
        "duration_seconds": 8, "schema": "otio-inspired",
        "tracks": [
            {"track_type": "video", "children": [
                {"shot_id": "S1", "scene_id": "SC1", "name": "剑光", "start_seconds": 0,
                 "duration_seconds": 4, "media_reference": {"path": str(video)},
                 "metadata": {"generation": {"is_real_video": True}, "visual_prompt": "剑光"}},
                {"shot_id": "S2", "scene_id": "SC2", "name": "山门", "start_seconds": 4,
                 "duration_seconds": 4, "media_reference": {"path": str(video)},
                 "metadata": {"generation": {"fallback_used": True}}},
            ]},
            {"track_type": "audio", "children": [
                {"shot_id": "S2", "clip_id": "S2_audio", "start_seconds": 4,
                 "duration_seconds": 4, "media_reference": {"path": str(audio)}},
            ]},
        ],
    }
    otio = export_canonical_to_otio(timeline)
    assert otio["OTIO_SCHEMA"] == "Timeline.1"
    tracks = otio["tracks"]["children"]
    assert tracks[0]["kind"] == "Video"
    assert len(tracks[0]["children"]) == 2
    assert tracks[0]["children"][0]["source_range"]["duration"]["value"] == 96
    assert tracks[0]["children"][0]["media_reference"]["target_url"].startswith("file:")
    assert tracks[0]["children"][1]["metadata"]["scicloud"]["generation"]["fallback_used"] is True
    assert tracks[1]["children"][0]["OTIO_SCHEMA"] == "Gap.1"
    assert tracks[1]["children"][1]["name"] == "S2_audio"
    path = save_otio_file(otio, tmp_path / "timeline.otio")
    assert json.load(open(path, encoding="utf-8"))["OTIO_SCHEMA"] == "Timeline.1"
