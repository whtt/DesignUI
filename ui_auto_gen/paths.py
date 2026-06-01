from __future__ import annotations

from pathlib import Path


STAGE_ORDER = [
    "00_ingest",
    "01_plan",
    "02_detect",
    "03_segment",
    "04_cutout",
    "05_style",
    "06_compose",
    "07_review",
    "08_export",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def make_run_id(project_name: str, timestamp: str) -> str:
    safe_name = "".join(char if char.isalnum() or char in "-_" else "_" for char in project_name)
    compact_time = timestamp.replace(":", "").replace("-", "").split(".")[0]
    return f"{safe_name}_{compact_time}"

