"""ChatGPT brief: the instruction to send ChatGPT with the old product photo, and the importer
that reads ChatGPT's reply back into the form.

Both sides are generated from one field table (`FIELDS`), so the option lists ChatGPT is asked to
choose from always match the app's dropdowns. Everything runs offline: the app never talks to
ChatGPT, it only reads text you paste.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from . import options as opt
from .models import ProjectData
from .utils import aspect_ratio

BRIEF_FORMAT = "product-image-prompt-builder/brief-v1"


@dataclass(frozen=True)
class BriefField:
    section: str                    # section name in the brief JSON
    key: str                        # key inside that section
    target: str                     # "<ProjectData attribute>.<field>" it fills
    label: str                      # shown in the import summary
    kind: str = "text"              # text | choice | multi | bool | int
    options: tuple[str, ...] = ()
    hint: str = ""                  # placeholder text written into the template
    limits: tuple[int, int] = (0, 0)
    default: Any = None             # value written into the template for bool / int


def _choices(items: list[str]) -> tuple[str, ...]:
    """Dropdown options without the 'Custom' / 'Other' escape hatch (ChatGPT writes its own text)."""
    return tuple(i for i in items if i not in (opt.CUSTOM, opt.OTHER))


FIELDS: list[BriefField] = [
    BriefField("scene", "type", "scene.scene_type", "Scene type", "choice", _choices(opt.SCENE_TYPES)),
    BriefField("scene", "environment", "scene.environment", "Environment",
               hint="one or two sentences describing the setting"),
    BriefField("scene", "surroundings", "scene.surroundings", "Surroundings",
               hint="props and objects around the product"),
    BriefField("scene", "background", "scene.background", "Background", "choice", _choices(opt.BACKGROUND_TYPES)),
    BriefField("scene", "time_of_day", "scene.time_of_day", "Time of day", "choice", _choices(opt.TIMES_OF_DAY)),

    BriefField("product_state", "states", "state.states", "Product state", "multi", _choices(opt.PRODUCT_STATES)),
    BriefField("product_state", "custom", "state.custom", "Custom product state"),

    BriefField("contents", "enabled", "contents.enabled", "Food / liquid on/off", "bool", default=True),
    BriefField("contents", "type", "contents.content_type", "Content type", "choice", _choices(opt.CONTENT_TYPES)),
    BriefField("contents", "name", "contents.name", "Food / liquid name"),
    BriefField("contents", "appearance", "contents.appearance", "Food appearance"),
    BriefField("contents", "fill_level", "contents.fill_level", "Fill level", "choice", _choices(opt.FILL_LEVELS)),
    BriefField("contents", "steam", "contents.steam", "Steam", "choice", _choices(opt.STEAM_LEVELS)),

    BriefField("human_model", "enabled", "model.enabled", "Human model on/off", "bool", default=True),
    BriefField("human_model", "gender_presentation", "model.gender_presentation", "Gender presentation",
               "choice", _choices(opt.GENDERS)),
    BriefField("human_model", "age_range", "model.age_range", "Age range", "choice", _choices(opt.AGE_RANGES)),
    BriefField("human_model", "appearance", "model.appearance", "Model appearance"),
    BriefField("human_model", "clothing", "model.clothing", "Clothing"),
    BriefField("human_model", "action", "model.action", "Model action",
               hint="start with an -ing verb, e.g. Holding the product"),
    BriefField("human_model", "visible_body_area", "model.visible_body_area", "Visible body area",
               "choice", _choices(opt.BODY_AREAS)),
    BriefField("human_model", "expression", "model.expression", "Expression", "choice", _choices(opt.EXPRESSIONS)),
    BriefField("human_model", "styling_notes", "model.styling_notes", "Model styling notes"),

    BriefField("camera", "angle", "camera.angle", "Camera angle", "choice", _choices(opt.CAMERA_ANGLES)),
    BriefField("camera", "distance", "camera.distance", "Camera distance", "choice", _choices(opt.CAMERA_DISTANCES)),
    BriefField("camera", "lens", "camera.lens", "Lens", "choice", _choices(opt.LENS_STYLES)),
    BriefField("camera", "depth_of_field", "camera.depth_of_field", "Depth of field", "choice",
               _choices(opt.DEPTH_OF_FIELD)),
    BriefField("camera", "perspective", "camera.perspective", "Perspective", "choice", _choices(opt.PERSPECTIVES)),

    BriefField("composition", "product_position", "composition.product_position", "Product position", "choice",
               _choices(opt.PRODUCT_POSITIONS)),
    BriefField("composition", "product_frame_occupancy_percent", "composition.occupancy_percent",
               "Frame occupancy", "int", limits=(10, 90), default=50),
    BriefField("composition", "style", "composition.style", "Composition style", "choice",
               _choices(opt.COMPOSITION_STYLES)),
    BriefField("composition", "framing", "composition.framing", "Framing", "choice", _choices(opt.FRAMINGS)),

    BriefField("lighting", "type", "lighting.type", "Lighting type", "choice", _choices(opt.LIGHTING_TYPES)),
    BriefField("lighting", "direction", "lighting.direction", "Light direction", "choice",
               _choices(opt.LIGHT_DIRECTIONS)),
    BriefField("lighting", "shadow_style", "lighting.shadow_style", "Shadow style", "choice",
               _choices(opt.SHADOW_STYLES)),
    BriefField("lighting", "reflection_level", "lighting.reflection_level", "Reflection level", "choice",
               _choices(opt.REFLECTION_LEVELS)),
    BriefField("lighting", "colour_temperature", "lighting.colour_temperature", "Colour temperature", "choice",
               _choices(opt.COLOUR_TEMPERATURES)),

    BriefField("visual_style", "photography_style", "style.photography_style", "Photography style", "choice",
               _choices(opt.PHOTOGRAPHY_STYLES)),
    BriefField("visual_style", "realism_level", "style.realism_level", "Realism level", "int",
               limits=(1, 10), default=opt.DEFAULT_REALISM),
]

ASPECT_HINT = "shape of the photo, e.g. 1:1, 4:5, 3:4, 9:16"

INSTRUCTION_HEADER = """\
I'm attaching an OLD product photo from our existing catalogue. I will create a NEW photo of a
DIFFERENT, new product in the same vibe, using a separate tool.

