"""Human model card (all fields hidden and left out of the prompt when switched off)."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from core import options as opt
from core.models import ProjectData

from .widgets import ChoiceField, SectionCard, TextArea, ToggleSwitch


class HumanModelCard(SectionCard):
    section_id = "model"
    title = "Human Model"
    subtitle = "Optional. When off, nothing about a model appears in the prompt."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toggle = ToggleSwitch("Include Human Model")
        self.register("enabled", self.toggle)
        self.watch(self.toggle)
        self.add_widget(self.toggle)

        self.container = QWidget()
        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(18)

        self.gender = ChoiceField(opt.GENDERS, searchable=False)
        self.age = ChoiceField(opt.AGE_RANGES, custom_label=opt.CUSTOM, searchable=False,
                               custom_placeholder="e.g. 60–70")
        self.add_row(self.field("Gender presentation", self.gender, "gender_presentation"),
                     self.field("Age range", self.age, "age_range"), parent=inner)

        self.appearance = QLineEdit()
        self.appearance.setPlaceholderText("e.g. Indian")
        self.clothing = QLineEdit()
        self.clothing.setPlaceholderText("e.g. Smart casual office outfit")
        self.add_row(self.field("Ethnicity / appearance", self.appearance, "appearance",
                                "Short phrases read best, e.g. “Indian” or “South Asian with short dark hair”."),
                     self.field("Clothing", self.clothing, "clothing"), parent=inner)

        self.action = TextArea(3, "e.g. Placing the product inside a microwave\nStart with an “-ing” verb for the "
                                  "best sentence flow: Holding / Eating from / Opening / Carrying …")
        self.add_row(self.field("Model action", self.action, "action",
                                "What the model is doing with the product."), parent=inner)

        self.body_area = ChoiceField(opt.BODY_AREAS, searchable=False)
        self.expression = ChoiceField(opt.EXPRESSIONS, custom_label=opt.CUSTOM, searchable=False,
                                      custom_placeholder="Describe the expression")
        self.add_row(self.field("Visible body area", self.body_area, "visible_body_area",
                                "How much of the person is in frame."),
                     self.field("Expression", self.expression, "expression"), parent=inner)

        self.notes = TextArea(3, "Hair, accessories, posture, anything else about how the model should look.")
        self.add_row(self.field("Model styling notes", self.notes, "styling_notes"), parent=inner)

        self.add_widget(self.container)
        self.toggle.toggled.connect(self.container.setVisible)

    def load(self, data: ProjectData) -> None:
        m = data.model
        self.toggle.setChecked(m.enabled)
        self.container.setVisible(m.enabled)
        self.gender.set_value(m.gender_presentation)
        self.age.set_value(m.age_range)
        self.appearance.setText(m.appearance)
        self.clothing.setText(m.clothing)
        self.action.setPlainText(m.action)
        self.body_area.set_value(m.visible_body_area)
        self.expression.set_value(m.expression)
        self.notes.setPlainText(m.styling_notes)

    def collect(self, data: ProjectData) -> None:
        m = data.model
        m.enabled = self.toggle.isChecked()
        m.gender_presentation = self.gender.value()
        m.age_range = self.age.value()
        m.appearance = self.appearance.text().strip()
        m.clothing = self.clothing.text().strip()
        m.action = self.action.toPlainText().strip()
        m.visible_body_area = self.body_area.value()
        m.expression = self.expression.value()
        m.styling_notes = self.notes.toPlainText().strip()
