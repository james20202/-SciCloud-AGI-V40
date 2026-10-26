import json
import os

import pytest

import core.episode_engine as episode_module
from core.episode_engine import EpisodeEngine


def test_episode_record_rejects_path_traversal(tmp_path):
    engine = EpisodeEngine(project_dir=str(tmp_path))
    with pytest.raises(ValueError, match="路径分隔符"):
        engine._path("../outside")
    with pytest.raises(ValueError, match="路径分隔符"):
        engine._path("folder\\episode")


def test_episode_save_replaces_record_atomically(tmp_path):
    engine = EpisodeEngine(project_dir=str(tmp_path))
    episode = {"episode_id": "EP-123", "status": "planned"}
    engine._save(episode)
    path = engine._path("EP-123")
    with open(path, encoding="utf-8") as handle:
        original = json.load(handle)

    assert original["status"] == "planned"
    assert not [name for name in os.listdir(engine.root) if name.endswith(".tmp")]


def test_episode_save_preserves_old_record_when_replace_fails(tmp_path, monkeypatch):
    engine = EpisodeEngine(project_dir=str(tmp_path))
    engine._save({"episode_id": "EP-123", "status": "planned"})
    path = engine._path("EP-123")
    def fail_replace(source, destination):
        raise OSError("simulated atomic replace failure")
    monkeypatch.setattr(episode_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated"):
        engine._save({"episode_id": "EP-123", "status": "corrupted"})

    with open(path, encoding="utf-8") as handle:
        assert json.load(handle)["status"] == "planned"
    assert not [name for name in os.listdir(engine.root) if name.endswith(".tmp")]
