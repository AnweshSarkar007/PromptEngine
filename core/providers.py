"""Extension point for plugging in a real image-generation API later.

The app today runs `PromptOnlyProvider`, which just hands the generated prompt back. To add an
API (OpenAI, Gemini, Stability, ...), implement `ImageGenerationProvider.generate`, register it in
`PROVIDERS`, and call it from `MainWindow` after `pipeline.run_pipeline` succeeds. Nothing in the
form, validation or JSON builder needs to change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass
class GenerationRequest:
    prompt: dict[str, Any]                  # output of json_builder.build_prompt_json
    product_images: list[str]               # local file paths, in order (primary is prompt-side)


@dataclass
class GenerationResult:
    ok: bool
    message: str = ""
    output_files: list[str] = field(default_factory=list)


class ImageGenerationProvider(Protocol):
    name: str

    def generate(self, request: GenerationRequest) -> GenerationResult: ...


class PromptOnlyProvider:
    """Default provider: no image is generated; the prompt is simply ready to copy / save."""

    name = "Prompt only (no image generation)"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(ok=True, message="Prompt generated. No image API is configured.")


PROVIDERS: dict[str, ImageGenerationProvider] = {"prompt_only": PromptOnlyProvider()}


def get_provider(key: str = "prompt_only") -> ImageGenerationProvider:
    return PROVIDERS[key]
