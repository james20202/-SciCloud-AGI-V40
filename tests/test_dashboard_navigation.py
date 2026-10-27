from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_emits_creation_request_instead_of_creating_fixed_task():
    source = (ROOT / "ui/pages/production_dashboard.py").read_text(encoding="utf-8")
    assert "create_requested = Signal(str)" in source
    assert "self.create_requested.emit(idea)" in source
    assert "ai_scheduler.create_task('V40创作项目','001')" not in source


def test_dashboard_shortcuts_have_real_routes():
    source = (ROOT / "ui/pages/production_dashboard.py").read_text(encoding="utf-8")
    # Top-5 honesty fix: the dashboard's "current/recent project" links
    # used to point at the legacy project page, which lists nothing
    # from V40 workflows. They now point at the workflow page, where
    # the real current project lives.
    for route in ("'分镜'", "'人物场景'", "'一键成片'", "'工作流'"):
        assert route in source
    assert "self.navigate_requested.emit(target)" in source


def test_main_window_connects_dashboard_actions():
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    assert "dashboard.create_requested.connect(self.open_creation_with_idea)" in source
    assert "dashboard.navigate_requested.connect(self.select)" in source
    assert "def open_creation_with_idea(self, idea):" in source
