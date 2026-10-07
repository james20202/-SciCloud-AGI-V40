
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel


class VoicePage(QWidget):

    def __init__(self):

        super().__init__()

        layout=QVBoxLayout()

        layout.addWidget(
            QLabel("🎙 配音中心")
        )


        self.setLayout(layout)
