# DesignUI / 自动化 UI 图生成流程

[中文](#中文) | [English](#english)

## 中文

DesignUI 是一个用于自动化 UI 图生成的最小工程框架。它的目标是把“底图 + 提示词 + 正反规则 + 参考图 + 算法选择”转换成一个可迭代的文件化 pipeline，后续可以逐步接入 YOLO、SAM、OCR、VLM、风格迁移和自审模型。

当前版本不依赖外部 API。每个步骤都通过独立目录和 JSON manifest 交接；部分轻量本地 adapter 已经可选接入，后续也可以继续替换成更强的真实算法，而不需要重写整个流程。

### 当前已具备

- 本地 Web UI。
- 命令行 pipeline。
- job config 生成与管理。
- 底图导入。
- 元素计划生成。
- 检测、分割、抠图、风格替换、合成、自审、导出的占位流程。
- 检测框、mask、合成意图的可视化调试预览。
- OCR 文字保护预览和背景修复预览。
- 本地 UI 中的 stage 产物链接和运行详情。
- PNG/JPG raster 处理基础：mask PNG、cutout PNG、placeholder asset PNG、基础 alpha 合成。
- 合成阶段会从原图恢复文字保护区域，减少占位生成物覆盖文字。
- 手动矩形圈选：用户可以在底图预览上框选元素，检测阶段优先使用这些区域。
- 可选轻量检测 adapter：`检测算法 = 轻量检测器` 会基于 SVG 结构或 PNG/JPG 边缘/背景差异生成本地区域提议，缺失时自动回退占位检测。
- 可选 SAM2.1 分割 adapter：安装模型依赖和 checkpoint 后可生成真实 mask，缺失时自动回退占位分割。
- 可选 RapidOCR 轻量 OCR adapter：安装 RapidOCR 和 ONNX Runtime 后，`OCR = RapidOCR` 会生成真实文字框和文字内容，缺失时自动回退占位 OCR。
- 可选轻量风格迁移 adapter：`Style = 轻量风格迁移` 会基于参考图或调色板对 cutout PNG 做本地色彩统计迁移，缺失时自动回退占位风格器。
- 可选轻量背景修复 adapter：不保持原布局时会对原元素区域生成本地背景补丁，优先使用 OpenCV Telea inpainting，保持原布局时自动跳过背景修复。
- 不保持原布局时的手动合成编辑器：可在右侧拖动 styled asset，调整前后顺序，并重新生成最终图。
- 本地 UI 左侧底部的 run 历史记录和缓存清除入口，支持单条缓存清除和全量清除。
- Run 详情视图：按阶段展示 manifest、预览图、关键计数、自审结果和 before/after 对比。
- 单阶段重跑：支持从指定 stage 重新执行必要依赖链，例如重跑背景修复后自动重跑合成、自审和导出。
- 轻量自审规则：检查最终图尺寸、素材越界、背景修复范围、mask 面积比例和文字保护覆盖风险。
- 单个生成素材展示与保存：抠图素材和风格素材可分组查看、单独打开，并复制保存到 `workspace/saved_outputs/`，避免清理 `runs/` 时丢失。
- 每一步独立产物目录。
- 运行摘要 `run_summary.json`。
- 工程文档、需求文档、数据契约和实现状态说明。

### 运行本地 UI

安装依赖：

```powershell
pip install -r requirements.txt
```

如果要启用可选的模型 adapter，请按设备安装对应依赖：

```powershell
pip install -r requirements-cpu.txt
# 或 CUDA 12.1 环境：
pip install -r requirements-gpu.txt
```

```powershell
python -B -m ui_auto_gen.cli serve --port 8765
```

然后打开：

```text
http://127.0.0.1:8765
```

在界面中可以填写：

- 提示词
- 正向规则
- 反向规则
- 需要处理的元素
- 底图来源
- 参考图
- 检测/分割/OCR/风格替换/自审算法选择

注意：轻量检测、SAM2、RapidOCR 和轻量风格迁移已经可以按需执行；其他算法选项会被记录到 job config 和 stage manifest 中，等待后续接入。

### 运行最小 pipeline

```powershell
python -B -m ui_auto_gen.cli run --config configs/sample_job.json
```

默认运行产物写入：

```text
runs/
```

也可以指定输出目录：

```powershell
python -B -m ui_auto_gen.cli run --config configs/sample_job.json --output-root C:\tmp\ui_runs
```

### 重要文件

- `docs/PRD.md`：需求和 MVP 范围。
- `docs/PROJECT_GUIDE.md`：后续对话和新贡献者的渐进式项目导航。
- `docs/WORKFLOW.md`：端到端流程。
- `docs/ARCHITECTURE.md`：架构和模块边界。
- `docs/DATA_CONTRACTS.md`：各步骤 JSON 数据契约。
- `docs/IMPLEMENTATION_STATUS.md`：已完成项和待完成项。
- `docs/NEXT_GOAL_DEBUG_UI.md`：当前可视化调试迭代目标。
- `docs/FEATURE_REQUIREMENTS.md`：公开功能需求说明。
- `docs/MODEL_SETUP.md`：可选模型安装和 checkpoint 配置说明。
- `docs/ROADMAP.md`：后续路线图。
- `configs/sample_job.json`：可运行示例配置。
- `configs/sample_lightweight_detector_job.json`：请求轻量检测、SAM2、RapidOCR 和轻量风格迁移的示例配置。
- `configs/sample_sam2_job.json`：请求 SAM2 分割的示例配置，缺模型时会 fallback。
- `configs/sample_rapidocr_job.json`：请求 RapidOCR 文字保护的示例配置，缺依赖时会 fallback。
- `configs/sample_lightweight_style_job.json`：请求轻量风格迁移的示例配置。
- `configs/sample_onnx_style_job.json`：请求 ONNX 小模型预训练风格迁移的示例配置。
- `configs/sample_lightweight_background_job.json`：请求轻量背景修复并关闭保持原布局的示例配置。
- `configs/sample_lama_background_job.json`：请求 LaMa/IOPaint 图像补全背景修复的示例配置。
- `ui_auto_gen/stages/`：独立 pipeline stage。
- `ui_auto_gen/web/`：本地 Web UI 和 API 服务。
- `skills/designui-automation/`：面向 Codex/agent 的渐进式自动化流程 skill。

### 当前限制

- 尚未接入语义目标检测或大模型风格生成。
- 已接入可选轻量检测、SAM2.1 分割、RapidOCR 轻量 OCR、轻量本地风格迁移、ONNX 小模型风格迁移和 LaMa/IOPaint 背景补全；其他 UI 选项如 `YOLO26`、`ControlNet + IPAdapter` 当前仍只是记录选择。
- 最终图目前通常是底图或文生图占位 SVG。
- 真实模型能力会在后续迭代中逐步接入。

## English

DesignUI is a minimal engineering framework for automated UI image generation. Its goal is to turn a base image, prompt, positive/negative rules, reference image, and algorithm selections into an iterative file-based pipeline that can later integrate YOLO, SAM, OCR, VLM, style-transfer, and self-review models.

The current version does not depend on external APIs. Each step exchanges artifacts through its own directory and JSON manifest; several lightweight local adapters are already optional, and stronger real algorithms can be added later without rewriting the whole pipeline.

### What Works Now

- Local Web UI.
- Command-line pipeline.
- Job config generation and management.
- Base image ingestion.
- Structured element planning.
- Placeholder detection, segmentation, cutout, style, composition, review, and export stages.
- Visual debug previews for detection boxes, masks, and composition intent.
- OCR text-protection previews and background-repair placeholder previews.
- Per-stage artifact links and run details in the local UI.
- PNG/JPG raster foundation: mask PNG, cutout PNG, placeholder asset PNG, and basic alpha compositing.
- Composition restores protected text regions from the source image so placeholders do not cover text.
- Manual rectangle selection: users can box-select elements on the base preview, and detection prioritizes those regions.
- Optional lightweight detector: `Detector = Lightweight Detector` generates local region proposals from SVG structure or PNG/JPG edge/background differences, otherwise it falls back to placeholder detection.
- Optional OmniParser detector: `Detector = OmniParser UI Element Detection` parses UI screenshots into candidate element regions through an isolated Python 3.12 subprocess environment.
- Optional SAM2.1 segmentation adapter: generates real masks when dependencies and checkpoint are available, otherwise falls back to placeholder segmentation.
- Optional RapidOCR lightweight OCR adapter: when RapidOCR and ONNX Runtime are installed, `OCR = RapidOCR` generates real text boxes and recognized text, otherwise it falls back to placeholder OCR.
- Optional lightweight style-transfer adapter: `Style = Lightweight Style Transfer` applies local color-statistics transfer from a reference image or palette to cutout PNG assets, otherwise it falls back to placeholder styling.
- Optional lightweight background-repair adapter: when layout preservation is disabled, it creates local background patches for original element regions, preferring OpenCV Telea inpainting when available; when layout is preserved, background repair is skipped.
- Manual composition editor when layout preservation is disabled: users can drag styled assets, adjust front/back order, and recompose the final image.
- Run history and cache clearing in the lower-left local UI, including single-run and full-cache clearing.
- Run detail view with stage manifests, preview artifacts, key counts, review output, and before/after comparison.
- Single-stage rerun from the local UI; rerunning a stage also reruns the downstream stages required to keep the final output coherent.
- Lightweight self-review checks for final size, asset bounds, background repair area, mask area ratios, and protected text overlap risk.
- Individual generated asset gallery and saving: cutout assets and styled assets are grouped, can be opened separately, and can be copied to `workspace/saved_outputs/` so they survive cache cleanup.
- Independent artifact directories for every stage.
- Machine-readable `run_summary.json`.
- Engineering docs, requirement docs, data contracts, and implementation status notes.

### Run The Local UI

Install dependencies:

```powershell
pip install -r requirements.txt
```

For optional model-backed adapters, install the matching device dependency set:

```powershell
pip install -r requirements-cpu.txt
# or, for CUDA 12.1 environments:
pip install -r requirements-gpu.txt
```

```powershell
python -B -m ui_auto_gen.cli serve --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

The UI lets you provide:

- Prompt
- Positive rules
- Negative rules
- Target elements
- Base image source
- Reference image
- Algorithm choices for detection, segmentation, OCR, style replacement, and review

Note: optional SAM2 and RapidOCR adapters require model dependencies and local model files where applicable. Future-only choices such as YOLO26 and ControlNet/IPAdapter are still recorded as intent.

### Run The Minimal Pipeline

```powershell
python -B -m ui_auto_gen.cli run --config configs/sample_job.json
```

By default, artifacts are written under:

```text
runs/
```

You can choose a different output root:

```powershell
python -B -m ui_auto_gen.cli run --config configs/sample_job.json --output-root C:\tmp\ui_runs
```

### Important Files

- `docs/PRD.md`: product requirements and MVP scope.
- `docs/PROJECT_GUIDE.md`: progressive project navigation for future conversations and contributors.
- `docs/WORKFLOW.md`: end-to-end workflow.
- `docs/ARCHITECTURE.md`: architecture and module boundaries.
- `docs/DATA_CONTRACTS.md`: JSON contracts exchanged between stages.
- `docs/IMPLEMENTATION_STATUS.md`: completed and pending work.
- `docs/NEXT_GOAL_DEBUG_UI.md`: current visual debugging iteration goal.
- `docs/FEATURE_REQUIREMENTS.md`: public feature requirements.
- `docs/MODEL_SETUP.md`: optional model setup and checkpoint configuration.
- `docs/ROADMAP.md`: future roadmap.
- `configs/sample_job.json`: runnable example job.
- `configs/sample_lightweight_detector_job.json`: example job that requests lightweight detection, SAM2, RapidOCR, and lightweight style transfer.
- `configs/sample_sam2_job.json`: example job that requests SAM2 segmentation and falls back safely when unavailable.
- `configs/sample_rapidocr_job.json`: example job that requests RapidOCR text protection and falls back safely when unavailable.
- `configs/sample_lightweight_style_job.json`: example job that requests lightweight style transfer.
- `configs/sample_lightweight_background_job.json`: example job that requests lightweight background repair with layout preservation disabled.
- `ui_auto_gen/stages/`: independent pipeline stages.
- `ui_auto_gen/web/`: local Web UI and API server.
- `skills/designui-automation/`: progressive Codex/agent skill for operating and extending this project.

### Current Limitations

- No semantic object detection, inpainting, or large-model style generation yet.
- Optional lightweight detection, SAM2.1 segmentation, RapidOCR lightweight OCR, and lightweight local style transfer are connected; other UI choices such as `YOLO26` and `ControlNet + IPAdapter` are currently recorded only.
- The final image is usually the original base image or a text-to-image placeholder SVG.
- Real model capabilities will be added incrementally in future iterations.
