"""Generates the natural-language `final_instruction` (and the plain-text export).

Deterministic template logic, no AI: every clause is only emitted when the user filled in the
matching field, and sections that are switched off (human model, food / liquid) are skipped.
"""
from __future__ import annotations

import re
from typing import Iterable

from . import options as opt
from .models import ProjectData
from .utils import aspect_ratio, file_name, split_lines

# --------------------------------------------------------------------------- #
# Wording tables
# --------------------------------------------------------------------------- #
_COMPOSITION_NOUN = {
    "Product hero": "product hero image",
    "Lifestyle": "lifestyle image",
    "Editorial": "editorial image",
    "Ecommerce": "ecommerce image",
    "UGC": "UGC-style image",
    "Advertising": "advertising image",
    "Premium commercial": "premium commercial image",
    "Minimal": "minimal image",
}

_STATE_CLAUSE = {
    "Closed": "the product is closed",
    "Open": "the product is open",
    "Lid attached": "the lid remains attached",
    "Lid removed": "the lid is removed",
    "Vent open": "the vent is open",
    "Vent closed": "the vent is closed",
    "Empty": "the container is empty",
    "Filled": "the container is filled",
    "Stacked": "the containers are stacked",
    "Being held": "the product is being held",
    "Being carried": "the product is being carried",
    "Being used": "the product is being used",
    "Inside appliance": "the product is placed inside an appliance",
    "On table": "the product is resting on a table",
}

_TRANSPARENCY_PHRASE = {
    "Transparent": "full transparency",
    "Semi-transparent": "semi-transparent finish",
    "Opaque": "opaque finish",
    "Mixed": "mixed transparency",
}

_PERSPECTIVE_PHRASE = {
    "Natural": "natural",
    "Slightly cinematic": "slightly cinematic",
    "Ecommerce accurate": "ecommerce-accurate",
}

_DOF_PHRASE = {
    "Deep focus": "deep focus",
    "Moderate": "moderate depth of field",
    "Shallow": "shallow depth of field",
    "Very shallow": "very shallow depth of field",
}

_DIRECTION_PHRASE = {
    "Front": "from the front",
    "Back": "from behind",
    "Left": "from the left",
    "Right": "from the right",
    "Top": "from above",
    "Mixed": "from mixed directions",
}

_POSITION_PHRASE = {
    "Center": "in the centre of the frame",
    "Left": "on the left side of the frame",
    "Right": "on the right side of the frame",
    "Foreground": "in the foreground",
    "Midground": "in the midground",
    "Background": "in the background",
}

_BODY_PHRASE = {
    "Hands only": "Only the model's hands are visible.",
    "Upper body": "The model is visible from the upper body.",
    "Half body": "The model is framed as a half-body shot.",
    "Full body": "The model is visible full body.",
}

_CONTENT_LABEL = {"Food": "food", "Liquid": "liquid", "Both": "food and liquid"}


# --------------------------------------------------------------------------- #
# Small text helpers
# --------------------------------------------------------------------------- #
def join_natural(items: Iterable[str]) -> str:
    """'a', 'a and b', 'a, b and c'."""
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def sentence(text: str) -> str:
    """Capitalise the first letter and make sure the text ends with punctuation."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text[-1] in ".!?" else text + "."


def one_line(text: str) -> str:
    """Collapse whitespace/newlines and drop a trailing full stop (for embedding in a clause)."""
    return re.sub(r"\s+", " ", text or "").strip().rstrip(".")


def article(phrase: str) -> str:
    """'a' / 'an' for the phrase (digits: 8, 11, 18, 80-89 take 'an')."""
    p = phrase.strip().lower()
    if not p:
        return "a"
    if p[0].isdigit():
        n = int(re.match(r"\d+", p).group())
        return "an" if n in (8, 11, 18) or 80 <= n <= 89 else "a"
    return "an" if p[0] in "aeiou" else "a"


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:] if text else text


def _soften_case(text: str) -> str:
    """'Noodles' -> 'noodles' for mid-sentence use; acronyms like 'UHT milk' are left alone."""
    return _lower_first(text) if text[:1].isupper() and text[1:2].islower() else text


# --------------------------------------------------------------------------- #
# Identity lock
# --------------------------------------------------------------------------- #
def build_identity_lock(data: ProjectData) -> str:
    """Canned lock text (when enabled) followed by the user's own lock instructions."""
    parts = []
    if data.identity.enabled:
        parts.append(opt.IDENTITY_LOCK_TEXT)
    custom = data.identity.custom.strip()
    if custom:
        parts.append(custom)
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# final_instruction
# --------------------------------------------------------------------------- #
def build_final_instruction(data: ProjectData) -> str:
    parts = [
        _opening(data),
        _preservation(data),
        _scene(data),
        _product_state(data),
        _contents(data),
        _human_model(data),
        _camera(data),
        _lighting(data),
        _composition(data),
        _output(data),
        _closing(data),
    ]
    return " ".join(p for p in parts if p)


