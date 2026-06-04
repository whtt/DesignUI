const runButton = document.querySelector("#runButton");
const statusTitle = document.querySelector("#statusTitle");
const stageList = document.querySelector("#stageList");
const resultImage = document.querySelector("#resultImage");
const resultEmpty = document.querySelector("#resultEmpty");
const summaryLink = document.querySelector("#summaryLink");
const saveFinalButton = document.querySelector("#saveFinalButton");
const refreshHistoryButton = document.querySelector("#refreshHistoryButton");
const clearRunsButton = document.querySelector("#clearRunsButton");
const runHistory = document.querySelector("#runHistory");
const placeholderGuide = document.querySelector("#placeholderGuide");
const debugGallery = document.querySelector("#debugGallery");
const assetPanel = document.querySelector("#assetPanel");
const cutoutAssetList = document.querySelector("#cutoutAssetList");
const styleAssetList = document.querySelector("#styleAssetList");
const compositionEditor = document.querySelector("#compositionEditor");
const compositionSurface = document.querySelector("#compositionSurface");
const compositionBaseImage = document.querySelector("#compositionBaseImage");
const compositionOverlay = document.querySelector("#compositionOverlay");
const compositionLayerList = document.querySelector("#compositionLayerList");
const applyCompositionButton = document.querySelector("#applyCompositionButton");
const workspaceMenu = document.querySelector("#workspaceMenu");
const workspaceButtons = document.querySelectorAll("[data-workspace-target]");
const workspacePages = document.querySelectorAll("[data-workspace-page]");
const runDetailPanel = document.querySelector("#runDetailPanel");
const detailRunTitle = document.querySelector("#detailRunTitle");
const detailCompareGrid = document.querySelector("#detailCompareGrid");
const detailReviewList = document.querySelector("#detailReviewList");
const detailStageGrid = document.querySelector("#detailStageGrid");
const selectedAssetDetail = document.querySelector("#selectedAssetDetail");
const baseImageInput = document.querySelector("#baseImage");
const referenceImageInput = document.querySelector("#referenceImage");
const basePreview = document.querySelector("#basePreview");
const preserveLayoutInput = document.querySelector("#preserveLayout");
const backgroundRepairSelect = document.querySelector("#backgroundRepair");
const selectionSurface = document.querySelector("#selectionSurface");
const selectionOverlay = document.querySelector("#selectionOverlay");
const manualRegionList = document.querySelector("#manualRegionList");
const clearManualRegionsButton = document.querySelector("#clearManualRegions");
let referencePreview = document.querySelector("#referencePreview");
let latestRun = null;
let manualRegions = [];
let activeSelection = null;
let compositionPlacements = [];
let activeCompositionDrag = null;
let activeWorkspacePage = "result";

const debugTargets = {
  detection_preview: {
    img: document.querySelector("#detectionPreview"),
    empty: document.querySelector("#detectionPreviewEmpty"),
    link: document.querySelector("#detectionPreviewLink"),
  },
  mask_preview: {
    img: document.querySelector("#maskPreview"),
    empty: document.querySelector("#maskPreviewEmpty"),
    link: document.querySelector("#maskPreviewLink"),
  },
  text_protect_preview: {
    img: document.querySelector("#textProtectPreview"),
    empty: document.querySelector("#textProtectPreviewEmpty"),
    link: document.querySelector("#textProtectPreviewLink"),
  },
  cutout_preview: {
    img: document.querySelector("#cutoutPreview"),
    empty: document.querySelector("#cutoutPreviewEmpty"),
    link: document.querySelector("#cutoutPreviewLink"),
  },
  background_repair_preview: {
    img: document.querySelector("#backgroundRepairPreview"),
    empty: document.querySelector("#backgroundRepairPreviewEmpty"),
    link: document.querySelector("#backgroundRepairPreviewLink"),
  },
  style_preview: {
    img: document.querySelector("#stylePreview"),
    empty: document.querySelector("#stylePreviewEmpty"),
    link: document.querySelector("#stylePreviewLink"),
  },
  composition_preview: {
    img: document.querySelector("#compositionPreview"),
    empty: document.querySelector("#compositionPreviewEmpty"),
    link: document.querySelector("#compositionPreviewLink"),
  },
};

baseImageInput.addEventListener("change", async () => {
  const file = baseImageInput.files[0];
  if (!file) return;
  basePreview.src = await fileToDataUrl(file);
  document.querySelector('input[name="baseMode"][value="upload"]').checked = true;
  clearManualRegions();
});

document.querySelectorAll('input[name="baseMode"]').forEach((input) => {
  input.addEventListener("change", () => {
    if (input.value === "sample" && input.checked) {
      basePreview.src = "/static/sample-thumb.svg";
    }
    clearManualRegions();
  });
});

