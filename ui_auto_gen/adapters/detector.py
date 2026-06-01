from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class DetectorAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def detect(self, elements: list[dict[str, Any]], width: int, height: int) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderDetector(DetectorAdapter):
    adapter_name = "placeholder_detector"

    def detect(self, elements: list[dict[str, Any]], width: int, height: int) -> list[dict[str, Any]]:
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

