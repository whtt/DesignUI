from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def resolve_path(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def probe_image(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower().lstrip(".") or "unknown"
    metadata: dict[str, Any] = {
        "format": suffix,
        "width": None,
        "height": None,
        "bytes": path.stat().st_size if path.exists() else None,
    }

    if suffix == "svg":
        text = path.read_text(encoding="utf-8", errors="ignore")
        width = _find_svg_number(text, "width")
        height = _find_svg_number(text, "height")
        viewbox = re.search(r'viewBox="([^"]+)"', text)
        if (width is None or height is None) and viewbox:
            parts = viewbox.group(1).split()
            if len(parts) == 4:
                width = width or _to_int(parts[2])
                height = height or _to_int(parts[3])
        metadata["width"] = width
        metadata["height"] = height
        return metadata

    with path.open("rb") as handle:
        header = handle.read(32)

    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        metadata["format"] = "png"
        metadata["width"] = int.from_bytes(header[16:20], "big")
        metadata["height"] = int.from_bytes(header[20:24], "big")
        return metadata

    if header.startswith(b"\xff\xd8"):
        size = _probe_jpeg_size(path)
        if size:
            metadata["format"] = "jpg"
            metadata["width"], metadata["height"] = size

    return metadata


def _find_svg_number(text: str, attr: str) -> int | None:
    match = re.search(rf'{attr}="([0-9.]+)', text)
    return _to_int(match.group(1)) if match else None


def _to_int(value: str) -> int | None:
    try:
        return int(float(value))
    except ValueError:
        return None


def _probe_jpeg_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        handle.read(2)
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                return None
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if marker in {b"\xc0", b"\xc1", b"\xc2", b"\xc3"}:
                handle.read(3)
                height = int.from_bytes(handle.read(2), "big")
                width = int.from_bytes(handle.read(2), "big")
                return width, height
            length_bytes = handle.read(2)
            if len(length_bytes) != 2:
                return None
            length = int.from_bytes(length_bytes, "big")
            handle.seek(length - 2, 1)

