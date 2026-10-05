"""Tests for the ChatGPT brief instruction + importer.  python -m unittest discover tests -v"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import options as opt                                             # noqa: E402
from core.chatgpt_brief import (BRIEF_FORMAT, FIELDS, apply_brief, brief_template,   # noqa: E402
                                build_instruction, extract_json)
from core.models import ProjectData                                         # noqa: E402

FILLED_REPLY = """Here's the brief based on your photo:

```json
{
  "format": "product-image-prompt-builder/brief-v1",
  "scene": {
    "type": "Kitchen",
    "environment": "Bright Indian kitchen with a white marble counter",
    "surroundings": "Fork, folded napkin, small plant",
    "background": "Slightly blurred",
    "time_of_day": "Afternoon"
  },
  "product_state": { "states": ["Lid removed", "Filled", "Steaming hot"], "custom": "" },
  "contents": { "enabled": true, "type": "Food", "name": "Vegetable pulao", "appearance": "",
                "fill_level": "75%", "steam": "Subtle" },
  "human_model": { "enabled": true, "gender_presentation": "Female", "age_range": "25-35",
                   "appearance": "Indian", "clothing": "", "action": "Holding a spoon over the bowl",
                   "visible_body_area": "Hands only", "expression": "", "styling_notes": "" },
  "camera": { "angle": "High angle", "distance": "Medium", "lens": "50mm",
              "depth_of_field": "Moderate", "perspective": "Natural" },
  "composition": { "product_position": "Centre", "product_frame_occupancy_percent": "60%",
                   "style": "Lifestyle", "framing": "Medium",
                   "space_for_text": { "enabled": true, "position": "Top" } },
  "lighting": { "type": "Soft window light from the left", "direction": "Left",
                "shadow_style": "Soft", "reflection_level": "Natural", "colour_temperature": "Warm" },
  "visual_style": { "photography_style": "Lifestyle", "realism_level": 9 },
  "output": { "aspect_ratio": "4:5" },
}
```
Hope this helps!"""


def form_with_product() -> ProjectData:
    d = ProjectData()
    d.reference.product_images = ["C:/p/front.jpg"]
    d.product.name = "Glasafe Bowl"
    d.product.width = 10
    d.scene.environment = "My own words"          # ChatGPT will overwrite this one
    d.camera.lens = "85mm"                        # and this one
    d.lighting.direction = "Back"                 # and this one ("Left")
    d.composition.style = "Premium commercial"
    return d


class InstructionTests(unittest.TestCase):
    def test_template_is_valid_json_with_every_field(self):
        text = build_instruction()
        self.assertIn("OLD product photo", text)
        self.assertIn("Do NOT describe the old product", text)
        tpl = extract_json(text)
        self.assertEqual(tpl, brief_template())
        self.assertEqual(tpl["format"], BRIEF_FORMAT)
        for f in FIELDS:
            self.assertIn(f.key, tpl[f.section], f"{f.section}.{f.key} missing from the template")

    def test_template_lists_dropdown_options_without_custom(self):
        tpl = brief_template()
        self.assertEqual(tpl["camera"]["angle"].split(" | "), [a for a in opt.CAMERA_ANGLES if a != opt.CUSTOM])
        self.assertNotIn("Other", tpl["product_state"]["states"][0])

    def test_unfilled_template_changes_nothing(self):
        d = form_with_product()
        before = d.to_dict()
        tpl = brief_template()
        for section in ("contents", "human_model"):     # booleans/ints alone are not "filling it in"
            tpl.pop(section)
        tpl["composition"].pop("product_frame_occupancy_percent")
        tpl["composition"].pop("space_for_text")
        tpl["visual_style"].pop("realism_level")
        result = apply_brief(json.dumps(tpl), d)
        self.assertFalse(result.ok)
        self.assertIn("unfilled", result.message)
        self.assertEqual(d.to_dict(), before)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.d = form_with_product()
        self.result = apply_brief(FILLED_REPLY, self.d)

    def test_reply_with_prose_fence_and_trailing_comma_is_read(self):
        self.assertTrue(self.result.ok, self.result.message)

    def test_choices_are_matched_to_dropdown_options(self):
        d = self.d
        self.assertEqual(d.scene.scene_type, "Kitchen")
        self.assertEqual(d.scene.background, "Slightly blurred")
        self.assertEqual(d.camera.angle, "High angle")
        self.assertEqual(d.camera.lens, "50mm")
        self.assertEqual(d.model.age_range, "25–35")                 # hyphen -> the app's en dash
        self.assertEqual(d.composition.product_position, "Center")   # Centre -> Center
        self.assertEqual(d.composition.occupancy_percent, 60)        # "60%" -> 60
        self.assertTrue(d.composition.space_for_text)
        self.assertEqual(d.composition.text_position, "Top")
        self.assertEqual(d.lighting.colour_temperature, "Warm")

    def test_free_text_values_are_kept_and_reported(self):
        self.assertEqual(self.d.lighting.type, "Soft window light from the left")
        self.assertIn("Lighting type", self.result.custom)
        self.assertEqual(self.d.state.states, ["Lid removed", "Filled"])
        self.assertEqual(self.d.state.custom, "Steaming hot")
        self.assertIn("Product state", self.result.custom)

    def test_blank_values_leave_existing_fields_alone(self):
        self.assertEqual(self.d.product.name, "Glasafe Bowl")
        self.assertEqual(self.d.product.width, 10)
        self.assertEqual(self.d.reference.product_images, ["C:/p/front.jpg"])
        self.assertEqual(self.d.model.clothing, "")
        self.assertEqual(self.d.contents.appearance, "")
        self.assertEqual(self.d.restrictions.text, opt.DEFAULT_RESTRICTIONS_TEXT)

    def test_filled_values_overwrite(self):
        self.assertEqual(self.d.scene.environment, "Bright Indian kitchen with a white marble counter")
        self.assertEqual(self.d.composition.style, "Lifestyle")
        self.assertTrue(self.d.contents.enabled)
        self.assertEqual(self.d.contents.name, "Vegetable pulao")

    def test_aspect_ratio_selects_matching_preset(self):
        self.assertEqual((self.d.output.width, self.d.output.height), (1080, 1350))
        d = ProjectData()
        apply_brief('{"output": {"aspect_ratio": "3:4"}, "camera": {"angle": "Eye level"}}', d)
        self.assertEqual((d.output.width, d.output.height), (800, 1067))
        apply_brief('{"output": {"aspect_ratio": "2:3"}, "camera": {"angle": "Eye level"}}', d)
        self.assertEqual((d.output.width, d.output.height), (1080, 1620))

    def test_unchosen_option_list_is_ignored(self):
        d = ProjectData()
        result = apply_brief('{"camera": {"angle": "Eye level | Top-down", "lens": "35mm"}}', d)
        self.assertEqual(d.camera.angle, "")
        self.assertEqual(d.camera.lens, "35mm")
        self.assertIn("Camera angle", result.skipped)

    def test_switching_sections_off(self):
        d = form_with_product()
        d.model.enabled = True
        apply_brief('{"human_model": {"enabled": false}, "contents": {"enabled": "no"}}', d)
        self.assertFalse(d.model.enabled)
        self.assertFalse(d.contents.enabled)

    def test_errors(self):
        d = ProjectData()
        self.assertFalse(apply_brief("", d).ok)
        self.assertFalse(apply_brief("Sorry, I can't see the image.", d).ok)
        self.assertFalse(apply_brief('{"weather": "sunny"}', d).ok)
        self.assertEqual(d.to_dict(), ProjectData().to_dict())

    def test_curly_quotes_are_forgiven(self):
        d = ProjectData()
        result = apply_brief("{\u201ccamera\u201d: {\u201cangle\u201d: \u201cTop-down\u201d}}", d)
        self.assertTrue(result.ok)
        self.assertEqual(d.camera.angle, "Top-down")

    def test_generated_prompt_json_can_be_pasted_back(self):
        from core.json_builder import build_prompt_json
        from core.sample import sample_project
        prompt = build_prompt_json(sample_project())
        d = ProjectData()
        result = apply_brief(json.dumps(prompt), d)
        self.assertTrue(result.ok)
        self.assertEqual(d.product.name, "Glasafe Borosilicate Container")
        self.assertEqual(d.product.materials, ["Borosilicate glass", "Silicone"])
        self.assertEqual(d.camera.angle, "3/4 front")
        self.assertEqual((d.output.width, d.output.height), (1080, 1350))


if __name__ == "__main__":
    unittest.main()