Study the photo and describe ONLY its photography and scene: setting, props, camera, lighting,
composition, mood, any person, any food or drink.
Do NOT describe the old product's shape, design, colour, logo or features.

Reply with ONLY the JSON below, filled in, inside one ```json code block. Rules:
- Where options are separated by "|", copy exactly ONE of them (for [ ] lists you may pick
  several). If none fits, write your own short text instead.
- Use "" for anything you cannot tell. Do not invent details that are not in the photo.
- If there is no food/drink or no person, set that section's "enabled" to false.
"""


# --------------------------------------------------------------------------- #
# Instruction (what you paste into ChatGPT)
# --------------------------------------------------------------------------- #
def brief_template() -> dict[str, Any]:
    tpl: dict[str, Any] = {"format": BRIEF_FORMAT}
    for f in FIELDS:
        section = tpl.setdefault(f.section, {})
        if f.kind == "choice":
            section[f.key] = " | ".join(f.options)
        elif f.kind == "multi":
            section[f.key] = [" | ".join(f.options)]
        elif f.kind in ("bool", "int"):
            section[f.key] = f.default
        else:
            section[f.key] = f.hint
        if (f.section, f.key) == ("composition", "framing"):
            section["space_for_text"] = {"enabled": False,
                                         "position": " | ".join(opt.TEXT_SPACE_POSITIONS)}
    tpl["output"] = {"aspect_ratio": ASPECT_HINT}
    return tpl


def build_instruction() -> str:
    return INSTRUCTION_HEADER + "\n" + json.dumps(brief_template(), indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------- #
# Import (what you paste back into the app)
# --------------------------------------------------------------------------- #
@dataclass
class BriefImport:
    ok: bool
    message: str = ""
    filled: list[str] = field(default_factory=list)       # labels of fields that were set
    custom: list[str] = field(default_factory=list)       # set, but not one of the listed options
    skipped: list[str] = field(default_factory=list)      # present but unusable (e.g. option not chosen)


_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def extract_json(text: str) -> Optional[dict[str, Any]]:
    """Find the JSON object in a ChatGPT reply (code block, or the outermost {...})."""
    candidates = [m.group(1) for m in _FENCE.finditer(text or "")]
    start, end = (text or "").find("{"), (text or "").rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for candidate in candidates:
        for variant in (candidate, _repair(candidate)):
            try:
                obj = json.loads(variant)
            except ValueError:
                continue
            if isinstance(obj, dict):
                return obj
    return None


def _repair(s: str) -> str:
    """Forgive the usual chat-copy damage: curly quotes and trailing commas."""
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r",\s*([}\]])", r"\1", s)


def _norm(s: str) -> str:
    s = str(s).replace("–", "-").replace("—", "-").replace("centre", "center").replace("Centre", "Center")
    return re.sub(r"\s+", " ", s).strip().lower()


def match_option(value: str, options: tuple[str, ...]) -> Optional[str]:
    wanted = _norm(value)
    return next((o for o in options if _norm(o) == wanted), None)


def _text(value: Any) -> Optional[str]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip() or None
    return None


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and _norm(value) in ("true", "yes", "on"):
        return True
    if isinstance(value, str) and _norm(value) in ("false", "no", "off", "none"):
        return False
    return None


def _as_int(value: Any, limits: tuple[int, int]) -> Optional[int]:
    if isinstance(value, bool):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not m:
        return None
    return max(limits[0], min(limits[1], int(round(float(m.group())))))


def _set(data: ProjectData, target: str, value: Any) -> None:
    section, attr = target.split(".")
    setattr(getattr(data, section), attr, value)


def apply_brief(text: str, data: ProjectData) -> BriefImport:
    """Fill `data` from a pasted ChatGPT reply. Only fields ChatGPT actually filled are changed."""
    obj = extract_json(text)
    if obj is None:
        return BriefImport(False, "No JSON found in the pasted text. Paste ChatGPT's whole reply, "
                                  "including the part between the ``` marks.")
    sections = {f.section for f in FIELDS} | {"output", "product"}
    if not any(isinstance(obj.get(s), dict) for s in sections):
        return BriefImport(False, "The pasted JSON has none of the expected sections "
                                  "(scene, camera, lighting, composition …).")

    report = BriefImport(True)
    for f in FIELDS:
        section = obj.get(f.section)
        if isinstance(section, dict) and f.key in section:
            _apply_field(f, section[f.key], data, report)

    composition = obj.get("composition")
    if isinstance(composition, dict) and isinstance(composition.get("space_for_text"), dict):
        _apply_text_space(composition["space_for_text"], data, report)
    if isinstance(obj.get("output"), dict):
        _apply_output(obj["output"], data, report)
    if isinstance(obj.get("product"), dict):              # e.g. a JSON previously generated by this app
        _apply_product(obj["product"], data, report)

    if not report.filled:
        return BriefImport(False, "Nothing usable was found. It looks like ChatGPT left the template "
                                  "unfilled; ask it to fill in the values.", skipped=report.skipped)
    return report


