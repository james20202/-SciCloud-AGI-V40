
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTextEdit,QPushButton


class StoryboardPage(QWidget):

    def __init__(self):

        super().__init__()

        layout=QVBoxLayout()


        title=QLabel(
            "🎞 分镜中心"
        )


        self.text=QTextEdit()


        btn=QPushButton(
            "保存分镜"
        )


        layout.addWidget(title)

        layout.addWidget(self.text)

        layout.addWidget(btn)


        self.setLayout(layout)
