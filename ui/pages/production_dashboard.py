import os
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame,QTextEdit,QProgressBar,QGridLayout
from PySide6.QtGui import QPixmap
from core.dashboard_summary import summarize_workflows
from core.workflow_engine import workflow_engine

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
BG_PATH = os.path.join(ASSET_DIR, 'bg_main.png')

class ProductionDashboard(QWidget):
    create_requested = Signal(str)
    navigate_requested = Signal(str)
    quick_requested = Signal(str, str)

    def __init__(self):
        super().__init__(); self.build()

    def mini(self, icon, title, sub):
        f=QFrame(); f.setObjectName('MiniCard'); l=QVBoxLayout(f); l.setContentsMargins(14,12,14,12); l.setSpacing(6)
        i=QLabel(icon); i.setStyleSheet('font-size:20px;color:#d6c38f;'); l.addWidget(i)
        t=QLabel(title); t.setStyleSheet('font-size:13px;font-weight:750;color:#f1eee6;'); l.addWidget(t)
        s=QLabel(sub); s.setObjectName('Muted'); s.setWordWrap(True); l.addWidget(s); return f

    def step(self, name, status, tone):
        f=QFrame(); f.setObjectName('PipelineStep'); l=QVBoxLayout(f); l.setContentsMargins(12,10,12,10); l.setSpacing(6)
        n=QLabel(name); n.setStyleSheet('font-size:12px;font-weight:700;color:#e8e5dc;'); l.addWidget(n)
        s=QLabel(status); s.setObjectName(tone); l.addWidget(s); return f

    def template(self, name, count):
        f=QFrame(); f.setObjectName('TemplateCard'); l=QVBoxLayout(f); l.setContentsMargins(14,11,14,11); l.setSpacing(4)
        n=QLabel(name); n.setStyleSheet('font-size:12px;font-weight:700;color:#efe9dc;'); l.addWidget(n)
        c=QLabel(count); c.setObjectName('Muted'); l.addWidget(c); return f

    def build(self):
        root=QGridLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        bg=QLabel(); bg.setScaledContents(True)
        if os.path.exists(BG_PATH): bg.setPixmap(QPixmap(BG_PATH))
        root.addWidget(bg,0,0)

        content=QWidget(); content.setObjectName('DashContent'); cl=QVBoxLayout(content); cl.setContentsMargins(16,14,16,16); cl.setSpacing(12)
        root.addWidget(content,0,0)

        body=QHBoxLayout(); body.setSpacing(12)
        left=QVBoxLayout(); left.setSpacing(11)

        # ===== Hero：主标题 + 输入框 + 开始创作 + 快捷操作 =====
        hero=QFrame(); hero.setObjectName('Hero'); hl=QVBoxLayout(hero); hl.setContentsMargins(24,20,24,18); hl.setSpacing(9)
        eyebrow=QLabel('SCICLOUD AGI  ·  DIRECTOR OS'); eyebrow.setStyleSheet('font-size:9px;letter-spacing:2px;color:#9c9a92;'); hl.addWidget(eyebrow)
        ht=QLabel('AI 电影导演工作站'); ht.setObjectName('HeroTitle'); hl.addWidget(ht)
        hs=QLabel('从一个想法开始，让AI为你完成整个影视制作流程'); hs.setObjectName('HeroSub'); hl.addWidget(hs)
        inp=QHBoxLayout(); inp.setSpacing(10)
        self.idea=QTextEdit(); self.idea.setPlaceholderText('告诉AI，你想拍什么？例如：一个修仙少年从凡人到仙尊的成长故事'); self.idea.setFixedHeight(64); inp.addWidget(self.idea,1)
        start=QPushButton('✦  开始创作'); start.setObjectName('Primary'); start.setFixedHeight(64); start.clicked.connect(self.start); inp.addWidget(start)
        hl.addLayout(inp)
        row=QHBoxLayout(); row.setSpacing(8)
        for t in ['生成剧本','分镜设计','角色设定','场景生成','一键生成视频']:
            b=QPushButton(t); b.setObjectName('QuickBtn'); b.clicked.connect(lambda _=False,k=t:self.quick(k)); row.addWidget(b)
        row.addStretch(); hl.addLayout(row)
        left.addWidget(hero)

        # ===== 创作工作台 =====
        section=QHBoxLayout(); st=QLabel('创作工作台'); st.setObjectName('SectionTitle'); section.addWidget(st); section.addStretch()
        note=QLabel('AI FIRST · LOCAL WORKFLOW'); note.setObjectName('Muted'); section.addWidget(note); left.addLayout(section)
        cards=QGridLayout(); cards.setSpacing(10)
        cards.addWidget(self.mini('▤','剧本创作','AI智能生成剧本·多种风格选择'),0,0)
        cards.addWidget(self.mini('♙','分镜设计','智能分镜·镜头规划·镜头预览'),0,1)
        cards.addWidget(self.mini('◈','角色生成','多风格角色·支持图生视频'),0,2)
        cards.addWidget(self.mini('▦','场景生成','AI场景·风格多样·高质量画面'),0,3)
        left.addLayout(cards)

        # ===== 制作流水线：真实工作流数据 =====
        # Previously every step and percentage here was hard-coded.
        # Now the stages come from the newest real workflow (see
        # core/dashboard_summary.py); with no workflow at all, every
        # stage honestly reads "待处理".
        try:
            summary = summarize_workflows(workflow_engine.list_workflows())
        except Exception:
            summary = summarize_workflows([])
        latest = summary['latest']
        pl=QHBoxLayout(); pt=QLabel('制作流水线'); pt.setObjectName('SectionTitle'); pl.addWidget(pt); pl.addStretch()
        more=QPushButton('查看全部 >'); more.setObjectName('Secondary'); more.setFixedHeight(28); more.clicked.connect(lambda: self.navigate_requested.emit('生产')); pl.addWidget(more); left.addLayout(pl)
        steps=QHBoxLayout(); steps.setSpacing(8)
        for stage in summary['pipeline']:
            tone = 'Ok' if stage['status'] == '已完成' else ('Warn' if stage['status'] == '进行中' else 'Muted')
            steps.addWidget(self.step(stage['name'], stage['status'], tone), 1)
        left.addLayout(steps)
        # The old "热门模板" block had no real usage statistics behind
        # it (fixed usage counts with no data behind them), so it is
        # removed outright rather than replaced with new fixed numbers.
        # rather than replaced with another set of fixed numbers.
        left.addStretch()
        body.addLayout(left,1)

        # ===== 右侧面板：AI导演中枢 / 当前项目 / 最近项目 =====
        right=QVBoxLayout(); right.setSpacing(10)
        W=290
        hub=QFrame(); hub.setObjectName('PanelCard'); hub.setFixedWidth(W); rl=QVBoxLayout(hub); rl.setContentsMargins(16,14,16,14); rl.setSpacing(8)
        rt=QLabel('AI 导演中枢'); rt.setObjectName('SectionTitle'); rl.addWidget(rt)
        if latest:
            stt=QLabel(f"◉ {latest['title']} · {latest['status_text']}"); stt.setStyleSheet('color:#d8c48c;font-size:12px;font-weight:600;'); stt.setWordWrap(True); rl.addWidget(stt)
            ssub=QLabel(f"已完成 {latest['done']} / {latest['total']} 个任务"); ssub.setObjectName('Muted'); rl.addWidget(ssub)
            bar=QProgressBar(); bar.setValue(latest['progress']); rl.addWidget(bar)
            rl.addWidget(QLabel(f"总体进度 {latest['progress']}%（按已完成任务数计算）"))
        else:
            stt=QLabel('◉ 暂无工作流'); stt.setStyleSheet('color:#d8c48c;font-size:12px;font-weight:600;'); rl.addWidget(stt)
            ssub=QLabel('请先从上方开始创作，生成导演计划并进入生产队列。'); ssub.setObjectName('Muted'); ssub.setWordWrap(True); rl.addWidget(ssub)
            bar=QProgressBar(); bar.setValue(0); rl.addWidget(bar)
        right.addWidget(hub)

        cur=QFrame(); cur.setObjectName('PanelCard'); cur.setFixedWidth(W); cll=QVBoxLayout(cur); cll.setContentsMargins(16,14,16,14); cll.setSpacing(8)
        cht=QHBoxLayout(); a=QLabel('当前项目'); a.setObjectName('SectionTitle'); cht.addWidget(a); cht.addStretch(); cht.addWidget(QLabel(latest['status_text'] if latest else '暂无')); cll.addLayout(cht)
        proj=QLabel(latest['title'] if latest else '暂无项目'); proj.setStyleSheet('font-size:15px;font-weight:750;color:#f2eee4;'); proj.setWordWrap(True); cll.addWidget(proj)
        pdesc=QLabel(f"{latest['done']} / {latest['total']} 个任务已完成" if latest else '请先开始创作'); pdesc.setObjectName('Muted'); cll.addWidget(pdesc)
        b2=QPushButton('继续创作'); b2.setObjectName('Secondary'); b2.clicked.connect(self.goto_project); cll.addWidget(b2)
        right.addWidget(cur)

        rec=QFrame(); rec.setObjectName('PanelCard'); rec.setFixedWidth(W); rcl=QVBoxLayout(rec); rcl.setContentsMargins(16,14,16,14); rcl.setSpacing(6)
        rh=QHBoxLayout(); r1=QLabel('最近项目'); r1.setObjectName('SectionTitle'); rh.addWidget(r1); rh.addStretch()
        r2=QPushButton('查看全部 >'); r2.setObjectName('Secondary'); r2.setFixedHeight(26); r2.clicked.connect(lambda: self.navigate_requested.emit('工作流')); rh.addWidget(r2); rcl.addLayout(rh)
        if summary['recent']:
            for item in summary['recent']:
                rr=QHBoxLayout(); n=QLabel(item['title']); n.setStyleSheet('font-size:12px;font-weight:650;color:#e3e0d7;'); n.setWordWrap(True); rr.addWidget(n); rr.addStretch()
                t=QLabel(item['created']); t.setObjectName('Muted'); rr.addWidget(t)
                s=QLabel(item['status_text']); s.setObjectName('Muted'); rr.addWidget(s)
                rcl.addLayout(rr)
        else:
            empty=QLabel('暂无项目，请先开始创作'); empty.setObjectName('Muted'); rcl.addWidget(empty)
        right.addWidget(rec)
        right.addStretch()
        body.addLayout(right)

        cl.addLayout(body)

    def start(self):
        idea = self.idea.toPlainText().strip()
        if not idea:
            self.idea.setFocus()
            self.idea.setPlaceholderText('请先输入创意，再开始创作。')
            return
        self.create_requested.emit(idea)

    def quick(self, key):
        routes = {
            '生成剧本': '创作',
            '分镜设计': '分镜',
            '角色设定': '人物场景',
            '场景生成': '人物场景',
            '一键生成视频': '一键成片',
        }
        idea = self.idea.toPlainText().strip()
        if not idea:
            idea = '创作一部60秒玄幻修仙短剧：主角从废柴逆袭，结尾留下悬念。'
            self.idea.setPlainText(idea)
        target = routes.get(key)
        if not target:
            return
        if key == '生成剧本':
            self.create_requested.emit(idea)
        else:
            self.navigate_requested.emit(target)
            self.quick_requested.emit(key, idea)

    def goto_project(self):
        # The old target was the legacy project page, which lists
        # nothing from V40 workflows. The real current project lives
        # on the workflow page.
        self.navigate_requested.emit('工作流')