def _apply_field(f: BriefField, raw: Any, data: ProjectData, report: BriefImport) -> None:
    if f.kind == "bool":
        value = _as_bool(raw)
        if value is None:
            report.skipped.append(f.label)
            return
        _set(data, f.target, value)
        report.filled.append(f.label)
        return

    if f.kind == "int":
        value = _as_int(raw, f.limits)
        if value is None:
            report.skipped.append(f.label)
            return
        _set(data, f.target, value)
        report.filled.append(f.label)
        return

    if f.kind == "multi":
        items = raw if isinstance(raw, list) else re.split(r"[,;]", str(raw or ""))
        chosen, extra = [], []
        for item in items:
            text = _text(item)
            if not text or "|" in text:                     # empty or the untouched option list
                continue
            hit = match_option(text, f.options)
            if hit:
                if hit not in chosen:
                    chosen.append(hit)
            else:
                extra.append(text)
        if not chosen and not extra:
            if any(_text(i) for i in items):
                report.skipped.append(f.label)
            return
        _set(data, f.target, chosen)
        if extra:                                           # unknown states go to the custom box
            data.state.custom = "; ".join(extra)
            report.custom.append(f.label)
        report.filled.append(f.label)
        return

    text = _text(raw)
    if text is None:
        return                                              # "" means ChatGPT could not tell
    if f.kind == "choice":
        if "|" in text:                                     # option list copied, nothing chosen
            report.skipped.append(f.label)
            return
        hit = match_option(text, f.options)
        if hit is None:
            report.custom.append(f.label)
        _set(data, f.target, hit or text)
        report.filled.append(f.label)
        return

    if f.hint and _norm(text) == _norm(f.hint):            # placeholder left as is
        report.skipped.append(f.label)
        return
    if f.target == "state.custom" and "Product state" in report.custom:   # keep states moved here above
        text = f"{text}; {data.state.custom}"
    _set(data, f.target, text)
    report.filled.append(f.label)


