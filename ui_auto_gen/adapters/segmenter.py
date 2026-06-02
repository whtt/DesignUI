from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ui_auto_gen.raster import rectangle_mask, save_png
from ui_auto_gen.utils import write_json


class SegmenterAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def segment(
        self,
        detections: list[dict[str, Any]],
        masks_dir: Path,
        image_size: tuple[int, int],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderSegmenter(SegmenterAdapter):
    adapter_name = "placeholder_segmenter"

    def segment(
        self,
        detections: list[dict[str, Any]],
        masks_dir: Path,
        image_size: tuple[int, int],
    ) -> list[dict[str, Any]]:
        masks_dir.mkdir(parents=True, exist_ok=True)
        masks = []
        for detection in detections:
            mask_id = f"mask_{detection['detection_id']}"
            mask_path = masks_dir / f"{mask_id}.json"
            mask_png_path = masks_dir / f"{mask_id}.png"
            save_png(rectangle_mask(image_size, detection["bbox"]), mask_png_path)
            mask_payload = {
                "schema_version": "1.0",
                "mask_id": mask_id,
                "shape": "rectangle",
                "bbox": detection["bbox"],
                "mask_png_path": str(mask_png_path),
                "placeholder_visual": "colored_rectangle_mask",
                "future_adapter": "sam_or_instance_segmentation",
                "note": "Placeholder rectangle mask. UI previews tint this area to show where future instance segmentation masks will appear.",
            }
            write_json(mask_path, mask_payload)
            masks.append(
                {
                    "mask_id": mask_id,
                    "detection_id": detection["detection_id"],
                    "mask_path": str(mask_path),
                    "mask_png_path": str(mask_png_path),
                    "bbox": detection["bbox"],
                    "confidence": detection.get("confidence", 0.0),
                    "source": self.adapter_name,
                    "placeholder_visual": "colored_rectangle_mask",
                    "future_adapter": "sam_or_instance_segmentation",
                }
            )
        return masks
