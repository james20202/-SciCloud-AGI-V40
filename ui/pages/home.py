from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar
)

from PySide6.QtCore import QTimer


from core.project_context import context

from core.ai_pipeline import ai_pipeline

from core.batch_manager import batch_manager

from core.task_manager import tasks

from core.logger_center import logger



class HomePage(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):


        layout = QVBoxLayout()



        title = QLabel(
            "⚔ 仙剧工坊 V16.5 批量生产驾驶舱"
        )

        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
        )


        layout.addWidget(title)



        self.project = QLabel(
            "当前项目：未选择"
        )


        layout.addWidget(
            self.project
        )



        self.progress = QProgressBar()


        layout.addWidget(
            self.progress
        )



        self.ai_button = QPushButton(
            "🧠 AI生成当前集"
        )


        self.ai_button.clicked.connect(
            self.ai_make
        )


        layout.addWidget(
            self.ai_button
        )



        self.batch_button = QPushButton(
            "📺 批量生成001-010集"
        )


        self.batch_button.clicked.connect(
            self.batch_make
        )


        layout.addWidget(
            self.batch_button
        )



        self.status = QLabel(
            "状态：等待"
        )


        layout.addWidget(
            self.status
        )



        self.logs = QTextEdit()


        self.logs.setReadOnly(
            True
        )


        layout.addWidget(
            self.logs
        )



        self.timer = QTimer(
            self
        )


        self.timer.timeout.connect(
            self.refresh
        )


        self.timer.start(
            1000
        )



        self.setLayout(
            layout
        )



    def ai_make(self):


        self.status.setText(
            "状态：AI生产中"
        )


        ai_pipeline.run()



        self.status.setText(
            "状态：完成 ✅"
        )



    def batch_make(self):


        self.status.setText(
            "状态：批量生产启动"
        )


        batch_manager.create_queue(

            "青云剑宗",

            1,

            10

        )


        while batch_manager.run_next():

            pass



        self.status.setText(
            "状态：批量完成 ✅"
        )



    def refresh(self):


        self.logs.setText(
            logger.get()
        )


        self.progress.setValue(
            tasks.progress()
        )

