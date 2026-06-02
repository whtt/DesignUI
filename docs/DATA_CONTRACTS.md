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

## Segmentation Manifest

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "sam2",
  "actual_adapter": "placeholder_segmenter",
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
      "confidence": 0.5,
      "source": "placeholder_segmenter",
      "placeholder_visual": "colored_rectangle_mask",
      "future_adapter": "sam_or_instance_segmentation"
    }
  ]
}
```

`placeholder_visual` describes how the current non-model output is made visible in previews. `future_adapter` names the adapter family expected to replace the placeholder.

## Style Manifest

```json
{
  "schema_version": "1.0",
  "requested_algorithm": "controlnet_ipadapter",
  "actual_adapter": "placeholder_style_adapter",
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

## Compose Manifest

```json
{
  "schema_version": "1.0",
  "final_image": "06_compose/final.png",
  "debug_artifacts": {
    "composition_preview": "06_compose/composition_preview.png"
  },
  "composition_source": "placeholder_compositor",
  "placed_assets": [
    {
      "asset_id": "styled_cutout_mask_det_primary_buttons_001",
      "bbox": [64, 64, 256, 128],
      "generated_asset_path": "05_style/styled_assets/styled_cutout_mask_det_primary_buttons_001.png",
      "mode": "alpha_paste_placeholder"
    }
  ]
}
```

## Review Manifest

```json
{
  "schema_version": "1.0",
  "pass": true,
  "score": 0.75,
  "issues": [],
  "checks": []
}
```
