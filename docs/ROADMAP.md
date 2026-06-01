# Roadmap

## Phase 0: Framework Skeleton

- File-based pipeline.
- Stage contracts.
- Placeholder stages.
- Run manifest.
- Documentation.

## Phase 1: Real Visual Parsing

- Adapter interfaces for detector, segmenter, style, and review.
- Visual debug previews for detections and masks.
- UI run details panel with stage artifacts.
- OCR adapter.
- YOLO26 detector adapter for known UI classes.
- Grounded detector adapter for open-vocabulary prompts.
- SAM/SAM2 segmenter adapter.

## Phase 2: Real Editing

- Mask refinement.
- Inpainting.
- Text preservation and redraw.
- Parameterized UI element renderer.

## Phase 3: Style Generation

- Style reference ingestion.
- ControlNet/IPAdapter/LoRA generation adapter.
- Asset-library replacement for icons and controls.
- Automatic style-token extraction.

## Phase 4: Review And Repair

- VLM self-review.
- OCR text regression checks.
- Layout and overlap validation.
- Local repair loop.

## Phase 5: Production Workflow

- Batch runner.
- Web UI.
- Human correction UI.
- Figma/PSD/layer export.
- Evaluation datasets and score dashboards.
