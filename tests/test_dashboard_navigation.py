from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_emits_creation_request_instead_of_creating_fixed_task():
    source = (ROOT / "ui/pages/production_dashboard.py").read_text(encoding="utf-8")
    assert "create_requested = Signal(str)" in source
    assert "self.create_requested.emit(idea)" in source
    assert "ai_scheduler.create_task('V40创作项目','001')" not in source


def test_dashboard_shortcuts_have_real_routes():
    source = (ROOT / "ui/pages/production_dashboard.py").read_text(encoding="utf-8")
    for route in ("'分镜'", "'人物场景'", "'一键成片'", "'项目'"):
        assert route in source
    assert "self.navigate_requested.emit(target)" in source


def test_main_window_connects_dashboard_actions():
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    assert "dashboard.create_requested.connect(self.open_creation_with_idea)" in source
    assert "dashboard.navigate_requested.connect(self.select)" in source
    assert "def open_creation_with_idea(self, idea):" in source
