# Model Setup

This project keeps model integrations optional. The pipeline should still run when model dependencies or checkpoints are missing.

## SAM2 Tiny Segmentation

DesignUI can use SAM2.1 tiny for the `03_segment` stage when `algorithms.segmenter` is set to `sam2`.

Current behavior:

- If `sam2`, `torch`, and the checkpoint are available, `Sam2TinySegmenter` generates real mask PNG files from detection boxes.
- If anything is missing or initialization fails, `SegmentStage` falls back to `PlaceholderSegmenter`.
- The segmentation manifest records `requested_algorithm`, `actual_adapter`, `model`, and `fallback`.

Default checkpoint path:

```text
models/sam2/sam2.1_hiera_tiny.pt
```

Environment variables:

```powershell
$env:DESIGNUI_SAM2_CHECKPOINT="D:\models\sam2.1_hiera_tiny.pt"
$env:DESIGNUI_SAM2_MODEL_CFG="configs/sam2.1/sam2.1_hiera_t.yaml"
$env:DESIGNUI_SAM2_DEVICE="auto"
```

`DESIGNUI_SAM2_DEVICE=auto` uses CUDA if available, otherwise CPU.

### Install

SAM2 is not included in `requirements.txt` because PyTorch install commands differ by machine.

Typical CPU-oriented setup:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install git+https://github.com/facebookresearch/sam2.git
python scripts/download_sam2_tiny.py
```

On Windows, the SAM2 project recommends WSL with Ubuntu for installation. CPU inference may be slow, but the project will fall back safely if SAM2 cannot run.

### Smoke Test

```powershell
python -B -m ui_auto_gen.cli run --config configs\sample_sam2_job.json --run-id sam2_tiny_smoke
```

If SAM2 is not installed yet, this command should still complete with `actual_adapter = placeholder_segmenter` and a recorded fallback reason.
