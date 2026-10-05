"""Output settings (size, aspect ratio, intended use, quality) and the restrictions card."""
from __future__ import annotations

from PySide6.QtWidgets import QAbstractSpinBox, QHBoxLayout, QPushButton, QWidget

from core import options as opt
from core.models import ProjectData
from core.utils import aspect_ratio

from .widgets import ChoiceField, NoWheelComboBox, NoWheelSpinBox, SectionCard, TextArea, label


class OutputCard(SectionCard):
    section_id = "output"
    title = "Output Settings"
    subtitle = "Pick a preset or type any size. The aspect ratio updates automatically."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.preset = NoWheelComboBox()
        self.preset.addItems([name for name, _w, _h in opt.OUTPUT_PRESETS] + [opt.PRESET_CUSTOM_LABEL])
        self.width_in = NoWheelSpinBox()
        self.height_in = NoWheelSpinBox()
        for spin in (self.width_in, self.height_in):
            spin.setRange(1, 30000)
            spin.setSuffix(" px")
            spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
            spin.setKeyboardTracking(False)

        self.ratio_label = label("", "Ratio")

        self.add_row(self.field("Size preset", self.preset, "preset", "Common social and marketplace sizes."),
                     self.field("Width", self.width_in, "width", "Output width in pixels.", required=True),
                     self.field("Height", self.height_in, "height", "Output height in pixels.", required=True))
        self.add_row(self._ratio_box())

        self.intended_use = ChoiceField(opt.INTENDED_USES, custom_label=opt.OTHER, custom_placeholder="Where will this be used?")
        self.quality = ChoiceField(opt.OUTPUT_QUALITIES, searchable=False)
        self.add_row(self.field("Intended use", self.intended_use, "intended_use",
                                "Helps the AI match platform conventions."),
                     self.field("Output quality", self.quality, "quality"))

        self.preset.currentIndexChanged.connect(self._on_preset)
        self.width_in.valueChanged.connect(self._on_size_edited)
        self.height_in.valueChanged.connect(self._on_size_edited)

    def _ratio_box(self) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(label("Aspect ratio:", "Hint"))
        lay.addWidget(self.ratio_label)
        lay.addStretch(1)
        return box

    def _set_size(self, width: int, height: int) -> None:
        for spin, value in ((self.width_in, width), (self.height_in, height)):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self._sync_preset_and_ratio()

    def _sync_preset_and_ratio(self) -> None:
        size = (self.width_in.value(), self.height_in.value())
        index = next((i for i, (_n, w, h) in enumerate(opt.OUTPUT_PRESETS) if (w, h) == size), len(opt.OUTPUT_PRESETS))
        self.preset.blockSignals(True)
        self.preset.setCurrentIndex(index)
        self.preset.blockSignals(False)
        self.ratio_label.setText(aspect_ratio(*size) or "—")

    def _on_preset(self, index: int) -> None:
        if index < len(opt.OUTPUT_PRESETS):
            _n, w, h = opt.OUTPUT_PRESETS[index]
            self._set_size(w, h)
            self.changed.emit()

    def _on_size_edited(self, _value: int) -> None:
        self._sync_preset_and_ratio()

    def load(self, data: ProjectData) -> None:
        o = data.output
        self._set_size(o.width, o.height)
        self.intended_use.set_value(o.intended_use)
        self.quality.set_value(o.quality)

    def collect(self, data: ProjectData) -> None:
        o = data.output
        o.width, o.height = self.width_in.value(), self.height_in.value()
        o.intended_use = self.intended_use.value()
        o.quality = self.quality.value()


class RestrictionsCard(SectionCard):
    section_id = "restrictions"
    title = "Restrictions"
    subtitle = "Things the AI must avoid — one per line. Edit, remove or add your own."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = TextArea(11)
        self.add_row(self.field("Things the AI must avoid", self.text, "text",
                                "Each line becomes one entry in the JSON restrictions list."))
        self.restore_btn = QPushButton("Restore default restrictions")
        self.restore_btn.setObjectName("Ghost")
        self.restore_btn.clicked.connect(lambda: self.text.setPlainText(opt.DEFAULT_RESTRICTIONS_TEXT))
        self.add_button_row(self.restore_btn)

    def load(self, data: ProjectData) -> None:
        self.text.setPlainText(data.restrictions.text)

    def collect(self, data: ProjectData) -> None:
        data.restrictions.text = self.text.toPlainText()
