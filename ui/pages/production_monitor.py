from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton
)


from core.production_record import record



class ProductionMonitor(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):


        layout=QVBoxLayout()



        title=QLabel(
            "📊 生产监控中心 V18.0"
        )


        title.setStyleSheet(
            "font-size:24px;font-weight:bold;"
        )


        layout.addWidget(
            title
        )



        self.list=QListWidget()


        layout.addWidget(
            self.list
        )



        self.info=QLabel(
            "统计："
        )


        layout.addWidget(
            self.info
        )



        refresh=QPushButton(
            "🔄 刷新状态"
        )


        refresh.clicked.connect(
            self.refresh
        )


        layout.addWidget(
            refresh
        )



        self.setLayout(
            layout
        )


        self.refresh()



    def refresh(self):


        self.list.clear()



        done=0

        wait=0

        running=0

        fail=0



        for ep,status in record.data.items():


            self.list.addItem(

                "第"

                +

                ep

                +

                "集："

                +

                status

            )



            if status=="完成":

                done+=1


            elif status=="生产中":

                running+=1


            elif status=="失败":

                fail+=1


            else:

                wait+=1



        self.info.setText(

            "完成："

            +

            str(done)

            +

            "  生产中："

            +

            str(running)

            +

            "  等待："

            +

            str(wait)

            +

            "  失败："

            +

            str(fail)

        )

