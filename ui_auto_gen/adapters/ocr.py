from __future__ import annotations

from abc import ABC, abstractmethod
import importlib
import os
from pathlib import Path
import time
from typing import Any

from ui_auto_gen.raster import load_rgba_image, save_png
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
        base_image: Path | None = None,
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
        base_image: Path | None = None,
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


class RapidOcrProtector(OcrProtectAdapter):
    adapter_name = "rapidocr_protector"

    def __init__(self, min_confidence: float | None = None) -> None:
        self.min_confidence = min_confidence if min_confidence is not None else float(
            os.environ.get("DESIGNUI_RAPIDOCR_MIN_CONFIDENCE", "0.45")
        )
        self.model_metadata: dict[str, Any] = {
            "model_family": "rapidocr",
            "engine": "onnxruntime",
            "min_confidence": self.min_confidence,
        }

    def protect_text(
        self,
        detections: list[dict[str, Any]],
        plan_manifest: dict[str, Any],
        regions_dir: Path,
        image_size: tuple[int, int],
        base_image: Path | None = None,
    ) -> list[dict[str, Any]]:
        if base_image is None:
            raise RuntimeError("RapidOCR text protection requires a base image path.")

        rapidocr_module = importlib.import_module("rapidocr")
        engine_cls = getattr(rapidocr_module, "RapidOCR")
        engine = engine_cls()

        regions_dir.mkdir(parents=True, exist_ok=True)
        ocr_input_path = regions_dir / "_rapidocr_input.png"
        save_png(load_rgba_image(base_image, width=image_size[0], height=image_size[1]), ocr_input_path)

        started = time.perf_counter()
        result = engine(str(ocr_input_path))
        self.model_metadata["elapsed_seconds"] = round(time.perf_counter() - started, 3)

        regions: list[dict[str, Any]] = []
        boxes = result.boxes if result.boxes is not None else []
        texts = result.txts if result.txts is not None else []
        scores = result.scores if result.scores is not None else []
        for index, (box, text, score) in enumerate(zip(boxes, texts, scores), start=1):
            confidence = float(score)
            if confidence < self.min_confidence:
                continue
            bbox = _bbox_from_polygon(box, image_size)
            if not bbox:
                continue
            detection = _best_detection(bbox, detections)
            region_id = f"ocr_{index:03d}"
            region_path = regions_dir / f"{region_id}.json"
            payload = {
                "schema_version": "1.0",
                "region_id": region_id,
                "detection_id": detection.get("detection_id") if detection else None,
                "element_id": detection.get("element_id") if detection else None,
                "bbox": bbox,
                "polygon": [[float(point[0]), float(point[1])] for point in box],
                "text": str(text),
                "confidence": confidence,
                "source": self.adapter_name,
                "model": self.model_metadata,
                "placeholder_visual": None,
                "future_adapter": None,
                "note": "Detected by RapidOCR and protected during composition.",
            }
            write_json(region_path, payload)
            regions.append(
                {
                    "region_id": region_id,
                    "detection_id": payload["detection_id"],
                    "element_id": payload["element_id"],
                    "region_path": str(region_path),
                    "bbox": bbox,
                    "polygon": payload["polygon"],
                    "text": payload["text"],
                    "confidence": confidence,
                    "source": self.adapter_name,
                    "model": self.model_metadata,
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


def _bbox_from_polygon(points: Any, image_size: tuple[int, int]) -> list[int] | None:
    image_width, image_height = image_size
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    if not xs or not ys:
        return None
    x1 = max(0, min(image_width - 1, int(min(xs))))
    y1 = max(0, min(image_height - 1, int(min(ys))))
    x2 = max(x1 + 1, min(image_width, int(max(xs)) + 1))
    y2 = max(y1 + 1, min(image_height, int(max(ys)) + 1))
    return [x1, y1, x2, y2]


def _best_detection(bbox: list[int], detections: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for detection in detections:
        score = _intersection_ratio(bbox, detection["bbox"])
        if score > best_score:
            best = detection
            best_score = score
    return best if best_score > 0 else None


def _intersection_ratio(inner: list[int], outer: list[int]) -> float:
    ix1 = max(inner[0], outer[0])
    iy1 = max(inner[1], outer[1])
    ix2 = min(inner[2], outer[2])
    iy2 = min(inner[3], outer[3])
    intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area = max(1, (inner[2] - inner[0]) * (inner[3] - inner[1]))
    return intersection / area
