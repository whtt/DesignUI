from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser(description="Run IOPaint LaMa inpainting for a single image/mask pair.")
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    image = Path(payload["image"]).resolve()
    mask = Path(payload["mask"]).resolve()
    output = Path(payload["output"]).resolve()
    device = str(payload.get("device") or "cuda")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        image_dir = root / "image"
        mask_dir = root / "mask"
        output_dir = root / "output"
        image_dir.mkdir()
        mask_dir.mkdir()
        output_dir.mkdir()
        image_copy = image_dir / "input.png"
        mask_copy = mask_dir / "input.png"
        shutil.copy2(image, image_copy)
        shutil.copy2(mask, mask_copy)
        completed = subprocess.run(
            [
                "iopaint",
                "run",
                "--model=lama",
                f"--device={device}",
                f"--image={image_dir}",
                f"--mask={mask_dir}",
                f"--output={output_dir}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"iopaint failed with exit code {completed.returncode}: {detail}")

        candidates = sorted(output_dir.glob("*"))
        if not candidates:
            raise RuntimeError("iopaint did not write any output image.")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidates[0], output)


if __name__ == "__main__":
    main()
