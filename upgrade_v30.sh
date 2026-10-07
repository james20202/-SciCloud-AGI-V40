#!/bin/bash

echo "================================"
echo "仙剧工坊 V30 一键升级系统"
echo "================================"


ROOT=$(pwd)

DATE=$(date +%Y%m%d_%H%M)

BACKUP="backup_v30_$DATE"


echo "当前目录:"
echo $ROOT


echo "开始备份..."


mkdir -p "$BACKUP"


cp -r core "$BACKUP/"
cp -r ui "$BACKUP/"

cp projects.json "$BACKUP/" 2>/dev/null
cp production.json "$BACKUP/" 2>/dev/null


echo "备份完成:"
echo $BACKUP



echo "创建 V30 目录结构..."


mkdir -p core/v30
mkdir -p ui/pages/v30
mkdir -p data/v30



echo "目录创建完成"


echo "开始升级核心模块..."

cat > core/v30/pipeline_manager.py <<'PY'

import json
import os
import time


class PipelineManager:


    def __init__(self):

        self.file="data/v30/pipeline.json"

        self.tasks={}

        self.load()



    def load(self):

        if os.path.exists(self.file):

            with open(
                self.file,
                "r",
                encoding="utf-8"
            ) as f:

                self.tasks=json.load(f)



    def save(self):

        os.makedirs(
            "data/v30",
            exist_ok=True
        )


        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                self.tasks,
                f,
                ensure_ascii=False,
                indent=2
            )



    def create(
        self,
        project,
        episode
    ):


        key=f"{project}_{episode}"


        self.tasks[key]={

            "剧本":"等待",

            "角色":"等待",

            "分镜":"等待",

            "素材":"等待",

            "视频":"等待"

        }


        self.save()



    def run(
        self,
        project,
        episode
    ):


        key=f"{project}_{episode}"


        if key not in self.tasks:

            self.create(
                project,
                episode
            )


        for step in self.tasks[key]:

            self.tasks[key][step]="生产中"

            self.save()


            time.sleep(0.2)


            self.tasks[key][step]="完成"

            self.save()



        return True



pipeline_manager=PipelineManager()

PY



echo "V30核心模块完成"

cat > core/v30/script_reader.py <<'PY'

import os


class ScriptReader:


    def read(self, path):

        if not os.path.exists(path):

            return ""


        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read()



    def analyze(self, text):

        return {

            "length":len(text),

            "scenes":text.count("场"),

            "characters":text.count("：")

        }



script_reader=ScriptReader()

PY



cat > core/v30/storyboard_engine.py <<'PY'


class StoryboardEngine:


    def create(self, script):


        return [

            {

                "shot":1,

                "content":script[:100]

            }

        ]



storyboard_engine=StoryboardEngine()

PY



cat > core/v30/character_engine.py <<'PY'


class CharacterEngine:


    def analyze(self, script):


        return {


            "角色":[],

            "状态":"完成"

        }



character_engine=CharacterEngine()

PY



cat > core/v30/asset_engine.py <<'PY'


class AssetEngine:


    def create_task(
        self,
        storyboard
    ):


        return {


            "素材任务":
            len(storyboard),

            "状态":
            "等待生成"

        }



asset_engine=AssetEngine()

PY



cat > core/v30/video_engine.py <<'PY'


class VideoEngine:


    def compose(
        self,
        assets
    ):


        return {


            "video":
            "output/video/final.mp4",

            "status":
            "完成"

        }



video_engine=VideoEngine()

PY



echo "V30 AI生产核心模块完成"

cat > ui/pages/v30/pipeline_center.py <<'PY'

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit
)


from core.v30.pipeline_manager import pipeline_manager



class PipelineCenter(QWidget):


    def __init__(self):

        super().__init__()

        self.init_ui()



    def init_ui(self):

        layout = QVBoxLayout()



        title = QLabel(
            "🚀 V30 AI自动生产流水线"
        )

        title.setStyleSheet(
            "font-size:26px;font-weight:bold;"
        )


        layout.addWidget(title)



        self.project = QLineEdit()

        self.project.setPlaceholderText(
            "项目名称"
        )

        layout.addWidget(
            self.project
        )



        self.episode = QLineEdit()

        self.episode.setPlaceholderText(
            "集数，例如001"
        )

        layout.addWidget(
            self.episode
        )



        create = QPushButton(
            "📋 创建生产任务"
        )


        create.clicked.connect(
            self.create_task
        )


        layout.addWidget(
            create
        )



        run = QPushButton(
            "🚀 执行AI流水线"
        )


        run.clicked.connect(
            self.run_task
        )


        layout.addWidget(
            run
        )



        self.output = QTextEdit()


        layout.addWidget(
            self.output
        )


        self.setLayout(
            layout
        )



    def create_task(self):


        pipeline_manager.create(

            self.project.text(),

            self.episode.text()

        )


        self.show_status()



    def run_task(self):


        pipeline_manager.run(

            self.project.text(),

            self.episode.text()

        )


        self.show_status()



    def show_status(self):


        self.output.clear()


        data = pipeline_manager.get_status()


        self.output.append(

            str(data)

        )

PY



echo "V30 UI流水线中心完成"

cat >> ui/main_window.py <<'PY'

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

PY



echo "V30主窗口接入完成"
echo "备份当前主窗口..."

cp ui/main_window.py ui/main_window_before_v305.py


echo "准备生成 V30.5 主窗口..."

cat > ui/main_window_v305.py <<'PY'

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



PY



cp ui/main_window.py ui/main_window_v305_backup.py

cp ui/main_window_v305.py ui/main_window.py


echo "V30.5 主窗口整体替换完成"

