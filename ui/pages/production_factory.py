from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QPlainTextEdit,QGroupBox,QFormLayout,QLineEdit
from core.model_hub import model_hub
from core.local_media_engine import local_media_engine
from core.production_engine import production_engine
import shutil, json

class ProductionFactoryPage(QWidget):
    def __init__(self):
        super().__init__(); root=QVBoxLayout(self)
        title=QLabel('🎞 本地生产工厂 · V40.30'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('把 AI 导演计划连接到真实的本地图像、视频、TTS、字幕、混音、剪辑与 MP4 导出。没有模型时不会伪造成功。'))
        box=QGroupBox('本地能力诊断'); form=QFormLayout(box)
        self.info=QPlainTextEdit(); self.info.setReadOnly(True); self.info.setMaximumHeight(230); root.addWidget(box); root.addWidget(self.info)
        row=QHBoxLayout(); b=QPushButton('🔍 检查本地环境'); b.clicked.connect(self.refresh); row.addWidget(b); root.addLayout(row)
        runbox=QGroupBox('生产运行'); rf=QFormLayout(runbox); self.plan=QLineEdit(); self.plan.setPlaceholderText('PLAN-...'); rf.addRow('计划 ID',self.plan); start=QPushButton('▶ 创建生产运行'); start.clicked.connect(self.start); rf.addRow(start); root.addWidget(runbox)
        root.addStretch(); self.refresh()
    def refresh(self):
        rows=[f'FFmpeg: {shutil.which("ffmpeg") or "未找到"}',f'FFprobe: {shutil.which("ffprobe") or "未找到"}']
        for mid in ['MODEL-COMFYUI','MODEL-LOCAL-TTS']:
            m=model_hub.get(mid); rows.append(f"{m.get('name')}: {'已启用' if m and m.get('enabled') else '未启用'}")
        self.info.setPlainText('\n'.join(rows))
    def start(self):
        d=production_engine.start_run(self.plan.text().strip() or 'UNBOUND','未命名生产'); self.info.append('\n生产运行已创建：'+d['run_id'])
