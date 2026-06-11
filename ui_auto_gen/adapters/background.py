from __future__ import annotations

from abc import ABC, abstractmethod
import json
import os
from pathlib import Path
import subprocess
import tempfile
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
                "repair_mask_path": cutout.get("mask_png_path"),
                "repair_scope": "segmentation_mask" if cutout.get("mask_png_path") else "bbox",
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
                    "repair_mask_path": cutout.get("mask_png_path"),
                    "repair_scope": "segmentation_mask" if cutout.get("mask_png_path") else "bbox",
                    "bbox": [x1, y1, x2, y2],
                    "source": self.adapter_name,
                    "placeholder_visual": "inpaint_patch_marker",
                    "future_adapter": "background_inpainting",
                }
            )
        return repairs


class LightweightBackgroundRepair(BackgroundRepairAdapter):
    adapter_name = "lightweight_background_repair"

    def __init__(self, blur_radius: int = 14, mask_mode: str | None = None) -> None:
        self.blur_radius = blur_radius
        self.mask_mode = (mask_mode or os.environ.get("DESIGNUI_BACKGROUND_REPAIR_MASK_MODE", "auto")).lower()
        self.model_metadata = {
            "model_family": "classical_inpaint_approximation",
            "model_size": "tiny",
            "engine": "opencv_telea_or_pillow_ring_fill",
            "blur_radius": blur_radius,
            "mask_mode": self.mask_mode,
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
            use_bbox_mask = _use_bbox_mask(cutout, image_size, self.mask_mode)
            mask_path = None if use_bbox_mask else Path(cutout["mask_png_path"]) if cutout.get("mask_png_path") else None
            repair_asset = _lightweight_patch(
                base,
                (x1, y1, x2, y2),
                self.blur_radius,
                mask_path=mask_path,
                image_size=image_size,
            )
            save_png(repair_asset, repair_asset_path)
            repair_scope = "bbox" if use_bbox_mask or not cutout.get("mask_png_path") else "segmentation_mask"
            repair_mask_path = None if use_bbox_mask else cutout.get("mask_png_path")
            payload = {
                "schema_version": "1.0",
                "repair_id": repair_id,
                "cutout_id": cutout["cutout_id"],
                "bbox": [x1, y1, x2, y2],
                "repair_asset_path": str(repair_asset_path),
                "repair_mask_path": repair_mask_path,
                "repair_scope": repair_scope,
                "source": self.adapter_name,
                "model": self.model_metadata,
                "placeholder_visual": None,
                "future_adapter": "large_model_background_inpainting",
                "note": "Lightweight local background repair using OpenCV Telea inpainting when available, with a Pillow ring-fill fallback. Future model adapters can replace this with prompt-guided inpainting.",
            }
            write_json(repair_path, payload)
            repairs.append(
                {
                    "repair_id": repair_id,
                    "cutout_id": cutout["cutout_id"],
                    "repair_path": str(repair_path),
                    "repair_asset_path": str(repair_asset_path),
                    "repair_mask_path": repair_mask_path,
                    "repair_scope": repair_scope,
                    "bbox": [x1, y1, x2, y2],
                    "source": self.adapter_name,
                    "model": self.model_metadata,
                    "placeholder_visual": None,
                    "future_adapter": "large_model_background_inpainting",
                }
            )
        return repairs


class LamaBackgroundRepair(BackgroundRepairAdapter):
    adapter_name = "lama_background_inpaint"

    def __init__(self, env_name: str | None = None, mask_mode: str | None = None) -> None:
        self.env_name = env_name or os.environ.get("DESIGNUI_INPAINT_ENV", "designui_inpaint")
        self.mask_mode = (mask_mode or os.environ.get("DESIGNUI_BACKGROUND_REPAIR_MASK_MODE", "auto")).lower()
        self.model_metadata = {
            "model_family": "lama",
            "engine": "iopaint_lama",
            "env_name": self.env_name,
            "device": os.environ.get("DESIGNUI_INPAINT_DEVICE", "cuda"),
            "mask_mode": self.mask_mode,
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
            raise RuntimeError("LaMa background repair requires a base image path.")
        repairs_dir.mkdir(parents=True, exist_ok=True)
        repair_regions = [_repair_region(cutout, image_size, self.mask_mode) for cutout in cutouts]
        inpaint_mask = _combined_repair_mask(repair_regions, image_size)
        if not inpaint_mask.getbbox():
            return []

        full_repaired_path = repairs_dir / "lama_background_canvas.png"
        mask_path = repairs_dir / "lama_inpaint_mask.png"
        save_png(inpaint_mask.convert("L"), mask_path)
        self._run_lama(base_image=base_image, mask_path=mask_path, output_path=full_repaired_path)
        repaired = load_rgba_image(full_repaired_path, *image_size)

        repairs = []
        for cutout, region in zip(cutouts, repair_regions, strict=False):
            repair_id = f"repair_{cutout['cutout_id']}"
            x1, y1, x2, y2 = clamp_bbox(cutout["bbox"], image_size)
            repair_path = repairs_dir / f"{repair_id}.json"
            repair_asset_path = repairs_dir / f"{repair_id}.png"
            patch = repaired.crop((x1, y1, x2, y2)).convert("RGBA")
            alpha = region["mask"].crop((x1, y1, x2, y2))
            patch.putalpha(alpha)
            save_png(patch, repair_asset_path)
            payload = {
                "schema_version": "1.0",
                "repair_id": repair_id,
                "cutout_id": cutout["cutout_id"],
                "bbox": [x1, y1, x2, y2],
                "repair_asset_path": str(repair_asset_path),
                "repair_mask_path": str(mask_path),
                "repair_scope": region["scope"],
                "source": self.adapter_name,
                "model": self.model_metadata,
                "placeholder_visual": None,
                "future_adapter": None,
                "note": "LaMa background repair generated through IOPaint in an isolated subprocess environment.",
            }
            write_json(repair_path, payload)
            repairs.append(
                {
                    "repair_id": repair_id,
                    "cutout_id": cutout["cutout_id"],
                    "repair_path": str(repair_path),
                    "repair_asset_path": str(repair_asset_path),
                    "repair_mask_path": str(mask_path),
                    "repair_scope": region["scope"],
                    "bbox": [x1, y1, x2, y2],
                    "source": self.adapter_name,
                    "model": self.model_metadata,
                    "placeholder_visual": None,
                    "future_adapter": None,
                }
            )
        return repairs

    def _run_lama(self, base_image: Path, mask_path: Path, output_path: Path) -> None:
        runner = Path(__file__).resolve().parents[2] / "scripts" / "run_lama_inpaint.py"
        payload = {
            "image": str(base_image),
            "mask": str(mask_path),
            "output": str(output_path),
            "device": self.model_metadata["device"],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(payload, handle)
            payload_path = Path(handle.name)
        try:
            command = _inpaint_python_command(self.env_name)
            completed = subprocess.run(
                [*command, str(runner), "--payload", str(payload_path)],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path(__file__).resolve().parents[2],
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "").strip()
                raise RuntimeError(f"LaMa inpaint runner failed with exit code {completed.returncode}: {detail}")
            if not output_path.exists():
                raise RuntimeError(f"LaMa inpaint runner did not write output: {output_path}")
        finally:
            payload_path.unlink(missing_ok=True)


def _repair_color(index: int) -> tuple[int, int, int]:
    colors = [(244, 63, 94), (217, 70, 239), (14, 165, 233), (234, 179, 8)]
    return colors[index % len(colors)]


def _lightweight_patch(
    base: Image.Image,
    bbox: tuple[int, int, int, int],
    blur_radius: int,
    mask_path: Path | None = None,
    image_size: tuple[int, int] | None = None,
) -> Image.Image:
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
    local_bbox = (local_x1, local_y1, local_x2, local_y2)
    if mask_path is None:
        expanded_mask = Image.new("L", expanded.size, 0)
        expanded_draw = Image.new("L", expanded.size, 0)
        expanded_draw.paste(255, local_bbox)
        expanded_mask = expanded_draw
    else:
        expanded_mask = _mask_for_region(
            mask_path=mask_path,
            region=(ex1, ey1, ex2, ey2),
            region_size=expanded.size,
            image_size=image_size or base.size,
        )
    target_mask = expanded_mask.crop(local_bbox)

    opencv_patch = _opencv_inpaint_patch(expanded, expanded_mask, local_bbox, target_mask)
    if opencv_patch is not None:
        return opencv_patch

    full_mask = Image.new("L", expanded.size, 255)
    ring_mask = ImageChops.subtract(full_mask, expanded_mask)
    ring_color = _mean_color(expanded, ring_mask)
    filled = Image.new("RGBA", expanded.size, ring_color)
    filled.paste(expanded, (0, 0), ring_mask)
    filled = filled.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    patch = filled.crop(local_bbox).filter(ImageFilter.SMOOTH_MORE).convert("RGBA")
    patch.putalpha(target_mask)
    return patch


def _use_bbox_mask(cutout: dict[str, Any], image_size: tuple[int, int], mask_mode: str) -> bool:
    if mask_mode == "bbox":
        return True
    if mask_mode in {"segmentation", "segmentation_mask", "mask"}:
        return False
    bbox = cutout.get("bbox") or [0, 0, image_size[0], image_size[1]]
    x1, y1, x2, y2 = clamp_bbox(bbox, image_size)
    area_ratio = ((x2 - x1) * (y2 - y1)) / max(1, image_size[0] * image_size[1])
    return area_ratio <= float(os.environ.get("DESIGNUI_BACKGROUND_REPAIR_BBOX_MAX_AREA", "0.12"))


def _repair_region(cutout: dict[str, Any], image_size: tuple[int, int], mask_mode: str) -> dict[str, Any]:
    x1, y1, x2, y2 = clamp_bbox(cutout.get("bbox") or [0, 0, image_size[0], image_size[1]], image_size)
    use_bbox_mask = _use_bbox_mask(cutout, image_size, mask_mode)
    if use_bbox_mask or not cutout.get("mask_png_path"):
        mask = Image.new("L", image_size, 0)
        mask.paste(255, (x1, y1, x2, y2))
        return {"scope": "bbox", "mask": _dilate_mask(mask)}

    mask_path = Path(cutout["mask_png_path"])
    mask = _mask_for_region(mask_path, (0, 0, image_size[0], image_size[1]), image_size, image_size)
    return {"scope": "segmentation_mask", "mask": _dilate_mask(mask)}


def _combined_repair_mask(regions: list[dict[str, Any]], image_size: tuple[int, int]) -> Image.Image:
    combined = Image.new("L", image_size, 0)
    for region in regions:
        combined = ImageChops.lighter(combined, region["mask"])
    return combined


def _dilate_mask(mask: Image.Image) -> Image.Image:
    grow = int(os.environ.get("DESIGNUI_BACKGROUND_REPAIR_MASK_GROW", "17"))
    grow = max(3, grow if grow % 2 == 1 else grow + 1)
    return mask.convert("L").filter(ImageFilter.MaxFilter(grow)).point(lambda value: 255 if value > 8 else 0, mode="L")


def _inpaint_python_command(env_name: str) -> list[str]:
    python_path = os.environ.get("DESIGNUI_INPAINT_PYTHON")
    if python_path:
        return [python_path]
    conda_executable = os.environ.get("DESIGNUI_CONDA", "conda")
    return [conda_executable, "run", "-n", env_name, "python"]


def _opencv_inpaint_patch(
    expanded: Image.Image,
    expanded_mask: Image.Image,
    local_bbox: tuple[int, int, int, int],
    target_mask: Image.Image,
) -> Image.Image | None:
    try:
        import cv2
        import numpy as np
    except Exception:
        return None

    inpaint_mask = expanded_mask.filter(ImageFilter.MaxFilter(9)).point(lambda value: 255 if value > 8 else 0, mode="L")
    if not inpaint_mask.getbbox():
        return None

    rgb = expanded.convert("RGB")
    rgb_array = np.array(rgb)
    mask_array = np.array(inpaint_mask)
    try:
        repaired = cv2.inpaint(rgb_array, mask_array, 5, cv2.INPAINT_TELEA)
    except Exception:
        return None

    patch = Image.fromarray(repaired).convert("RGBA").crop(local_bbox).filter(ImageFilter.SMOOTH_MORE)
    patch.putalpha(target_mask)
    return patch


def _mask_for_region(
    mask_path: Path | None,
    region: tuple[int, int, int, int],
    region_size: tuple[int, int],
    image_size: tuple[int, int],
) -> Image.Image:
    if not mask_path or not mask_path.exists():
        return Image.new("L", region_size, 255)

    with Image.open(mask_path) as mask_image:
        mask = mask_image.convert("L")

    rx1, ry1, rx2, ry2 = region
    if mask.size == image_size:
        return mask.crop(region)

    bbox_width = max(1, rx2 - rx1)
    bbox_height = max(1, ry2 - ry1)
    if mask.size == (bbox_width, bbox_height):
        return mask.resize(region_size)

    return mask.resize(image_size).crop(region)


def _mean_color(image: Image.Image, mask: Image.Image) -> tuple[int, int, int, int]:
    stat = ImageStat.Stat(image.convert("RGBA"), mask=mask)
    if not stat.count or stat.count[0] == 0:
        return (248, 250, 252, 255)
    return tuple(max(0, min(255, int(value))) for value in stat.mean[:3]) + (255,)
