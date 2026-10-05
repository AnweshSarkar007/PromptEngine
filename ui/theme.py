"""Light / dark neutral themes: one token dict per theme -> QPalette + stylesheet."""
from __future__ import annotations

from string import Template

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from core.utils import app_data_dir

LIGHT = {
    "bg": "#F3F4F6", "surface": "#FFFFFF", "surface_alt": "#F7F8FA", "input": "#FFFFFF",
    "border": "#E3E6EA", "border_strong": "#CDD2D9", "text": "#1E2329", "muted": "#68707C",
    "accent": "#3652D9", "accent_hover": "#2B43B8", "accent_text": "#FFFFFF", "accent_soft": "#E8ECFD",
    "hover": "#EEF0F3", "danger": "#C8372D", "danger_soft": "#FDEDEC", "warn": "#B26A00",
    "warn_soft": "#FFF5E0", "toggle_off": "#C3C8D0", "handle": "#C6CBD3", "nav_bg": "#FAFAFB",
    "json_bg": "#FBFBFC", "tooltip_bg": "#1E2329", "tooltip_text": "#FFFFFF",
    # JSON syntax colours
    "j_key": "#2B43B8", "j_string": "#1B7F4B", "j_number": "#B35C00", "j_literal": "#8A3FB0",
    "j_punct": "#7A828D",
}

DARK = {
    "bg": "#16181C", "surface": "#1F2227", "surface_alt": "#1A1D21", "input": "#16181C",
    "border": "#2E3238", "border_strong": "#3C424A", "text": "#E7E9EC", "muted": "#9199A4",
    "accent": "#7B93FF", "accent_hover": "#97A9FF", "accent_text": "#10131A", "accent_soft": "#262C48",
    "hover": "#272B31", "danger": "#FF7B72", "danger_soft": "#3A1F1F", "warn": "#F0B35A",
    "warn_soft": "#3A2E17", "toggle_off": "#444B54", "handle": "#444B54", "nav_bg": "#1A1C20",
    "json_bg": "#14161A", "tooltip_bg": "#E7E9EC", "tooltip_text": "#16181C",
    "j_key": "#8FA4FF", "j_string": "#7FD6A0", "j_number": "#F0B35A", "j_literal": "#C99BF0",
    "j_punct": "#7C8591",
}

THEMES = {"light": LIGHT, "dark": DARK}