referenceImageInput.addEventListener("change", async () => {
  const file = referenceImageInput.files[0];
  if (!file) return;
  const url = await fileToDataUrl(file);
  const img = document.createElement("img");
  img.src = url;
  img.alt = "参考图预览";
  referencePreview.replaceWith(img);
  img.id = "referencePreview";
  referencePreview = img;
});

basePreview.addEventListener("load", renderManualRegions);
window.addEventListener("resize", () => {
  renderManualRegions();
  renderCompositionOverlay();
});

selectionSurface.addEventListener("pointerdown", (event) => {
  const point = pointerToNorm(event);
  if (!point) return;
  event.preventDefault();
  activeSelection = {
    start: point,
    end: point,
    element: document.createElement("div"),
  };
  activeSelection.element.className = "manual-region-box active";
  selectionOverlay.appendChild(activeSelection.element);
  selectionSurface.setPointerCapture(event.pointerId);
  updateActiveSelection();
});

selectionSurface.addEventListener("pointermove", (event) => {
  if (!activeSelection) return;
  const point = pointerToNorm(event);
  if (!point) return;
  activeSelection.end = point;
  updateActiveSelection();
});

selectionSurface.addEventListener("pointerup", (event) => {
  if (!activeSelection) return;
  const point = pointerToNorm(event);
  if (point) activeSelection.end = point;
  const bboxNorm = normalizedSelection(activeSelection.start, activeSelection.end);
  activeSelection.element.remove();
  activeSelection = null;
  selectionSurface.releasePointerCapture(event.pointerId);
  if (bboxNorm[2] - bboxNorm[0] < 0.01 || bboxNorm[3] - bboxNorm[1] < 0.01) return;
  addManualRegion(bboxNorm);
});

selectionSurface.addEventListener("pointercancel", () => {
  if (activeSelection?.element) activeSelection.element.remove();
  activeSelection = null;
});

clearManualRegionsButton.addEventListener("click", clearManualRegions);
refreshHistoryButton.addEventListener("click", loadRunHistory);
clearRunsButton.addEventListener("click", clearRunCache);
preserveLayoutInput.addEventListener("change", updateBackgroundRepairAvailability);
applyCompositionButton.addEventListener("click", applyManualComposition);
workspaceButtons.forEach((button) => {
  button.addEventListener("click", () => setWorkspacePage(button.dataset.workspaceTarget));
});
saveFinalButton.addEventListener("click", () => {
  if (!latestRun?.final_image_url) return;
  saveArtifact({
    url: latestRun.final_image_url,
    label: `${latestRun.run_id}_final`,
    statusElement: saveFinalButton,
  });
});

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  statusTitle.textContent = "运行中";
  summaryLink.hidden = true;
  saveFinalButton.hidden = true;
  resultImage.hidden = true;
  resultEmpty.hidden = false;
  renderAssetPanel([], []);
  renderCompositionEditor(null);
  setWorkspacePage("result");
  setResultSectionsVisible(false);
  latestRun = null;
  resetDebugImages();
  setStages("pending");

  try {
    const payload = await collectPayload();
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "运行失败");

    latestRun = data;
    statusTitle.textContent = `完成：${data.run_id}`;
    setStages("complete", data.stages);
    setResultSectionsVisible(true);
    renderDebugImages(data.debug_images || {});
    renderAssetPanel(data.cutout_assets || [], data.styled_assets || data.generated_assets || []);
    renderCompositionEditor(data);
    renderRunDetails(data);
    resultImage.src = withCacheBust(data.final_image_url);
    resultImage.hidden = false;
    resultEmpty.hidden = true;
    summaryLink.href = data.summary_url;
    summaryLink.hidden = false;
    saveFinalButton.hidden = false;
    await loadRunHistory();
  } catch (error) {
    statusTitle.textContent = error.message;
    setStages("");
  } finally {
    runButton.disabled = false;
  }
});

loadRunHistory();
updateBackgroundRepairAvailability();

async function collectPayload() {
  const baseMode = document.querySelector('input[name="baseMode"]:checked').value;
  const baseFile = baseImageInput.files[0];
  const referenceFile = referenceImageInput.files[0];

  return {
    projectName: "ui_web_job",
    prompt: valueOf("#prompt"),
    positiveRules: valueOf("#positiveRules"),
    negativeRules: valueOf("#negativeRules"),
    elementHints: valueOf("#elementHints"),
    manualRegions: manualRegions.map((region) => ({
      id: region.id,
      name: region.name,
      type_hint: region.type_hint,
      bbox_norm: region.bbox_norm,
    })),
    baseMode,
    baseImage: baseFile ? await filePayload(baseFile) : null,
    referenceImage: referenceFile ? await filePayload(referenceFile) : null,
    preserveLayout: preserveLayoutInput.checked,
    keepText: document.querySelector("#keepText").checked,
    algorithms: {
      detector: valueOf("#detector"),
      segmenter: valueOf("#segmenter"),
      ocr: valueOf("#ocr"),
      backgroundRepair: valueOf("#backgroundRepair"),
      style: valueOf("#style"),
      review: valueOf("#review"),
    },
  };
}

