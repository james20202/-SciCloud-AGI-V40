"""Tests for the top-5 UI honesty fixes (UI_AUDIT.md).

Runnable without pytest: `python3 tests/test_top5_honesty.py`
runs every test_* function and exits non-zero on any failure.
Under pytest the same test_* functions run as plain tests (no
fixtures), so CI keeps working either way.

Qt pages are NOT imported here (no PySide6 in the test VM):
the honest logic lives in small pure core helpers, and the pages
are checked by source assertions (no fake strings, no fake calls).
"""
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO = os.path.join(os.path.dirname(__file__), "..")


def _read(relpath):
    with open(os.path.join(REPO, relpath), encoding="utf-8") as stream:
        return stream.read()


def test_dashboard_summary_uses_real_workflow_data():
    from core.dashboard_summary import summarize_workflows

    workflows = [
        {
            "workflow_id": "WF-TEST1",
            "title": "竹林夜行",
            "status": "completed",
            "created_at": "2026-10-27T22:15:00",
            "tasks": [
                {"type": "story", "status": "done"},
                {"type": "storyboard", "status": "done"},
                {"type": "character", "status": "done"},
                {"type": "scene", "status": "failed"},
                {"type": "video", "status": "pending"},
            ],
        },
        {
            "workflow_id": "WF-TEST0",
            "title": "金色样片",
            "status": "failed",
            "created_at": "2026-10-26T21:00:00",
            "tasks": [{"type": "story", "status": "done"}],
        },
    ]
    summary = summarize_workflows(workflows)
    assert summary["latest"]["title"] == "竹林夜行"
    assert summary["latest"]["done"] == 3
    assert summary["latest"]["total"] == 5
    assert summary["latest"]["progress"] == 60
    stages = {s["name"]: s["status"] for s in summary["pipeline"]}
    assert stages["剧本"] == "已完成"
    assert stages["分镜"] == "已完成"
    assert stages["场景"] == "待处理"  # failed is not done, not running
    assert stages["生成视频"] == "待处理"
    assert [r["title"] for r in summary["recent"]] == ["竹林夜行", "金色样片"]
    empty = summarize_workflows([])
    assert empty["latest"] is None
    assert empty["recent"] == []
    assert all(s["status"] == "待处理" for s in empty["pipeline"])


def test_dashboard_source_has_no_hardcoded_fake_numbers():
    source = _read("ui/pages/production_dashboard.py")
    for fake in ("12.8万次", "8.6万次", "6.2万次", "5.4万次", "3.7万次",
                 "进行中 65%", "仙侠修仙项目", "都市异能故事", "星际冒险", "古风言情"):
        assert fake not in source, fake
    assert "summarize_workflows" in source


def test_deprecated_engines_never_report_done():
    # ai_scheduler: guard returns False, never touches the record.
    sys.path.insert(0, REPO)
    import core.ai_scheduler as scheduler_module

    scheduler = scheduler_module.AIScheduler()
    scheduler.create_task("某项目", "001")
    assert scheduler.run() is False
    assert scheduler.status == "已废弃"
    assert len(scheduler.tasks) == 1  # not consumed, not completed

    # pipeline_manager: guard marks deprecated, never "完成".
    import core.v30.pipeline_manager as pm_module

    with tempfile.TemporaryDirectory() as tmp:
        manager = pm_module.PipelineManager()
        manager.file = os.path.join(tmp, "pipeline.json")
        manager.tasks = {}
        manager.create("某项目", "001")
        assert manager.run("某项目", "001") is False
        assert all(v == "已废弃" for v in manager.tasks["某项目_001"].values())
        assert "完成" not in str(manager.tasks)

    # batch_engine: guard consumes nothing and marks nothing done.
    import core.batch_engine as batch_module

    with tempfile.TemporaryDirectory() as tmp:
        engine = batch_module.BatchEngine()
        engine.status_file = os.path.join(tmp, "batch_status.json")
        engine.data = {}
        engine.queue = []
        engine.create_batch("某项目", "1", "2")
        assert len(engine.queue) == 2
        assert engine.run_all() is False
        assert len(engine.queue) == 2
        assert engine.run_one() is False
        assert "完成" not in str(engine.data)


