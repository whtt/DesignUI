from __future__ import annotations

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class ExportStage(PipelineStage):
    name = "08_export"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        compose_manifest = read_json(context.run_root / "06_compose" / "compose_manifest.json")
        review_manifest = read_json(context.run_root / "07_review" / "review_manifest.json")

        summary = {
            "schema_version": "1.0",
            "run_id": context.run_id,
            "project_name": context.config.get("project_name"),
            "final_image": compose_manifest.get("final_image"),
            "review": {
                "pass": review_manifest.get("pass"),
                "score": review_manifest.get("score"),
                "issues": review_manifest.get("issues", []),
            },
            "stage_manifests": {
                stage_name: stage_data.get("manifest")
                for stage_name, stage_data in context.manifest.get("stages", {}).items()
            },
        }
        summary_path = paths.artifact("run_summary.json")
        write_json(summary_path, summary)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(summary_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"summary": str(summary_path), "final_image": str(compose_manifest.get("final_image"))},
            notes=["Exported run summary."],
        )

