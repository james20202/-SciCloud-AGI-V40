from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QMessageBox, QFileDialog, QInputDialog
)
from core.asset_manager import asset_manager
from core.character_reference_engine import character_reference_engine
import os
import subprocess
import platform


class AssetCenter(QWidget):
    def __init__(self):
        super().__init__()
        self.build()
        self.refresh()

    def build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)
        title = QLabel("📦 素材资产中心")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        root.addWidget(QLabel("角色、场景、参考图与生成结果统一登记；角色参考图支持版本历史和镜头绑定。"))
        bar = QHBoxLayout()
        actions = [
            ("🔄 刷新", self.refresh),
            ("🎭 人物", lambda: self.filter("character")),
            ("🖼 角色参考图", lambda: self.filter("character_reference")),
            ("➕ 绑定参考图", self.bind_character_reference),
            ("🏯 场景", lambda: self.filter("scene")),
            ("🎬 全部资产", lambda: self.filter(None)),
            ("📂 打开资产目录", self.open_dir),
        ]
        for label, callback in actions:
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
        root.addLayout(bar)
        self.stats = QLabel()
        self.stats.setObjectName("Muted")
        root.addWidget(self.stats)
        self.list = QListWidget()
        self.list.itemSelectionChanged.connect(self.show_selected)
        root.addWidget(self.list, 1)
        self.detail = QLabel("选择资产查看详情")
        self.detail.setWordWrap(True)
        self.detail.setObjectName("Muted")
        root.addWidget(self.detail)

    def refresh(self):
        self.filter(None)

    def filter(self, kind):
        self.current_kind = kind
        self.list.clear()
        assets = asset_manager.list_assets(asset_type=kind) if kind else asset_manager.list_assets()
        for asset in assets:
            self.list.addItem(
                f"{asset.get('asset_id')} · {asset.get('entity_id')} · {asset.get('name')} · "
                f"V{asset.get('version')} · {asset.get('type')}"
            )
        stats = asset_manager.stats()
        refs = len(character_reference_engine.list_references())
        self.stats.setText(
            f"资产总数 {stats['total']} · 人物 {stats['character']} · 场景 {stats['scene']} · "
            f"图片 {stats['image']} · 视频 {stats['video']} · 音频 {stats['voice']} · "
            f"角色参考图 {refs} · 其他 {stats['other']}"
        )

    def _current_assets(self):
        return asset_manager.list_assets(asset_type=self.current_kind) if self.current_kind else asset_manager.list_assets()

    def selected(self):
        row = self.list.currentRow()
        assets = self._current_assets()
        return assets[row] if 0 <= row < len(assets) else None

    def show_selected(self):
        asset = self.selected()
        if not asset:
            return
        self.detail.setText(
            f"资产：{asset.get('asset_id')}\n实体：{asset.get('entity_id')} · V{asset.get('version')}\n"
            f"类型：{asset.get('type')}\n名称：{asset.get('name')}\n项目：{asset.get('project_id') or '-'}\n"
            f"来源：{asset.get('source') or '-'}\n创建：{asset.get('created_at')}\n"
            f"元数据：{asset.get('metadata', {})}"
        )

    def bind_character_reference(self):
        selected = self.selected()
        character_id = ""
        character_name = ""
        if selected and selected.get("type") == "character":
            character_id = str(selected.get("entity_id") or "")
            character_name = str(selected.get("name") or "")
        if not character_id:
            character_id, ok = QInputDialog.getText(
                self, "绑定角色参考图", "角色稳定 ID（需与导演计划中的角色 ID 一致）："
            )
            if not ok or not character_id.strip():
                return
            character_name, ok = QInputDialog.getText(
                self, "绑定角色参考图", "角色名称：", text=character_id.strip()
            )
            if not ok:
                return
        path, _ = QFileDialog.getOpenFileName(
            self, "选择角色参考图", "", "图片 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not path:
            return
        project_id, ok = QInputDialog.getText(
            self, "参考图归属", "项目/剧集 ID（留空表示全局角色资产）："
        )
        if not ok:
            return
        try:
            item = character_reference_engine.register_reference(
                character_id.strip(), character_name.strip(), path, project_id=project_id.strip() or None
            )
            self.filter("character_reference")
            QMessageBox.information(
                self, "角色参考图已登记",
                f"角色：{character_name.strip()}\n版本：V{item.get('version')}\n文件：{item.get('source')}\n\n"
                "新镜头将尝试绑定此参考图。ComfyUI 工作流还需要配置对应的参考图节点。"
            )
        except Exception as exc:
            QMessageBox.warning(self, "参考图登记失败", str(exc))

    def open_dir(self):
        path = os.path.join(os.path.dirname(asset_manager.db), "assets")
        os.makedirs(path, exist_ok=True)
        try:
            if platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            elif platform.system() == "Windows":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            QMessageBox.information(self, "打开目录", str(exc))
