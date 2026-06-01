const form = document.querySelector("#jobForm");
const runButton = document.querySelector("#runButton");
const statusTitle = document.querySelector("#statusTitle");
const stageList = document.querySelector("#stageList");
const resultImage = document.querySelector("#resultImage");
const resultEmpty = document.querySelector("#resultEmpty");
const summaryLink = document.querySelector("#summaryLink");
const baseImageInput = document.querySelector("#baseImage");
const referenceImageInput = document.querySelector("#referenceImage");
const basePreview = document.querySelector("#basePreview");
let referencePreview = document.querySelector("#referencePreview");

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

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  statusTitle.textContent = "运行中";
  summaryLink.hidden = true;
  resultImage.hidden = true;
  resultEmpty.hidden = false;
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

    statusTitle.textContent = `完成：${data.run_id}`;
    setStages("complete", data.stages);
    resultImage.src = `${data.final_image_url}?t=${Date.now()}`;
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

function setStages(className, stages = []) {
  const completed = new Set(stages.map((stage) => stage.name));
  [...stageList.children].forEach((item) => {
    item.className = "";
    if (className === "complete") {
      const prefix = item.textContent.slice(0, 2);
      if ([...completed].some((name) => name.startsWith(prefix))) {
        item.classList.add("complete");
      }
    } else if (className) {
      item.classList.add(className);
    }
  });
}
