from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton
)


from core.publish_manager import publish_manager



class PublishCenter(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):


        layout = QVBoxLayout()



        title = QLabel(
            "📤 仙剧工坊 V21.2 发布中心"
        )


        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
        )


        layout.addWidget(
            title
        )



        self.list = QListWidget()


        layout.addWidget(
            self.list
        )



        self.info = QLabel(
            "状态：等待"
        )


        layout.addWidget(
            self.info
        )



        refresh = QPushButton(
            "🔄 刷新发布列表"
        )


        refresh.clicked.connect(
            self.refresh
        )


        layout.addWidget(
            refresh
        )



        check = QPushButton(
            "📋 发布检查"
        )


        check.clicked.connect(
            self.check
        )


        layout.addWidget(
            check
        )



        finish = QPushButton(
            "✅ 标记发布完成"
        )


        finish.clicked.connect(
            self.finish
        )


        layout.addWidget(
            finish
        )



        self.setLayout(
            layout
        )


        self.refresh()



    def refresh(self):


        self.list.clear()



        data = publish_manager.get_all()



        for ep,item in data.items():


            self.list.addItem(

                "第"

                +

                ep

                +

                "集  "

                +

                item["status"]

            )



        self.info.setText(

            "发布任务："

            +

            str(len(data))

            +

            " 个"

        )



    def get_episode(self):


        item=self.list.currentItem()



        if not item:

            return None



        text=item.text()


        return text[1:4]



    def check(self):


        ep=self.get_episode()



        if ep:


            data=publish_manager.data[ep]


            self.info.setText(

                "视频："

                +

                data["video"]

                +

                " 字幕："

                +

                data["subtitle"]

                +

                " 封面："

                +

                data["cover"]

            )



    def finish(self):


        ep=self.get_episode()



        if ep:


            publish_manager.update(

                ep,

                "status",

                "已发布"

            )


            self.refresh()

