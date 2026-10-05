"""Turns a `ProjectData` into the structured prompt dictionary / JSON text.

Key names and order follow the brief's template, with the scene/style reference removed. The only
additive key is `visual_style.avoid_ai_look_instruction` (when AI look avoidance is on). Images are
referenced by file name only: no folder locations and no embedded image data.
"""
from __future__ import annotations

import json
from typing import Any

from . import options as opt
from .models import ProjectData
from .prompt_builder import build_final_instruction, build_identity_lock
from .utils import aspect_ratio, file_name, image_entry, num, split_lines

TASK = "generate_product_image"


def build_prompt_json(data: ProjectData) -> dict[str, Any]:
    ref, p = data.reference, data.product

    style: dict[str, Any] = {
        "photography_style": data.style.photography_style,
        "realism_level": data.style.realism_level,
        "avoid_ai_look": data.style.avoid_ai_look,
    }
    if data.style.avoid_ai_look:
        style["avoid_ai_look_instruction"] = opt.AI_LOOK_AVOIDANCE_TEXT

    return {
        "task": TASK,
        "reference_images": {
            "product_identity": {
                "images": [image_entry(path) for path in ref.product_images],
                "primary_reference": file_name(ref.effective_primary()),
                "role": opt.PRODUCT_REFERENCE_ROLE,
            },
        },
        "product": {
            "name": p.name.strip(),
            "category": p.category.strip(),
            "dimensions_cm": {
                "width": num(p.width),
                "height": num(p.height),
                "depth": num(p.depth),
                "diameter": num(p.diameter),
            },
            "materials": p.resolved_materials(),
            "colour": p.colour.strip(),
            "transparency": p.transparency,
            "features": split_lines(p.features),
            "important_details": p.important_details.strip(),
            "identity_lock": build_identity_lock(data),
        },
        "scene": {
            "type": data.scene.scene_type.strip(),
            "environment": data.scene.environment.strip(),
            "surroundings": data.scene.surroundings.strip(),
            "background": data.scene.background,
            "time_of_day": data.scene.time_of_day,
        },
        "product_state": {
            "states": data.state.resolved_states(),
            "custom": data.state.custom.strip(),
        },
        "contents": _contents(data),
        "human_model": _human_model(data),
        "camera": {
            "angle": data.camera.angle.strip(),
            "distance": data.camera.distance,
            "lens": data.camera.lens,
            "depth_of_field": data.camera.depth_of_field,
            "perspective": data.camera.perspective.strip(),
        },
        "composition": {
            "product_position": data.composition.product_position.strip(),
            "product_frame_occupancy_percent": data.composition.occupancy_percent,
            "style": data.composition.style.strip(),
            "framing": data.composition.framing,
            "space_for_text": {
                "enabled": data.composition.space_for_text,
                "position": data.composition.text_position if data.composition.space_for_text else "",
            },
        },
        "lighting": {
            "type": data.lighting.type.strip(),
            "direction": data.lighting.direction,
            "shadow_style": data.lighting.shadow_style,
            "reflection_level": data.lighting.reflection_level,
            "colour_temperature": data.lighting.colour_temperature,
        },
        "visual_style": style,
        "output": {
            "width": data.output.width or None,
            "height": data.output.height or None,
            "aspect_ratio": aspect_ratio(data.output.width, data.output.height),
            "intended_use": data.output.intended_use,
            "quality": data.output.quality.lower(),
        },
        "restrictions": split_lines(data.restrictions.text),
        "final_instruction": build_final_instruction(data),
    }


def _contents(data: ProjectData) -> dict[str, Any]:
    c = data.contents
    if not c.enabled:                     # switched off: no food/liquid data in the prompt
        return {"enabled": False}
    return {
        "enabled": True,
        "type": c.content_type,
        "name": c.name.strip(),
        "appearance": c.appearance.strip(),
        "fill_level": c.fill_level,
        "steam": c.steam,
    }


def _human_model(data: ProjectData) -> dict[str, Any]:
    m = data.model
    if not m.enabled:                     # switched off: no model data in the prompt
        return {"enabled": False}
    return {
        "enabled": True,
        "gender_presentation": m.gender_presentation,
        "age_range": m.age_range.strip(),
        "appearance": m.appearance.strip(),
        "clothing": m.clothing.strip(),
        "action": m.action.strip(),
        "visible_body_area": m.visible_body_area,
        "expression": m.expression.strip(),
        "styling_notes": m.styling_notes.strip(),
    }


def to_json_text(prompt: dict[str, Any]) -> str:
    """Pretty-printed UTF-8 JSON (non-ASCII such as '–' and '×' stay readable)."""
    return json.dumps(prompt, indent=2, ensure_ascii=False)
