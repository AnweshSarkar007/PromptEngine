"""Reusable building blocks: toggle switch, chips, searchable choice field, section card, ..."""
from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import (Property, QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF, QSize, Qt,
                            Signal)
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QCheckBox, QComboBox, QDoubleSpinBox,
                               QFrame, QHBoxLayout, QLabel, QLayout, QLineEdit, QPlainTextEdit,
                               QPushButton, QSizePolicy, QSlider, QSpinBox, QVBoxLayout, QWidget)

from core.models import ProjectData


# --------------------------------------------------------------------------- #
# Style helpers
# --------------------------------------------------------------------------- #
def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def mark_invalid(widget: QWidget, flag: bool = True) -> None:
    """Red outline on a field (compound widgets provide their own `set_invalid`)."""
    if hasattr(widget, "set_invalid"):
        widget.set_invalid(flag)
        return
    widget.setProperty("invalid", bool(flag))
    repolish(widget)


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    line.setFrameShape(QFrame.HLine)
    return line


# --------------------------------------------------------------------------- #
# Inputs that must not hijack the mouse wheel while the form is scrolled
# --------------------------------------------------------------------------- #
class NoWheelComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus() or self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoWheelSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        super().wheelEvent(event) if self.hasFocus() else event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        super().wheelEvent(event) if self.hasFocus() else event.ignore()


class NoWheelSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        super().wheelEvent(event) if self.hasFocus() else event.ignore()


