

from PySide6.QtWidgets import QWidget,QVBoxLayout,QListWidget



class QueuePage(QWidget):


    def __init__(self):

        super().__init__()


        layout=QVBoxLayout()


        self.list=QListWidget()


        self.list.addItem(
            "等待任务..."
        )


        layout.addWidget(
            self.list
        )


        self.setLayout(
            layout
        )

