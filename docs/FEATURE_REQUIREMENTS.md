# Feature Requirements

This document describes the public product capabilities DesignUI should eventually support. It is intentionally implementation-light and safe to publish.

## Core Workflow

- Users can provide a base UI image.
- Users can provide a prompt describing the desired visual transformation.
- Users can provide positive rules and negative rules.
- Users can provide a reference image.
- Users can choose algorithms for planning, detection, segmentation, OCR, style replacement, composition, and review.
- Users can run the workflow without writing code.
- Users can inspect final output and intermediate artifacts.

## Input Modes

- Example base image.
- Uploaded base image.
- Text-to-image generated base image.
- Reference image upload.
- Future: multiple reference images.
- Future: brand/design-token input.
- Future: Figma or HTML input.

## Element Selection

Users should be able to define target elements in several ways:

- Text prompt: "buttons, cards, avatars, charts".
- Manual rectangle selection on the image. Current version supports this as the first correction UI.
- Manual polygon/lasso selection.
- Click-to-select detected elements.
- Brush-based mask correction.
- Future: natural-language refinement, such as "select the blue CTA button".

Manual selection is important because model detection will not always be reliable. The system should allow human correction without rerunning the entire pipeline.

## Visual Parsing

- Detect UI elements.
- Segment target elements.
- Preserve text regions.
- Identify layout hierarchy.
- Identify reusable UI components.
- Extract color, radius, shadow, stroke, and spacing tokens.

## Placeholder Communication

Early versions must make unfinished model integrations visually obvious:

- Instance segmentation placeholders should tint the target area and clearly label the preview as a future mask/model step.
- Style replacement placeholders should use an obvious marker, such as an emoji/sticker, instead of pretending to be final generated art.
- OCR protection placeholders should explain that future text locks will protect detected text regions.
- Background repair placeholders should explain that future inpainting will repair removed or replaced regions.
- Placeholder metadata should identify the future adapter family that is expected to replace the placeholder.

## Raster Editing

- Generate mask PNG files.
- Generate transparent cutout PNG files.
- Generate preview images for every major stage.
- Support simple alpha compositing.
- Support background repair placeholders.
- Future: real inpainting.
- Future: edge feathering and matting.
- Future: shadow separation.

## Style Replacement

- Replace selected elements with generated assets.
- Support parameterized UI redraw for controls such as buttons, cards, forms, and tables.
- Support asset-library replacement for icons.
- Support image-generation-based replacement for avatars, illustrations, and decorative elements.
- Preserve text content unless the user explicitly asks otherwise.

## Review And Repair

- Check whether all requested elements were processed.
- Check text readability.
- Check layout preservation.
- Check style consistency.
- Check visible artifacts such as dirty edges.
- Allow local retry for only the failed element or stage.

## Run Management

- Show run history.
- Show per-run summary.
- Show per-stage manifests.
- Show per-stage visual artifacts.
- Allow rerun from a specific stage.
- Allow compare before/after.
- Allow export of debug bundles.

## Export

- Final PNG/JPG.
- Layered JSON.
- Future: PSD.
- Future: layered PNG.
- Future: Figma document.
- Future: HTML/CSS reconstruction.

## Non-Goals For Early Versions

- Full production design automation.
- Perfect UI-to-code reconstruction.
- Fully autonomous visual judgment.
- Replacing a human designer.
