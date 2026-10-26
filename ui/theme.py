THEME = """
QMainWindow, QWidget { background:#05070d; color:#eef2f7; font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC",sans-serif; font-size:13px; }

/* ===== 顶部栏 ===== */
QFrame#Topbar { background:#080b14; border-bottom:1px solid #1e2a3a; }
QLabel#Brand { font-size:18px; font-weight:800; color:#f4f8ff; }
QLabel#BrandMark { font-size:22px; font-weight:900; color:#22d3ee; }
QLabel#TopSub { color:#8b98ab; font-size:11px; }
QLabel#TopMuted, QLabel#Muted { color:#8b98ab; font-size:11px; }
QLabel#StatusPill { background:rgba(34,211,238,0.12); border:1px solid #155e75; border-radius:12px; padding:6px 11px; color:#67e8f9; font-size:11px; }
QToolButton#TopAction { background:#0d1420; border:1px solid #223349; border-radius:9px; color:#cbd5e1; font-size:12px; padding:6px 12px; }
QToolButton#TopAction:hover { background:#142238; border:1px solid #22d3ee; color:#ffffff; }
QLabel#StorageChip { background:#0d1420; border:1px solid #223349; border-radius:9px; padding:6px 11px; color:#94a3b8; font-size:11px; }
QLabel#UserChip { background:#0d1420; border:1px solid #223349; border-radius:9px; padding:5px 10px; color:#e2e8f0; font-size:12px; }
QLabel#UserAvatar { background:rgba(34,211,238,0.16); border:1px solid #22d3ee; border-radius:11px; color:#a5f3fc; font-weight:800; padding:4px 8px; font-size:11px; }

/* ===== 左侧导航（只换样式，不增按钮） ===== */
QFrame#Dock { background:rgba(8,11,20,0.92); border:1px solid #1e2a3a; border-radius:16px; }
QToolButton#NavButton { background:transparent; border:1px solid transparent; border-radius:11px; color:#7d8ca3; font-size:12px; padding:8px 6px; }
QToolButton#NavButton:hover { background:#111a2b; color:#e2e8f0; border:1px solid #223349; }
QToolButton#NavButton:checked { background:rgba(34,211,238,0.16); color:#a5f3fc; border:1px solid #22d3ee; }
QLabel#DockFooterBrand { color:#cbd5e1; font-size:12px; font-weight:750; }
QLabel#DockFooterSub { color:#64748b; font-size:10px; }

/* ===== 驾驶舱透明内容层（透出背景插画） ===== */
QWidget#DashContent { background:transparent; }

/* ===== 页面与卡片 ===== */
QLabel#PageTitle { font-size:26px; font-weight:850; color:#f8fafc; }
QLabel#SubBrand { color:#cbd5e1; font-size:12px; }
QLabel#HeroTitle { font-size:29px; font-weight:850; color:#ffffff; }
QLabel#HeroSub { color:#cbd5e1; font-size:12px; }
QFrame#Hero { background:rgba(11,16,28,0.85); border:1px solid #223349; border-radius:18px; }
QFrame#Card { background:rgba(11,16,28,0.82); border:1px solid #1e2a3a; border-radius:15px; }
QFrame#PanelCard { background:rgba(11,16,28,0.85); border:1px solid #1e2a3a; border-radius:15px; }
QFrame#MiniCard { background:rgba(13,20,32,0.85); border:1px solid #1e2a3a; border-radius:13px; }
QFrame#TemplateCard { background:rgba(13,20,32,0.85); border:1px solid #223349; border-radius:13px; }
QFrame#TemplateCard:hover { background:#12203a; border:1px solid #22d3ee; }
QFrame#PipelineStep { background:rgba(13,20,32,0.85); border:1px solid #1e2a3a; border-radius:12px; }
QLabel#SectionTitle { font-size:15px; font-weight:750; color:#f1f5f9; }
QLabel#BigValue { font-size:24px; font-weight:850; color:#f8fafc; }
QLabel#Tag { background:#0d1420; border:1px solid #223349; border-radius:10px; padding:5px 9px; color:#94a3b8; font-size:10px; }
QLabel#TagActive { background:rgba(34,211,238,0.16); border:1px solid #22d3ee; border-radius:10px; padding:5px 9px; color:#a5f3fc; font-size:10px; }
QLabel#Ok { color:#34d399; }
QLabel#Warn { color:#fbbf24; }

/* ===== 按钮 ===== */
QPushButton#Primary { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22d3ee,stop:1 #818cf8); border:0; border-radius:11px; padding:11px 18px; color:#04121a; font-weight:800; }
QPushButton#Primary:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #67e8f9,stop:1 #a5b4fc); }
QPushButton#Secondary { background:#0d1420; border:1px solid #223349; border-radius:10px; padding:9px 13px; color:#dbe7f3; }
QPushButton#Secondary:hover { background:#142238; border:1px solid #22d3ee; }
QPushButton#QuickBtn { background:#0d1420; border:1px solid #223349; border-radius:10px; padding:9px 14px; color:#dbe7f3; font-size:12px; font-weight:600; }
QPushButton#QuickBtn:hover { background:#142238; border:1px solid #22d3ee; color:#a5f3fc; }

/* ===== 输入控件 ===== */
QTextEdit, QPlainTextEdit, QLineEdit, QComboBox, QListWidget, QTableWidget { background:#070c16; border:1px solid #223349; border-radius:10px; padding:9px; color:#eef2f7; }
QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus { border:1px solid #22d3ee; }

/* ===== 进度条 ===== */
QProgressBar { background:#111a2b; border:0; border-radius:5px; height:8px; text-align:center; color:transparent; }
QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22d3ee,stop:1 #818cf8); border-radius:5px; }

QScrollArea { border:0; background:transparent; }
QMenu { background:#0b101c; border:1px solid #223349; padding:6px; }
QMenu::item { padding:8px 18px; border-radius:7px; }
QMenu::item:selected { background:#142238; }
QToolTip { background:#0d1420; border:1px solid #22d3ee; color:#eef2f7; padding:6px; }
"""
