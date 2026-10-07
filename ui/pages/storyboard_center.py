from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QTextEdit
)



class StoryboardCenter(QWidget):


    def __init__(self):

        super().__init__()


        main = QVBoxLayout()



        title = QLabel(
            "🎞 分镜中心 V13.0"
        )

        title.setStyleSheet(
            "font-size:24px;font-weight:bold;"
        )

        main.addWidget(
            title
        )


        self.shots = QListWidget()


        self.shots.addItem(
            "镜头01 青云山门"
        )

        self.shots.addItem(
            "镜头02 拜师"
        )


        main.addWidget(
            self.shots
        )



        self.detail = QTextEdit()


        self.detail.setPlaceholderText(
            """
镜头：

场景：

人物：

动作：

AI提示词：
"""
        )


        main.addWidget(
            self.detail
        )



        ai = QPushButton(
            "🧠 AI生成分镜"
        )


        main.addWidget(
            ai
        )



        image = QPushButton(
            "🖼 生成图片任务"
        )


        main.addWidget(
            image
        )


        self.setLayout(
            main
        )

