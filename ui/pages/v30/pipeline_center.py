"""V30 AI 自动生产流水线（已废弃）。

历史问题：旧版流水线管理器对每个步骤 time.sleep(0.2)
然后直接标“完成”，没有任何生成、调用或校验——这是假完成。
本页不再调用旧版流水线：两个操作按钮已禁用，只保留一条
明确指引，告诉用户去工作流页走真实生产链。引擎层也已设防
（见 core/v30/pipeline_manager.py）：run() 不再标完成。
旧版记录仍可查看，但会明确标注为旧版记录，不代表真实生产。
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
)

from core.v30.pipeline_manager import pipeline_manager

DEPRECATED_TEXT = (
    "已废弃：旧版流水线不生成任何内容，不再执行。"
    "请到工作流页创建导演计划并用一键出片生产真实成片。"
)


class PipelineCenter(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("🚀 V30 AI自动生产流水线")
        title.setStyleSheet("font-size:26px;font-weight:bold;")
        layout.addWidget(title)
        note = QLabel(DEPRECATED_TEXT)
        note.setWordWrap(True)
        layout.addWidget(note)
        self.project = QLineEdit()
        self.project.setPlaceholderText("项目名称")
        self.project.setEnabled(False)
        layout.addWidget(self.project)
        self.episode = QLineEdit()
        self.episode.setPlaceholderText("集数，例如001")
        self.episode.setEnabled(False)
        layout.addWidget(self.episode)
        create = QPushButton("📋 创建生产任务（已废弃）")
        create.setEnabled(False)
        create.clicked.connect(self.create_task)
        layout.addWidget(create)
        run = QPushButton("🚀 执行AI流水线（已废弃）")
        run.setEnabled(False)
        run.clicked.connect(self.run_task)
        layout.addWidget(run)
        self.output = QTextEdit()
        layout.addWidget(self.output)
        self.setLayout(layout)

    def create_task(self):
        self.output.setPlainText(DEPRECATED_TEXT)

    def run_task(self):
        # Guard: never invoke the old pipeline run and never mark done.
        self.output.setPlainText(DEPRECATED_TEXT)

    def show_status(self):
        self.output.clear()
        self.output.append(DEPRECATED_TEXT)
        self.output.append("旧版记录（仅供查看，不代表真实生产）：")
        self.output.append(str(pipeline_manager.get_status()))
