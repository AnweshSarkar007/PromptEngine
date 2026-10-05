"""Photography cards: camera, lighting, composition and visual style."""
from __future__ import annotations

from PySide6.QtWidgets import QPushButton

from core import options as opt
from core.models import ProjectData

from .widgets import ChoiceField, SectionCard, SliderField, ToggleSwitch, label


class CameraCard(SectionCard):
    section_id = "camera"
    title = "Camera"
    subtitle = "How the shot is framed. Camera angle is required."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = ChoiceField(opt.CAMERA_ANGLES, custom_label=opt.CUSTOM, custom_placeholder="Describe the camera angle")
        self.distance = ChoiceField(opt.CAMERA_DISTANCES, searchable=False)
        self.add_row(
            self.field("Camera angle", self.angle, "angle", "Where the camera sits relative to the product.", required=True),
            self.field("Camera distance", self.distance, "distance", "How close the camera is."))

        self.lens = ChoiceField(opt.LENS_STYLES, searchable=False)
        self.dof = ChoiceField(opt.DEPTH_OF_FIELD, searchable=False)
        self.add_row(
            self.field("Lens style", self.lens, "lens", "Focal length / lens type. Auto lets the AI decide."),
            self.field("Depth of field", self.dof, "depth_of_field", "How much of the scene is in focus."))

        self.perspective = ChoiceField(opt.PERSPECTIVES, custom_label=opt.CUSTOM, searchable=False,
                                       custom_placeholder="Describe the perspective")
        self.add_row(self.field("Perspective", self.perspective, "perspective",
                                "Ecommerce accurate keeps proportions true to life."))

    def load(self, data: ProjectData) -> None:
        c = data.camera
        self.angle.set_value(c.angle)
        self.distance.set_value(c.distance)
        self.lens.set_value(c.lens)
        self.dof.set_value(c.depth_of_field)
        self.perspective.set_value(c.perspective)

    def collect(self, data: ProjectData) -> None:
        c = data.camera
        c.angle = self.angle.value()
        c.distance = self.distance.value()
        c.lens = self.lens.value()
        c.depth_of_field = self.dof.value()
        c.perspective = self.perspective.value()


class LightingCard(SectionCard):
    section_id = "lighting"
    title = "Lighting"
    subtitle = "The light sets the mood, the shadows and how glass and metal reflect."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.type = ChoiceField(opt.LIGHTING_TYPES, custom_label=opt.CUSTOM, custom_placeholder="Describe the lighting")
        self.direction = ChoiceField(opt.LIGHT_DIRECTIONS, searchable=False)
        self.add_row(self.field("Lighting type", self.type, "type"),
                     self.field("Light direction", self.direction, "direction", "Where the main light comes from."))

        self.shadow = ChoiceField(opt.SHADOW_STYLES, searchable=False)
        self.reflection = ChoiceField(opt.REFLECTION_LEVELS, searchable=False)
        self.temperature = ChoiceField(opt.COLOUR_TEMPERATURES, searchable=False)
        self.add_row(self.field("Shadow style", self.shadow, "shadow_style"),
                     self.field("Reflection level", self.reflection, "reflection_level",
                                "Important for glass and polished surfaces."),
                     self.field("Colour temperature", self.temperature, "colour_temperature"))

    def load(self, data: ProjectData) -> None:
        lt = data.lighting
        self.type.set_value(lt.type)
        self.direction.set_value(lt.direction)
        self.shadow.set_value(lt.shadow_style)
        self.reflection.set_value(lt.reflection_level)
        self.temperature.set_value(lt.colour_temperature)

    def collect(self, data: ProjectData) -> None:
        lt = data.lighting
        lt.type = self.type.value()
        lt.direction = self.direction.value()
        lt.shadow_style = self.shadow.value()
        lt.reflection_level = self.reflection.value()
        lt.colour_temperature = self.temperature.value()


