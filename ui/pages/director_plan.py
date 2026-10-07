from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame,QTextEdit,QLineEdit,QComboBox,QSpinBox,QListWidget,QProgressBar,QMessageBox
from core.director_plan import director_plan_engine
from core.workflow_engine import workflow_engine

class DirectorPlanPage(QWidget):
    def __init__(self, initial_idea=''):
        super().__init__(); self.plan=None; self.initial_idea=initial_idea; self.build()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(14)
        t=QLabel('🧠 AI导演计划'); t.setObjectName('PageTitle'); root.addWidget(t)
        s=QLabel('V40.1：把一句话创意转换成可执行的内容与生产计划。'); s.setObjectName('Muted'); root.addWidget(s)
        form=QFrame(); form.setObjectName('Hero'); fl=QVBoxLayout(form)
        self.title=QLineEdit(); self.title.setPlaceholderText('项目名称（可选）'); fl.addWidget(self.title)
        self.idea=QTextEdit(); self.idea.setPlaceholderText('输入创意，例如：60秒中式恐怖短剧，道士进入废弃凶宅，遇到红衣女鬼，结尾留下悬念。'); self.idea.setFixedHeight(100); self.idea.setPlainText(self.initial_idea); fl.addWidget(self.idea)
        row=QHBoxLayout(); self.duration=QSpinBox(); self.duration.setRange(10,600); self.duration.setValue(60); row.addWidget(QLabel('时长')); row.addWidget(self.duration); self.ratio=QComboBox(); self.ratio.addItems(['9:16','16:9','1:1']); row.addWidget(QLabel('画幅')); row.addWidget(self.ratio); row.addStretch(); btn=QPushButton('✨ 生成导演计划'); btn.setObjectName('Primary'); btn.clicked.connect(self.generate); row.addWidget(btn); self.queue_btn=QPushButton('🚀 进入生产队列'); self.queue_btn.setEnabled(False); self.queue_btn.clicked.connect(self.enqueue); row.addWidget(self.queue_btn); fl.addLayout(row); root.addWidget(form)
        self.summary=QLabel('等待生成'); self.summary.setObjectName('Muted'); root.addWidget(self.summary)
        self.tasks=QListWidget(); root.addWidget(self.tasks,1)
    def generate(self):
        self.plan=director_plan_engine.create_plan(self.idea.toPlainText(),self.title.text().strip() or None,self.duration.value(),self.ratio.currentText())
        self.summary.setText(f"{self.plan['title']}  ·  {self.plan['intent']['genre']}  ·  {len(self.plan['shots'])} 个镜头  ·  {len(self.plan['tasks'])} 个生产任务")
        self.tasks.clear()
        for task in self.plan['tasks']:
            self.tasks.addItem(f"{task['id']}   {task['name']}   ·   等待执行")
        self.queue_btn.setEnabled(True)

    def enqueue(self):
        if not self.plan: return
        wf=workflow_engine.create_from_plan(self.plan)
        QMessageBox.information(self,'已进入生产队列',f"{wf['workflow_id']} 已建立。\n可执行任务：{sum(t['status']=='ready' for t in wf['tasks'])}")
