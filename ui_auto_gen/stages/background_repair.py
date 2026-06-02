from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters.background import PlaceholderBackgroundRepair
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_background_repair_preview


class BackgroundRepairStage(PipelineStage):
    name = "04_background_repair"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        repairs_dir = paths.artifact("repairs")
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        cutout_manifest = read_json(context.run_root / "04_cutout" / "cutout_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        adapter = PlaceholderBackgroundRepair()
        repairs = adapter.create_repairs(
            cutouts=cutout_manifest["cutouts"],
            repairs_dir=repairs_dir,
            image_size=(width, height),
        )

        preview_path = paths.artifact("background_repair_preview.png")
        write_background_repair_preview(
            base_image=Path(ingest_manifest["base_image"]["run_path"]),
            width=width,
            height=height,
            repairs=repairs,
            destination=preview_path,
        )

        manifest = {
            "schema_version": "1.0",
            "actual_adapter": adapter.adapter_name,
            "repairs": repairs,
            "debug_artifacts": {
                "background_repair_preview": str(preview_path),
            },
            "notes": [
                "Background repair is currently a visible placeholder. Future implementation should inpaint exposed background before style assets are composited."
            ],
        }
        manifest_path = paths.artifact("background_repair_manifest.json")
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
                "repairs_dir": str(repairs_dir),
                "background_repair_preview": str(preview_path),
            },
            notes=[f"Created {len(repairs)} placeholder background repair patches."],
        )
