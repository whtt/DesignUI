from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters.ocr import PlaceholderOcrProtector
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_text_protect_preview


class TextProtectStage(PipelineStage):
    name = "02_ocr_protect"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        regions_dir = paths.artifact("text_regions")
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        requested_algorithm = context.config.get("algorithms", {}).get("ocr", "placeholder_ocr")
        adapter = PlaceholderOcrProtector()
        text_regions = adapter.protect_text(
            detections=detection_manifest["detections"],
            plan_manifest=plan_manifest,
            regions_dir=regions_dir,
            image_size=(width, height),
        )

        preview_path = paths.artifact("text_protect_preview.png")
        write_text_protect_preview(
            base_image=Path(ingest_manifest["base_image"]["run_path"]),
            width=width,
            height=height,
            text_regions=text_regions,
            destination=preview_path,
        )

        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "text_regions": text_regions,
            "debug_artifacts": {
                "text_protect_preview": str(preview_path),
            },
        }
        manifest_path = paths.artifact("text_protect_manifest.json")
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
                "text_regions_dir": str(regions_dir),
                "text_protect_preview": str(preview_path),
            },
            notes=[f"Created {len(text_regions)} placeholder text protection regions."],
        )
