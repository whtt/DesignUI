from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageStat

from ui_auto_gen.raster import clamp_bbox, load_rgba_image, placeholder_asset, save_png
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
                marker=_style_marker(len(styled_assets)),
                marker_label="STYLE TODO",
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
                "placeholder_visual": "emoji_style_transfer",
                "future_adapter": "style_transfer_or_parameterized_renderer",
                "note": "Placeholder styled PNG asset with emoji marker. Future implementation should write generated image or vector asset.",
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
                    "placeholder_visual": "emoji_style_transfer",
                    "future_adapter": "style_transfer_or_parameterized_renderer",
                }
            )
        return styled_assets


class LightweightStyleTransferAdapter(StyleAdapter):
    adapter_name = "lightweight_style_transfer_adapter"

    def __init__(self, strength: float = 0.72) -> None:
        self.strength = max(0.0, min(1.0, strength))
        self.model_metadata: dict[str, Any] = {
            "model_family": "classical_color_transfer",
            "model_size": "tiny",
            "engine": "pillow",
            "strength": self.strength,
        }

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
        reference_path = _reference_path(plan_manifest)
        reference_image = load_rgba_image(reference_path) if reference_path and reference_path.exists() else None
        palette = _palette_from_manifest(plan_manifest)
        style_source = str(reference_path) if reference_image else "global_style.palette"
        self.model_metadata["style_source"] = style_source

        styled_assets = []
        for index, cutout in enumerate(cutouts):
            detection_id = cutout["mask_id"].removeprefix("mask_")
            element_id = detection_to_element.get(detection_id, "unknown")
            element = elements_by_id.get(element_id, {})
            asset_id = f"styled_{cutout['cutout_id']}"
            asset_path = assets_dir / f"{asset_id}.json"
            asset_png_path = assets_dir / f"{asset_id}.png"
            source_path = Path(cutout.get("alpha_asset_path") or "")
            cutout_image = load_rgba_image(source_path)
            styled_image = _apply_lightweight_transfer(
                cutout_image=cutout_image,
                reference_image=reference_image,
                palette=palette,
                index=index,
                strength=self.strength,
            )
            save_png(styled_image, asset_png_path)
            payload = {
                "schema_version": "1.0",
                "asset_id": asset_id,
                "cutout_id": cutout["cutout_id"],
                "element_id": element_id,
                "action": element.get("action", "restyle"),
                "requested_style": element.get("style", ""),
                "global_style": plan_manifest.get("global_style", {}),
                "generated_asset_path": str(asset_png_path),
                "source_cutout_path": str(source_path),
                "source": self.adapter_name,
                "model": self.model_metadata,
                "note": "Lightweight local color-statistics style transfer. Future neural style adapters can replace this behind the same contract.",
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
                    "model": self.model_metadata,
                }
            )
        return styled_assets


