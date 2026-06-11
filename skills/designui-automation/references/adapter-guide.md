# DesignUI Adapter Guide

Use this reference when adding or modifying a pipeline stage, adapter, or model integration.

## Adapter Contract Pattern

Adapters should:

- expose a small class with `adapter_name`
- return file paths and metadata that match the stage manifest contract
- record model metadata when real inference or local algorithm behavior runs
- raise clear exceptions on setup/inference failure
- let the stage catch failures and write a fallback record

Stages should:

- read prior manifests from `context.run_root`
- select the adapter from `context.config["algorithms"]`
- write a manifest under their own stage directory
- write visual debug artifacts when useful
- return `StageResult` with concise notes

## Existing Adapter Files

- `ui_auto_gen/adapters/detector.py`
- `ui_auto_gen/adapters/ocr.py`
- `ui_auto_gen/adapters/sam2.py`
- `ui_auto_gen/adapters/segmenter.py`
- `ui_auto_gen/adapters/background.py`
- `ui_auto_gen/adapters/style.py`
- `ui_auto_gen/adapters/reviewer.py`

## Existing Stage Files

- `ui_auto_gen/stages/detect.py`
- `ui_auto_gen/stages/text_protect.py`
- `ui_auto_gen/stages/segment.py`
- `ui_auto_gen/stages/cutout.py`
- `ui_auto_gen/stages/background_repair.py`
- `ui_auto_gen/stages/style.py`
- `ui_auto_gen/stages/compose.py`
- `ui_auto_gen/stages/review.py`

## Fallback Manifest Shape

Use this pattern when optional adapters fail:

```json
{
  "requested_algorithm": "sam2",
  "actual_adapter": "placeholder_segmenter",
  "model": null,
  "fallback": {
    "requested_adapter": "sam2_segmenter",
    "fallback_adapter": "placeholder_segmenter",
    "reason": "checkpoint missing"
  }
}
```

## New Adapter Checklist

1. Add or update adapter class.
2. Export it from `ui_auto_gen/adapters/__init__.py` if other modules import it there.
3. Update the relevant stage selection logic.
4. Add or update manifest fields.
5. Add a sample config if the adapter is user-selectable.
6. Add UI option if it should be selectable from the Web UI.
7. Update docs listed in `references/task-playbook.md`.
8. Run compile, frontend syntax check, diff check, and a targeted smoke test.

## UI Option Checklist

When adding a dropdown algorithm:

- add the option in `ui_auto_gen/web/static/index.html`
- ensure `ui_auto_gen/web/static/app.js` includes it in the payload if needed
- ensure `ui_auto_gen/web/server.py` writes it into job config
- ensure the stage recognizes the algorithm value
- document whether it is real, optional, or placeholder
