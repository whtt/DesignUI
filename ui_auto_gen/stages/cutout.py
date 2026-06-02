from __future__ import annotations

from pathlib import Path

from PIL import Image

from ui_auto_gen.raster import cutout_contact_sheet, cutout_from_mask, load_rgba_image, save_png
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class CutoutStage(PipelineStage):
    name = "04_cutout"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        cutouts_dir = paths.artifact("cutouts")
        cutouts_dir.mkdir(parents=True, exist_ok=True)
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        segmentation_manifest = read_json(context.run_root / "03_segment" / "segmentation_manifest.json")
        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        base_image = load_rgba_image(Path(ingest_manifest["base_image"]["run_path"]), width, height)

        cutouts = []
        for mask in segmentation_manifest["masks"]:
            cutout_id = f"cutout_{mask['mask_id']}"
            cutout_path = cutouts_dir / f"{cutout_id}.json"
            mask_png_path = Path(mask["mask_png_path"])
            alpha_asset_path = cutouts_dir / f"{cutout_id}.png"
            with Image.open(mask_png_path) as mask_image:
                cutout_image = cutout_from_mask(base_image, mask_image.convert("L"), mask["bbox"])
            save_png(cutout_image, alpha_asset_path)
            cutout_payload = {
                "schema_version": "1.0",
                "cutout_id": cutout_id,
                "mask_id": mask["mask_id"],
                "bbox": mask["bbox"],
                "mask_png_path": str(mask_png_path),
                "alpha_asset_path": str(alpha_asset_path),
                "background_repair_path": None,
                "note": "Raster cutout generated from the current mask. Background repair is still not implemented.",
            }
            write_json(cutout_path, cutout_payload)
            cutouts.append(
                {
                    "cutout_id": cutout_id,
                    "mask_id": mask["mask_id"],
                    "cutout_path": str(cutout_path),
                    "mask_png_path": str(mask_png_path),
                    "alpha_asset_path": str(alpha_asset_path),
                    "bbox": mask["bbox"],
                    "source": "raster_cutout",
                }
            )

        preview_path = paths.artifact("cutout_preview.png")
        save_png(cutout_contact_sheet(cutouts), preview_path)
        manifest = {
            "schema_version": "1.0",
            "cutouts": cutouts,
            "debug_artifacts": {
                "cutout_preview": str(preview_path),
            },
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
            artifacts={
                "manifest": str(manifest_path),
                "cutouts_dir": str(cutouts_dir),
                "cutout_preview": str(preview_path),
            },
            notes=[f"Created {len(cutouts)} raster cutout PNG assets."],
        )
