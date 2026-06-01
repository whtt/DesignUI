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
  schemas.py
  utils.py
  visual_debug.py
  adapters/
    detector.py
    segmenter.py
    style.py
    reviewer.py
  stages/
    base.py
    ingest.py
    plan.py
    detect.py
    segment.py
    cutout.py
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
  03_segment/
  04_cutout/
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
  DetectorAdapter -> PlaceholderDetector -> future YoloDetector / GroundedSamDetector
adapters/segmenter.py
  SegmenterAdapter -> PlaceholderSegmenter -> future SamSegmenter / YoloSegmenter
adapters/style.py
  StyleAdapter -> PlaceholderStyleAdapter -> future ControlNet/IPAdapter adapter
adapters/reviewer.py
  ReviewAdapter -> ContractReviewer -> future VLM reviewer
```

Only the adapter implementation should know model-specific details. The stage output contract should remain stable.

## Visual Debug Artifacts

The current debug layer writes SVG previews without external dependencies:

- `02_detect/detection_preview.svg`: base image plus detection boxes.
- `03_segment/mask_preview.svg`: base image plus translucent placeholder masks.
- `06_compose/composition_preview.svg`: base image plus intended asset placement.

These previews are served by the local UI through `/artifacts/...` links.

## Local UI

The local UI is served by `ui_auto_gen.web.server` and uses only the Python standard library. It accepts form input in the browser, writes a generated job config under `workspace/ui_jobs/`, invokes `PipelineRunner`, and serves run artifacts back from `runs/`.
