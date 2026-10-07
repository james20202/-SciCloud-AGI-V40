from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QListWidget,
    QHBoxLayout
)


class CharacterCenter(QWidget):

    def __init__(self):

        super().__init__()

        main = QVBoxLayout()


        title = QLabel(
            "🧑 角色中心 V13.0"
        )

        title.setStyleSheet(
            "font-size:24px;font-weight:bold;"
        )

        main.addWidget(title)



        body = QHBoxLayout()


        self.list = QListWidget()

        self.list.addItem(
            "林凡"
        )

        self.list.addItem(
            "韩长老"
        )

        body.addWidget(
            self.list
        )



        self.info = QTextEdit()

        self.info.setPlaceholderText(
            """
角色名称：

年龄：

身份：

外貌：

服装：

固定AI提示词：
"""
        )

        body.addWidget(
            self.info
        )


        main.addLayout(
            body
        )



        save = QPushButton(
            "💾 保存角色设定"
        )

        main.addWidget(
            save
        )


        self.setLayout(
            main
        )

