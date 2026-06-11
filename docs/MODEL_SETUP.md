# Model Setup

This project keeps model integrations optional. The pipeline should still run when model dependencies or checkpoints are missing.

## Lightweight Detection

DesignUI can use a lightweight local detector for the `02_detect` stage when `algorithms.detector` is set to `lightweight_detector`.

Current behavior:

- Manual regions remain authoritative. If the user draws boxes, those boxes become detections.
- For SVG inputs, `LightweightDetector` extracts candidate regions from SVG rectangles.
- For PNG/JPG inputs, it uses Pillow-based background-difference, edge detection, connected components, and simple box merging.
- If no candidates are found or detection fails, `DetectStage` falls back to `PlaceholderDetector`.

This is not a semantic model. It proposes visually salient regions and assigns them to requested elements in order. YOLO, Grounding DINO, Grounded SAM, or VLM region proposal adapters can replace it later behind the same detection contract.

Environment variables:

```powershell
$env:DESIGNUI_LIGHTWEIGHT_DETECT_MAX_DIM="720"
$env:DESIGNUI_LIGHTWEIGHT_DETECT_MIN_AREA="0.0025"
```

### Smoke Test

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_lightweight_detector_job.json --run-id lightweight_detector_smoke
```

Successful runs should record:

```text
actual_adapter = lightweight_detector
fallback = null
```

## OmniParser UI Element Detection

DesignUI can use OmniParser v2 icon detection for the `02_detect` stage when `algorithms.detector` is set to `omniparser`.

Recommended deployment keeps OmniParser isolated from the main DesignUI environment:

```powershell
conda create -n designui_omni python=3.12
conda run -n designui_omni python -m pip install -r requirements-omniparser.txt
python scripts/download_omniparser_weights.py
```

Default settings:

```powershell
$env:DESIGNUI_OMNIPARSER_ENV="designui_omni"
$env:DESIGNUI_OMNIPARSER_MODEL="models/omniparser/icon_detect/model.pt"
$env:DESIGNUI_OMNIPARSER_BOX_THRESHOLD="0.05"
```

The main pipeline calls OmniParser through a subprocess. If OmniParser is unavailable or returns no regions, detection falls back to the lightweight local detector and then to placeholder detection.

### Smoke Test

Use a real PNG/JPG UI screenshot for this smoke test. The existing SVG placeholder sample is not suitable for validating OmniParser because the detector expects raster UI pixels.

```powershell
python -B -m ui_auto_gen.cli run --config path\to\omniparser_ui_job.json --run-id omniparser_smoke --overwrite
```

Successful runs should record:

```text
actual_adapter = omniparser_detector
fallback = null
```

## SAM2 Segmentation

DesignUI can use SAM2.1 for the `03_segment` stage when `algorithms.segmenter` is set to `sam2` or a size-specific value such as `sam2_small`.

Current behavior:

- If `sam2`, `torch`, and the checkpoint are available, `Sam2Segmenter` generates real mask PNG files from detection boxes.
- If anything is missing or initialization fails, `SegmentStage` falls back to `PlaceholderSegmenter`.
- The segmentation manifest records `requested_algorithm`, `actual_adapter`, `model`, and `fallback`.

Default checkpoint path:

```text
models/sam2/sam2.1_hiera_small.pt
```

Environment variables:

```powershell
$env:DESIGNUI_SAM2_CHECKPOINT="D:\models\sam2.1_hiera_small.pt"
$env:DESIGNUI_SAM2_MODEL_CFG="configs/sam2.1/sam2.1_hiera_s.yaml"
$env:DESIGNUI_SAM2_MODEL_SIZE="small"
$env:DESIGNUI_SAM2_DEVICE="auto"
```

`DESIGNUI_SAM2_DEVICE=auto` uses CUDA if available, otherwise CPU.

### Install

SAM2 dependencies are split by device because PyTorch wheels differ by CPU/CUDA target. For CPU:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-cpu.txt
```

For CUDA 12.1 GPU environments:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
```

If the GPU machine needs a different CUDA wheel target, update the PyTorch index URL in `requirements-gpu.txt` before installing.

If `git clone` times out, download the GitHub zip and install it locally:

```powershell
mkdir external
Invoke-WebRequest -Uri "https://github.com/facebookresearch/sam2/archive/refs/heads/main.zip" -OutFile external\sam2-main.zip
Expand-Archive -LiteralPath external\sam2-main.zip -DestinationPath external -Force
.\.venv\Scripts\python.exe -m pip install -e external\sam2-main
```

Download the small checkpoint:

```powershell
.\.venv\Scripts\python.exe scripts\download_sam2_checkpoint.py --size small
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
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_sam2_small_job.json --run-id sam2_small_smoke
```

If SAM2 is not installed yet, this command should still complete with `actual_adapter = placeholder_segmenter` and a recorded fallback reason.

## Current Local Deployment

As of the latest local deployment:

- Python runtime: `.venv` created with Python 3.10.
- PyTorch: CPU build installed.
- CUDA: unavailable on this machine.
- SAM2: installed from GitHub.
- Checkpoint: `models/sam2/sam2.1_hiera_small.pt`.
- Verified run: `actual_adapter = sam2_segmenter`, `model_size = small`, `device = cuda`, `fallback = null`.

## RapidOCR Lightweight OCR

DesignUI can use RapidOCR for the `02_ocr_protect` stage when `algorithms.ocr` is set to `rapidocr`.

Current behavior:

- If `rapidocr` and `onnxruntime` are available, `RapidOcrProtector` runs local CPU OCR and writes detected text boxes, recognized text, confidence, polygon points, and model metadata.
- If RapidOCR is missing or inference fails, `TextProtectStage` falls back to `PlaceholderOcrProtector`.
- The text protection manifest records `requested_algorithm`, `actual_adapter`, `model`, and `fallback`.

### Install

RapidOCR dependencies are included in the device-specific requirement files:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-cpu.txt
# or:
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
```

