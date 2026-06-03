from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters.ocr import PlaceholderOcrProtector, RapidOcrProtector
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_text_protect_preview


class TextProtectStage(PipelineStage):
    name = "02_ocr_protect"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        regions_dir = paths.artifact("text_regions")
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        requested_algorithm = context.config.get("algorithms", {}).get("ocr", "placeholder_ocr")
        base_image = Path(ingest_manifest["base_image"]["run_path"])
        adapter, text_regions, fallback = self._run_adapter(
            requested_algorithm=requested_algorithm,
            detections=detection_manifest["detections"],
            plan_manifest=plan_manifest,
            regions_dir=regions_dir,
            image_size=(width, height),
            base_image=base_image,
        )

        preview_path = paths.artifact("text_protect_preview.png")
        write_text_protect_preview(
            base_image=base_image,
            width=width,
            height=height,
            text_regions=text_regions,
            destination=preview_path,
        )

        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "model": getattr(adapter, "model_metadata", None),
            "fallback": fallback,
            "text_regions": text_regions,
            "debug_artifacts": {
                "text_protect_preview": str(preview_path),
            },
        }
        manifest_path = paths.artifact("text_protect_manifest.json")
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
                "text_regions_dir": str(regions_dir),
                "text_protect_preview": str(preview_path),
            },
            notes=_notes(adapter.adapter_name, len(text_regions), fallback),
        )

    def _run_adapter(
        self,
        requested_algorithm: str,
        detections: list[dict],
        plan_manifest: dict,
        regions_dir: Path,
        image_size: tuple[int, int],
        base_image: Path,
    ) -> tuple[object, list[dict], dict | None]:
        if requested_algorithm in {"rapidocr", "rapid_ocr", "rapidocr_onnxruntime"}:
            try:
                adapter = RapidOcrProtector()
                regions = adapter.protect_text(
                    detections=detections,
                    plan_manifest=plan_manifest,
                    regions_dir=regions_dir,
                    image_size=image_size,
                    base_image=base_image,
                )
                return adapter, regions, None
            except Exception as exc:
                fallback_adapter = PlaceholderOcrProtector()
                regions = fallback_adapter.protect_text(
                    detections=detections,
                    plan_manifest=plan_manifest,
                    regions_dir=regions_dir,
                    image_size=image_size,
                    base_image=base_image,
                )
                return fallback_adapter, regions, {
                    "requested_adapter": "rapidocr_protector",
                    "fallback_adapter": fallback_adapter.adapter_name,
                    "reason": str(exc),
                }

        adapter = PlaceholderOcrProtector()
        regions = adapter.protect_text(
            detections=detections,
            plan_manifest=plan_manifest,
            regions_dir=regions_dir,
            image_size=image_size,
            base_image=base_image,
        )
        return adapter, regions, None


def _notes(adapter_name: str, region_count: int, fallback: dict | None) -> list[str]:
    if fallback:
        return [
            f"Requested RapidOCR but fell back to {adapter_name}.",
            f"Created {region_count} fallback placeholder text protection regions.",
            f"Fallback reason: {fallback['reason']}",
        ]
    if adapter_name == "rapidocr_protector":
        return [f"Created {region_count} RapidOCR text protection regions."]
    return [f"Created {region_count} placeholder text protection regions."]
