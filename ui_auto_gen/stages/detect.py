from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters import PlaceholderDetector
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_detection_preview


class DetectStage(PipelineStage):
    name = "02_detect"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        requested_algorithm = context.config.get("algorithms", {}).get("detector", "placeholder_detector")
        adapter = PlaceholderDetector()
        detections = adapter.detect(plan_manifest["elements"], width, height)
        preview_path = paths.artifact("detection_preview.png")
        write_detection_preview(
            base_image=Path(ingest_manifest["base_image"]["run_path"]),
            width=width,
            height=height,
            detections=detections,
            destination=preview_path,
        )
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "detections": detections,
            "debug_artifacts": {
                "detection_preview": str(preview_path),
            },
            "notes": [
                "Placeholder detector created deterministic boxes. Replace this adapter with YOLO/Grounded-SAM later."
            ],
        }
        manifest_path = paths.artifact("detection_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path), "detection_preview": str(preview_path)},
            notes=[f"Created {len(detections)} placeholder detections."],
        )
