"""AI 调度中心（已废弃）。

历史问题：旧版 ai_pipeline.run() 只写日志、不生成任何内容，
却返回 True，页面随即显示“状态：AI完成 ✅”——这是假完成。
本页不再调用旧版调度，也不再报完成：两个操作按钮已禁用，
只保留一条明确指引，告诉用户去工作流页走真实生产链。
ai_scheduler 本身也已在引擎层设防（见 core/ai_scheduler.py），
即使其他代码误调 run() 也不会再写出“完成”状态。
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
    "已废弃：旧版 AI 调度不生成任何内容，不再执行。"
    "请到工作流页创建导演计划并用一键出片生产真实成片。"
)


class AICenter(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("🧠 仙剧工坊 V22.2 AI调度中心")
        title.setStyleSheet("font-size:26px;font-weight:bold;")
        layout.addWidget(title)
        note = QLabel(DEPRECATED_TEXT)
        note.setWordWrap(True)
        layout.addWidget(note)
        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("输入项目名称，例如：青云剑宗")
        self.project_input.setEnabled(False)
        layout.addWidget(self.project_input)
        self.episode_input = QLineEdit()
        self.episode_input.setPlaceholderText("输入集数，例如：001")
        self.episode_input.setEnabled(False)
        layout.addWidget(self.episode_input)
        self.queue = QListWidget()
        layout.addWidget(self.queue)
        self.status = QLabel("状态：" + DEPRECATED_TEXT)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        create = QPushButton("➕ 创建AI任务（已废弃）")
        create.setEnabled(False)
        create.clicked.connect(self.create_task)
        layout.addWidget(create)
        run = QPushButton("🚀 启动AI调度（已废弃）")
        run.setEnabled(False)
        run.clicked.connect(self.run_ai)
        layout.addWidget(run)
        refresh = QPushButton("🔄 刷新日志")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        self.setLayout(layout)

    def create_task(self):
        # Guard: even a programmatic click must not queue a fake task.
        self.status.setText("状态：" + DEPRECATED_TEXT)

    def run_ai(self):
        # Guard: never invoke the old scheduler and never report "AI完成".
        self.status.setText("状态：" + DEPRECATED_TEXT)

    def refresh(self):
        # Do not surface ai_scheduler.status: a stale "完成" from an
        # old session would be the same fake completion again.
        self.status.setText("状态：" + DEPRECATED_TEXT)
