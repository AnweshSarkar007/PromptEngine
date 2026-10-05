"""Plain dataclasses describing everything the user can enter.

`ProjectData` is the single source of truth: UI cards read from / write to it, the project
file is just `to_dict()`, and the JSON builder consumes it. No Qt imports here.
"""
from __future__ import annotations

import dataclasses
import types
import typing
from dataclasses import dataclass, field
from typing import Any, Optional

from . import options as opt


@dataclass
class ReferenceData:
    product_images: list[str] = field(default_factory=list)   # file paths, in user order
    primary_path: str = ""                                    # one of product_images

    def effective_primary(self) -> str:
        """The chosen primary image, or the first image when none (or a stale one) is set."""
        if self.primary_path in self.product_images:
            return self.primary_path
        return self.product_images[0] if self.product_images else ""


@dataclass
class ProductData:
    name: str = ""
    category: str = ""
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    diameter: Optional[float] = None
    materials: list[str] = field(default_factory=list)
    other_material: str = ""
    colour: str = ""
    transparency: str = ""
    features: str = ""            # one feature per line
    important_details: str = ""

    def resolved_materials(self) -> list[str]:
        """Selected materials with the 'Other' chip replaced by the typed text."""
        out: list[str] = []
        for m in self.materials:
            if m == opt.OTHER:
                if self.other_material.strip():
                    out.append(self.other_material.strip())
            else:
                out.append(m)
        return out


@dataclass
class IdentityLockData:
    enabled: bool = True
    custom: str = ""


@dataclass
class SceneData:
    scene_type: str = ""
    environment: str = ""
    surroundings: str = ""
    background: str = ""
    time_of_day: str = ""


@dataclass
class ProductStateData:
    states: list[str] = field(default_factory=list)
    custom: str = ""

    def resolved_states(self) -> list[str]:
        """Selected states; the generic 'Other' chip is dropped once custom text exists."""
        if self.custom.strip():
            return [s for s in self.states if s != opt.OTHER]
        return list(self.states)


@dataclass
class ContentsData:
    enabled: bool = False
    content_type: str = ""
    name: str = ""
    appearance: str = ""
    fill_level: str = ""
    steam: str = "None"


@dataclass
class ModelData:
    enabled: bool = False
    gender_presentation: str = ""
    age_range: str = ""
    appearance: str = ""
    clothing: str = ""
    action: str = ""
    visible_body_area: str = ""
    expression: str = ""
    styling_notes: str = ""


@dataclass
class CameraData:
    angle: str = ""
    distance: str = ""
    lens: str = ""
    depth_of_field: str = ""
    perspective: str = ""


@dataclass
class CompositionData:
    product_position: str = ""
    occupancy_percent: int = 50
    style: str = ""
    framing: str = ""
    space_for_text: bool = False
    text_position: str = "Top"


@dataclass
class LightingData:
    type: str = ""
    direction: str = ""
    shadow_style: str = ""
    reflection_level: str = ""
    colour_temperature: str = ""


@dataclass
class StyleData:
    photography_style: str = ""
    realism_level: int = opt.DEFAULT_REALISM
    avoid_ai_look: bool = True


@dataclass
class OutputData:
    width: int = 1080
    height: int = 1080
    intended_use: str = ""
    quality: str = "Maximum"


@dataclass
class RestrictionsData:
    text: str = opt.DEFAULT_RESTRICTIONS_TEXT


@dataclass
class ProjectData:
    reference: ReferenceData = field(default_factory=ReferenceData)
    product: ProductData = field(default_factory=ProductData)
    identity: IdentityLockData = field(default_factory=IdentityLockData)
    scene: SceneData = field(default_factory=SceneData)
    state: ProductStateData = field(default_factory=ProductStateData)
    contents: ContentsData = field(default_factory=ContentsData)
    model: ModelData = field(default_factory=ModelData)
    camera: CameraData = field(default_factory=CameraData)
    composition: CompositionData = field(default_factory=CompositionData)
    lighting: LightingData = field(default_factory=LightingData)
    style: StyleData = field(default_factory=StyleData)
    output: OutputData = field(default_factory=OutputData)
    restrictions: RestrictionsData = field(default_factory=RestrictionsData)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProjectData":
        """Tolerant loader: unknown keys are ignored, missing/invalid ones keep their defaults."""
        return _load(cls, raw)


# --------------------------------------------------------------------------- #
# Tolerant dict -> dataclass loader (keeps old project files loadable)
# --------------------------------------------------------------------------- #
def _load(cls: type, raw: Any) -> Any:
    obj = cls()
    if not isinstance(raw, dict):
        return obj
    hints = typing.get_type_hints(cls)
    for f in dataclasses.fields(cls):
        if f.name not in raw:
            continue
        tp = hints[f.name]
        value = raw[f.name]
        if dataclasses.is_dataclass(tp):
            setattr(obj, f.name, _load(tp, value))
            continue
        coerced = _coerce(value, tp)
        if coerced is not _INVALID:
            setattr(obj, f.name, coerced)
    return obj


_INVALID = object()


def _coerce(value: Any, tp: Any) -> Any:
    origin = typing.get_origin(tp)
    if origin is list:
        if not isinstance(value, list):
            return _INVALID
        return [str(v) for v in value if v is not None]
    if origin in (typing.Union, types.UnionType):          # Optional[float]
        if value is None:
            return None
        inner = [a for a in typing.get_args(tp) if a is not type(None)][0]
        return _coerce(value, inner)
    if tp is bool:
        return bool(value) if isinstance(value, (bool, int)) else _INVALID
    if tp is int:
        if isinstance(value, bool):
            return _INVALID
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return _INVALID
    if tp is float:
        if isinstance(value, bool):
            return _INVALID
        try:
            return float(value)
        except (TypeError, ValueError):
            return _INVALID
    if tp is str:
        return "" if value is None else str(value)
    return _INVALID
