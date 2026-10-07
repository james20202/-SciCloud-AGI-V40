from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QMessageBox
from core.asset_manager import asset_manager
import os, subprocess, platform

class AssetCenter(QWidget):
    def __init__(self):
        super().__init__(); self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        title=QLabel('📦 Asset Center · 素材资产中心'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('V40.4：生成结果、人物、场景统一登记；每个实体拥有稳定 ID 和版本号。'))
        bar=QHBoxLayout()
        for text,fn in [('🔄 刷新',self.refresh),('🎭 人物',lambda:self.filter('character')),('🏯 场景',lambda:self.filter('scene')),('🎬 生成结果',lambda:self.filter(None)),('📂 打开资产目录',self.open_dir)]:
            b=QPushButton(text); b.clicked.connect(fn); bar.addWidget(b)
        root.addLayout(bar)
        self.stats=QLabel(); self.stats.setObjectName('Muted'); root.addWidget(self.stats)
        self.list=QListWidget(); self.list.itemSelectionChanged.connect(self.show_selected); root.addWidget(self.list,1)
        self.detail=QLabel('选择资产查看详情'); self.detail.setWordWrap(True); self.detail.setObjectName('Muted'); root.addWidget(self.detail)
    def refresh(self): self.filter(None)
    def filter(self, kind):
        self.current_kind=kind; self.list.clear(); assets=asset_manager.list_assets(asset_type=kind) if kind else asset_manager.list_assets()
        for a in assets:
            self.list.addItem(f"{a.get('asset_id')} · {a.get('entity_id')} · {a.get('name')} · V{a.get('version')} · {a.get('type')}")
        s=asset_manager.stats(); self.stats.setText(f"资产总数 {s['total']}  ·  人物 {s['character']}  ·  场景 {s['scene']}  ·  图片 {s['image']}  ·  视频 {s['video']}  ·  音频 {s['voice']}  ·  其他 {s['other']}")
    def selected(self):
        row=self.list.currentRow(); assets=asset_manager.list_assets(asset_type=self.current_kind) if self.current_kind else asset_manager.list_assets(); return assets[row] if 0<=row<len(assets) else None
    def show_selected(self):
        a=self.selected()
        if not a: return
        self.detail.setText(f"资产：{a.get('asset_id')}\n实体：{a.get('entity_id')} · V{a.get('version')}\n类型：{a.get('type')}\n名称：{a.get('name')}\n项目：{a.get('project_id') or '-'}\n来源：{a.get('source') or '-'}\n创建：{a.get('created_at')}\n元数据：{a.get('metadata',{})}")
    def open_dir(self):
        path=os.path.join(os.path.dirname(asset_manager.db),'assets'); os.makedirs(path,exist_ok=True)
        try:
            if platform.system()=='Darwin': subprocess.Popen(['open',path])
            elif platform.system()=='Windows': os.startfile(path)
            else: subprocess.Popen(['xdg-open',path])
        except Exception as e: QMessageBox.information(self,'打开目录',str(e))
