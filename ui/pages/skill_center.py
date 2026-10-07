from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QMessageBox
from core.skill_registry import skill_registry

class SkillCenter(QWidget):
    def __init__(self): super().__init__(); self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        title=QLabel('🧰 Skill Registry'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('V40.2：AI能力统一注册表。后续可挂接本地模型、ComfyUI、TTS、视频生成等执行适配器。'))
        bar=QHBoxLayout(); b=QPushButton('刷新'); b.clicked.connect(self.refresh); bar.addWidget(b); root.addLayout(bar)
        self.list=QListWidget(); root.addWidget(self.list,1)
    def refresh(self):
        self.list.clear()
        for s in skill_registry.list():
            state='启用' if s.get('enabled') else '停用'
            self.list.addItem(f"{s['skill_id']}  ·  {s['name']}  ·  {state}  ·  {s.get('provider','')}")
