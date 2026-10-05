"""Main window: header actions, section navigation, scrollable form, JSON preview.

The window never touches form fields directly. It asks each `SectionCard` to `collect` into a
`ProjectData`, runs `core.pipeline.run_pipeline`, and shows the result.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea,
                               QSplitter, QVBoxLayout, QWidget)

from core import options as opt
from core.chatgpt_brief import apply_brief
from core.models import ProjectData
from core.pipeline import PipelineResult, run_pipeline
from core.project_manager import (ProjectError, ensure_project_suffix, load_project, save_project,
                                  write_text_atomic)
from core.utils import resource_path

from .brief_panel import BriefCard
from .camera_panel import CameraCard, CompositionCard, LightingCard, VisualStyleCard
from .json_preview import JsonPreviewPanel
from .model_panel import HumanModelCard
from .output_panel import OutputCard, RestrictionsCard
from .product_panel import ContentsCard, IdentityLockCard, ProductDetailsCard, ProductStateCard
from .reference_panel import ReferencePanel
from .scene_panel import SceneCard
from .theme import THEMES, apply_theme
from .widgets import SectionCard, label, repolish

PREVIEW_ID = "preview"


class ValidationBanner(QFrame):
    """Dismissible list of validation messages; each message jumps to its field when clicked."""

    jumpRequested = Signal(str, str)           # section id, field key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ErrorBanner")
        self.title = label("", "BannerTitle")
        self.body = QLabel()
        self.body.setTextFormat(Qt.RichText)
        self.body.setWordWrap(True)
        self.body.setOpenExternalLinks(False)
        self.body.linkActivated.connect(self._on_link)
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("Ghost")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setToolTip("Dismiss")
        self.close_btn.clicked.connect(self.hide)

        head = QHBoxLayout()
        head.addWidget(self.title, 1)
        head.addWidget(self.close_btn)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 10, 10, 12)
        lay.setSpacing(4)
        lay.addLayout(head)
        lay.addWidget(self.body)
        self.hide()

    def show_issues(self, errors, warnings) -> None:
        if not errors and not warnings:
            self.hide()
            return
        self.setObjectName("ErrorBanner" if errors else "WarnBanner")
        repolish(self)
        if errors:
            n = len(errors)
            self.title.setText(f"{n} thing{'s' if n != 1 else ''} to fix before the JSON can be generated")
        else:
            self.title.setText("JSON generated — a few notes")
        rows = [f'<li><a href="{i.section_id}|{i.field_key}">{html.escape(i.message)}</a></li>' for i in errors]
        rows += [f"<li>{html.escape(i.message)}</li>" for i in warnings]
        self.body.setText('<ul style="margin:0 0 0 -18px">' + "".join(rows) + "</ul>")
        self.show()

    def _on_link(self, href: str) -> None:
        section, _, key = href.partition("|")
        self.jumpRequested.emit(section, key)


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings, theme: str = "light"):
        super().__init__()
        self.settings = settings
        self.theme_name = theme if theme in THEMES else "light"
        self.tokens = THEMES[self.theme_name]
        self._project_path: Optional[Path] = None
        self._dirty = False
        self._stale = True
        self._loading = False
        self._nav_lock = False
        self._after_scroll = None
        self._last_result: Optional[PipelineResult] = None

        self.setMinimumSize(1080, 680)
        self.resize(1480, 920)
        icon_path = resource_path("assets/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._build_shortcuts()
        start_dir = self._last_dir()
        self.references.last_dir = start_dir

        self.apply(ProjectData())                       # fills every card with its defaults
        self._restore_window_state()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.setFixedWidth(224)
        self.nav.setFocusPolicy(Qt.NoFocus)
        for number, (section_id, title) in enumerate(opt.SECTIONS, 1):
            item = QListWidgetItem(f"{number:>2}   {title}")
            item.setData(Qt.UserRole, section_id)
            self.nav.addItem(item)
        self.nav.itemClicked.connect(self._on_nav_clicked)
        self.nav.itemActivated.connect(self._on_nav_clicked)
        body.addWidget(self.nav)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setHandleWidth(1)
        self.splitter.addWidget(self._build_form_area())
        self.preview = JsonPreviewPanel(self.tokens)
        self.preview.setMinimumWidth(320)
        self.preview.copyRequested.connect(self.copy_json)
        self.preview.saveJsonRequested.connect(self.save_json)
        self.preview.exportTextRequested.connect(self.export_text)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([860, 420])
        body.addWidget(self.splitter, 1)
        outer.addLayout(body, 1)

        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().showMessage("Ready — add your product images and fill in the form.")

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("Header")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(10)

        title = QLabel(opt.APP_NAME)
        title.setObjectName("AppTitle")
        self.project_label = QLabel()
        self.project_label.setObjectName("ProjectName")
        lay.addWidget(title)
        lay.addSpacing(8)
        lay.addWidget(self.project_label)
        lay.addStretch(1)

        self.load_btn = QPushButton("Load Project")
        self.save_btn = QPushButton("Save Project")
        self.reset_btn = QPushButton("Reset Form")
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("Ghost")
        self.generate_btn = QPushButton("Generate JSON")
        self.generate_btn.setObjectName("Primary")
        self.load_btn.setToolTip("Open a saved .project.json file (Ctrl+O).")
        self.save_btn.setToolTip("Save every field and image reference to a .project.json file (Ctrl+S; "
                                 "Ctrl+Shift+S saves under a new name).")
        self.reset_btn.setToolTip("Clear the form back to its defaults.")
        self.theme_btn.setToolTip("Switch between light and dark appearance.")
        self.generate_btn.setToolTip("Validate the form and build the JSON prompt (Ctrl+G).")
        self.load_btn.clicked.connect(self.load_project_file)
        self.save_btn.clicked.connect(lambda: self.save_project_file())
        self.reset_btn.clicked.connect(self.reset_form)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.generate_btn.clicked.connect(self.generate)
        for w in (self.load_btn, self.save_btn, self.reset_btn, self.theme_btn):
            lay.addWidget(w)
        lay.addSpacing(6)
        lay.addWidget(self.generate_btn)
        self._update_theme_button()
        return header

    def _build_form_area(self) -> QWidget:
        wrap = QWidget()
        wrap.setObjectName("FormHost")
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.banner = ValidationBanner()
        self.banner.jumpRequested.connect(self.jump_to)
        banner_wrap = QHBoxLayout()
        banner_wrap.setContentsMargins(28, 14, 28, 0)
        banner_wrap.addWidget(self.banner)
        v.addLayout(banner_wrap)

        self.references = ReferencePanel()
        self.brief = BriefCard()
        self.brief.loadRequested.connect(self.load_brief)
        self.cards: list[SectionCard] = [
            self.references, self.brief, ProductDetailsCard(), IdentityLockCard(), SceneCard(), ProductStateCard(),
            ContentsCard(), HumanModelCard(), CameraCard(), LightingCard(), CompositionCard(),
            VisualStyleCard(), OutputCard(), RestrictionsCard(),
        ]
        self.cards_by_id = {c.section_id: c for c in self.cards}

        column = QWidget()
        column.setMaximumWidth(1000)
        col_lay = QVBoxLayout(column)
        col_lay.setContentsMargins(0, 0, 0, 0)
        col_lay.setSpacing(18)
        for card in self.cards:
            col_lay.addWidget(card)
            card.changed.connect(lambda c=card: self._on_changed(c))
        col_lay.addStretch(1)

        self.host = QWidget()
        self.host.setObjectName("FormHost")
        host_lay = QHBoxLayout(self.host)
        host_lay.setContentsMargins(28, 18, 28, 32)
        host_lay.addWidget(column, 1)
        host_lay.addStretch(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.host)
        v.addWidget(self.scroll, 1)

        self._scroll_anim = QPropertyAnimation(self.scroll.verticalScrollBar(), b"value", self)
        self._scroll_anim.setDuration(260)
        self._scroll_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._scroll_anim.finished.connect(self._on_scroll_finished)
        self.scroll.verticalScrollBar().valueChanged.connect(self._sync_nav_to_scroll)
        return wrap

    def _build_shortcuts(self) -> None:
        for keys, slot in (("Ctrl+G", self.generate), ("Ctrl+O", self.load_project_file),
                           ("Ctrl+S", lambda: self.save_project_file()),
                           ("Ctrl+Shift+S", lambda: self.save_project_file(save_as=True)),
                           ("Ctrl+Shift+C", self.copy_json)):
            QShortcut(QKeySequence(keys), self, activated=slot)

    # ------------------------------------------------------------------ #
    # Data <-> form
    # ------------------------------------------------------------------ #
    def collect(self) -> ProjectData:
        data = ProjectData()
        for card in self.cards:
            card.collect(data)
        return data

    def apply(self, data: ProjectData, path: Optional[Path] = None) -> None:
        """Show `data` in the form and treat it as a clean, ungenerated state."""
        self._loading = True
        try:
            for card in self.cards:
                card.load(data)
                card.clear_invalid()
        finally:
            self._loading = False
        self._project_path = path
        self._dirty = False
        self._stale = True
        self._last_result = None
        self.banner.hide()
        self.preview.clear()
        self._update_title()

    def _on_changed(self, card: SectionCard) -> None:
        if self._loading:
            return
        card.clear_invalid()
        self._mark_changed()

    def _mark_changed(self) -> None:
        self._dirty = True
        self._stale = True
        if self.preview.has_json():
            self.preview.set_state("stale")
        self._update_title()

    def load_brief(self, text: str) -> None:
        """Fill the form from a pasted ChatGPT reply (images, product details and restrictions stay)."""
        data = self.collect()
        result = apply_brief(text, data)
        if result.ok:
            self._loading = True
            try:
                for card in self.cards:
                    if card not in (self.brief, self.references):
                        card.load(data)
                        card.clear_invalid()
            finally:
                self._loading = False
            self._mark_changed()
            self.statusBar().showMessage(f"Loaded {len(result.filled)} fields from the ChatGPT reply.", 6000)
        self.brief.show_result(result)

    def _update_title(self) -> None:
        name = self._project_path.name if self._project_path else "Untitled project"
        mark = " •" if self._dirty else ""
        self.project_label.setText(f"{name}{mark}")
        self.setWindowTitle(f"{opt.APP_NAME} — {name}{mark}")

    # ------------------------------------------------------------------ #
    # Generate / copy / save / export
    # ------------------------------------------------------------------ #
    def generate(self) -> bool:
        data = self.collect()
        result = run_pipeline(data)
        for card in self.cards:
            card.clear_invalid()
        for issue in result.errors:
            card = self.cards_by_id.get(issue.section_id)
            if card:
                card.mark_invalid(issue.field_key, True)
        self.banner.show_issues(result.errors, result.warnings)

        if not result.ok:
            self.preview.set_state("blocked")
            first = result.errors[0]
            self.jump_to(first.section_id, first.field_key)
            n = len(result.errors)
            self.statusBar().showMessage(f"{n} item{'s' if n != 1 else ''} need attention before generating.", 8000)
            return False

        self._last_result = result
        self._stale = False
        self.preview.set_json(result.json_text)
        self.statusBar().showMessage("JSON generated.", 5000)
        return True

    def ensure_generated(self) -> bool:
        """Copy / save / export always use fresh output, regenerating if the form changed."""
        return (self._last_result is not None and not self._stale) or self.generate()

    def copy_json(self) -> None:
        if not self.ensure_generated():
            return
        QGuiApplication.clipboard().setText(self._last_result.json_text)
        self.preview.flash_copied()
        self.statusBar().showMessage("JSON copied to the clipboard.", 4000)

    def save_json(self) -> None:
        if self.ensure_generated():
            self._save_text("Save JSON prompt", "_prompt.json", "JSON files (*.json)", ".json",
                            self._last_result.json_text + "\n", "JSON saved")

    def export_text(self) -> None:
        if self.ensure_generated():
            self._save_text("Export prompt as text", "_prompt.txt", "Text files (*.txt)", ".txt",
                            self._last_result.text_prompt, "Prompt exported")

    def _save_text(self, caption: str, suffix: str, name_filter: str, ext: str, text: str, done: str) -> None:
        default = str(Path(self._last_dir()) / (self._slug() + suffix))
        path, _ = QFileDialog.getSaveFileName(self, caption, default, name_filter)
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext
        try:
            write_text_atomic(path, text)
        except ProjectError as exc:
            QMessageBox.critical(self, opt.APP_NAME, str(exc))
            return
        self._remember_dir(path)
        self.statusBar().showMessage(f"{done}: {path}", 6000)

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #
    def save_project_file(self, save_as: bool = False) -> bool:
        path = self._project_path
        if save_as or path is None:
            default = str(Path(self._last_dir()) / (self._slug() + opt.PROJECT_SUFFIX))
            chosen, _ = QFileDialog.getSaveFileName(self, "Save project", default,
                                                    "Project files (*.project.json);;All files (*)")
            if not chosen:
                return False
            path = ensure_project_suffix(chosen)
        try:
            saved = save_project(path, self.collect())
        except ProjectError as exc:
            QMessageBox.critical(self, opt.APP_NAME, str(exc))
            return False
        self._project_path = saved
        self._dirty = False
        self._remember_dir(str(saved))
        self._update_title()
        self.statusBar().showMessage(f"Project saved: {saved}", 6000)
        return True

    def load_project_file(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Load project", self._last_dir(),
                                              "Project files (*.project.json *.json);;All files (*)")
        if path:
            self.open_project_path(path)

    def open_project_path(self, path: str) -> bool:
        try:
            data, warnings = load_project(path)
        except ProjectError as exc:
            QMessageBox.critical(self, opt.APP_NAME, str(exc))
            return False
        self.apply(data, Path(path))
        self._remember_dir(path)
        self.statusBar().showMessage(f"Project loaded: {path}", 6000)
        if warnings:
            QMessageBox.information(self, opt.APP_NAME, "\n".join(warnings))
        return True

    def reset_form(self) -> None:
        answer = QMessageBox.question(self, opt.APP_NAME,
                                      "Reset every field to its default?\nUnsaved changes will be lost.",
                                      QMessageBox.Reset | QMessageBox.Cancel, QMessageBox.Cancel)
        if answer == QMessageBox.Reset:
            self.apply(ProjectData())
            self.scroll.verticalScrollBar().setValue(0)
            self.statusBar().showMessage("Form reset.", 4000)

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, opt.APP_NAME, "You have unsaved changes. Save them to a project file first?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save_project_file()
        return answer == QMessageBox.Discard

    def closeEvent(self, event) -> None:
        if not self._confirm_discard():
            event.ignore()
            return
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitter", self.splitter.saveState())
        self.settings.setValue("theme", self.theme_name)
        self.settings.sync()
        event.accept()

    # ------------------------------------------------------------------ #
    # Navigation / scrolling
    # ------------------------------------------------------------------ #
    def _on_nav_clicked(self, item: QListWidgetItem) -> None:
        self.scroll_to_section(item.data(Qt.UserRole))

    def _card_top(self, card: QWidget) -> int:
        return card.mapTo(self.host, QPoint(0, 0)).y()

    def scroll_to_section(self, section_id: str, then=None) -> None:
        if section_id == PREVIEW_ID:
            self._reveal_preview()
            if then:
                then()
            return
        card = self.cards_by_id.get(section_id)
        if card is None:
            return
        self._select_nav(section_id)
        bar = self.scroll.verticalScrollBar()
        target = max(0, min(self._card_top(card) - 14, bar.maximum()))
        self._after_scroll = then
        if not self.isVisible() or abs(bar.value() - target) < 4:
            bar.setValue(target)
            self._on_scroll_finished()
            return
        self._nav_lock = True
        self._scroll_anim.stop()
        self._scroll_anim.setStartValue(bar.value())
        self._scroll_anim.setEndValue(target)
        self._scroll_anim.start()

    def _on_scroll_finished(self) -> None:
        self._nav_lock = False
        callback, self._after_scroll = self._after_scroll, None
        if callback:
            callback()

    def jump_to(self, section_id: str, field_key: str) -> None:
        card = self.cards_by_id.get(section_id)
        if card is None:
            return
        self.scroll_to_section(section_id, then=lambda: card.focus_field(field_key))

    def _reveal_preview(self) -> None:
        sizes = self.splitter.sizes()
        if sizes[1] < 200:
            total = sum(sizes)
            self.splitter.setSizes([total - 460, 460])
        self.preview.view.setFocus()
        self._select_nav(PREVIEW_ID)

    def _select_nav(self, section_id: str) -> None:
        for row in range(self.nav.count()):
            if self.nav.item(row).data(Qt.UserRole) == section_id:
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(row)
                self.nav.blockSignals(False)
                return

    def _sync_nav_to_scroll(self, value: int) -> None:
        """Highlight the nav entry of the card currently at the top of the viewport."""
        if self._nav_lock:
            return
        bar = self.scroll.verticalScrollBar()
        current = self.cards[0]
        if value >= bar.maximum() > 0:
            current = self.cards[-1]
        else:
            for card in self.cards:
                if self._card_top(card) <= value + 60:
                    current = card
        self._select_nav(current.section_id)

    # ------------------------------------------------------------------ #
    # Theme, settings, small helpers
    # ------------------------------------------------------------------ #
    def toggle_theme(self) -> None:
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.tokens = apply_theme(QApplication.instance(), self.theme_name)
        self.preview.set_tokens(self.tokens)
        self.settings.setValue("theme", self.theme_name)
        self._update_theme_button()

    def _update_theme_button(self) -> None:
        self.theme_btn.setText("Dark mode" if self.theme_name == "light" else "Light mode")

    def _restore_window_state(self) -> None:
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        state = self.settings.value("splitter")
        if state:
            self.splitter.restoreState(state)

    def _last_dir(self) -> str:
        saved = self.settings.value("last_dir", "")
        if saved and Path(saved).is_dir():
            return str(saved)
        return str(Path.home() / "Documents") if (Path.home() / "Documents").is_dir() else str(Path.home())

    def _remember_dir(self, path: str) -> None:
        folder = str(Path(path).parent)
        self.settings.setValue("last_dir", folder)
        self.references.last_dir = folder

    def _slug(self) -> str:
        name = self.cards_by_id["product"].name_edit.text()
        return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "product"
