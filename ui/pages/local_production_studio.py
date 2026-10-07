import json
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTextEdit,QPushButton,QSpinBox,QComboBox
from core.shot_production_engine import shot_production_engine

class LocalProductionStudio(QWidget):
    def __init__(self):
        super().__init__(); self.setObjectName('Page'); self.build()
    def build(self):
        l=QVBoxLayout(self); l.setContentsMargins(30,26,30,26); l.setSpacing(14)
        title=QLabel('🎞 本地生产工作台 · V40.80'); title.setObjectName('PageTitle'); l.addWidget(title)
        desc=QLabel('镜头级真实生产：素材存在才算完成；没有本地模型时明确阻塞，不伪造结果。'); desc.setObjectName('SubBrand'); l.addWidget(desc)
        row=QHBoxLayout(); self.episode=QLineEdit(); self.episode.setPlaceholderText('EP-...'); row.addWidget(QLabel('Episode ID')); row.addWidget(self.episode); self.run=QLineEdit(); self.run.setPlaceholderText('SHOTRUN-...'); row.addWidget(QLabel('Run ID')); row.addWidget(self.run); l.addLayout(row)
        row=QHBoxLayout(); self.shot=QLineEdit(); self.shot.setPlaceholderText('SHOT-001'); row.addWidget(QLabel('镜头')); row.addWidget(self.shot)
        b=QPushButton('▶ 执行镜头'); b.clicked.connect(self.run_shot); row.addWidget(b)
        b=QPushButton('▶ 执行全部可运行镜头'); b.clicked.connect(self.run_all); row.addWidget(b)
        b=QPushButton('↻ 重置阻塞镜头'); b.clicked.connect(self.retry); row.addWidget(b); l.addLayout(row)
        self.output=QTextEdit(); self.output.setReadOnly(True); l.addWidget(self.output,1)
    def show_result(self,r): self.output.setPlainText(json.dumps(r,ensure_ascii=False,indent=2))
    def run_shot(self): self.show_result(shot_production_engine.produce_shot(self.run.text().strip(),self.shot.text().strip()))
    def run_all(self): self.show_result(shot_production_engine.run_ready(self.run.text().strip()))
    def retry(self): self.show_result(shot_production_engine.retry_blocked(self.run.text().strip()))
