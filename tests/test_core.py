"""Core (non-UI) tests. Run from the project root:  python -m unittest discover tests -v"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import options as opt                                    # noqa: E402
from core.json_builder import build_prompt_json, to_json_text      # noqa: E402
from core.models import ProjectData                                # noqa: E402
from core.pipeline import run_pipeline                             # noqa: E402
from core.sample import sample_project                             # noqa: E402
from core.project_manager import (ProjectError, ensure_project_suffix,   # noqa: E402
                                  load_project, save_project)
from core.prompt_builder import (article, build_final_instruction,       # noqa: E402
                                 build_text_prompt, join_natural)
from core.utils import aspect_ratio, split_lines                    # noqa: E402
from core.validation import has_errors, validate                    # noqa: E402

# The structure requested in the brief (values irrelevant, only keys matter).
SPEC_KEYS = {
    "task": None,
    "reference_images": {
        "product_identity": {"images": None, "primary_reference": None, "role": None},
    },
    "product": {
        "name": None, "category": None,
        "dimensions_cm": {"width": None, "height": None, "depth": None, "diameter": None},
        "materials": None, "colour": None, "transparency": None, "features": None,
        "important_details": None, "identity_lock": None,
    },
    "scene": {"type": None, "environment": None, "surroundings": None, "background": None,
              "time_of_day": None},
    "product_state": {"states": None, "custom": None},
    "contents": {"enabled": None, "type": None, "name": None, "appearance": None,
                 "fill_level": None, "steam": None},
    "human_model": {"enabled": None, "gender_presentation": None, "age_range": None,
                    "appearance": None, "clothing": None, "action": None,
                    "visible_body_area": None, "expression": None, "styling_notes": None},
    "camera": {"angle": None, "distance": None, "lens": None, "depth_of_field": None,
               "perspective": None},
    "composition": {"product_position": None, "product_frame_occupancy_percent": None,
                    "style": None, "framing": None,
                    "space_for_text": {"enabled": None, "position": None}},
    "lighting": {"type": None, "direction": None, "shadow_style": None, "reflection_level": None,
                 "colour_temperature": None},
    "visual_style": {"photography_style": None, "realism_level": None, "avoid_ai_look": None},
    "output": {"width": None, "height": None, "aspect_ratio": None, "intended_use": None,
               "quality": None},
    "restrictions": None,
    "final_instruction": None,
}


example_project = sample_project


def minimal_valid() -> ProjectData:
    d = ProjectData()
    d.reference.product_images = ["C:/x/front.jpg"]
    d.product.name = "Jar"
    d.product.width = 12
    d.scene.environment = "Kitchen counter"
    d.camera.angle = "Eye level"
    return d


def key_structure(obj):
    if isinstance(obj, dict):
        return {k: key_structure(v) for k, v in obj.items()}
    return None


class JsonStructureTests(unittest.TestCase):
    def test_matches_brief_template_exactly(self):
        d = ProjectData()
        out = build_prompt_json(d)
        got = key_structure(out)
        # Disabled sections collapse to {"enabled": false}; the AI-look text key is additive.
        for section in ("contents", "human_model"):
            self.assertEqual(out[section], {"enabled": False})
            got[section] = SPEC_KEYS[section]
        extra_ai = got["visual_style"].pop("avoid_ai_look_instruction")
        self.assertIsNone(extra_ai)
        self.assertEqual(got, SPEC_KEYS)
        self.assertEqual(list(out.keys()), list(SPEC_KEYS.keys()))      # same order too

    def test_enabled_sections_have_every_key(self):
        out = build_prompt_json(example_project())
        self.assertEqual(set(out["contents"]), set(SPEC_KEYS["contents"]))
        self.assertEqual(set(out["human_model"]), set(SPEC_KEYS["human_model"]))

    def test_images_are_file_names_only(self):
        out = build_prompt_json(example_project())
        imgs = out["reference_images"]["product_identity"]["images"]
        self.assertEqual(imgs, [{"filename": "front.jpg"}, {"filename": "side.jpg"}, {"filename": "lid.jpg"}])
        self.assertEqual(out["reference_images"]["product_identity"]["primary_reference"], "front.jpg")
        text = to_json_text(out)
        json.loads(text)                                   # valid JSON
        # No folder locations anywhere in the prompt or its text export.
        for rendered in (text, build_text_prompt(out)):
            self.assertNotIn("ProductReferences", rendered)
            self.assertNotIn('"path"', rendered)
            self.assertNotIn("base64", rendered.lower())

    def test_only_product_identity_references(self):
        out = build_prompt_json(example_project())
        self.assertEqual(list(out["reference_images"]), ["product_identity"])
        text = build_final_instruction(example_project()).lower()
        self.assertNotIn("old product", text)
        self.assertNotIn("scene reference", text)

    def test_older_projects_with_extra_reference_images_still_load(self):
        d = ProjectData.from_dict({"reference": {"product_images": ["C:/a.jpg"], "scene_image": "C:/s.jpg",
                                                 "vibe_image": "C:/old.jpg"}})
        self.assertEqual(d.reference.product_images, ["C:/a.jpg"])
        self.assertFalse(hasattr(d.reference, "vibe_image"))

    def test_identity_lock_and_ai_look_toggles(self):
        d = example_project()
        out = build_prompt_json(d)
        self.assertEqual(out["product"]["identity_lock"], opt.IDENTITY_LOCK_TEXT)
        self.assertEqual(out["visual_style"]["avoid_ai_look_instruction"], opt.AI_LOOK_AVOIDANCE_TEXT)
        d.identity.enabled = False
        d.identity.custom = "Keep the red dot on the lid."
        d.style.avoid_ai_look = False
        out = build_prompt_json(d)
        self.assertEqual(out["product"]["identity_lock"], "Keep the red dot on the lid.")
        self.assertNotIn("avoid_ai_look_instruction", out["visual_style"])
        d.identity.enabled = True
        self.assertTrue(build_prompt_json(d)["product"]["identity_lock"].endswith("red dot on the lid."))

    def test_numbers_units_and_lists(self):
        out = build_prompt_json(example_project())
        self.assertEqual(out["product"]["dimensions_cm"],
                         {"width": 22, "height": 7.5, "depth": 15, "diameter": None})
        self.assertNotIn("volume", out["product"])
        self.assertNotIn("weight", out["product"])
        self.assertEqual(out["product"]["features"], ["Air vent lid", "Snap-lock clips"])
        self.assertEqual(out["output"]["aspect_ratio"], "4:5")
        self.assertEqual(out["output"]["quality"], "maximum")
        self.assertEqual(out["restrictions"], opt.DEFAULT_RESTRICTIONS)

    def test_other_material_and_state_replacement(self):
        d = minimal_valid()
        d.product.materials = ["Plastic", "Other"]
        d.product.other_material = "Bamboo fibre"
        d.state.states = ["Open", "Other"]
        d.state.custom = "Lid hanging on the rim"
        out = build_prompt_json(d)
        self.assertEqual(out["product"]["materials"], ["Plastic", "Bamboo fibre"])
        self.assertEqual(out["product_state"]["states"], ["Open"])


class FinalInstructionTests(unittest.TestCase):
    def setUp(self):
        self.text = build_final_instruction(example_project())

    def test_matches_brief_example_phrases(self):
        for phrase in (
            "Generate a highly photorealistic lifestyle image using the uploaded multi-angle "
            "new-product references as the exclusive source of truth for the product.",
            "borosilicate glass and silicone construction",
            "Show the glass container in a kitchen setting",
            "The lid remains attached and the vent is open.",
            "Include noodles inside the glass container.",
            "The product fills roughly 50% of the frame.",
            "A 25–35-year-old Indian woman is placing the product inside a microwave.",
            "a natural 3/4 front camera angle",
            "medium framing",
            "natural daylight",
            "natural shadows",
            "Maintain realistic real-world scale and avoid any AI-looking product distortion.",
        ):
            self.assertIn(phrase, self.text)

    def test_off_sections_are_omitted(self):
        d = example_project()
        d.model.enabled = False
        d.contents.enabled = False
        text = build_final_instruction(d)
        self.assertNotIn("woman", text)
        self.assertNotIn("noodles", text)

    def test_model_action_not_gerund_falls_back(self):
        d = example_project()
        d.model.action = "Hand placed on the lid"
        self.assertIn("Model action: Hand placed on the lid.", build_final_instruction(d))

    def test_realism_wording(self):
        d = minimal_valid()
        d.style.realism_level = 6
        self.assertTrue(build_final_instruction(d).startswith("Generate a realistic image"))
        d.style.realism_level = 8
        self.assertTrue(build_final_instruction(d).startswith("Generate a photorealistic image"))

    def test_single_reference_wording(self):
        text = build_final_instruction(minimal_valid())
        self.assertIn("the uploaded new-product reference image", text)
        self.assertNotIn("primary product reference", text)

    def test_helpers(self):
        self.assertEqual(join_natural(["a", "b", "c"]), "a, b and c")
        self.assertEqual(join_natural(["a", "b"]), "a and b")
        self.assertEqual(article("18–25-year-old"), "an")
        self.assertEqual(article("25–35-year-old"), "a")
        self.assertEqual(article("elderly"), "an")

    def test_text_export(self):
        out = build_prompt_json(example_project())
        txt = build_text_prompt(out)
        self.assertTrue(txt.startswith("Generate a highly photorealistic"))
        self.assertIn("1. front.jpg  [PRIMARY]\n", txt)
        self.assertIn("THINGS TO AVOID", txt)
        self.assertIn("- Do not modify the lid.", txt)


class ValidationTests(unittest.TestCase):
    def messages(self, data):
        return {(i.section_id, i.field_key) for i in validate(data, check_files=False) if i.is_error}

    def test_empty_form_reports_every_required_field(self):
        d = ProjectData()
        self.assertEqual(self.messages(d), {
            ("references", "product_images"), ("product", "name"), ("product", "dimensions"),
            ("scene", "environment"), ("camera", "angle"),
        })

    def test_minimal_valid_passes(self):
        self.assertFalse(has_errors(validate(minimal_valid(), check_files=False)))

    def test_any_single_dimension_is_enough(self):
        d = minimal_valid()
        d.product.width = None
        self.assertIn(("product", "dimensions"), self.messages(d))
        d.product.diameter = 12
        self.assertNotIn(("product", "dimensions"), self.messages(d))

    def test_scene_type_alone_satisfies_scene(self):
        d = minimal_valid()
        d.scene.environment = ""
        self.assertIn(("scene", "environment"), self.messages(d))
        d.scene.scene_type = "Cafe"
        self.assertNotIn(("scene", "environment"), self.messages(d))

    def test_output_bounds(self):
        d = minimal_valid()
        d.output.width = 10
        d.output.height = 99999
        self.assertEqual({k for s, k in self.messages(d) if s == "output"}, {"width", "height"})

    def test_too_many_images(self):
        d = minimal_valid()
        d.reference.product_images = [f"C:/x/{i}.jpg" for i in range(16)]
        self.assertIn(("references", "product_images"), self.messages(d))

    def test_missing_files_are_warnings_only(self):
        issues = validate(minimal_valid(), check_files=True)
        self.assertFalse(has_errors(issues))
        self.assertTrue(any("not found" in i.message for i in issues))

    def test_pipeline_blocks_on_errors(self):
        res = run_pipeline(ProjectData())
        self.assertFalse(res.ok)
        self.assertTrue(res.errors)
        res = run_pipeline(minimal_valid())
        self.assertTrue(res.ok)
        self.assertIn('"task": "generate_product_image"', res.json_text)


class ProjectFileTests(unittest.TestCase):
    def test_round_trip(self):
        d = example_project()
        d.restrictions.text = "- Only this\n- And that"
        d.composition.space_for_text = True
        d.composition.text_position = "Left"
        with tempfile.TemporaryDirectory() as tmp:
            path = save_project(Path(tmp) / "demo", d)
            self.assertTrue(path.name.endswith(".project.json"))
            loaded, warnings = load_project(path)
        self.assertEqual(loaded.to_dict(), d.to_dict())
        self.assertEqual(warnings, [])

    def test_suffix_handling(self):
        self.assertEqual(ensure_project_suffix("a").name, "a.project.json")
        self.assertEqual(ensure_project_suffix("a.json").name, "a.project.json")
        self.assertEqual(ensure_project_suffix("a.project.json").name, "a.project.json")

    def test_partial_and_unknown_keys_are_tolerated(self):
        raw = {"product": {"name": "Cup", "width": "12.5", "bogus": 1, "materials": "oops"},
               "output": {"width": 800.0}, "unknown_section": {}, "camera": "garbage"}
        d = ProjectData.from_dict(raw)
        self.assertEqual(d.product.name, "Cup")
        self.assertEqual(d.product.width, 12.5)
        self.assertEqual(d.product.materials, [])            # wrong type -> default
        self.assertEqual(d.output.width, 800)
        self.assertEqual(d.output.height, 1080)              # untouched default
        self.assertEqual(d.camera.angle, "")

    def test_bad_files_raise_friendly_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.project.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ProjectError):
                load_project(bad)
            other = Path(tmp) / "other.project.json"
            other.write_text('{"hello": 1}', encoding="utf-8")
            with self.assertRaisesRegex(ProjectError, "not a Product Image Prompt Builder"):
                load_project(other)
            with self.assertRaises(ProjectError):
                load_project(Path(tmp) / "missing.project.json")

    def test_moved_images_are_found_relative_to_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            old = tmp / "old"
            new = tmp / "new"
            old.mkdir()
            new.mkdir()
            img = old / "front.png"
            img.write_bytes(b"x")
            d = minimal_valid()
            d.reference.product_images = [str(img).replace("\\", "/")]
            path = save_project(old / "p", d)
            (new / "front.png").write_bytes(b"x")
            (new / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            img.unlink()
            # Relative path from old/ is "front.png", so moving the project beside its image works.
            loaded, warnings = load_project(new / path.name)
        self.assertTrue(loaded.reference.product_images[0].endswith("/new/front.png"))
        self.assertEqual(len(warnings), 1)


class UtilTests(unittest.TestCase):
    def test_aspect_ratio(self):
        cases = {(1080, 1080): "1:1", (1080, 1350): "4:5", (1080, 1920): "9:16",
                 (1920, 1080): "16:9", (800, 1067): "3:4", (1000, 1500): "2:3"}
        for (w, h), expected in cases.items():
            self.assertEqual(aspect_ratio(w, h), expected, (w, h))
        self.assertEqual(aspect_ratio(0, 10), "")
        self.assertEqual(aspect_ratio(1000, 777), "1.29:1")

    def test_split_lines(self):
        self.assertEqual(split_lines("- a\n\n* b\n1. c\n  • d  \nplain"), ["a", "b", "c", "d", "plain"])


if __name__ == "__main__":
    unittest.main()