function updateBackgroundRepairAvailability() {
  backgroundRepairSelect.disabled = preserveLayoutInput.checked;
  backgroundRepairSelect.title = preserveLayoutInput.checked
    ? "保持原布局时会跳过背景修复"
    : "不保持原布局时用于补齐元素移走后的背景";
}

function addManualRegion(bboxNorm) {
  const index = manualRegions.length + 1;
  const id = `manual_${String(index).padStart(3, "0")}`;
  manualRegions.push({
    id,
    name: id,
    type_hint: "manual",
    bbox_norm: bboxNorm,
  });
  renderManualRegions();
}

function clearManualRegions() {
  manualRegions = [];
  renderManualRegions();
}

function renderManualRegions() {
  renderManualOverlay();
  renderManualList();
}

function renderManualOverlay() {
  selectionOverlay.querySelectorAll(".manual-region-box:not(.active)").forEach((element) => element.remove());
  const contentRect = imageContentRect();
  if (!contentRect) return;
  const surfaceRect = selectionSurface.getBoundingClientRect();
  manualRegions.forEach((region, index) => {
    const element = document.createElement("div");
    element.className = "manual-region-box";
    element.textContent = region.name;
    positionRegionElement(element, region.bbox_norm, contentRect, surfaceRect);
    selectionOverlay.appendChild(element);
  });
}

function renderManualList() {
  if (!manualRegions.length) {
    manualRegionList.textContent = "暂无手动框";
    return;
  }
  manualRegionList.innerHTML = "";
  manualRegions.forEach((region, index) => {
    const row = document.createElement("div");
    row.className = "manual-region-row";

    const nameInput = document.createElement("input");
    nameInput.value = region.name;
    nameInput.setAttribute("aria-label", "手动框名称");
    nameInput.addEventListener("input", () => {
      region.name = nameInput.value.trim() || region.id;
      region.type_hint = region.name;
      renderManualOverlay();
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "删除";
    deleteButton.addEventListener("click", () => {
      manualRegions.splice(index, 1);
      renderManualRegions();
    });

    row.appendChild(nameInput);
    row.appendChild(deleteButton);
    manualRegionList.appendChild(row);
  });
}

function pointerToNorm(event) {
  const rect = imageContentRect();
  if (!rect) return null;
  const x = clamp((event.clientX - rect.left) / rect.width, 0, 1);
  const y = clamp((event.clientY - rect.top) / rect.height, 0, 1);
  return { x, y };
}

function imageContentRect() {
  const rect = basePreview.getBoundingClientRect();
  const naturalWidth = basePreview.naturalWidth || rect.width;
  const naturalHeight = basePreview.naturalHeight || rect.height;
  if (!rect.width || !rect.height || !naturalWidth || !naturalHeight) return null;

  const elementRatio = rect.width / rect.height;
  const imageRatio = naturalWidth / naturalHeight;
  let width = rect.width;
  let height = rect.height;
  let left = rect.left;
  let top = rect.top;
  if (elementRatio > imageRatio) {
    width = rect.height * imageRatio;
    left = rect.left + (rect.width - width) / 2;
  } else {
    height = rect.width / imageRatio;
    top = rect.top + (rect.height - height) / 2;
  }
  return { left, top, width, height };
}

function updateActiveSelection() {
  if (!activeSelection) return;
  const bboxNorm = normalizedSelection(activeSelection.start, activeSelection.end);
  const contentRect = imageContentRect();
  if (!contentRect) return;
  const surfaceRect = selectionSurface.getBoundingClientRect();
  positionRegionElement(activeSelection.element, bboxNorm, contentRect, surfaceRect);
}

function normalizedSelection(start, end) {
  return [
    Math.min(start.x, end.x),
    Math.min(start.y, end.y),
    Math.max(start.x, end.x),
    Math.max(start.y, end.y),
  ];
}

function positionRegionElement(element, bboxNorm, contentRect, surfaceRect) {
  const left = contentRect.left - surfaceRect.left + bboxNorm[0] * contentRect.width;
  const top = contentRect.top - surfaceRect.top + bboxNorm[1] * contentRect.height;
  const width = (bboxNorm[2] - bboxNorm[0]) * contentRect.width;
  const height = (bboxNorm[3] - bboxNorm[1]) * contentRect.height;
  Object.assign(element.style, {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
  });
}

function renderDebugImages(debugImages) {
  for (const [key, target] of Object.entries(debugTargets)) {
    const url = debugImages[key];
    if (!url) continue;
    target.img.src = withCacheBust(url);
    target.img.hidden = false;
    target.empty.hidden = true;
    target.link.href = url;
    target.link.hidden = false;
  }
}

function setResultSectionsVisible(visible) {
  workspaceMenu.hidden = !visible;
  if (!visible) {
    workspacePages.forEach((page) => {
      page.hidden = true;
    });
    compositionEditor.hidden = true;
    return;
  }
  applyWorkspacePage();
}

function setWorkspacePage(page) {
  activeWorkspacePage = page || "result";
  applyWorkspacePage();
}

function applyWorkspacePage() {
  workspaceButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.workspaceTarget === activeWorkspacePage);
  });
  workspacePages.forEach((page) => {
    const isActive = page.dataset.workspacePage === activeWorkspacePage;
    if (page === compositionEditor) {
      page.hidden = !isActive || !compositionPlacements.length;
    } else if (page === assetPanel) {
      page.hidden = !isActive;
    } else if (page === runDetailPanel) {
      page.hidden = !isActive || !latestRun;
    } else {
      page.hidden = !isActive;
    }
  });
  renderCompositionOverlay();
}

