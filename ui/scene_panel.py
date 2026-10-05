"""Scene & environment card."""
from __future__ import annotations

from core import options as opt
from core.models import ProjectData

from .widgets import ChoiceField, SectionCard, TextArea


class SceneCard(SectionCard):
    section_id = "scene"
    title = "Scene & Environment"
    subtitle = "Where the product appears and what surrounds it."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_type = ChoiceField(opt.SCENE_TYPES, custom_label=opt.CUSTOM, custom_placeholder="Describe the scene type")
        self.background = ChoiceField(opt.BACKGROUND_TYPES, searchable=False)
        self.add_row(
            self.field("Scene type", self.scene_type, "scene_type", "Start typing to search the list."),
            self.field("Background type", self.background, "background", "How sharp or soft the background is."))

        self.environment = TextArea(4, "e.g. Modern Indian kitchen with neutral cabinetry, clean countertop and "
                                       "realistic everyday styling.")
        self.add_row(self.field("Environment description", self.environment, "environment",
                                "Describe the place in a sentence or two. Required unless a scene type is chosen.",
                                required=True))

        self.surroundings = TextArea(3, "Props and objects around the product, one per line or as a sentence.")
        self.time_of_day = ChoiceField(opt.TIMES_OF_DAY, searchable=False)
        self.add_row(self.field("Surroundings", self.surroundings, "surroundings",
                                "Other objects that should appear near the product."),
                     self.field("Time of day", self.time_of_day, "time_of_day",
                                "Sets the mood of natural light."))

    def load(self, data: ProjectData) -> None:
        s = data.scene
        self.scene_type.set_value(s.scene_type)
        self.environment.setPlainText(s.environment)
        self.surroundings.setPlainText(s.surroundings)
        self.background.set_value(s.background)
        self.time_of_day.set_value(s.time_of_day)

    def collect(self, data: ProjectData) -> None:
        s = data.scene
        s.scene_type = self.scene_type.value()
        s.environment = self.environment.toPlainText().strip()
        s.surroundings = self.surroundings.toPlainText().strip()
        s.background = self.background.value()
        s.time_of_day = self.time_of_day.value()
