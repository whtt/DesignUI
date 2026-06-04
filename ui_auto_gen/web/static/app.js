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
const baseImageInput = document.querySelector("#baseImage");
const referenceImageInput = document.querySelector("#referenceImage");
const basePreview = document.querySelector("#basePreview");
const selectionSurface = document.querySelector("#selectionSurface");
const selectionOverlay = document.querySelector("#selectionOverlay");
const manualRegionList = document.querySelector("#manualRegionList");
const clearManualRegionsButton = document.querySelector("#clearManualRegions");
let referencePreview = document.querySelector("#referencePreview");
let latestRun = null;
let manualRegions = [];
let activeSelection = null;

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
window.addEventListener("resize", renderManualRegions);

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
    preserveLayout: document.querySelector("#preserveLayout").checked,
    keepText: document.querySelector("#keepText").checked,
    algorithms: {
      detector: valueOf("#detector"),
      segmenter: valueOf("#segmenter"),
      ocr: valueOf("#ocr"),
      style: valueOf("#style"),
      review: valueOf("#review"),
    },
  };
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
  placeholderGuide.hidden = !visible;
  debugGallery.hidden = !visible;
  assetPanel.hidden = !visible;
}

function renderAssetPanel(cutoutAssets, styledAssets) {
  renderAssetList(cutoutAssetList, cutoutAssets, "暂无抠图素材");
  renderAssetList(styleAssetList, styledAssets, "暂无风格素材");
  assetPanel.hidden = !cutoutAssets.length && !styledAssets.length;
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
    card.appendChild(image);
    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(actions);
    container.appendChild(card);
  });
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

function restoreRunPreview(run) {
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
  renderAssetPanel(run.cutout_assets || [], run.styled_assets || run.generated_assets || []);
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
