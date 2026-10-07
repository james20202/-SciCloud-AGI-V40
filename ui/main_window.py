from PySide6.QtWidgets import QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QPushButton,QStackedWidget,QFrame,QLabel
from ui.pages.production_dashboard import ProductionDashboard
from ui.pages.project_matrix import ProjectMatrix
from ui.pages.asset_center import AssetCenter
from ui.pages.ai_center import AICenter
from ui.pages.batch_center import BatchCenter
from ui.pages.video_center import VideoCenter
from ui.pages.publish_center import PublishCenter
from ui.pages.system_center import SystemCenter
from ui.pages.director_plan import DirectorPlanPage
from ui.pages.workflow_queue import WorkflowQueuePage
from ui.pages.vision_center import VisionCenter
from ui.pages.prompt_center import PromptCenter
from ui.pages.skill_center import SkillCenter
from ui.pages.model_center import ModelCenter
from ui.pages.bible_center import BibleCenter
from ui.pages.storyboard_director import StoryboardDirectorPage
from ui.pages.director_loop_center import DirectorLoopCenter
from ui.pages.production_factory import ProductionFactoryPage
from ui.pages.episode_center import EpisodeCenterPage
from ui.pages.autopilot_center import AutopilotCenter
from ui.pages.local_production_studio import LocalProductionStudio
from ui.pages.episode_pipeline_center import EpisodePipelineCenter
from ui.pages.model_diagnostics import ModelDiagnosticsPage
from ui.pages.model_router_center import ModelRouterCenter
from ui.pages.model_router_center import ModelRouterCenter
from ui.pages.model_router_center import ModelRouterCenter
from ui.pages.model_router_center import ModelRouterCenter
try: from ui.pages.v30.pipeline_center import PipelineCenter
except Exception: PipelineCenter=None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('SciCloud AGI V40 · AI内容导演操作系统'); self.resize(1480,900); self.build()
    def build(self):
        root=QWidget(); self.setCentralWidget(root); layout=QHBoxLayout(root); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        side=QFrame(); side.setObjectName('Sidebar'); side.setFixedWidth(230); sl=QVBoxLayout(side); sl.setContentsMargins(18,24,18,20); sl.setSpacing(6)
        brand=QLabel('✦ SciCloud AGI'); brand.setObjectName('Brand'); sl.addWidget(brand); sub=QLabel('V40 · AI内容导演操作系统'); sub.setObjectName('SubBrand'); sl.addWidget(sub); sl.addSpacing(22)
        self.stack=QStackedWidget(); self.pages={}; self.buttons=[]
        entries=[('🎬  导演驾驶舱',ProductionDashboard()),('🧠  AI导演计划',DirectorPlanPage()),('⚙  生产工作流',WorkflowQueuePage()),('📚  项目矩阵',ProjectMatrix()),('📖  Character / Scene Bible',BibleCenter()),('🎥  AI导演分镜',StoryboardDirectorPage()),('👁  视觉导演审核',VisionCenter()),('🎭  人物 / 资产中心',AssetCenter()),('🏭  本地生产工厂',ProductionFactoryPage()),('🎬  一键自动生产一集',EpisodeCenterPage()),('🚀  V40.60 自动驾驶',AutopilotCenter()),('🎞  V40.80 本地生产工作台',LocalProductionStudio()),('🚀  V40.100 一键成片流水线',EpisodePipelineCenter()),('🩺  模型实战诊断',ModelDiagnosticsPage()),('🧭  模型自动路由',ModelRouterCenter()),('🧭  模型自动路由',ModelRouterCenter()),('🧭  模型自动路由',ModelRouterCenter()),('🧭  模型自动路由',ModelRouterCenter()),('🧠  AI中心',AICenter()),('🚀  批量生产',BatchCenter())]
        if PipelineCenter: entries.append(('⚙  自动流水线',PipelineCenter()))
        entries += [('🧠  Model Hub',ModelCenter()),('🪄  Prompt Engine',PromptCenter()),('🧰  Skill Registry',SkillCenter()),('🎞  视频中心',VideoCenter()),('📤  发布中心',PublishCenter()),('🛠  系统中心',SystemCenter())]
        for name,page in entries:self.add_page(name,page,sl)
        sl.addStretch(); foot=QLabel('Local-first\n数据随项目目录保存'); foot.setObjectName('SubBrand'); sl.addWidget(foot)
        layout.addWidget(side); layout.addWidget(self.stack,1); self.buttons[0].setChecked(True)
    def add_page(self,name,page,layout):
        b=QPushButton(name); b.setObjectName('NavButton'); b.setCheckable(True); b.clicked.connect(lambda checked,p=page,btn=b:self.select(p,btn)); layout.addWidget(b); self.buttons.append(b); self.pages[name]=page; self.stack.addWidget(page)
    def select(self,page,button):
        self.stack.setCurrentWidget(page)
        for b in self.buttons:b.setChecked(b is button)
