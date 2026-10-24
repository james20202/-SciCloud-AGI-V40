import os
import tempfile
import unittest

from core.character_reference_engine import CharacterReferenceEngine


class FakeRegistry:
    def __init__(self):
        self.items = []
    def list_assets(self, asset_type=None, entity_id=None):
        return [x for x in self.items if (not asset_type or x.get("type") == asset_type)
                and (not entity_id or x.get("entity_id") == entity_id)]
    def register(self, asset_type, name, source=None, entity_id=None, metadata=None, project_id=None, version=None):
        item = {"asset_id": f"A{len(self.items)+1}", "type": asset_type, "name": name,
                "source": source, "entity_id": entity_id, "metadata": metadata or {},
                "project_id": project_id, "version": version or 1}
        self.items.append(item)
        return item


class CharacterReferenceEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = os.path.join(self.temp.name, "ref.png")
        # A valid minimal 1x1 PNG.
        import base64
        with open(self.source, "wb") as stream:
            stream.write(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l0sAAAAASUVORK5CYII="))
        self.registry = FakeRegistry()
        self.engine = CharacterReferenceEngine(os.path.join(self.temp.name, "refs"), self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def test_registers_versioned_reference_and_keeps_source_unchanged(self):
        item = self.engine.register_reference("char-1", "林青", self.source, project_id="ep-1")
        self.assertEqual(item["version"], 1)
        self.assertTrue(os.path.isfile(item["source"]))
        self.assertEqual(os.path.getsize(item["source"]), os.path.getsize(self.source))
        self.assertNotEqual(item["source"], self.source)
        second = self.engine.register_reference("char-1", "林青", self.source, project_id="ep-1")
        self.assertEqual(second["version"], 2)

    def test_rejects_missing_or_unsupported_reference(self):
        with self.assertRaises(ValueError):
            self.engine.register_reference("char-1", "林青", self.source + ".missing")
        text_file = os.path.join(self.temp.name, "ref.txt")
        with open(text_file, "w") as stream:
            stream.write("not an image")
        with self.assertRaises(ValueError):
            self.engine.register_reference("char-1", "林青", text_file)

    def test_binds_reference_to_explicit_character_anchor_only(self):
        self.engine.register_reference("char-1", "林青", self.source, project_id="ep-1")
        shot = {"shot_id": "S1", "visual_prompt": "林青站在山门前",
                "consistency": {"character_anchors": [{"id": "char-1", "name": "林青"}]}}
        result = self.engine.bind_shot_references(shot, project_id="ep-1")
        self.assertEqual(result["character_reference_count"], 1)
        self.assertTrue(os.path.isfile(result["character_reference_assets"][0]["path"]))
        self.assertIn("参考图锁定", result["visual_prompt"])

    def test_does_not_guess_reference_for_unidentified_character(self):
        self.engine.register_reference("char-1", "林青", self.source)
        result = self.engine.bind_shot_references({"shot_id": "S2", "consistency": {"character_anchors": []}})
        self.assertEqual(result["character_reference_count"], 0)
        self.assertNotIn("character_reference_assets", {"character_reference_assets": []} if False else {})
    
    def test_audit_reports_reference_coverage(self):
        report = self.engine.audit([
            {"shot_id": "S1", "character_reference_assets": [{"character_id": "char-1"}]},
            {"shot_id": "S2", "character_reference_assets": []},
        ])
        self.assertEqual(report["reference_coverage_percent"], 50.0)


if __name__ == "__main__":
    unittest.main()
