from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ui_auto_gen.raster import load_rgba_image, save_png  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OmniParser icon detection and emit DesignUI proposals.")
    parser.add_argument("--image", required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--elements-json", required=True)
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--box-threshold", type=float, default=0.05)
    parser.add_argument("--max-regions", type=int, default=24)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    started = time.perf_counter()
    image_path = Path(args.image)
    model_path = Path(args.model_path)
    with Path(args.elements_json).open("r", encoding="utf-8") as handle:
        elements = json.load(handle)

    inference_image, temporary_path = _prepare_image(image_path, args.width, args.height)
    try:
        proposals, model_info = _detect_regions(
            image_path=inference_image,
            model_path=model_path,
            box_threshold=args.box_threshold,
            max_regions=max(args.max_regions, len(elements)),
            image_size=(args.width, args.height),
        )
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)

    payload = {
        "schema_version": "1.0",
        "model": {
            "model_family": "omniparser",
            "version": "v2",
            "engine": "ultralytics_icon_detect",
            "model_path": str(model_path),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            **model_info,
        },
        "proposals": proposals,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_image(path: Path, width: int, height: int) -> tuple[Path, Path | None]:
    try:
        with Image.open(path) as image:
            image.verify()
        return path, None
    except Exception:
        image = load_rgba_image(path, width=width, height=height).convert("RGB")
        temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_path = Path(temp.name)
        temp.close()
        save_png(image.convert("RGBA"), temp_path)
        return temp_path, temp_path


def _detect_regions(
    image_path: Path,
    model_path: Path,
    box_threshold: float,
    max_regions: int,
    image_size: tuple[int, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    results = model.predict(source=str(image_path), conf=box_threshold, verbose=False)
    if not results:
        return [], {"class_names": {}}

    result = results[0]
    names = getattr(result, "names", None) or getattr(model, "names", {}) or {}
    proposals: list[dict[str, Any]] = []
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return [], {"class_names": names}

    for index, box in enumerate(boxes):
        xyxy = box.xyxy[0].tolist()
        confidence = float(box.conf[0].item()) if box.conf is not None else 0.0
        class_id = int(box.cls[0].item()) if box.cls is not None else -1
        label = str(names.get(class_id, f"class_{class_id}")) if isinstance(names, dict) else f"class_{class_id}"
        bbox = _clamp_bbox([int(round(value)) for value in xyxy], image_size)
        if _too_small(bbox, image_size):
            continue
        proposals.append(
            {
                "proposal_id": f"omniparser_{index + 1:03d}",
                "bbox": bbox,
                "confidence": round(confidence, 4),
                "label": label,
                "class_id": class_id,
            }
        )

    proposals.sort(key=lambda item: (-item["confidence"], item["bbox"][1], item["bbox"][0]))
    return proposals[:max_regions], {"class_names": names}


def _clamp_bbox(bbox: list[int], image_size: tuple[int, int]) -> list[int]:
    width, height = image_size
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(x1 + 1, min(width, x2))
    y2 = max(y1 + 1, min(height, y2))
    return [x1, y1, x2, y2]


def _too_small(bbox: list[int], image_size: tuple[int, int]) -> bool:
    width, height = image_size
    area = max(1, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
    return area / max(1, width * height) < 0.0002


if __name__ == "__main__":
    main()
