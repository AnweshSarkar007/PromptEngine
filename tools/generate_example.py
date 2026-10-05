"""Regenerate the files in examples/ from core/sample.py using the real builders.

    python tools/generate_example.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.chatgpt_brief import build_instruction                  # noqa: E402
from core.json_builder import build_prompt_json, to_json_text   # noqa: E402
from core.project_manager import save_project, write_text_atomic  # noqa: E402
from core.prompt_builder import build_text_prompt                # noqa: E402
from core.sample import sample_project                           # noqa: E402


def main() -> int:
    out = ROOT / "examples"
    out.mkdir(exist_ok=True)
    data = sample_project()
    save_project(out / "example.project.json", data, relative_paths=False)
    prompt = build_prompt_json(data)
    write_text_atomic(out / "example_output.json", to_json_text(prompt) + "\n")
    write_text_atomic(out / "example_prompt.txt", build_text_prompt(prompt))
    write_text_atomic(out / "chatgpt_instruction.txt", build_instruction())
    print("Wrote example.project.json, example_output.json, example_prompt.txt and chatgpt_instruction.txt to", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
