from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame,QTextEdit,QProgressBar,QGridLayout
from core.ai_scheduler import ai_scheduler

class ProductionDashboard(QWidget):
    def __init__(self): super().__init__(); self.build()
    def card(self,title,value,sub):
        f=QFrame(); f.setObjectName('Card'); l=QVBoxLayout(f); a=QLabel(title); a.setObjectName('Muted'); l.addWidget(a); v=QLabel(value); v.setStyleSheet('font-size:26px;font-weight:700;'); l.addWidget(v); s=QLabel(sub); s.setObjectName('Muted'); l.addWidget(s); return f
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(18)
        title=QLabel('导演驾驶舱'); title.setObjectName('PageTitle'); root.addWidget(title)
        sub=QLabel('告诉 AI 导演你想拍什么，其余流程由 V40 自动拆解。'); sub.setObjectName('Muted'); root.addWidget(sub)
        hero=QFrame(); hero.setObjectName('Hero'); hl=QVBoxLayout(hero); hl.setContentsMargins(24,22,24,22)
        h=QLabel('🎬 今天要创作什么？'); h.setStyleSheet('font-size:21px;font-weight:700;'); hl.addWidget(h)
        self.idea=QTextEdit(); self.idea.setPlaceholderText('例如：中式恐怖 + 道士斗法，60秒短剧，结尾留下悬念……'); self.idea.setFixedHeight(110); hl.addWidget(self.idea)
        row=QHBoxLayout(); start=QPushButton('✨ AI导演开始创作'); start.setObjectName('Primary'); start.clicked.connect(self.start); row.addWidget(start); demo=QPushButton('使用示例创意'); demo.setObjectName('Secondary'); demo.clicked.connect(lambda:self.idea.setPlainText('中式恐怖短剧：道士进入废弃凶宅，发现红衣女鬼，最后出现反转。60秒，9:16。')); row.addWidget(demo); row.addStretch(); hl.addLayout(row)
        root.addWidget(hero)
        grid=QGridLayout(); grid.setSpacing(14); grid.addWidget(self.card('进行中','03','生产任务'),0,0); grid.addWidget(self.card('已完成','12','项目 / 集数'),0,1); grid.addWidget(self.card('素材','286','人物 / 场景 / 道具'),0,2); root.addLayout(grid)
        r=QFrame(); r.setObjectName('Card'); rl=QVBoxLayout(r); rh=QLabel('生产流程'); rh.setStyleSheet('font-size:18px;font-weight:700;'); rl.addWidget(rh)
        self.status=QLabel('等待导演任务'); self.status.setObjectName('Muted'); rl.addWidget(self.status)
        self.progress=QProgressBar(); self.progress.setValue(0); rl.addWidget(self.progress); root.addWidget(r)
        recent=QFrame(); recent.setObjectName('Card'); l=QVBoxLayout(recent); q=QLabel('最近项目'); q.setStyleSheet('font-size:18px;font-weight:700;'); l.addWidget(q); l.addWidget(QLabel('《凶宅道士》  ·  第01集  ·  82%')); l.addWidget(QLabel('《九天剑诀》  ·  第03集  ·  已完成')); root.addWidget(recent); root.addStretch()
    def start(self):
        idea=self.idea.toPlainText().strip() or '未填写创意'
        self.status.setText('导演正在规划：'+idea[:80])
        self.progress.setValue(12)
        try:
            ai_scheduler.create_task('V40创作项目','001'); self.progress.setValue(28)
        except Exception: pass