def _product_noun(data: ProjectData) -> str:
    return data.product.category.strip().lower() or data.product.name.strip() or "product"


def _opening(data: ProjectData) -> str:
    style = data.style
    realism = _realism_word(style.realism_level)
    photo = style.photography_style.strip()
    comp = data.composition.style.strip()
    adjectives = [realism]
    # Skip photography-style words that add nothing or would repeat the image type.
    if photo and photo.lower() not in ("photorealistic", comp.lower()):
        adjectives.append(photo if photo.isupper() else photo.lower())
    noun = _COMPOSITION_NOUN.get(comp) or (f"{comp.lower()} image" if comp else "image")
    count = len(data.reference.product_images)
    if count > 1:
        refs = "the uploaded multi-angle new-product references"
    else:
        refs = "the uploaded new-product reference image"
    return (f"Generate {article(adjectives[0])} {' '.join(adjectives)} {noun} using {refs} "
            f"as the exclusive source of truth for the product.")


def _realism_word(level: int) -> str:
    if level >= 9:
        return "highly photorealistic"
    if level >= 7:
        return "photorealistic"
    if level >= 5:
        return "realistic"
    return "lightly stylised"


def _preservation(data: ProjectData) -> str:
    p = data.product
    items = ["geometry", "proportions"]
    materials = [m.lower() for m in p.resolved_materials()]
    if materials:
        items.append(f"{join_natural(materials)} construction")
    items.append(f"{p.colour.strip().lower()} colour" if p.colour.strip() else "colour")
    items.append(_TRANSPARENCY_PHRASE.get(p.transparency, "transparency") if p.transparency else "transparency")
    items.append("logo placement")
    out = [f"Preserve the exact {join_natural(items)}."]

    if len(data.reference.product_images) > 1:
        primary = file_name(data.reference.effective_primary())
        out.append(f"Treat {primary} as the primary product reference.")
    features = split_lines(p.features)
    if features:
        out.append(f"Keep these features exactly as shown in the references: {join_natural(features)}.")
    if p.important_details.strip():
        out.append(sentence("Important details to preserve: " + one_line(p.important_details)))
    if data.identity.enabled:
        out.append("Do not redesign, simplify, stretch or substitute the product.")
    if data.identity.custom.strip():
        out.append(sentence("Additional identity requirements: " + one_line(data.identity.custom)))
    return " ".join(out)


def _scene(data: ProjectData) -> str:
    s = data.scene
    subject = "the " + _product_noun(data)
    scene_type = s.scene_type.strip().lower()
    env = one_line(s.environment)
    if scene_type and env:
        out = f"Show {subject} in a {scene_type} setting: {env}."
    elif env:
        out = f"Show {subject} in this environment: {env}."
    elif scene_type:
        out = f"Show {subject} in a {scene_type} setting."
    else:
        out = f"Show {subject}."
    extra = []
    if s.surroundings.strip():
        extra.append(sentence("Surroundings: " + one_line(s.surroundings)))
    if s.background.strip():
        extra.append(f"Background style: {s.background.strip().lower()}.")
    if s.time_of_day.strip() and s.time_of_day != "Not applicable":
        extra.append(f"Time of day: {s.time_of_day.strip().lower()}.")
    return " ".join([out] + extra)


