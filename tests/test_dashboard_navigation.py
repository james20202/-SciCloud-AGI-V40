import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from ui.pages.production_dashboard import ProductionDashboard


def test_dashboard_start_emits_idea():
    app = QApplication.instance() or QApplication([])
    dashboard = ProductionDashboard()
    captured = []
    dashboard.create_requested.connect(captured.append)
    dashboard.idea.setPlainText("一个修仙少年在天劫中觉醒")
    dashboard.start()
    assert captured == ["一个修仙少年在天劫中觉醒"]


def test_dashboard_quick_actions_and_project_navigation_emit_routes():
    app = QApplication.instance() or QApplication([])
    dashboard = ProductionDashboard()
    routes = []
    dashboard.navigate_requested.connect(routes.append)
    dashboard.quick("分镜设计")
    dashboard.quick("角色设定")
    dashboard.quick("场景生成")
    dashboard.quick("一键生成视频")
    dashboard.goto_project()
    assert routes == ["分镜", "人物场景", "人物场景", "一键成片", "项目"]


def test_dashboard_empty_start_does_not_create_task():
    app = QApplication.instance() or QApplication([])
    dashboard = ProductionDashboard()
    captured = []
    dashboard.create_requested.connect(captured.append)
    dashboard.idea.clear()
    dashboard.start()
    assert captured == []
