from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QProgressBar,QComboBox,QMessageBox
from core.workflow_engine import workflow_engine, STATUS_READY, STATUS_RUNNING, STATUS_DONE, STATUS_FAILED
from core.execution_engine import execution_engine
from core.auto_director import auto_director
from core.qc_engine import qc_engine
from core.director_loop import director_loop

class WorkflowQueuePage(QWidget):
    def __init__(self, workflow_id=None):
        super().__init__(); self.workflow_id=workflow_id; self.workflow=None; self.build(); self.refresh_workflows()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        title=QLabel('⚙ 生产工作流'); title.setObjectName('PageTitle'); root.addWidget(title)
        root.addWidget(QLabel('V40.10：导演计划进入可暂停、可恢复、可重试，并支持视觉审核与自动修复的生产队列。'))
        bar=QHBoxLayout(); self.selector=QComboBox(); bar.addWidget(self.selector,1)
        for text,fn in [('⚡ 执行任务',self.execute),('🤖 AI自动执行',self.auto_run),('🔍 AI审核',self.qc),('🧭 导演闭环',self.director_loop),('■ 停止自动执行',self.stop_auto),('▶ 开始任务',self.start),('✓ 手动完成',self.complete),('↻ 重试',self.retry),('Ⅱ 暂停',self.pause),('▶ 恢复',self.resume)]:
            b=QPushButton(text); b.clicked.connect(fn); bar.addWidget(b)
        root.addLayout(bar)
        self.progress=QProgressBar(); root.addWidget(self.progress)
        self.status=QLabel('等待工作流'); root.addWidget(self.status)
        self.tasks=QListWidget(); root.addWidget(self.tasks,1)
        self.selector.currentIndexChanged.connect(self.select_workflow)
    def refresh_workflows(self, workflow_id=None):
        self.selector.blockSignals(True); self.selector.clear(); wfs=workflow_engine.list_workflows()
        for wf in wfs: self.selector.addItem(f"{wf['workflow_id']} · {wf['title']}",wf['workflow_id'])
        self.selector.blockSignals(False)
        if workflow_id:
            idx=self.selector.findData(workflow_id)
            if idx>=0:self.selector.setCurrentIndex(idx)
        elif wfs:self.selector.setCurrentIndex(0)
        self.select_workflow(self.selector.currentIndex())
    def select_workflow(self,_):
        wid=self.selector.currentData()
        if not wid:return
        try:self.workflow=workflow_engine.load(wid)
        except Exception:return
        self.render()
    def render(self):
        if not self.workflow:return
        self.progress.setValue(workflow_engine.progress(self.workflow)); self.status.setText(f"{self.workflow['status']} · {self.workflow['workflow_id']} · 可执行任务 {sum(t['status']==STATUS_READY for t in self.workflow['tasks'])}")
        self.tasks.clear()
        for t in self.workflow['tasks']:
            dep=','.join(t.get('depends_on',[])) or '无依赖'
            err=f" · {t['error']}" if t.get('error') else ''
            self.tasks.addItem(f"{t['id']}  {t['name']}  [{t['status']}]  {t.get('progress',0)}%  · 依赖: {dep}{err}")
    def selected_id(self):
        item=self.tasks.currentRow(); return self.workflow['tasks'][item]['id'] if self.workflow and item>=0 else None
    def start(self):
        tid=self.selected_id();
        if tid is not None:self.workflow=workflow_engine.start_task(self.workflow_id or self.workflow['workflow_id'],tid); self.render()
    def complete(self):
        tid=self.selected_id();
        if tid is not None:self.workflow=workflow_engine.complete_task(self.workflow_id or self.workflow['workflow_id'],tid); self.render()
    def execute(self):
        tid=self.selected_id()
        if tid is None or not self.workflow:return
        result=execution_engine.execute(self.workflow['workflow_id'],tid)
        QMessageBox.information(self,'任务执行',result.get('message',''))
        self.workflow=workflow_engine.load(self.workflow['workflow_id']); self.render()
    def auto_run(self):
        if not self.workflow:return
        result=auto_director.run(self.workflow['workflow_id'], max_steps=50)
        QMessageBox.information(self,'AI导演自动执行',result.get('message',''))
        self.workflow=workflow_engine.load(self.workflow['workflow_id']); self.render()
    def qc(self):
        if not self.workflow:return
        result=qc_engine.inspect_workflow(self.workflow['workflow_id'])
        QMessageBox.information(self,'AI导演审核',result.get('message',''))
        self.workflow=workflow_engine.load(self.workflow['workflow_id']); self.render()

    def director_loop(self):
        if not self.workflow:return
        result=director_loop.run_review_cycle(self.workflow['workflow_id'])
        QMessageBox.information(self,'AI导演闭环',result.get('message',''))
        self.workflow=workflow_engine.load(self.workflow['workflow_id']); self.render()

    def stop_auto(self):
        auto_director.stop()
        self.status.setText('正在停止自动执行…')
    def retry(self):
        tid=self.selected_id();
        if tid is not None:self.workflow=workflow_engine.retry_task(self.workflow['workflow_id'],tid); self.render()
    def pause(self):
        if self.workflow:self.workflow=workflow_engine.pause(self.workflow['workflow_id']); self.render()
    def resume(self):
        if self.workflow:self.workflow=workflow_engine.resume(self.workflow['workflow_id']); self.render()
