from __future__ import annotations

import argparse
from pathlib import Path
import urllib.request


STYLE_MODELS = {
    "candy": "candy-9.onnx",
    "mosaic": "mosaic-9.onnx",
    "pointilism": "pointilism-9.onnx",
    "rain-princess": "rain-princess-9.onnx",
    "udnie": "udnie-9.onnx",
}

BASE_URL = "https://github.com/onnx/models/raw/main/validated/vision/style_transfer/fast_neural_style/model"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download ONNX Fast Neural Style Transfer models.")
    parser.add_argument("--output-dir", default="models/style_transfer")
    parser.add_argument("--style", choices=sorted(STYLE_MODELS), action="append")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    styles = args.style or sorted(STYLE_MODELS)
    for style in styles:
        filename = STYLE_MODELS[style]
        destination = output_dir / filename
        if destination.exists():
            print(f"File already exists: {destination}")
            continue
        url = f"{BASE_URL}/{filename}"
        print(f"Downloading {url} -> {destination}")
        urllib.request.urlretrieve(url, destination)
    print("Done.")


if __name__ == "__main__":
    main()
