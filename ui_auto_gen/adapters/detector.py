from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageFilter, ImageStat

from ui_auto_gen.raster import load_rgba_image


class DetectorAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def detect(
        self,
        elements: list[dict[str, Any]],
        width: int,
        height: int,
        manual_regions: list[dict[str, Any]] | None = None,
        base_image: Path | None = None,
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
        base_image: Path | None = None,
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


class LightweightDetector(DetectorAdapter):
    adapter_name = "lightweight_detector"

    def __init__(self, max_dimension: int | None = None, min_area_ratio: float | None = None) -> None:
        self.max_dimension = max_dimension or int(os.environ.get("DESIGNUI_LIGHTWEIGHT_DETECT_MAX_DIM", "720"))
        self.min_area_ratio = min_area_ratio or float(os.environ.get("DESIGNUI_LIGHTWEIGHT_DETECT_MIN_AREA", "0.0025"))
        self.model_metadata = {
            "model_family": "classical_region_proposal",
            "model_size": "tiny",
            "engine": "pillow_connected_components",
            "max_dimension": self.max_dimension,
            "min_area_ratio": self.min_area_ratio,
        }

    def detect(
        self,
        elements: list[dict[str, Any]],
        width: int,
        height: int,
        manual_regions: list[dict[str, Any]] | None = None,
        base_image: Path | None = None,
    ) -> list[dict[str, Any]]:
        if manual_regions:
            return _manual_detections(manual_regions, width, height)
        if base_image is None:
            raise RuntimeError("Lightweight detection requires a base image path.")

        if base_image.suffix.lower() == ".svg":
            proposals = _detect_svg_rectangles(base_image, width, height)
        else:
            image = load_rgba_image(base_image, width, height)
            proposals = _detect_connected_components(
                image=image,
                max_dimension=self.max_dimension,
                min_area_ratio=self.min_area_ratio,
            )
        if not proposals:
            raise RuntimeError("Lightweight detector did not find any candidate regions.")

        max_count = max(len(elements), 1)
        detections = []
        for index, proposal in enumerate(proposals[:max_count], start=1):
            element = elements[index - 1] if index <= len(elements) else {}
            element_id = element.get("element_id") or f"detected_region_{index:03d}"
            detections.append(
                {
                    "detection_id": f"det_{element_id}_{index:03d}",
                    "element_id": element_id,
                    "label": element.get("type_hint", "region"),
                    "bbox": proposal["bbox"],
                    "confidence": proposal["confidence"],
                    "source": self.adapter_name,
                    "model": self.model_metadata,
                    "proposal": {
                        "area_ratio": proposal["area_ratio"],
                        "edge_density": proposal["edge_density"],
                    },
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


def _detect_connected_components(
    image: Image.Image,
    max_dimension: int,
    min_area_ratio: float,
) -> list[dict[str, Any]]:
    original_width, original_height = image.size
    scale = min(1.0, max_dimension / max(original_width, original_height))
    work_size = (max(1, round(original_width * scale)), max(1, round(original_height * scale)))
    work = image.convert("RGBA").resize(work_size, Image.Resampling.BILINEAR)
    rgb = work.convert("RGB")
    gray = work.convert("L")
    alpha = work.getchannel("A")

    bg_color = _estimate_background_color(rgb)
    bg = Image.new("RGB", work_size, bg_color)
    color_delta = ImageChops.difference(rgb, bg).convert("L")
    edge = gray.filter(ImageFilter.FIND_EDGES)
    color_stat = ImageStat.Stat(color_delta)
    edge_stat = ImageStat.Stat(edge)
    alpha_mask = alpha.point(lambda value: 255 if value > 12 else 0, mode="L")
    min_area = max(16, int(work_size[0] * work_size[1] * min_area_ratio))
    boxes: list[tuple[int, int, int, int]] = []
    for color_multiplier, edge_multiplier, grow_size in (
        (1.4, 1.4, 3),
        (1.15, 1.2, 3),
        (0.95, 1.0, 3),
        (0.75, 0.9, 3),
    ):
        color_threshold = max(24, int(color_stat.mean[0] + color_stat.stddev[0] * color_multiplier))
        edge_threshold = max(24, int(edge_stat.mean[0] + edge_stat.stddev[0] * edge_multiplier))
        color_mask = color_delta.point(lambda value, threshold=color_threshold: 255 if value >= threshold else 0, mode="L")
        edge_mask = edge.point(lambda value, threshold=edge_threshold: 255 if value >= threshold else 0, mode="L")
        mask = ImageChops.lighter(color_mask, edge_mask)
        mask = ImageChops.multiply(mask, alpha_mask)
        mask = mask.filter(ImageFilter.MaxFilter(grow_size)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
        attempt_boxes = _component_boxes(mask, min_area=min_area)
        attempt_boxes = _discard_oversized_boxes(attempt_boxes, work_size)
        if attempt_boxes:
            boxes = attempt_boxes
            break

    boxes = _merge_close_boxes(boxes, work_size)
    proposals = []
    for box in boxes:
        x1, y1, x2, y2 = box
        area = max(1, (x2 - x1) * (y2 - y1))
        area_ratio = area / max(1, work_size[0] * work_size[1])
        if area_ratio > 0.92:
            continue
        edge_density = _mask_density(edge_mask, box)
        confidence = max(0.15, min(0.95, 0.35 + area_ratio * 2.0 + edge_density * 0.45))
        proposals.append(
            {
                "bbox": _scale_box(box, 1.0 / scale, (original_width, original_height)),
                "confidence": round(confidence, 4),
                "area_ratio": round(area_ratio, 5),
                "edge_density": round(edge_density, 5),
            }
        )
    proposals.sort(key=lambda item: (item["area_ratio"], item["edge_density"]), reverse=True)
    return proposals


def _detect_svg_rectangles(svg_path: Path, width: int, height: int) -> list[dict[str, Any]]:
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    view_width, view_height = _svg_view_size(root, width, height)
    scale_x = width / max(1.0, view_width)
    scale_y = height / max(1.0, view_height)
    proposals = []
    for element in root.iter():
        if _local_name(element.tag) != "rect":
            continue
        rect_width = _svg_number(element.get("width"), view_width)
        rect_height = _svg_number(element.get("height"), view_height)
        x = _svg_number(element.get("x"), 0.0)
        y = _svg_number(element.get("y"), 0.0)
        if rect_width <= 0 or rect_height <= 0:
            continue
        area_ratio = (rect_width * rect_height) / max(1.0, view_width * view_height)
        if area_ratio > 0.86 or area_ratio < 0.002:
            continue
        bbox = [
            max(0, min(width - 1, round(x * scale_x))),
            max(0, min(height - 1, round(y * scale_y))),
            max(1, min(width, round((x + rect_width) * scale_x))),
            max(1, min(height, round((y + rect_height) * scale_y))),
        ]
        proposals.append(
            {
                "bbox": bbox,
                "confidence": round(max(0.25, min(0.9, 0.45 + area_ratio * 2.0)), 4),
                "area_ratio": round(area_ratio, 5),
                "edge_density": 0.0,
            }
        )
    proposals.sort(key=lambda item: item["area_ratio"], reverse=True)
    return proposals


def _svg_view_size(root: ET.Element, fallback_width: int, fallback_height: int) -> tuple[float, float]:
    view_box = root.get("viewBox")
    if view_box:
        parts = [_svg_number(part, 0.0) for part in view_box.replace(",", " ").split()]
        if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
            return parts[2], parts[3]
    return _svg_number(root.get("width"), fallback_width), _svg_number(root.get("height"), fallback_height)


def _svg_number(value: str | None, default: float) -> float:
    if value is None:
        return float(default)
    text = value.strip().lower().replace("px", "")
    try:
        return float(text)
    except ValueError:
        return float(default)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _estimate_background_color(image: Image.Image) -> tuple[int, int, int]:
    width, height = image.size
    sample_points = []
    step_x = max(1, width // 32)
    step_y = max(1, height // 32)
    for x in range(0, width, step_x):
        sample_points.append((x, 0))
        sample_points.append((x, height - 1))
    for y in range(0, height, step_y):
        sample_points.append((0, y))
        sample_points.append((width - 1, y))
    pixels = [image.getpixel(point) for point in sample_points]
    return tuple(sorted(channel)[len(channel) // 2] for channel in zip(*pixels))


def _component_boxes(mask: Image.Image, min_area: int) -> list[tuple[int, int, int, int]]:
    width, height = mask.size
    pixels = mask.load()
    visited = bytearray(width * height)
    boxes = []
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if visited[index] or pixels[x, y] == 0:
                continue
            stack = [(x, y)]
            visited[index] = 1
            min_x = max_x = x
            min_y = max_y = y
            area = 0
            while stack:
                cx, cy = stack.pop()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    next_index = ny * width + nx
                    if visited[next_index] or pixels[nx, ny] == 0:
                        continue
                    visited[next_index] = 1
                    stack.append((nx, ny))
            if area >= min_area:
                boxes.append((min_x, min_y, max_x + 1, max_y + 1))
    return boxes


def _discard_oversized_boxes(
    boxes: list[tuple[int, int, int, int]],
    image_size: tuple[int, int],
) -> list[tuple[int, int, int, int]]:
    image_area = max(1, image_size[0] * image_size[1])
    filtered = []
    for box in boxes:
        area_ratio = _box_area(box) / image_area
        width_ratio = (box[2] - box[0]) / max(1, image_size[0])
        height_ratio = (box[3] - box[1]) / max(1, image_size[1])
        if area_ratio > 0.92 or (width_ratio > 0.98 and height_ratio > 0.98):
            continue
        filtered.append(box)
    return filtered


def _merge_close_boxes(boxes: list[tuple[int, int, int, int]], image_size: tuple[int, int]) -> list[tuple[int, int, int, int]]:
    if not boxes:
        return []
    gap = max(8, min(image_size) // 80)
    max_union_area = image_size[0] * image_size[1] * 0.72
    merged: list[tuple[int, int, int, int]] = []
    for box in sorted(boxes, key=_box_area, reverse=True):
        target_index = None
        for index, existing in enumerate(merged):
            union = _union_box(existing, box)
            if _expanded_intersects(existing, box, gap) and _box_area(union) <= max_union_area:
                target_index = index
                break
        if target_index is None:
            merged.append(box)
        else:
            merged[target_index] = _union_box(merged[target_index], box)
    return merged


def _expanded_intersects(a: tuple[int, int, int, int], b: tuple[int, int, int, int], gap: int) -> bool:
    return not (a[2] + gap < b[0] or b[2] + gap < a[0] or a[3] + gap < b[1] or b[3] + gap < a[1])


def _union_box(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def _box_area(box: tuple[int, int, int, int]) -> int:
    return max(1, box[2] - box[0]) * max(1, box[3] - box[1])


def _mask_density(mask: Image.Image, box: tuple[int, int, int, int]) -> float:
    crop = mask.crop(box)
    stat = ImageStat.Stat(crop)
    return stat.mean[0] / 255.0


def _scale_box(box: tuple[int, int, int, int], scale: float, image_size: tuple[int, int]) -> list[int]:
    width, height = image_size
    x1, y1, x2, y2 = box
    return [
        max(0, min(width - 1, int(x1 * scale))),
        max(0, min(height - 1, int(y1 * scale))),
        max(1, min(width, int(x2 * scale))),
        max(1, min(height, int(y2 * scale))),
    ]
