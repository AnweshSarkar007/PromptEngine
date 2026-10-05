"""The single entry point the UI uses: form data -> validation -> prompt JSON."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .json_builder import build_prompt_json, to_json_text
from .models import ProjectData
from .prompt_builder import build_text_prompt
from .providers import GenerationRequest
from .validation import ValidationIssue, has_errors, validate


@dataclass
class PipelineResult:
    issues: list[ValidationIssue] = field(default_factory=list)
    prompt: Optional[dict[str, Any]] = None
    json_text: str = ""
    text_prompt: str = ""

    @property
    def ok(self) -> bool:
        return self.prompt is not None

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.is_error]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if not i.is_error]


def run_pipeline(data: ProjectData) -> PipelineResult:
    """Validate; when there are no errors, build the JSON prompt and its text export."""
    issues = validate(data)
    if has_errors(issues):
        return PipelineResult(issues=issues)
    prompt = build_prompt_json(data)
    return PipelineResult(
        issues=issues,
        prompt=prompt,
        json_text=to_json_text(prompt),
        text_prompt=build_text_prompt(prompt),
    )


def to_generation_request(data: ProjectData, prompt: dict[str, Any]) -> GenerationRequest:
    """Bundle what an image-generation provider needs (used once an API is integrated)."""
    return GenerationRequest(
        prompt=prompt,
        product_images=list(data.reference.product_images),
    )
