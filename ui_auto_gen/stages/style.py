from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters import PlaceholderStyleAdapter
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json


class StyleStage(PipelineStage):
    name = "05_style"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        assets_dir = paths.artifact("styled_assets")
        cutout_manifest = read_json(context.run_root / "04_cutout" / "cutout_manifest.json")
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")
        text_protect_manifest = _read_optional_manifest(context.run_root / "02_ocr_protect" / "text_protect_manifest.json")

        requested_algorithm = context.config.get("algorithms", {}).get("style", "placeholder_style_adapter")
        adapter = PlaceholderStyleAdapter()
        styled_assets = adapter.create_assets(
            cutouts=cutout_manifest["cutouts"],
            plan_manifest=plan_manifest,
            detection_manifest=detection_manifest,
            assets_dir=assets_dir,
        )
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "styled_assets": styled_assets,
            "protected_text_regions": text_protect_manifest.get("text_regions", []),
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


def _read_optional_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    return read_json(path)
