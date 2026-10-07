from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QLineEdit
)


from core.ai_scheduler import ai_scheduler

from core.logger_center import logger



class AICenter(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):


        layout=QVBoxLayout()



        title=QLabel(
            "🧠 仙剧工坊 V22.2 AI调度中心"
        )


        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
        )


        layout.addWidget(
            title
        )



        self.project_input=QLineEdit()

        self.project_input.setPlaceholderText(
            "输入项目名称，例如：青云剑宗"
        )

        layout.addWidget(
            self.project_input
        )



        self.episode_input=QLineEdit()

        self.episode_input.setPlaceholderText(
            "输入集数，例如：001"
        )

        layout.addWidget(
            self.episode_input
        )



        self.queue=QListWidget()


        layout.addWidget(
            self.queue
        )



        self.status=QLabel(
            "状态：等待"
        )


        layout.addWidget(
            self.status
        )



        create=QPushButton(
            "➕ 创建AI任务"
        )


        create.clicked.connect(
            self.create_task
        )


        layout.addWidget(
            create
        )



        run=QPushButton(
            "🚀 启动AI调度"
        )


        run.clicked.connect(
            self.run_ai
        )


        layout.addWidget(
            run
        )



        refresh=QPushButton(
            "🔄 刷新日志"
        )


        refresh.clicked.connect(
            self.refresh
        )


        layout.addWidget(
            refresh
        )



        self.setLayout(
            layout
        )



    def create_task(self):


        project=self.project_input.text()

        episode=self.episode_input.text()



        if project and episode:


            ai_scheduler.create_task(

                project,

                episode

            )


            self.queue.addItem(

                project

                +

                " 第"

                +

                episode

                +

                "集"

            )



            self.status.setText(

                "状态：任务已创建"

            )



    def run_ai(self):


        result=ai_scheduler.run()



        if result:


            self.status.setText(

                "状态：AI完成 ✅"

            )

        else:


            self.status.setText(

                "状态：失败"

            )



    def refresh(self):


        self.status.setText(

            "状态："

            +

            ai_scheduler.status

        )


