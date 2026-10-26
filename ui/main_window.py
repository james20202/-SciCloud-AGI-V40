import getpass
import os
import shutil

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QStackedWidget, QFrame, QLabel, QToolButton, QMenu, QSizePolicy, QSpacerItem
from ui.pages.production_dashboard import ProductionDashboard
from ui.pages.director_plan import DirectorPlanPage
from ui.pages.storyboard_director import StoryboardDirectorPage
from ui.pages.autopilot_center import AutopilotCenter
from ui.pages.workflow_queue import WorkflowQueuePage
from ui.pages.local_production_studio import LocalProductionStudio
from ui.pages.episode_pipeline_center import EpisodePipelineCenter
from ui.pages.project_matrix import ProjectMatrix
from ui.pages.asset_center import AssetCenter
from ui.pages.bible_center import BibleCenter
from ui.pages.prompt_center import PromptCenter
from ui.pages.skill_center import SkillCenter
from ui.pages.model_center import ModelCenter
from ui.pages.model_diagnostics import ModelDiagnosticsPage
from ui.pages.model_router_center import ModelRouterCenter
from ui.pages.video_center import VideoCenter
from ui.pages.publish_center import PublishCenter
from ui.pages.system_center import SystemCenter
from ui.pages.production_factory import ProductionFactoryPage
from ui.pages.vision_center import VisionCenter
from ui.pages.ai_center import AICenter
from ui.pages.batch_center import BatchCenter
try:
    from ui.pages.v30.pipeline_center import PipelineCenter
