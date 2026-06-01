from __future__ import annotations

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class SegmentStage(PipelineStage):
    name = "03_segment"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        masks_dir = paths.artifact("masks")
        masks_dir.mkdir(parents=True, exist_ok=True)
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")

        masks = []
        for detection in detection_manifest["detections"]:
            mask_id = f"mask_{detection['detection_id']}"
            mask_path = masks_dir / f"{mask_id}.json"
            mask_payload = {
                "schema_version": "1.0",
                "mask_id": mask_id,
                "shape": "rectangle",
                "bbox": detection["bbox"],
                "note": "Placeholder rectangle mask. Replace with raster or polygon mask later.",
            }
            write_json(mask_path, mask_payload)
            masks.append(
                {
                    "mask_id": mask_id,
                    "detection_id": detection["detection_id"],
                    "mask_path": str(mask_path),
                    "bbox": detection["bbox"],
                    "confidence": detection.get("confidence", 0.0),
                    "source": "placeholder_segmenter",
                }
            )

        requested_algorithm = context.config.get("algorithms", {}).get("segmenter", "placeholder_segmenter")
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": "placeholder_segmenter",
            "masks": masks,
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
            artifacts={"manifest": str(manifest_path), "masks_dir": str(masks_dir)},
            notes=[f"Created {len(masks)} placeholder mask manifests."],
        )
