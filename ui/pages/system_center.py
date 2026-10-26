from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame,QFileDialog,QMessageBox
from core.version import VERSION, PRODUCT_NAME
from core.update_manager import update_manager

class SystemCenter(QWidget):
    def __init__(self):
        super().__init__(); self.build()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(18)
        t=QLabel('系统中心'); t.setObjectName('PageTitle'); root.addWidget(t)
        s=QLabel('版本、升级与本地运行环境'); s.setObjectName('Muted'); root.addWidget(s)
        card=QFrame(); card.setObjectName('Card'); l=QVBoxLayout(card); l.setContentsMargins(20,20,20,20)
        v=QLabel(f'{PRODUCT_NAME}  ·  {VERSION}'); v.setStyleSheet('font-size:20px;font-weight:700;'); l.addWidget(v)
        info=QLabel('数据、项目、素材与成片默认保留在当前安装目录；升级时自动备份代码，不覆盖 data / projects / output。'); info.setObjectName('Muted'); l.addWidget(info)
        row=QHBoxLayout(); b=QPushButton('检查在线更新'); b.setObjectName('Secondary'); b.clicked.connect(self.check); row.addWidget(b)
        z=QPushButton('导入 ZIP 升级包'); z.setObjectName('Primary'); z.clicked.connect(self.import_zip); row.addWidget(z); row.addStretch(); l.addLayout(row)
        root.addWidget(card)
        tip=QLabel('一键升级：点击“检查在线更新”，发现新版本后确认即可自动下载并升级，升级后自动重启；没有网络时仍可用“导入 ZIP 升级包”。'); tip.setObjectName('Muted'); root.addWidget(tip); root.addStretch()
    def check(self):
        r=update_manager.check_online()
        if r.get('error'):
            QMessageBox.warning(self,'更新检查',r.get('message','检查失败，未确认是否有更新。'))
            return
        if not r.get('available'):
            QMessageBox.information(self,'更新检查',f'已是最新版本（{VERSION}）。')
            return
        latest=r.get('version','')
        ans=QMessageBox.question(self,'发现新版本',f'发现新版本 {latest}，当前 {VERSION}；升级将自动备份代码，不覆盖 data / projects / output，升级后自动重启。是否一键升级？',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if ans!=QMessageBox.Yes:
            return
        try:
            update_manager.download_and_stage(r.get('url') or None)
            QMessageBox.information(self,'升级已准备','升级包已下载并准备完成，软件将自动备份并重启升级。')
            self.window().close()
        except Exception as e:
            QMessageBox.critical(self,'升级失败',str(e))
    def import_zip(self):
        p,_=QFileDialog.getOpenFileName(self,'选择升级 ZIP','','ZIP 文件 (*.zip)')
        if not p:return
        try:
            update_manager.local_package(p)
            QMessageBox.information(self,'升级已准备','升级包已准备完成，软件将自动备份并重启升级。')
            self.window().close()
        except Exception as e:
            QMessageBox.critical(self,'升级失败',str(e))
