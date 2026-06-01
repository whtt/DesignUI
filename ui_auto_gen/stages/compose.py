from __future__ import annotations

from pathlib import Path

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import copy_file, read_json, write_json
from ui_auto_gen.visual_debug import write_composition_preview


class ComposeStage(PipelineStage):
    name = "06_compose"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        style_manifest = read_json(context.run_root / "05_style" / "style_manifest.json")

        source_image = Path(ingest_manifest["base_image"]["run_path"])
        final_image = paths.artifact(f"final{source_image.suffix}")
        copy_file(source_image, final_image)
        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        placed_assets = [
            {
                "asset_id": asset["asset_id"],
                "bbox": asset["bbox"],
                "mode": "not_applied_placeholder",
            }
            for asset in style_manifest["styled_assets"]
        ]
        preview_path = paths.artifact("composition_preview.svg")
        write_composition_preview(
            base_image=source_image,
            width=width,
            height=height,
            placed_assets=placed_assets,
            destination=preview_path,
        )

        manifest = {
            "schema_version": "1.0",
            "final_image": str(final_image),
            "debug_artifacts": {
                "composition_preview": str(preview_path),
            },
            "composition_source": "placeholder_compositor",
            "placed_assets": placed_assets,
            "notes": [
                "Placeholder compositor copied the base image. Future compositor should apply styled assets by layer."
            ],
        }
        manifest_path = paths.artifact("compose_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={
                "manifest": str(manifest_path),
                "final_image": str(final_image),
                "composition_preview": str(preview_path),
            },
            notes=["Copied base image as placeholder final output."],
        )
