"""Form validation. Errors block JSON generation; warnings are shown but do not."""
from __future__ import annotations

import os
from dataclasses import dataclass

from . import options as opt
from .models import ProjectData
from .utils import file_name

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    severity: str          # ERROR | WARNING
    section_id: str        # nav / card id, see options.SECTIONS
    field_key: str         # key understood by the card's focus_field()
    message: str

    @property
    def is_error(self) -> bool:
        return self.severity == ERROR


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(i.is_error for i in issues)


def validate(data: ProjectData, check_files: bool = True) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def error(section: str, key: str, msg: str) -> None:
        issues.append(ValidationIssue(ERROR, section, key, msg))

    def warn(section: str, key: str, msg: str) -> None:
        issues.append(ValidationIssue(WARNING, section, key, msg))

    ref, p = data.reference, data.product

    # --- required fields -------------------------------------------------- #
    if not ref.product_images:
        error("references", "product_images", "Add at least one product reference image.")
    elif len(ref.product_images) > opt.MAX_PRODUCT_IMAGES:
        error("references", "product_images",
              f"Use at most {opt.MAX_PRODUCT_IMAGES} product reference images.")

    if not p.name.strip():
        error("product", "name", "Enter the product name.")

    dims = (p.width, p.height, p.depth, p.diameter)
    if not any(d is not None and d > 0 for d in dims):
        error("product", "dimensions", "Enter at least one product dimension.")

    if not (data.scene.scene_type.strip() or data.scene.environment.strip()):
        error("scene", "environment", "Choose a scene type or describe the environment.")

    if not data.camera.angle.strip():
        error("camera", "angle", "Choose a camera angle (a custom angle needs text).")

    o = data.output
    for key, label, value in (("width", "width", o.width), ("height", "height", o.height)):
        if not (opt.MIN_OUTPUT_PX <= value <= opt.MAX_OUTPUT_PX):
            error("output", key,
                  f"Output {label} must be between {opt.MIN_OUTPUT_PX} and {opt.MAX_OUTPUT_PX} px.")

    # --- warnings --------------------------------------------------------- #
    if check_files:
        for path in ref.product_images:
            if not os.path.isfile(path):
                warn("references", "product_images", f"Product image not found: {path}")

    names = [file_name(path).lower() for path in ref.product_images]
    if len(set(names)) != len(names):
        warn("references", "product_images",
             "Some product images share the same file name, so they can't be told apart in the prompt. "
             "Rename one of them.")

    if data.contents.enabled and "Empty" in data.state.states:
        warn("state", "states", "Product state is 'Empty' but food / liquid is switched on.")

    if data.contents.enabled and not (data.contents.name.strip() or data.contents.content_type):
        warn("contents", "name", "Food / liquid is on but no content name or type is set.")

    return issues
