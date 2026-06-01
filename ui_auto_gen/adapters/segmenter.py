from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ui_auto_gen.utils import write_json


class SegmenterAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def segment(self, detections: list[dict[str, Any]], masks_dir: Path) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderSegmenter(SegmenterAdapter):
    adapter_name = "placeholder_segmenter"

    def segment(self, detections: list[dict[str, Any]], masks_dir: Path) -> list[dict[str, Any]]:
        masks_dir.mkdir(parents=True, exist_ok=True)
        masks = []
        for detection in detections:
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
                    "source": self.adapter_name,
                }
            )
        return masks

