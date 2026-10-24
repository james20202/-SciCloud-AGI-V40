import os
import tempfile
import unittest

from core.character_reference_comfyui import bind_character_references


class CharacterReferenceComfyUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "ref.png")
        with open(self.path, "wb") as stream:
            stream.write(b"test-image-bytes")
        self.model = {"endpoint": "http://127.0.0.1:8188"}
        self.refs = [{"character_id": "char-1", "character_name": "林青", "path": self.path}]

    def tearDown(self):
        self.temp.cleanup()

    def test_injects_uploaded_image_only_into_explicit_reference_node(self):
        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "__SCICLOUD_CHARACTER_REFERENCE__:char-1"},
                  "_meta": {"title": "林青 reference"}},
            "2": {"class_type": "LoadImage", "inputs": {"image": "background.png"}, "_meta": {"title": "Background"}}
        }
        calls = []
        def uploader(model, path):
            calls.append(path)
            return "scicloud_refs/ref_v1.png"
        result, report = bind_character_references(workflow, self.refs, self.model, uploader=uploader)
        self.assertEqual(result["1"]["inputs"]["image"], "scicloud_refs/ref_v1.png")
        self.assertEqual(result["2"]["inputs"]["image"], "background.png")
        self.assertEqual(report["bound"], 1)
        self.assertEqual(len(calls), 1)
        self.assertTrue(workflow["1"]["inputs"]["image"].startswith("__SCICLOUD"))

    def test_unmarked_workflow_reports_reference_not_injected(self):
        workflow = {"1": {"class_type": "LoadImage", "inputs": {"image": "input.png"}}}
        result, report = bind_character_references(workflow, self.refs, self.model, uploader=lambda *a: self.fail("must not upload"))
        self.assertEqual(report["bound"], 0)
        self.assertFalse(report["success"])
        self.assertIn("没有匹配", report["warnings"][0]["message"])

    def test_rejects_non_loopback_endpoint(self):
        with self.assertRaises(ValueError):
            bind_character_references({"1": {}}, self.refs, {"endpoint": "https://example.com"})

    def test_no_references_is_noop(self):
        workflow = {"1": {"class_type": "LoadImage", "inputs": {"image": "input.png"}}}
        result, report = bind_character_references(workflow, [], self.model)
        self.assertEqual(result, workflow)
        self.assertEqual(report["bound"], 0)


if __name__ == "__main__":
    unittest.main()
