from __future__ import annotations

from pathlib import Path

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class ReviewStage(PipelineStage):
    name = "07_review"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")
        style_manifest = read_json(context.run_root / "05_style" / "style_manifest.json")
        compose_manifest = read_json(context.run_root / "06_compose" / "compose_manifest.json")

        issues = []
        checks = []
        expected_count = len(plan_manifest["elements"])
        detection_count = len(detection_manifest["detections"])
        asset_count = len(style_manifest["styled_assets"])
        final_exists = Path(compose_manifest["final_image"]).exists()

        checks.append(_check("element_count_matches_detections", expected_count == detection_count))
        checks.append(_check("element_count_matches_assets", expected_count == asset_count))
        checks.append(_check("final_image_exists", final_exists))

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
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": context.config.get("algorithms", {}).get("review", "contract_review"),
            "actual_adapter": "contract_review",
            "pass": passed,
            "score": score,
            "issues": issues,
            "checks": checks,
        }
        manifest_path = paths.artifact("review_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path)},
            notes=[f"Review pass={passed}, score={score}."],
        )


def _check(name: str, passed: bool) -> dict[str, object]:
    return {
        "name": name,
        "pass": passed,
    }
