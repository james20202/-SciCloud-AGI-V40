from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QMessageBox
from core.diagnostics import diagnostics

class ModelDiagnosticsPage(QWidget):
    def __init__(self): super().__init__(); self.build(); self.refresh()
    def build(self):
        l=QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(12)
        t=QLabel('🩺 模型实战诊断'); t.setObjectName('PageTitle'); l.addWidget(t)
        l.addWidget(QLabel('V40.101–130：逐项探测本机模型能力。只有真实探测通过才进入“可生产”状态。'))
        b=QPushButton('重新扫描本机能力'); b.setObjectName('Secondary'); b.clicked.connect(self.refresh); l.addWidget(b)
        self.summary=QLabel(); self.summary.setObjectName('Muted'); l.addWidget(self.summary)
        self.list=QListWidget(); l.addWidget(self.list,1)
    def refresh(self):
        r=diagnostics.run(); s=r['summary']; self.summary.setText(f"模型 {s['total']} · 已启用 {s['enabled']} · 可用 {s['ready']} · 阻塞 {s['blocked']}")
        self.list.clear()
        for x in s['models']:
            p=x['probe']; self.list.addItem(('✅ ' if p['ready'] else '⛔ ')+x['model_id']+' · '+x['name']+' · '+p['reason'])
