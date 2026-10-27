"""AI 批量生产中心（已废弃）。

历史问题：旧版批量引擎逐个走旧版调度，
而旧版 ai_pipeline 只写日志不生成，却逐集标“完成”——这是
假完成。本页不再调用旧版批量引擎：两个操作按钮已禁用，
只保留一条明确指引。引擎层也已设防（见 core/batch_engine.py
和 core/ai_scheduler.py）：run_all/run_one 不再执行、不再标完成。
批量生产如需恢复，必须以工作流 WF 为单位批量跑真实一键出片，
那是另一次较大的改动，不在本 PR 假装完成。
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QLineEdit,
)

DEPRECATED_TEXT = (
    "已废弃：旧版批量生产不生成任何内容，不再执行。"
    "请到工作流页逐个用一键出片生产真实成片。"
)


class BatchCenter(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("🚀 仙剧工坊 V26.5 AI批量生产中心"))
        note = QLabel(DEPRECATED_TEXT)
        note.setWordWrap(True)
        layout.addWidget(note)
        self.project = QLineEdit()
        self.project.setPlaceholderText("项目名称")
        self.project.setEnabled(False)
        layout.addWidget(self.project)
        self.start = QLineEdit()
        self.start.setPlaceholderText("开始集数")
        self.start.setEnabled(False)
        layout.addWidget(self.start)
        self.end = QLineEdit()
        self.end.setPlaceholderText("结束集数")
        self.end.setEnabled(False)
        layout.addWidget(self.end)
        self.list = QListWidget()
        layout.addWidget(self.list)
        btn1 = QPushButton("📋 创建批量任务（已废弃）")
        btn1.setEnabled(False)
        btn1.clicked.connect(self.create)
        layout.addWidget(btn1)
        btn2 = QPushButton("🚀 开始全部生产（已废弃）")
        btn2.setEnabled(False)
        btn2.clicked.connect(self.run)
        layout.addWidget(btn2)
        self.setLayout(layout)

    def create(self):
        self.list.clear()
        self.list.addItem(DEPRECATED_TEXT)

    def run(self):
        # Guard: never invoke the old batch run and never mark done.
        self.list.clear()
        self.list.addItem(DEPRECATED_TEXT)
