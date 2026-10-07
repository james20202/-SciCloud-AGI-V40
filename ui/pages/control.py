

from PySide6.QtWidgets import (

    QWidget,

    QVBoxLayout,

    QLabel,

    QPushButton,

    QComboBox

)

import os



class ControlPage(QWidget):


    def __init__(self):

        super().__init__()


        layout = QVBoxLayout()



        title = QLabel(

            "⚔ 项目控制中心"

        )


        title.setStyleSheet(

            """

            font-size:28px;

            font-weight:bold;

            """

        )


        layout.addWidget(title)



        self.project_box = QComboBox()


        self.episode_box = QComboBox()



        self.load_projects()



        layout.addWidget(

            QLabel("当前作品")

        )


        layout.addWidget(

            self.project_box

        )



        layout.addWidget(

            QLabel("当前集数")

        )


        layout.addWidget(

            self.episode_box

        )




        self.progress = QLabel(

            """

            制作进度

            

            📝 剧本   100%

            🎞 分镜   0%

            🖼 素材   0%

            🎙 配音   0%

            🎬 视频   0%

            """

        )


        layout.addWidget(

            self.progress

        )



        self.setLayout(

            layout

        )





    def load_projects(self):


        base="projects"


        if not os.path.exists(base):

            return



        for p in os.listdir(base):

            self.project_box.addItem(p)

