from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QFileDialog
)

import os
import subprocess



class VideoCenter(QWidget):


    def __init__(self):

        super().__init__()

        self.video_path = "output/video"

        self.init_ui()



    def init_ui(self):

        layout = QVBoxLayout()



        title = QLabel(
            "🎬 仙剧工坊 V20.0 成片管理中心"
        )

        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
        )

        layout.addWidget(title)



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
            "🔄 刷新成片列表"
        )

        refresh.clicked.connect(
            self.refresh
        )

        layout.addWidget(
            refresh
        )



        preview = QPushButton(
            "▶ 预览视频"
        )

        preview.clicked.connect(
            self.preview
        )

        layout.addWidget(
            preview
        )



        open_dir = QPushButton(
            "📂 打开视频目录"
        )

        open_dir.clicked.connect(
            self.open_dir
        )

        layout.addWidget(
            open_dir
        )



        export = QPushButton(
            "📦 导出成片"
        )

        export.clicked.connect(
            self.export_video
        )

        layout.addWidget(
            export
        )



        self.setLayout(
            layout
        )


        self.refresh()



    def refresh(self):

        self.list.clear()



        if not os.path.exists(
            self.video_path
        ):

            self.info.setText(
                "状态：没有视频目录"
            )

            return



        videos = os.listdir(
            self.video_path
        )


        count = 0


        for video in videos:


            if video.endswith(
                ".mp4"
            ):


                self.list.addItem(

                    "🎬 "

                    +

                    video

                )

                count += 1



        self.info.setText(

            "成片数量："

            +

            str(count)

            +

            " 个"

        )



    def get_current_video(self):


        item = self.list.currentItem()


        if not item:

            return None



        name = item.text().replace(
            "🎬 ",
            ""
        )


        return os.path.join(

            self.video_path,

            name

        )



    def preview(self):


        video = self.get_current_video()


        if video and os.path.exists(video):


            subprocess.Popen(
                [
                    "open",
                    video
                ]
            )



    def open_dir(self):


        if os.path.exists(
            self.video_path
        ):

            subprocess.Popen(
                [
                    "open",
                    self.video_path
                ]
            )



    def export_video(self):


        video = self.get_current_video()


        if not video:

            self.info.setText(
                "请选择视频"
            )

            return



        target = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录"
        )


        if target:


            subprocess.Popen(
                [
                    "cp",
                    video,
                    target
                ]
            )


            self.info.setText(
                "导出完成"
            )

