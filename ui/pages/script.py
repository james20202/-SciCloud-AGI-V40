from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QLineEdit,
    QMessageBox
)

import os



class ScriptPage(QWidget):


    def __init__(self):

        super().__init__()

        self.create_ui()



    def create_ui(self):


        layout = QVBoxLayout()



        title = QLabel(
            "📝 剧本中心"
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



        self.project_input = QLineEdit()


        self.project_input.setPlaceholderText(
            "输入作品名称，例如：青云剑宗"
        )


        layout.addWidget(
            self.project_input
        )



        self.text = QTextEdit()


        self.text.setPlaceholderText(
            "请输入剧情内容..."
        )


        layout.addWidget(
            self.text
        )



        save_btn = QPushButton(
            "💾 保存剧本"
        )


        save_btn.setMinimumHeight(
            45
        )


        save_btn.clicked.connect(
            self.save_script
        )


        layout.addWidget(
            save_btn
        )


        self.status = QLabel(
            ""
        )


        layout.addWidget(
            self.status
        )



        self.setLayout(
            layout
        )




    def save_script(self):


        project = self.project_input.text().strip()


        content = self.text.toPlainText()



        if not project:


            QMessageBox.warning(
                self,
                "提示",
                "请输入作品名称"
            )

            return



        if not content:


            QMessageBox.warning(
                self,
                "提示",
                "请输入剧本内容"
            )

            return



        path = os.path.join(

            "projects",

            project,

            "第001集",

            "01_剧本"

        )


        os.makedirs(
            path,
            exist_ok=True
        )



        file_path = os.path.join(

            path,

            "剧本.txt"

        )



        with open(

            file_path,

            "w",

            encoding="utf-8"

        ) as f:


            f.write(
                content
            )



        self.status.setText(
            "✅ 保存成功：" + file_path
        )



        QMessageBox.information(

            self,

            "完成",

            "剧本保存成功"

        )

