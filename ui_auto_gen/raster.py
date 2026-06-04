from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont


RGBA = tuple[int, int, int, int]


def load_rgba_image(path: Path, width: int | None = None, height: int | None = None) -> Image.Image:
    try:
        with Image.open(path) as image:
            return image.convert("RGBA")
    except Exception:
        fallback_width = width or 960
        fallback_height = height or 540
        image = Image.new("RGBA", (fallback_width, fallback_height), (248, 250, 252, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, fallback_width - 1, fallback_height - 1), outline=(217, 225, 236, 255), width=2)
        draw.text((24, 24), f"Raster fallback for {path.name}", fill=(100, 116, 139, 255), font=_font())
        return image


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def clamp_bbox(bbox: list[int], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = image_size
    x1, y1, x2, y2 = [int(value) for value in bbox]
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(x1 + 1, min(width, x2))
    y2 = max(y1 + 1, min(height, y2))
    return x1, y1, x2, y2


def rectangle_mask(image_size: tuple[int, int], bbox: list[int]) -> Image.Image:
    mask = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle(clamp_bbox(bbox, image_size), fill=255)
    return mask


def cutout_from_mask(base: Image.Image, mask: Image.Image, bbox: list[int]) -> Image.Image:
    base_rgba = base.convert("RGBA")
    masked = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    masked.paste(base_rgba, (0, 0), mask)
    return masked.crop(clamp_bbox(bbox, base_rgba.size))


def placeholder_asset(
    size: tuple[int, int],
    label: str,
    fill: RGBA,
    border: RGBA,
    marker: str | None = None,
    marker_label: str | None = None,
) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = max(6, min(width, height) // 12)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=fill, outline=border, width=2)

    if marker:
        marker_font = _emoji_font(max(18, min(width, height) // 2))
        marker_box = draw.textbbox((0, 0), marker, font=marker_font)
        marker_width = marker_box[2] - marker_box[0]
        marker_height = marker_box[3] - marker_box[1]
        draw.text(
            ((width - marker_width) / 2, max(2, (height - marker_height) / 2 - 8)),
            marker,
            fill=(15, 23, 42, 230),
            font=marker_font,
        )

    if marker_label and height >= 42:
        draw.text((10, 8), marker_label[:34], fill=(15, 23, 42, 235), font=_font())

    text = label[:32]
    draw.text((10, max(8, height - 18)), text, fill=(30, 41, 59, 235), font=_font())
    return image


def draw_bbox_overlay(base: Image.Image, items: list[dict[str, Any]], label_key: str, translucent: bool = False) -> Image.Image:
    return draw_bbox_overlay_with_palette(base, items, label_key, translucent=translucent)


def draw_bbox_overlay_with_palette(
    base: Image.Image,
    items: list[dict[str, Any]],
    label_key: str,
    translucent: bool = False,
    palette: list[tuple[int, int, int]] | None = None,
) -> Image.Image:
    image = base.convert("RGBA").copy()
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for index, item in enumerate(items):
        colors = palette or [_color(index)]
        color = colors[index % len(colors)]
        x1, y1, x2, y2 = clamp_bbox(item["bbox"], image.size)
        fill_alpha = 62 if translucent else 24
        draw.rectangle((x1, y1, x2, y2), fill=(*color, fill_alpha), outline=(*color, 255), width=3)
        label = str(item.get(label_key) or item.get("label") or item.get("mask_id") or item.get("asset_id") or "item")
        label_width = max(96, min(260, len(label) * 7 + 12))
        label_top = max(0, y1 - 22)
        draw.rounded_rectangle((x1, label_top, x1 + label_width, label_top + 20), radius=4, fill=(*color, 255))
        draw.text((x1 + 6, label_top + 3), label[:34], fill=(255, 255, 255, 255), font=_font())
    return Image.alpha_composite(image, overlay)


def paste_assets(base: Image.Image, assets: list[dict[str, Any]]) -> Image.Image:
    image = base.convert("RGBA").copy()
    for asset in assets:
        asset_path = asset.get("generated_asset_path")
        if not asset_path:
            continue
        path = Path(asset_path)
        if not path.exists():
            continue
        overlay = load_rgba_image(path)
        x1, y1, x2, y2 = clamp_bbox(asset["bbox"], image.size)
        overlay = overlay.resize((x2 - x1, y2 - y1))
        overlay = _constrain_overlay_alpha(overlay, asset, (x1, y1, x2, y2), image.size)
        image.alpha_composite(overlay, (x1, y1))
    return image


def _constrain_overlay_alpha(
    overlay: Image.Image,
    asset: dict[str, Any],
    bbox: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> Image.Image:
    mask_path = asset.get("repair_mask_path") or asset.get("mask_png_path")
    if not mask_path:
        return overlay

    path = Path(str(mask_path))
    if not path.exists():
        return overlay

    x1, y1, x2, y2 = bbox
    with Image.open(path) as mask_image:
        mask = mask_image.convert("L")

    if mask.size == image_size:
        mask = mask.crop((x1, y1, x2, y2))
    elif mask.size != overlay.size:
        mask = mask.resize(overlay.size)

    constrained = overlay.convert("RGBA").copy()
    constrained.putalpha(ImageChops.multiply(constrained.getchannel("A"), mask))
    return constrained


def restore_regions(target: Image.Image, source: Image.Image, regions: list[dict[str, Any]]) -> Image.Image:
    image = target.convert("RGBA").copy()
    source_rgba = source.convert("RGBA")
    for region in regions:
        x1, y1, x2, y2 = clamp_bbox(region["bbox"], image.size)
        patch = source_rgba.crop((x1, y1, x2, y2))
        image.alpha_composite(patch, (x1, y1))
    return image


def cutout_contact_sheet(cutouts: list[dict[str, Any]], destination_size: tuple[int, int] = (960, 360)) -> Image.Image:
    width, height = destination_size
    sheet = _checkerboard(destination_size)
    draw = ImageDraw.Draw(sheet)
    if not cutouts:
        draw.text((24, 24), "No cutouts", fill=(100, 116, 139, 255), font=_font())
        return sheet

    gap = 18
    columns = min(4, max(1, len(cutouts)))
    cell_width = (width - (gap * (columns + 1))) // columns
    cell_height = height - (gap * 2)
    for index, cutout in enumerate(cutouts[:columns]):
        path = Path(cutout.get("alpha_asset_path") or "")
        if not path.exists():
            continue
        image = load_rgba_image(path)
        image.thumbnail((cell_width, cell_height - 28))
        x = gap + index * (cell_width + gap)
        y = gap + 18
        sheet.alpha_composite(image, (x + (cell_width - image.width) // 2, y))
        draw.text((x, height - gap - 16), cutout["cutout_id"][:28], fill=(51, 65, 85, 255), font=_font())
    return sheet


def asset_contact_sheet(assets: list[dict[str, Any]], destination_size: tuple[int, int] = (960, 360)) -> Image.Image:
    width, height = destination_size
    sheet = _checkerboard(destination_size)
    draw = ImageDraw.Draw(sheet)
    if not assets:
        draw.text((24, 24), "No styled assets", fill=(100, 116, 139, 255), font=_font())
        return sheet

    gap = 18
    columns = min(4, max(1, len(assets)))
    cell_width = (width - (gap * (columns + 1))) // columns
    cell_height = height - (gap * 2)
    for index, asset in enumerate(assets[:columns]):
        path = Path(asset.get("generated_asset_path") or "")
        if not path.exists():
            continue
        image = load_rgba_image(path)
        image.thumbnail((cell_width, cell_height - 28))
        x = gap + index * (cell_width + gap)
        y = gap + 18
        sheet.alpha_composite(image, (x + (cell_width - image.width) // 2, y))
        draw.text((x, height - gap - 16), asset["asset_id"][:28], fill=(51, 65, 85, 255), font=_font())
    return sheet


def _checkerboard(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    cell = 16
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(241, 245, 249, 255))
    return image


def _color(index: int) -> tuple[int, int, int]:
    colors = [(37, 99, 235), (22, 163, 74), (220, 38, 38), (147, 51, 234), (234, 88, 12), (8, 145, 178)]
    return colors[index % len(colors)]


def _font() -> ImageFont.ImageFont:
    return ImageFont.load_default()


def _emoji_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguiemj.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except OSError:
                continue
    return ImageFont.load_default()