def test_deprecated_pages_never_call_fake_engines():
    ai_source = _read("ui/pages/ai_center.py")
    assert "ai_scheduler.run()" not in ai_source
    assert "已废弃" in ai_source
    pipeline_source = _read("ui/pages/v30/pipeline_center.py")
    assert "pipeline_manager.run(" not in pipeline_source
    assert "已废弃" in pipeline_source
    batch_source = _read("ui/pages/batch_center.py")
    assert "batch_engine.run_all()" not in batch_source
    assert "已废弃" in batch_source


def test_publish_packages_lists_real_zips_only():
    from core.publish_packages import list_real_packages, package_contents

    with tempfile.TemporaryDirectory() as tmp:
        packages_dir = os.path.join(tmp, "packages")
        ep_dir = os.path.join(tmp, "output")
        os.makedirs(packages_dir)
        os.makedirs(ep_dir)
        wf_zip = os.path.join(packages_dir, "WF-ABC_episode_package.zip")
        with zipfile.ZipFile(wf_zip, "w") as z:
            z.writestr("final.mp4", b"video")
            z.writestr("manifest.json", b"{}")
        ep_zip = os.path.join(ep_dir, "EP-123_publish.zip")
        with zipfile.ZipFile(ep_zip, "w") as z:
            z.writestr("episode.mp4", b"video")
        # Noise files must be ignored, not listed as packages.
        open(os.path.join(packages_dir, "notes.txt"), "w").write("x")
        open(os.path.join(ep_dir, "publish.json"), "w").write("{}")
        found = list_real_packages(packages_dir, ep_dir)
        assert [f["name"] for f in found] == [
            "WF-ABC_episode_package.zip",
            "EP-123_publish.zip",
        ] or sorted(f["name"] for f in found) == sorted(
            ["WF-ABC_episode_package.zip", "EP-123_publish.zip"]
        )
        assert all(f["size_bytes"] > 0 for f in found)
        assert package_contents(wf_zip) == ["final.mp4", "manifest.json"]
        assert list_real_packages(os.path.join(tmp, "missing"), os.path.join(tmp, "missing2")) == []
    publish_source = _read("ui/pages/publish_center.py")
    assert "publish_manager" not in publish_source
    assert "list_real_packages" in publish_source


def test_autopilot_pack_resolves_final_video_before_build():
    from core.autopilot_pack import resolve_and_build

    calls = []

    def fake_build(episode_id, final_video):
        calls.append((episode_id, final_video))
        return {"success": True, "package": "x.zip"}

    # No EP record at all: explicit guidance, build never called.
    def missing_loader(episode_id):
        raise FileNotFoundError("no such file")

    result = resolve_and_build("EP-NONE", load_pipeline=missing_loader, build=fake_build)
    assert result["success"] is False
    assert "不存在" in result["message"]
    assert calls == []

    # EP record without a final video: explicit guidance, build never called.
    result = resolve_and_build(
        "EP-1", load_pipeline=lambda eid: {"final_video": None}, build=fake_build
    )
    assert result["success"] is False
    assert "最终视频尚未生成" in result["message"]
    assert calls == []

    # EP record with a real final video: build is called WITH it.
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"video")
        video_path = tmp.name
    try:
        result = resolve_and_build(
            "EP-1",
            load_pipeline=lambda eid: {"final_video": video_path},
            build=fake_build,
        )
        assert result["success"] is True
        assert calls == [("EP-1", video_path)]
    finally:
        os.unlink(video_path)

    autopilot_source = _read("ui/pages/autopilot_center.py")
    assert "resolve_and_build" in autopilot_source
    assert "publish_pack_engine.build(self.ep" not in autopilot_source


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001 - manual runner reports all
            failed += 1
            print(f"FAIL {name}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
