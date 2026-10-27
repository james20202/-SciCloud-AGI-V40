"""发布中心（V40 真实发布包列表）。

历史问题：旧版读的是启动目录下的 legacy publish.json，
而 V40 生产链从不写它，所以列表永远是空的；“发布检查”
还用 text[1:4] 抠集数，取不到数据时只打日志、点了没反应；
“标记发布完成”只改 legacy 文件里的状态，不生成、不上传、
不校验任何成片。

现在：列表只读真实的 V40 发布包（见 core/publish_packages.py）：
工作流 TASK-12 产出的 *_episode_package.zip 和 EP 路线产出的
*_publish.zip。列表为空时明确告诉用户先去哪里完成一集，
而不是显示假发布。发布检查只读 zip 内容列表，不抠集数、
不取不存在的键。“标记发布完成”按钮已禁用：本地 zip 只是
交付物，不是上传证明，没有真实上传/校验就不改状态为已发布。
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
)

from core.publish_packages import list_real_packages, package_contents

EMPTY_TEXT = (
    "暂无发布包：请先在工作流页完成一集（TASK-12 会生成发布包），"
    "或在生产页完成 EP 发布阶段，再回来查看。"
)


class PublishCenter(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("📤 发布中心")
        title.setStyleSheet("font-size:26px;font-weight:bold;")
        layout.addWidget(title)
        note = QLabel(
            "这里只列出 V40 真实生成的发布包（工作流 TASK-12 / EP 发布阶段）。"
            "本地发布包只是交付物文件，未上传到任何平台。"
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.list = QListWidget()
        layout.addWidget(self.list)
        self.info = QLabel("状态：等待")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        refresh = QPushButton("🔄 刷新发布列表")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        check = QPushButton("📋 发布检查")
        check.clicked.connect(self.check)
        layout.addWidget(check)
        finish = QPushButton("✅ 标记发布完成（已禁用：无真实上传）")
        finish.setEnabled(False)
        finish.clicked.connect(self.finish)
        layout.addWidget(finish)
        self.setLayout(layout)
        self.refresh()

    def refresh(self):
        self.list.clear()
        packages = list_real_packages()
        for package in packages:
            item = QListWidgetItem(
                f"{package['name']}  ·  {package['size_bytes']} 字节  ·  {package['modified']}"
            )
            item.setData(Qt.UserRole, package["path"])
            self.list.addItem(item)
        if packages:
            self.info.setText(f"发布包：{len(packages)} 个（真实文件，非上传状态）")
        else:
            self.info.setText(EMPTY_TEXT)

    def selected_package_path(self):
        item = self.list.currentItem()
        if not item:
            return None
        return item.data(Qt.UserRole)

    def check(self):
        path = self.selected_package_path()
        if not path:
            self.info.setText("请先在列表中选择一个发布包，再做发布检查。")
            return
        names = package_contents(path)
        if not names:
            self.info.setText(f"发布包无法读取为 zip：{path}")
            return
        self.info.setText(
            f"发布包：{path}\n包含 {len(names)} 个文件："
            + "、".join(names[:20])
            + ("……" if len(names) > 20 else "")
        )

    def finish(self):
        # Guard: never mark a local zip as "已发布" without a real
        # upload/verification step, which this page does not have.
        self.info.setText(
            "不能标记为已发布：本地发布包只是交付物文件，未上传到任何平台，"
            "也没有上传校验。本页不改写任何发布状态。"
        )
