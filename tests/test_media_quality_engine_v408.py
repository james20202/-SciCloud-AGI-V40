import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from core.media_quality_engine import MediaQualityEngine


class MediaQualityEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "episode.mp4")
        with open(self.path, "wb") as stream:
            stream.write(b"media")
        self.ffprobe_json = json.dumps({
            "format": {"duration": "10.0", "size": "5", "format_name": "mov,mp4"},
            "streams": [{"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
                        {"codec_type": "audio", "codec_name": "aac"}]
        })

    def tearDown(self):
        self.temp.cleanup()

    def test_reports_black_frames_and_long_silence_as_warnings(self):
        def runner(command, **kwargs):
            if command[0] == "ffprobe":
                return SimpleNamespace(returncode=0, stdout=self.ffprobe_json, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr=(
                "black_start:2.0 black_end:4.0 black_duration:2.0\n"
                "silence_start:6.0\nsilence_end:9.0 | silence_duration:3.0\n"))
        engine = MediaQualityEngine(runner=runner, which=lambda name: "/usr/bin/" + name)
        report = engine.inspect(self.path, expected_duration=10)
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["black_segments"]), 1)
        self.assertEqual(len(report["silence_segments"]), 1)
        self.assertEqual({x["code"] for x in report["warnings"]}, {"black_frames", "long_silence"})

    def test_missing_video_stream_fails_quality_gate(self):
        payload = json.dumps({"format": {"duration": "10", "size": "5"}, "streams": [{"codec_type": "audio"}]})
        def runner(command, **kwargs):
            if command[0] == "ffprobe":
                return SimpleNamespace(returncode=0, stdout=payload, stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        engine = MediaQualityEngine(runner=runner, which=lambda name: "/usr/bin/" + name)
        report = engine.inspect(self.path)
        self.assertFalse(report["passed"])
        self.assertIn("missing_video_stream", report["errors"])

    def test_missing_file_is_rejected_without_running_tools(self):
        engine = MediaQualityEngine(which=lambda name: None)
        report = engine.inspect(self.path + ".missing")
        self.assertFalse(report["passed"])
        self.assertIn("missing_file", report["errors"])


if __name__ == "__main__":
    unittest.main()
