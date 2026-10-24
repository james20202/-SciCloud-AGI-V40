import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from ui.pages.production_dashboard import ProductionDashboard

# Keep one QApplication alive for the complete pytest process. Recreating it
# per test can leave Qt's shared QObject in a deleted state at interpreter exit.
_APP = QApplication.instance() or QApplication([])


def test_dashboard_start_emits_user_idea():
    dashboard = ProductionDashboard()
    captured = []
    dashboard.create_requested.connect(captured.append)
    dashboard.idea.setPlainText("青云宗废柴弟子在天劫中觉醒")
    dashboard.start()
    assert captured == ["青云宗废柴弟子在天劫中觉醒"]
    dashboard.deleteLater()


def test_dashboard_quick_action_emits_route_and_context():
    dashboard = ProductionDashboard()
    routes, quick = [], []
    dashboard.navigate_requested.connect(routes.append)
    dashboard.quick_requested.connect(lambda key, idea: quick.append((key, idea)))
    dashboard.idea.setPlainText("道士夜闯凶宅")
    dashboard.quick("分镜设计")
    assert routes == ["分镜"]
    assert quick == [("分镜设计", "道士夜闯凶宅")]
    dashboard.deleteLater()


def test_dashboard_quick_action_supplies_default_idea():
    dashboard = ProductionDashboard()
    captured = []
    dashboard.create_requested.connect(captured.append)
    dashboard.quick("生成剧本")
    assert len(captured) == 1
    assert "玄幻修仙" in captured[0]
    dashboard.deleteLater()
