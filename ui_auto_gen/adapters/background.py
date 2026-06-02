from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ui_auto_gen.raster import clamp_bbox, placeholder_asset, save_png
from ui_auto_gen.utils import write_json


class BackgroundRepairAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def create_repairs(
        self,
        cutouts: list[dict[str, Any]],
        repairs_dir: Path,
        image_size: tuple[int, int],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderBackgroundRepair(BackgroundRepairAdapter):
    adapter_name = "placeholder_background_repair"

    def create_repairs(
        self,
        cutouts: list[dict[str, Any]],
        repairs_dir: Path,
        image_size: tuple[int, int],
    ) -> list[dict[str, Any]]:
        repairs_dir.mkdir(parents=True, exist_ok=True)
        repairs = []
        for index, cutout in enumerate(cutouts, start=1):
            repair_id = f"repair_{cutout['cutout_id']}"
            x1, y1, x2, y2 = clamp_bbox(cutout["bbox"], image_size)
            repair_path = repairs_dir / f"{repair_id}.json"
            repair_asset_path = repairs_dir / f"{repair_id}.png"
            color = _repair_color(index - 1)
            repair_asset = placeholder_asset(
                size=(x2 - x1, y2 - y1),
                label=cutout["cutout_id"],
                fill=(*color, 112),
                border=(*color, 255),
                marker="\U0001fa79",
                marker_label="INPAINT TODO",
            )
            save_png(repair_asset, repair_asset_path)
            payload = {
                "schema_version": "1.0",
                "repair_id": repair_id,
                "cutout_id": cutout["cutout_id"],
                "bbox": [x1, y1, x2, y2],
                "repair_asset_path": str(repair_asset_path),
                "placeholder_visual": "inpaint_patch_marker",
                "future_adapter": "background_inpainting",
                "note": "Placeholder background repair patch. Future implementation should inpaint the exposed background under replaced elements.",
            }
            write_json(repair_path, payload)
            repairs.append(
                {
                    "repair_id": repair_id,
                    "cutout_id": cutout["cutout_id"],
                    "repair_path": str(repair_path),
                    "repair_asset_path": str(repair_asset_path),
                    "bbox": [x1, y1, x2, y2],
                    "source": self.adapter_name,
                    "placeholder_visual": "inpaint_patch_marker",
                    "future_adapter": "background_inpainting",
                }
            )
        return repairs


def _repair_color(index: int) -> tuple[int, int, int]:
    colors = [(244, 63, 94), (217, 70, 239), (14, 165, 233), (234, 179, 8)]
    return colors[index % len(colors)]
