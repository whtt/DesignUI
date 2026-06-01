from __future__ import annotations

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class CutoutStage(PipelineStage):
    name = "04_cutout"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        cutouts_dir = paths.artifact("cutouts")
        cutouts_dir.mkdir(parents=True, exist_ok=True)
        segmentation_manifest = read_json(context.run_root / "03_segment" / "segmentation_manifest.json")

        cutouts = []
        for mask in segmentation_manifest["masks"]:
            cutout_id = f"cutout_{mask['mask_id']}"
            cutout_path = cutouts_dir / f"{cutout_id}.json"
            cutout_payload = {
                "schema_version": "1.0",
                "cutout_id": cutout_id,
                "mask_id": mask["mask_id"],
                "bbox": mask["bbox"],
                "alpha_asset_path": None,
                "background_repair_path": None,
                "note": "Placeholder cutout. Future implementation should write transparent PNG and inpaint metadata.",
            }
            write_json(cutout_path, cutout_payload)
            cutouts.append(
                {
                    "cutout_id": cutout_id,
                    "mask_id": mask["mask_id"],
                    "cutout_path": str(cutout_path),
                    "bbox": mask["bbox"],
                    "source": "placeholder_cutout",
                }
            )

        manifest = {
            "schema_version": "1.0",
            "cutouts": cutouts,
        }
        manifest_path = paths.artifact("cutout_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path), "cutouts_dir": str(cutouts_dir)},
            notes=[f"Created {len(cutouts)} placeholder cutout records."],
        )

