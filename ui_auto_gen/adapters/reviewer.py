from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from PIL import Image


class ReviewAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def review(
        self,
        plan_manifest: dict[str, Any],
        detection_manifest: dict[str, Any],
        style_manifest: dict[str, Any],
        compose_manifest: dict[str, Any],
        segmentation_manifest: dict[str, Any] | None = None,
        text_protect_manifest: dict[str, Any] | None = None,
        ingest_manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class ContractReviewer(ReviewAdapter):
    adapter_name = "contract_review"

    def review(
        self,
        plan_manifest: dict[str, Any],
        detection_manifest: dict[str, Any],
        style_manifest: dict[str, Any],
        compose_manifest: dict[str, Any],
        segmentation_manifest: dict[str, Any] | None = None,
        text_protect_manifest: dict[str, Any] | None = None,
        ingest_manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        issues = []
        checks = []
        expected_count = len(plan_manifest["elements"])
        detection_count = len(detection_manifest["detections"])
        asset_count = len(style_manifest["styled_assets"])
        final_exists = Path(compose_manifest["final_image"]).exists()
        checks.append(_check("element_count_matches_detections", expected_count == detection_count))
        checks.append(_check("element_count_matches_assets", expected_count == asset_count))
        checks.append(_check("final_image_exists", final_exists))
        checks.append(_check("text_protection_regions_recorded", "protected_text_regions" in compose_manifest))
        checks.append(_check("background_repair_plan_recorded", "background_repairs" in compose_manifest))

        image_size = _image_size(ingest_manifest)
        if image_size:
            checks.append(_check("final_size_matches_source", _final_size_matches(compose_manifest, image_size)))
            checks.append(_check("placed_assets_within_bounds", _assets_within_bounds(compose_manifest.get("placed_assets", []), image_size)))
            checks.append(_check("background_repairs_within_bounds", _assets_within_bounds(compose_manifest.get("background_repairs", []), image_size)))

        text_regions = (text_protect_manifest or {}).get("text_regions", [])
        protected_text_overlap = _max_overlap_ratio(text_regions, compose_manifest.get("placed_assets", []))
        checks.append(_check("protected_text_restored_after_composition", "protected_text_regions" in compose_manifest))
        if protected_text_overlap > 0.4:
            issues.append(
                {
                    "type": "protected_text_overlap",
                    "severity": "medium",
                    "message": "One or more generated assets overlap protected text regions before text restoration.",
                    "max_overlap_ratio": round(protected_text_overlap, 3),
                }
            )

        repair_area_ratio = _total_area_ratio(compose_manifest.get("background_repairs", []), image_size)
        checks.append(_check("background_repair_area_reasonable", repair_area_ratio <= 0.65))
        if repair_area_ratio > 0.65:
            issues.append(
                {
                    "type": "large_background_repair_area",
                    "severity": "medium",
                    "message": "Background repair covers a large share of the image; detection or mask scope may be too broad.",
                    "area_ratio": round(repair_area_ratio, 3),
                }
            )

        mask_ratios = _mask_area_ratios(segmentation_manifest or {})
        if mask_ratios:
            min_ratio = min(mask_ratios)
            max_ratio = max(mask_ratios)
            checks.append(_check("mask_area_ratio_recorded", True))
            if max_ratio > 0.98 and (segmentation_manifest or {}).get("actual_adapter") != "placeholder_segmenter":
                issues.append(
                    {
                        "type": "mask_matches_full_bbox",
                        "severity": "medium",
                        "message": "A non-placeholder mask fills almost the full bbox; segmentation may be too coarse.",
                        "max_mask_bbox_ratio": round(max_ratio, 3),
                    }
                )
            if min_ratio < 0.01:
                issues.append(
                    {
                        "type": "tiny_mask_area",
                        "severity": "high",
                        "message": "A mask contains almost no foreground pixels.",
                        "min_mask_bbox_ratio": round(min_ratio, 3),
                    }
                )
        else:
            checks.append(_check("mask_area_ratio_recorded", False))

        if not final_exists:
            issues.append(
                {
                    "type": "missing_final_image",
                    "severity": "high",
                    "message": "Compose stage did not produce a final image.",
                }
            )

        placeholder_parts = ["composition"]
        if detection_manifest.get("actual_adapter") == "placeholder_detector":
            placeholder_parts.append("detection")
        if not segmentation_manifest or segmentation_manifest.get("actual_adapter") == "placeholder_segmenter":
            placeholder_parts.append("segmentation")
        if not text_protect_manifest or text_protect_manifest.get("actual_adapter") == "placeholder_ocr_protector":
            placeholder_parts.append("OCR")
        if style_manifest.get("actual_adapter") == "placeholder_style_adapter":
            placeholder_parts.append("style transfer")
        if placeholder_parts:
            issues.append(
                {
                    "type": "placeholder_pipeline",
                    "severity": "info",
                    "message": (
                        "Pipeline contracts passed, but "
                        + _join_parts(placeholder_parts)
                        + _verb_for_parts(placeholder_parts)
                        + " placeholder or contract-only behavior."
                    ),
                }
            )

        for check in checks:
            if not check["pass"]:
                issues.append(
                    {
                        "type": "failed_check",
                        "severity": "medium",
                        "message": f"Review check failed: {check['name']}.",
                    }
                )

        passed = all(check["pass"] for check in checks) and not any(issue.get("severity") == "high" for issue in issues)
        score = _score(checks, issues)
        return {
            "pass": passed,
            "score": score,
            "issues": issues,
            "checks": checks,
        }


def _check(name: str, passed: bool) -> dict[str, object]:
    return {
        "name": name,
        "pass": passed,
    }


def _image_size(ingest_manifest: dict[str, Any] | None) -> tuple[int, int] | None:
    if not ingest_manifest:
        return None
    base_image = ingest_manifest.get("base_image", {})
    width = int(base_image.get("width") or 0)
    height = int(base_image.get("height") or 0)
    if width <= 0 or height <= 0:
        return None
    return width, height


def _final_size_matches(compose_manifest: dict[str, Any], image_size: tuple[int, int]) -> bool:
    path = Path(str(compose_manifest.get("final_image") or ""))
    if not path.exists():
        return False
    try:
        with Image.open(path) as image:
            return image.size == image_size
    except Exception:
        return False


def _assets_within_bounds(assets: list[dict[str, Any]], image_size: tuple[int, int]) -> bool:
    width, height = image_size
    for asset in assets:
        bbox = asset.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            return False
        x1, y1, x2, y2 = [int(value) for value in bbox]
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height or x2 <= x1 or y2 <= y1:
            return False
    return True


def _total_area_ratio(items: list[dict[str, Any]], image_size: tuple[int, int] | None) -> float:
    if not image_size:
        return 0.0
    width, height = image_size
    image_area = max(1, width * height)
    area = 0
    for item in items:
        bbox = item.get("bbox")
        if isinstance(bbox, list) and len(bbox) == 4:
            x1, y1, x2, y2 = [int(value) for value in bbox]
            area += max(0, x2 - x1) * max(0, y2 - y1)
    return area / image_area


def _max_overlap_ratio(regions: list[dict[str, Any]], assets: list[dict[str, Any]]) -> float:
    max_ratio = 0.0
    for region in regions:
        region_bbox = region.get("bbox")
        if not isinstance(region_bbox, list) or len(region_bbox) != 4:
            continue
        region_area = _bbox_area(region_bbox)
        if region_area <= 0:
            continue
        for asset in assets:
            asset_bbox = asset.get("bbox")
            if not isinstance(asset_bbox, list) or len(asset_bbox) != 4:
                continue
            max_ratio = max(max_ratio, _intersection_area(region_bbox, asset_bbox) / region_area)
    return max_ratio


def _bbox_area(bbox: list[int]) -> int:
    x1, y1, x2, y2 = [int(value) for value in bbox]
    return max(0, x2 - x1) * max(0, y2 - y1)


def _intersection_area(a: list[int], b: list[int]) -> int:
    ax1, ay1, ax2, ay2 = [int(value) for value in a]
    bx1, by1, bx2, by2 = [int(value) for value in b]
    return max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))


