from __future__ import annotations

import shutil
from pathlib import Path

from ui_auto_gen.paths import make_run_id, repo_root
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages import (
    BackgroundRepairStage,
    ComposeStage,
    CutoutStage,
    DetectStage,
    ExportStage,
    IngestStage,
    PlanStage,
    ReviewStage,
    SegmentStage,
    StyleStage,
    TextProtectStage,
)
from ui_auto_gen.utils import read_json, utc_now_iso, write_json


STAGE_DEPENDENCIES: dict[str, list[str]] = {
    "00_ingest": [
        "00_ingest",
        "01_plan",
        "02_detect",
        "02_ocr_protect",
        "03_segment",
        "04_cutout",
        "04_background_repair",
        "05_style",
        "06_compose",
        "07_review",
        "08_export",
    ],
    "01_plan": [
        "01_plan",
        "02_detect",
        "02_ocr_protect",
        "03_segment",
        "04_cutout",
        "04_background_repair",
        "05_style",
        "06_compose",
        "07_review",
        "08_export",
    ],
    "02_detect": [
        "02_detect",
        "02_ocr_protect",
        "03_segment",
        "04_cutout",
        "04_background_repair",
        "05_style",
        "06_compose",
        "07_review",
        "08_export",
    ],
    "02_ocr_protect": ["02_ocr_protect", "06_compose", "07_review", "08_export"],
    "03_segment": ["03_segment", "04_cutout", "04_background_repair", "05_style", "06_compose", "07_review", "08_export"],
    "04_cutout": ["04_cutout", "04_background_repair", "05_style", "06_compose", "07_review", "08_export"],
    "04_background_repair": ["04_background_repair", "06_compose", "07_review", "08_export"],
    "05_style": ["05_style", "06_compose", "07_review", "08_export"],
    "06_compose": ["06_compose", "07_review", "08_export"],
    "07_review": ["07_review", "08_export"],
    "08_export": ["08_export"],
}


class PipelineRunner:
    def __init__(self, output_root: Path | None = None) -> None:
        self.repo_root = repo_root()
        self.output_root = output_root or self.repo_root / "runs"
        self.stages = [
            IngestStage(),
            PlanStage(),
            DetectStage(),
            TextProtectStage(),
            SegmentStage(),
            CutoutStage(),
            BackgroundRepairStage(),
            StyleStage(),
            ComposeStage(),
            ReviewStage(),
            ExportStage(),
        ]

    def run(self, config_path: Path, run_id: str | None = None, overwrite: bool = False) -> tuple[PipelineContext, list[StageResult]]:
        resolved_config = config_path.resolve()
        config = read_json(resolved_config)
        created_at = utc_now_iso()
        actual_run_id = run_id or make_run_id(config.get("project_name", "ui_run"), created_at)
        run_root = self.output_root / actual_run_id

        if run_root.exists() and overwrite:
            actual_run_id = f"{actual_run_id}_{make_run_id('replacement', utc_now_iso())}"
            run_root = self.output_root / actual_run_id
        if run_root.exists():
            raise FileExistsError(f"Run directory already exists: {run_root}")

        run_root.mkdir(parents=True, exist_ok=False)
        shutil.copy2(resolved_config, run_root / "job_config.json")

        manifest = {
            "schema_version": "1.0",
            "run_id": actual_run_id,
            "project_name": config.get("project_name"),
            "created_at": created_at,
            "config_path": str(resolved_config),
            "stages": {},
        }
        context = PipelineContext(
            run_id=actual_run_id,
            repo_root=self.repo_root,
            run_root=run_root,
            config_path=resolved_config,
            config=config,
            manifest=manifest,
        )

        results: list[StageResult] = []
        try:
            for stage in self.stages:
                result = stage.run(context)
                results.append(result)
                self._write_manifest(context)
        except Exception as exc:
            context.manifest["failed_at"] = stage.name if "stage" in locals() else "startup"
            context.manifest["error"] = str(exc)
            self._write_manifest(context)
            raise

        context.manifest["completed_at"] = utc_now_iso()
        self._write_manifest(context)
        return context, results

    def rerun_from_stage(self, run_root: Path, stage_name: str) -> tuple[PipelineContext, list[StageResult]]:
        resolved_run_root = run_root.resolve()
        config_path = resolved_run_root / "job_config.json"
        manifest_path = resolved_run_root / "manifest.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Run config not found: {config_path}")
        if stage_name not in STAGE_DEPENDENCIES:
            raise ValueError(f"Unsupported stage for rerun: {stage_name}")

        config = read_json(config_path)
        manifest = read_json(manifest_path) if manifest_path.exists() else {}
        run_id = str(manifest.get("run_id") or resolved_run_root.name)
        stages_to_run = STAGE_DEPENDENCIES[stage_name]

        for name in stages_to_run:
            stage_dir = resolved_run_root / name
            if stage_dir.exists():
                shutil.rmtree(stage_dir)
            manifest.get("stages", {}).pop(name, None)

        manifest.setdefault("schema_version", "1.0")
        manifest["run_id"] = run_id
        manifest["project_name"] = config.get("project_name")
        manifest.setdefault("created_at", utc_now_iso())
        manifest["config_path"] = str(config_path)
        manifest["rerun_at"] = utc_now_iso()
        manifest["rerun_from_stage"] = stage_name
        manifest.pop("failed_at", None)
        manifest.pop("error", None)

        context = PipelineContext(
            run_id=run_id,
            repo_root=self.repo_root,
            run_root=resolved_run_root,
            config_path=config_path,
            config=config,
            manifest=manifest,
        )

        stage_by_name = {stage.name: stage for stage in self.stages}
        results: list[StageResult] = []
        try:
            for name in stages_to_run:
                result = stage_by_name[name].run(context)
                results.append(result)
                self._write_manifest(context)
        except Exception as exc:
            context.manifest["failed_at"] = name if "name" in locals() else stage_name
            context.manifest["error"] = str(exc)
            self._write_manifest(context)
            raise

        context.manifest["completed_at"] = utc_now_iso()
        self._write_manifest(context)
        return context, results

    def _write_manifest(self, context: PipelineContext) -> None:
        write_json(context.run_root / "manifest.json", context.manifest)
