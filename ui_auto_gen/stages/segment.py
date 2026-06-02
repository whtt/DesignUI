from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters import PlaceholderSegmenter
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_mask_preview


class SegmentStage(PipelineStage):
    name = "03_segment"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        masks_dir = paths.artifact("masks")
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")

        requested_algorithm = context.config.get("algorithms", {}).get("segmenter", "placeholder_segmenter")
        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        adapter = PlaceholderSegmenter()
        masks = adapter.segment(detection_manifest["detections"], masks_dir, (width, height))
        preview_path = paths.artifact("mask_preview.png")
        write_mask_preview(
            base_image=Path(ingest_manifest["base_image"]["run_path"]),
            width=width,
            height=height,
            masks=masks,
            destination=preview_path,
        )
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "masks": masks,
            "debug_artifacts": {
                "mask_preview": str(preview_path),
            },
        }
        manifest_path = paths.artifact("segmentation_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path), "masks_dir": str(masks_dir), "mask_preview": str(preview_path)},
            notes=[f"Created {len(masks)} placeholder mask manifests."],
        )
