from __future__ import annotations

import base64
import html
import mimetypes
from pathlib import Path
from typing import Any


COLORS = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]


def write_detection_preview(
    base_image: Path,
    width: int,
    height: int,
    detections: list[dict[str, Any]],
    destination: Path,
) -> None:
    overlays = []
    for index, detection in enumerate(detections):
        color = COLORS[index % len(COLORS)]
        label = f"{detection.get('label', 'element')} {detection.get('confidence', 0):.2f}"
        overlays.append(_rect_overlay(detection["bbox"], color, label))
    _write_overlay_svg(base_image, width, height, overlays, destination)


def write_mask_preview(
    base_image: Path,
    width: int,
    height: int,
    masks: list[dict[str, Any]],
    destination: Path,
) -> None:
    overlays = []
    for index, mask in enumerate(masks):
        color = COLORS[index % len(COLORS)]
        overlays.append(_rect_overlay(mask["bbox"], color, mask["mask_id"], fill_opacity="0.22"))
    _write_overlay_svg(base_image, width, height, overlays, destination)


def write_composition_preview(
    base_image: Path,
    width: int,
    height: int,
    placed_assets: list[dict[str, Any]],
    destination: Path,
) -> None:
    overlays = []
    for index, asset in enumerate(placed_assets):
        color = COLORS[index % len(COLORS)]
        overlays.append(_rect_overlay(asset["bbox"], color, asset["asset_id"], stroke_dasharray="8 5"))
    _write_overlay_svg(base_image, width, height, overlays, destination)


def _write_overlay_svg(base_image: Path, width: int, height: int, overlays: list[str], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image_href = _data_uri(base_image)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#f8fafc"/>
  <image href="{image_href}" x="0" y="0" width="{width}" height="{height}" preserveAspectRatio="none"/>
  {chr(10).join(overlays)}
</svg>
"""
    destination.write_text(svg, encoding="utf-8")


def _rect_overlay(
    bbox: list[int],
    color: str,
    label: str,
    fill_opacity: str = "0.08",
    stroke_dasharray: str | None = None,
) -> str:
    x1, y1, x2, y2 = bbox
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    safe_label = html.escape(label)
    dash = f' stroke-dasharray="{stroke_dasharray}"' if stroke_dasharray else ""
    label_y = max(18, y1 - 7)
    return f"""<g>
    <rect x="{x1}" y="{y1}" width="{width}" height="{height}" fill="{color}" fill-opacity="{fill_opacity}" stroke="{color}" stroke-width="3"{dash}/>
    <rect x="{x1}" y="{label_y - 16}" width="{max(96, len(safe_label) * 8)}" height="20" rx="4" fill="{color}"/>
    <text x="{x1 + 6}" y="{label_y - 2}" font-family="Arial, sans-serif" font-size="12" fill="#ffffff">{safe_label}</text>
  </g>"""


def _data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"

