from __future__ import annotations

from pathlib import Path

from ui_auto_gen.adapters import PlaceholderSegmenter, Sam2Segmenter
from ui_auto_gen.schemas import PipelineContext, StageResult
from ui_auto_gen.stages.base import PipelineStage
from ui_auto_gen.utils import read_json, write_json
from ui_auto_gen.visual_debug import write_mask_preview


class SegmentStage(PipelineStage):
    name = "03_segment"

    def run(self, context: PipelineContext) -> StageResult:
        paths = context.stage_dir(self.name)
        masks_dir = paths.artifact("masks")
        ingest_manifest = read_json(context.run_root / "00_ingest" / "ingest_manifest.json")
        detection_manifest = read_json(context.run_root / "02_detect" / "detection_manifest.json")

        requested_algorithm = context.config.get("algorithms", {}).get("segmenter", "placeholder_segmenter")
        width = ingest_manifest["base_image"].get("width") or 960
        height = ingest_manifest["base_image"].get("height") or 540
        base_image = Path(ingest_manifest["base_image"]["run_path"])
        adapter, masks, fallback = self._run_adapter(
            requested_algorithm=requested_algorithm,
            detections=detection_manifest["detections"],
            masks_dir=masks_dir,
            image_size=(width, height),
            base_image=base_image,
            repo_root=context.repo_root,
        )
        preview_path = paths.artifact("mask_preview.png")
        write_mask_preview(
            base_image=base_image,
            width=width,
            height=height,
            masks=masks,
            destination=preview_path,
        )
        manifest = {
            "schema_version": "1.0",
            "requested_algorithm": requested_algorithm,
            "actual_adapter": adapter.adapter_name,
            "model": getattr(adapter, "model_metadata", None),
            "fallback": fallback,
            "masks": masks,
            "debug_artifacts": {
                "mask_preview": str(preview_path),
            },
        }
        manifest_path = paths.artifact("segmentation_manifest.json")
        write_json(manifest_path, manifest)

        context.manifest["stages"][self.name] = {
            "status": "completed",
            "manifest": str(manifest_path),
        }

        return StageResult(
            stage=self.name,
            status="completed",
            artifacts={"manifest": str(manifest_path), "masks_dir": str(masks_dir), "mask_preview": str(preview_path)},
            notes=_notes(adapter.adapter_name, len(masks), fallback),
        )

    def _run_adapter(
        self,
        requested_algorithm: str,
        detections: list[dict],
        masks_dir: Path,
        image_size: tuple[int, int],
        base_image: Path,
        repo_root: Path,
    ) -> tuple[object, list[dict], dict | None]:
        if requested_algorithm in {
            "sam2",
            "sam2_small",
            "sam2.1_hiera_small",
            "sam2_tiny",
            "sam2.1_hiera_tiny",
            "sam2_base_plus",
            "sam2_large",
        }:
            try:
                adapter = Sam2Segmenter.from_env(repo_root, requested_size=requested_algorithm)
                masks = adapter.segment(detections, masks_dir, image_size, base_image=base_image)
                return adapter, masks, None
            except Exception as exc:
                fallback_adapter = PlaceholderSegmenter()
                masks = fallback_adapter.segment(detections, masks_dir, image_size, base_image=base_image)
                return fallback_adapter, masks, {
                    "requested_adapter": "sam2_segmenter",
                    "fallback_adapter": fallback_adapter.adapter_name,
                    "reason": str(exc),
                }

        adapter = PlaceholderSegmenter()
        masks = adapter.segment(detections, masks_dir, image_size, base_image=base_image)
        return adapter, masks, None


def _notes(adapter_name: str, mask_count: int, fallback: dict | None) -> list[str]:
    if fallback:
        return [
            f"Requested SAM2 but fell back to {adapter_name}.",
            f"Created {mask_count} fallback placeholder mask manifests.",
            f"Fallback reason: {fallback['reason']}",
        ]
    if adapter_name == "sam2_segmenter":
        return [f"Created {mask_count} SAM2 mask manifests."]
    return [f"Created {mask_count} placeholder mask manifests."]
