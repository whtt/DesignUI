const runButton = document.querySelector("#runButton");
const statusTitle = document.querySelector("#statusTitle");
const stageList = document.querySelector("#stageList");
const resultImage = document.querySelector("#resultImage");
const resultEmpty = document.querySelector("#resultEmpty");
const summaryLink = document.querySelector("#summaryLink");
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

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  statusTitle.textContent = "运行中";
  summaryLink.hidden = true;
  resultImage.hidden = true;
  resultEmpty.hidden = false;
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
    renderDebugImages(data.debug_images || {});
    resultImage.src = withCacheBust(data.final_image_url);
    resultImage.hidden = false;
    resultEmpty.hidden = true;
    summaryLink.href = data.summary_url;
    summaryLink.hidden = false;
  } catch (error) {
    statusTitle.textContent = error.message;
    setStages("");
  } finally {
    runButton.disabled = false;
  }
});

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
