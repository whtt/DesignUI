from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat

from ui_auto_gen.raster import clamp_bbox, load_rgba_image, placeholder_asset, save_png
from ui_auto_gen.utils import write_json


class BackgroundRepairAdapter(ABC):
    adapter_name: str

    @abstractmethod
    def create_repairs(
        self,
        cutouts: list[dict[str, Any]],
        repairs_dir: Path,
        image_size: tuple[int, int],
        base_image: Path | None = None,
        preserve_layout: bool = True,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError


class PlaceholderBackgroundRepair(BackgroundRepairAdapter):
    adapter_name = "placeholder_background_repair"

    def create_repairs(
        self,
        cutouts: list[dict[str, Any]],
        repairs_dir: Path,
        image_size: tuple[int, int],
        base_image: Path | None = None,
        preserve_layout: bool = True,
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


class LightweightBackgroundRepair(BackgroundRepairAdapter):
    adapter_name = "lightweight_background_repair"

    def __init__(self, blur_radius: int = 14) -> None:
        self.blur_radius = blur_radius
        self.model_metadata = {
            "model_family": "classical_inpaint_approximation",
            "model_size": "tiny",
            "engine": "pillow_ring_fill",
            "blur_radius": blur_radius,
        }

    def create_repairs(
        self,
        cutouts: list[dict[str, Any]],
        repairs_dir: Path,
        image_size: tuple[int, int],
        base_image: Path | None = None,
        preserve_layout: bool = True,
    ) -> list[dict[str, Any]]:
        if base_image is None:
            raise RuntimeError("Lightweight background repair requires a base image path.")
        repairs_dir.mkdir(parents=True, exist_ok=True)
        base = load_rgba_image(base_image, *image_size)
        repairs = []
        for cutout in cutouts:
            repair_id = f"repair_{cutout['cutout_id']}"
            x1, y1, x2, y2 = clamp_bbox(cutout["bbox"], image_size)
            repair_path = repairs_dir / f"{repair_id}.json"
            repair_asset_path = repairs_dir / f"{repair_id}.png"
            repair_asset = _lightweight_patch(base, (x1, y1, x2, y2), self.blur_radius)
            save_png(repair_asset, repair_asset_path)
            payload = {
                "schema_version": "1.0",
                "repair_id": repair_id,
                "cutout_id": cutout["cutout_id"],
                "bbox": [x1, y1, x2, y2],
                "repair_asset_path": str(repair_asset_path),
                "source": self.adapter_name,
                "model": self.model_metadata,
                "placeholder_visual": None,
                "future_adapter": "large_model_background_inpainting",
                "note": "Lightweight local background repair using surrounding color statistics and blur. Future model adapters can replace this with prompt-guided inpainting.",
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
                    "model": self.model_metadata,
                    "placeholder_visual": None,
                    "future_adapter": "large_model_background_inpainting",
                }
            )
        return repairs


def _repair_color(index: int) -> tuple[int, int, int]:
    colors = [(244, 63, 94), (217, 70, 239), (14, 165, 233), (234, 179, 8)]
    return colors[index % len(colors)]


def _lightweight_patch(base: Image.Image, bbox: tuple[int, int, int, int], blur_radius: int) -> Image.Image:
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    pad = max(16, min(96, max(width, height) // 3))
    ex1 = max(0, x1 - pad)
    ey1 = max(0, y1 - pad)
    ex2 = min(base.width, x2 + pad)
    ey2 = min(base.height, y2 + pad)
    expanded = base.crop((ex1, ey1, ex2, ey2)).convert("RGBA")
    local_x1 = x1 - ex1
    local_y1 = y1 - ey1
    local_x2 = local_x1 + width
    local_y2 = local_y1 + height

    mask = Image.new("L", expanded.size, 255)
    mask_draw = Image.new("L", expanded.size, 0)
    mask_draw.paste(255, (local_x1, local_y1, local_x2, local_y2))
    ring_mask = ImageChops.subtract(mask, mask_draw)
    ring_color = _mean_color(expanded, ring_mask)
    filled = Image.new("RGBA", expanded.size, ring_color)
    filled.paste(expanded, (0, 0), ring_mask)
    filled = filled.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    patch = filled.crop((local_x1, local_y1, local_x2, local_y2))
    return patch.filter(ImageFilter.SMOOTH_MORE)


def _mean_color(image: Image.Image, mask: Image.Image) -> tuple[int, int, int, int]:
    stat = ImageStat.Stat(image.convert("RGBA"), mask=mask)
    if not stat.count or stat.count[0] == 0:
        return (248, 250, 252, 255)
    return tuple(max(0, min(255, int(value))) for value in stat.mean[:3]) + (255,)
