from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QMessageBox
)

from PySide6.QtCore import QTimer

from core.data_center import app_data

from core.logger import log

import datetime



class ScriptCenter(QWidget):


    def __init__(self):

        super().__init__()


        layout = QVBoxLayout()


        self.info = QLabel(
            "当前项目：未选择"
        )

        layout.addWidget(
            self.info
        )


        self.editor = QTextEdit()

        self.editor.setPlaceholderText(
            "请输入剧本内容..."
        )

        layout.addWidget(
            self.editor
        )


        self.save_button = QPushButton(
            "💾 保存剧本"
        )

        self.save_button.clicked.connect(
            self.save_script
        )

        layout.addWidget(
            self.save_button
        )


        self.status = QLabel(
            "状态：等待操作"
        )

        layout.addWidget(
            self.status
        )


        self.setLayout(
            layout
        )


        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.update_project
        )

        self.timer.start(
            1000
        )


        self.update_project()



    def update_project(self):


        if app_data.project:


            self.info.setText(

                "当前项目："

                +

                app_data.project

                +

                " 第"

                +

                app_data.episode

                +

                "集"

            )


        else:

            self.info.setText(
                "当前项目：未选择"
            )



    def save_script(self):


        path = app_data.get_script_file()


        if not path:


            QMessageBox.warning(

                self,

                "提示",

                "请先在项目中心选择项目"

            )

            return



        content = self.editor.toPlainText()



        with open(

            path,

            "w",

            encoding="utf-8"

        ) as f:

            f.write(
                content
            )



        log(
            "保存剧本: "
            +
            path
        )


        now = datetime.datetime.now().strftime(
            "%H:%M:%S"
        )


        self.status.setText(

            "状态：保存成功 ✅\n"

            +

            path

            +

            "\n时间："

            +

            now

        )


        QMessageBox.information(

            self,

            "保存完成",

            "剧本保存成功\n\n"

            +

            path

        )