function renderAssetPanel(cutoutAssets, styledAssets) {
  renderAssetList(cutoutAssetList, cutoutAssets, "暂无抠图素材");
  renderAssetList(styleAssetList, styledAssets, "暂无风格素材");
  renderSelectedAsset(null);
  applyWorkspacePage();
}

function renderAssetList(container, assets, emptyText) {
  container.innerHTML = "";
  if (!assets.length) {
    container.textContent = emptyText;
    return;
  }

  assets.forEach((asset) => {
    const card = document.createElement("article");
    card.className = "asset-card";

    const image = document.createElement("img");
    image.src = withCacheBust(asset.url);
    image.alt = asset.element_id || asset.asset_id || "生成素材";

    const title = document.createElement("b");
    title.textContent = asset.element_id || asset.asset_id || "生成素材";

    const meta = document.createElement("span");
    meta.textContent = asset.source || "generated";

    const actions = document.createElement("div");
    actions.className = "asset-actions";

    const selectButton = document.createElement("button");
    selectButton.className = "small-button";
    selectButton.type = "button";
    selectButton.textContent = "选择";
    selectButton.addEventListener("click", () => renderSelectedAsset(asset));

    actions.appendChild(selectButton);
    card.appendChild(image);
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(actions);
    container.appendChild(card);
  });
}

function renderSelectedAsset(asset) {
  selectedAssetDetail.innerHTML = "";
  if (!asset) {
    selectedAssetDetail.textContent = "选择一个素材后查看和保存";
    return;
  }

  const preview = document.createElement("img");
  preview.src = withCacheBust(asset.url);
  preview.alt = asset.element_id || asset.asset_id || "素材";

  const meta = document.createElement("div");
  meta.className = "selected-asset-meta";
  const title = document.createElement("b");
  title.textContent = asset.element_id || asset.asset_id || "素材";
  const source = document.createElement("span");
  source.textContent = asset.source || "generated";
  meta.appendChild(title);
  meta.appendChild(source);

  const actions = document.createElement("div");
  actions.className = "selected-asset-actions";
  const openLink = document.createElement("a");
  openLink.className = "ghost-link";
  openLink.href = asset.url;
  openLink.target = "_blank";
  openLink.textContent = "打开";
  const saveButton = document.createElement("button");
  saveButton.className = "small-button";
  saveButton.type = "button";
  saveButton.textContent = "保存";
  saveButton.addEventListener("click", () => {
    saveArtifact({
      url: asset.url,
      label: asset.element_id || asset.asset_id || "asset",
      statusElement: saveButton,
    });
  });
  actions.appendChild(openLink);
  actions.appendChild(saveButton);

  selectedAssetDetail.appendChild(preview);
  selectedAssetDetail.appendChild(meta);
  selectedAssetDetail.appendChild(actions);
}

async function saveArtifact({ url, label, statusElement }) {
  const previousText = statusElement.textContent;
  statusElement.disabled = true;
  statusElement.textContent = "保存中";
  try {
    const response = await fetch("/api/save-artifact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, label }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "保存失败");
    statusElement.textContent = "已保存";
    statusElement.title = data.saved_path;
  } catch (error) {
    statusElement.textContent = error.message;
  } finally {
    window.setTimeout(() => {
      statusElement.disabled = false;
      statusElement.textContent = previousText;
    }, 1400);
  }
}

async function loadRunHistory() {
  try {
    const response = await fetch("/api/runs");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "读取历史失败");
    renderRunHistory(data.runs || []);
  } catch (error) {
    runHistory.textContent = error.message;
  }
}

