from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ui_auto_gen.raster import clamp_bbox, placeholder_asset, save_png
from ui_auto_gen.utils import write_json


class StyleAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def create_assets(
        self,
        cutouts: list[dict[str, Any]],
        plan_manifest: dict[str, Any],
        detection_manifest: dict[str, Any],
        assets_dir: Path,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderStyleAdapter(StyleAdapter):
    adapter_name = "placeholder_style_adapter"

    def create_assets(
        self,
        cutouts: list[dict[str, Any]],
        plan_manifest: dict[str, Any],
        detection_manifest: dict[str, Any],
        assets_dir: Path,
    ) -> list[dict[str, Any]]:
        assets_dir.mkdir(parents=True, exist_ok=True)
        elements_by_id = {element["element_id"]: element for element in plan_manifest["elements"]}
        detection_to_element = {
            detection["detection_id"]: detection["element_id"]
            for detection in detection_manifest["detections"]
        }

        styled_assets = []
        for cutout in cutouts:
            detection_id = cutout["mask_id"].removeprefix("mask_")
            element_id = detection_to_element.get(detection_id, "unknown")
            element = elements_by_id.get(element_id, {})
            asset_id = f"styled_{cutout['cutout_id']}"
            asset_path = assets_dir / f"{asset_id}.json"
            x1, y1, x2, y2 = clamp_bbox(cutout["bbox"], (100000, 100000))
            asset_png_path = assets_dir / f"{asset_id}.png"
            color = _style_color(len(styled_assets))
            asset_png = placeholder_asset(
                size=(x2 - x1, y2 - y1),
                label=element.get("name", element_id),
                fill=(*color, 178),
                border=(*color, 255),
            )
            save_png(asset_png, asset_png_path)
            payload = {
                "schema_version": "1.0",
                "asset_id": asset_id,
                "cutout_id": cutout["cutout_id"],
                "element_id": element_id,
                "action": element.get("action", "restyle"),
                "requested_style": element.get("style", ""),
                "global_style": plan_manifest.get("global_style", {}),
                "generated_asset_path": str(asset_png_path),
                "note": "Placeholder styled PNG asset. Future implementation should write generated image or vector asset.",
            }
            write_json(asset_path, payload)
            styled_assets.append(
                {
                    "asset_id": asset_id,
                    "element_id": element_id,
                    "cutout_id": cutout["cutout_id"],
                    "asset_path": str(asset_path),
                    "generated_asset_path": str(asset_png_path),
                    "bbox": cutout["bbox"],
                    "source": self.adapter_name,
                }
            )
        return styled_assets


def _style_color(index: int) -> tuple[int, int, int]:
    colors = [(96, 165, 250), (74, 222, 128), (251, 146, 60), (196, 181, 253), (45, 212, 191)]
    return colors[index % len(colors)]
