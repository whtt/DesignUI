# Data Contracts

All contracts include a `schema_version` field. Breaking changes should increment the major version.

## Job Config

```json
{
  "schema_version": "1.0",
  "project_name": "sample_dashboard_restyle",
  "base_image": "examples/base_placeholder.svg",
  "target_elements": [
    {
      "id": "primary_buttons",
      "name": "primary buttons",
      "type_hint": "button",
      "action": "replace_style",
      "style": "glassmorphism blue accent",
      "keep_text": true
    }
  ],
  "global_style": {
    "description": "quiet enterprise dashboard",
    "palette": ["#111827", "#2563EB", "#22C55E"],
    "corner_radius": 10
  },
  "prompt": "Restyle the UI as a quiet enterprise dashboard.",
  "positive_rules": "Keep layout and text clear.",
  "negative_rules": "No blurry text or broken spacing.",
  "reference_image": "workspace/ui_jobs/job_x/inputs/reference_image.png",
  "manual_regions": [
    {
      "id": "manual_001",
      "name": "primary button",
      "type_hint": "button",
      "bbox_norm": [0.12, 0.18, 0.34, 0.28],
      "source": "manual_selection"
    }
  ],
  "algorithms": {
    "detector": "placeholder_detector",
    "segmenter": "placeholder_segmenter",
    "ocr": "placeholder_ocr",
    "style": "placeholder_style_adapter",
    "review": "contract_review"
  },
  "output": {
    "formats": ["image", "json"],
    "preserve_layout": true
  }
}
```

## Ingest Manifest

```json
{
  "schema_version": "1.0",
  "base_image": {
    "source_path": "...",
    "run_path": "...",
    "width": 1280,
    "height": 720,
    "format": "svg"
  }
}
```

## Plan Manifest

```json
{
  "schema_version": "1.0",
  "prompt": "Restyle the UI as a quiet enterprise dashboard.",
  "positive_rules": "Keep layout and text clear.",
  "negative_rules": "No blurry text or broken spacing.",
  "reference_image": "workspace/ui_jobs/job_x/inputs/reference_image.png",
  "algorithms": {
    "detector": "placeholder_detector",
    "segmenter": "placeholder_segmenter",
    "ocr": "placeholder_ocr",
    "style": "placeholder_style_adapter",
    "review": "contract_review"
  },
  "elements": [
    {
      "element_id": "primary_buttons",
      "name": "primary buttons",
      "type_hint": "button",
      "action": "replace_style",
      "style": "glassmorphism blue accent",
      "keep_text": true,
      "constraints": {
        "preserve_layout": true
      }
    }
  ],
  "global_style": {}
}
```

## Detection Manifest

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "yolo26",
  "actual_adapter": "placeholder_detector",
  "manual_regions_used": true,
  "model": null,
  "fallback": null,
  "debug_artifacts": {
    "detection_preview": "02_detect/detection_preview.png"
  },
  "detections": [
    {
      "detection_id": "det_primary_buttons_001",
      "element_id": "primary_buttons",
      "label": "button",
      "bbox": [64, 64, 256, 128],
      "confidence": 0.5,
      "source": "manual_selection"
    }
  ]
}
```

`bbox` uses `[x1, y1, x2, y2]` pixel coordinates in the ingested base image coordinate system.

When lightweight detection runs successfully, `actual_adapter` becomes `lightweight_detector`, `model` records the local region-proposal metadata, and detections include proposal diagnostics:

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "lightweight_detector",
  "actual_adapter": "lightweight_detector",
  "manual_regions_used": false,
  "model": {
    "model_family": "classical_region_proposal",
    "model_size": "tiny",
    "engine": "pillow_connected_components",
    "max_dimension": 720,
    "min_area_ratio": 0.0025
  },
  "fallback": null,
  "detections": [
    {
      "detection_id": "det_primary_button_001",
      "element_id": "primary_button",
      "label": "button",
      "bbox": [64, 320, 624, 480],
      "confidence": 0.7957,
      "source": "lightweight_detector",
      "proposal": {
        "area_ratio": 0.17284,
        "edge_density": 0.0
      }
    }
  ]
}
```

When lightweight detection cannot find candidates, `actual_adapter` becomes `placeholder_detector` and `fallback` records `requested_adapter`, `fallback_adapter`, and `reason`.

