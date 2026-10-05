"""Offscreen UI smoke test. Run from the project root:

    set QT_QPA_PLATFORM=offscreen && python tests/smoke_ui.py [screenshot_dir]

Builds the real MainWindow, fills every card through the widgets, generates JSON, round-trips a
project file and checks the show/hide toggles. Optionally saves light/dark screenshots.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QSettings, Qt                      # noqa: E402
from PySide6.QtGui import QColor, QImage                      # noqa: E402
from PySide6.QtWidgets import QApplication                    # noqa: E402

from core import options as opt                               # noqa: E402
from core.models import ProjectData                           # noqa: E402
from ui.main_window import MainWindow                         # noqa: E402
from ui.theme import apply_theme                              # noqa: E402

failures: list[str] = []


def check(cond: bool, message: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + message)
    if not cond:
        failures.append(message)


def make_images(folder: Path) -> list[str]:
    paths = []
    for i, colour in enumerate(("#4C8BF5", "#34A853", "#FBBC05", "#EA4335")):
        img = QImage(640, 480 + i * 40, QImage.Format_RGB32)
        img.fill(QColor(colour))
        p = folder / f"view_{i + 1}.png"
        img.save(str(p))
        paths.append(str(p).replace("\\", "/"))
    return paths


def fill_form(w: MainWindow, images: list[str]) -> None:
    ref = w.cards_by_id["references"]
    ref.thumbs.add_paths(images[:3])

    prod = w.cards_by_id["product"]
    prod.name_edit.setText("Glasafe 900 ml Lunch Box")
    prod.category.set_value("Glass container")
    prod.transparency.set_value("Transparent")
    prod.width_in.set_optional_value(22)
    prod.height_in.set_optional_value(7.5)
    prod.materials.set_values(["Borosilicate glass", "Silicone"])
    prod.colour.setText("Clear")
    prod.features.setPlainText("- Air vent lid\n- Snap-lock clips")

    scene = w.cards_by_id["scene"]
    scene.scene_type.set_value("Kitchen")
    scene.environment.setPlainText("Modern Indian kitchen with neutral cabinetry.")

    w.cards_by_id["state"].states.set_values(["Lid attached", "Vent open"])
    c = w.cards_by_id["contents"]
    c.toggle.setChecked(True)
    c.content_type.set_value("Food")
    c.name_edit.setText("noodles")
    m = w.cards_by_id["model"]
    m.toggle.setChecked(True)
    m.gender.set_value("Female")
    m.age.set_value("25–35")
    m.appearance.setText("Indian")
    m.action.setPlainText("Placing the product inside a microwave")
    w.cards_by_id["camera"].angle.set_value("3/4 front")
    w.cards_by_id["camera"].distance.set_value("Medium")
    w.cards_by_id["lighting"].type.set_value("Natural daylight")
    w.cards_by_id["composition"].style.set_value("Lifestyle")
    w.cards_by_id["style"].photo_style.set_value("Photorealistic")
    w.cards_by_id["output"].preset.setCurrentIndex(1)           # 1080 x 1350
    w.cards_by_id["output"].intended_use.set_value("Meta Ads")


def settle(app: QApplication, seconds: float) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    shots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    app = QApplication.instance() or QApplication(sys.argv)
    tmp = Path(tempfile.mkdtemp(prefix="ppb_smoke_"))
    settings = QSettings(str(tmp / "settings.ini"), QSettings.IniFormat)
    tokens = apply_theme(app, "light")
    w = MainWindow(settings, "light")
    w.show()
    app.processEvents()

    print("Defaults")
    d = w.collect()
    check(d.to_dict() == ProjectData().to_dict(), "fresh form collects back to ProjectData() defaults")
    check(w.cards_by_id["output"].ratio_label.text() == "1:1", "default size shows 1:1 ratio")
    check(w.cards_by_id["restrictions"].text.toPlainText() == opt.DEFAULT_RESTRICTIONS_TEXT, "default restrictions loaded")
    check(not w.cards_by_id["contents"].container.isVisible(), "food/liquid fields hidden while off")
    check(not w.cards_by_id["model"].container.isVisible(), "model fields hidden while off")

    print("Validation")
    check(w.generate() is False, "empty form is blocked")
    check(w.banner.isVisible(), "validation banner shown")
    check(len(w.preview.view.toPlainText()) == 0, "no JSON produced when invalid")
    check(w.cards_by_id["product"].name_edit.property("invalid") is True, "product name outlined as invalid")

    print("Fill + generate")
    images = make_images(tmp)
    fill_form(w, images)
    app.processEvents()
    check(w.cards_by_id["output"].ratio_label.text() == "4:5", "preset 1080x1350 -> 4:5")
    check(w.cards_by_id["contents"].container.isVisible(), "food/liquid fields visible when on")
    check(w.cards_by_id["model"].container.isVisible(), "model fields visible when on")
    check(w.generate() is True, "valid form generates")
    prompt = json.loads(w.preview.view.toPlainText())
    check(prompt["task"] == "generate_product_image", "preview contains the prompt JSON")
    check(len(prompt["reference_images"]["product_identity"]["images"]) == 3, "3 product images listed")
    check(list(prompt["reference_images"]) == ["product_identity"], "only product identity images are referenced")
    check(":/" not in w.preview.view.toPlainText(), "no folder paths anywhere in the prompt")
    check(prompt["product"]["materials"] == ["Borosilicate glass", "Silicone"], "materials collected")
    check(prompt["human_model"]["action"].startswith("Placing"), "model data present when enabled")
    check("noodles" in prompt["final_instruction"], "final_instruction mentions contents")

    print("Reference list behaviour")
    thumbs = w.cards_by_id["references"].thumbs
    thumbs.clearSelection()
    thumbs.setCurrentRow(2)
    thumbs.item(2).setSelected(True)
    thumbs.set_primary_selected()
    check(thumbs.primary().endswith("view_3.png"), "primary reference can be changed")
    thumbs.move_selected(-1)
    check([p.rsplit("/", 1)[-1] for p in thumbs.paths()] == ["view_1.png", "view_3.png", "view_2.png"], "move earlier reorders")
    thumbs.add_paths([images[0], str(tmp / "nope.txt")])
    check(len(thumbs.paths()) == 3, "duplicate and unsupported files are skipped")
    thumbs.add_paths(images)
    check(len(thumbs.paths()) == 4, "new image added")
    thumbs.clearSelection()
    thumbs.setCurrentRow(0)
    thumbs.item(0).setSelected(True)
    thumbs.remove_selected()
    check(len(thumbs.paths()) == 3, "remove works")
    check(thumbs.primary() in thumbs.paths(), "primary stays valid after removal")

    print("Drag & drop (simulated external file drops)")
    from PySide6.QtCore import QMimeData, QPointF, QUrl
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    def drop(widget, paths):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        pos = QPointF(20, 20)
        enter = QDragEnterEvent(pos.toPoint(), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(widget, enter)
        ev = QDropEvent(pos, Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(widget, ev)
        return enter.isAccepted(), ev.isAccepted()

    extra = tmp / "extra"
    extra.mkdir()
    fresh = make_images(extra)
    before = len(thumbs.paths())
    entered, dropped = drop(thumbs.viewport(), [fresh[0], fresh[1]])
    check(entered and dropped, "product list accepts an image drop")
    check(len(thumbs.paths()) == before + 2, "dropped product images are added")
    entered, dropped = drop(thumbs.viewport(), [str(tmp / "notes.txt")])
    check(not entered, "non-image drop is rejected")
    check(drop(thumbs.viewport(), [str(extra)])[1] and len(thumbs.paths()) == 7, "dropping a folder adds its supported images")

    print("ChatGPT brief")
    brief = w.cards_by_id["brief"]
    brief.copy_btn.click()
    check('"format": "product-image-prompt-builder/brief-v1"' in QApplication.clipboard().text(),
          "Copy ChatGPT instruction puts the instruction on the clipboard")
    name_before = w.cards_by_id["product"].name_edit.text()
    images_before = thumbs.paths()
    brief.paste.setPlainText(
        "Sure! Here is the filled brief:\n```json\n"
        '{"format": "product-image-prompt-builder/brief-v1",'
        ' "scene": {"type": "Dining table", "environment": "Sunlit wooden dining table", "background": "Slightly blurred"},'
        ' "camera": {"angle": "Top-down", "lens": "50mm"},'
        ' "lighting": {"type": "Window light", "colour_temperature": "Warm"},'
        ' "human_model": {"enabled": false},'
        ' "output": {"aspect_ratio": "4:5"}}\n```\nLet me know if you need changes.')
    w._dirty = False
    brief.load_btn.click()
    app.processEvents()
    check(w.cards_by_id["scene"].scene_type.value() == "Dining table", "brief fills scene type")
    check(w.cards_by_id["camera"].angle.value() == "Top-down", "brief fills camera angle")
    check(w.cards_by_id["lighting"].temperature.value() == "Warm", "brief fills colour temperature")
    check(not w.cards_by_id["model"].toggle.isChecked(), "brief can switch the human model off")
    check(w.cards_by_id["output"].ratio_label.text() == "4:5", "brief aspect ratio picks the 4:5 preset")
    check(w.cards_by_id["product"].name_edit.text() == name_before, "brief leaves product name alone")
    check(thumbs.paths() == images_before, "brief leaves images alone")
    check(brief.result.isVisible() and brief.result.property("state") == "ok", "brief shows a success summary")
    check(w._dirty, "loading a brief marks the project as changed")
    brief.paste.setPlainText("no json here")
    brief.load_btn.click()
    check(brief.result.property("state") == "error", "garbage paste shows an error and changes nothing")

    print("Toggles")
    w.cards_by_id["model"].toggle.setChecked(False)
    w.cards_by_id["contents"].toggle.setChecked(False)
    w.generate()
    p2 = json.loads(w.preview.view.toPlainText())
    check(p2["human_model"] == {"enabled": False} and p2["contents"] == {"enabled": False},
          "switched-off sections are reduced to enabled:false")
    check("woman" not in p2["final_instruction"], "no model text in final_instruction when off")

    print("Stale tracking")
    w.cards_by_id["product"].name_edit.setText("Changed")
    check(w.preview.status.property("state") == "stale", "preview marked stale after an edit")

    print("Project round trip")
    before = w.collect().to_dict()
    path = tmp / "demo.project.json"
    from core.project_manager import save_project
    save_project(path, w.collect())
    w.apply(ProjectData())
    check(w.collect().to_dict() == ProjectData().to_dict(), "apply(defaults) resets the form")
    check(w.open_project_path(str(path)), "project reloads")
    check(w.collect().to_dict() == before, "every field restored after reload")
    check(not w._dirty, "freshly loaded project is not dirty")

    print("Theme + screenshots")
    w.generate()
    app.processEvents()
    w.toggle_theme()
    check(w.theme_name == "dark", "theme toggles to dark")
    w.toggle_theme()
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
        w.resize(1480, 920)
        app.processEvents()
        for name in ("light", "dark"):
            if w.theme_name != name:
                w.toggle_theme()
            app.processEvents()
            w.scroll.verticalScrollBar().setValue(0)
            app.processEvents()
            w.grab().save(str(shots / f"{name}_top.png"))
            for section in ("brief", "product", "model", "composition", "output"):
                w.scroll_to_section(section)
                settle(app, 0.45)                      # let the scroll animation finish
                w.grab().save(str(shots / f"{name}_{section}.png"))

    w._dirty = False
    w.close()
    print("\nRESULT:", "FAILED " + str(len(failures)) if failures else "all checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