def _product_state(data: ProjectData) -> str:
    clauses = [_STATE_CLAUSE[s] for s in data.state.resolved_states() if s in _STATE_CLAUSE]
    custom = one_line(data.state.custom)
    if custom:
        clauses.append(_lower_first(custom))
    return sentence(join_natural(clauses)) if clauses else ""


def _contents(data: ProjectData) -> str:
    c = data.contents
    if not c.enabled:
        return ""
    label = _soften_case(one_line(c.name)) or _CONTENT_LABEL.get(c.content_type, "contents")
    noun = _product_noun(data)
    if c.content_type == "Liquid":
        out = f"Fill the {noun} with {label}"
    else:
        out = f"Include {label} inside the {noun}"
    if c.steam in ("Subtle", "Visible"):
        out += f", with {c.steam.lower()} steam rising"
    out += "."
    extra = []
    if c.appearance.strip():
        extra.append(sentence("Appearance: " + one_line(c.appearance)))
    if c.fill_level:
        extra.append(f"The {noun} is full." if c.fill_level == "Full"
                     else f"The {noun} is filled to about {c.fill_level}.")
    return " ".join([out] + extra)


def _human_model(data: ProjectData) -> str:
    m = data.model
    if not m.enabled:
        return ""
    adj, noun = _person_words(m.gender_presentation, m.age_range)
    appearance = one_line(m.appearance)
    inline_appearance = appearance if appearance and len(appearance.split()) <= 3 and "," not in appearance else ""
    words = " ".join(w for w in (adj, inline_appearance, noun) if w)
    person = f"{article(words)} {words}"

    action = one_line(m.action)
    if not action:
        out = [sentence(f"Include {person} in the scene")]
    else:
        first = action.split()[0].lower()
        if first.endswith("ing"):                   # "Holding the product" -> "is holding ..."
            out = [sentence(f"{person} is {_lower_first(action)}")]
        else:
            out = [sentence(f"Include {person} in the scene"), sentence("Model action: " + action)]
    if appearance and not inline_appearance:
        out.append(sentence("Model appearance: " + appearance))
    if m.clothing.strip():
        out.append(sentence("The model wears " + one_line(m.clothing)))
    if m.visible_body_area in _BODY_PHRASE:
        out.append(_BODY_PHRASE[m.visible_body_area])
    if m.expression.strip():
        out.append(f"The model's expression is {m.expression.strip().lower()}.")
    if m.styling_notes.strip():
        out.append(sentence("Styling notes: " + one_line(m.styling_notes)))
    return " ".join(out)


def _person_words(gender: str, age: str) -> tuple[str, str]:
    """(age adjective, person noun), e.g. ('25–35-year-old', 'woman')."""
    age = age.strip()
    low = age.lower()
    female, male = gender == "Female", gender == "Male"
    if low == "child":
        return "", "girl" if female else "boy" if male else "child"
    if low == "teen":
        return "teenage", "girl" if female else "boy" if male else "person"
    noun = "woman" if female else "man" if male else "person"
    if not age:
        return "", noun
    if re.fullmatch(r"\d+\s*[–-]\s*\d+", age):
        return f"{age}-year-old", noun
    if re.fullmatch(r"\d+\+", age):
        return f"{age[:-1]}-plus-year-old", noun
    return age, noun                                   # custom text, used as typed


