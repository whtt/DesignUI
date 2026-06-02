# 实现状态说明

本文档记录当前本地 UI 和自动化 UI 图生成 pipeline 的真实接入状态。

结论：当前版本已经把“本地 UI -> 生成 job config -> 跑完整 pipeline -> 产出 run artifacts -> 展示调试图和 stage 详情”的工程链路接通。真实检测、分割、OCR、抠图、风格迁移、视觉自审等模型能力仍未接入，当前仍以占位 adapter 为主。

## 已完成项

### 本地 UI

- 已完成：本地 Web UI 页面。
- 已完成：提示词、正向规则、反向规则输入。
- 已完成：需要处理的元素输入。
- 已完成：底图来源选择：示例底图、上传底图、文生图占位。
- 已完成：参考图上传和预览。
- 已完成：底图预览上的手动矩形圈选。
- 已完成：手动框列表、命名和删除。
- 已完成：检测、分割、OCR、风格替换、自审算法选择。
- 已完成：保持原布局、保留文字开关。
- 已完成：一键运行。
- 已完成：运行后展示 stage 状态。
- 已完成：运行后展示最终图。
- 已完成：运行后展示摘要链接。
- 已完成：运行后展示检测框预览。
- 已完成：运行后展示 mask 预览。
- 已完成：运行后展示抠图预览。
- 已完成：运行后展示合成意图预览。
- 已完成：点击 stage 后展示 notes 和 artifact links。

### 后端服务

- 已完成：本地 Python HTTP 服务。
- 已完成：`GET /` 返回 UI 页面。
- 已完成：`POST /api/run` 接收 UI 表单数据。
- 已完成：将 UI 表单数据转换为 job config。
- 已完成：保存 `manual_regions` 到 job config。
- 已完成：保存上传底图。
- 已完成：保存上传参考图。
- 已完成：文生图占位模式生成 SVG 底图。
- 已完成：调用 `PipelineRunner`。
- 已完成：返回 run id、最终图路径、摘要路径、stage 状态。
- 已完成：返回 debug image URLs。
- 已完成：返回每个 stage 的 artifact URLs。
- 已完成：通过 `/artifacts/...` 访问运行产物。

### Pipeline 工程链路

- 已完成：`00_ingest` 读取并复制底图。
- 已完成：`01_plan` 将元素提示转换为结构化元素计划。
- 已完成：`02_detect` 生成检测 manifest。
- 已完成：`02_detect` 在存在手动框时优先使用手动框生成 detections。
- 已完成：`03_segment` 生成 mask manifest。
- 已完成：`04_cutout` 生成 cutout manifest。
- 已完成：`05_style` 生成 styled asset manifest。
- 已完成：`06_compose` 生成 final image。
- 已完成：`07_review` 生成 review manifest。
- 已完成：`08_export` 生成 run summary。
- 已完成：每一步都有独立目录和 JSON 产物。
- 已完成：算法选择会被写入 job config 和相关 stage manifest。
- 已完成：运行产物统一存放在 `runs/`。
- 已完成：UI 生成的临时 job config 统一存放在 `workspace/ui_jobs/`。

### Adapter 边界

- 已完成：`DetectorAdapter` 接口。
- 已完成：`PlaceholderDetector` 占位检测器。
- 已完成：`SegmenterAdapter` 接口。
- 已完成：`PlaceholderSegmenter` 占位分割器。
- 已完成：`StyleAdapter` 接口。
- 已完成：`PlaceholderStyleAdapter` 占位风格器。
- 已完成：`ReviewAdapter` 接口。
- 已完成：`ContractReviewer` 契约检查器。

### 可视化调试产物

- 已完成：`02_detect/detection_preview.png`，展示检测框。
- 已完成：`03_segment/mask_preview.png`，展示半透明占位 mask。
- 已完成：`04_cutout/cutout_preview.png`，展示透明抠图 contact sheet。
- 已完成：`06_compose/composition_preview.png`，展示合成放置意图。
- 已完成：这些调试图会通过 UI 展示，并可通过 artifact link 打开。

### Raster 图像处理基础

