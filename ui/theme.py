"""Modern tech theme for SciCloud AGI V40.

Deep dark background with a cyan/blue primary accent and a violet
secondary. This file only changes appearance: every object name used by
the existing pages is preserved, so no page logic has to change.
"""

THEME = """
/* ===== Base ===== */
QMainWindow, QWidget { background:#070b14; color:#e6edf7; font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC",sans-serif; font-size:13px; }

/* ===== Topbar ===== */
QFrame#Topbar { background:#0a101f; border-bottom:1px solid #1e2c4a; }
QLabel#Brand { font-size:18px; font-weight:800; color:#f2f7ff; }
QLabel#BrandMark { font-size:22px; font-weight:900; color:#22d3ee; }
QLabel#TopSub { color:#8b98b0; font-size:11px; }
QLabel#TopMuted, QLabel#Muted { color:#8b98b0; font-size:11px; }
QLabel#StatusPill { background:#08222e; border:1px solid #155e75; border-radius:12px; padding:6px 11px; color:#67e8f9; font-size:11px; }
QToolButton#TopAction { background:#101a2e; border:1px solid #223354; border-radius:9px; color:#c7d3e8; font-size:12px; padding:6px 12px; }
QToolButton#TopAction:hover { background:#16233f; color:#ffffff; border:1px solid #22d3ee; }
QLabel#StorageChip { background:#101a2e; border:1px solid #223354; border-radius:9px; padding:6px 11px; color:#9fb0cc; font-size:11px; }
QLabel#UserChip { background:#101a2e; border:1px solid #223354; border-radius:9px; padding:5px 10px; color:#e6edf7; font-size:12px; }
QLabel#UserAvatar { background:#0e2a3d; border:1px solid #22d3ee; border-radius:11px; color:#67e8f9; font-weight:800; padding:4px 8px; font-size:11px; }

/* ===== Left navigation ===== */
QFrame#Dock { background:rgba(10,16,31,0.95); border:1px solid #1e2c4a; border-radius:16px; }
QToolButton#NavButton { background:transparent; border:1px solid transparent; border-radius:11px; color:#8b98b0; font-size:12px; padding:8px 6px; }
QToolButton#NavButton:hover { background:#12203a; color:#f2f7ff; border:1px solid #223354; }
QToolButton#NavButton:checked { background:#0e2a3d; color:#67e8f9; border:1px solid #22d3ee; }
QLabel#NavSection { color:#5b7aa6; font-size:10px; font-weight:700; padding:10px 6px 2px 6px; }
QToolButton#NavSubButton { background:transparent; border:1px solid transparent; border-radius:9px; color:#aebbd4; font-size:12px; padding:7px 10px; text-align:left; }
QToolButton#NavSubButton:hover { background:#12203a; color:#ffffff; border:1px solid #223354; }
QToolButton#NavSubButton:checked { background:#0e2a3d; color:#67e8f9; border:1px solid #22d3ee; }
QLabel#DockFooterBrand { color:#c7d3e8; font-size:12px; font-weight:750; }
QLabel#DockFooterSub { color:#5b7aa6; font-size:10px; }

/* ===== Dashboard transparent layer ===== */
QWidget#DashContent { background:transparent; }

/* ===== Pages and cards ===== */
QLabel#PageTitle { font-size:26px; font-weight:850; color:#f2f7ff; }
QLabel#SubBrand { color:#aebbd4; font-size:12px; }
QLabel#HeroTitle { font-size:29px; font-weight:850; color:#ffffff; }
QLabel#HeroSub { color:#aebbd4; font-size:12px; }
QFrame#Hero { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0e2a3d,stop:1 #1a1440); border:1px solid #22406e; border-radius:18px; }
QFrame#Card { background:rgba(15,23,42,0.92); border:1px solid #223354; border-radius:15px; }
QFrame#PanelCard { background:rgba(13,20,36,0.92); border:1px solid #223354; border-radius:15px; }
QFrame#MiniCard { background:rgba(15,23,42,0.92); border:1px solid #223354; border-radius:13px; }
QFrame#TemplateCard { background:rgba(15,23,42,0.92); border:1px solid #223354; border-radius:13px; }
QFrame#TemplateCard:hover { background:#14213c; border:1px solid #22d3ee; }
QFrame#PipelineStep { background:rgba(15,23,42,0.92); border:1px solid #223354; border-radius:12px; }
QLabel#SectionTitle { font-size:15px; font-weight:750; color:#f2f7ff; }
QLabel#BigValue { font-size:24px; font-weight:850; color:#f2f7ff; }
QLabel#Tag { background:#101a2e; border:1px solid #223354; border-radius:10px; padding:5px 9px; color:#aebbd4; font-size:10px; }
QLabel#TagActive { background:#0e2a3d; border:1px solid #22d3ee; border-radius:10px; padding:5px 9px; color:#67e8f9; font-size:10px; }
QLabel#Ok { color:#34d399; }
QLabel#Warn { color:#fbbf24; }
QLabel#Error { color:#f87171; }

/* ===== Buttons ===== */
QPushButton#Primary { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22d3ee,stop:1 #38bdf8); border:0; border-radius:11px; padding:11px 18px; color:#04121a; font-weight:800; }
QPushButton#Primary:hover { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #67e8f9,stop:1 #60a5fa); }
QPushButton#Secondary { background:#101a2e; border:1px solid #223354; border-radius:10px; padding:9px 13px; color:#dbe5f5; }
QPushButton#Secondary:hover { background:#16233f; border:1px solid #38bdf8; }
QPushButton#QuickBtn { background:#101a2e; border:1px solid #223354; border-radius:10px; padding:9px 14px; color:#dbe5f5; font-size:12px; font-weight:600; }
QPushButton#QuickBtn:hover { background:#14213c; border:1px solid #22d3ee; color:#67e8f9; }

/* ===== Inputs, lists, tables ===== */
QTextEdit, QPlainTextEdit, QLineEdit, QComboBox, QListWidget, QTableWidget, QSpinBox { background:#0a101f; border:1px solid #223354; border-radius:10px; padding:9px; color:#e6edf7; }
QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border:1px solid #22d3ee; }
QListWidget::item:selected, QTableWidget::item:selected { background:#0e2a3d; color:#ffffff; }
QHeaderView::section { background:#101a2e; color:#aebbd4; border:0; border-bottom:1px solid #223354; padding:6px; }
QTabBar::tab { background:#101a2e; border:1px solid #223354; border-bottom:0; border-top-left-radius:9px; border-top-right-radius:9px; padding:7px 14px; color:#aebbd4; }
QTabBar::tab:selected { background:#0e2a3d; color:#67e8f9; border:1px solid #22d3ee; border-bottom:0; }
QCheckBox, QRadioButton { color:#dbe5f5; }

/* ===== Progress ===== */
QProgressBar { background:#101a2e; border:0; border-radius:5px; height:8px; text-align:center; color:transparent; }
QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #22d3ee,stop:1 #8b5cf6); border-radius:5px; }

QScrollArea { border:0; background:transparent; }
QMenu { background:#0d1424; border:1px solid #223354; padding:6px; }
QMenu::item { padding:8px 18px; border-radius:7px; }
QMenu::item:selected { background:#14213c; }
QToolTip { background:#101a2e; border:1px solid #223354; color:#e6edf7; padding:6px; }
"""
