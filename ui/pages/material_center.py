from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget
)



class MaterialCenter(QWidget):


    def __init__(self):

        super().__init__()


        main = QVBoxLayout()


        title = QLabel(
            "🖼 素材中心 V13.0"
        )


        title.setStyleSheet(
            "font-size:24px;font-weight:bold;"
        )


        main.addWidget(
            title
        )



        self.materials = QListWidget()


        self.materials.addItem(
            "🧑 人物素材"
        )

        self.materials.addItem(
            "🏔 场景素材"
        )

        self.materials.addItem(
            "⚔ 道具素材"
        )

        self.materials.addItem(
            "🎬 视频素材"
        )


        main.addWidget(
            self.materials
        )



        refresh = QPushButton(
            "🔄 刷新素材"
        )


        main.addWidget(
            refresh
        )



        open_btn = QPushButton(
            "📂 打开素材目录"
        )


        main.addWidget(
            open_btn
        )



        self.setLayout(
            main
        )

