"""A complete sample project (the microwave / noodles scenario) used by tests and the examples folder."""
from __future__ import annotations

from .models import ProjectData


def sample_project() -> ProjectData:
    d = ProjectData()
    d.reference.product_images = [
        "C:/ProductReferences/front.jpg",
        "C:/ProductReferences/side.jpg",
        "C:/ProductReferences/lid.jpg",
    ]
    d.reference.primary_path = "C:/ProductReferences/front.jpg"

    d.product.name = "Glasafe Borosilicate Container"
    d.product.category = "Glass container"
    d.product.width, d.product.height, d.product.depth = 22.0, 7.5, 15.0
    d.product.materials = ["Borosilicate glass", "Silicone"]
    d.product.colour = "clear"
    d.product.transparency = "Transparent"
    d.product.features = "- Air vent lid\n- Snap-lock clips\n"
    d.product.important_details = "Vent sits on the left of the lid."

    d.scene.scene_type = "Kitchen"
    d.scene.environment = "Modern Indian kitchen with neutral cabinetry."
    d.state.states = ["Lid attached", "Vent open"]

    d.contents.enabled = True
    d.contents.content_type = "Food"
    d.contents.name = "Noodles"
    d.contents.steam = "None"

    d.model.enabled = True
    d.model.gender_presentation = "Female"
    d.model.age_range = "25–35"
    d.model.appearance = "Indian"
    d.model.action = "Placing the product inside a microwave"

    d.camera.angle = "3/4 front"
    d.camera.perspective = "Natural"
    d.camera.distance = "Medium"
    d.composition.style = "Lifestyle"
    d.composition.framing = "Medium"
    d.lighting.type = "Natural daylight"
    d.lighting.shadow_style = "Natural"
    d.style.photography_style = "Photorealistic"
    d.output.width, d.output.height = 1080, 1350
    d.output.intended_use = "Meta Ads"
    return d
