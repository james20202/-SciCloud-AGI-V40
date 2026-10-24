import os
import time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
from ui.pages import director_plan as director_page_module

_APP = QApplication.instance() or QApplication([])


def test_plan_worker_runs_generation_off_ui_thread(monkeypatch):
    def slow_create_plan(idea, title, duration, ratio):
        time.sleep(0.15)
        return {
            "plan_id": "PLAN-ASYNC", "title": title or "测试",
            "intent": {"genre": "玄幻", "duration_seconds": duration, "hook": "钩子"},
            "story": {"logline": "梗概"}, "characters": [], "scenes": [],
            "shots": [{"id": "SHOT-1", "duration": duration, "visual_prompt": "画面"}],
            "tasks": [], "generation": {"mode": "deterministic_fallback", "message": "test"}
        }
    monkeypatch.setattr(director_page_module.director_plan_engine, "create_plan", slow_create_plan)
    page = director_page_module.DirectorPlanPage("测试创意")
    loop = QEventLoop()
    page.worker = None
    page.generate()
    assert page.generate_btn.isEnabled() is False
    assert page.worker is not None and page.worker.isRunning()
    page.worker.finished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    assert page.plan is not None
    assert page.generate_btn.isEnabled() is True
    assert page.queue_btn.isEnabled() is True
    page.close()