class OnnxFastNeuralStyleAdapter(StyleAdapter):
    adapter_name = "onnx_fast_neural_style_adapter"

    def __init__(
        self,
        style_preset: str | None = None,
        model_dir: Path | None = None,
        device: str | None = None,
    ) -> None:
        self.style_preset = _safe_style_preset(style_preset or os.environ.get("DESIGNUI_STYLE_PRESET", "mosaic"))
        self.model_dir = model_dir or Path(os.environ.get("DESIGNUI_STYLE_MODEL_DIR", "models/style_transfer"))
        self.model_path = self.model_dir / f"{self.style_preset}-9.onnx"
        self.device = (device or os.environ.get("DESIGNUI_STYLE_DEVICE", "cpu")).lower()
        self.model_metadata: dict[str, Any] = {
            "model_family": "fast_neural_style_transfer",
            "engine": "onnxruntime",
            "style_preset": self.style_preset,
            "model_path": str(self.model_path),
            "device": self.device,
        }

    def create_assets(
        self,
        cutouts: list[dict[str, Any]],
        plan_manifest: dict[str, Any],
        detection_manifest: dict[str, Any],
        assets_dir: Path,
    ) -> list[dict[str, Any]]:
        if not self.model_path.exists():
            raise RuntimeError(
                f"ONNX style model is missing: {self.model_path}. "
                "Run scripts/download_fast_style_models.py first."
            )

        session = self._create_session()
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
            asset_png_path = assets_dir / f"{asset_id}.png"
            source_path = Path(cutout.get("alpha_asset_path") or "")
            cutout_image = load_rgba_image(source_path)
            styled_image = self._stylize_cutout(session, cutout_image)
            save_png(styled_image, asset_png_path)
            payload = {
                "schema_version": "1.0",
                "asset_id": asset_id,
                "cutout_id": cutout["cutout_id"],
                "element_id": element_id,
                "action": element.get("action", "restyle"),
                "requested_style": element.get("style", ""),
                "global_style": plan_manifest.get("global_style", {}),
                "generated_asset_path": str(asset_png_path),
                "source_cutout_path": str(source_path),
                "source": self.adapter_name,
                "model": self.model_metadata,
                "note": "ONNX fast neural style transfer applied with a fixed pretrained style preset.",
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
                    "model": self.model_metadata,
                }
            )
        return styled_assets

    def _create_session(self):
        try:
            import onnxruntime as ort
        except Exception as exc:
            raise RuntimeError("onnxruntime is required for ONNX fast neural style transfer.") from exc

        available = ort.get_available_providers()
        providers = ["CPUExecutionProvider"]
        if self.device == "cuda" and "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        elif self.device in {"auto", "gpu"} and "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self.model_metadata["providers"] = providers
        options = ort.SessionOptions()
        options.log_severity_level = 3
        return ort.InferenceSession(str(self.model_path), sess_options=options, providers=providers)

    def _stylize_cutout(self, session: Any, cutout_image: Image.Image) -> Image.Image:
        import numpy as np

        image = cutout_image.convert("RGBA")
        alpha = image.getchannel("A")
        rgb = Image.new("RGB", image.size, (255, 255, 255))
        rgb.paste(image.convert("RGB"), (0, 0), alpha)
        original_size = rgb.size
        input_image = _resize_for_onnx_style(rgb, session.get_inputs()[0].shape)
        input_array = np.asarray(input_image).astype("float32").transpose(2, 0, 1)[None, :, :, :]
        input_name = session.get_inputs()[0].name
        output = session.run(None, {input_name: input_array})[0][0]
        output = output.transpose(1, 2, 0)
        output = np.clip(output, 0, 255).astype("uint8")
        styled_rgb = Image.fromarray(output, mode="RGB")
        if styled_rgb.size != original_size:
            styled_rgb = styled_rgb.resize(original_size, Image.Resampling.LANCZOS)
        styled = Image.merge("RGBA", (*styled_rgb.split(), alpha))
        return styled


def _style_color(index: int) -> tuple[int, int, int]:
    colors = [(96, 165, 250), (74, 222, 128), (251, 146, 60), (196, 181, 253), (45, 212, 191)]
    return colors[index % len(colors)]


def _style_marker(index: int) -> str:
    markers = ["\U0001f3a8", "\u2728", "\U0001f58c", "\U0001f4a0", "\U0001f9e9"]
    return markers[index % len(markers)]


def _reference_path(plan_manifest: dict[str, Any]) -> Path | None:
    raw_path = plan_manifest.get("reference_image") or plan_manifest.get("global_style", {}).get("reference_image")
    if not raw_path:
        return None
    return Path(raw_path)


