from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ui_auto_gen.utils import write_json


class OcrProtectAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def protect_text(
        self,
        detections: list[dict[str, Any]],
        plan_manifest: dict[str, Any],
        regions_dir: Path,
        image_size: tuple[int, int],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderOcrProtector(OcrProtectAdapter):
    adapter_name = "placeholder_ocr_protector"

    def protect_text(
        self,
        detections: list[dict[str, Any]],
        plan_manifest: dict[str, Any],
        regions_dir: Path,
        image_size: tuple[int, int],
    ) -> list[dict[str, Any]]:
        regions_dir.mkdir(parents=True, exist_ok=True)
        elements_by_id = {element["element_id"]: element for element in plan_manifest["elements"]}
        regions = []
        for detection in detections:
            element = elements_by_id.get(detection["element_id"], {})
            if not element.get("keep_text", True):
                continue
            text_region = _region_from_bbox(detection["bbox"], image_size)
            if not text_region:
                continue
            region_id = f"text_{detection['detection_id']}_001"
            region_path = regions_dir / f"{region_id}.json"
            payload = {
                "schema_version": "1.0",
                "region_id": region_id,
                "detection_id": detection["detection_id"],
                "element_id": detection["element_id"],
                "bbox": text_region,
                "text": None,
                "confidence": 0.0,
                "placeholder_visual": "ocr_lock_tint",
                "future_adapter": "paddleocr_doctr_or_vlm_ocr",
                "note": "Placeholder text lock. Future OCR should replace this with detected text bounds and text content.",
            }
            write_json(region_path, payload)
            regions.append(
                {
                    "region_id": region_id,
                    "detection_id": detection["detection_id"],
                    "element_id": detection["element_id"],
                    "region_path": str(region_path),
                    "bbox": text_region,
                    "text": None,
                    "confidence": 0.0,
                    "source": self.adapter_name,
                    "placeholder_visual": "ocr_lock_tint",
                    "future_adapter": "paddleocr_doctr_or_vlm_ocr",
                }
            )
        return regions


def _region_from_bbox(bbox: list[int], image_size: tuple[int, int]) -> list[int] | None:
    image_width, image_height = image_size
    x1, y1, x2, y2 = [int(value) for value in bbox]
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    if width < 16 or height < 12:
        return None

    pad_x = max(4, width // 10)
    text_height = max(12, min(28, height // 3))
    text_width = max(16, width - pad_x * 2)
    top = y1 + max(4, min(height // 4, height - text_height - 2))
    left = x1 + pad_x
    return [
        max(0, min(image_width - 1, left)),
        max(0, min(image_height - 1, top)),
        max(1, min(image_width, left + text_width)),
        max(1, min(image_height, top + text_height)),
    ]