- 已完成：通过 Pillow 读取 PNG/JPG。
- 已完成：对 SVG 等暂不支持的格式生成 raster fallback canvas。
- 已完成：生成矩形 mask PNG。
- 已完成：根据 mask PNG 生成透明 cutout PNG。
- 已完成：生成 placeholder styled asset PNG。
- 已完成：基础 alpha paste 合成，输出 `06_compose/final.png`。
- 已完成：最终图不再只是复制底图，而是会贴回 placeholder styled assets。

### 占位可视化说明

- 已完成：`03_segment/mask_preview.png` 会给目标区域加半透明彩色涂层，并标注 `INSTANCE SEG TODO`，明确表示这里未来会由实例分割模型生成精细 mask。
- 已完成：`05_style` 的 placeholder styled asset 会渲染 emoji / sticker 标记，明确表示这里未来会由风格迁移、参数化重绘或资产库替换生成真实素材。
- 已完成：分割和风格阶段的 manifest 已新增 `placeholder_visual` 和 `future_adapter` 字段，记录当前占位表现和未来替换方向。
- 已完成：UI 已新增“待接入模型说明”区域，解释实例分割、风格迁移、OCR 保护和背景修复目前的占位含义。

### OCR and background repair placeholders

- Completed: added `02_ocr_protect`, which writes placeholder text-region manifests and `text_protect_preview.png`.
- Completed: text protection regions are labeled `OCR LOCK TODO` and use `placeholder_visual = ocr_lock_tint`.
- Completed: `06_compose` restores protected text regions from the source image after placeholder style assets are pasted.
- Completed: added `04_background_repair`, which writes placeholder repair manifests, patch PNG files, and `background_repair_preview.png`.
- Completed: background repair regions are labeled `INPAINT TODO` and use `placeholder_visual = inpaint_patch_marker`.
- Completed: UI now displays text protection and background repair previews as independent debug cards.
- Still not connected: real OCR text recognition, real text content regression, and real inpainting models.

### SAM2 tiny segmentation

- Completed: added optional `Sam2TinySegmenter` for `algorithms.segmenter = sam2`.
- Completed: added `configs/sample_sam2_job.json` for SAM2-requested smoke tests.
- Completed: added `docs/MODEL_SETUP.md` and `scripts/download_sam2_tiny.py` for local checkpoint setup.
- Completed: `03_segment/segmentation_manifest.json` now records `model` and `fallback` metadata.
- Completed: when SAM2 dependencies, checkpoint, or device setup fail, the pipeline falls back to `PlaceholderSegmenter` and still completes.
- Completed local deployment: `.venv` uses Python 3.10 with CPU PyTorch and SAM2 installed.
- Completed local deployment: `models/sam2/sam2.1_hiera_tiny.pt` is downloaded locally and ignored by Git.
- Verified local run: UI and CLI can use `actual_adapter = sam2_tiny_segmenter`, `device = cpu`, `fallback = null`.

### 文档

- 已完成：需求文档 `docs/PRD.md`。
- 已完成：流程文档 `docs/WORKFLOW.md`。
- 已完成：架构文档 `docs/ARCHITECTURE.md`。
- 已完成：数据契约文档 `docs/DATA_CONTRACTS.md`。
- 已完成：路线图 `docs/ROADMAP.md`。
- 已完成：可视化调试目标文档 `docs/NEXT_GOAL_DEBUG_UI.md`。
- 已完成：当前实现状态文档 `docs/IMPLEMENTATION_STATUS.md`。

## 占位或未接入项

### 提示词和规则

- 占位：提示词、正向规则、反向规则会被保存到 job config。
- 未接入：提示词还没有真正驱动 VLM 规划。
- 未接入：正反规则还没有真正约束检测、生成或自审。
- 未接入：还没有 prompt 模板系统。
- 未接入：还没有规则冲突检查。

### 参考图

- 已接入文件管理：参考图可以上传、保存、预览。
- 占位：参考图路径会被写入 job config。
- 未接入：参考图还没有传给风格迁移模型。
- 未接入：还没有 IPAdapter、CLIP style embedding 或风格 token 提取。

### 文生图

- 占位：文生图模式目前只生成一张 SVG 占位底图。
- 未接入：还没有真实 text-to-image 模型。
- 未接入：还没有生成底图后的自审和重试。

