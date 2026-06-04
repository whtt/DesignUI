---
name: designui-automation
description: "Use when working on the DesignUI repository: automated UI image generation workflows, local Web UI, file-based pipeline stages, model adapters for detection/SAM2/OCR/style transfer, run artifacts, docs navigation, debugging, or planning the next implementation step."
---

# DesignUI Automation

Use this skill to understand, run, debug, and extend the DesignUI project without loading every project document into context.

## First Pass

1. Start from the repository root.
2. Read `references/project-map.md` for the fastest project map.
3. Check `git status --short` before changing files.
4. Use the task router below to load only the needed reference.

## Task Router

- **Understand the product quickly**: read `references/project-map.md`.
- **Run or verify the pipeline**: read `references/task-playbook.md`, then use `README.md` for exact commands.
- **Change a stage or adapter**: read `references/adapter-guide.md`, then inspect the matching files in `ui_auto_gen/stages/` and `ui_auto_gen/adapters/`.
- **Check current capability status**: read `docs/IMPLEMENTATION_STATUS.md`.
- **Modify JSON contracts**: read `docs/DATA_CONTRACTS.md`.
- **Plan product scope or next milestones**: read `docs/FEATURE_REQUIREMENTS.md`, `docs/ROADMAP.md`, and `private/IMPLEMENTATION_PATH.md` if available.
- **Set up optional local models**: read `docs/MODEL_SETUP.md`.
- **Debug UI/artifact display**: read `docs/NEXT_GOAL_DEBUG_UI.md`, then inspect `ui_auto_gen/web/` and `ui_auto_gen/visual_debug.py`.

## Working Rules

- Keep stages independent. Stage outputs are JSON manifests and files under `runs/{run_id}/{stage}/`.
- Keep model-specific code behind adapters. Stages should select adapters and record `requested_algorithm`, `actual_adapter`, `model`, and `fallback`.
- Preserve fallback behavior. Optional model adapters must fail soft and keep the pipeline runnable.
- Prefer small, inspectable artifacts over hidden state. Add previews or manifest fields when adding new behavior.
- Update docs with code changes. At minimum, update `docs/IMPLEMENTATION_STATUS.md`; update contracts/setup docs when interfaces or dependencies change.
- Do not commit generated artifacts from `runs/`, `workspace/`, `models/`, `external/`, `private/`, or ignored chat exports.

## Validation

Use the smallest verification that covers the change:

```powershell
.\.venv\Scripts\python.exe -B -m compileall -q ui_auto_gen scripts
node --check ui_auto_gen\web\static\app.js
git diff --check
```

For end-to-end checks:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_job.json --run-id smoke_designui --overwrite
```

Use model-specific sample configs only when that adapter is touched.
