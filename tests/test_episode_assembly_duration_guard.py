from types import SimpleNamespace

from core.episode_pipeline import EpisodePipeline


def _pipeline_record(episode_id, duration=60):
    return {
        "episode_id": episode_id,
        "plan_id": "PLAN-1",
        "stage": "media",
        "duration_seconds": duration,
        "aspect_ratio": "9:16",
        "shot_run_id": "RUN-1",
        "stages": {
            stage: {"status": "pending", "result": None}
            for stage in EpisodePipeline.STAGES
        },
    }


def test_assembly_blocks_when_shot_duration_is_far_below_episode_target(tmp_path, monkeypatch):
    import core.episode_pipeline as module

    source = tmp_path / "shot.mp4"
    source.write_bytes(b"fixture")
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    record = _pipeline_record("EP-SHORT", 60)
    record["stages"]["media"] = {"status": "done", "result": {"success": True}}
    pipeline._save(record)

    monkeypatch.setattr(
        module.shot_production_engine,
        "load",
        lambda _run_id: {
            "shots": [{
                "shot_id": "SHOT-1",
                "index": 1,
                "spec": {"duration_seconds": 30},
                "artifacts": [{"kind": "video", "path": str(source)}],
            }]
        },
    )
    monkeypatch.setattr(
        module.local_media_engine,
        "probe",
        lambda _path: {"success": True, "duration_seconds": 30},
    )
    monkeypatch.setattr(
        module.local_media_engine,
        "normalize_video_clip",
        lambda _src, dst, **kwargs: {"success": True, "duration_seconds": 30, "path": dst},
    )
    monkeypatch.setattr(
        module.episode_audio_engine,
        "prepare",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("audio/assembly must not start")),
    )

    result = pipeline.assemble("EP-SHORT")

    assert result["status"] == "blocked"
    assert result["stages"]["assemble"]["status"] == "blocked"
    assert "镜头时长合计与剧集目标不匹配" in result["stages"]["assemble"]["result"]["message"]
    assert result["stages"]["assemble"]["result"]["detail"]["expected_duration_seconds"] == 60
    assert result["stages"]["assemble"]["result"]["detail"]["actual_duration_seconds"] == 30


def test_assembly_blocks_invalid_episode_duration_before_audio_prepare(tmp_path, monkeypatch):
    import core.episode_pipeline as module

    source = tmp_path / "shot.mp4"
    source.write_bytes(b"fixture")
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    record = _pipeline_record("EP-NAN", float("nan"))
    record["stages"]["media"] = {"status": "done", "result": {"success": True}}
    # Use a valid persisted value first, then corrupt the record to model legacy/bad input.
    record["duration_seconds"] = 60
    pipeline._save(record)
    loaded = pipeline.load("EP-NAN")
    loaded["duration_seconds"] = float("nan")
    # The pipeline's JSON persistence rejects NaN, so exercise the guard with a JSON-compatible invalid string.
    loaded["duration_seconds"] = "not-a-duration"
    pipeline._save(loaded)

    monkeypatch.setattr(
        module.shot_production_engine,
        "load",
        lambda _run_id: {
            "shots": [{
                "shot_id": "SHOT-1",
                "index": 1,
                "spec": {"duration_seconds": 5},
                "artifacts": [{"kind": "video", "path": str(source)}],
            }]
        },
    )
    monkeypatch.setattr(module.local_media_engine, "probe", lambda _path: {"success": True, "duration_seconds": 5})
    monkeypatch.setattr(
        module.local_media_engine,
        "normalize_video_clip",
        lambda _src, dst, **kwargs: {"success": True, "duration_seconds": 5, "path": dst},
    )
    monkeypatch.setattr(
        module.episode_audio_engine,
        "prepare",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("audio/assembly must not start")),
    )

    result = pipeline.assemble("EP-NAN")
    assert result["status"] == "blocked"
    assert "剧集目标时长无效" in result["stages"]["assemble"]["result"]["message"]