RapidOCR may download its ONNX model files on first use. In the current local deployment those files live inside `.venv`, which is ignored by Git.

Environment variable:

```powershell
$env:DESIGNUI_RAPIDOCR_MIN_CONFIDENCE="0.45"
```

### Run The UI With RapidOCR Enabled

Use the virtual environment Python:

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli serve --port 8765
```

Then choose `RapidOCR` in the OCR dropdown.

### Smoke Test

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_rapidocr_job.json --run-id rapidocr_smoke
```

If RapidOCR cannot run, this command should still complete with `actual_adapter = placeholder_ocr_protector` and a recorded fallback reason.

## Current RapidOCR Local Deployment

As of the latest local deployment:

- Python runtime: `.venv` created with Python 3.10.
- OCR engine: RapidOCR with ONNX Runtime.
- GPU: not required.
- Verified run: `actual_adapter = rapidocr_protector`, `fallback = null`.
- First-use model files: stored under `.venv` and ignored by Git.

## Lightweight Style Transfer

DesignUI can use a lightweight local style-transfer adapter for the `05_style` stage when `algorithms.style` is set to `lightweight_style_transfer`.

Current behavior:

- `LightweightStyleTransferAdapter` loads each cutout PNG from `04_cutout`.
- If a reference image is provided, it transfers RGB channel statistics from that reference image.
- If no reference image is provided, it uses `global_style.palette` or prompt-derived default palettes.
- It preserves the cutout alpha channel and writes real styled PNG assets.
- If the adapter fails, `StyleStage` falls back to `PlaceholderStyleAdapter`.

This adapter does not require a neural checkpoint, GPU, or external API. It is intentionally small so the pipeline can exercise the style-generation contract before adding ONNX fast neural style transfer, ControlNet, IPAdapter, LoRA, or parameterized UI redraw.

### Smoke Test

```powershell
.\.venv\Scripts\python.exe -B -m ui_auto_gen.cli run --config configs\sample_lightweight_style_job.json --run-id lightweight_style_smoke
```

Successful runs should record:

```text
actual_adapter = lightweight_style_transfer_adapter
model.engine = pillow
fallback = null
```

## Lightweight Background Repair

DesignUI uses `LightweightBackgroundRepair` when `algorithms.background_repair = lightweight_background_repair` and `output.preserve_layout = false`.

Current behavior:

- Uses OpenCV Telea inpainting when `cv2` is available.
- Falls back to the Pillow ring-fill repair when OpenCV is unavailable.
- Uses `DESIGNUI_BACKGROUND_REPAIR_MASK_MODE=auto` by default.
- In `auto` mode, small UI controls are repaired by bbox so translucent buttons/icons are fully removed; larger objects still prefer segmentation masks.

Environment variables:

```powershell
$env:DESIGNUI_BACKGROUND_REPAIR_MASK_MODE="auto"
$env:DESIGNUI_BACKGROUND_REPAIR_BBOX_MAX_AREA="0.12"
```

## LaMa Background Inpainting

DesignUI uses `LamaBackgroundRepair` when `algorithms.background_repair = lama_background_inpaint` and `output.preserve_layout = false`.

Recommended isolated environment:

```bash
conda create -y -n designui_inpaint python=3.11
conda run -n designui_inpaint python -m pip install -r requirements-inpaint.txt
```

Python 3.11 is recommended because `iopaint==1.5.3` pins `Pillow==9.5.0`, which has Linux wheels for Python 3.11. Python 3.12 may try to compile Pillow from source.

Runtime variables:

```bash
export DESIGNUI_INPAINT_ENV=designui_inpaint
export DESIGNUI_INPAINT_DEVICE=cuda
export DESIGNUI_BACKGROUND_REPAIR_MASK_MODE=auto
```

In `auto` mode, LaMa repair first uses the extracted cutout alpha mask (`repair_scope = cutout_alpha`). This keeps image completion limited to the actual UI pixels that were removed. If no cutout alpha is available, it falls back to segmentation or bbox masks.

Smoke test:

```bash
DESIGNUI_INPAINT_ENV=designui_inpaint DESIGNUI_INPAINT_DEVICE=cuda \
python -B -m ui_auto_gen.cli run --config configs/sample_lama_background_job.json --run-id lama_background_smoke --overwrite
```

Successful runs should record `actual_adapter = lama_background_inpaint`, `model.engine = iopaint_lama`, and `fallback = null`.
