"""Save / load `.project.json` files and write exported text, with friendly errors."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import options as opt
from .models import ProjectData
from .utils import normalize_path


class ProjectError(Exception):
    """Raised with a message that is safe to show to the user."""


def ensure_project_suffix(path: str | os.PathLike) -> Path:
    """'a' / 'a.json' / 'a.project.json' -> 'a.project.json'."""
    p = Path(path)
    name = p.name
    if name.lower().endswith(opt.PROJECT_SUFFIX):
        return p
    if name.lower().endswith(".json"):
        name = name[: -len(".json")]
    return p.with_name(name + opt.PROJECT_SUFFIX)


def write_text_atomic(path: str | os.PathLike, text: str) -> None:
    """Write UTF-8 text via a temp file so a failed write never corrupts the target."""
    path = Path(path)
    tmp_name = None
    try:
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except OSError as exc:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass
        raise ProjectError(f"Could not write '{path.name}': {exc.strerror or exc}") from exc


def save_project(path: str | os.PathLike, data: ProjectData, relative_paths: bool = True) -> Path:
    path = ensure_project_suffix(path)
    folder = path.parent.resolve()
    images = list(data.reference.product_images)

    # Relative paths let a project survive being moved together with its images.
    relative: dict[str, str] = {}
    for img in images if relative_paths else []:
        try:
            relative[img] = os.path.relpath(img, folder).replace("\\", "/")
        except ValueError:                       # different drive
            continue

    payload = {
        "format": opt.PROJECT_FORMAT,
        "schema_version": opt.PROJECT_SCHEMA_VERSION,
        "app_version": opt.APP_VERSION,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "relative_image_paths": relative,
        "data": data.to_dict(),
    }
    write_text_atomic(path, json.dumps(payload, indent=2, ensure_ascii=False))
    return path


def load_project(path: str | os.PathLike) -> tuple[ProjectData, list[str]]:
    """Return (data, warnings). Raises ProjectError for unreadable / foreign files."""
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ProjectError(f"Could not open '{path.name}': {exc.strerror or exc}") from exc
    except UnicodeDecodeError as exc:
        raise ProjectError(f"'{path.name}' is not a text file.") from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ProjectError(f"'{path.name}' is not valid JSON ({exc.msg}, line {exc.lineno}).") from exc

    if not isinstance(payload, dict) or payload.get("format") != opt.PROJECT_FORMAT \
            or not isinstance(payload.get("data"), dict):
        raise ProjectError(f"'{path.name}' is not a {opt.APP_NAME} project file.")

    warnings: list[str] = []
    version = payload.get("schema_version", 0)
    if isinstance(version, int) and version > opt.PROJECT_SCHEMA_VERSION:
        warnings.append("This project was saved by a newer version; unknown settings were ignored.")

    data = ProjectData.from_dict(payload["data"])
    relative = payload.get("relative_image_paths")
    relative = relative if isinstance(relative, dict) else {}
    folder = path.parent.resolve()
    moved = _relocate_images(data, relative, folder)
    if moved:
        warnings.append(f"{moved} image(s) were found next to the project file at a new location.")
    return data, warnings


def _relocate_images(data: ProjectData, relative: dict, folder: Path) -> int:
    """Re-point images that vanished from their saved path but exist relative to the project."""
    moved = 0

    def fix(old: str) -> str:
        nonlocal moved
        if not old or os.path.isfile(old):
            return old
        rel = relative.get(old)
        if isinstance(rel, str):
            candidate = (folder / rel).resolve()
            if candidate.is_file():
                moved += 1
                return normalize_path(candidate)
        return old

    ref = data.reference
    fixed = {old: fix(old) for old in [*ref.product_images, ref.primary_path]}
    ref.product_images = [fixed[p] for p in ref.product_images]
    ref.primary_path = fixed[ref.primary_path]
    return moved
