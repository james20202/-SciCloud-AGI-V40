from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget
)


from ui.pages.production_dashboard import ProductionDashboard
from ui.pages.project_center import ProjectCenter
from ui.pages.project_matrix import ProjectMatrix
from ui.pages.asset_center import AssetCenter
from ui.pages.character_center import CharacterCenter
from ui.pages.storyboard_center import StoryboardCenter
from ui.pages.material_center import MaterialCenter
from ui.pages.ai_center import AICenter
from ui.pages.production_monitor import ProductionMonitor
from ui.pages.video_center import VideoCenter
from ui.pages.publish_center import PublishCenter
from ui.pages.batch_center import BatchCenter



class MainWindow(QMainWindow):


    def __init__(self):

        super().__init__()


        self.setWindowTitle(
            "⚔ 仙剧工坊 V26.5 AI生产系统"
        )


        self.resize(
            1280,
            800
        )


        self.init_ui()



    def init_ui(self):


        root = QWidget()


        self.setCentralWidget(
            root
        )


        main_layout = QHBoxLayout(
            root
        )


        menu_layout = QVBoxLayout()


        self.stack = QStackedWidget()



        # 页面初始化

        self.dashboard = ProductionDashboard()

        self.project = ProjectCenter()

        self.matrix = ProjectMatrix()

        self.asset = AssetCenter()

        self.character = CharacterCenter()

        self.storyboard = StoryboardCenter()

        self.material = MaterialCenter()

        self.ai = AICenter()

        self.monitor = ProductionMonitor()

        self.video = VideoCenter()

        self.publish = PublishCenter()

        self.batch = BatchCenter()



        pages = [

            self.dashboard,

            self.project,

            self.matrix,

            self.asset,

            self.character,

            self.storyboard,

            self.material,

            self.ai,

            self.monitor,

            self.video,

            self.publish,

            self.batch

        ]



        for page in pages:

            self.stack.addWidget(
                page
            )



        menus = [

            (
                "⚔ AI生产驾驶舱",
                self.dashboard
            ),

            (
                "📚 项目中心",
                self.project
            ),

            (
                "📚 项目矩阵中心",
                self.matrix
            ),

            (
                "📦 项目资产中心",
                self.asset
            ),

            (
                "🧑 角色库",
                self.character
            ),

            (
                "🎞 分镜中心",
                self.storyboard
            ),

            (
                "🖼 素材中心",
                self.material
            ),

            (
                "🧠 AI中心",
                self.ai
            ),

            (
                "🚀 AI批量生产中心",
                self.batch
            ),

            (
                "📊 生产监控",
                self.monitor
            ),

            (
                "🎬 视频炼制",
                self.video
            ),

            (
                "📤 发布中心",
                self.publish
            )

        ]



        for text,page in menus:


            button = QPushButton(
                text
            )


            button.clicked.connect(

                lambda checked=False,
                p=page:

                self.stack.setCurrentWidget(
                    p
                )

            )


            menu_layout.addWidget(
                button
            )



        menu_layout.addStretch()



        main_layout.addLayout(
            menu_layout,
            1
        )


        main_layout.addWidget(
            self.stack,
            5
        )



        # 默认进入驾驶舱

        self.stack.setCurrentWidget(
            self.dashboard
        )


# V30 Pipeline Extension

try:

    from ui.pages.v30.pipeline_center import PipelineCenter


    self.pipeline = PipelineCenter()


    self.stack.addWidget(
        self.pipeline
    )


except Exception as e:

    print(
        "V30 Pipeline加载失败:",
        e
    )


# V30 Pipeline Extension

try:

    from ui.pages.v30.pipeline_center import PipelineCenter


    self.pipeline = PipelineCenter()


    self.stack.addWidget(
        self.pipeline
    )


except Exception as e:

    print(
        "V30 Pipeline加载失败:",
        e
    )

