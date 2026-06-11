# Project Guide

This guide is the progressive-disclosure entry point for future DesignUI conversations. Start here, then open only the document that matches the task.

## Snapshot

DesignUI is a local automated UI image generation/editing pipeline. It takes a base image, prompt, rules, target elements, optional reference image, and algorithm choices, then writes independent stage artifacts and debug previews.

Current real or optional local capabilities:

- lightweight local region detection
- manual rectangle selection
- OmniParser UI element detection
- SAM2.1 segmentation
- RapidOCR text protection
- lightweight color-statistics style transfer
- raster cutout and composition
- debug artifact gallery in the local UI

Still mostly placeholder:

- semantic/open-vocabulary detection
- real background inpainting
- parameterized UI redraw
- VLM visual review and automatic repair loop

## Read Next By Task

- **Run the app**: read `README.md`.
- **Understand the pipeline**: read `docs/WORKFLOW.md`.
- **Understand code boundaries**: read `docs/ARCHITECTURE.md`.
- **See what is actually connected**: read `docs/IMPLEMENTATION_STATUS.md`.
- **Work with manifests**: read `docs/DATA_CONTRACTS.md`.
- **Plan product scope**: read `docs/FEATURE_REQUIREMENTS.md` and `docs/ROADMAP.md`.
- **Set up optional models**: read `docs/MODEL_SETUP.md`.
- **Work on visual debugging UI**: read `docs/NEXT_GOAL_DEBUG_UI.md`.
- **Continue private implementation planning**: read `private/IMPLEMENTATION_PATH.md` if present.
- **Use as a Codex skill**: read `skills/designui-automation/SKILL.md`.

## Common Commands

Run UI:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli serve --port 8765
```

Run minimal pipeline:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_job.json --run-id smoke_designui --overwrite
```

Validate code:

```powershell
.\.venv\Scripts\python.exe -B -m compileall -q ui_auto_gen scripts
node --check ui_auto_gen\web\static\app.js
git diff --check
```

Optional algorithm dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-cpu.txt
# or, for CUDA 12.1 environments:
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
```

Optional OmniParser detector environment:

```powershell
conda create -n designui_omni python=3.12
conda run -n designui_omni python -m pip install -r requirements-omniparser.txt
python scripts\download_omniparser_weights.py
```

## File Locator

- `ui_auto_gen/pipeline.py`: stage orchestration.
- `ui_auto_gen/stages/`: stage logic.
- `ui_auto_gen/adapters/`: model/local algorithm adapters.
- `ui_auto_gen/raster.py`: PNG/JPG loading, masks, cutouts, composition helpers.
- `ui_auto_gen/visual_debug.py`: preview images.
- `ui_auto_gen/web/server.py`: local HTTP API.
- `ui_auto_gen/web/static/`: frontend UI.
- `configs/`: sample jobs.
- `runs/`: generated artifacts, ignored by Git.
- `workspace/`: generated UI jobs and logs, ignored by Git.
- `models/`: local checkpoints, ignored by Git.
- `private/`: private planning notes, ignored by Git.

## Change Checklist

Before editing:

```powershell
git status --short
```

After editing:

- Update docs that match the changed behavior.
- Run the smallest useful smoke test.
- Check `actual_adapter` and `fallback` in manifests when validating model behavior.
- Keep generated artifacts out of Git.

## Development Process

- Commit cohesive changes after validation; do not commit generated outputs from `runs/`, `workspace/`, `models/`, `external/`, `.venv/`, or `private/`.
- Add new generated or local-only paths to `.gitignore` before running tools that create them.
- Use short imperative commit subjects, for example `Add optional model requirements`.
- Push only reviewed local commits to `origin`; use a pull request for shared review.
- PR descriptions should state the behavior change, validation commands, related issue or doc links, and screenshots for UI changes.