function renderRunHistory(runs) {
  runHistory.innerHTML = "";
  if (!runs.length) {
    runHistory.textContent = "暂无历史记录";
    return;
  }

  runs.forEach((run) => {
    const item = document.createElement("div");
    item.className = "run-history-item";

    const text = document.createElement("div");
    const title = document.createElement("b");
    title.textContent = run.run_id;
    const meta = document.createElement("span");
    const assetCount = (run.cutout_assets || []).length + (run.styled_assets || run.generated_assets || []).length;
    meta.textContent = `${run.status} · ${assetCount} 个素材`;
    text.appendChild(title);
    text.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "history-actions";

    const viewButton = document.createElement("button");
    viewButton.className = "small-button";
    viewButton.type = "button";
    viewButton.textContent = "查看";
    viewButton.disabled = !run.final_image_url;
    viewButton.addEventListener("click", () => restoreRunPreview(run));

    const summary = document.createElement("a");
    summary.className = "ghost-link";
    summary.href = run.summary_url || "#";
    summary.target = "_blank";
    summary.textContent = "摘要";
    if (!run.summary_url) summary.hidden = true;

    const deleteButton = document.createElement("button");
    deleteButton.className = "small-button danger-button";
    deleteButton.type = "button";
    deleteButton.textContent = "清除";
    deleteButton.addEventListener("click", () => deleteRunCache(run.run_id));

    actions.appendChild(viewButton);
    actions.appendChild(summary);
    actions.appendChild(deleteButton);
    item.appendChild(text);
    item.appendChild(actions);
    runHistory.appendChild(item);
  });
}

async function restoreRunPreview(run) {
  const runDetails = await fetchRunDetails(run);
  run = runDetails || run;
  latestRun = {
    run_id: run.run_id,
    final_image_url: run.final_image_url,
  };
  statusTitle.textContent = `查看历史：${run.run_id}`;
  resultImage.src = withCacheBust(run.final_image_url);
  resultImage.hidden = false;
  resultEmpty.hidden = true;
  summaryLink.href = run.summary_url || "#";
  summaryLink.hidden = !run.summary_url;
  saveFinalButton.hidden = !run.final_image_url;
  setResultSectionsVisible(true);
  resetDebugImages();
  renderDebugImages(run.debug_images || {});
  renderAssetPanel(run.cutout_assets || [], run.styled_assets || run.generated_assets || []);
  renderCompositionEditor(run);
  renderRunDetails(run);
}

async function fetchRunDetails(run) {
  if (!run?.run_id || run.stage_details) return run;
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(run.run_id)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "读取历史详情失败");
    return data;
  } catch (error) {
    statusTitle.textContent = error.message;
    return run;
  }
}

async function deleteRunCache(runId) {
  try {
    const response = await fetch("/api/delete-run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "清除失败");
    if (latestRun?.run_id === runId) {
      latestRun = null;
      statusTitle.textContent = `已清除：${runId}`;
      summaryLink.hidden = true;
      saveFinalButton.hidden = true;
      resultImage.hidden = true;
      resultEmpty.hidden = false;
      setResultSectionsVisible(false);
      renderAssetPanel([], []);
      renderCompositionEditor(null);
      renderRunDetails(null);
      resetDebugImages();
    }
    renderRunHistory(data.runs || []);
  } catch (error) {
    statusTitle.textContent = error.message;
  }
}

async function clearRunCache() {
  if (!confirm("确定清除全部历史缓存吗？已保存到 workspace/saved_outputs 的图片不会被删除。")) {
    return;
  }
  clearRunsButton.disabled = true;
  clearRunsButton.textContent = "清除中";
  try {
    const response = await fetch("/api/clear-runs", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "清除失败");
    latestRun = null;
    statusTitle.textContent = `已清除 ${data.deleted.length} 个 run`;
    summaryLink.hidden = true;
    saveFinalButton.hidden = true;
    resultImage.hidden = true;
    resultEmpty.hidden = false;
    setResultSectionsVisible(false);
    renderAssetPanel([], []);
    renderCompositionEditor(null);
    renderRunDetails(null);
    resetDebugImages();
    setStages("");
    renderRunHistory([]);
  } catch (error) {
    statusTitle.textContent = error.message;
  } finally {
    clearRunsButton.disabled = false;
    clearRunsButton.textContent = "清除缓存";
  }
}

function renderRunDetails(run) {
  detailCompareGrid.innerHTML = "";
  detailReviewList.innerHTML = "";
  detailStageGrid.innerHTML = "";
  if (!run) {
    applyWorkspacePage();
    return;
  }

  detailRunTitle.textContent = run.run_id || "阶段详情";
  renderDetailCompare(run);
  renderReviewDetails(run.review || {});
  renderStageDetails(run);
  applyWorkspacePage();
}

function renderDetailCompare(run) {
  const items = [
    { label: "原图", url: run.base_image_url },
    { label: "修复底板", url: run.background_canvas_url },
    { label: "最终图", url: run.final_image_url },
  ].filter((item) => item.url);

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "detail-compare-card";
    const title = document.createElement("b");
    title.textContent = item.label;
    const image = document.createElement("img");
    image.src = withCacheBust(item.url);
    image.alt = item.label;
    card.appendChild(title);
    card.appendChild(image);
    detailCompareGrid.appendChild(card);
  });
}

