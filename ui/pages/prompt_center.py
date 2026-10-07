from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QTextEdit,QComboBox,QFrame
from core.prompt_engine import prompt_engine

class PromptCenter(QWidget):
    def __init__(self):
        super().__init__(); self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        title=QLabel('🪄 Prompt Engine'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('V40.2：Prompt 模板、变量、版本和模型适配的统一入口。'))
        row=QHBoxLayout(); self.selector=QComboBox(); row.addWidget(self.selector,1)
        btn=QPushButton('刷新模板'); btn.clicked.connect(self.refresh); row.addWidget(btn); root.addLayout(row)
        self.info=QLabel(''); self.info.setObjectName('Muted'); root.addWidget(self.info)
        self.editor=QTextEdit(); self.editor.setPlaceholderText('选择模板后查看/编辑 Prompt 模板……'); root.addWidget(self.editor,1)
        save=QPushButton('保存模板'); save.setObjectName('Primary'); save.clicked.connect(self.save); root.addWidget(save)
    def refresh(self):
        self.selector.clear(); self.templates=prompt_engine.list_templates()
        for t in self.templates:self.selector.addItem(f"{t['name']} · {t['key']}",t['key'])
        self.selector.currentIndexChanged.connect(self.load)
        if self.templates:self.load(0)
    def load(self,i):
        if not self.templates or i<0:return
        t=self.templates[i]; self.editor.setPlainText(t.get('template','')); self.info.setText(f"{t['id']} · V{t.get('version',1)} · 反向Prompt：{t.get('negative','')}")
    def save(self):
        if not self.templates:return
        i=self.selector.currentIndex(); t=dict(self.templates[i]); t['template']=self.editor.toPlainText(); t['version']=int(t.get('version',1))+1; prompt_engine.save_template(t); self.refresh()
