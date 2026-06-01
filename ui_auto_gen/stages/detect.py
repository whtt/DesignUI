from __future__ import annotations

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class DetectStage(PipelineStage):
    name = "02_detect"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        elements = plan_manifest["elements"]
        detections = []

        for index, element in enumerate(elements, start=1):
            bbox = _placeholder_bbox(index, len(elements), width, height)
            detections.append(
                {
                    "detection_id": f"det_{element['element_id']}_001",
                    "element_id": element["element_id"],
                    "label": element.get("type_hint", "unknown"),
                    "bbox": bbox,
                    "confidence": 0.5,
                    "source": "placeholder_detector",
                }
            )

        requested_algorithm = context.config.get("algorithms", {}).get("detector", "placeholder_detector")
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": "placeholder_detector",
            "detections": detections,
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
            artifacts={"manifest": str(manifest_path)},
            notes=[f"Created {len(detections)} placeholder detections."],
        )


def _placeholder_bbox(index: int, total: int, width: int, height: int) -> list[int]:
    margin_x = max(24, width // 16)
    margin_y = max(24, height // 12)
    box_width = max(80, width // 5)
    box_height = max(48, height // 8)
    usable_height = max(1, height - (2 * margin_y) - box_height)
    step = usable_height // max(1, total - 1) if total > 1 else 0
    x1 = margin_x
    y1 = margin_y + ((index - 1) * step)
    x2 = min(width, x1 + box_width)
    y2 = min(height, y1 + box_height)
    return [x1, y1, x2, y2]
