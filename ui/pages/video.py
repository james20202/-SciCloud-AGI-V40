
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel


class VideoPage(QWidget):

    def __init__(self):

        super().__init__()

        layout=QVBoxLayout()


        layout.addWidget(
            QLabel("🎬 视频中心")
        )


        self.setLayout(layout)