def _mask_area_ratios(segmentation_manifest: dict[str, Any]) -> list[float]:
    ratios = []
    for mask in segmentation_manifest.get("masks", []):
        bbox = mask.get("bbox")
        mask_path = Path(str(mask.get("mask_png_path") or ""))
        if not isinstance(bbox, list) or len(bbox) != 4 or not mask_path.exists():
            continue
        bbox_area = max(1, _bbox_area(bbox))
        try:
            with Image.open(mask_path) as image:
                alpha = image.convert("L")
                non_zero = sum(1 for value in alpha.getdata() if value)
        except Exception:
            continue
        ratios.append(non_zero / bbox_area)
    return ratios


def _score(checks: list[dict[str, object]], issues: list[dict[str, Any]]) -> float:
    if not checks:
        return 0.0
    passed_ratio = sum(1 for check in checks if check["pass"]) / len(checks)
    high_penalty = 0.25 * sum(1 for issue in issues if issue.get("severity") == "high")
    medium_penalty = 0.08 * sum(1 for issue in issues if issue.get("severity") == "medium")
    return round(max(0.0, min(1.0, passed_ratio - high_penalty - medium_penalty)), 3)


def _join_parts(parts: list[str]) -> str:
    if len(parts) <= 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def _verb_for_parts(parts: list[str]) -> str:
    return " still uses" if len(parts) == 1 else " still use"
