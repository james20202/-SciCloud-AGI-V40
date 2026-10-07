import json
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QComboBox,QTextEdit,QMessageBox,QSplitter
from core.storyboard_engine import storyboard_director
from core.director_plan import director_plan_engine

class StoryboardDirectorPage(QWidget):
    def __init__(self): super().__init__(); self.sb=None; self.build(); self.refresh()
    def build(self):
        root=QVBoxLayout(self); root.setContentsMargins(28,24,28,24); root.setSpacing(10)
        root.addWidget(QLabel('🎥 AI导演分镜系统',objectName='PageTitle'))
        root.addWidget(QLabel('把剧情转成可执行镜头：景别、机位、运动、构图、动作、表情、光线、节奏与转场统一保存。'))
        bar=QHBoxLayout(); self.plan_box=QComboBox(); bar.addWidget(self.plan_box,1)
        for text,fn in [('从导演计划生成分镜',self.create),('生成镜头 Prompt',self.make_prompt),('🔍连续性检查',self.check_continuity),('保存镜头',self.save_shot),('🔄刷新',self.refresh)]:
            b=QPushButton(text); b.clicked.connect(fn); bar.addWidget(b)
        root.addLayout(bar)
        split=QSplitter(); self.shot_list=QListWidget(); self.shot_list.currentRowChanged.connect(self.load_shot); split.addWidget(self.shot_list)
        self.editor=QTextEdit(); self.editor.setPlaceholderText('镜头 JSON'); split.addWidget(self.editor); split.setSizes([360,900]); root.addWidget(split,1)
        self.info=QLabel(); self.info.setObjectName('Muted'); root.addWidget(self.info)
    def refresh(self):
        self.plan_box.clear()
        plans=director_plan_engine.load_plans()
        for p in plans:self.plan_box.addItem(f"{p.get('plan_id')} · {p.get('title')}",p)
        self.shot_list.clear(); self.sb=(storyboard_director.list()[0] if storyboard_director.list() else None)
        if self.sb:
            for s in self.sb.get('shots',[]): self.shot_list.addItem(f"{s['id']} · {s.get('type')} · {s.get('shot_size')} · {s.get('rhythm')}")
            self.info.setText(f"{self.sb['storyboard_id']} · V{self.sb.get('version',1)} · {len(self.sb.get('shots',[]))} 镜头")
    def create(self):
        plan=self.plan_box.currentData()
        if not plan: QMessageBox.information(self,'提示','请先创建一个 AI 导演计划'); return
        self.sb=storyboard_director.create_from_plan(plan); self.refresh(); QMessageBox.information(self,'完成',f"已生成 {len(self.sb['shots'])} 个导演镜头")
    def load_shot(self,row):
        if not self.sb or row<0 or row>=len(self.sb['shots']): return
        self.editor.setPlainText(json.dumps(self.sb['shots'][row],ensure_ascii=False,indent=2))
    def save_shot(self):
        if not self.sb:return
        row=self.shot_list.currentRow()
        if row<0:return
        try:data=json.loads(self.editor.toPlainText())
        except Exception as e:QMessageBox.warning(self,'JSON错误',str(e));return
        self.sb=storyboard_director.update_shot(self.sb['storyboard_id'],row,data); self.refresh(); self.shot_list.setCurrentRow(row)
    def make_prompt(self):
        if not self.sb:return
        row=self.shot_list.currentRow()
        if row<0:return
        plan=self.plan_box.currentData(); rec=storyboard_director.build_prompt(self.sb['storyboard_id'],row,plan)
        if rec:self.editor.setPlainText(json.dumps(rec,ensure_ascii=False,indent=2)); self.info.setText(f"Prompt 已生成：{rec['prompt_id']} · 连续性约束 {len(rec.get('continuity_constraints',[]))} 条")

    def check_continuity(self):
        if not self.sb:return
        report=storyboard_director.check_continuity(self.sb['storyboard_id'])
        if not report:return
        self.info.setText(f"连续性评分：{report.get('score')} · 问题 {len(report.get('issues',[]))} · 提示 {len(report.get('warnings',[]))}")
        QMessageBox.information(self,'连续性检查',f"评分：{report.get('score')}\n问题：{len(report.get('issues',[]))}\n提示：{len(report.get('warnings',[]))}\n\n{chr(10).join(x.get('message','') for x in report.get('issues',[])[:5])}")
