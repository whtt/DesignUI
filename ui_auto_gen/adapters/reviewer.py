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

        issues.append(
            {
                "type": "placeholder_pipeline",
                "severity": "info",
                "message": "Pipeline contracts passed, but detection, segmentation, style transfer, and composition are placeholders.",
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