except Exception:
    PipelineCenter = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SciCloud AGI V40 · AI内容导演操作系统')
        self.resize(1540, 960)
        self.setMinimumSize(1200, 760)
        self.pages = {}
        self.build()

    def build(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        outer.addWidget(self.build_topbar())
        body = QWidget(); bl = QHBoxLayout(body); bl.setContentsMargins(12,12,12,12); bl.setSpacing(12)
        bl.addWidget(self.build_dock())
        self.stack = QStackedWidget(); self.stack.setObjectName('ContentStack'); bl.addWidget(self.stack,1)
        outer.addWidget(body,1)
        self.register_pages()
        dashboard = self.pages.get('驾驶舱')
        if dashboard:
            dashboard.create_requested.connect(self.open_creation_with_idea)
            dashboard.navigate_requested.connect(self.select)
            dashboard.quick_requested.connect(self.handle_dashboard_quick)
        self.select('驾驶舱')

    def build_topbar(self):
        bar=QFrame(); bar.setObjectName('Topbar'); l=QHBoxLayout(bar); l.setContentsMargins(18,10,18,10); l.setSpacing(10)
        mark=QLabel('✦'); mark.setObjectName('BrandMark'); l.addWidget(mark)
        brand=QLabel('SciCloud AGI V40'); brand.setObjectName('Brand'); l.addWidget(brand)
        sub=QLabel('AI导演·让创意变成现实'); sub.setObjectName('TopSub'); l.addWidget(sub)
        l.addStretch()
        # 不再写死在线状态、存储占用和固定用户名：在线状态须由本机诊断确认，
        # 存储用应用所在磁盘的实际占用，用户用本机登录用户；诊断前只显示待诊断。
        status=QLabel('●  本地模式 · 待诊断'); status.setObjectName('StatusPill'); status.setToolTip('未运行本机诊断，请在系统中心运行诊断后查看 FFmpeg / Ollama / ComfyUI 状态'); l.addWidget(status)
        for t,k in [('项目','项目'),('资源','资产'),('模型','模型')]:
            b=QToolButton(); b.setObjectName('TopAction'); b.setText(t); b.clicked.connect(lambda _=False,kk=k:self.select(kk)); l.addWidget(b)
        try:
            app_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            disk=shutil.disk_usage(app_root)
            storage_text=f'存储 {100 * (disk.total - disk.free) / disk.total:.0f}%'
        except Exception:
            storage_text='存储 --'
        storage=QLabel(storage_text); storage.setObjectName('StorageChip'); l.addWidget(storage)
        try:
            username=getpass.getuser() or '本地用户'
        except Exception:
            username='本地用户'
        avatar_text=username[:2].upper() if len(username) >= 2 else username.upper()
        avatar=QLabel(avatar_text); avatar.setObjectName('UserAvatar'); l.addWidget(avatar)
        user=QLabel(username); user.setObjectName('UserChip'); l.addWidget(user)
        return bar

    def build_dock(self):
        dock=QFrame(); dock.setObjectName('Dock'); dock.setFixedWidth(148)
        l=QVBoxLayout(dock); l.setContentsMargins(8,12,8,12); l.setSpacing(4)
        self.dock_buttons=[]
        items=[('⌂','首页','驾驶舱'),('✦','创作','创作'),('▶','生产','生产'),('◇','资产','资产'),('◈','AI核心','模型')]
        for icon,label,key in items:
            b=QToolButton(); b.setObjectName('NavButton'); b.setCheckable(True); b.setText(icon+'\n'+label); b.setToolTip(label); b.setMinimumHeight(52); b.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed); b.clicked.connect(lambda _=False,k=key:self.select(k)); l.addWidget(b); self.dock_buttons.append((key,b))
        tools=QToolButton(); tools.setObjectName('NavButton'); tools.setText('☷\n更多'); tools.setToolTip('更多功能'); tools.setMinimumHeight(52); tools.clicked.connect(self.show_more_menu); l.addWidget(tools); self.dock_buttons.append(('工具',tools))
        sets=QToolButton(); sets.setObjectName('NavButton'); sets.setText('⚙\n系统'); sets.setToolTip('系统中心'); sets.setMinimumHeight(52); sets.clicked.connect(lambda:self.select('系统')); l.addWidget(sets); self.dock_buttons.append(('设置',sets))
        l.addItem(QSpacerItem(1,1,QSizePolicy.Minimum,QSizePolicy.Expanding))
        fb=QLabel('SciCloud AGI V40'); fb.setObjectName('DockFooterBrand'); fb.setAlignment(Qt.AlignCenter); l.addWidget(fb)
        fs=QLabel('AI让每个人都能成为导演'); fs.setObjectName('DockFooterSub'); fs.setAlignment(Qt.AlignCenter); l.addWidget(fs)
        return dock

    def register_pages(self):
        self.add_page('驾驶舱',ProductionDashboard()); self.add_page('创作',DirectorPlanPage()); self.add_page('分镜',StoryboardDirectorPage()); self.add_page('视觉审核',VisionCenter())
        self.add_page('生产',AutopilotCenter()); self.add_page('工作流',WorkflowQueuePage()); self.add_page('本地工厂',ProductionFactoryPage()); self.add_page('生产工作台',LocalProductionStudio()); self.add_page('一键成片',EpisodePipelineCenter())
        self.add_page('资产',AssetCenter()); self.add_page('人物场景',BibleCenter()); self.add_page('Prompt',PromptCenter()); self.add_page('Skill',SkillCenter())
        self.add_page('模型',ModelCenter()); self.add_page('模型诊断',ModelDiagnosticsPage()); self.add_page('模型路由',ModelRouterCenter()); self.add_page('后期',VideoCenter()); self.add_page('发布',PublishCenter()); self.add_page('系统',SystemCenter()); self.add_page('项目',ProjectMatrix()); self.add_page('AI中心',AICenter()); self.add_page('批量生产',BatchCenter())
        if PipelineCenter: self.add_page('自动流水线',PipelineCenter())
    def add_page(self,key,page): self.pages[key]=page; self.stack.addWidget(page)

    def open_creation_with_idea(self, idea):
        page = self.pages.get('创作')
        if page is not None and hasattr(page, 'idea'):
            page.idea.setPlainText(idea)
            page.generate()
        self.select('创作')

    def handle_dashboard_quick(self, key, idea):
        if key == '生成剧本':
            self.open_creation_with_idea(idea)
        elif key == '分镜设计':
            self.open_creation_with_idea(idea)
            page = self.pages.get('分镜')
            if page:
                page.refresh()
                page.create()
                self.select('分镜')
        elif key in ('角色设定', '场景生成'):
            self.open_creation_with_idea(idea)
            self.select('人物场景')
        elif key == '一键生成视频':
            page = self.pages.get('一键成片')
            if page:
                page.idea.setText(idea)
                page.create()
                page.out.append('生产任务已创建。点击“一键跑完整集”开始执行；如果本机缺少图像/视频模型，系统会显示具体阻塞原因。')
                self.select('一键成片')
    def select(self,key):
        routes={'驾驶舱':'驾驶舱','创作':'创作','生产':'生产','资产':'资产','模型':'模型','后期':'后期','系统':'系统'}
        target=routes.get(key,key); page=self.pages.get(target) or self.pages.get(key)
        if page: self.stack.setCurrentWidget(page)
        groups={'生产':{'工作流','本地工厂','生产工作台','一键成片'},'创作':{'分镜','视觉审核'},'资产':{'人物场景','Prompt','Skill'},'模型':{'模型诊断','模型路由'},'后期':{'发布'}}
        for group,b in self.dock_buttons: b.setChecked(group==key or key in groups.get(group,set()))
    def show_more_menu(self):
        menu=QMenu(self)
        sections={'创作工具':['分镜','视觉审核'],'生产工具':['工作流','本地工厂','生产工作台','一键成片'],'资产工具':['人物场景','Prompt','Skill'],'模型工具':['模型诊断','模型路由'],'项目与自动化':['项目','AI中心','批量生产','自动流水线'],'发布':['发布']}
        for title,keys in sections.items():
            sub=menu.addMenu(title)
            for key in keys:
                if key not in self.pages: continue
                a=sub.addAction(key); a.triggered.connect(lambda _=False,k=key:self.select(k))
        menu.exec(self.mapToGlobal(self.rect().topRight()+QPoint(-18,52)))
