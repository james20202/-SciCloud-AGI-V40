from PySide6.QtWidgets import QMessageBox



def success(parent, text):

    QMessageBox.information(
        parent,
        "成功",
        text
    )



def warning(parent, text):

    QMessageBox.warning(
        parent,
        "提示",
        text
    )

