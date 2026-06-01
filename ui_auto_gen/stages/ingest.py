from __future__ import annotations

from pathlib import Path

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import copy_file, probe_image, resolve_path, write_json


class IngestStage(PipelineStage):
    name = "00_ingest"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        base_image_value = context.config.get("base_image")
        if not base_image_value:
            raise ValueError("Job config must include base_image.")

        source = resolve_path(str(base_image_value), context.config_path.parent)
        if not source.exists():
            source = resolve_path(str(base_image_value), context.repo_root)
        if not source.exists():
            raise FileNotFoundError(f"Base image not found: {source}")

        destination = paths.artifact(f"base_image{source.suffix}")
        copy_file(source, destination)

        image_metadata = probe_image(destination)
        manifest = {
            "schema_version": "1.0",
            "base_image": {
                "source_path": str(source),
                "run_path": str(destination),
                **image_metadata,
            },
        }
        manifest_path = paths.artifact("ingest_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path), "base_image": str(Path(destination))},
            notes=["Copied base image into the run directory."],
        )
