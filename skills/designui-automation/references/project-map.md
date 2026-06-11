# DesignUI Project Map

Use this reference when a future conversation needs quick orientation.

## Product

DesignUI is a local automated UI image generation/editing workflow. It converts a base image, prompt, rules, target elements or manual boxes, optional reference image, and selected algorithms into a file-based pipeline run with debug previews, manifests, and a final image.

## Current Core Flow

```text
00_ingest
01_plan
02_detect
02_ocr_protect
03_segment
04_cutout
04_background_repair
05_style
06_compose
07_review
08_export
```

Every stage owns its output directory under `runs/{run_id}/`.

## Key Entry Points

- `README.md`: install, run, and user-facing overview.
- `docs/PROJECT_GUIDE.md`: project navigation and task locator.
- `docs/WORKFLOW.md`: stage-by-stage workflow.
- `docs/ARCHITECTURE.md`: module and adapter boundaries.
- `docs/DATA_CONTRACTS.md`: JSON manifests.
- `docs/IMPLEMENTATION_STATUS.md`: what is real, what is placeholder.
- `docs/MODEL_SETUP.md`: optional SAM2/RapidOCR/model setup.
- `configs/`: runnable sample jobs.
- `ui_auto_gen/cli.py`: CLI entry point.
- `ui_auto_gen/pipeline.py`: runner and stage orchestration.
- `ui_auto_gen/web/server.py`: local UI API server.

## Current Real Adapters

- `LightweightDetector`: local region proposals for SVG and PNG/JPG.
- `OmniParserDetector`: optional UI element detection through an isolated OmniParser subprocess.
- `Sam2Segmenter`: optional SAM2.1 segmentation.
- `RapidOcrProtector`: optional RapidOCR text detection.
- `LightweightStyleTransferAdapter`: local color-statistics style transfer.
- `ContractReviewer`: contract-level review, not visual VLM review.

## Important Limitations

- Lightweight detection is not semantic object detection.
- SAM2 depends on local dependencies and checkpoint; fallback is expected.
- Background repair is still placeholder, not real inpainting.
- Visual self-review is still contract-level, not VLM-based.
- Some UI dropdown options only record intent and do not execute real adapters yet.
