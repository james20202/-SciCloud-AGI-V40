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

# ComfyUI auto-start (best-effort): probe 8188, start in the background
# only when it does not answer. This must never stop SciCloud itself
# from starting, so any failure is swallowed here; the one-click
# preflight remains the gate that reports an unreachable ComfyUI.
try:
    from core.comfyui_autostart import ensure_comfyui_running
    ensure_comfyui_running()
except Exception as exc:
    print(f"[comfyui-autostart] skipped: {exc}", file=sys.stderr)


window = MainWindow()

window.show()


sys.exit(
    app.exec()
)