## Text Protect Manifest

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "placeholder_ocr",
  "actual_adapter": "placeholder_ocr_protector",
  "model": null,
  "fallback": null,
  "debug_artifacts": {
    "text_protect_preview": "02_ocr_protect/text_protect_preview.png"
  },
  "text_regions": [
    {
      "region_id": "text_det_primary_buttons_001_001",
      "detection_id": "det_primary_buttons_001",
      "element_id": "primary_buttons",
      "region_path": "02_ocr_protect/text_regions/text_det_primary_buttons_001_001.json",
      "bbox": [80, 80, 220, 104],
      "text": null,
      "confidence": 0.0,
      "source": "placeholder_ocr_protector",
      "placeholder_visual": "ocr_lock_tint",
      "future_adapter": "paddleocr_doctr_or_vlm_ocr"
    }
  ]
}
```

When RapidOCR runs successfully, `actual_adapter` becomes `rapidocr_protector`, `model` records the RapidOCR/ONNX Runtime metadata, and `text_regions` include real OCR fields:

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "rapidocr",
  "actual_adapter": "rapidocr_protector",
  "model": {
    "model_family": "rapidocr",
    "engine": "onnxruntime",
    "min_confidence": 0.45,
    "elapsed_seconds": 2.016
  },
  "fallback": null,
  "text_regions": [
    {
      "region_id": "ocr_001",
      "detection_id": "det_primary_button_001",
      "element_id": "primary_button",
      "region_path": "02_ocr_protect/text_regions/ocr_001.json",
      "bbox": [21, 22, 182, 41],
      "polygon": [[21.0, 22.0], [182.0, 22.0], [182.0, 41.0], [21.0, 41.0]],
      "text": "Submit",
      "confidence": 0.98,
      "source": "rapidocr_protector",
      "model": {
        "model_family": "rapidocr",
        "engine": "onnxruntime"
      }
    }
  ]
}
```

When RapidOCR cannot run, `actual_adapter` becomes `placeholder_ocr_protector` and `fallback` records `requested_adapter`, `fallback_adapter`, and `reason`.

## Segmentation Manifest

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "sam2",
  "actual_adapter": "sam2_tiny_segmenter",
  "model": {
    "model_family": "sam2",
    "model_size": "tiny",
    "checkpoint": "models/sam2/sam2.1_hiera_tiny.pt",
    "model_cfg": "configs/sam2.1/sam2.1_hiera_t.yaml",
    "device": "cpu"
  },
  "fallback": null,
  "debug_artifacts": {
    "mask_preview": "03_segment/mask_preview.png"
  },
  "masks": [
    {
      "mask_id": "mask_det_primary_buttons_001",
      "detection_id": "det_primary_buttons_001",
      "mask_path": "03_segment/masks/mask_det_primary_buttons_001.json",
      "mask_png_path": "03_segment/masks/mask_det_primary_buttons_001.png",
      "bbox": [64, 64, 256, 128],
      "confidence": 0.91,
      "source": "sam2_tiny_segmenter",
      "model": {
        "model_family": "sam2",
        "model_size": "tiny"
      }
    }
  ]
}
```

`placeholder_visual` describes how the current non-model output is made visible in previews. `future_adapter` names the adapter family expected to replace the placeholder.

When SAM2 cannot run, `actual_adapter` becomes `placeholder_segmenter` and `fallback` records `requested_adapter`, `fallback_adapter`, and `reason`.

## Style Manifest

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "controlnet_ipadapter",
  "actual_adapter": "placeholder_style_adapter",
  "model": null,
  "fallback": null,
  "debug_artifacts": {
    "style_preview": "05_style/style_preview.png"
  },
  "styled_assets": [
    {
      "asset_id": "styled_cutout_mask_det_primary_buttons_001",
      "element_id": "primary_buttons",
      "cutout_id": "cutout_mask_det_primary_buttons_001",
      "asset_path": "05_style/styled_assets/styled_cutout_mask_det_primary_buttons_001.json",
      "generated_asset_path": "05_style/styled_assets/styled_cutout_mask_det_primary_buttons_001.png",
      "bbox": [64, 64, 256, 128],
      "source": "placeholder_style_adapter",
      "placeholder_visual": "emoji_style_transfer",
      "future_adapter": "style_transfer_or_parameterized_renderer"
    }
  ]
}
```

