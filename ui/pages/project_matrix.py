from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QLineEdit
)


from core.project_manager import project_manager



class ProjectMatrix(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):


        layout = QVBoxLayout()



        title = QLabel(
            "📚 仙剧工坊 V25.2 项目矩阵中心"
        )


        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
        )


        layout.addWidget(
            title
        )



        self.project_input = QLineEdit()


        self.project_input.setPlaceholderText(
            "输入新项目名称"
        )


        layout.addWidget(
            self.project_input
        )



        self.episode_input = QLineEdit()


        self.episode_input.setPlaceholderText(
            "输入集数，例如 001"
        )


        layout.addWidget(
            self.episode_input
        )



        self.list = QListWidget()


        layout.addWidget(
            self.list
        )



        self.info = QLabel(
            "项目状态：等待"
        )


        layout.addWidget(
            self.info
        )



        create = QPushButton(
            "➕ 新建项目"
        )


        create.clicked.connect(
            self.create_project
        )


        layout.addWidget(
            create
        )



        add = QPushButton(
            "📺 添加集数"
        )


        add.clicked.connect(
            self.add_episode
        )


        layout.addWidget(
            add
        )



        refresh = QPushButton(
            "🔄 刷新项目列表"
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


        self.refresh()



    def refresh(self):


        self.list.clear()


        data = project_manager.get_projects()



        for name,item in data.items():


            self.list.addItem(

                "📚 "

                +

                name

                +

                "  状态："

                +

                item["status"]

                +

                "  集数："

                +

                str(
                    len(
                        item["episodes"]
                    )
                )

            )



        self.info.setText(

            "项目总数："

            +

            str(
                project_manager.get_project_count()
            )

        )



    def create_project(self):


        name = self.project_input.text()



        if name:


            project_manager.create_project(
                name
            )


            self.refresh()



    def add_episode(self):


        project = self.project_input.text()


        episode = self.episode_input.text()



        if project and episode:


            project_manager.add_episode(

                project,

                episode

            )


            self.refresh()

