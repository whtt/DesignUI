# Next Goal: Visual Debug Pipeline

## Objective

Before connecting real model adapters, upgrade the current placeholder pipeline into a visual debugging workflow.

This phase should make every run easier to inspect:

- Which algorithm was requested?
- Which placeholder adapter actually ran?
- What elements were planned?
- What boxes were detected?
- What masks were generated?
- Which artifacts belong to each stage?
- Where did the final output come from?

## Why This Comes Before Real Models

Real detection, segmentation, OCR, and style-transfer models will fail in different ways. Without visual debugging, it is hard to tell whether the problem is:

- prompt planning,
- detection,
- segmentation,
- cutout,
- generation,
- composition,
- or review.

This phase builds the inspection surface first, so later model integration can be incremental and easier to validate.

## Scope

### Adapter Boundaries

- Add explicit adapter interfaces for detection, segmentation, style generation, and review.
- Keep placeholder implementations as the default.
- Record both requested algorithm and actual adapter in stage manifests.

### Visual Debug Artifacts

- Generate a detection preview image with bounding boxes.
- Generate a mask preview image with translucent placeholder masks.
- Generate a composition preview image showing intended placement.
- Keep all visual artifacts inside the corresponding stage directory.

### UI Run Details

- Show debug preview images after a run.
- Show per-stage notes.
- Show per-stage artifact links.
- Make it obvious which outputs are placeholders.

## Out Of Scope

- Real YOLO/SAM/OCR/VLM integration.
- Real alpha cutout.
- Real inpainting.
- Neural or production-grade style transfer.
- PSD/Figma export.

## Done Criteria

- Done: Running the UI produces final output plus debug preview images.
- Done: The UI displays detection, mask, and composition previews.
- Done: Each stage in the UI can reveal its notes and artifact links.
- Done: The CLI pipeline still runs from `configs/sample_job.json`.
- Done: Docs identify completed and still-placeholder behavior.
