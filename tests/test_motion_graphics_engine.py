import os
import tempfile
from unittest.mock import patch

from PIL import Image
from core.motion_graphics_engine import MotionGraphicsEngine


def test_create_card_writes_valid_png_with_requested_dimensions():
    engine = MotionGraphicsEngine()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "title.png")
        result = engine.create_card("青云剑宗", path, "第一集：天劫降临", aspect_ratio="9:16")
        assert result["success"]
        assert os.path.isfile(path) and os.path.getsize(path) > 0
        with Image.open(path) as image:
            assert image.size == (1080, 1920)
            assert image.format == "PNG"


def test_create_card_rejects_empty_title_and_invalid_ratio():
    engine = MotionGraphicsEngine()
    with tempfile.TemporaryDirectory() as tmp:
        assert not engine.create_card("", os.path.join(tmp, "empty.png"))["success"]
        result = engine.create_card("Title", os.path.join(tmp, "bad.png"), aspect_ratio="4:3")
        assert not result["success"]
        assert not os.path.exists(os.path.join(tmp, "bad.png"))


def test_create_card_supports_landscape_and_known_styles():
    engine = MotionGraphicsEngine()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "landscape.png")
        result = engine.create_card("Sect Battle", path, aspect_ratio="16:9", style="horror")
        assert result["success"]
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert os.path.getsize(path) > 0


def test_render_card_rejects_invalid_duration_without_running_ffmpeg():
    engine = MotionGraphicsEngine()
    with patch("core.motion_graphics_engine.shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("core.motion_graphics_engine.subprocess.run") as run:
        result = engine.render_card("Title", "/tmp/title.mp4", duration_seconds=0)
    assert not result["success"]
    run.assert_not_called()


def test_render_card_verifies_non_empty_mp4_output():
    engine = MotionGraphicsEngine()
    with tempfile.TemporaryDirectory() as tmp:
        output = os.path.join(tmp, "card.mp4")

        def fake_run(command, capture_output, text, timeout):
            with open(output, "wb") as handle:
                handle.write(b"mp4-test")
            class Result:
                returncode = 0
                stderr = ""
            return Result()

        with patch("core.motion_graphics_engine.shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("core.motion_graphics_engine.subprocess.run", side_effect=fake_run) as run:
            result = engine.render_card("Title", output, duration_seconds=1, aspect_ratio="1:1")
        assert result["success"]
        assert result["size_bytes"] == len(b"mp4-test")
        assert result["duration_seconds"] == 1.0
        run.assert_called_once()
