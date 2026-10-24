from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame,QTextEdit,QLineEdit,QComboBox,QSpinBox,QListWidget,QMessageBox
from core.director_plan import director_plan_engine
from core.workflow_engine import workflow_engine

_ACTIVE_WORKERS=set()

class PlanWorker(QThread):
    plan_ready=Signal(object)
    plan_failed=Signal(str)
    def __init__(self, idea, title, duration, ratio):
        super().__init__()
        self.args=(idea,title,duration,ratio)
    def run(self):
        try:
            self.plan_ready.emit(director_plan_engine.create_plan(*self.args))
        except Exception as exc:
            self.plan_failed.emit(str(exc))


class DirectorPlanPage(QWidget):
    def __init__(self, initial_idea=''):
        super().__init__(); self.plan=None; self.initial_idea=initial_idea; self.worker=None; self.build()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(14)
        t=QLabel('🧠 AI导演计划'); t.setObjectName('PageTitle'); root.addWidget(t)
        s=QLabel('V40.1：把一句话创意转换成可执行的内容与生产计划。'); s.setObjectName('Muted'); root.addWidget(s)
        form=QFrame(); form.setObjectName('Hero'); fl=QVBoxLayout(form)
        self.title=QLineEdit(); self.title.setPlaceholderText('项目名称（可选）'); fl.addWidget(self.title)
        self.idea=QTextEdit(); self.idea.setPlaceholderText('输入创意，例如：60秒中式恐怖短剧，道士进入废弃凶宅，遇到红衣女鬼，结尾留下悬念。'); self.idea.setFixedHeight(100); self.idea.setPlainText(self.initial_idea); fl.addWidget(self.idea)
        row=QHBoxLayout(); self.duration=QSpinBox(); self.duration.setRange(10,600); self.duration.setValue(60); row.addWidget(QLabel('时长')); row.addWidget(self.duration); self.ratio=QComboBox(); self.ratio.addItems(['9:16','16:9','1:1']); row.addWidget(QLabel('画幅')); row.addWidget(self.ratio); row.addStretch(); self.generate_btn=QPushButton('✨ 生成导演计划'); self.generate_btn.setObjectName('Primary'); self.generate_btn.clicked.connect(self.generate); row.addWidget(self.generate_btn); self.queue_btn=QPushButton('🚀 进入生产队列'); self.queue_btn.setEnabled(False); self.queue_btn.clicked.connect(self.enqueue); row.addWidget(self.queue_btn); fl.addLayout(row); root.addWidget(form)
        self.summary=QLabel('等待生成'); self.summary.setObjectName('Muted'); root.addWidget(self.summary)
        self.tasks=QListWidget(); root.addWidget(self.tasks,1)
    def _validate_plan(self, plan):
        if not isinstance(plan, dict):
            raise ValueError('导演引擎返回的计划不是有效对象。')
        for key in ('intent','story','characters','scenes','shots','tasks'):
            if key not in plan or plan[key] is None:
                plan[key] = {} if key in ('intent','story') else []
        if not isinstance(plan['intent'], dict): plan['intent'] = {}
        if not isinstance(plan['story'], dict): plan['story'] = {}
        for key in ('characters','scenes','shots','tasks'):
            if not isinstance(plan[key], list):
                raise ValueError(f'导演计划字段 {key} 格式错误，应该是列表。')
        if not plan['shots']:
            raise ValueError('导演计划没有生成镜头，请修改创意后重试。')
        try:
            actual = round(sum(float(s.get('duration', 0)) for s in plan['shots']), 1)
        except (AttributeError, TypeError, ValueError):
            raise ValueError('镜头时长字段无效，请重新生成导演计划。')
        target = round(float(plan['intent'].get('duration_seconds', self.duration.value())), 1)
        if abs(actual-target) > 0.1:
            raise ValueError(f'镜头总时长为 {actual:g} 秒，与目标 {target:g} 秒不一致；计划未进入生产队列。')
        return plan
    def generate(self):
        idea=self.idea.toPlainText().strip()
        if not idea:
            QMessageBox.warning(self,'需要创意内容','请先输入一句话创意，再生成导演计划。')
            self.queue_btn.setEnabled(False); self.plan=None
            return
        if self.worker and self.worker.isRunning(): return
        self.plan=None; self.queue_btn.setEnabled(False); self.generate_btn.setEnabled(False)
        self.generate_btn.setText('正在生成…')
        self.summary.setText('正在生成导演计划；本机 Ollama 推理期间界面仍可操作。')
        worker=PlanWorker(idea,self.title.text().strip() or None,self.duration.value(),self.ratio.currentText())
        self.worker=worker; _ACTIVE_WORKERS.add(worker)
        worker.plan_ready.connect(self._on_plan_ready)
        worker.plan_failed.connect(self._on_plan_failed)
        worker.finished.connect(lambda w=worker: _ACTIVE_WORKERS.discard(w))
        worker.start()

    def _restore_generate_button(self):
        self.generate_btn.setEnabled(True); self.generate_btn.setText('✨ 生成导演计划')

    def _on_plan_ready(self, plan):
        self._restore_generate_button()
        try: plan=self._validate_plan(plan)
        except Exception as exc:
            self.plan=None; self.queue_btn.setEnabled(False); self.summary.setText('导演计划校验失败，未进入生产队列。')
            QMessageBox.warning(self,'导演计划校验失败',str(exc)); return
        self.plan=plan
        generation=plan.get('generation',{})
        mode='本地 Ollama' if generation.get('mode')=='local_ollama' else '本地规则兜底'
        self.summary.setText(f"{plan.get('title','未命名项目')}  ·  {plan['intent'].get('genre','原创短剧')}  ·  {len(plan['shots'])} 个镜头  ·  {len(plan['tasks'])} 个生产任务  ·  {sum(float(s.get('duration',0)) for s in plan['shots']):g} 秒  ·  {mode}")
        self.summary.setToolTip(generation.get('message','导演计划已生成'))
        self.tasks.clear()
        for task in plan['tasks']: self.tasks.addItem(f"{task.get('id','TASK')}   {task.get('name',task.get('type','生产任务'))}   ·   等待执行")
        self.queue_btn.setEnabled(True)

    def _on_plan_failed(self, message):
        self._restore_generate_button(); self.plan=None; self.queue_btn.setEnabled(False)
        self.summary.setText('导演计划生成失败，请检查创意或查看日志。')
        QMessageBox.warning(self,'导演计划生成失败',message)

    def enqueue(self):
        if not self.plan: return
        try:
            wf=workflow_engine.create_from_plan(self.plan)
            QMessageBox.information(self,'已进入生产队列',f"{wf['workflow_id']} 已建立。\n可执行任务：{sum(t.get('status')=='ready' for t in wf.get('tasks',[]))}")
        except Exception as exc:
            QMessageBox.warning(self,'进入生产队列失败',str(exc))