_QSS = Template("""
* { font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif; }
QMainWindow, QWidget#Root, QWidget#FormHost { background: $bg; }
QScrollArea { border: none; background: $bg; }
QLabel { color: $text; background: transparent; }
QToolTip { background: $tooltip_bg; color: $tooltip_text; border: none; padding: 6px 9px; }

QFrame#Header { background: $surface; border-bottom: 1px solid $border; }
QLabel#AppTitle { font-size: 17px; font-weight: 600; }
QLabel#ProjectName { color: $muted; font-size: 13px; }
QListWidget#Nav { background: $nav_bg; border: none; border-right: 1px solid $border; padding: 10px 8px; outline: 0; }
QListWidget#Nav::item { padding: 9px 12px; border-radius: 8px; color: $muted; margin: 1px 0; }
QListWidget#Nav::item:hover { background: $hover; color: $text; }
QListWidget#Nav::item:selected { background: $accent_soft; color: $accent; font-weight: 600; }

QFrame#Card { background: $surface; border: 1px solid $border; border-radius: 14px; }
QLabel#CardTitle { font-size: 17px; font-weight: 600; }
QLabel#CardSubtitle, QLabel#Hint, QLabel#Notice { color: $muted; font-size: 12px; }
QLabel#SubHeading { font-size: 14px; font-weight: 600; }
QLabel#FieldLabel { font-size: 12px; font-weight: 600; }
QLabel#Required { color: $danger; }
QFrame#Divider { background: $border; max-height: 1px; border: none; }
QLabel#BriefResult { background: $surface_alt; border: 1px solid $border; border-radius: 8px; padding: 10px 12px; font-size: 12px; }
QLabel#BriefResult[state="ok"] { background: $accent_soft; border-color: $accent; }
QLabel#BriefResult[state="error"] { background: $danger_soft; border-color: $danger; }
QLabel#LockText { background: $surface_alt; border: 1px solid $border; border-radius: 8px; padding: 10px 12px; color: $muted; font-size: 12px; }
QLabel#Ratio { font-weight: 600; color: $accent; }

QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: $input; color: $text; border: 1px solid $border_strong; border-radius: 8px;
    padding: 6px 10px; selection-background-color: $accent; selection-color: $accent_text;
}
QLineEdit:hover, QPlainTextEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: $muted; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid $accent; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { color: $muted; background: $surface_alt; }
*[invalid="true"] { border: 1px solid $danger; background: $danger_soft; }
QComboBox { min-height: 20px; padding-right: 8px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; border: none; width: 28px; }
QComboBox::down-arrow { image: url("$chevron"); width: 12px; height: 12px; }
QComboBox QAbstractItemView { background: $surface; color: $text; border: 1px solid $border_strong; selection-background-color: $accent_soft; selection-color: $accent; outline: 0; padding: 4px; }

QPushButton { background: $surface; color: $text; border: 1px solid $border_strong; border-radius: 8px; padding: 7px 14px; }
QPushButton:hover { background: $hover; }
QPushButton:pressed { background: $accent_soft; }
QPushButton:disabled { color: $muted; background: $surface_alt; border-color: $border; }
QPushButton:focus { border: 1px solid $accent; }
QPushButton#Primary { background: $accent; color: $accent_text; border: 1px solid $accent; font-weight: 600; padding: 8px 20px; }
QPushButton#Primary:hover { background: $accent_hover; border-color: $accent_hover; }
QPushButton#Ghost { background: transparent; border: 1px solid transparent; color: $muted; }
QPushButton#Ghost:hover { background: $hover; color: $text; }
QPushButton[chip="true"] { border-radius: 15px; padding: 5px 14px; background: $surface_alt; border: 1px solid $border_strong; }
QPushButton[chip="true"]:hover { border-color: $accent; background: $surface_alt; }
QPushButton[chip="true"]:checked { background: $accent_soft; color: $accent; border: 1px solid $accent; font-weight: 600; }

QSlider::groove:horizontal { height: 6px; background: $border_strong; border-radius: 3px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 3px; }
QSlider::handle:horizontal { background: $accent; border: 3px solid $surface; width: 12px; height: 12px; margin: -7px 0; border-radius: 9px; }
QSlider::handle:horizontal:hover { background: $accent_hover; }

QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: $handle; border-radius: 4px; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: $muted; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: $handle; border-radius: 4px; min-width: 36px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QListWidget#Thumbs { background: $surface_alt; border: 1.5px dashed $border_strong; border-radius: 12px; }
QListWidget#Thumbs[dragover="true"] { border-color: $accent; background: $accent_soft; }
QListWidget#Thumbs[invalid="true"] { border: 1.5px dashed $danger; background: $danger_soft; }

QFrame#ErrorBanner { background: $danger_soft; border: 1px solid $danger; border-radius: 10px; }
QFrame#WarnBanner { background: $warn_soft; border: 1px solid $warn; border-radius: 10px; }
QLabel#BannerTitle { font-weight: 600; }
QLabel#StatusChip { background: $surface_alt; color: $muted; border: 1px solid $border; border-radius: 10px; padding: 3px 10px; font-size: 12px; }
QLabel#StatusChip[state="ok"] { background: $accent_soft; color: $accent; border-color: $accent; }
QLabel#StatusChip[state="stale"] { background: $warn_soft; color: $warn; border-color: $warn; }
QLabel#StatusChip[state="blocked"] { background: $danger_soft; color: $danger; border-color: $danger; }

QFrame#PreviewPane { background: $surface; border-left: 1px solid $border; }
QPlainTextEdit#JsonView { background: $json_bg; color: $text; border: 1px solid $border; border-radius: 10px; padding: 8px;
    font-family: "Cascadia Mono", Consolas, "Courier New", monospace; font-size: 12px; }
QSplitter::handle { background: $border; }
QStatusBar { background: $surface; color: $muted; border-top: 1px solid $border; }
QStatusBar::item { border: none; }
QMenu { background: $surface; color: $text; border: 1px solid $border_strong; padding: 4px; }
QMenu::item { padding: 6px 22px; border-radius: 6px; }
QMenu::item:selected { background: $accent_soft; color: $accent; }
QMenu::item:disabled { color: $muted; }
""")


def stylesheet(tokens: dict[str, str]) -> str:
    return _QSS.safe_substitute(tokens)


def _chevron_path(colour: str) -> str:
    """Small drop-down arrow PNG (QSS needs a file); generated once per colour in the app data folder."""
    folder = app_data_dir() / "theme"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"chevron_{colour.lstrip('#')}.png"
    if not path.exists():
        pix = QPixmap(24, 24)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(colour), 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(6, 9), QPointF(12, 15), QPointF(18, 9)])
        p.end()
        pix.save(str(path), "PNG")
    return path.as_posix()


def apply_theme(app: QApplication, name: str) -> dict[str, str]:
    """Apply the named theme to the whole application and return its tokens."""
    tokens = dict(THEMES.get(name, LIGHT))
    tokens["chevron"] = _chevron_path(tokens["muted"])
    app.setStyle("Fusion")                      # predictable look; QSS layers on top
    pal = QPalette()
    roles = {
        QPalette.Window: tokens["bg"], QPalette.WindowText: tokens["text"],
        QPalette.Base: tokens["input"], QPalette.AlternateBase: tokens["surface_alt"],
        QPalette.Text: tokens["text"], QPalette.Button: tokens["surface"],
        QPalette.ButtonText: tokens["text"], QPalette.Highlight: tokens["accent"],
        QPalette.HighlightedText: tokens["accent_text"], QPalette.Mid: tokens["toggle_off"],
        QPalette.PlaceholderText: tokens["muted"], QPalette.ToolTipBase: tokens["tooltip_bg"],
        QPalette.ToolTipText: tokens["tooltip_text"], QPalette.Link: tokens["accent"],
        QPalette.BrightText: tokens["danger"],
    }
    for role, colour in roles.items():
        pal.setColor(role, QColor(colour))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(tokens["muted"]))
    app.setPalette(pal)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(stylesheet(tokens))
    return tokens
