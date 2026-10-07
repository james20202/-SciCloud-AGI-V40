from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTextEdit
from core.model_router import model_router
class ModelRouterCenter(QWidget):
    def __init__(self):
        super().__init__(); l=QVBoxLayout(self)
        l.addWidget(QLabel('🧭 模型自动路由 · V40.131～160'))
        self.out=QTextEdit(); self.out.setReadOnly(True); l.addWidget(self.out)
        b=QPushButton('扫描并生成生产路由'); b.clicked.connect(self.scan); l.addWidget(b); self.scan()
    def scan(self):
        p=model_router.plan(['image','video','tts','sound','edit','vision'])
        self.out.setPlainText(__import__('json').dumps(p,ensure_ascii=False,indent=2))
