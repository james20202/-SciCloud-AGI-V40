import json
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTextEdit,QPushButton,QSpinBox,QComboBox
from core.episode_pipeline import episode_pipeline
class EpisodePipelineCenter(QWidget):
    def __init__(self):
        super().__init__(); self.setObjectName('Page'); l=QVBoxLayout(self); l.setContentsMargins(30,26,30,26); l.setSpacing(12)
        l.addWidget(QLabel('🚀 V40.100 · Episode Pipeline')); l.addWidget(QLabel('一句话 → 镜头 → 本地媒体 → 成片 → QC → 发布。真实文件才算成功。'))
        row=QHBoxLayout(); self.idea=QLineEdit(); self.idea.setPlaceholderText('例如：道士进入废弃凶宅，遇到红衣女鬼，结尾留下悬念'); row.addWidget(self.idea,1); self.ep=QLineEdit(); self.ep.setPlaceholderText('EP-...'); row.addWidget(self.ep)
        l.addLayout(row); row=QHBoxLayout()
        for name,fn in [('创建Pipeline',self.create),('准备镜头',self.prepare),('执行媒体',self.media),('一键跑完整集',self.run),('状态',self.status)]: b=QPushButton(name); b.clicked.connect(fn); row.addWidget(b)
        l.addLayout(row); self.out=QTextEdit(); self.out.setReadOnly(True); l.addWidget(self.out,1)
    def show(self,x): self.out.setPlainText(json.dumps(x,ensure_ascii=False,indent=2))
    def create(self):
        try:
            d=episode_pipeline.create(self.idea.text().strip()); self.ep.setText(d['episode_id']); self.show(d)
        except Exception as e:self.show({'error':str(e)})
    def prepare(self): self._call(lambda:episode_pipeline.prepare_shots(self.ep.text().strip()))
    def media(self): self._call(lambda:episode_pipeline.run_media(self.ep.text().strip()))
    def run(self): self._call(lambda:episode_pipeline.run(self.ep.text().strip()))
    def status(self): self._call(lambda:episode_pipeline.status(self.ep.text().strip()))
    def _call(self,fn):
        try:self.show(fn())
        except Exception as e:self.show({'error':str(e)})
