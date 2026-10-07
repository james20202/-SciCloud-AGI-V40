from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QMessageBox,QInputDialog
from core.model_hub import model_hub
from core.execution_engine import execution_engine

class ModelCenter(QWidget):
    def __init__(self): super().__init__(); self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        title=QLabel('🧠 Model Hub'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('V40.3：模型与本地执行适配器中心。这里只登记和检测真实能力，不把“注册成功”伪装成“已经生成”。'))
        bar=QHBoxLayout()
        for text,fn,obj in [('刷新',self.refresh,'Secondary'),('检测连接',self.test_selected,'Secondary'),('启用 / 停用',self.toggle,'Secondary')]:
            b=QPushButton(text); b.setObjectName(obj); b.clicked.connect(fn); bar.addWidget(b)
        root.addLayout(bar)
        self.list=QListWidget(); self.list.itemSelectionChanged.connect(self.show_selected); root.addWidget(self.list,1)
        self.detail=QLabel('选择一个模型查看详情'); self.detail.setObjectName('Muted'); self.detail.setWordWrap(True); root.addWidget(self.detail)
    def refresh(self):
        self.list.clear()
        for m in model_hub.list():
            state='● 已启用' if m.get('enabled') else '○ 未启用'
            self.list.addItem(f"{m['model_id']}  ·  {m['name']}  ·  {m.get('adapter')}  ·  {state}")
    def selected(self):
        i=self.list.currentRow(); items=model_hub.list(); return items[i] if 0<=i<len(items) else None
    def show_selected(self):
        m=self.selected()
        if m:self.detail.setText(f"{m.get('name')}\n类型：{m.get('type')}\nProvider：{m.get('provider')}\nAdapter：{m.get('adapter')}\n说明：{m.get('description','')}\nEndpoint：{m.get('endpoint','-')}")
    def test_selected(self):
        m=self.selected()
        if not m:return
        r=execution_engine.test_model(m['model_id']); QMessageBox.information(self,'模型检测',r.get('message',''))
    def toggle(self):
        m=self.selected()
        if not m:return
        model_hub.set_enabled(m['model_id'],not m.get('enabled')); self.refresh()
