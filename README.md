# Product Image Prompt Builder

A Windows desktop app that turns a simple form plus your product photos into a **structured JSON prompt** for AI image generation. It works fully offline, needs no database, and saves your work as plain `.project.json` files.

You upload 1–15 photos of the **new** product; the prompt lists them (by file name) under `reference_images.product_identity` as the "exclusive source of truth for product identity", with a strict identity lock so the image model does not redesign or swap the product. The look of the shot (scene, camera, lighting, composition, style) comes from the form, which ChatGPT can fill in for you from one of your existing catalogue photos (see *Filling the form from ChatGPT*).

```
USER INPUTS → STRUCTURED FORM → REFERENCE ROLE ASSIGNMENT → VALIDATION → JSON PROMPT → COPY / SAVE / EXPORT
```

---

## 1. Run from source

Requires **Python 3.10+** on Windows 10 or 11.

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 2. Using the app

1. **Reference Images** – drag & drop or *Add images…* (JPG, PNG, WEBP; up to 15) of the **new** product. Drag thumbnails to reorder, double-click (or *Set as primary*) to mark the **Primary Product Reference**.
2. **ChatGPT Brief** (optional, saves typing) – see below. ChatGPT studies a photo from your existing catalogue (an old product photo with the look you want) and fills in the scene, camera, lighting, composition and style cards for you.
3. Fill in / check the cards: **Product Details**, **Identity Lock**, **Scene & Environment**, **Product State**, **Food / Liquid**, **Human Model**, **Camera**, **Lighting**, **Composition**, **Visual Style**, **Output Settings**, **Restrictions**. The left navigation jumps to any card.
4. Click **Generate JSON** (Ctrl+G). If something required is missing, a red banner lists it — click an item to jump to the field.
5. **Copy JSON**, **Save JSON…** or **Export Prompt TXT…** from the preview panel. These always regenerate first, so you never copy stale output.
6. **Save Project** (Ctrl+S) keeps *everything* — fields, toggles, restrictions, output settings and image references — in a `.project.json`. **Load Project** (Ctrl+O) restores it. **Reset Form** returns to defaults.

Required before generating: at least one product image, product name, a scene type *or* environment description, at least one dimension, a camera angle, and a valid output width/height. Missing image files only produce a warning.

### Filling the form from ChatGPT

The app itself stays fully offline; it never contacts ChatGPT. You copy text across by hand:

