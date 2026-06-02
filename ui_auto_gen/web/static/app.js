const runButton = document.querySelector("#runButton");
const statusTitle = document.querySelector("#statusTitle");
const stageList = document.querySelector("#stageList");
const resultImage = document.querySelector("#resultImage");
const resultEmpty = document.querySelector("#resultEmpty");
const summaryLink = document.querySelector("#summaryLink");
const baseImageInput = document.querySelector("#baseImage");
const referenceImageInput = document.querySelector("#referenceImage");
const basePreview = document.querySelector("#basePreview");
const stageDetailText = document.querySelector("#stageDetailText");
let referencePreview = document.querySelector("#referencePreview");
let latestRun = null;

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
  cutout_preview: {
    img: document.querySelector("#cutoutPreview"),
    empty: document.querySelector("#cutoutPreviewEmpty"),
    link: document.querySelector("#cutoutPreviewLink"),
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

stageList.addEventListener("click", (event) => {
  const item = event.target.closest("li");
  if (!item || !latestRun) return;
  const stage = latestRun.stages.find((candidate) => candidate.name === item.dataset.stage);
  if (!stage) return;
  [...stageList.children].forEach((child) => child.classList.remove("selected"));
  item.classList.add("selected");
  renderStageDetail(stage);
});

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  statusTitle.textContent = "运行中";
  summaryLink.hidden = true;
  resultImage.hidden = true;
  resultEmpty.hidden = false;
  latestRun = null;
  stageDetailText.textContent = "运行中...";
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
    renderStageDetail(data.stages[0]);
  } catch (error) {
    statusTitle.textContent = error.message;
    stageDetailText.textContent = error.stack || error.message;
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

function renderStageDetail(stage) {
  if (!stage) {
    stageDetailText.textContent = "暂无运行详情";
    return;
  }
  const artifactLines = Object.entries(stage.artifacts || {}).map(([key, value]) => {
    const url = stage.artifact_urls?.[key];
    return url ? `${key}: ${value}\n  url: ${url}` : `${key}: ${value}`;
  });
  stageDetailText.textContent = [
    `stage: ${stage.name}`,
    `status: ${stage.status}`,
    "",
    "notes:",
    ...(stage.notes || []).map((note) => `- ${note}`),
    "",
    "artifacts:",
    ...(artifactLines.length ? artifactLines.map((line) => `- ${line}`) : ["- none"]),
  ].join("\n");
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
