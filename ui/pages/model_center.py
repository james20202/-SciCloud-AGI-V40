from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QMessageBox,QInputDialog
from core.model_hub import model_hub
from core.execution_engine import execution_engine

class ModelCenter(QWidget):
    def __init__(self): super().__init__(); self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        title=QLabel('🧠 Model Hub'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('V40.3：模型与本地执行适配器中心。这里只登记和检测真实能力，不把“注册成功”伪装成“已经生成”。'))
        # Cloud LLM is env-configured, not a Model Hub entry: one static
        # note only, no new navigation, no rendering changes.
        cloud_note=QLabel('云端 LLM（可选，默认关闭，仅用于导演计划文字生成，不用于出图/出视频）：通过环境变量 SCICLOUD_CLOUD_LLM_ENABLED / SCICLOUD_CLOUD_LLM_BASE_URL / SCICLOUD_CLOUD_LLM_MODEL / SCICLOUD_CLOUD_LLM_API_KEY 配置，指向 OpenAI 兼容转发口（如 127.0.0.1:18899/v1）；任何云端失败都会自动回落本地 Ollama，再回落本地规则。提示词会发往上游，不适合敏感内容。')
        cloud_note.setObjectName('Muted'); cloud_note.setWordWrap(True); root.addWidget(cloud_note)
        # ComfyUI auto-start status: read-only label only, no new buttons.
        # The packaged app does not bundle ComfyUI, so the path always
        # points outside the bundle; see core/comfyui_autostart.py.
        try:
            from core.comfyui_autostart import status as comfyui_autostart_status
            _auto = comfyui_autostart_status()
            _auto_text = (
                f"ComfyUI 自动启动：{'已开启' if _auto['enabled'] else '已关闭（SCICLOUD_COMFYUI_AUTOSTART）'}"
                f" · 路径：{_auto['comfyui_dir']}"
                f" · 启动命令：{_auto['start_command']}"
                f" · 端口：{_auto['endpoint']}"
            )
        except Exception:
            _auto_text = "ComfyUI 自动启动：状态不可用"
        _auto_note = QLabel(_auto_text)
        _auto_note.setObjectName('Muted'); _auto_note.setWordWrap(True); root.addWidget(_auto_note)
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
