from __future__ import annotations

import shutil
from pathlib import Path

from ui_auto_gen.paths import make_run_id, repo_root
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages import (
    ComposeStage,
    CutoutStage,
    DetectStage,
    ExportStage,
    IngestStage,
    PlanStage,
    ReviewStage,
    SegmentStage,
    StyleStage,
)
from ui_auto_gen.utils import read_json, utc_now_iso, write_json


class PipelineRunner:
    def __init__(self, output_root: Path | None = None) -> None:
        self.repo_root = repo_root()
        self.output_root = output_root or self.repo_root / "runs"
        self.stages = [
            IngestStage(),
            PlanStage(),
            DetectStage(),
            SegmentStage(),
            CutoutStage(),
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

    def _write_manifest(self, context: PipelineContext) -> None:
        write_json(context.run_root / "manifest.json", context.manifest)