def _camera(data: ProjectData) -> str:
    c = data.camera
    parts = []
    angle = c.angle.strip().lower()
    perspective = c.perspective.strip()
    persp = _PERSPECTIVE_PHRASE.get(perspective, perspective.lower())
    if angle:
        parts.append(f"{article(persp or angle)} {persp + ' ' if persp else ''}{angle} camera angle")
    elif persp:
        parts.append(f"{article(persp)} {persp} perspective")
    if c.distance:
        parts.append(f"{article(c.distance)} {c.distance.lower()} shot")
    if c.lens and c.lens != "Auto":
        parts.append(f"{article(c.lens)} {c.lens} lens")
    if c.depth_of_field:
        parts.append(_DOF_PHRASE.get(c.depth_of_field, c.depth_of_field.lower()))
    if data.composition.framing:
        parts.append(f"{data.composition.framing.lower()} framing")
    return f"Use {join_natural(parts)}." if parts else ""


def _lighting(data: ProjectData) -> str:
    lt = data.lighting
    parts = []
    if lt.type.strip():
        t = lt.type.strip().lower()
        parts.append(t if "light" in t else f"{t} lighting")
    if lt.direction in _DIRECTION_PHRASE:
        if parts:
            parts[0] += f" {_DIRECTION_PHRASE[lt.direction]}"
        else:
            parts.append(f"lighting {_DIRECTION_PHRASE[lt.direction]}")
    if lt.shadow_style:
        parts.append(f"{lt.shadow_style.lower()} shadows")
    if lt.reflection_level:
        parts.append(f"{lt.reflection_level.lower().replace('high gloss', 'high-gloss')} reflections")
    if lt.colour_temperature:
        parts.append(f"a {lt.colour_temperature.lower()} colour temperature")
    return f"Light the scene with {join_natural(parts)}." if parts else ""


def _composition(data: ProjectData) -> str:
    c = data.composition
    pos = c.product_position.strip()
    where = _POSITION_PHRASE.get(pos, pos.lower() if pos else "")
    fill = f"fills roughly {c.occupancy_percent}% of the frame" if c.occupancy_percent else ""
    if where and fill:
        text = f"Place the product {where} so it {fill}."
    elif where:
        text = f"Place the product {where}."
    elif fill:
        text = f"The product {fill}."
    else:
        text = ""
    if c.space_for_text and c.text_position:
        text = (text + " " if text else "") + (
            f"Leave clean negative space at the {c.text_position.lower()} of the frame for text overlay.")
    return text


def _output(data: ProjectData) -> str:
    o = data.output
    if o.width <= 0 or o.height <= 0:
        return ""
    text = f"Compose the image at {o.width}×{o.height} px ({aspect_ratio(o.width, o.height)})"
    if o.intended_use:
        text += f" for {o.intended_use}"
    if o.quality:
        text += f" at {o.quality.lower()} quality"
    return text + "."


def _closing(data: ProjectData) -> str:
    out = "Maintain realistic real-world scale"
    if data.style.avoid_ai_look:
        out += " and avoid any AI-looking product distortion"
    return out + "."


# --------------------------------------------------------------------------- #
# Plain-text export
# --------------------------------------------------------------------------- #
def build_text_prompt(prompt: dict) -> str:
    """Readable .txt version of a generated prompt dict (for pasting into a chat UI)."""
    lines = [prompt.get("final_instruction", "").strip(), ""]

    refs = prompt.get("reference_images", {})
    identity = refs.get("product_identity", {})
    lines.append("REFERENCE IMAGES")
    lines.append(f"Product identity ({identity.get('role', '')}):")
    primary = identity.get("primary_reference", "")
    for i, img in enumerate(identity.get("images", []), 1):
        mark = "  [PRIMARY]" if img.get("filename") == primary else ""
        lines.append(f"  {i}. {img.get('filename', '')}{mark}")

    lock = prompt.get("product", {}).get("identity_lock", "").strip()
    if lock:
        lines += ["", "PRODUCT IDENTITY LOCK", lock]
    ai_text = prompt.get("visual_style", {}).get("avoid_ai_look_instruction", "").strip()
    if ai_text:
        lines += ["", "REALISM", ai_text]
    restrictions = prompt.get("restrictions", [])
    if restrictions:
        lines += ["", "THINGS TO AVOID"] + [f"- {r}" for r in restrictions]
    return "\n".join(lines).rstrip() + "\n"
