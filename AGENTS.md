# Repository Guidelines

## Project Structure & Module Organization

`ui_auto_gen/` contains the Python package. The main entry point is `ui_auto_gen/cli.py`; `pipeline.py` orchestrates staged runs. Stage implementations live in `ui_auto_gen/stages/`, model/local algorithm integrations live in `ui_auto_gen/adapters/`, raster helpers are in `ui_auto_gen/raster.py`, and visual previews are in `ui_auto_gen/visual_debug.py`. The local web UI is split between `ui_auto_gen/web/server.py` and static assets in `ui_auto_gen/web/static/`.

Sample job configs are in `configs/`. Project documentation is in `docs/`. Utility scripts are in `scripts/`. Agent automation material is in `skills/designui-automation/`. Generated artifacts such as `runs/`, `workspace/`, `models/`, and private notes should stay out of commits.

## Build, Test, and Development Commands

Install runtime dependencies:

```sh
pip install -r requirements.txt
```

Install optional model-backed algorithm dependencies for the target device:

```sh
pip install -r requirements-cpu.txt
# or, for CUDA 12.1 environments:
pip install -r requirements-gpu.txt
```

Run the local UI:

```sh
python -B -m ui_auto_gen.cli serve --port 8765
```

Run a smoke pipeline:

```sh
python -B -m ui_auto_gen.cli run --config configs/sample_job.json --run-id smoke_designui --overwrite
```

Validate syntax before committing:

```sh
python -B -m compileall -q ui_auto_gen scripts
node --check ui_auto_gen/web/static/app.js
git diff --check
```

## Coding Style & Naming Conventions

Use Python 3.10+ style with type hints where practical. Follow the existing 4-space indentation, small functions, `snake_case` for modules/functions/variables, and `PascalCase` for classes. Keep stage names and artifact directories consistent with the pipeline convention, for example `04_cutout` and `cutout_manifest.json`.

JavaScript in `ui_auto_gen/web/static/app.js` uses plain browser APIs, `const`/`let`, semicolons, and camelCase names. Keep CSS class names lowercase and hyphenated.

## Testing Guidelines

There is no dedicated test suite yet. Treat compile checks, `node --check`, and at least one CLI smoke run as the minimum validation. When changing adapters or stages, inspect the generated stage manifest for `actual_adapter`, `fallback`, artifact paths, and count fields. Prefer deterministic sample configs in `configs/` for repeatable checks.

## Commit & Pull Request Guidelines

Recent commits use short imperative subjects, for example `Add run details rerun and review checks` or `Fix direct run cache deletion`. Keep the subject specific and under roughly 72 characters.

Commit cohesive changes after running the relevant validation; do not commit generated artifacts from `runs/`, `workspace/`, `models/`, `external/`, `.venv/`, or `private/`. Add new local-only output paths to `.gitignore` before generating files.

Pull requests should describe the behavior change, list validation commands run, link related issues or docs, and include screenshots when the web UI changes. Push reviewed local commits to `origin` and use PRs for shared review. Update relevant docs in `docs/` when data contracts, commands, or pipeline behavior change.
