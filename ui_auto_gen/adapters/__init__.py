from ui_auto_gen.adapters.background import BackgroundRepairAdapter, LightweightBackgroundRepair, PlaceholderBackgroundRepair
from ui_auto_gen.adapters.detector import DetectorAdapter, LightweightDetector, OmniParserDetector, PlaceholderDetector
from ui_auto_gen.adapters.ocr import OcrProtectAdapter, PlaceholderOcrProtector, RapidOcrProtector
from ui_auto_gen.adapters.reviewer import ContractReviewer, ReviewAdapter
from ui_auto_gen.adapters.sam2 import Sam2Segmenter
from ui_auto_gen.adapters.segmenter import PlaceholderSegmenter, SegmenterAdapter
from ui_auto_gen.adapters.style import LightweightStyleTransferAdapter, PlaceholderStyleAdapter, StyleAdapter

__all__ = [
    "BackgroundRepairAdapter",
    "ContractReviewer",
    "DetectorAdapter",
    "LightweightStyleTransferAdapter",
    "LightweightBackgroundRepair",
    "LightweightDetector",
    "OcrProtectAdapter",
    "OmniParserDetector",
    "PlaceholderBackgroundRepair",
    "PlaceholderDetector",
    "PlaceholderOcrProtector",
    "PlaceholderSegmenter",
    "PlaceholderStyleAdapter",
    "RapidOcrProtector",
    "ReviewAdapter",
    "Sam2Segmenter",
    "SegmenterAdapter",
    "StyleAdapter",
]
