from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QFrame
)


class ProjectCard(QFrame):


    def __init__(
        self,
        name
    ):

        super().__init__()


        layout = QVBoxLayout()


        title = QLabel(
            "⚔ " + name
        )


        status = QLabel(
            "第001集\n"
            "📝剧本 ✅\n"
            "🎞分镜 ⏳\n"
            "🖼素材 ⬜\n"
            "🎬视频 ⬜"
        )


        btn = QPushButton(
            "进入项目"
        )


        layout.addWidget(
            title
        )

        layout.addWidget(
            status
        )

        layout.addWidget(
            btn
        )


        self.setLayout(
            layout
        )



class ProjectCenter(QWidget):


    def __init__(self):

        super().__init__()


        main = QVBoxLayout()


        title = QLabel(
            "📚 项目中心 V12.5"
        )


        title.setStyleSheet(
            "font-size:24px;font-weight:bold;"
        )


        main.addWidget(
            title
        )



        cards = QHBoxLayout()


        cards.addWidget(

            ProjectCard(
                "青云剑宗"
            )

        )


        cards.addWidget(

            ProjectCard(
                "新作品"
            )

        )


        main.addLayout(
            cards
        )



        create = QPushButton(
            "➕ 创建新项目"
        )


        main.addWidget(
            create
        )


        self.setLayout(
            main
        )

