from PySide6.QtWidgets import *

from core.batch_engine import batch_engine



class BatchCenter(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):

        layout=QVBoxLayout()


        layout.addWidget(
            QLabel(
                "🚀 仙剧工坊 V26.5 AI批量生产中心"
            )
        )


        self.project=QLineEdit()

        self.project.setPlaceholderText(
            "项目名称"
        )

        layout.addWidget(
            self.project
        )



        self.start=QLineEdit()

        self.start.setPlaceholderText(
            "开始集数"
        )

        layout.addWidget(
            self.start
        )



        self.end=QLineEdit()

        self.end.setPlaceholderText(
            "结束集数"
        )

        layout.addWidget(
            self.end
        )



        self.list=QListWidget()

        layout.addWidget(
            self.list
        )



        btn1=QPushButton(
            "📋 创建批量任务"
        )

        btn1.clicked.connect(
            self.create
        )

        layout.addWidget(btn1)



        btn2=QPushButton(
            "🚀 开始全部生产"
        )

        btn2.clicked.connect(
            self.run
        )

        layout.addWidget(btn2)



        self.setLayout(layout)



    def create(self):

        q=batch_engine.create_batch(

            self.project.text(),

            self.start.text(),

            self.end.text()

        )


        self.list.clear()


        for i in q:

            self.list.addItem(

                "⏳ 第"

                +

                i["episode"]

                +

                "集"

            )



    def run(self):

        batch_engine.run_all()

        self.list.clear()


        data=batch_engine.get_status()


        for p,eps in data.items():

            for e,s in eps.items():

                self.list.addItem(

                    p

                    +

                    " 第"

                    +

                    e

                    +

                    "集 "

                    +

                    s

                )