function renderReviewDetails(review) {
  const status = document.createElement("div");
  status.className = "review-status";
  const score = review.score === undefined || review.score === null ? "-" : review.score;
  status.textContent = `自审：${review.pass ? "通过" : "需关注"} · 分数 ${score}`;
  detailReviewList.appendChild(status);

  const checks = review.checks || [];
  const issues = review.issues || [];
  if (!checks.length && !issues.length) {
    const empty = document.createElement("div");
    empty.className = "detail-empty";
    empty.textContent = "暂无自审结果";
    detailReviewList.appendChild(empty);
    return;
  }

  checks.slice(0, 12).forEach((check) => {
    const item = document.createElement("span");
    item.className = check.pass ? "review-chip pass" : "review-chip fail";
    item.textContent = `${check.pass ? "通过" : "失败"} ${check.name}`;
    detailReviewList.appendChild(item);
  });

  issues.slice(0, 8).forEach((issue) => {
    const item = document.createElement("div");
    item.className = `review-issue ${issue.severity || "info"}`;
    item.textContent = `${issue.severity || "info"} · ${issue.message || issue.type}`;
    detailReviewList.appendChild(item);
  });
}

function renderStageDetails(run) {
  const stages = run.stage_details || [];
  if (!stages.length) {
    detailStageGrid.textContent = "暂无阶段详情";
    return;
  }

  stages.forEach((stage) => {
    const card = document.createElement("article");
    card.className = "detail-stage-card";

    const header = document.createElement("header");
    const title = document.createElement("b");
    title.textContent = `${stage.name} ${stage.label || ""}`.trim();
    const status = document.createElement("span");
    status.className = `stage-pill ${stage.status}`;
    status.textContent = stage.status || "missing";
    header.appendChild(title);
    header.appendChild(status);

    const summary = document.createElement("p");
    summary.textContent = compactSummary(stage.summary || {});

    const actions = document.createElement("div");
    actions.className = "stage-actions";
    if (stage.manifest_url) {
      const link = document.createElement("a");
      link.className = "ghost-link";
      link.href = stage.manifest_url;
      link.target = "_blank";
      link.textContent = "Manifest";
      actions.appendChild(link);
    }
    if (stage.can_rerun) {
      const rerunButton = document.createElement("button");
      rerunButton.className = "small-button";
      rerunButton.type = "button";
      rerunButton.textContent = "重跑";
      rerunButton.addEventListener("click", () => rerunStage(stage.name, rerunButton));
      actions.appendChild(rerunButton);
    }

    const previews = document.createElement("div");
    previews.className = "stage-preview-list";
    Object.entries(stage.preview_urls || {}).forEach(([key, url]) => {
      const preview = document.createElement("a");
      preview.href = url;
      preview.target = "_blank";
      preview.textContent = key;
      previews.appendChild(preview);
    });

    card.appendChild(header);
    card.appendChild(summary);
    card.appendChild(actions);
    if (previews.children.length) card.appendChild(previews);
    detailStageGrid.appendChild(card);
  });
}

