# DesignUI / 自动化 UI 图生成流程

[中文](#中文) | [English](#english)

## 中文

DesignUI 是一个用于自动化 UI 图生成的最小工程框架。它的目标是把“底图 + 提示词 + 正反规则 + 参考图 + 算法选择”转换成一个可迭代的文件化 pipeline，后续可以逐步接入 YOLO、SAM、OCR、VLM、风格迁移和自审模型。

当前版本刻意不接外部 API 或真实模型。每个步骤都通过独立目录和 JSON manifest 交接，方便后续替换成真实算法，而不需要重写整个流程。

### 当前已具备

- 本地 Web UI。
- 命令行 pipeline。
- job config 生成与管理。
- 底图导入。
- 元素计划生成。
- 检测、分割、抠图、风格替换、合成、自审、导出的占位流程。
- 每一步独立产物目录。
- 运行摘要 `run_summary.json`。
- 工程文档、需求文档、数据契约和实现状态说明。

### 运行本地 UI

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

注意：当前算法选择会被记录到 job config 和 stage manifest 中，但真实模型还未接入。

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
- `docs/WORKFLOW.md`：端到端流程。
- `docs/ARCHITECTURE.md`：架构和模块边界。
- `docs/DATA_CONTRACTS.md`：各步骤 JSON 数据契约。
- `docs/IMPLEMENTATION_STATUS.md`：已完成项和待完成项。
- `docs/ROADMAP.md`：后续路线图。
- `configs/sample_job.json`：可运行示例配置。
- `ui_auto_gen/stages/`：独立 pipeline stage。
- `ui_auto_gen/web/`：本地 Web UI 和 API 服务。

### 当前限制

- 尚未接入真实目标检测、分割、OCR、抠图、inpainting 或风格迁移。
- `YOLO26`、`SAM2`、`ControlNet + IPAdapter` 等 UI 选项当前只是记录选择。
- 最终图目前通常是底图或文生图占位 SVG。
- 真实模型能力会在后续迭代中逐步接入。

## English

DesignUI is a minimal engineering framework for automated UI image generation. Its goal is to turn a base image, prompt, positive/negative rules, reference image, and algorithm selections into an iterative file-based pipeline that can later integrate YOLO, SAM, OCR, VLM, style-transfer, and self-review models.

The current version intentionally avoids external APIs and real model integrations. Each step exchanges artifacts through its own directory and JSON manifest, making it easy to replace placeholder logic with real algorithms later without rewriting the whole pipeline.

### What Works Now

- Local Web UI.
- Command-line pipeline.
- Job config generation and management.
- Base image ingestion.
- Structured element planning.
- Placeholder detection, segmentation, cutout, style, composition, review, and export stages.
- Independent artifact directories for every stage.
- Machine-readable `run_summary.json`.
- Engineering docs, requirement docs, data contracts, and implementation status notes.

### Run The Local UI

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

Note: current algorithm choices are recorded in the generated job config and stage manifests, but real model adapters are not connected yet.

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
- `docs/WORKFLOW.md`: end-to-end workflow.
- `docs/ARCHITECTURE.md`: architecture and module boundaries.
- `docs/DATA_CONTRACTS.md`: JSON contracts exchanged between stages.
- `docs/IMPLEMENTATION_STATUS.md`: completed and pending work.
- `docs/ROADMAP.md`: future roadmap.
- `configs/sample_job.json`: runnable example job.
- `ui_auto_gen/stages/`: independent pipeline stages.
- `ui_auto_gen/web/`: local Web UI and API server.

### Current Limitations

- No real object detection, segmentation, OCR, cutout, inpainting, or style transfer yet.
- UI choices such as `YOLO26`, `SAM2`, and `ControlNet + IPAdapter` are currently recorded only.
- The final image is usually the original base image or a text-to-image placeholder SVG.
- Real model capabilities will be added incrementally in future iterations.
