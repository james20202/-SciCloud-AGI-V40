from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton
)

from core.project import create_project



class CreateProjectDialog(QDialog):


    def __init__(self):

        super().__init__()


        self.setWindowTitle(
            "创建新作品"
        )


        self.resize(
            400,
            300
        )


        layout = QVBoxLayout()


        title = QLabel(
            "⚔ 创建仙剧项目"
        )


        layout.addWidget(
            title
        )


        self.name_input = QLineEdit()

        self.name_input.setPlaceholderText(
            "输入作品名称"
        )


        layout.addWidget(
            self.name_input
        )



        self.episode_input = QLineEdit()

        self.episode_input.setText(
            "001"
        )


        layout.addWidget(
            self.episode_input
        )



        btn = QPushButton(
            "🚀 创建"
        )


        btn.clicked.connect(
            self.create
        )


        layout.addWidget(
            btn
        )


        self.setLayout(
            layout
        )



    def create(self):


        name = self.name_input.text()


        episode = self.episode_input.text()



        if name:


            create_project(
                name,
                episode
            )


            self.accept()