1. In the **ChatGPT Brief** card click **Copy ChatGPT instruction**.
2. In ChatGPT, attach your **old product photo** and paste the instruction. It asks ChatGPT to describe only the photography and scene (never the old product's design) and to answer in a fixed JSON template whose options are exactly the app's dropdown values. A copy of the instruction is in [`examples/chatgpt_instruction.txt`](examples/chatgpt_instruction.txt).
3. Copy ChatGPT's whole reply, paste it into the box and click **Load into form**.

The app finds the JSON even when ChatGPT wraps it in other text or a code block, matches each value to the dropdown option (forgiving case, "Centre"/"Center", "25-35"/"25–35", "60%"), and keeps anything else as your own text so nothing is lost. Only fields ChatGPT actually filled are changed: your images, product details and restrictions are left alone. A summary shows what was filled, what was kept as free text and what was ignored. Review the cards, then click **Generate JSON**.

You can also paste a JSON prompt this app generated earlier; its settings load back into the form the same way.

Tips: toggling **Food / Liquid** or **Human Model** off hides their fields *and* removes them from the prompt. Model actions that start with an "-ing" verb ("Holding the product", "Opening the lid") read best in the generated sentence.

| Shortcut | Action |
|---|---|
| Ctrl+G | Generate JSON |
| Ctrl+Shift+C | Copy JSON |
| Ctrl+S / Ctrl+Shift+S | Save project / Save project as… |
| Ctrl+O | Load project |

## 3. What the JSON looks like

See [`examples/example_output.json`](examples/example_output.json) (built by the real code from [`examples/example.project.json`](examples/example.project.json)) and the plain-text version in [`examples/example_prompt.txt`](examples/example_prompt.txt).

The structure follows the brief exactly. A few deliberate details:

- **Images are listed by file name only**, e.g. `{ "filename": "front.jpg" }`. The prompt never reveals where the files live on your computer, and never embeds image data. Upload the same files alongside the prompt in your image tool. `primary_reference` is the primary image's file name. (Your `.project.json` still stores full paths so it can show the thumbnails again when you reopen it; that file is for you, not for the AI.)
- **Only product images are referenced.** The brief's original `scene_style_reference` was removed: the shot's look is described in the form (or filled from ChatGPT), so `reference_images` contains just `product_identity`.
- **Identity lock:** `product.identity_lock` contains the standard lock paragraph (when *Strict Product Identity Lock* is on) followed by your own custom instructions.
- **AI look avoidance:** when on, `visual_style.avoid_ai_look_instruction` holds the anti-AI-look text.
- **Switched-off sections** (`contents`, `human_model`) are emitted as just `{ "enabled": false }`, and are left out of `final_instruction`.
- Unset numbers are `null`. `restrictions` and `features` are lists (one entry per line you typed). `aspect_ratio` is calculated (odd sizes such as 800 × 1067 snap to the nearest common ratio, `3:4`).
- `final_instruction` is assembled from your selections by plain template logic (no AI involved): realism level, image type, preserved features, scene, product state, contents, model, camera, lighting, composition and output.

## 4. Building the Windows `.exe`

```bat
build.bat            :: one-folder build  ->  dist\Product Image Prompt Builder\Product Image Prompt Builder.exe
build.bat onefile    :: single-file build ->  dist\Product Image Prompt Builder.exe
```

`build.bat` creates a local `.venv`, installs `requirements.txt`, generates `assets\icon.ico` if it is missing, and runs PyInstaller (`--windowed`, so no console window). Equivalent manual command:

```bat
pyinstaller --noconfirm --clean --windowed --onedir --name "Product Image Prompt Builder" ^
  --icon assets\icon.ico --add-data "assets;assets" main.py
```

### One-folder vs one-file — the trade-off

| | **One-folder (default)** | One-file |
|---|---|---|
| Start-up | Fast | Slow: unpacks ~100+ MB of Qt to a temp folder on *every* launch |
| Antivirus / SmartScreen | Fewer false positives | More likely to be flagged (self-extracting exe) |
| Bundled assets (icon) | Plain files next to the exe | Extracted to a temp dir each run |
| Distribution | A folder (zip it, or use the installer) | One file to copy around |
| Installer | Ideal for Inno Setup | Works, but gains nothing |

Because the app bundles Qt (large, many DLLs) and an installer is the normal way to hand it to a team, **one-folder is the default**. Use `onefile` only if you really need a single portable file and can accept the slower start.

The assets (icon) are found at run time through `core/utils.py::resource_path()`, which works from source, one-folder and one-file builds.

Windows SmartScreen may warn about an unsigned `.exe` the first time ("More info → Run anyway"). Signing the executable with a code-signing certificate removes this.

## 5. Optional installer with Inno Setup

1. Install [Inno Setup 6.3+](https://jrsoftware.org/isinfo.php).
2. Run `build.bat` (the one-folder build).
3. Open `installer\setup.iss` in Inno Setup and press **Compile** (or run `ISCC.exe installer\setup.iss`).
4. The installer appears in `installer\Output\ProductImagePromptBuilder-Setup-1.0.0.exe`.

The installer:

- installs to **Program Files** (`{autopf}`),
- adds a **Start Menu** shortcut,
- offers an **optional Desktop shortcut** (unchecked by default),
- registers an **uninstaller** (Settings → Apps, and `unins000.exe` in the install folder),
- can launch the app when it finishes.

Before shipping, change `MyAppPublisher` and, for new releases, `MyAppVersion` (keep `AppId` the same so upgrades replace the old version).

Per-user settings and logs are kept in `%APPDATA%\ProductImagePromptBuilder` and `%LOCALAPPDATA%\ProductImagePromptBuilder`; the uninstaller leaves them so a reinstall remembers your preferences.

## 6. Project layout

```
product_prompt_builder/
├── main.py                  entry point: logging, error dialog hook, theme, window
├── core/                    pure Python, no Qt
│   ├── models.py            ProjectData dataclasses (single source of truth) + tolerant loader
│   ├── options.py           every dropdown list, preset and canned instruction text
│   ├── prompt_builder.py    final_instruction generator + plain-text export
│   ├── json_builder.py      ProjectData -> prompt dict -> pretty JSON
│   ├── validation.py        errors (block generation) and warnings
│   ├── chatgpt_brief.py     ChatGPT instruction + importer for its reply (offline text parsing)
│   ├── project_manager.py   save/load .project.json (atomic writes, moved-image recovery)
│   ├── pipeline.py          validate -> build, the one call the UI makes
│   ├── providers.py         ImageGenerationProvider interface (future API integration)
│   ├── sample.py            sample project used by tests and examples
│   └── utils.py             aspect ratio, line splitting, resource paths
├── ui/
│   ├── main_window.py       header, navigation, scrolling form, validation banner
│   ├── reference_panel.py   thumbnail grid (drop / reorder / primary)
│   ├── brief_panel.py       "ChatGPT Brief" card: copy instruction, paste reply, load into form
│   ├── product_panel.py     product details, identity lock, state, food/liquid cards
│   ├── scene_panel.py, model_panel.py, camera_panel.py (camera/lighting/composition/style),
│   │   output_panel.py (output + restrictions)
│   ├── json_preview.py      syntax-coloured preview + copy/save/export buttons
│   ├── widgets.py           toggle switch, chips, searchable choice field, card base class
│   └── theme.py             light / dark styling
├── assets/icon.ico          generated by tools/make_icon.py
├── tools/                   make_icon.py, generate_example.py
├── examples/                example project + generated JSON / TXT
├── tests/                   test_core.py, test_brief.py (unittest), smoke_ui.py (offscreen UI test)
├── installer/setup.iss      Inno Setup script
├── build.bat, requirements.txt
```

## 7. Adding an image-generation API later

The first version stops at the prompt, but the design keeps the seam clean:

- The UI calls only `core.pipeline.run_pipeline(data)` → `PipelineResult(prompt, json_text, …)`.
- `core/providers.py` defines `ImageGenerationProvider` with one method, `generate(GenerationRequest) -> GenerationResult`. `GenerationRequest` carries the prompt dict plus the local product image paths (use `pipeline.to_generation_request`).
- To integrate an API: implement a provider class, register it in `PROVIDERS`, and call it from `MainWindow.generate()` after a successful pipeline run (ideally in a worker thread). The form, validation and JSON builder do not change.

## 8. Tests

```bat
.venv\Scripts\python -m unittest discover tests -v          :: core logic (JSON structure, validation, projects…)
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python tests\smoke_ui.py                      :: builds the real window and drives it
```

`smoke_ui.py [folder]` can also save light/dark screenshots. On the offscreen platform set `QT_QPA_FONTDIR=C:\Windows\Fonts` so text renders.

## 9. Troubleshooting

- **A WEBP/JPG will not add:** the file is skipped with a note under the thumbnails when it is not a readable image (wrong format, corrupt, or not an image).
- **Images show "File missing" after moving a project:** keep the project next to its images, or re-add them; the loader also tries each image's path relative to the `.project.json`.
- **Something unexpected happened:** the app shows an error box and writes details to `%LOCALAPPDATA%\ProductImagePromptBuilder\app.log`.
- **Build fails on a new Python release:** `build.bat` uses whatever `python` / `py -3` is on PATH. If a brand-new Python is not yet supported by PyInstaller or PySide6, install Python 3.12 or 3.13 and delete `.venv` before building again.
