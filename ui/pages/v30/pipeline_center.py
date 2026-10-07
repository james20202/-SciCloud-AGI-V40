
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit
)


from core.v30.pipeline_manager import pipeline_manager



class PipelineCenter(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):

        layout = QVBoxLayout()



        title = QLabel(
            "🚀 V30 AI自动生产流水线"
        )

        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
        )


        layout.addWidget(title)



        self.project = QLineEdit()

        self.project.setPlaceholderText(
            "项目名称"
        )

        layout.addWidget(
            self.project
        )



        self.episode = QLineEdit()

        self.episode.setPlaceholderText(
            "集数，例如001"
        )

        layout.addWidget(
            self.episode
        )



        create = QPushButton(
            "📋 创建生产任务"
        )


        create.clicked.connect(
            self.create_task
        )


        layout.addWidget(
            create
        )



        run = QPushButton(
            "🚀 执行AI流水线"
        )


        run.clicked.connect(
            self.run_task
        )


        layout.addWidget(
            run
        )



        self.output = QTextEdit()


        layout.addWidget(
            self.output
        )


        self.setLayout(
            layout
        )



    def create_task(self):


        pipeline_manager.create(

            self.project.text(),

            self.episode.text()

        )


        self.show_status()



    def run_task(self):


        pipeline_manager.run(

            self.project.text(),

            self.episode.text()

        )


        self.show_status()



    def show_status(self):


        self.output.clear()


        data = pipeline_manager.get_status()


        self.output.append(

            str(data)

        )

