from __future__ import annotations

import argparse
from pathlib import Path
import urllib.request


FILES = [
    "icon_detect/model.pt",
    "icon_detect/model.yaml",
    "icon_detect/train_args.yaml",
]

BASE_URL = "https://huggingface.co/microsoft/OmniParser-v2.0/resolve/main"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download OmniParser v2 icon detection weights.")
    parser.add_argument("--output-dir", default="models/omniparser")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for relative_path in FILES:
        destination = output_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            print(f"File already exists: {destination}")
            continue
        url = f"{BASE_URL}/{relative_path}"
        print(f"Downloading {url} -> {destination}")
        urllib.request.urlretrieve(url, destination)
    print("Done.")


if __name__ == "__main__":
    main()
