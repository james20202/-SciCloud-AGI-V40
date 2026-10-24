import os
import tempfile
import unittest

from PIL import Image

from core.reference_image_quality import reference_image_quality_engine


class ReferenceImageQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.a = os.path.join(self.temp.name, "a.png")
        self.b = os.path.join(self.temp.name, "b.png")
        self.c = os.path.join(self.temp.name, "c.png")
        Image.new("RGB", (64, 64), (120, 30, 220)).save(self.a)
        Image.new("RGB", (64, 64), (120, 30, 220)).save(self.b)
        Image.new("RGB", (64, 64), (20, 240, 10)).save(self.c)

    def tearDown(self):
        self.temp.cleanup()

    def test_identical_images_have_high_advisory_score(self):
        report = reference_image_quality_engine.compare(self.a, self.b, "林青")
        self.assertTrue(report["success"])
        self.assertGreaterEqual(report["score"], 0.99)
        self.assertIn("不是人脸识别", report["limitations"])

    def test_visually_different_images_score_lower(self):
        same = reference_image_quality_engine.compare(self.a, self.b)
        different = reference_image_quality_engine.compare(self.a, self.c)
        self.assertTrue(different["success"])
        self.assertLess(different["score"], same["score"])

    def test_missing_images_are_not_evaluated(self):
        report = reference_image_quality_engine.compare(self.a, self.c + ".missing")
        self.assertFalse(report["success"])
        self.assertEqual(report["status"], "not_evaluated")


if __name__ == "__main__":
    unittest.main()
