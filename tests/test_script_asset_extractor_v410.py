from core.script_asset_extractor import ScriptAssetExtractor


class Registry:
    def __init__(self):
        self.items = []
        self.counter = 0

    def list_assets(self, **kwargs):
        return list(self.items)

    def register(self, **kwargs):
        self.counter += 1
        item = {"asset_id": f"A{self.counter}", **kwargs}
        self.items.append(item)
        return item


def test_extracts_structured_assets_and_preserves_shot_dialogue_prompt():
    registry = Registry()
    extractor = ScriptAssetExtractor(registry)
    plan = {
        "plan_id": "PLAN-TEST",
        "characters": [{"id": "CHAR-1", "name": "林霄", "description": "白衣剑修"}],
        "scenes": [{"id": "SCENE-1", "name": "青云山", "props": [{"id": "PROP-1", "name": "古剑"}]}],
        "shots": [{"id": "SHOT-1", "duration": 7, "visual_prompt": "moonlit sword",
                   "dialogue": [{"speaker": "林霄", "text": "剑来"}]}],
    }
    report = extractor.extract(plan, "EP-1")
    assert report["created_count"] == 4
    storyboard = next(x for x in registry.items if x["type"] == "storyboard")
    assert storyboard["metadata"]["visual_prompt"] == "moonlit sword"
    assert storyboard["metadata"]["dialogue"] == [{"speaker": "林霄", "text": "剑来"}]
    assert storyboard["metadata"]["duration_seconds"] == 7


def test_extraction_is_idempotent_by_plan_and_entity_id():
    registry = Registry()
    extractor = ScriptAssetExtractor(registry)
    plan = {"plan_id": "PLAN-IDEMPOTENT", "characters": [{"id": "C1", "name": "主角"}],
            "scenes": [], "shots": []}
    first = extractor.extract(plan)
    second = extractor.extract(plan)
    assert first["created_count"] == 1
    assert second["created_count"] == 0
    assert second["reused_count"] == 1
    assert len(registry.items) == 1


def test_explicit_props_deduplicate_across_plan_scene_and_shot():
    registry = Registry()
    extractor = ScriptAssetExtractor(registry)
    plan = {"plan_id": "PLAN-PROP", "characters": [], "scenes": [
        {"id": "S1", "name": "屋内", "props": [{"id": "P1", "name": "玉佩"}]}],
        "shots": [{"id": "SH1", "props": [{"id": "P1", "name": "玉佩"}]}]}
    report = extractor.extract(plan)
    assert report["prop_count"] == 1
    assert len([x for x in registry.items if x["type"] == "prop"]) == 1
