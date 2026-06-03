from __future__ import annotations

from ui_auto_gen.adapters import ContractReviewer
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class ReviewStage(PipelineStage):
    name = "07_review"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")
        text_protect_manifest = read_json(context.run_root / "02_ocr_protect" / "text_protect_manifest.json")
        segmentation_manifest = read_json(context.run_root / "03_segment" / "segmentation_manifest.json")
        style_manifest = read_json(context.run_root / "05_style" / "style_manifest.json")
        compose_manifest = read_json(context.run_root / "06_compose" / "compose_manifest.json")

        adapter = ContractReviewer()
        review = adapter.review(
            plan_manifest=plan_manifest,
            detection_manifest=detection_manifest,
            style_manifest=style_manifest,
            compose_manifest=compose_manifest,
            segmentation_manifest=segmentation_manifest,
            text_protect_manifest=text_protect_manifest,
        )
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": context.config.get("algorithms", {}).get("review", "contract_review"),
            "actual_adapter": adapter.adapter_name,
            **review,
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
            notes=[f"Review pass={review['pass']}, score={review['score']}."],
        )
