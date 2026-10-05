"""Small helpers shared by core and UI (paths, text splitting, aspect ratio)."""
from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path
from typing import Optional

from . import options as opt


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
def resource_path(relative: str) -> Path:
    """Locate a bundled asset both from source and from a PyInstaller build."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent.parent
    return root / relative


def app_data_dir() -> Path:
    """Per-user writable folder for logs (created on demand)."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    path = Path(base) / "ProductImagePromptBuilder"
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_path(path: str | os.PathLike) -> str:
    """Absolute path with forward slashes, e.g. 'C:/ProductReferences/front.jpg'."""
    return os.path.abspath(os.fspath(path)).replace("\\", "/")


def file_name(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def image_entry(path: str) -> dict[str, str]:
    """JSON entry for an image: the file name only (no folder location, never image bytes)."""
    return {"filename": file_name(path)}


def is_supported_image(path: str) -> bool:
    return path.lower().endswith(opt.IMAGE_EXTENSIONS)


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #
_BULLET_RE = re.compile(r"^\s*(?:[-*•–—]+\s*|\d+[.)]\s+)")


def split_lines(text: str) -> list[str]:
    """One item per non-empty line, with leading bullets / numbering removed."""
    items = []
    for line in (text or "").splitlines():
        cleaned = _BULLET_RE.sub("", line).strip()
        if cleaned:
            items.append(cleaned)
    return items


def num(value: Optional[float]) -> Optional[int | float]:
    """JSON-friendly number: None when unset/<=0, int when whole, else 2 decimals."""
    if value is None or value <= 0:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 2)


# --------------------------------------------------------------------------- #
# Aspect ratio
# --------------------------------------------------------------------------- #
_COMMON_RATIOS = [
    (1, 1), (5, 4), (4, 5), (4, 3), (3, 4), (3, 2), (2, 3), (16, 9), (9, 16),
    (21, 9), (9, 21), (2, 1), (1, 2), (16, 10), (10, 16), (3, 1), (1, 3),
]


def aspect_ratio(width: int, height: int) -> str:
    """'4:5' style ratio. Odd sizes (e.g. 800x1067) snap to a common ratio within 0.5%."""
    if width <= 0 or height <= 0:
        return ""
    g = math.gcd(width, height)
    rw, rh = width // g, height // g
    if max(rw, rh) <= 32:
        return f"{rw}:{rh}"
    actual = width / height
    best = min(_COMMON_RATIOS, key=lambda r: abs(actual - r[0] / r[1]))
    if abs(actual - best[0] / best[1]) / actual <= 0.005:
        return f"{best[0]}:{best[1]}"
    return f"{actual:.2f}:1"
