from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QFormLayout, QLineEdit, QPlainTextEdit
from core.model_hub import model_hub
from core.production_engine import production_engine
from core.comfyui_runner import comfyui_runner
from core.asset_manager import asset_manager
from core.config import OUTPUT_DIR
import shutil, json, os


class ProductionFactoryPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 26)
        root.setSpacing(14)
        title = QLabel('🎞 本地生产工厂')
        title.setObjectName('PageTitle')
        root.addWidget(title)
        desc = QLabel('本地优先：ComfyUI + SD1.5 真正出图。没有本地模型或服务时明确阻塞，不伪造结果。')
        desc.setObjectName('SubBrand')
        root.addWidget(desc)

        box = QGroupBox('本地能力')
        form = QFormLayout(box)
        self.info = QPlainTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(150)
        form.addRow(self.info)
        root.addWidget(box)

        image_box = QGroupBox('AI 自动出图 · SD1.5')
        image_form = QFormLayout(image_box)
        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText('例如：中式修仙少年站在云海山巅，古风长袍，电影感光影……')
        self.negative = QLineEdit()
        self.negative.setText('low quality, blurry, deformed hands, extra fingers, watermark, text')
        image_form.addRow('正向 Prompt', self.prompt)
        image_form.addRow('反向 Prompt', self.negative)
        row = QHBoxLayout()
        test = QPushButton('检查 ComfyUI')
        test.setObjectName('Secondary')
        test.clicked.connect(self.check_comfy)
        row.addWidget(test)
        gen = QPushButton('▶ 一键生成真实图片')
        gen.setObjectName('Primary')
        gen.clicked.connect(self.generate_image)
        row.addWidget(gen)
        image_form.addRow(row)
        root.addWidget(image_box)

        runbox = QGroupBox('生产运行')
        rf = QFormLayout(runbox)
        self.plan = QLineEdit()
        self.plan.setPlaceholderText('PLAN-...')
        rf.addRow('计划 ID', self.plan)
        start = QPushButton('创建生产运行')
        start.setObjectName('Secondary')
        start.clicked.connect(self.start)
        rf.addRow(start)
        root.addWidget(runbox)
        root.addStretch()
        self.refresh()

    def refresh(self):
        rows = [f'FFmpeg: {shutil.which("ffmpeg") or "未找到"}', f'FFprobe: {shutil.which("ffprobe") or "未找到"}']
        for mid in ['MODEL-COMFYUI', 'MODEL-LOCAL-TTS']:
            m = model_hub.get(mid)
            rows.append(f"{m.get('name') if m else mid}: {'已启用' if m and m.get('enabled') else '未启用'}")
        self.info.setPlainText('\n'.join(rows))

    def check_comfy(self):
        self.info.append('\n' + json.dumps(comfyui_runner.test(), ensure_ascii=False, indent=2))

    def generate_image(self):
        prompt = self.prompt.text().strip()
        if not prompt:
            self.info.append('\n请先输入 Prompt。')
            return
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        target = os.path.join(OUTPUT_DIR, 'comfyui', 'SciCloud_V40_image.png')
        result = comfyui_runner.generate_image(prompt, self.negative.text().strip(), destination=target,
                                               width=512, height=512, steps=15, cfg=7.0,
                                               filename_prefix='SciCloud_V40')
        if result.get('success') and result.get('path'):
            asset = asset_manager.register_result_file(result['path'], asset_type='image', name='ComfyUI SD1.5 出图', metadata={
                'engine': 'ComfyUI', 'prompt_id': result.get('prompt_id'), 'prompt': prompt,
                'negative_prompt': self.negative.text().strip(), 'size': '512x512', 'steps': 15, 'cfg': 7.0
            })
            result['asset'] = asset
        self.info.append('\n' + json.dumps(result, ensure_ascii=False, indent=2))

    def start(self):
        d = production_engine.start_run(self.plan.text().strip() or 'UNBOUND', '未命名生产')
        self.info.append('\n生产运行已创建：' + d['run_id'])