class TextArea(QPlainTextEdit):
    """Multi-line input with a fixed number of visible lines; wheel scrolls the page unless focused."""

    def __init__(self, lines: int = 3, placeholder: str = "", parent=None):
        super().__init__(parent)
        self._lines = lines
        self.setPlaceholderText(placeholder)
        self.setTabChangesFocus(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(200, self._lines * self.fontMetrics().lineSpacing() + 30)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def wheelEvent(self, event):
        if self.hasFocus() and self.verticalScrollBar().maximum() > 0:
            super().wheelEvent(event)
        else:
            event.ignore()

    def set_invalid(self, flag: bool) -> None:
        self.setProperty("invalid", bool(flag))
        repolish(self)


class OptionalNumberField(NoWheelDoubleSpinBox):
    """Number box where 0 means 'not set' (shown as such, returned as None)."""

    def __init__(self, suffix: str = " cm", maximum: float = 100000.0, decimals: int = 2, parent=None):
        super().__init__(parent)
        self.setRange(0, maximum)
        self.setDecimals(decimals)
        self.setSpecialValueText("Not set")
        self.setSuffix(suffix)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setKeyboardTracking(False)

    def textFromValue(self, value: float) -> str:
        return f"{value:g}"                         # 22 not 22.00

    def optional_value(self) -> Optional[float]:
        v = self.value()
        return v if v > 0 else None

    def set_optional_value(self, value: Optional[float]) -> None:
        self.setValue(value or 0)

    def set_invalid(self, flag: bool) -> None:
        self.setProperty("invalid", bool(flag))
        repolish(self)


# --------------------------------------------------------------------------- #
# Toggle switch
# --------------------------------------------------------------------------- #
class ToggleSwitch(QAbstractButton):
    """iOS-style on/off switch with an optional text label to the right."""

    TRACK_W, TRACK_H, GAP = 40, 22, 10

    def __init__(self, text: str = "", checked: bool = False, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.toggled.connect(self._on_toggled)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _on_toggled(self, checked: bool) -> None:
        target = 1.0 if checked else 0.0
        if not self.isVisible():
            self._set_offset(target)
            return
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(target)
        self._anim.start()

    def sizeHint(self) -> QSize:
        w = self.TRACK_W
        if self.text():
            w += self.GAP + self.fontMetrics().horizontalAdvance(self.text()) + 2
        return QSize(w, max(self.TRACK_H + 6, self.fontMetrics().height() + 6))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal = self.palette()
        enabled = self.isEnabled()
        p.setOpacity(1.0 if enabled else 0.5)

        off, on = pal.color(QPalette.Mid), pal.color(QPalette.Highlight)
        t = self._offset
        track = QColor(int(off.red() + (on.red() - off.red()) * t),
                       int(off.green() + (on.green() - off.green()) * t),
                       int(off.blue() + (on.blue() - off.blue()) * t))
        y = (self.height() - self.TRACK_H) / 2
        track_rect = QRectF(0, y, self.TRACK_W, self.TRACK_H)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(track_rect, self.TRACK_H / 2, self.TRACK_H / 2)

        knob_d = self.TRACK_H - 6
        knob_x = 3 + t * (self.TRACK_W - knob_d - 6)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(knob_x, y + 3, knob_d, knob_d))

        if self.hasFocus():
            ring = QColor(on)
            ring.setAlpha(150)
            p.setPen(QPen(ring, 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(track_rect.adjusted(-2, -2, 2, 2), self.TRACK_H / 2 + 2, self.TRACK_H / 2 + 2)

        if self.text():
            p.setPen(pal.color(QPalette.WindowText))
            p.drawText(QRect(self.TRACK_W + self.GAP, 0, self.width() - self.TRACK_W - self.GAP, self.height()),
                       Qt.AlignVCenter | Qt.AlignLeft, self.text())


# --------------------------------------------------------------------------- #
# Flow layout + chip group (multi-select)
# --------------------------------------------------------------------------- #
class FlowLayout(QLayout):
    """Left-to-right layout that wraps onto new lines (port of the Qt flow-layout example)."""

    def __init__(self, parent=None, hspacing: int = 8, vspacing: int = 8):
        super().__init__(parent)
        self._items = []
        self._h, self._v = hspacing, vspacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = area.x(), area.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > area.right() + 1 and line_h > 0:
                x = area.x()
                y += line_h + self._v
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._h
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


class ChipGroup(QWidget):
    """Pill-shaped multi-select. `toggled(label, checked)` fires for each chip change."""

    changed = Signal()
    toggled = Signal(str, bool)

    def __init__(self, options: Iterable[str], parent=None):
        super().__init__(parent)
        self._chips: dict[str, QPushButton] = {}
        flow = FlowLayout(self)
        for text in options:
            chip = QPushButton(text)
            chip.setProperty("chip", True)
            chip.setCheckable(True)
            chip.setCursor(Qt.PointingHandCursor)
            chip.toggled.connect(lambda checked, t=text: self._on_toggled(t, checked))
            flow.addWidget(chip)
            self._chips[text] = chip

    def _on_toggled(self, text: str, checked: bool) -> None:
        self.toggled.emit(text, checked)
        self.changed.emit()

    def values(self) -> list[str]:
        return [t for t, c in self._chips.items() if c.isChecked()]

    def set_values(self, values: Iterable[str]) -> None:
        wanted = set(values)
        for text, chip in self._chips.items():
            chip.blockSignals(True)
            chip.setChecked(text in wanted)
            chip.blockSignals(False)
            self.toggled.emit(text, text in wanted)     # lets owners show/hide dependent fields

    def is_checked(self, text: str) -> bool:
        return self._chips[text].isChecked()

    def set_invalid(self, flag: bool) -> None:
        for chip in self._chips.values():
            chip.setProperty("invalid", bool(flag))
            repolish(chip)

    def setFocus(self, *args):                             # focus the first chip
        next(iter(self._chips.values())).setFocus(*args)


# --------------------------------------------------------------------------- #
# Choice field: dropdown (searchable when long) + optional "Custom / Other" text box
# --------------------------------------------------------------------------- #
class ChoiceField(QWidget):
    """Dropdown whose value is a string. Long lists become type-to-search (contains-match).

    When `custom_label` is among the items, choosing it reveals a text box and `value()` returns
    the typed text instead of the label. Blank means 'nothing chosen' and returns ''.
    """

    changed = Signal()

    def __init__(self, items: Iterable[str], custom_label: Optional[str] = None,
                 searchable: Optional[bool] = None, placeholder: str = "Select…",
                 custom_placeholder: str = "Type your own…", parent=None):
        super().__init__(parent)
        self._items = list(items)
        self._custom_label = custom_label
        self._searchable = len(self._items) >= 9 if searchable is None else searchable
        self._offset = 0 if self._searchable else 1        # plain combos get a leading blank row

        self.combo = NoWheelComboBox()
        if not self._searchable:
            self.combo.addItem(placeholder)
        self.combo.addItems(self._items)
        if self._searchable:
            self.combo.setEditable(True)
            self.combo.setInsertPolicy(QComboBox.NoInsert)
            self.combo.completer().setFilterMode(Qt.MatchContains)
            self.combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
            self.combo.lineEdit().setPlaceholderText(placeholder)
            self.combo.lineEdit().editingFinished.connect(self._settle_typed_text)
            self.combo.setCurrentIndex(-1)
        else:
            self.combo.setCurrentIndex(0)

        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText(custom_placeholder)
        self.custom_edit.setVisible(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self.combo)
        lay.addWidget(self.custom_edit)
        self.setFocusProxy(self.combo)

        self.combo.currentIndexChanged.connect(self._on_index_changed)
        self.custom_edit.textChanged.connect(lambda _t: self.changed.emit())

    # -- value ------------------------------------------------------------ #
    def _selected(self) -> str:
        i = self.combo.currentIndex()
        if i < self._offset:
            return ""
        return self.combo.itemText(i)

    def value(self) -> str:
        sel = self._selected()
        if self._custom_label and sel == self._custom_label:
            return self.custom_edit.text().strip()
        return sel

    def set_value(self, value: str) -> None:
        self.combo.blockSignals(True)
        self.custom_edit.blockSignals(True)
        value = (value or "").strip()
        index = self.combo.findText(value, Qt.MatchFixedString) if value else -1
        if not value:
            self.combo.setCurrentIndex(-1 if self._searchable else 0)
            self.custom_edit.clear()
        elif index >= self._offset:
            self.combo.setCurrentIndex(index)
            self.custom_edit.clear()
        elif self._custom_label:
            self.combo.setCurrentIndex(self.combo.findText(self._custom_label))
            self.custom_edit.setText(value)
        else:                                               # unknown value from an older project
            self.combo.addItem(value)
            self.combo.setCurrentIndex(self.combo.count() - 1)
        self.combo.blockSignals(False)
        self.custom_edit.blockSignals(False)
        self._sync_custom_visibility()

    # -- behaviour -------------------------------------------------------- #
    def _sync_custom_visibility(self) -> None:
        show = bool(self._custom_label) and self._selected() == self._custom_label
        self.custom_edit.setVisible(show)

    def _on_index_changed(self, _i: int) -> None:
        self._sync_custom_visibility()
        if self.custom_edit.isVisible():
            self.custom_edit.setFocus()
        self.changed.emit()

    def _settle_typed_text(self) -> None:
        """Searchable combo: snap typed text to an item, clear it, or restore the old choice."""
        text = self.combo.lineEdit().text().strip()
        if not text:
            self.combo.setCurrentIndex(-1)
            return
        idx = self.combo.findText(text, Qt.MatchFixedString)     # case-insensitive exact
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
            self.combo.lineEdit().setText(self.combo.itemText(idx))
        else:
            self.combo.lineEdit().setText(self.combo.itemText(self.combo.currentIndex())
                                          if self.combo.currentIndex() >= 0 else "")

    def set_invalid(self, flag: bool) -> None:
        for w in (self.combo, self.custom_edit):
            w.setProperty("invalid", bool(flag))
            repolish(w)
        if self._searchable:
            le = self.combo.lineEdit()
            le.setProperty("invalid", bool(flag))
            repolish(le)

    def focus_custom_or_combo(self) -> None:
        (self.custom_edit if self.custom_edit.isVisible() else self.combo).setFocus()


class SliderField(QWidget):
    """Horizontal slider with a live value label (e.g. '50%' or '9 / 10')."""

    changed = Signal()

    def __init__(self, minimum: int, maximum: int, value: int, template: str = "{v}", parent=None):
        super().__init__(parent)
        self._template = template
        self.slider = NoWheelSlider(Qt.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.setTickPosition(QSlider.NoTicks)
        self._value_label = QLabel()
        self._value_label.setMinimumWidth(56)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self._value_label)
        self.setFocusProxy(self.slider)
        self.slider.valueChanged.connect(self._on_changed)
        self._refresh()

    def _refresh(self) -> None:
        self._value_label.setText(self._template.format(v=self.slider.value()))

    def _on_changed(self, _v: int) -> None:
        self._refresh()
        self.changed.emit()

    def value(self) -> int:
        return self.slider.value()

    def set_value(self, value: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self._refresh()


# --------------------------------------------------------------------------- #
# Field wrapper + section card
# --------------------------------------------------------------------------- #
class FieldBox(QWidget):
    """Label above an input, with optional hint line and tooltip."""

    def __init__(self, text: str, widget: QWidget, tooltip: str = "", required: bool = False,
                 hint: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(4)
        self.label = label(text, "FieldLabel")
        head.addWidget(self.label)
        if required:
            head.addWidget(label("*", "Required"))
        head.addStretch(1)
        lay.addLayout(head)
        lay.addWidget(widget)
        if hint:
            lay.addWidget(label(hint, "Hint", wrap=True))
        self.widget = widget
        if tooltip:
            self.setToolTip(tooltip)


class SectionCard(QFrame):
    """Base for every form section. Subclasses implement `load` / `collect`.

    `changed` fires on any edit. Fields registered under a key can be highlighted
    (validation) and focused (jump-to-error).
    """

    changed = Signal()
    section_id = ""
    title = ""
    subtitle = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._fields: dict[str, QWidget] = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 22, 26, 24)
        outer.setSpacing(16)
        outer.addWidget(label(self.title, "CardTitle"))
        if self.subtitle:
            sub = label(self.subtitle, "CardSubtitle", wrap=True)
            outer.addWidget(sub)
        self.body = QVBoxLayout()
        self.body.setSpacing(18)
        outer.addLayout(self.body)

    # -- layout helpers --------------------------------------------------- #
    def add_row(self, *items: QWidget, parent: Optional[QVBoxLayout] = None) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(18)
        for item in items:
            row.addWidget(item, 1)
        (parent or self.body).addLayout(row)
        return row

    def add_widget(self, widget: QWidget, parent: Optional[QVBoxLayout] = None) -> None:
        (parent or self.body).addWidget(widget)

    def add_button_row(self, *buttons: QWidget) -> None:
        """Left-aligned, natural-width buttons (a bare add_widget would stretch them full width)."""
        row = QHBoxLayout()
        row.setSpacing(8)
        for b in buttons:
            row.addWidget(b)
        row.addStretch(1)
        self.body.addLayout(row)

    def field(self, text: str, widget: QWidget, key: str = "", tooltip: str = "",
              required: bool = False, hint: str = "") -> FieldBox:
        """Create a labelled field, register it under `key` and watch it for edits."""
        box = FieldBox(text, widget, tooltip, required, hint)
        if tooltip:
            widget.setToolTip(tooltip)
        if key:
            self._fields[key] = widget
        self.watch(widget)
        return box

    def register(self, key: str, widget: QWidget) -> None:
        self._fields[key] = widget

    def watch(self, *widgets: QWidget) -> None:
        """Connect the right 'value changed' signal of each widget to `changed`."""
        for w in widgets:
            if isinstance(w, (ChoiceField, ChipGroup, SliderField)):
                w.changed.connect(self.changed)
            elif isinstance(w, QLineEdit):
                w.textChanged.connect(lambda _t: self.changed.emit())
            elif isinstance(w, QPlainTextEdit):
                w.textChanged.connect(self.changed)
            elif isinstance(w, QAbstractSpinBox):
                w.valueChanged.connect(lambda _v: self.changed.emit())
            elif isinstance(w, (QCheckBox, QAbstractButton)):
                w.toggled.connect(lambda _c: self.changed.emit())
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(lambda _i: self.changed.emit())

    # -- validation helpers ----------------------------------------------- #
    def mark_invalid(self, key: str, flag: bool = True) -> None:
        widget = self._fields.get(key)
        if widget is not None:
            mark_invalid(widget, flag)
            if key == "dimensions":                         # all four dimension boxes
                for k in ("width", "height", "depth", "diameter"):
                    if k in self._fields:
                        mark_invalid(self._fields[k], flag)

    def clear_invalid(self) -> None:
        for widget in self._fields.values():
            mark_invalid(widget, False)

    def focus_field(self, key: str) -> None:
        widget = self._fields.get(key)
        if widget is not None:
            widget.setFocus(Qt.OtherFocusReason)

    # -- data binding (implemented by each card) --------------------------- #
    def load(self, data: ProjectData) -> None:
        raise NotImplementedError

    def collect(self, data: ProjectData) -> None:
        raise NotImplementedError
