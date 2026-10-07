from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QLineEdit,QSpinBox,QDoubleSpinBox,QCheckBox,QMessageBox
from core.vision_qc import vision_qc

class VisionCenter(QWidget):
    def __init__(self):
        super().__init__(); self.build(); self.load()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        title=QLabel('👁  视觉导演审核'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('V40.10：接入本地视觉模型后，可对人物一致性、构图、镜头、光影、动作等进行结构化审核。未配置模型时只做技术级 QC。'))
        self.enabled=QCheckBox('启用本地视觉模型'); root.addWidget(self.enabled)
        root.addWidget(QLabel('视觉命令（最后自动附加一个 JSON 参数，命令需输出 JSON 到 stdout）'))
        self.command=QLineEdit(); self.command.setPlaceholderText('例如：python3 /你的视觉模型/vision_qc.py'); root.addWidget(self.command)
        row=QHBoxLayout(); row.addWidget(QLabel('通过分数'))
        self.score=QDoubleSpinBox(); self.score.setRange(0,100); self.score.setValue(70); row.addWidget(self.score)
        row.addWidget(QLabel('超时（秒）')); self.timeout=QSpinBox(); self.timeout.setRange(5,600); self.timeout.setValue(120); row.addWidget(self.timeout); root.addLayout(row)
        buttons=QHBoxLayout(); save=QPushButton('保存视觉审核配置'); save.clicked.connect(self.save); buttons.addWidget(save)
        test=QPushButton('测试配置'); test.clicked.connect(self.test); buttons.addWidget(test); root.addLayout(buttons)
        self.status=QLabel(''); self.status.setObjectName('Muted'); self.status.setWordWrap(True); root.addWidget(self.status)
        root.addStretch()
    def load(self):
        cfg=vision_qc._cfg(); self.enabled.setChecked(bool(cfg.get('enabled'))); self.command.setText(cfg.get('command','')); self.score.setValue(float(cfg.get('pass_score',70))); self.timeout.setValue(int(cfg.get('timeout',120))); self.update_status(cfg)
    def update_status(self,cfg): self.status.setText('状态：已启用本地视觉审核' if cfg.get('enabled') and cfg.get('command') else '状态：未配置视觉模型；不会虚构视觉评分。')
    def save(self):
        cfg={'enabled':self.enabled.isChecked(),'command':self.command.text().strip(),'pass_score':self.score.value(),'timeout':self.timeout.value()}
        vision_qc.save_config(cfg); self.update_status(cfg); QMessageBox.information(self,'保存完成','视觉导演审核配置已保存。')
    def test(self):
        cfg={'enabled':self.enabled.isChecked(),'command':self.command.text().strip(),'pass_score':self.score.value(),'timeout':self.timeout.value()}
        vision_qc.save_config(cfg); r=vision_qc.analyze(__file__,{'test':True}); QMessageBox.information(self,'视觉审核测试',r.get('message','测试完成'))
