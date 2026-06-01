from __future__ import annotations

from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class StyleStage(PipelineStage):
    name = "05_style"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        assets_dir = paths.artifact("styled_assets")
        assets_dir.mkdir(parents=True, exist_ok=True)
        cutout_manifest = read_json(context.run_root / "04_cutout" / "cutout_manifest.json")
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")

        elements_by_id = {element["element_id"]: element for element in plan_manifest["elements"]}
        detection_to_element = {
            detection["detection_id"]: detection["element_id"]
            for detection in detection_manifest["detections"]
        }

        styled_assets = []
        for cutout in cutout_manifest["cutouts"]:
            detection_id = cutout["mask_id"].removeprefix("mask_")
            element_id = detection_to_element.get(detection_id, "unknown")
            element = elements_by_id.get(element_id, {})
            asset_id = f"styled_{cutout['cutout_id']}"
            asset_path = assets_dir / f"{asset_id}.json"
            payload = {
                "schema_version": "1.0",
                "asset_id": asset_id,
                "cutout_id": cutout["cutout_id"],
                "element_id": element_id,
                "action": element.get("action", "restyle"),
                "requested_style": element.get("style", ""),
                "global_style": plan_manifest.get("global_style", {}),
                "generated_asset_path": None,
                "note": "Placeholder styled asset. Future implementation should write generated image or vector asset.",
            }
            write_json(asset_path, payload)
            styled_assets.append(
                {
                    "asset_id": asset_id,
                    "element_id": element_id,
                    "cutout_id": cutout["cutout_id"],
                    "asset_path": str(asset_path),
                    "bbox": cutout["bbox"],
                    "source": "placeholder_style_adapter",
                }
            )

        requested_algorithm = context.config.get("algorithms", {}).get("style", "placeholder_style_adapter")
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": "placeholder_style_adapter",
            "styled_assets": styled_assets,
        }
        manifest_path = paths.artifact("style_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path), "assets_dir": str(assets_dir)},
            notes=[f"Created {len(styled_assets)} placeholder styled asset records."],
        )
