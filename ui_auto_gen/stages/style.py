from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters import LightweightStyleTransferAdapter, OnnxFastNeuralStyleAdapter, PlaceholderStyleAdapter
from ui_auto_gen.raster import asset_contact_sheet, save_png
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
        style_preset = context.config.get("algorithms", {}).get("style_preset")
        adapter, styled_assets, fallback = self._run_adapter(
            requested_algorithm=requested_algorithm,
            style_preset=style_preset,
            cutouts=cutout_manifest["cutouts"],
            plan_manifest=plan_manifest,
            detection_manifest=detection_manifest,
            assets_dir=assets_dir,
        )
        preview_path = paths.artifact("style_preview.png")
        save_png(asset_contact_sheet(styled_assets), preview_path)
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "model": getattr(adapter, "model_metadata", None),
            "fallback": fallback,
            "styled_assets": styled_assets,
            "protected_text_regions": text_protect_manifest.get("text_regions", []),
            "debug_artifacts": {
                "style_preview": str(preview_path),
            },
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
            artifacts={"manifest": str(manifest_path), "assets_dir": str(assets_dir), "style_preview": str(preview_path)},
            notes=_notes(adapter.adapter_name, len(styled_assets), fallback),
        )

    def _run_adapter(
        self,
        requested_algorithm: str,
        style_preset: str | None,
        cutouts: list[dict],
        plan_manifest: dict,
        detection_manifest: dict,
        assets_dir: Path,
    ) -> tuple[object, list[dict], dict | None]:
        if requested_algorithm in {"onnx_fast_neural_style", "fast_neural_style", "onnx_style_transfer"}:
            try:
                adapter = OnnxFastNeuralStyleAdapter(style_preset=style_preset)
                assets = adapter.create_assets(
                    cutouts=cutouts,
                    plan_manifest=plan_manifest,
                    detection_manifest=detection_manifest,
                    assets_dir=assets_dir,
                )
                return adapter, assets, None
            except Exception as exc:
                fallback_adapter = LightweightStyleTransferAdapter()
                try:
                    assets = fallback_adapter.create_assets(
                        cutouts=cutouts,
                        plan_manifest=plan_manifest,
                        detection_manifest=detection_manifest,
                        assets_dir=assets_dir,
                    )
                    return fallback_adapter, assets, {
                        "requested_adapter": "onnx_fast_neural_style_adapter",
                        "fallback_adapter": fallback_adapter.adapter_name,
                        "reason": str(exc),
                    }
                except Exception as fallback_exc:
                    placeholder_adapter = PlaceholderStyleAdapter()
                    assets = placeholder_adapter.create_assets(
                        cutouts=cutouts,
                        plan_manifest=plan_manifest,
                        detection_manifest=detection_manifest,
                        assets_dir=assets_dir,
                    )
                    return placeholder_adapter, assets, {
                        "requested_adapter": "onnx_fast_neural_style_adapter",
                        "fallback_adapter": placeholder_adapter.adapter_name,
                        "reason": f"{exc}; lightweight fallback failed: {fallback_exc}",
                    }

        if requested_algorithm in {"lightweight_style_transfer", "palette_transfer", "color_statistics_transfer"}:
            try:
                adapter = LightweightStyleTransferAdapter()
                assets = adapter.create_assets(
                    cutouts=cutouts,
                    plan_manifest=plan_manifest,
                    detection_manifest=detection_manifest,
                    assets_dir=assets_dir,
                )
                return adapter, assets, None
            except Exception as exc:
                fallback_adapter = PlaceholderStyleAdapter()
                assets = fallback_adapter.create_assets(
                    cutouts=cutouts,
                    plan_manifest=plan_manifest,
                    detection_manifest=detection_manifest,
                    assets_dir=assets_dir,
                )
                return fallback_adapter, assets, {
                    "requested_adapter": "lightweight_style_transfer_adapter",
                    "fallback_adapter": fallback_adapter.adapter_name,
                    "reason": str(exc),
                }

        adapter = PlaceholderStyleAdapter()
        assets = adapter.create_assets(
            cutouts=cutouts,
            plan_manifest=plan_manifest,
            detection_manifest=detection_manifest,
            assets_dir=assets_dir,
        )
        return adapter, assets, None


def _read_optional_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    return read_json(path)


def _notes(adapter_name: str, asset_count: int, fallback: dict | None) -> list[str]:
    if fallback:
        return [
            f"Requested style transfer but fell back to {adapter_name}.",
            f"Created {asset_count} fallback styled asset records.",
            f"Fallback reason: {fallback['reason']}",
        ]
    if adapter_name == "onnx_fast_neural_style_adapter":
        return [f"Created {asset_count} ONNX fast neural style-transfer assets."]
    if adapter_name == "lightweight_style_transfer_adapter":
        return [f"Created {asset_count} lightweight style-transfer assets."]
    return [f"Created {asset_count} placeholder styled asset records."]
