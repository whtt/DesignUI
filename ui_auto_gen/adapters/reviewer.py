from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


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

        if not final_exists:
            issues.append(
                {
                    "type": "missing_final_image",
                    "severity": "high",
                    "message": "Compose stage did not produce a final image.",
                }
            )

        placeholder_parts = ["detection", "composition"]
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
                        + " still use placeholder or contract-only behavior."
                    ),
                }
            )

        passed = all(check["pass"] for check in checks)
        score = 0.75 if passed else 0.25
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


def _join_parts(parts: list[str]) -> str:
    if len(parts) <= 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + ", and " + parts[-1]
