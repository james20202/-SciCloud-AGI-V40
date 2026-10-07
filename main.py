import sys

from PySide6.QtWidgets import QApplication


from ui.theme import THEME



app = QApplication(sys.argv)


app.setStyleSheet(
    THEME
)


from ui.main_window import MainWindow



window = MainWindow()

window.show()


sys.exit(
    app.exec()
)

