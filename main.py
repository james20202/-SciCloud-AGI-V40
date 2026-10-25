import sys

from PySide6.QtWidgets import QApplication


from ui.theme import THEME



app = QApplication(sys.argv)


app.setStyleSheet(
    THEME
)


from ui.main_window import MainWindow
from core.production_bot import configure_production_bot


# Register the local Production Bot, but never launch production automatically on startup.
production_bot = configure_production_bot(auto_execute=False)


window = MainWindow()

window.show()


sys.exit(
    app.exec()
)

