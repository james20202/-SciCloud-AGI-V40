THEME = """
QMainWindow, QWidget { background:#08090c; color:#f1f0ec; font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC",sans-serif; font-size:13px; }

/* ===== 顶部栏 ===== */
QFrame#Topbar { background:#0a0b0f; border-bottom:1px solid #22242b; }
QLabel#Brand { font-size:18px; font-weight:800; color:#f7f6f2; }
QLabel#BrandMark { font-size:22px; font-weight:900; color:#dccb8f; }
QLabel#TopSub { color:#8c8e96; font-size:11px; }
QLabel#TopMuted, QLabel#Muted { color:#8a8c94; font-size:11px; }
QLabel#StatusPill { background:#101f17; border:1px solid #2c5a3f; border-radius:12px; padding:6px 11px; color:#8fd6ae; font-size:11px; }
QToolButton#TopAction { background:#121318; border:1px solid #2a2c33; border-radius:9px; color:#cfccc2; font-size:12px; padding:6px 12px; }
QToolButton#TopAction:hover { background:#1c1d23; color:#ffffff; }
QLabel#StorageChip { background:#14151a; border:1px solid #33353d; border-radius:9px; padding:6px 11px; color:#9aa0a8; font-size:11px; }
QLabel#UserChip { background:#17181d; border:1px solid #33353d; border-radius:9px; padding:5px 10px; color:#e6e3da; font-size:12px; }
QLabel#UserAvatar { background:#23251f; border:1px solid #574e33; border-radius:11px; color:#f1dfb0; font-weight:800; padding:4px 8px; font-size:11px; }

/* ===== 左侧导航 ===== */
QFrame#Dock { background:rgba(11,12,16,0.92); border:1px solid #202228; border-radius:16px; }
QToolButton#NavButton { background:transparent; border:1px solid transparent; border-radius:11px; color:#7c7e85; font-size:12px; padding:8px 6px; }
QToolButton#NavButton:hover { background:#17181d; color:#e9e7e0; }
QToolButton#NavButton:checked { background:#251f12; color:#f1dfb0; border:1px solid #5a4b2a; }
QLabel#DockFooterBrand { color:#cfcbc0; font-size:12px; font-weight:750; }
QLabel#DockFooterSub { color:#6f727a; font-size:10px; }

/* ===== 驾驶舱透明内容层（透出背景插画） ===== */
QWidget#DashContent { background:transparent; }

/* ===== 页面与卡片 ===== */
QLabel#PageTitle { font-size:26px; font-weight:850; color:#f7f5ef; }
QLabel#SubBrand { color:#c9c6bd; font-size:12px; }
QLabel#HeroTitle { font-size:29px; font-weight:850; color:#fffdf7; }
QLabel#HeroSub { color:#c9c6bd; font-size:12px; }
QFrame#Hero { background:rgba(13,14,18,0.80); border:1px solid #3a3b44; border-radius:18px; }
QFrame#Card { background:rgba(16,17,21,0.82); border:1px solid #24252b; border-radius:15px; }
QFrame#PanelCard { background:rgba(14,15,19,0.85); border:1px solid #272930; border-radius:15px; }
QFrame#MiniCard { background:rgba(17,18,22,0.85); border:1px solid #26272d; border-radius:13px; }
QFrame#TemplateCard { background:rgba(18,19,24,0.85); border:1px solid #2a2c34; border-radius:13px; }
QFrame#TemplateCard:hover { background:#1a1b20; border:1px solid #4a4030; }
QFrame#PipelineStep { background:rgba(18,19,24,0.85); border:1px solid #272930; border-radius:12px; }
QLabel#SectionTitle { font-size:15px; font-weight:750; color:#f1efe9; }
QLabel#BigValue { font-size:24px; font-weight:850; color:#f6f3ea; }
QLabel#Tag { background:#17181c; border:1px solid #303139; border-radius:10px; padding:5px 9px; color:#aaa9a4; font-size:10px; }
QLabel#TagActive { background:#29251d; border:1px solid #5c5035; border-radius:10px; padding:5px 9px; color:#e7d5a8; font-size:10px; }
QLabel#Ok { color:#9ad3b3; }
QLabel#Warn { color:#e1c178; }

/* ===== 按钮 ===== */
QPushButton#Primary { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #c6a85f,stop:1 #8d7440); border:0; border-radius:11px; padding:11px 18px; color:#16130d; font-weight:800; }
QPushButton#Primary:hover { background:#d7bb73; }
QPushButton#Secondary { background:#15161a; border:1px solid #303139; border-radius:10px; padding:9px 13px; color:#d5d2c8; }
QPushButton#Secondary:hover { background:#1d1e23; }
QPushButton#QuickBtn { background:#16171c; border:1px solid #2e3038; border-radius:10px; padding:9px 14px; color:#d8d4c9; font-size:12px; font-weight:600; }
QPushButton#QuickBtn:hover { background:#1e2026; border:1px solid #4a4030; color:#f1dfb0; }

/* ===== 输入控件 ===== */
QTextEdit, QPlainTextEdit, QLineEdit, QComboBox, QListWidget, QTableWidget { background:#0d0e12; border:1px solid #292a30; border-radius:10px; padding:9px; color:#eeece6; }
QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus { border:1px solid #77663d; }

/* ===== 进度条 ===== */
QProgressBar { background:#191a1e; border:0; border-radius:5px; height:8px; text-align:center; color:transparent; }
QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #b79b58,stop:1 #d5bf80); border-radius:5px; }

QScrollArea { border:0; background:transparent; }
QMenu { background:#111216; border:1px solid #303139; padding:6px; }
QMenu::item { padding:8px 18px; border-radius:7px; }
QMenu::item:selected { background:#24252a; }
QToolTip { background:#17181c; border:1px solid #3a3b42; color:#eeece6; padding:6px; }
"""
