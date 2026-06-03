# Architecture

## Design Principles

- Stages are independent.
- Disk artifacts are the integration boundary.
- JSON contracts are explicit and versioned.
- Placeholder logic is acceptable as long as it preserves the real future interface.
- Heavy model integrations should live behind adapters.

## Directory Layout

```text
ui_auto_gen/
  cli.py
  pipeline.py
  paths.py
  raster.py
  schemas.py
  utils.py
  visual_debug.py
  adapters/
    detector.py
    ocr.py
    segmenter.py
    background.py
    style.py
    reviewer.py
  stages/
    base.py
    ingest.py
    plan.py
    detect.py
    text_protect.py
    segment.py
    cutout.py
    background_repair.py
    style.py
    compose.py
    review.py
    export.py
  web/
    server.py
    static/
docs/
configs/
examples/
runs/
workspace/
```

## Runtime Artifact Layout

Each run creates:

```text
runs/{run_id}/
  job_config.json
  manifest.json
  00_ingest/
  01_plan/
  02_detect/
  02_ocr_protect/
  03_segment/
  04_cutout/
  04_background_repair/
  05_style/
  06_compose/
  07_review/
  08_export/
```

Each stage owns its directory. A stage may read prior stage outputs, but it should not mutate them.

## Stage Interface

Each stage receives a `PipelineContext` and returns a `StageResult`.

The context provides:

- Run ID.
- Run root.
- Job config.
- Managed stage paths.
- Manifest read/write helpers.

The result provides:

- Stage name.
- Status.
- Output artifact paths.
- Human-readable notes.

## Adapter Strategy

Model-backed stages should use small adapters:

```text
adapters/detector.py
  DetectorAdapter -> PlaceholderDetector -> LightweightDetector -> future YoloDetector / GroundedSamDetector
adapters/ocr.py
  OcrProtectAdapter -> PlaceholderOcrProtector -> RapidOcrProtector -> future PaddleOcrProtector / VlmOcrProtector
adapters/segmenter.py
  SegmenterAdapter -> PlaceholderSegmenter
adapters/sam2.py
  SegmenterAdapter -> Sam2TinySegmenter -> future larger SAM2 variants
adapters/background.py
  BackgroundRepairAdapter -> PlaceholderBackgroundRepair -> future InpaintingRepairAdapter
adapters/style.py
  StyleAdapter -> PlaceholderStyleAdapter -> LightweightStyleTransferAdapter -> future ControlNet/IPAdapter adapter
adapters/reviewer.py
  ReviewAdapter -> ContractReviewer -> future VLM reviewer
```

Only the adapter implementation should know model-specific details. The stage output contract should remain stable.

Lightweight detection is optional. `DetectStage` attempts `LightweightDetector` only when `algorithms.detector` requests `lightweight_detector`; otherwise it uses the placeholder detector. The current implementation uses SVG rectangle parsing for SVG inputs and Pillow-based edge/background connected components for raster images. It is a region-proposal algorithm, not a semantic detector.

SAM2 is optional. `SegmentStage` attempts `Sam2TinySegmenter` only when `algorithms.segmenter` requests `sam2`; otherwise it uses the placeholder segmenter. If SAM2 dependencies, checkpoint, device, or model initialization fail, the stage records a fallback reason and completes with placeholder masks.

RapidOCR is optional. `TextProtectStage` attempts `RapidOcrProtector` only when `algorithms.ocr` requests `rapidocr`; otherwise it uses the placeholder OCR protector. If RapidOCR or ONNX Runtime is unavailable, the stage records a fallback reason and completes with placeholder text locks.

Lightweight style transfer is optional. `StyleStage` attempts `LightweightStyleTransferAdapter` only when `algorithms.style` requests `lightweight_style_transfer`; otherwise it uses the placeholder style adapter. The current implementation uses Pillow-based color-statistics transfer from a reference image or `global_style.palette`, so it runs locally without GPU or large model dependencies.

## Visual Debug Artifacts

The current debug layer writes SVG previews without external dependencies:

- `02_detect/detection_preview.png`: raster base plus detection boxes.
- `02_ocr_protect/text_protect_preview.png`: raster base plus placeholder text locks.
- `03_segment/mask_preview.png`: raster base plus translucent placeholder masks.
- `04_cutout/cutout_preview.png`: transparent cutout contact sheet.
- `04_background_repair/background_repair_preview.png`: raster base plus inpainting placeholder regions.
- `05_style/style_preview.png`: contact sheet of generated styled assets.
- `06_compose/composition_preview.png`: raster base plus intended asset placement.

These previews are served by the local UI through `/artifacts/...` links.

## Raster Foundation

`ui_auto_gen.raster` provides the current image-processing base:

- Load PNG/JPG images through Pillow.
- Create a raster fallback canvas for unsupported formats such as SVG.
- Generate rectangular mask PNG files.
- Generate transparent cutout PNG files from masks.
- Generate placeholder styled PNG assets.
- Generate lightweight color-transferred styled PNG assets.
- Generate placeholder background repair patch PNG files.
- Alpha-composite styled assets into `final.png`.
- Restore protected text regions from the source image during composition.

The SVG fallback is a debugging approximation only. Uploaded PNG/JPG images use real pixels.

## Local UI

The local UI is served by `ui_auto_gen.web.server` and uses only the Python standard library. It accepts form input in the browser, writes a generated job config under `workspace/ui_jobs/`, invokes `PipelineRunner`, and serves run artifacts back from `runs/`.
