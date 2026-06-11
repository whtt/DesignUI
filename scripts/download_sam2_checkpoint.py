from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path


SAM2_CHECKPOINTS = {
    "tiny": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt",
    "small": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_small.pt",
    "base_plus": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt",
    "large": "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a SAM2.1 checkpoint used by DesignUI.")
    parser.add_argument("--size", choices=sorted(SAM2_CHECKPOINTS), default="small")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    output = Path(args.output or f"models/sam2/sam2.1_hiera_{args.size}.pt")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        print(f"Checkpoint already exists: {output}")
        return

    print(f"Downloading SAM2.1 {args.size} checkpoint to {output}")
    urllib.request.urlretrieve(SAM2_CHECKPOINTS[args.size], output)
    print("Done.")


if __name__ == "__main__":
    main()
