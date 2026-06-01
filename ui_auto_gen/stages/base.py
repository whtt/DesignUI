from __future__ import annotations

from abc import ABC, abstractmethod

from ui_auto_gen.schemas import PipelineContext, StageResult


class PipelineStage(ABC):
    name: str

    @abstractmethod
    def run(self, context: PipelineContext) -> StageResult:
        raise NotImplementedError

