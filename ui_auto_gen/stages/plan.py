from __future__ import annotations

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import write_json


class PlanStage(PipelineStage):
    name = "01_plan"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        target_elements = context.config.get("target_elements", [])
        if not target_elements:
            raise ValueError("Job config must include at least one target element.")

        preserve_layout = bool(context.config.get("output", {}).get("preserve_layout", True))
        elements = []
        for index, element in enumerate(target_elements, start=1):
            element_id = element.get("id") or f"element_{index:03d}"
            elements.append(
                {
                    "element_id": element_id,
                    "name": element.get("name", element_id),
                    "type_hint": element.get("type_hint", "unknown"),
                    "action": element.get("action", "restyle"),
                    "style": element.get("style", ""),
                    "keep_text": bool(element.get("keep_text", True)),
                    "constraints": {
                        "preserve_layout": preserve_layout,
                    },
                }
            )

        manifest = {
            "schema_version": "1.0",
            "prompt": context.config.get("prompt", ""),
            "positive_rules": context.config.get("positive_rules", ""),
            "negative_rules": context.config.get("negative_rules", ""),
            "reference_image": context.config.get("reference_image"),
            "algorithms": context.config.get("algorithms", {}),
            "elements": elements,
            "global_style": context.config.get("global_style", {}),
        }
        manifest_path = paths.artifact("plan_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path)},
            notes=[f"Normalized {len(elements)} target elements."],
        )
