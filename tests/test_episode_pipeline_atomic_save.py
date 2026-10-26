import json

import pytest

import core.episode_pipeline as module
from core.episode_pipeline import EpisodePipeline


def test_pipeline_save_replaces_state_atomically_and_cleans_temp_files(tmp_path):
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    original = {"episode_id": "EP-ATOMIC", "stage": "plan", "value": 1}
    pipeline._save(original)
    original_path = tmp_path / "episode_pipelines" / "EP-ATOMIC.json"

    updated = {"episode_id": "EP-ATOMIC", "stage": "media", "value": 2}
    pipeline._save(updated)

    assert json.loads(original_path.read_text(encoding="utf-8"))["value"] == 2
    assert list((tmp_path / "episode_pipelines").glob(".episode-pipeline-*.tmp")) == []


def test_pipeline_save_failure_preserves_previous_valid_state(tmp_path, monkeypatch):
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    pipeline._save({"episode_id": "EP-SAFE", "value": "original"})
    original_path = tmp_path / "episode_pipelines" / "EP-SAFE.json"
    original_text = original_path.read_text(encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic replace failure"):
        pipeline._save({"episode_id": "EP-SAFE", "value": "corrupted candidate"})

    assert original_path.read_text(encoding="utf-8") == original_text
    assert list((tmp_path / "episode_pipelines").glob(".episode-pipeline-*.tmp")) == []


@pytest.mark.parametrize("episode_id", ["", ".", "..", "../outside", "nested/episode", r"nested\\episode", "bad\x00id"])
def test_pipeline_path_rejects_unsafe_episode_ids(tmp_path, episode_id):
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    with pytest.raises(ValueError):
        pipeline._path(episode_id)
