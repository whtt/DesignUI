from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters import LightweightDetector, PlaceholderDetector
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_detection_preview


class DetectStage(PipelineStage):
    name = "02_detect"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        plan_manifest = read_json(context.run_root / "01_plan" / "plan_manifest.json")

        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        base_image = Path(ingest_manifest["base_image"]["run_path"])
        requested_algorithm = context.config.get("algorithms", {}).get("detector", "placeholder_detector")
        manual_regions = context.config.get("manual_regions", [])
        adapter, detections, fallback = self._run_adapter(
            requested_algorithm=requested_algorithm,
            elements=plan_manifest["elements"],
            width=width,
            height=height,
            manual_regions=manual_regions,
            base_image=base_image,
        )
        preview_path = paths.artifact("detection_preview.png")
        write_detection_preview(
            base_image=base_image,
            width=width,
            height=height,
            detections=detections,
            destination=preview_path,
        )
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "manual_regions_used": bool(manual_regions),
            "model": getattr(adapter, "model_metadata", None),
            "fallback": fallback,
            "detections": detections,
            "debug_artifacts": {
                "detection_preview": str(preview_path),
            },
            "notes": _manifest_notes(adapter.adapter_name, bool(manual_regions), fallback),
        }
        manifest_path = paths.artifact("detection_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path), "detection_preview": str(preview_path)},
            notes=_result_notes(adapter.adapter_name, len(detections), bool(manual_regions), fallback),
        )

    def _run_adapter(
        self,
        requested_algorithm: str,
        elements: list[dict],
        width: int,
        height: int,
        manual_regions: list[dict],
        base_image: Path,
    ) -> tuple[object, list[dict], dict | None]:
        if requested_algorithm in {"lightweight_detector", "lightweight_region_detector", "connected_components"}:
            try:
                adapter = LightweightDetector()
                detections = adapter.detect(
                    elements=elements,
                    width=width,
                    height=height,
                    manual_regions=manual_regions,
                    base_image=base_image,
                )
                return adapter, detections, None
            except Exception as exc:
                fallback_adapter = PlaceholderDetector()
                detections = fallback_adapter.detect(
                    elements=elements,
                    width=width,
                    height=height,
                    manual_regions=manual_regions,
                    base_image=base_image,
                )
                return fallback_adapter, detections, {
                    "requested_adapter": "lightweight_detector",
                    "fallback_adapter": fallback_adapter.adapter_name,
                    "reason": str(exc),
                }

        adapter = PlaceholderDetector()
        detections = adapter.detect(
            elements=elements,
            width=width,
            height=height,
            manual_regions=manual_regions,
            base_image=base_image,
        )
        return adapter, detections, None


def _manifest_notes(adapter_name: str, manual_regions_used: bool, fallback: dict | None) -> list[str]:
    if fallback:
        return [
            f"Requested lightweight detector but fell back to {adapter_name}.",
            f"Fallback reason: {fallback['reason']}",
        ]
    if manual_regions_used:
        return ["Manual regions were used as authoritative detections."]
    if adapter_name == "lightweight_detector":
        return ["Lightweight detector generated local connected-component region proposals."]
    return ["Placeholder detector created deterministic boxes. Replace this adapter with YOLO/Grounded-SAM later."]


def _result_notes(adapter_name: str, detection_count: int, manual_regions_used: bool, fallback: dict | None) -> list[str]:
    if fallback:
        return [
            f"Created {detection_count} fallback detections with {adapter_name}.",
            f"Fallback reason: {fallback['reason']}",
        ]
    if manual_regions_used:
        return [f"Created {detection_count} detections from manual regions."]
    if adapter_name == "lightweight_detector":
        return [f"Created {detection_count} lightweight region detections."]
    return [f"Created {detection_count} placeholder detections."]
