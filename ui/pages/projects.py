from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton
)

import os


from ui.pages.create_project import CreateProjectDialog



BASE_PATH = "projects"



class ProjectsPage(QWidget):


    def __init__(self):

        super().__init__()


        self.create_ui()


        self.load_projects()



    def create_ui(self):


        layout = QVBoxLayout()



        title = QLabel(
            "📚 我的作品"
        )


        title.setStyleSheet(
            """
            font-size:28px;
            font-weight:bold;
            """
        )


        layout.addWidget(
            title
        )



        self.list = QListWidget()


        self.list.setMinimumHeight(
            400
        )


        layout.addWidget(
            self.list
        )



        self.create_btn = QPushButton(
            "🚀 新建作品"
        )


        self.create_btn.setMinimumHeight(
            50
        )


        self.create_btn.clicked.connect(
            self.open_create
        )


        layout.addWidget(
            self.create_btn
        )



        self.setLayout(
            layout
        )



    def load_projects(self):


        self.list.clear()



        if not os.path.exists(
            BASE_PATH
        ):

            return



        for name in os.listdir(
            BASE_PATH
        ):


            project_path = os.path.join(
                BASE_PATH,
                name
            )


            if os.path.isdir(
                project_path
            ):


                episodes = []


                for item in os.listdir(
                    project_path
                ):

                    if item.startswith(
                        "第"
                    ):

                        episodes.append(
                            item
                        )


                text = (
                    f"⚔ {name}"
                    "\n"
                    f"  集数：{len(episodes)}"
                )


                self.list.addItem(
                    text
                )




    def open_create(self):


        dialog = CreateProjectDialog()


        result = dialog.exec()



        if result:


            self.load_projects()