def _palette_from_manifest(plan_manifest: dict[str, Any]) -> list[tuple[int, int, int]]:
    raw_palette = plan_manifest.get("global_style", {}).get("palette") or []
    colors = [_parse_hex_color(value) for value in raw_palette if isinstance(value, str)]
    colors = [color for color in colors if color is not None]
    if colors:
        return colors

    text = " ".join(
        [
            str(plan_manifest.get("prompt", "")),
            str(plan_manifest.get("positive_rules", "")),
            str(plan_manifest.get("global_style", {}).get("description", "")),
        ]
    ).lower()
    if "dark" in text or "深色" in text:
        return [(17, 24, 39), (37, 99, 235), (34, 197, 94)]
    if "clay" in text or "3d" in text:
        return [(248, 113, 113), (251, 191, 36), (96, 165, 250)]
    if "glass" in text or "蓝" in text or "blue" in text:
        return [(15, 23, 42), (37, 99, 235), (147, 197, 253)]
    return [(31, 41, 55), (37, 99, 235), (34, 197, 94)]


def _parse_hex_color(value: str) -> tuple[int, int, int] | None:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
    except ValueError:
        return None


def _safe_style_preset(value: str) -> str:
    preset = value.strip().lower().replace("_", "-")
    allowed = {"candy", "mosaic", "pointilism", "rain-princess", "udnie"}
    if preset not in allowed:
        raise RuntimeError(f"Unsupported ONNX style preset: {value}. Expected one of: {', '.join(sorted(allowed))}.")
    return preset


def _resize_for_onnx_style(image: Image.Image, input_shape: list[Any]) -> Image.Image:
    height = _shape_dim(input_shape[2]) if len(input_shape) >= 4 else None
    width = _shape_dim(input_shape[3]) if len(input_shape) >= 4 else None
    if height and width:
        return image.resize((width, height), Image.Resampling.LANCZOS)

    max_dim = int(os.environ.get("DESIGNUI_STYLE_MAX_DIM", "768"))
    if max(image.size) <= max_dim:
        return image
    ratio = max_dim / max(image.size)
    size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _shape_dim(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def _apply_lightweight_transfer(
    cutout_image: Image.Image,
    reference_image: Image.Image | None,
    palette: list[tuple[int, int, int]],
    index: int,
    strength: float,
) -> Image.Image:
    image = cutout_image.convert("RGBA")
    alpha = image.getchannel("A")
    rgb = image.convert("RGB")
    if reference_image is not None:
        styled_rgb = _match_color_statistics(rgb, alpha, reference_image.convert("RGB"), strength)
    else:
        styled_rgb = _tint_to_palette(rgb, alpha, palette[index % len(palette)], strength)

    styled_rgb = ImageEnhance.Color(styled_rgb).enhance(1.08)
    styled_rgb = ImageEnhance.Contrast(styled_rgb).enhance(1.04)
    styled_rgb = styled_rgb.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.SHARPEN)
    styled = Image.merge("RGBA", (*styled_rgb.split(), alpha))
    return styled


def _match_color_statistics(source: Image.Image, alpha: Image.Image, reference: Image.Image, strength: float) -> Image.Image:
    source_stats = ImageStat.Stat(source, mask=alpha)
    reference_stats = ImageStat.Stat(reference)
    source_channels = source.split()
    adjusted_channels = []
    for channel, source_mean, source_std, ref_mean, ref_std in zip(
        source_channels,
        source_stats.mean,
        source_stats.stddev,
        reference_stats.mean,
        reference_stats.stddev,
    ):
        scale = ref_std / max(1.0, source_std)
        lut = []
        for value in range(256):
            transferred = ref_mean + (value - source_mean) * scale
            blended = value * (1.0 - strength) + transferred * strength
            lut.append(max(0, min(255, int(round(blended)))))
        adjusted_channels.append(channel.point(lut))
    return Image.merge("RGB", adjusted_channels)


def _tint_to_palette(source: Image.Image, alpha: Image.Image, target: tuple[int, int, int], strength: float) -> Image.Image:
    source_stats = ImageStat.Stat(source, mask=alpha)
    source_mean = source_stats.mean
    channels = source.split()
    adjusted_channels = []
    for channel, mean, target_value in zip(channels, source_mean, target):
        offset = (target_value - mean) * strength
        lut = [max(0, min(255, int(round(value + offset)))) for value in range(256)]
        adjusted_channels.append(channel.point(lut))
    return Image.merge("RGB", adjusted_channels)
