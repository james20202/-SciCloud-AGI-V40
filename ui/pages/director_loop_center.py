from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QPlainTextEdit,QProgressBar
from core.workflow_engine import workflow_engine
from core.director_loop import director_loop

class DirectorLoopCenter(QWidget):
    def __init__(self):
        super().__init__(); self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(12)
        t=QLabel('🧭 AI导演闭环'); t.setObjectName('PageTitle'); root.addWidget(t)
        root.addWidget(QLabel('V40.20：审核 → 导演决策 → 联动修复计划 → 任务重排 → 再审核。视觉判断只使用真实 Vision 模型。'))
        bar=QHBoxLayout(); self.selector=QComboBox(); bar.addWidget(self.selector,1); b=QPushButton('🧠 执行导演审核闭环'); b.clicked.connect(self.run); bar.addWidget(b); root.addLayout(bar)
        self.progress=QProgressBar(); root.addWidget(self.progress)
        self.output=QPlainTextEdit(); self.output.setReadOnly(True); root.addWidget(self.output,1)
    def refresh(self):
        self.selector.clear()
        for wf in workflow_engine.list_workflows(): self.selector.addItem(f"{wf['workflow_id']} · {wf['title']}",wf['workflow_id'])
    def run(self):
        wid=self.selector.currentData()
        if not wid:return
        r=director_loop.run_review_cycle(wid)
        self.progress.setValue(int(r.get('story',{}).get('score',0)))
        self.output.setPlainText(self._pretty(r))
    def _pretty(self,r):
        lines=[f"状态：{r.get('stage')}",f"结果：{r.get('message')}"]
        if r.get('story'): lines.append(f"故事级评分：{r['story'].get('score')} / 100")
        if r.get('decision'): lines.append(f"导演决策：{r['decision'].get('decision_id')}\n问题类别：{', '.join(r['decision'].get('targets',[])) or '无'}\n联动修复：{r['decision'].get('cascade')}" )
        if r.get('repair_plan'): lines.append(f"修复计划：{r['repair_plan'].get('repair_plan_id')}\n重排任务：{', '.join(r['repair_plan'].get('requeued_types',[]))}")
        return '\n\n'.join(lines)
