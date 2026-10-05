"""Section 1: the new product's identity images (1-15)."""
from __future__ import annotations

import math
import os
from typing import Optional

from PySide6.QtCore import QItemSelectionModel, QMimeData, QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QDrag, QFont, QImageIOHandler, QImageReader, QPainter, QPalette,
                           QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QListView,
                               QListWidget, QListWidgetItem, QMenu, QPushButton, QStyle,
                               QStyledItemDelegate)

from core import options as opt
from core.models import ProjectData
from core.utils import file_name, is_supported_image, normalize_path

from .widgets import SectionCard, label, repolish

THUMB = 112                      # thumbnail edge in px
CELL_W, CELL_H = 134, 164        # grid cell incl. breathing room
ROLE_PATH = Qt.UserRole
ROLE_PIXMAP = Qt.UserRole + 1
ROLE_PRIMARY = Qt.UserRole + 2
ROLE_MISSING = Qt.UserRole + 3


def load_thumbnail(path: str, max_side: int = 320) -> QPixmap:
    """Decode an image scaled down to `max_side` (null pixmap when unreadable)."""
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    size = reader.size()
    no_rotation = reader.transformation() == QImageIOHandler.Transformation.TransformationNone
    if no_rotation and size.isValid() and max(size.width(), size.height()) > max_side:
        reader.setScaledSize(size.scaled(max_side, max_side, Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        return QPixmap()
    pix = QPixmap.fromImage(image)
    if max(pix.width(), pix.height()) > max_side:
        pix = pix.scaled(max_side, max_side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pix


def image_urls(mime: QMimeData) -> list[str]:
    if not mime.hasUrls():
        return []
    return [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]


def has_image_urls(mime: QMimeData) -> bool:
    return any(is_supported_image(p) or os.path.isdir(p) for p in image_urls(mime))


# --------------------------------------------------------------------------- #
# Thumbnail cell painter
# --------------------------------------------------------------------------- #
class ThumbDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index) -> QSize:
        return QSize(CELL_W, CELL_H)

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        pal = option.palette
        selected = bool(option.state & QStyle.State_Selected)
        primary = bool(index.data(ROLE_PRIMARY))
        accent = pal.color(QPalette.Highlight)

        card = QRectF(option.rect).adjusted(5, 5, -5, -5)
        painter.setBrush(pal.color(QPalette.Base))
        border = QPen(accent if (selected or primary) else pal.color(QPalette.Mid), 2 if (selected or primary) else 1)
        painter.setPen(border)
        painter.drawRoundedRect(card, 10, 10)

        # picture area
        area = QRectF(card.left() + 8, card.top() + 8, card.width() - 16, THUMB)
        pix: QPixmap = index.data(ROLE_PIXMAP)
        if pix is not None and not pix.isNull():
            scaled = pix.size().scaled(int(area.width()), int(area.height()), Qt.KeepAspectRatio)
            target = QRectF(area.center().x() - scaled.width() / 2, area.center().y() - scaled.height() / 2,
                            scaled.width(), scaled.height())
            painter.drawPixmap(target, pix, QRectF(pix.rect()))
        else:
            painter.setPen(pal.color(QPalette.BrightText))
            painter.drawText(area, Qt.AlignCenter, "File missing" if index.data(ROLE_MISSING) else "Unreadable")

        # number badge (top-left) and primary pill (top-right)
        badge = QRectF(card.left() + 12, card.top() + 12, 22, 22)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 150))
        painter.drawEllipse(badge)
        painter.setPen(QColor("#FFFFFF"))
        small = QFont(option.font)
        small.setPointSizeF(max(option.font.pointSizeF() - 1.5, 7))
        small.setBold(True)
        painter.setFont(small)
        painter.drawText(badge, Qt.AlignCenter, str(index.row() + 1))

        if primary:
            pill = QRectF(card.right() - 78, card.top() + 12, 66, 20)
            painter.setPen(Qt.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(pill, 10, 10)
            painter.setPen(pal.color(QPalette.HighlightedText))
            painter.drawText(pill, Qt.AlignCenter, "★ Primary")

        # file name
        name_font = QFont(option.font)
        name_font.setPointSizeF(max(option.font.pointSizeF() - 1, 7.5))
        painter.setFont(name_font)
        painter.setPen(pal.color(QPalette.Text))
        name_rect = QRectF(card.left() + 8, area.bottom() + 6, card.width() - 16, 20)
        text = painter.fontMetrics().elidedText(file_name(index.data(ROLE_PATH)), Qt.ElideMiddle, int(name_rect.width()))
        painter.drawText(name_rect, Qt.AlignCenter, text)
        painter.restore()


# --------------------------------------------------------------------------- #
# Product image grid (drop, browse, remove, reorder, primary)
# --------------------------------------------------------------------------- #
class ThumbnailList(QListWidget):
    pathsChanged = Signal()
    message = Signal(str)
    deleteRequested = Signal()
    MIME = "application/x-ppb-thumb-row"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Thumbs")
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setWrapping(True)
        self.setSpacing(0)
        self.setGridSize(QSize(CELL_W, CELL_H))
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        # setMovement(Static) above silently switched drops off on the viewport; our own
        # reorder / file-drop handling below needs them on.
        self.viewport().setAcceptDrops(True)
        self.setItemDelegate(ThumbDelegate(self))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.StrongFocus)

        self._paths: list[str] = []
        self._primary = ""
        self._pix: dict[str, QPixmap] = {}
        self._drop_index: Optional[int] = None
        self._fit_height()

    # -- state ------------------------------------------------------------ #
    def paths(self) -> list[str]:
        return list(self._paths)

    def primary(self) -> str:
        return self._primary if self._primary in self._paths else (self._paths[0] if self._paths else "")

    def set_state(self, paths: list[str], primary: str) -> None:
        self._paths = list(paths)[: opt.MAX_PRODUCT_IMAGES]
        self._primary = primary if primary in self._paths else ""
        self._pix = {p: load_thumbnail(p) for p in self._paths}
        self._refresh()

    def _refresh(self) -> None:
        keep = {self.item(r).data(ROLE_PATH) for r in range(self.count()) if self.item(r).isSelected()}
        current = self.item(self.currentRow()).data(ROLE_PATH) if self.currentRow() >= 0 else ""
        self.clear()
        primary = self.primary()
        for path in self._paths:
            item = QListWidgetItem()
            item.setData(ROLE_PATH, path)
            item.setData(ROLE_PIXMAP, self._pix.get(path))
            item.setData(ROLE_PRIMARY, path == primary)
            item.setData(ROLE_MISSING, not os.path.isfile(path))
            item.setToolTip(path)
            item.setSizeHint(QSize(CELL_W, CELL_H))
            self.addItem(item)
            if path in keep:
                item.setSelected(True)
            if path == current:           # keep the 'current' row without touching the selection
                self.selectionModel().setCurrentIndex(self.indexFromItem(item), QItemSelectionModel.NoUpdate)
        self._fit_height()
        self.viewport().update()

    # -- editing ---------------------------------------------------------- #
    def add_paths(self, candidates: list[str]) -> None:
        added = bad = dupes = over = 0
        files: list[str] = []
        for raw in candidates:                            # a dropped folder contributes its images
            if os.path.isdir(raw):
                files += [os.path.join(raw, n) for n in sorted(os.listdir(raw)) if is_supported_image(n)]
            else:
                files.append(raw)
        for raw in files:
            path = normalize_path(raw)
            if not is_supported_image(path) or not QImageReader(path).canRead():
                bad += 1
            elif path in self._paths:
                dupes += 1
            elif len(self._paths) >= opt.MAX_PRODUCT_IMAGES:
                over += 1
            else:
                self._paths.append(path)
                self._pix[path] = load_thumbnail(path)
                added += 1
        if added and not self._primary:
            self._primary = self._paths[0]
        self._refresh()
        if added:
            self.pathsChanged.emit()
        notes = []
        if bad:
            notes.append(f"{bad} file(s) skipped: not a readable JPG, PNG or WEBP image")
        if dupes:
            notes.append(f"{dupes} already added")
        if over:
            notes.append(f"{over} skipped: the limit is {opt.MAX_PRODUCT_IMAGES} images")
        if notes:
            self.message.emit(" · ".join(notes) + ".")

    def selected_paths(self) -> list[str]:
        return [i.data(ROLE_PATH) for i in self.selectedItems()]

    def remove_selected(self) -> None:
        doomed = set(self.selected_paths())
        if not doomed:
            return
        self._paths = [p for p in self._paths if p not in doomed]
        for p in doomed:
            self._pix.pop(p, None)
        if self._primary in doomed:
            self._primary = self._paths[0] if self._paths else ""
        self._refresh()
        self.pathsChanged.emit()

    def set_primary_selected(self) -> None:
        sel = self.selected_paths()
        if sel:
            self._primary = sel[0]
            self._refresh()
            self.pathsChanged.emit()

    def move_selected(self, delta: int) -> None:
        row = self.currentRow()
        if row < 0 or not self.item(row).isSelected():
            rows = sorted(self.row(i) for i in self.selectedItems())
            if not rows:
                return
            row = rows[0] if delta < 0 else rows[-1]
        new = max(0, min(len(self._paths) - 1, row + delta))
        if new != row:
            self._reorder(row, new)

    def _reorder(self, src: int, dst: int) -> None:
        self._paths.insert(dst, self._paths.pop(src))
        self._refresh()
        self.clearSelection()
        self.setCurrentRow(dst)
        self.item(dst).setSelected(True)
        self.pathsChanged.emit()

    # -- drag & drop ------------------------------------------------------ #
    def startDrag(self, supported_actions) -> None:
        row = self.currentRow()
        if row < 0:
            return
        mime = QMimeData()
        mime.setData(self.MIME, str(row).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.viewport().grab(self.visualItemRect(self.item(row))).scaledToWidth(96, Qt.SmoothTransformation))
        drag.exec(Qt.MoveAction)

    def _accepts(self, mime: QMimeData) -> bool:
        return mime.hasFormat(self.MIME) or has_image_urls(mime)

    def _insertion_index(self, pos: QPoint) -> int:
        item = self.itemAt(pos)
        if item is None:
            return self.count()
        rect = self.visualItemRect(item)
        row = self.row(item)
        return row + 1 if pos.x() > rect.center().x() else row

    def dragEnterEvent(self, event) -> None:
        if self._accepts(event.mimeData()):
            event.acceptProposedAction()
            self._set_dragover(not event.mimeData().hasFormat(self.MIME))
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if not self._accepts(event.mimeData()):
            event.ignore()
            return
        event.acceptProposedAction()
        self._drop_index = self._insertion_index(event.position().toPoint()) if event.mimeData().hasFormat(self.MIME) else None
        self.viewport().update()

    def dragLeaveEvent(self, event) -> None:
        self._drop_index = None
        self._set_dragover(False)
        self.viewport().update()

    def dropEvent(self, event) -> None:
        mime = event.mimeData()
        self._set_dragover(False)
        index = self._drop_index
        self._drop_index = None
        if mime.hasFormat(self.MIME) and event.source() is self:
            src = int(bytes(mime.data(self.MIME)).decode())
            dst = self._insertion_index(event.position().toPoint()) if index is None else index
            dst = dst - 1 if src < dst else dst
            event.acceptProposedAction()
            if 0 <= dst < len(self._paths) and dst != src:
                self._reorder(src, dst)
            else:
                self.viewport().update()
        elif has_image_urls(mime):
            event.acceptProposedAction()
            self.add_paths(image_urls(mime))
        else:
            event.ignore()

    def _set_dragover(self, flag: bool) -> None:
        self.setProperty("dragover", flag)
        repolish(self)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.deleteRequested.emit()
        else:
            super().keyPressEvent(event)

    # -- painting / sizing ------------------------------------------------ #
    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.Antialiasing)
        if self.count() == 0:
            p.setPen(self.palette().color(QPalette.PlaceholderText))
            p.drawText(self.viewport().rect(), Qt.AlignCenter,
                       "Drag & drop product images here\nor use “Add images…”\n\nJPG · PNG · WEBP  ·  up to 15 images")
        elif self._drop_index is not None:
            if self._drop_index < self.count():
                r = self.visualItemRect(self.item(self._drop_index))
                x = r.left() + 2
            else:
                r = self.visualItemRect(self.item(self.count() - 1))
                x = r.right() - 2
            p.setPen(QPen(self.palette().color(QPalette.Highlight), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(x, r.top() + 10, x, r.bottom() - 10)
        p.end()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_height()

    def _fit_height(self) -> None:
        """Grow with the number of rows instead of scrolling inside the card."""
        cols = max(1, (self.viewport().width() or CELL_W * 5) // CELL_W)
        rows = max(1, math.ceil(max(self.count(), 1) / cols))
        height = max(rows * CELL_H + 10, 190)
        if self.height() != height:
            self.setFixedHeight(height)


# --------------------------------------------------------------------------- #
# The card
# --------------------------------------------------------------------------- #
class ReferencePanel(SectionCard):
    section_id = "references"
    title = "Reference Images"
    subtitle = "Upload 1–15 photos of the new product from different angles and mark the clearest one as primary."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_dir = ""

        # --- product identity references ------------------------------------
        head = QHBoxLayout()
        head.setSpacing(4)
        head.addWidget(label("Product reference images", "SubHeading"))
        head.addWidget(label("*", "Required"))
        head.addStretch(1)
        self.count_label = label("", "Hint")
        head.addWidget(self.count_label)
        self.body.addLayout(head)
        self.body.addWidget(label(opt.PRODUCT_REF_HELP, "Hint", wrap=True))

        self.thumbs = ThumbnailList()
        self.thumbs.setToolTip("Drop images here. Drag a thumbnail to reorder it; double-click to make it the "
                               "primary reference.")
        self.body.addWidget(self.thumbs)
        self.register("product_images", self.thumbs)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.add_btn = QPushButton("Add images…")
        self.remove_btn = QPushButton("Remove")
        self.primary_btn = QPushButton("★ Set as primary")
        self.left_btn = QPushButton("◀")
        self.right_btn = QPushButton("▶")
        for b, tip in ((self.add_btn, "Browse for JPG, PNG or WEBP files (select several at once)."),
                       (self.remove_btn, "Remove the selected image(s) from the list (files are not deleted)."),
                       (self.primary_btn, "Mark the selected image as the Primary Product Reference."),
                       (self.left_btn, "Move the selected image earlier in the order."),
                       (self.right_btn, "Move the selected image later in the order.")):
            b.setToolTip(tip)
        self.add_btn.setObjectName("Primary")
        self.left_btn.setFixedWidth(44)
        self.right_btn.setFixedWidth(44)
        for b in (self.add_btn, self.remove_btn, self.primary_btn, self.left_btn, self.right_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        self.body.addLayout(buttons)

        self.notice = label("", "Notice", wrap=True)
        self.notice.setVisible(False)
        self.body.addWidget(self.notice)
        self._notice_timer = QTimer(self, singleShot=True, interval=8000)
        self._notice_timer.timeout.connect(lambda: self.notice.setVisible(False))

        # --- wiring ------------------------------------------------------------
        self.add_btn.clicked.connect(self._browse)
        self.remove_btn.clicked.connect(self.thumbs.remove_selected)
        self.thumbs.deleteRequested.connect(self.thumbs.remove_selected)
        self.primary_btn.clicked.connect(self.thumbs.set_primary_selected)
        self.thumbs.itemDoubleClicked.connect(lambda _i: self.thumbs.set_primary_selected())
        self.left_btn.clicked.connect(lambda: self.thumbs.move_selected(-1))
        self.right_btn.clicked.connect(lambda: self.thumbs.move_selected(+1))
        self.thumbs.itemSelectionChanged.connect(self._update_buttons)
        self.thumbs.pathsChanged.connect(self._on_paths_changed)
        self.thumbs.message.connect(self._show_notice)
        self.thumbs.customContextMenuRequested.connect(self._context_menu)
        self._update_buttons()

    # -- UI logic --------------------------------------------------------- #
    def _browse(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Choose product reference images", self.last_dir,
                                                opt.IMAGE_FILTER)
        if files:
            self.last_dir = os.path.dirname(files[0])
            self.thumbs.add_paths(files)

    def _on_paths_changed(self) -> None:
        self._update_buttons()
        self.thumbs.setProperty("invalid", False)
        repolish(self.thumbs)
        self.changed.emit()

    def _update_buttons(self) -> None:
        n = self.thumbs.count()
        has_sel = bool(self.thumbs.selectedItems())
        row = self.thumbs.currentRow()
        self.count_label.setText(f"{n} / {opt.MAX_PRODUCT_IMAGES} images")
        self.remove_btn.setEnabled(has_sel)
        self.primary_btn.setEnabled(has_sel)
        self.left_btn.setEnabled(has_sel and row > 0)
        self.right_btn.setEnabled(has_sel and 0 <= row < n - 1)
        self.add_btn.setEnabled(n < opt.MAX_PRODUCT_IMAGES)

    def _show_notice(self, text: str) -> None:
        self.notice.setText(text)
        self.notice.setVisible(True)
        self._notice_timer.start()

    def _context_menu(self, pos: QPoint) -> None:
        if self.thumbs.itemAt(pos) is None:
            return
        menu = QMenu(self)
        menu.addAction("★ Set as primary reference", self.thumbs.set_primary_selected)
        menu.addAction("Move earlier", lambda: self.thumbs.move_selected(-1))
        menu.addAction("Move later", lambda: self.thumbs.move_selected(+1))
        menu.addSeparator()
        menu.addAction("Remove", self.thumbs.remove_selected)
        menu.exec(self.thumbs.viewport().mapToGlobal(pos))

    # -- data binding ----------------------------------------------------- #
    def load(self, data: ProjectData) -> None:
        self.thumbs.set_state(data.reference.product_images, data.reference.effective_primary())
        self._update_buttons()

    def collect(self, data: ProjectData) -> None:
        data.reference.product_images = self.thumbs.paths()
        data.reference.primary_path = self.thumbs.primary()
