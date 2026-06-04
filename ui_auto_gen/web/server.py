from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import shutil
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from ui_auto_gen.pipeline import PipelineRunner
from ui_auto_gen.paths import repo_root
from ui_auto_gen.utils import utc_now_iso, write_json


STATIC_ROOT = Path(__file__).resolve().parent / "static"
REPO_ROOT = repo_root()
SAVED_ROOT = REPO_ROOT / "workspace" / "saved_outputs"
RUN_HISTORY_LIMIT = 60


class UiServer:
    def __init__(self, host: str, port: int, output_root: Path | None = None) -> None:
        self.host = host
        self.port = port
        self.output_root = output_root or REPO_ROOT / "runs"

    def serve(self) -> None:
        handler = self._handler()
        server = ThreadingHTTPServer((self.host, self.port), handler)
        print(f"UI server running at http://{self.host}:{self.port}")
        print("Press Ctrl+C to stop.")
        server.serve_forever()

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        output_root = self.output_root.resolve()

        class RequestHandler(BaseHTTPRequestHandler):
            server_version = "UiAutoGen/0.1"

            def do_GET(self) -> None:
                if self.path in {"/", "/index.html"}:
                    self._serve_static(STATIC_ROOT / "index.html")
                    return
                if self.path.startswith("/static/"):
                    relative = self.path.removeprefix("/static/").split("?", 1)[0]
                    self._serve_static(STATIC_ROOT / unquote(relative))
                    return
                if self.path.startswith("/artifacts/"):
                    self._serve_artifact(output_root)
                    return
                if self.path.startswith("/saved/"):
                    self._serve_saved()
                    return
                if self.path == "/api/runs":
                    self._send_json({"runs": _list_runs(output_root)}, HTTPStatus.OK)
                    return
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                if self.path == "/api/run":
                    self._handle_run(output_root)
                    return
                if self.path == "/api/save-artifact":
                    self._handle_save_artifact(output_root)
                    return
                if self.path == "/api/delete-run":
                    self._handle_delete_run(output_root)
                    return
                if self.path == "/api/clear-runs":
                    deleted = _clear_runs(output_root)
                    self._send_json({"deleted": deleted, "runs": []}, HTTPStatus.OK)
                    return
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

            def do_DELETE(self) -> None:
                if self.path == "/api/runs":
                    deleted = _clear_runs(output_root)
                    self._send_json({"deleted": deleted, "runs": []}, HTTPStatus.OK)
                    return
                if self.path.startswith("/api/runs/"):
                    run_id = unquote(self.path.removeprefix("/api/runs/").split("?", 1)[0])
                    deleted = _delete_run(output_root, run_id)
                    self._send_json({"deleted": deleted, "runs": _list_runs(output_root)}, HTTPStatus.OK)
                    return
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

            def log_message(self, format: str, *args: Any) -> None:
                print(f"{self.address_string()} - {format % args}")

            def _handle_run(self, output_root: Path) -> None:
                try:
                    payload = self._read_json_body()
                    config_path = _create_job_config(payload)
                    runner = PipelineRunner(output_root=output_root)
                    context, results = runner.run(config_path=config_path)
                    export_artifacts = results[-1].artifacts
                    final_image = Path(export_artifacts["final_image"])
                    summary = Path(export_artifacts["summary"])
                    response = {
                        "run_id": context.run_id,
                        "run_root": str(context.run_root),
                        "summary_path": str(summary),
                        "summary_url": _artifact_url(output_root, summary),
                        "final_image_path": str(final_image),
                        "final_image_url": _artifact_url(output_root, final_image),
                        "debug_images": _collect_debug_images(output_root, results),
                        "cutout_assets": _collect_cutout_assets(output_root, context.run_root),
                        "styled_assets": _collect_styled_assets(output_root, context.run_root),
                        "stages": [
                            {
                                "name": result.stage,
                                "status": result.status,
                                "notes": result.notes,
                                "artifacts": result.artifacts,
                                "artifact_urls": _artifact_urls(output_root, result.artifacts),
                            }
                            for result in results
                        ],
                    }
                    self._send_json(response, HTTPStatus.OK)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

            def _handle_save_artifact(self, output_root: Path) -> None:
                try:
                    payload = self._read_json_body()
                    saved = _save_artifact(output_root, payload)
                    self._send_json(saved, HTTPStatus.OK)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

            def _handle_delete_run(self, output_root: Path) -> None:
                try:
                    payload = self._read_json_body()
                    run_id = str(payload.get("run_id") or "")
                    deleted = _delete_run(output_root, run_id)
                    self._send_json({"deleted": deleted, "runs": _list_runs(output_root)}, HTTPStatus.OK)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

            def _read_json_body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                return json.loads(raw.decode("utf-8"))

            def _serve_static(self, path: Path) -> None:
                resolved = path.resolve()
                if not _is_relative_to(resolved, STATIC_ROOT.resolve()) or not resolved.exists() or not resolved.is_file():
                    self._send_json({"error": "Static file not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_file(resolved)

            def _serve_artifact(self, output_root: Path) -> None:
                relative = unquote(self.path.removeprefix("/artifacts/").split("?", 1)[0])
                path = (output_root / relative).resolve()
                if not _is_relative_to(path, output_root) or not path.exists() or not path.is_file():
                    self._send_json({"error": "Artifact not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_file(path)

            def _serve_saved(self) -> None:
                relative = unquote(self.path.removeprefix("/saved/").split("?", 1)[0])
                saved_root = SAVED_ROOT.resolve()
                path = (saved_root / relative).resolve()
                if not _is_relative_to(path, saved_root) or not path.exists() or not path.is_file():
                    self._send_json({"error": "Saved file not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_file(path)

            def _send_file(self, path: Path) -> None:
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                data = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _send_json(self, data: dict[str, Any], status: HTTPStatus) -> None:
                raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

        return RequestHandler


def _create_job_config(payload: dict[str, Any]) -> Path:
    now = utc_now_iso()
    safe_timestamp = now.replace(":", "").replace("-", "").split(".")[0]
    job_root = REPO_ROOT / "workspace" / "ui_jobs" / f"job_{safe_timestamp}"
    input_root = job_root / "inputs"
    input_root.mkdir(parents=True, exist_ok=True)

    base_image_path = _resolve_base_image(payload, input_root)
    reference_image_path = _save_data_url(payload.get("referenceImage"), input_root, "reference_image")
    manual_regions = _manual_regions_from_payload(payload)
    target_elements = _target_elements_from_payload(payload, manual_regions)
    algorithms = payload.get("algorithms", {})

    config = {
        "schema_version": "1.0",
        "project_name": payload.get("projectName") or "ui_web_job",
        "base_image": str(base_image_path),
        "prompt": payload.get("prompt", ""),
        "positive_rules": payload.get("positiveRules", ""),
        "negative_rules": payload.get("negativeRules", ""),
        "reference_image": str(reference_image_path) if reference_image_path else None,
        "manual_regions": manual_regions,
        "target_elements": target_elements,
        "algorithms": {
            "detector": algorithms.get("detector", "placeholder_detector"),
            "segmenter": algorithms.get("segmenter", "placeholder_segmenter"),
            "ocr": algorithms.get("ocr", "placeholder_ocr"),
            "style": algorithms.get("style", "placeholder_style_adapter"),
            "review": algorithms.get("review", "contract_review"),
        },
        "global_style": {
            "description": payload.get("prompt", ""),
            "positive_rules": payload.get("positiveRules", ""),
            "negative_rules": payload.get("negativeRules", ""),
            "reference_image": str(reference_image_path) if reference_image_path else None,
            "palette": payload.get("palette", []),
        },
        "output": {
            "formats": ["image", "json"],
            "preserve_layout": bool(payload.get("preserveLayout", True)),
        },
    }

    config_path = job_root / "job_config.json"
    write_json(config_path, config)
    return config_path


def _resolve_base_image(payload: dict[str, Any], input_root: Path) -> Path:
    mode = payload.get("baseMode", "sample")
    if mode == "upload":
        saved = _save_data_url(payload.get("baseImage"), input_root, "base_image")
        if saved:
            return saved
        raise ValueError("Base image upload mode requires a base image.")
    if mode == "text":
        prompt = payload.get("prompt", "Generated UI concept")
        return _write_text_to_image_placeholder(prompt, input_root / "generated_base.svg")
    return REPO_ROOT / "examples" / "base_placeholder.svg"


def _target_elements_from_payload(payload: dict[str, Any], manual_regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if manual_regions:
        return [
            {
                "id": region["id"],
                "name": region["name"],
                "type_hint": region.get("type_hint", "manual"),
                "action": "replace_style",
                "style": payload.get("prompt", ""),
                "keep_text": bool(payload.get("keepText", True)),
            }
            for region in manual_regions
        ]

    hints = payload.get("elementHints", "")
    names = [item.strip() for item in hints.replace(",", "\n").splitlines() if item.strip()]
    if not names:
        names = ["requested UI elements"]

    return [
        {
            "id": _safe_id(name, index),
            "name": name,
            "type_hint": "auto",
            "action": "replace_style",
            "style": payload.get("prompt", ""),
            "keep_text": bool(payload.get("keepText", True)),
        }
        for index, name in enumerate(names, start=1)
    ]


def _manual_regions_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_regions = payload.get("manualRegions", [])
    if not isinstance(raw_regions, list):
        return []

    regions = []
    for index, region in enumerate(raw_regions, start=1):
        if not isinstance(region, dict):
            continue
        bbox_norm = region.get("bbox_norm")
        if not isinstance(bbox_norm, list) or len(bbox_norm) != 4:
            continue
        x1, y1, x2, y2 = _normalize_bbox_norm(bbox_norm)
        if x2 - x1 < 0.005 or y2 - y1 < 0.005:
            continue
        name = str(region.get("name") or f"manual region {index}").strip()
        region_id = _safe_id(str(region.get("id") or name), index)
        regions.append(
            {
                "id": region_id,
                "name": name,
                "type_hint": str(region.get("type_hint") or "manual"),
                "bbox_norm": [x1, y1, x2, y2],
                "source": "manual_selection",
            }
        )
    return regions


def _normalize_bbox_norm(values: list[Any]) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = [max(0.0, min(1.0, float(value))) for value in values]
    left, right = sorted([x1, x2])
    top, bottom = sorted([y1, y2])
    return left, top, right, bottom


def _save_data_url(value: Any, input_root: Path, stem: str) -> Path | None:
    if not value:
        return None
    if not isinstance(value, dict):
        return None
    data_url = value.get("dataUrl")
    name = value.get("name") or stem
    if not data_url or "," not in data_url:
        return None

    metadata, encoded = data_url.split(",", 1)
    extension = _extension_from_data_url(metadata, name)
    path = input_root / f"{stem}{extension}"
    path.write_bytes(base64.b64decode(encoded))
    return path


def _extension_from_data_url(metadata: str, name: str) -> str:
    suffix = Path(name).suffix
    if suffix:
        return suffix.lower()
    if "image/png" in metadata:
        return ".png"
    if "image/jpeg" in metadata:
        return ".jpg"
    if "image/svg+xml" in metadata:
        return ".svg"
    return ".img"


def _write_text_to_image_placeholder(prompt: str, path: Path) -> Path:
    safe_prompt = html.escape(prompt[:180] or "Generated UI concept")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
  <rect width="960" height="540" fill="#eef2f7"/>
  <rect x="56" y="48" width="848" height="444" rx="24" fill="#ffffff"/>
  <rect x="96" y="96" width="360" height="36" rx="10" fill="#dbeafe"/>
  <rect x="96" y="168" width="768" height="86" rx="18" fill="#f8fafc"/>
  <rect x="96" y="286" width="360" height="148" rx="18" fill="#f1f5f9"/>
  <rect x="504" y="286" width="360" height="148" rx="18" fill="#f1f5f9"/>
  <text x="96" y="132" font-family="Arial" font-size="22" fill="#1f2937">{safe_prompt}</text>
  <text x="96" y="220" font-family="Arial" font-size="18" fill="#64748b">Text-to-image placeholder. Replace this with a real generation adapter later.</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    return path


def _safe_id(name: str, index: int) -> str:
    safe = "".join(char.lower() if char.isalnum() else "_" for char in name).strip("_")
    return safe or f"element_{index:03d}"


def _artifact_url(output_root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(output_root.resolve()).as_posix()
    return f"/artifacts/{relative}"


def _artifact_urls(output_root: Path, artifacts: dict[str, str]) -> dict[str, str]:
    urls = {}
    for key, value in artifacts.items():
        path = Path(value)
        if path.exists() and path.is_file() and _is_relative_to(path.resolve(), output_root.resolve()):
            urls[key] = _artifact_url(output_root, path)
    return urls


def _collect_debug_images(output_root: Path, results: list[Any]) -> dict[str, str]:
    debug_images = {}
    debug_keys = {
        "detection_preview",
        "text_protect_preview",
        "mask_preview",
        "cutout_preview",
        "background_repair_preview",
        "style_preview",
        "composition_preview",
    }
    for result in results:
        for key, value in result.artifacts.items():
            if key in debug_keys:
                path = Path(value)
                if path.exists() and path.is_file() and _is_relative_to(path.resolve(), output_root.resolve()):
                    debug_images[key] = _artifact_url(output_root, path)
    return debug_images


def _collect_cutout_assets(output_root: Path, run_root: Path) -> list[dict[str, Any]]:
    cutout_manifest_path = run_root / "04_cutout" / "cutout_manifest.json"
    if not cutout_manifest_path.exists():
        return []

    try:
        cutout_manifest = json.loads(cutout_manifest_path.read_text(encoding="utf-8"))
        segmentation_manifest = _read_json_if_exists(run_root / "03_segment" / "segmentation_manifest.json")
        detection_manifest = _read_json_if_exists(run_root / "02_detect" / "detection_manifest.json")
    except json.JSONDecodeError:
        return []

    mask_to_detection = {
        mask.get("mask_id"): mask.get("detection_id")
        for mask in segmentation_manifest.get("masks", [])
    }
    detection_to_element = {
        detection.get("detection_id"): detection.get("element_id")
        for detection in detection_manifest.get("detections", [])
    }
    assets = []
    for cutout in cutout_manifest.get("cutouts", []):
        asset_path = Path(str(cutout.get("alpha_asset_path") or ""))
        if not asset_path.exists() or not asset_path.is_file():
            continue
        resolved = asset_path.resolve()
        if not _is_relative_to(resolved, output_root.resolve()):
            continue
        assets.append(
            {
                "asset_id": cutout.get("cutout_id"),
                "element_id": detection_to_element.get(mask_to_detection.get(cutout.get("mask_id"))),
                "source": cutout.get("source") or "cutout",
                "path": str(resolved),
                "url": _artifact_url(output_root, resolved),
            }
        )
    return assets


def _collect_styled_assets(output_root: Path, run_root: Path) -> list[dict[str, Any]]:
    style_manifest_path = run_root / "05_style" / "style_manifest.json"
    if not style_manifest_path.exists():
        return []

    try:
        style_manifest = json.loads(style_manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    assets = []
    for asset in style_manifest.get("styled_assets", []):
        asset_path = Path(str(asset.get("generated_asset_path") or ""))
        if not asset_path.exists() or not asset_path.is_file():
            continue
        resolved = asset_path.resolve()
        if not _is_relative_to(resolved, output_root.resolve()):
            continue
        assets.append(
            {
                "asset_id": asset.get("asset_id"),
                "element_id": asset.get("element_id"),
                "source": asset.get("source"),
                "path": str(resolved),
                "url": _artifact_url(output_root, resolved),
            }
        )
    return assets


def _list_runs(output_root: Path) -> list[dict[str, Any]]:
    root = output_root.resolve()
    if not root.exists():
        return []

    run_roots = [path for path in root.iterdir() if path.is_dir()]
    run_roots.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    runs = []
    for run_root in run_roots[:RUN_HISTORY_LIMIT]:
        summary_path = run_root / "08_export" / "run_summary.json"
        manifest_path = run_root / "manifest.json"
        summary = _read_json_if_exists(summary_path)
        manifest = _read_json_if_exists(manifest_path)
        raw_final_image = str(summary.get("final_image") or "")
        final_image = Path(raw_final_image) if raw_final_image else None
        final_image_url = (
            _artifact_url(root, final_image)
            if final_image and final_image.exists() and _is_relative_to(final_image.resolve(), root)
            else None
        )
        runs.append(
            {
                "run_id": summary.get("run_id") or manifest.get("run_id") or run_root.name,
                "project_name": summary.get("project_name") or manifest.get("project_name"),
                "created_at": manifest.get("created_at"),
                "completed_at": manifest.get("completed_at"),
                "status": "failed" if manifest.get("failed_at") else ("completed" if summary else "partial"),
                "summary_path": str(summary_path) if summary_path.exists() else None,
                "summary_url": _artifact_url(root, summary_path) if summary_path.exists() else None,
                "final_image_path": str(final_image) if final_image and final_image.exists() else None,
                "final_image_url": final_image_url,
                "cutout_assets": _collect_cutout_assets(root, run_root),
                "styled_assets": _collect_styled_assets(root, run_root),
                "mtime": run_root.stat().st_mtime,
            }
        )

    for run in runs:
        run.pop("mtime", None)
    return runs


def _clear_runs(output_root: Path) -> list[str]:
    root = output_root.resolve()
    if not root.exists():
        return []
    deleted = []
    for child in root.iterdir():
        resolved = child.resolve()
        if not _is_relative_to(resolved, root) or resolved == root:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        deleted.append(child.name)
    return deleted


def _delete_run(output_root: Path, run_id: str) -> str:
    root = output_root.resolve()
    if not run_id or "/" in run_id or "\\" in run_id:
        raise ValueError("Invalid run id.")
    target = (root / run_id).resolve()
    if not _is_relative_to(target, root) or target == root or not target.exists():
        raise ValueError("Run cache does not exist.")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return run_id


def _save_artifact(output_root: Path, payload: dict[str, Any]) -> dict[str, str]:
    source = _artifact_path_from_payload(output_root, payload)
    if not source.exists() or not source.is_file():
        raise ValueError("Artifact file does not exist.")

    label = _safe_filename(str(payload.get("label") or source.stem))
    extension = source.suffix.lower() or ".png"
    safe_timestamp = utc_now_iso().replace(":", "").replace("-", "").split(".")[0]
    destination = SAVED_ROOT / f"{safe_timestamp}_{label}{extension}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "saved_path": str(destination),
        "saved_url": _saved_url(destination),
    }


def _artifact_path_from_payload(output_root: Path, payload: dict[str, Any]) -> Path:
    root = output_root.resolve()
    raw_url = str(payload.get("url") or "")
    raw_path = str(payload.get("path") or "")
    if raw_url.startswith("/artifacts/"):
        relative = unquote(raw_url.removeprefix("/artifacts/").split("?", 1)[0])
        source = (root / relative).resolve()
    elif raw_path:
        source = Path(raw_path).resolve()
    else:
        raise ValueError("Save request requires an artifact URL or path.")

    if not _is_relative_to(source, root):
        raise ValueError("Only run artifacts can be saved.")
    return source


def _safe_filename(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
    return safe or "artifact"


def _saved_url(path: Path) -> str:
    relative = path.resolve().relative_to(SAVED_ROOT.resolve()).as_posix()
    return f"/saved/{relative}"


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local UI for the automated UI image pipeline.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    output_root = Path(args.output_root).resolve() if args.output_root else None
    UiServer(host=args.host, port=args.port, output_root=output_root).serve()


if __name__ == "__main__":
    main()
