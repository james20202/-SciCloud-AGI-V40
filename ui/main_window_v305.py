
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget
)


from ui.pages.production_dashboard import ProductionDashboard
from ui.pages.project_matrix import ProjectMatrix
from ui.pages.asset_center import AssetCenter
from ui.pages.ai_center import AICenter
from ui.pages.batch_center import BatchCenter
from ui.pages.video_center import VideoCenter
from ui.pages.publish_center import PublishCenter


try:
    from ui.pages.v30.pipeline_center import PipelineCenter
except Exception:
    PipelineCenter = None



class MainWindow(QMainWindow):


    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "⚔ 仙剧工坊 V30 AI全自动生产系统"
        )

        self.resize(
            1400,
            850
        )

        self.init_ui()



    def init_ui(self):

        root = QWidget()

        self.setCentralWidget(root)


        layout = QHBoxLayout(root)


        menu = QVBoxLayout()


        self.stack = QStackedWidget()



        self.pages = {}



        self.add_page(
            "⚔ AI生产驾驶舱",
            ProductionDashboard()
        )


        self.add_page(
            "📚 项目矩阵",
            ProjectMatrix()
        )


        self.add_page(
            "📦 项目资产中心",
            AssetCenter()
        )


        self.add_page(
            "🧠 AI中心",
            AICenter()
        )


        self.add_page(
            "🚀 AI批量生产",
            BatchCenter()
        )


        if PipelineCenter:

            self.add_page(
                "🚀 AI自动流水线",
                PipelineCenter()
            )


        self.add_page(
            "🎬 视频中心",
            VideoCenter()
        )


        self.add_page(
            "📤 发布中心",
            PublishCenter()
        )



        for name,page in self.pages.items():

            btn = QPushButton(name)

            btn.clicked.connect(

                lambda checked=False,
                p=page:

                self.stack.setCurrentWidget(p)

            )

            menu.addWidget(btn)



        menu.addStretch()



        layout.addLayout(
            menu,
            1
        )


        layout.addWidget(
            self.stack,
            5
        )



    def add_page(
        self,
        name,
        page
    ):

        self.pages[name]=page

        self.stack.addWidget(page)



