# DesignUI Task Playbook

Use this reference for common operations.

## Check Workspace State

```powershell
git status --short
```

Read changed files before editing them. Do not revert unrelated changes.

## Run The Local UI

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli serve --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

If port `8765` is busy, use another port unless the user asks to restart the current server.

## Run CLI Smoke Tests

Minimal pipeline:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_job.json --run-id smoke_designui --overwrite
```

Lightweight detector plus optional models:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_lightweight_detector_job.json --run-id smoke_lightweight_detector --overwrite
```

SAM2:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_sam2_job.json --run-id smoke_sam2 --overwrite
```

RapidOCR:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_rapidocr_job.json --run-id smoke_rapidocr --overwrite
```

Lightweight style transfer:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_lightweight_style_job.json --run-id smoke_style --overwrite
```

## Inspect A Run

Start from:

```text
runs/{run_id}/08_export/run_summary.json
```

Then inspect stage manifests:

- `02_detect/detection_manifest.json`
- `02_ocr_protect/text_protect_manifest.json`
- `03_segment/segmentation_manifest.json`
- `05_style/style_manifest.json`
- `06_compose/compose_manifest.json`
- `07_review/review_manifest.json`

Check `actual_adapter` and `fallback` before assuming a model actually ran.

## Standard Validation

```powershell
.\.venv\Scripts\python.exe -B -m compileall -q ui_auto_gen scripts
node --check ui_auto_gen\web\static\app.js
git diff --check
```

Use Browser/in-app verification after meaningful frontend changes.

## Documentation Updates

- Change behavior: update `docs/IMPLEMENTATION_STATUS.md`.
- Change stages or flow: update `docs/WORKFLOW.md`.
- Change architecture or adapter boundary: update `docs/ARCHITECTURE.md`.
- Change manifest fields: update `docs/DATA_CONTRACTS.md`.
- Change optional model setup: update `docs/MODEL_SETUP.md`.
- Add major feature scope: update `docs/FEATURE_REQUIREMENTS.md` or `docs/ROADMAP.md`.