### 检测算法

- 占位：下拉框里的 `YOLO26`、`Grounded SAM`、`VLM 区域提议` 目前只会被记录。
- 当前实际执行：`PlaceholderDetector`。
- 已接入：手动矩形圈选优先于占位检测框。
- 未接入：YOLO26 检测。
- 未接入：Grounding DINO / Grounded SAM 开放词汇检测。
- 未接入：VLM 区域提议。
- 未接入：检测置信度阈值配置。
- 未接入：重复框合并和 NMS。

### 分割算法

- 占位：下拉框里的 `SAM2`、`YOLO26 Seg`、`Mask Refiner` 目前只会被记录。
- 当前实际执行：`PlaceholderSegmenter`。
- 未接入：SAM/SAM2 mask 生成。
- 未接入：YOLO26 segmentation。
- 未接入：mask 边缘精修。
- 未接入：透明 PNG mask 输出。
- 未接入：mask 质量评分。

### OCR

- 占位：OCR 下拉框目前只会被记录。
- 当前实际执行：`PlaceholderOcrProtector`，会生成文字保护占位区域。
- 未接入：PaddleOCR、docTR、VLM OCR。
- 已接入占位：文字区域保护 manifest、预览图，以及合成阶段原图恢复。
- 未接入：文字重新排版。
- 未接入：文字内容回归检查。

### 抠图和背景修复

- 已接入：`04_cutout` 会生成 cutout JSON 和透明 PNG。
- 已接入：矩形 mask 下的 alpha cutout。
- 已接入：透明 PNG 元素输出。
- 已接入占位：背景修复 manifest、预览图和 placeholder patch。
- 未接入：真实背景 inpainting。
- 未接入：阴影分离。
- 未接入：边缘羽化。

### 风格替换

- 占位：下拉框里的 `ControlNet + IPAdapter`、`参数化 UI 重绘`、`资产库替换` 目前只会被记录。
- 当前实际执行：`PlaceholderStyleAdapter`。
- 未接入：ControlNet、IPAdapter、LoRA、ComfyUI workflow。
- 未接入：参数化按钮/卡片/表单控件重绘。
- 未接入：图标资产库替换。
- 未接入：色板和 design token 自动应用。

### 合成

- 已接入：`06_compose` 当前会输出 raster `final.png`。
- 已接入：合成意图预览。
- 已接入：根据 bbox 放回 placeholder styled asset。
- 已接入：透明通道混合。
- 未接入：真实生成资产图层合成。
- 未接入：阴影、高光、边框重建。
- 未接入：像素网格对齐。
- 未接入：全局色彩统一。

### 自审

- 当前实际执行：契约检查。
- 已接入：检查元素数量、styled asset 数量、最终图是否存在。
- 占位：VLM 视觉自审只在下拉框中记录。
- 未接入：风格一致性评分。
- 未接入：布局重叠检测。
- 未接入：OCR 文本保持检查。
- 未接入：边缘瑕疵检查。
- 未接入：局部自动修复循环。

### 导出

- 已接入：最终图片路径。
- 已接入：run summary JSON。
- 未接入：PSD。
- 未接入：layered PNG。
- 未接入：Figma。
- 未接入：HTML/CSS 重建。
- 未接入：可复现模型参数包。

## 当前 UI 中容易误解的地方

- “检测算法”下拉框现在不是实际切换模型，只是记录用户选择。
- “分割算法”下拉框现在不是实际切换模型，只是记录用户选择。
- “OCR”下拉框现在没有实际 OCR 行为。
- “风格替换”下拉框现在没有实际生成行为。
- “自审”下拉框现在只有契约检查真实运行。
- “最终结果”目前多数情况下等于输入底图或文生图占位底图。
- “参考图”目前只参与保存和记录，还没有参与生成。

## 下一批建议优先完成

1. 扩展手动 correction UI：polygon/lasso/brush mask。
2. 接入第一个真实模型，优先建议从分割或 OCR 开始。
3. 增加运行历史列表和 run 详情页。
4. 将背景修复占位升级为真实 inpainting adapter。
5. 增加 OCR 文本内容回归检查。
