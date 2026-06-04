from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters.background import LightweightBackgroundRepair, PlaceholderBackgroundRepair
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_background_repair_preview


class BackgroundRepairStage(PipelineStage):
    name = "04_background_repair"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        repairs_dir = paths.artifact("repairs")
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        cutout_manifest = read_json(context.run_root / "04_cutout" / "cutout_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        base_image = Path(ingest_manifest["base_image"]["run_path"])
        preserve_layout = bool(context.config.get("output", {}).get("preserve_layout", True))
        requested_algorithm = context.config.get("algorithms", {}).get("background_repair", "lightweight_background_repair")
        adapter, repairs, fallback = self._run_adapter(
            requested_algorithm=requested_algorithm,
            preserve_layout=preserve_layout,
            cutouts=cutout_manifest["cutouts"],
            repairs_dir=repairs_dir,
            image_size=(width, height),
            base_image=base_image,
        )

        preview_path = paths.artifact("background_repair_preview.png")
        write_background_repair_preview(
            base_image=base_image,
            width=width,
            height=height,
            repairs=repairs,
            destination=preview_path,
        )

        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "model": getattr(adapter, "model_metadata", None),
            "fallback": fallback,
            "preserve_layout": preserve_layout,
            "skipped": preserve_layout,
            "repairs": repairs,
            "debug_artifacts": {
                "background_repair_preview": str(preview_path),
            },
            "notes": _manifest_notes(adapter.adapter_name, preserve_layout, fallback),
        }
        manifest_path = paths.artifact("background_repair_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={
                "manifest": str(manifest_path),
                "repairs_dir": str(repairs_dir),
                "background_repair_preview": str(preview_path),
            },
            notes=_result_notes(adapter.adapter_name, len(repairs), preserve_layout, fallback),
        )

    def _run_adapter(
        self,
        requested_algorithm: str,
        preserve_layout: bool,
        cutouts: list[dict],
        repairs_dir: Path,
        image_size: tuple[int, int],
        base_image: Path,
    ) -> tuple[object, list[dict], dict | None]:
        if preserve_layout:
            return _SkippedBackgroundRepair(), [], None

        if requested_algorithm in {"lightweight_background_repair", "lightweight_inpaint", "pillow_inpaint"}:
            try:
                adapter = LightweightBackgroundRepair()
                repairs = adapter.create_repairs(
                    cutouts=cutouts,
                    repairs_dir=repairs_dir,
                    image_size=image_size,
                    base_image=base_image,
                    preserve_layout=preserve_layout,
                )
                return adapter, repairs, None
            except Exception as exc:
                fallback_adapter = PlaceholderBackgroundRepair()
                repairs = fallback_adapter.create_repairs(
                    cutouts=cutouts,
                    repairs_dir=repairs_dir,
                    image_size=image_size,
                    base_image=base_image,
                    preserve_layout=preserve_layout,
                )
                return fallback_adapter, repairs, {
                    "requested_adapter": "lightweight_background_repair",
                    "fallback_adapter": fallback_adapter.adapter_name,
                    "reason": str(exc),
                }

        adapter = PlaceholderBackgroundRepair()
        repairs = adapter.create_repairs(
            cutouts=cutouts,
            repairs_dir=repairs_dir,
            image_size=image_size,
            base_image=base_image,
            preserve_layout=preserve_layout,
        )
        return adapter, repairs, None


class _SkippedBackgroundRepair:
    adapter_name = "skipped_background_repair"
    model_metadata = None


def _manifest_notes(adapter_name: str, preserve_layout: bool, fallback: dict | None) -> list[str]:
    if preserve_layout:
        return ["Background repair skipped because preserve_layout is enabled."]
    if fallback:
        return [
            f"Requested lightweight background repair but fell back to {adapter_name}.",
            f"Fallback reason: {fallback['reason']}",
        ]
    if adapter_name == "lightweight_background_repair":
        return ["Lightweight local background repair created real repair patches for moved elements."]
    return ["Placeholder background repair patches created for future inpainting replacement."]


def _result_notes(adapter_name: str, repair_count: int, preserve_layout: bool, fallback: dict | None) -> list[str]:
    if preserve_layout:
        return ["Skipped background repair because layout is preserved."]
    if fallback:
        return [
            f"Created {repair_count} fallback placeholder background repair patches.",
            f"Fallback reason: {fallback['reason']}",
        ]
    if adapter_name == "lightweight_background_repair":
        return [f"Created {repair_count} lightweight background repair patches."]
    return [f"Created {repair_count} placeholder background repair patches."]
