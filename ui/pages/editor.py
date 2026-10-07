

from PySide6.QtWidgets import QWidget,QVBoxLayout,QTextEdit,QPushButton


class EditorPage(QWidget):


    def __init__(self):

        super().__init__()


        layout=QVBoxLayout()



        self.text=QTextEdit()



        save=QPushButton(

            "保存剧本"

        )



        layout.addWidget(
            self.text
        )


        layout.addWidget(
            save
        )


        self.setLayout(
            layout
        )

