from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path


SAM2_TINY_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the SAM2.1 tiny checkpoint used by DesignUI.")
    parser.add_argument("--output", default="models/sam2/sam2.1_hiera_tiny.pt")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        print(f"Checkpoint already exists: {output}")
        return

    print(f"Downloading SAM2.1 tiny checkpoint to {output}")
    urllib.request.urlretrieve(SAM2_TINY_URL, output)
    print("Done.")


if __name__ == "__main__":
    main()