def _apply_text_space(raw: dict, data: ProjectData, report: BriefImport) -> None:
    enabled = _as_bool(raw.get("enabled"))
    if enabled is None:
        return
    data.composition.space_for_text = enabled
    report.filled.append("Space for text")
    pos = _text(raw.get("position"))
    if enabled and pos and "|" not in pos:
        hit = match_option(pos, tuple(opt.TEXT_SPACE_POSITIONS))
        if hit:
            data.composition.text_position = hit


def _apply_output(raw: dict, data: ProjectData, report: BriefImport) -> None:
    width, height = _as_int(raw.get("width"), (1, 30000)), _as_int(raw.get("height"), (1, 30000))
    if width and height:
        data.output.width, data.output.height = width, height
        report.filled.append("Output size")
        return
    ratio = _text(raw.get("aspect_ratio"))
    if not ratio or _norm(ratio) == _norm(ASPECT_HINT):
        return
    m = re.search(r"(\d+(?:\.\d+)?)\s*[:x×/]\s*(\d+(?:\.\d+)?)", ratio)
    if not m or float(m.group(1)) <= 0 or float(m.group(2)) <= 0:
        report.skipped.append("Output size")
        return
    rw, rh = float(m.group(1)), float(m.group(2))
    wanted = aspect_ratio(int(rw * 1000), int(rh * 1000))
    preset = next(((w, h) for _n, w, h in opt.OUTPUT_PRESETS if aspect_ratio(w, h) == wanted), None)
    data.output.width, data.output.height = preset or (1080, int(round(1080 * rh / rw)))
    report.filled.append("Output size")


def _apply_product(raw: dict, data: ProjectData, report: BriefImport) -> None:
    p = data.product
    for key, attr, label in (("name", "name", "Product name"), ("colour", "colour", "Product colour"),
                             ("important_details", "important_details", "Important product details")):
        text = _text(raw.get(key))
        if text:
            setattr(p, attr, text)
            report.filled.append(label)
    category = _text(raw.get("category"))
    if category and "|" not in category:
        p.category = match_option(category, tuple(opt.PRODUCT_CATEGORIES)) or category
        report.filled.append("Product category")
    transparency = _text(raw.get("transparency"))
    if transparency and "|" not in transparency:
        p.transparency = match_option(transparency, tuple(opt.TRANSPARENCY)) or transparency
        report.filled.append("Transparency")
    materials = raw.get("materials")
    if isinstance(materials, list) and materials:
        known, other = [], []
        for m in materials:
            text = _text(m)
            if text and "|" not in text:
                hit = match_option(text, _choices(opt.MATERIALS))
                (known.append(hit) if hit else other.append(text))
        if known or other:
            p.materials = known + ([opt.OTHER] if other else [])
            p.other_material = ", ".join(other)
            report.filled.append("Product material")
    features = raw.get("features")
    if isinstance(features, list) and any(_text(x) for x in features):
        p.features = "\n".join(f"- {_text(x)}" for x in features if _text(x))
        report.filled.append("Product features")
    dims = raw.get("dimensions_cm")
    if isinstance(dims, dict):
        for key in ("width", "height", "depth", "diameter"):
            value = dims.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                setattr(p, key, float(value))
                report.filled.append(f"Product {key}")
