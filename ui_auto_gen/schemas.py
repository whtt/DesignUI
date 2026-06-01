from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class StageResult:
    stage: str
    status: str
    artifacts: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StagePaths:
    name: str
    root: Path

    def artifact(self, relative_path: str) -> Path:
        return self.root / relative_path


@dataclass
class PipelineContext:
    run_id: str
    repo_root: Path
    run_root: Path
    config_path: Path
    config: JsonDict
    manifest: JsonDict

    def stage_dir(self, name: str) -> StagePaths:
        path = self.run_root / name
        path.mkdir(parents=True, exist_ok=True)
        return StagePaths(name=name, root=path)

