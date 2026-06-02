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

Recommended local CPU-oriented setup on this Windows machine:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Install SAM2 from GitHub:

```powershell
.\.venv\Scripts\python.exe -m pip install git+https://github.com/facebookresearch/sam2.git
```

If `git clone` times out, download the GitHub zip and install it locally:

```powershell
mkdir external
Invoke-WebRequest -Uri "https://github.com/facebookresearch/sam2/archive/refs/heads/main.zip" -OutFile external\sam2-main.zip
Expand-Archive -LiteralPath external\sam2-main.zip -DestinationPath external -Force
.\.venv\Scripts\python.exe -m pip install -e external\sam2-main
```

Download the tiny checkpoint:

```powershell
.\.venv\Scripts\python.exe scripts\download_sam2_tiny.py
```

On Windows, the SAM2 project recommends WSL with Ubuntu for installation. CPU inference may be slow, but the project will fall back safely if SAM2 cannot run.

### Run The UI With SAM2 Enabled

Use the virtual environment Python, not the global Python:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli serve --port 8765
```

Then choose `SAM2` in the segmentation dropdown.

### Smoke Test

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_sam2_job.json --run-id sam2_tiny_smoke
```

If SAM2 is not installed yet, this command should still complete with `actual_adapter = placeholder_segmenter` and a recorded fallback reason.

## Current Local Deployment

As of the latest local deployment:

- Python runtime: `.venv` created with Python 3.10.
- PyTorch: CPU build installed.
- CUDA: unavailable on this machine.
- SAM2: installed from the GitHub zip under `external/sam2-main`.
- Checkpoint: `models/sam2/sam2.1_hiera_tiny.pt`.
- Verified run: `actual_adapter = sam2_tiny_segmenter`, `device = cpu`, `fallback = null`.