function compactSummary(summary) {
  const entries = Object.entries(summary).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!entries.length) return "暂无摘要";
  return entries
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : value}`)
    .join(" · ");
}

async function rerunStage(stageName, button) {
  if (!latestRun?.run_id) return;
  const previousText = button.textContent;
  button.disabled = true;
  button.textContent = "重跑中";
  statusTitle.textContent = `重跑阶段：${stageName}`;
  try {
    const response = await fetch("/api/rerun-stage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: latestRun.run_id, stage: stageName }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "阶段重跑失败");
    latestRun = data;
    statusTitle.textContent = `已重跑：${stageName}`;
    setStages("complete", data.stages || []);
    renderDebugImages(data.debug_images || {});
    renderAssetPanel(data.cutout_assets || [], data.styled_assets || data.generated_assets || []);
    renderCompositionEditor(data);
    renderRunDetails(data);
    resultImage.src = withCacheBust(data.final_image_url);
    resultImage.hidden = false;
    resultEmpty.hidden = true;
    await loadRunHistory();
  } catch (error) {
    statusTitle.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = previousText;
  }
}

function renderCompositionEditor(run) {
  compositionPlacements = [];
  compositionOverlay.innerHTML = "";
  compositionLayerList.innerHTML = "";
  const canvasUrl = run?.background_canvas_url || run?.base_image_url;
  if (!run || run.preserve_layout !== false || !canvasUrl) {
    compositionEditor.hidden = true;
    applyWorkspacePage();
    return;
  }

  const assets = run.styled_assets || run.generated_assets || [];
  const usableAssets = assets.filter((asset) => Array.isArray(asset.bbox) && asset.url);
  if (!usableAssets.length) {
    compositionEditor.hidden = true;
    applyWorkspacePage();
    return;
  }

  compositionBaseImage.src = withCacheBust(canvasUrl);
  compositionPlacements = usableAssets.map((asset, index) => ({
    asset_id: asset.asset_id,
    element_id: asset.element_id || asset.asset_id,
    url: asset.url,
    bbox: [...asset.bbox],
    z_index: index,
  }));
  compositionBaseImage.addEventListener("load", renderCompositionOverlay, { once: true });
  applyWorkspacePage();
  renderCompositionOverlay();
}

function renderCompositionOverlay() {
  compositionOverlay.innerHTML = "";
  const rect = compositionContentRect();
  if (!rect || !compositionPlacements.length) {
    renderCompositionLayerList();
    return;
  }
  [...compositionPlacements]
    .sort((a, b) => a.z_index - b.z_index)
    .forEach((placement) => {
      const element = document.createElement("div");
      element.className = "composition-asset";
      element.dataset.assetId = placement.asset_id;
      element.style.zIndex = String(placement.z_index + 1);

      const image = document.createElement("img");
      image.src = withCacheBust(placement.url);
      image.alt = placement.element_id;
      const label = document.createElement("b");
      label.textContent = placement.element_id;
      element.appendChild(image);
      element.appendChild(label);
      positionCompositionElement(element, placement.bbox, rect);
      element.addEventListener("pointerdown", (event) => startCompositionDrag(event, placement.asset_id));
      compositionOverlay.appendChild(element);
    });
  renderCompositionLayerList();
}

function compositionContentRect() {
  const surfaceRect = compositionSurface.getBoundingClientRect();
  const naturalWidth = compositionBaseImage.naturalWidth || 960;
  const naturalHeight = compositionBaseImage.naturalHeight || 540;
  if (!surfaceRect.width || !surfaceRect.height) return null;
  const surfaceRatio = surfaceRect.width / surfaceRect.height;
  const imageRatio = naturalWidth / naturalHeight;
  let width = surfaceRect.width;
  let height = surfaceRect.height;
  let left = 0;
  let top = 0;
  if (surfaceRatio > imageRatio) {
    width = surfaceRect.height * imageRatio;
    left = (surfaceRect.width - width) / 2;
  } else {
    height = surfaceRect.width / imageRatio;
    top = (surfaceRect.height - height) / 2;
  }
  return { left, top, width, height, imageWidth: naturalWidth, imageHeight: naturalHeight };
}

function positionCompositionElement(element, bbox, rect) {
  const [x1, y1, x2, y2] = bbox;
  Object.assign(element.style, {
    left: `${rect.left + (x1 / rect.imageWidth) * rect.width}px`,
    top: `${rect.top + (y1 / rect.imageHeight) * rect.height}px`,
    width: `${((x2 - x1) / rect.imageWidth) * rect.width}px`,
    height: `${((y2 - y1) / rect.imageHeight) * rect.height}px`,
  });
}

function startCompositionDrag(event, assetId) {
  const placement = compositionPlacements.find((item) => item.asset_id === assetId);
  const rect = compositionContentRect();
  if (!placement || !rect) return;
  event.preventDefault();
  const [x1, y1] = placement.bbox;
  activeCompositionDrag = {
    assetId,
    startX: event.clientX,
    startY: event.clientY,
    bbox: [...placement.bbox],
    originX: x1,
    originY: y1,
  };
  event.currentTarget.setPointerCapture(event.pointerId);
  event.currentTarget.classList.add("active");
  event.currentTarget.addEventListener("pointermove", moveCompositionDrag);
  event.currentTarget.addEventListener("pointerup", endCompositionDrag, { once: true });
  event.currentTarget.addEventListener("pointercancel", endCompositionDrag, { once: true });
}

function moveCompositionDrag(event) {
  if (!activeCompositionDrag) return;
  const rect = compositionContentRect();
  const placement = compositionPlacements.find((item) => item.asset_id === activeCompositionDrag.assetId);
  if (!rect || !placement) return;
  const dx = ((event.clientX - activeCompositionDrag.startX) / rect.width) * rect.imageWidth;
  const dy = ((event.clientY - activeCompositionDrag.startY) / rect.height) * rect.imageHeight;
  const boxWidth = activeCompositionDrag.bbox[2] - activeCompositionDrag.bbox[0];
  const boxHeight = activeCompositionDrag.bbox[3] - activeCompositionDrag.bbox[1];
  const nextX = clamp(Math.round(activeCompositionDrag.originX + dx), 0, rect.imageWidth - boxWidth);
  const nextY = clamp(Math.round(activeCompositionDrag.originY + dy), 0, rect.imageHeight - boxHeight);
  placement.bbox = [nextX, nextY, nextX + boxWidth, nextY + boxHeight];
  positionCompositionElement(event.currentTarget, placement.bbox, rect);
}

function endCompositionDrag(event) {
  if (event.currentTarget) {
    event.currentTarget.classList.remove("active");
    event.currentTarget.removeEventListener("pointermove", moveCompositionDrag);
  }
  activeCompositionDrag = null;
  renderCompositionLayerList();
}

function renderCompositionLayerList() {
  compositionLayerList.innerHTML = "";
  if (!compositionPlacements.length) {
    compositionLayerList.textContent = "不保持原布局时可调整素材位置和前后顺序";
    return;
  }
  [...compositionPlacements]
    .sort((a, b) => b.z_index - a.z_index)
    .forEach((placement) => {
      const row = document.createElement("div");
      row.className = "composition-layer-row";
      const title = document.createElement("b");
      title.textContent = placement.element_id;
      const forward = document.createElement("button");
      forward.className = "small-button";
      forward.type = "button";
      forward.textContent = "前移";
      forward.addEventListener("click", () => moveCompositionLayer(placement.asset_id, 1));
      const backward = document.createElement("button");
      backward.className = "small-button";
      backward.type = "button";
      backward.textContent = "后移";
      backward.addEventListener("click", () => moveCompositionLayer(placement.asset_id, -1));
      row.appendChild(title);
      row.appendChild(forward);
      row.appendChild(backward);
      compositionLayerList.appendChild(row);
    });
}

function moveCompositionLayer(assetId, delta) {
  normalizeCompositionOrder();
  const ordered = [...compositionPlacements].sort((a, b) => a.z_index - b.z_index);
  const currentIndex = ordered.findIndex((item) => item.asset_id === assetId);
  if (currentIndex < 0) return;
  const nextIndex = clamp(currentIndex + delta, 0, ordered.length - 1);
  if (nextIndex === currentIndex) return;
  [ordered[currentIndex], ordered[nextIndex]] = [ordered[nextIndex], ordered[currentIndex]];
  ordered.forEach((placement, index) => {
    placement.z_index = index;
  });
  compositionPlacements = ordered;
  renderCompositionOverlay();
}

function normalizeCompositionOrder() {
  compositionPlacements
    .sort((a, b) => a.z_index - b.z_index)
    .forEach((placement, index) => {
      placement.z_index = index;
    });
}

async function applyManualComposition() {
  if (!latestRun?.run_id || !compositionPlacements.length) return;
  applyCompositionButton.disabled = true;
  applyCompositionButton.textContent = "合成中";
  try {
    normalizeCompositionOrder();
    const response = await fetch("/api/recompose", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: latestRun.run_id,
        placements: compositionPlacements.map((placement) => ({
          asset_id: placement.asset_id,
          bbox: placement.bbox,
          z_index: placement.z_index,
        })),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "合成失败");
    latestRun.final_image_url = data.final_image_url;
    resultImage.src = withCacheBust(data.final_image_url);
    resultImage.hidden = false;
    resultEmpty.hidden = true;
    if (data.composition_preview_url && debugTargets.composition_preview) {
      debugTargets.composition_preview.img.src = withCacheBust(data.composition_preview_url);
      debugTargets.composition_preview.img.hidden = false;
      debugTargets.composition_preview.empty.hidden = true;
      debugTargets.composition_preview.link.href = data.composition_preview_url;
      debugTargets.composition_preview.link.hidden = false;
    }
    statusTitle.textContent = `已应用合成：${latestRun.run_id}`;
  } catch (error) {
    statusTitle.textContent = error.message;
  } finally {
    applyCompositionButton.disabled = false;
    applyCompositionButton.textContent = "应用合成";
  }
}

function resetDebugImages() {
  for (const target of Object.values(debugTargets)) {
    target.img.removeAttribute("src");
    target.img.hidden = true;
    target.empty.hidden = false;
    target.link.hidden = true;
  }
}

function setStages(className, stages = []) {
  const completed = new Set(stages.map((stage) => stage.name));
  [...stageList.children].forEach((item) => {
    item.className = "";
    if (className === "complete") {
      if (completed.has(item.dataset.stage)) {
        item.classList.add("complete");
      }
    } else if (className) {
      item.classList.add(className);
    }
  });
}

function valueOf(selector) {
  return document.querySelector(selector).value.trim();
}

async function filePayload(file) {
  return {
    name: file.name,
    type: file.type,
    dataUrl: await fileToDataUrl(file),
  };
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function withCacheBust(url) {
  return `${url}?t=${Date.now()}`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
