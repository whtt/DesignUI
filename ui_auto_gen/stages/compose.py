from __future__ import annotations

from pathlib import Path

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.raster import load_rgba_image, paste_assets, restore_regions, save_png
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_composition_preview


class ComposeStage(PipelineStage):
    name = "06_compose"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        style_manifest = read_json(context.run_root / "05_style" / "style_manifest.json")
        background_manifest = _read_optional_manifest(context.run_root / "04_background_repair" / "background_repair_manifest.json")
        text_manifest = _read_optional_manifest(context.run_root / "02_ocr_protect" / "text_protect_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        source_image = Path(ingest_manifest["base_image"]["run_path"])
        background_repairs = [
            {
                "asset_id": repair["repair_id"],
                "bbox": repair["bbox"],
                "generated_asset_path": repair.get("repair_asset_path"),
                "mode": "background_repair_placeholder",
            }
            for repair in background_manifest.get("repairs", [])
        ]
        placed_assets = [
            {
                "asset_id": asset["asset_id"],
                "bbox": asset["bbox"],
                "generated_asset_path": asset.get("generated_asset_path"),
                "mode": "alpha_paste_placeholder",
            }
            for asset in style_manifest["styled_assets"]
        ]
        base = load_rgba_image(source_image, width, height)
        final_image = paths.artifact("final.png")
        repaired_base = paste_assets(base, background_repairs)
        styled_image = paste_assets(repaired_base, placed_assets)
        protected_text_regions = text_manifest.get("text_regions", [])
        save_png(restore_regions(styled_image, base, protected_text_regions), final_image)
        preview_path = paths.artifact("composition_preview.png")
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
            "background_repairs": background_repairs,
            "placed_assets": placed_assets,
            "protected_text_regions": protected_text_regions,
            "notes": [
                "Raster compositor pasted placeholder background repair patches and styled assets, then restored protected text regions from the source image."
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
            notes=[
                f"Composited {len(background_repairs)} background repair placeholders and {len(placed_assets)} styled assets.",
                f"Restored {len(protected_text_regions)} protected text regions from the source image.",
            ],
        )


def _read_optional_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    return read_json(path)
