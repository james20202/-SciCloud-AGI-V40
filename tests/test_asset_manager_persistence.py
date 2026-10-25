import json

import core.asset_manager as asset_module


def test_asset_registry_atomic_write_and_nonempty_file_validation(tmp_path, monkeypatch):
    db = tmp_path / "assets.json"
    monkeypatch.setattr(asset_module, "ASSET_DB", str(db))
    manager = asset_module.AssetManager()

    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    assert manager.register_result_file(str(empty), asset_type="image") is None

    valid = tmp_path / "shot.png"
    valid.write_bytes(b"image-bytes")
    asset = manager.register_result_file(str(valid), asset_type="image")
    assert asset["metadata"]["size"] == len(b"image-bytes")
    assert json.loads(db.read_text(encoding="utf-8"))[0]["asset_id"] == asset["asset_id"]
    assert not list(tmp_path.glob(".assets-*.tmp"))


def test_asset_execution_preserves_structured_output_metadata(tmp_path, monkeypatch):
    db = tmp_path / "assets.json"
    monkeypatch.setattr(asset_module, "ASSET_DB", str(db))
    manager = asset_module.AssetManager()
    output = tmp_path / "shot.mp4"
    output.write_bytes(b"video")

    assets = manager.register_execution(
        {"id": "TASK-VIDEO", "type": "video"},
        [{"path": str(output), "shot_id": "SHOT-1", "duration": 4.5}],
        project_id="PLAN-1",
    )

    assert len(assets) == 1
    assert assets[0]["metadata"]["output_metadata"] == {"shot_id": "SHOT-1", "duration": 4.5}
