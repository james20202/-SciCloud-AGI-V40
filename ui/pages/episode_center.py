from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QPlainTextEdit,QGroupBox,QFormLayout,QLineEdit,QSpinBox,QComboBox
from core.episode_engine import episode_engine

class EpisodeCenterPage(QWidget):
    def __init__(self):
        super().__init__(); root=QVBoxLayout(self)
        title=QLabel('🎬 一键自动生产一集 · V40.40'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('输入一句创意，建立整集项目、导演计划和生产工作流。真实模型负责真实生成；未配置能力会明确失败，不伪造成片。'))
        box=QGroupBox('创建整集'); form=QFormLayout(box)
        self.idea=QPlainTextEdit(); self.idea.setPlaceholderText('例如：道士进入废弃凶宅，发现红衣女鬼，结尾留下一个反常悬念。'); self.idea.setMaximumHeight(100); form.addRow('创意',self.idea)
        self.title=QLineEdit(); form.addRow('片名（可选）',self.title)
        self.duration=QSpinBox(); self.duration.setRange(15,600); self.duration.setValue(60); form.addRow('时长（秒）',self.duration)
        self.ratio=QComboBox(); self.ratio.addItems(['9:16','16:9','1:1']); form.addRow('画幅',self.ratio)
        row=QHBoxLayout(); create=QPushButton('🚀 一键建立整集'); create.clicked.connect(self.create); row.addWidget(create); self.runbtn=QPushButton('▶ 自动生产'); self.runbtn.clicked.connect(self.run); row.addWidget(self.runbtn); form.addRow(row)
        root.addWidget(box)
        ctl=QHBoxLayout()
        for text,fn in [('Ⅱ 暂停',self.pause),('▶ 恢复',self.resume),('↻ 重试失败任务',self.retry),('🔄 刷新状态',self.refresh)]:
            b=QPushButton(text); b.clicked.connect(fn); ctl.addWidget(b)
        root.addLayout(ctl)
        self.output=QPlainTextEdit(); self.output.setReadOnly(True); root.addWidget(self.output,1)
        self.episode_id=None
    def _show(self, data): self.output.setPlainText(__import__('json').dumps(data,ensure_ascii=False,indent=2))
    def create(self):
        idea=self.idea.toPlainText().strip()
        if not idea: self.output.setPlainText('请先输入创意。'); return
        ep=episode_engine.create_episode(idea,self.title.text().strip() or None,self.duration.value(),self.ratio.currentText()); self.episode_id=ep['episode_id']; self._show(ep)
    def run(self):
        if not self.episode_id: self.create()
        if self.episode_id: self._show(episode_engine.run(self.episode_id))
    def pause(self):
        if self.episode_id: self._show(episode_engine.pause(self.episode_id))
    def resume(self):
        if self.episode_id: self._show(episode_engine.resume(self.episode_id))
    def retry(self):
        if self.episode_id: self._show(episode_engine.retry_failed(self.episode_id))
    def refresh(self):
        if self.episode_id: self._show(episode_engine.status(self.episode_id))
