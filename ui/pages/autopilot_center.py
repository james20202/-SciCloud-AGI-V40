from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTextEdit,QComboBox
from core.episode_engine import episode_engine
from core.autopilot_engine import autopilot_engine
from core.shot_production_engine import shot_production_engine
from core.episode_pipeline import episode_pipeline
from core.autopilot_pack import resolve_and_build
class AutopilotCenter(QWidget):
    def __init__(self):
        super().__init__(); l=QVBoxLayout(self)
        l.addWidget(QLabel('🚀 V40.60 AI导演自动驾驶'))
        row=QHBoxLayout(); self.ep=QLineEdit(); self.ep.setPlaceholderText('EP-...'); row.addWidget(self.ep)
        for text,fn in [('状态',self.status),('启动自动驾驶',self.run),('准备镜头',self.prepare),('镜头队列',self.shots),('打包发布',self.pack)]:
            b=QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        l.addLayout(row); self.out=QTextEdit(); self.out.setReadOnly(True); l.addWidget(self.out)
    def show(self,x): self.out.setPlainText(str(x))
    def status(self):
        try:self.show(episode_engine.status(self.ep.text().strip()))
        except Exception as e:self.show({'error':str(e)})
    def run(self):
        try:self.show(autopilot_engine.run(self.ep.text().strip()))
        except Exception as e:self.show({'error':str(e)})
    def prepare(self):
        try:
            self.show(episode_pipeline.prepare_shots(self.ep.text().strip()))
        except Exception as e:self.show({'error':str(e)})
    def shots(self):
        try:
            ep=episode_engine.status(self.ep.text().strip()); self.show(episode_pipeline.status(self.ep.text().strip()))
        except Exception as e:self.show({'error':str(e)})
    def pack(self):
        # Previously this called build(ep_id) with no final_video, and
        # build() rejects a missing final video, so the button could
        # never succeed. Now the EP record's real final_video is
        # resolved first (see core/autopilot_pack.py); when it does
        # not exist yet, the user is told exactly what to generate
        # first instead of getting a silent failure.
        try:self.show(resolve_and_build(self.ep.text().strip()))
        except Exception as e:self.show({'error':str(e)})