When lightweight style transfer runs successfully, `actual_adapter` becomes `lightweight_style_transfer_adapter`, `model` records the local transfer metadata, and styled assets point to real color-transferred cutout PNG files:

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "lightweight_style_transfer",
  "actual_adapter": "lightweight_style_transfer_adapter",
  "model": {
    "model_family": "classical_color_transfer",
    "model_size": "tiny",
    "engine": "pillow",
    "strength": 0.72,
    "style_source": "global_style.palette"
  },
  "fallback": null,
  "debug_artifacts": {
    "style_preview": "05_style/style_preview.png"
  },
  "styled_assets": [
    {
      "asset_id": "styled_cutout_mask_det_primary_buttons_001",
      "element_id": "primary_buttons",
      "cutout_id": "cutout_mask_det_primary_buttons_001",
      "asset_path": "05_style/styled_assets/styled_cutout_mask_det_primary_buttons_001.json",
      "generated_asset_path": "05_style/styled_assets/styled_cutout_mask_det_primary_buttons_001.png",
      "bbox": [64, 64, 256, 128],
      "source": "lightweight_style_transfer_adapter",
      "model": {
        "model_family": "classical_color_transfer",
        "engine": "pillow"
      }
    }
  ]
}
```

When lightweight style transfer cannot run, `actual_adapter` becomes `placeholder_style_adapter` and `fallback` records `requested_adapter`, `fallback_adapter`, and `reason`.

## Cutout Manifest

```json
{
  "schema_version": "1.0",
  "debug_artifacts": {
    "cutout_preview": "04_cutout/cutout_preview.png"
  },
  "cutouts": [
    {
      "cutout_id": "cutout_mask_det_primary_buttons_001",
      "mask_id": "mask_det_primary_buttons_001",
      "cutout_path": "04_cutout/cutouts/cutout_mask_det_primary_buttons_001.json",
      "mask_png_path": "03_segment/masks/mask_det_primary_buttons_001.png",
      "alpha_asset_path": "04_cutout/cutouts/cutout_mask_det_primary_buttons_001.png",
      "bbox": [64, 64, 256, 128],
      "source": "raster_cutout"
    }
  ]
}
```

## Background Repair Manifest

```json
{
  "schema_version": "1.0",
  "actual_adapter": "placeholder_background_repair",
  "debug_artifacts": {
    "background_repair_preview": "04_background_repair/background_repair_preview.png"
  },
  "repairs": [
    {
      "repair_id": "repair_cutout_mask_det_primary_buttons_001",
      "cutout_id": "cutout_mask_det_primary_buttons_001",
      "repair_path": "04_background_repair/repairs/repair_cutout_mask_det_primary_buttons_001.json",
      "repair_asset_path": "04_background_repair/repairs/repair_cutout_mask_det_primary_buttons_001.png",
      "bbox": [64, 64, 256, 128],
      "source": "placeholder_background_repair",
      "placeholder_visual": "inpaint_patch_marker",
      "future_adapter": "background_inpainting"
    }
  ]
}
```

## Compose Manifest

```json
{
  "schema_version": "1.0",
  "final_image": "06_compose/final.png",
  "debug_artifacts": {
    "composition_preview": "06_compose/composition_preview.png"
  },
  "composition_source": "placeholder_compositor",
  "background_repairs": [
    {
      "asset_id": "repair_cutout_mask_det_primary_buttons_001",
      "bbox": [64, 64, 256, 128],
      "generated_asset_path": "04_background_repair/repairs/repair_cutout_mask_det_primary_buttons_001.png",
      "mode": "background_repair_placeholder",
      "source": "placeholder_background_repair",
      "placeholder_visual": "inpaint_patch_marker",
      "applied_to_final": false
    }
  ],
  "placed_assets": [
    {
      "asset_id": "styled_cutout_mask_det_primary_buttons_001",
      "bbox": [64, 64, 256, 128],
      "generated_asset_path": "05_style/styled_assets/styled_cutout_mask_det_primary_buttons_001.png",
      "mode": "alpha_paste_placeholder"
    }
  ],
  "protected_text_regions": [
    {
      "region_id": "text_det_primary_buttons_001_001",
      "bbox": [80, 80, 220, 104],
      "source": "placeholder_ocr_protector"
    }
  ]
}
```

Placeholder background repair patches are visible debug artifacts only. `06_compose/final.png` skips repairs with `applied_to_final = false` so colored inpainting placeholders and selection-like boxes do not appear in the final output.

## Review Manifest

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "contract_review",
  "actual_adapter": "contract_review",
  "pass": true,
  "score": 0.75,
  "issues": [
    {
      "type": "placeholder_pipeline",
      "severity": "info",
      "message": "Pipeline contracts passed, but composition still uses placeholder or contract-only behavior."
    }
  ],
  "checks": [
    {
      "name": "final_image_exists",
      "pass": true
    }
  ]
}
```
