
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QListWidget


class MaterialPage(QWidget):

    def __init__(self):

        super().__init__()

        layout=QVBoxLayout()

        title=QLabel(
            "🖼 素材中心"
        )

        title.setStyleSheet(
            "font-size:28px;font-weight:bold;"
        )


        self.list=QListWidget()


        btn=QPushButton(
            "上传图片"
        )


        layout.addWidget(title)

        layout.addWidget(self.list)

        layout.addWidget(btn)


        self.setLayout(layout)
