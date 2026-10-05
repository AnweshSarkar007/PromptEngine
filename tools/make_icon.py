"""Generate assets/icon.ico (multi-size, PNG-compressed) with Qt - no extra dependencies.

    python tools/make_icon.py
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt     # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QGuiApplication, QImage, QLinearGradient, QPainter,   # noqa: E402
                           QPainterPath, QPen)

SIZES = (256, 128, 64, 48, 32, 16)


def render(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    s = float(size)

    # rounded gradient tile
    grad = QLinearGradient(0, 0, s, s)
    grad.setColorAt(0, QColor("#6C8CFF"))
    grad.setColorAt(1, QColor("#2B43B8"))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(QRectF(s * 0.04, s * 0.04, s * 0.92, s * 0.92), s * 0.22, s * 0.22)

    # photo frame
    frame = QRectF(s * 0.2, s * 0.24, s * 0.6, s * 0.46)
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawRoundedRect(frame, s * 0.06, s * 0.06)

    # sun + mountains inside the frame
    p.setBrush(QColor("#6C8CFF"))
    p.drawEllipse(QPointF(frame.left() + frame.width() * 0.27, frame.top() + frame.height() * 0.32), s * 0.05, s * 0.05)
    hills = QPainterPath()
    hills.moveTo(frame.left() + s * 0.02, frame.bottom() - s * 0.02)
    hills.lineTo(frame.left() + frame.width() * 0.38, frame.top() + frame.height() * 0.45)
    hills.lineTo(frame.left() + frame.width() * 0.60, frame.top() + frame.height() * 0.70)
    hills.lineTo(frame.left() + frame.width() * 0.75, frame.top() + frame.height() * 0.55)
    hills.lineTo(frame.right() - s * 0.02, frame.bottom() - s * 0.02)
    hills.closeSubpath()
    p.setBrush(QColor("#2B43B8"))
    p.drawPath(hills)

    # "prompt lines" under the frame
    p.setPen(QPen(QColor(255, 255, 255, 235), max(1.0, s * 0.045), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(s * 0.22, s * 0.79), QPointF(s * 0.78, s * 0.79))
    p.drawLine(QPointF(s * 0.22, s * 0.88), QPointF(s * 0.56, s * 0.88))
    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(data)


def build_ico(path: Path) -> None:
    images = [png_bytes(render(size)) for size in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, blob in zip(SIZES, images):
        dim = 0 if size >= 256 else size                    # 0 means 256 in the ICO format
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        blobs += blob
        offset += len(blob)
    path.write_bytes(header + entries + blobs)


def main() -> int:
    _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    target = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    build_ico(target)
    print(f"Wrote {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
