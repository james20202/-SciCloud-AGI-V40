from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QLineEdit,QTextEdit,QComboBox,QMessageBox
from core.bible_manager import bible_manager

class BibleCenter(QWidget):
    def __init__(self):
        super().__init__(); self.kind='character'; self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(10)
        title=QLabel('📖 Character Bible / Scene Bible'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('把人物与场景变成长期创作约束：身份、外观、服装、声音、光线、氛围和负面约束都会进入 Prompt。'))
        bar=QHBoxLayout(); self.kindbox=QComboBox(); self.kindbox.addItems(['人物 Character Bible','场景 Scene Bible']); self.kindbox.currentIndexChanged.connect(self.change_kind); bar.addWidget(self.kindbox)
        for text,fn in [('＋新建',self.new_item),('保存新版本',self.save_version),('🔄刷新',self.refresh)]:
            b=QPushButton(text); b.clicked.connect(fn); bar.addWidget(b)
        root.addLayout(bar)
        self.list=QListWidget(); self.list.currentRowChanged.connect(self.load_selected); root.addWidget(self.list,1)
        self.name=QLineEdit(); self.name.setPlaceholderText('名称'); root.addWidget(self.name)
        self.editor=QTextEdit(); self.editor.setPlaceholderText('JSON设定。可直接编辑人物/场景 Bible。保存时自动生成新版本。'); root.addWidget(self.editor,3)
        self.info=QLabel(); self.info.setObjectName('Muted'); root.addWidget(self.info)
    def change_kind(self): self.kind='scene' if self.kindbox.currentIndex()==1 else 'character'; self.refresh()
    def refresh(self):
        self.list.clear()
        for x in bible_manager.list(self.kind): self.list.addItem(f"{x['entity_id']} · {x['name']} · V{x.get('version',1)}")
        self.info.setText(f'{"人物" if self.kind=="character" else "场景"} Bible：{self.list.count()} 个实体')
    def load_selected(self,row):
        items=bible_manager.list(self.kind)
        if 0<=row<len(items):
            x=items[row]; self.name.setText(x.get('name','')); import json; self.editor.setPlainText(json.dumps(x,ensure_ascii=False,indent=2)); self.info.setText(f"{x['entity_id']} · 当前版本 V{x.get('version',1)}")
    def new_item(self):
        x=bible_manager.create_character('新人物') if self.kind=='character' else bible_manager.create_scene('新场景')
        self.refresh(); self.list.setCurrentRow(0)
    def save_version(self):
        row=self.list.currentRow(); items=bible_manager.list(self.kind)
        if not (0<=row<len(items)): QMessageBox.information(self,'保存','请先选择一个实体'); return
        import json
        try: data=json.loads(self.editor.toPlainText())
        except Exception as e: QMessageBox.warning(self,'JSON错误',str(e)); return
        eid=items[row]['entity_id']; data.pop('entity_id',None); data.pop('type',None); data.pop('version',None); data.pop('created_at',None); data.pop('updated_at',None)
        saved=bible_manager.update(self.kind,eid,data,True); self.refresh()
        QMessageBox.information(self,'已保存',f"{eid} 已生成 V{saved['version']}")
