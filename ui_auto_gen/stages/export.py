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
        cutout_manifest = read_json(context.run_root / "04_cutout" / "cutout_manifest.json")
        style_manifest = read_json(context.run_root / "05_style" / "style_manifest.json")
        cutout_assets = [
            {
                "asset_id": cutout.get("cutout_id"),
                "generated_asset_path": cutout.get("alpha_asset_path"),
                "source": cutout.get("source"),
            }
            for cutout in cutout_manifest.get("cutouts", [])
        ]
        styled_assets = [
            {
                "asset_id": asset.get("asset_id"),
                "element_id": asset.get("element_id"),
                "generated_asset_path": asset.get("generated_asset_path"),
                "source": asset.get("source"),
            }
            for asset in style_manifest.get("styled_assets", [])
        ]

        summary = {
            "schema_version": "1.0",
            "run_id": context.run_id,
            "project_name": context.config.get("project_name"),
            "final_image": compose_manifest.get("final_image"),
            "cutout_assets": cutout_assets,
            "styled_assets": styled_assets,
            "generated_assets": styled_assets,
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