class CompositionCard(SectionCard):
    section_id = "composition"
    title = "Composition"
    subtitle = "Where the product sits in the frame and how much of it the product fills."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.position = ChoiceField(opt.PRODUCT_POSITIONS, custom_label=opt.CUSTOM, searchable=False,
                                    custom_placeholder="Describe the position")
        self.style = ChoiceField(opt.COMPOSITION_STYLES, custom_label=opt.CUSTOM, custom_placeholder="Describe the style")
        self.add_row(self.field("Product position", self.position, "product_position"),
                     self.field("Composition style", self.style, "style", "The kind of image this should feel like."))

        self.occupancy = SliderField(10, 90, 50, "{v}%")
        self.framing = ChoiceField(opt.FRAMINGS, searchable=False)
        self.add_row(self.field("Product frame occupancy", self.occupancy, "occupancy",
                                "How much of the image area the product fills."),
                     self.field("Framing", self.framing, "framing", "Tight crops close in; loose leaves breathing room."))

        self.text_toggle = ToggleSwitch("Leave space for text")
        self.text_toggle.setToolTip("Keeps an area clear for headlines or logos added later.")
        self.register("space_for_text", self.text_toggle)
        self.watch(self.text_toggle)
        self.text_position = ChoiceField(opt.TEXT_SPACE_POSITIONS, searchable=False)
        self.text_box = self.field("Space for text — position", self.text_position, "text_position")
        self.text_box.setVisible(False)
        self.text_toggle.toggled.connect(self.text_box.setVisible)
        self.add_widget(self.text_toggle)
        self.add_row(self.text_box)

    def load(self, data: ProjectData) -> None:
        c = data.composition
        self.position.set_value(c.product_position)
        self.style.set_value(c.style)
        self.occupancy.set_value(c.occupancy_percent)
        self.framing.set_value(c.framing)
        self.text_toggle.setChecked(c.space_for_text)
        self.text_box.setVisible(c.space_for_text)
        self.text_position.set_value(c.text_position)

    def collect(self, data: ProjectData) -> None:
        c = data.composition
        c.product_position = self.position.value()
        c.style = self.style.value()
        c.occupancy_percent = self.occupancy.value()
        c.framing = self.framing.value()
        c.space_for_text = self.text_toggle.isChecked()
        c.text_position = self.text_position.value() or "Top"


class VisualStyleCard(SectionCard):
    section_id = "style"
    title = "Visual Style"
    subtitle = "The overall photographic look and how real it should feel."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.photo_style = ChoiceField(opt.PHOTOGRAPHY_STYLES, searchable=False)
        self.add_row(self.field("Photography style", self.photo_style, "photography_style"))

        self.realism = SliderField(1, 10, opt.DEFAULT_REALISM, "{v} / 10")
        self.reset_realism = QPushButton(f"Use recommended ({opt.DEFAULT_REALISM})")
        self.reset_realism.setObjectName("Ghost")
        self.reset_realism.clicked.connect(lambda: self.realism.slider.setValue(opt.DEFAULT_REALISM))
        box = self.field("Realism level", self.realism, "realism_level",
                         f"1 = stylised, 10 = indistinguishable from a real photo. Recommended: {opt.DEFAULT_REALISM}.")
        self.add_row(box)
        self.add_button_row(self.reset_realism)

        self.ai_toggle = ToggleSwitch("AI look avoidance", checked=True)
        self.ai_toggle.setToolTip("Adds an instruction that steers the model away from typical AI-image artefacts.")
        self.register("avoid_ai_look", self.ai_toggle)
        self.watch(self.ai_toggle)
        self.ai_text = label(opt.AI_LOOK_AVOIDANCE_TEXT, "LockText", wrap=True)
        self.ai_toggle.toggled.connect(self.ai_text.setVisible)
        self.add_widget(self.ai_toggle)
        self.add_widget(self.ai_text)

    def load(self, data: ProjectData) -> None:
        s = data.style
        self.photo_style.set_value(s.photography_style)
        self.realism.set_value(s.realism_level)
        self.ai_toggle.setChecked(s.avoid_ai_look)
        self.ai_text.setVisible(s.avoid_ai_look)

    def collect(self, data: ProjectData) -> None:
        s = data.style
        s.photography_style = self.photo_style.value()
        s.realism_level = self.realism.value()
        s.avoid_ai_look = self.ai_toggle.isChecked()
