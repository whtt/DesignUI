# 实现状态说明

本文档记录当前本地 UI 和自动化 UI 图生成 pipeline 的真实接入状态。

结论先说清楚：当前版本已经把“傻瓜式 UI → 生成 job config → 跑完整 pipeline → 产出 run artifacts”的工程链路接通了，但检测、分割、OCR、抠图、风格迁移、视觉自审等模型能力仍是占位实现。

## 已完成项

### 本地 UI

- 已完成：本地 Web UI 页面。
- 已完成：提示词输入框。
- 已完成：正向规则输入框。
- 已完成：反向规则输入框。
- 已完成：需要处理的元素输入框。
- 已完成：底图来源选择。
- 已完成：示例底图模式。
- 已完成：上传底图控件。
- 已完成：文生图占位模式。
- 已完成：参考图上传控件。
- 已完成：底图预览。
- 已完成：参考图预览。
- 已完成：检测算法下拉选择。
- 已完成：分割算法下拉选择。
- 已完成：OCR 下拉选择。
- 已完成：风格替换下拉选择。
- 已完成：自审下拉选择。
- 已完成：保持原布局开关。
- 已完成：保留文字开关。
- 已完成：运行按钮。
- 已完成：运行后展示 stage 状态。
- 已完成：运行后展示最终图。
- 已完成：运行后提供摘要链接。

### 后端服务

- 已完成：本地 Python HTTP 服务。
- 已完成：`GET /` 返回 UI 页面。
- 已完成：`POST /api/run` 接收 UI 表单数据。
- 已完成：将 UI 表单数据转换为 job config。
- 已完成：保存上传的底图文件。
- 已完成：保存上传的参考图文件。
- 已完成：文生图占位模式生成一张 SVG 占位底图。
- 已完成：调用现有 `PipelineRunner`。
- 已完成：返回 run id、最终图路径、摘要路径、stage 状态。
- 已完成：通过 `/artifacts/...` 访问运行产物。

### Pipeline 工程链路

- 已完成：`00_ingest` 读取并复制底图。
- 已完成：`01_plan` 将元素提示转换为结构化元素计划。
- 已完成：`02_detect` 生成检测 manifest。
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

### 文档

- 已完成：需求文档 `docs/PRD.md`。
- 已完成：流程文档 `docs/WORKFLOW.md`。
- 已完成：架构文档 `docs/ARCHITECTURE.md`。
- 已完成：数据契约文档 `docs/DATA_CONTRACTS.md`。
- 已完成：路线图 `docs/ROADMAP.md`。
- 已完成：当前实现状态文档 `docs/IMPLEMENTATION_STATUS.md`。

## 占位或未接入项

### 提示词和规则

- 占位：提示词目前会被保存到 job config。
- 占位：正向规则目前会被保存到 job config。
- 占位：反向规则目前会被保存到 job config。
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
- 当前实际执行：`placeholder_detector`。
- 未接入：YOLO26 检测。
- 未接入：Grounding DINO / Grounded SAM 开放词汇检测。
- 未接入：VLM 区域提议。
- 未接入：检测置信度阈值配置。
- 未接入：重复框合并和 NMS。

### 分割算法

- 占位：下拉框里的 `SAM2`、`YOLO26 Seg`、`Mask Refiner` 目前只会被记录。
- 当前实际执行：`placeholder_segmenter`。
- 未接入：SAM/SAM2 mask 生成。
- 未接入：YOLO26 segmentation。
- 未接入：mask 边缘精修。
- 未接入：透明 PNG mask 输出。
- 未接入：mask 质量评分。

### OCR

- 占位：OCR 下拉框目前只会被记录。
- 当前实际执行：没有真实 OCR。
- 未接入：PaddleOCR。
- 未接入：docTR。
- 未接入：VLM OCR。
- 未接入：文字区域保护。
- 未接入：文字重新排版。
- 未接入：文字内容回归检查。

### 抠图和背景修复

- 占位：`04_cutout` 目前只生成 cutout JSON。
- 未接入：真实 alpha cutout。
- 未接入：透明 PNG 元素输出。
- 未接入：背景 inpainting。
- 未接入：阴影分离。
- 未接入：边缘羽化。

### 风格替换

- 占位：下拉框里的 `ControlNet + IPAdapter`、`参数化 UI 重绘`、`资产库替换` 目前只会被记录。
- 当前实际执行：`placeholder_style_adapter`。
- 未接入：ControlNet。
- 未接入：IPAdapter。
- 未接入：LoRA。
- 未接入：ComfyUI workflow。
- 未接入：参数化按钮/卡片/表单控件重绘。
- 未接入：图标资产库替换。
- 未接入：色板和 design token 自动应用。

### 合成

- 占位：`06_compose` 当前只是复制底图作为 final image。
- 未接入：真实图层合成。
- 未接入：根据 bbox 放回替换元素。
- 未接入：透明通道混合。
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

1. 接入真实图片读写能力，支持 PNG/JPG 上的 bbox 可视化。
2. 在 `02_detect` 增加一个简单可视化检测框输出。
3. 在 `03_segment` 增加真实 mask 文件格式，即使先用矩形 mask。
4. 在 `06_compose` 增加基础 PIL 合成功能。
5. 增加 OCR 文字保护占位层，防止后续生成模型破坏文字。
6. 再接第一个真实模型，优先建议从检测或分割开始。

