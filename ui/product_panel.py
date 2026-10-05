"""Product details, identity lock, product state and food / liquid cards."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCompleter, QLineEdit, QVBoxLayout, QWidget

from core import options as opt
from core.models import ProjectData

from .widgets import ChipGroup, ChoiceField, OptionalNumberField, SectionCard, TextArea, ToggleSwitch, label


class ProductDetailsCard(SectionCard):
    section_id = "product"
    title = "Product Details"
    subtitle = "Describe the new product. Everything here is treated as fact the AI must respect."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Glasafe 900 ml Borosilicate Lunch Box")
        self.add_row(self.field("Product name", self.name_edit, "name", "The name of the product.", required=True))

        self.category = ChoiceField(opt.PRODUCT_CATEGORIES, custom_label=opt.OTHER, searchable=False,
                                    custom_placeholder="Describe the category")
        self.transparency = ChoiceField(opt.TRANSPARENCY, searchable=False)
        self.add_row(
            self.field("Product category", self.category, "category", "Pick a category or choose Other to type your own."),
            self.field("Transparency", self.transparency, "transparency",
                       "How see-through the product body is."))

        self.width_in = OptionalNumberField()
        self.height_in = OptionalNumberField()
        self.depth_in = OptionalNumberField()
        self.diameter_in = OptionalNumberField()
        self.register("dimensions", self.width_in)
        self.add_row(
            self.field("Width (cm)", self.width_in, "width", "Product width in centimetres."),
            self.field("Height (cm)", self.height_in, "height", "Product height in centimetres."),
            self.field("Depth (cm)", self.depth_in, "depth", "Product depth in centimetres."),
            self.field("Diameter (cm) · optional", self.diameter_in, "diameter",
                       "For round products only. Leave as “Not set” otherwise."))
        self.add_widget(label("Enter at least one dimension.", "Hint"))

        self.materials = ChipGroup(opt.MATERIALS)
        self.other_material = QLineEdit()
        self.other_material.setPlaceholderText("Which other material?")
        self.other_material.setVisible(False)
        self.materials.toggled.connect(self._on_material_toggled)
        mat_box = QWidget()
        mat_lay = QVBoxLayout(mat_box)
        mat_lay.setContentsMargins(0, 0, 0, 0)
        mat_lay.setSpacing(10)
        mat_lay.addWidget(self.materials)
        mat_lay.addWidget(self.other_material)
        self.register("other_material", self.other_material)
        self.watch(self.other_material)
        self.add_row(self.field("Product material", mat_box, "materials", "Select every material the product uses."))

        self.colour = QLineEdit()
        self.colour.setPlaceholderText("e.g. Clear glass with a grey silicone sleeve")
        self.add_row(self.field("Product colour", self.colour, "colour", "Describe the colours exactly as they appear."))

        self.features = TextArea(4, "One per line, e.g.\n- Air vent lid\n- Silicone sleeve\n- Snap-lock clips\n- Carry handle")
        self.add_row(self.field("Product features", self.features, "features",
                                "List each feature on its own line. These are preserved in the image."))
        self.important = TextArea(5, "Exact construction details that must be preserved, e.g. “Vent sits on the left of "
                                     "the lid; clips are grey; logo is embossed on the base.”")
        self.add_row(self.field("Important product details", self.important, "important_details",
                                "Use this for construction details the AI must not change."))

    def _on_material_toggled(self, text: str, checked: bool) -> None:
        if text == opt.OTHER:
            self.other_material.setVisible(checked)

    def load(self, data: ProjectData) -> None:
        p = data.product
        self.name_edit.setText(p.name)
        self.category.set_value(p.category)
        self.transparency.set_value(p.transparency)
        self.width_in.set_optional_value(p.width)
        self.height_in.set_optional_value(p.height)
        self.depth_in.set_optional_value(p.depth)
        self.diameter_in.set_optional_value(p.diameter)
        self.materials.set_values(p.materials)
        self.other_material.setText(p.other_material)
        self.colour.setText(p.colour)
        self.features.setPlainText(p.features)
        self.important.setPlainText(p.important_details)

    def collect(self, data: ProjectData) -> None:
        p = data.product
        p.name = self.name_edit.text().strip()
        p.category = self.category.value()
        p.transparency = self.transparency.value()
        p.width = self.width_in.optional_value()
        p.height = self.height_in.optional_value()
        p.depth = self.depth_in.optional_value()
        p.diameter = self.diameter_in.optional_value()
        p.materials = self.materials.values()
        p.other_material = self.other_material.text().strip()
        p.colour = self.colour.text().strip()
        p.features = self.features.toPlainText()
        p.important_details = self.important.toPlainText().strip()


class IdentityLockCard(SectionCard):
    section_id = "identity"
    title = "Product Identity Lock"
    subtitle = "Stops the AI from redesigning, simplifying or swapping your product."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toggle = ToggleSwitch("Strict Product Identity Lock", checked=True)
        self.toggle.setToolTip("When on, the full identity-lock paragraph below is added to the JSON.")
        self.register("enabled", self.toggle)
        self.watch(self.toggle)
        self.add_widget(self.toggle)

        self.lock_text = label(opt.IDENTITY_LOCK_TEXT, "LockText", wrap=True)
        self.add_widget(self.lock_text)
        self.toggle.toggled.connect(self.lock_text.setVisible)

        self.custom = TextArea(3, "Optional extra rules, e.g. “The red dot on the lid must stay exactly where it is.”")
        self.add_row(self.field("Custom identity-lock instructions", self.custom, "custom",
                                "Added after the standard lock text. Works even when the strict lock is off."))

    def load(self, data: ProjectData) -> None:
        self.toggle.setChecked(data.identity.enabled)
        self.lock_text.setVisible(data.identity.enabled)
        self.custom.setPlainText(data.identity.custom)

    def collect(self, data: ProjectData) -> None:
        data.identity.enabled = self.toggle.isChecked()
        data.identity.custom = self.custom.toPlainText().strip()


class ProductStateCard(SectionCard):
    section_id = "state"
    title = "Product State"
    subtitle = "What condition is the product in, and what is happening to it?"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.states = ChipGroup(opt.PRODUCT_STATES)
        self.add_row(self.field("Product state", self.states, "states", "Select everything that applies."))
        self.custom = QLineEdit()
        self.custom.setPlaceholderText("e.g. Lid resting on the counter next to the container")
        self.add_row(self.field("Custom product state", self.custom, "custom",
                                "Anything the options above do not cover."))

    def load(self, data: ProjectData) -> None:
        self.states.set_values(data.state.states)
        self.custom.setText(data.state.custom)

    def collect(self, data: ProjectData) -> None:
        data.state.states = self.states.values()
        data.state.custom = self.custom.text().strip()


class ContentsCard(SectionCard):
    section_id = "contents"
    title = "Food / Liquid"
    subtitle = "Only included in the prompt when switched on."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toggle = ToggleSwitch("Does the product contain food or liquid?")
        self.register("enabled", self.toggle)
        self.watch(self.toggle)
        self.add_widget(self.toggle)

        self.container = QWidget()
        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(18)

        self.content_type = ChoiceField(opt.CONTENT_TYPES, searchable=False)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Chicken salad, Noodles, Coffee")
        completer = QCompleter(opt.FOOD_EXAMPLES, self.name_edit)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.name_edit.setCompleter(completer)
        self.add_row(
            self.field("Content type", self.content_type, "type", "Food, liquid or both."),
            self.field("Food / liquid name", self.name_edit, "name", "Start typing for suggestions."),
            parent=inner)

        self.appearance = TextArea(3, "e.g. Fresh chicken salad with lettuce, cherry tomatoes and grilled chicken.")
        self.add_row(self.field("Food appearance", self.appearance, "appearance",
                                "How the food or liquid should look."), parent=inner)

        self.fill_level = ChoiceField(opt.FILL_LEVELS, searchable=False)
        self.steam = ChoiceField(opt.STEAM_LEVELS, searchable=False)
        self.add_row(self.field("Fill level", self.fill_level, "fill_level", "How full the product is."),
                     self.field("Steam", self.steam, "steam", "Steam rising from hot contents."), parent=inner)

        self.add_widget(self.container)
        self.toggle.toggled.connect(self.container.setVisible)

    def load(self, data: ProjectData) -> None:
        c = data.contents
        self.toggle.setChecked(c.enabled)
        self.container.setVisible(c.enabled)
        self.content_type.set_value(c.content_type)
        self.name_edit.setText(c.name)
        self.appearance.setPlainText(c.appearance)
        self.fill_level.set_value(c.fill_level)
        self.steam.set_value(c.steam)

    def collect(self, data: ProjectData) -> None:
        c = data.contents
        c.enabled = self.toggle.isChecked()
        c.content_type = self.content_type.value()
        c.name = self.name_edit.text().strip()
        c.appearance = self.appearance.toPlainText().strip()
        c.fill_level = self.fill_level.value()
        c.steam = self.steam.value()
