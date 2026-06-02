from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DetectorAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def detect(
        self,
        elements: list[dict[str, Any]],
        width: int,
        height: int,
        manual_regions: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderDetector(DetectorAdapter):
    adapter_name = "placeholder_detector"

    def detect(
        self,
        elements: list[dict[str, Any]],
        width: int,
        height: int,
        manual_regions: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        if manual_regions:
            return _manual_detections(manual_regions, width, height)

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
                    "source": self.adapter_name,
                }
            )
        return detections


def _manual_detections(manual_regions: list[dict[str, Any]], width: int, height: int) -> list[dict[str, Any]]:
    detections = []
    for index, region in enumerate(manual_regions, start=1):
        region_id = region.get("id") or f"manual_{index:03d}"
        bbox = _manual_bbox(region, width, height)
        detections.append(
            {
                "detection_id": f"det_{region_id}_001",
                "element_id": region_id,
                "label": region.get("type_hint") or "manual",
                "bbox": bbox,
                "confidence": 1.0,
                "source": "manual_selection",
                "manual_region_id": region_id,
            }
        )
    return detections


def _manual_bbox(region: dict[str, Any], width: int, height: int) -> list[int]:
    bbox_norm = region.get("bbox_norm")
    if bbox_norm and len(bbox_norm) == 4:
        raw_x1, raw_y1, raw_x2, raw_y2 = [float(value) for value in bbox_norm]
        x1, x2 = sorted([raw_x1, raw_x2])
        y1, y2 = sorted([raw_y1, raw_y2])
        return [
            max(0, min(width - 1, round(x1 * width))),
            max(0, min(height - 1, round(y1 * height))),
            max(1, min(width, round(x2 * width))),
            max(1, min(height, round(y2 * height))),
        ]

    bbox = region.get("bbox") or [0, 0, width, height]
    x1, y1, x2, y2 = [int(value) for value in bbox]
    return [
        max(0, min(width - 1, x1)),
        max(0, min(height - 1, y1)),
        max(1, min(width, x2)),
        max(1, min(height, y2)),
    ]


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
