

from PySide6.QtWidgets import (

    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QProgressBar

)



class DashboardPage(QWidget):


    def __init__(self):

        super().__init__()


        layout=QVBoxLayout()



        title=QLabel(

            "⚔ 仙剧工坊 V4.0 生产驾驶舱"

        )


        title.setStyleSheet(

            """

            font-size:28px;

            font-weight:bold;

            """

        )


        layout.addWidget(
            title
        )



        info=QLabel(

            """

当前项目：

青云剑宗



当前集数：

第001集

            """

        )


        layout.addWidget(
            info
        )





        layout.addWidget(

            QLabel(
                "制作进度"
            )

        )



        steps=[

            ("📝 剧本",100),

            ("🎞 分镜",40),

            ("🖼 素材",20),

            ("🎙 配音",0),

            ("🎬 视频",0)

        ]



        for name,value in steps:


            row=QHBoxLayout()


            label=QLabel(
                name
            )


            bar=QProgressBar()


            bar.setValue(
                value
            )


            row.addWidget(
                label
            )


            row.addWidget(
                bar
            )


            layout.addLayout(
                row
            )





        layout.addWidget(

            QLabel(
                "快捷操作"
            )

        )



        buttons=[

            "📚 打开作品",

            "📝 编辑剧本",

            "🖼 管理素材",

            "🎬 视频生成"

        ]



        for b in buttons:


            btn=QPushButton(
                b
            )


            layout.addWidget(
                btn
            )




        layout.addStretch()


        self.setLayout(
            layout
        )

