from ui_auto_gen.adapters.background import BackgroundRepairAdapter, PlaceholderBackgroundRepair
from ui_auto_gen.adapters.detector import DetectorAdapter, LightweightDetector, PlaceholderDetector
from ui_auto_gen.adapters.ocr import OcrProtectAdapter, PlaceholderOcrProtector, RapidOcrProtector
from ui_auto_gen.adapters.reviewer import ContractReviewer, ReviewAdapter
from ui_auto_gen.adapters.sam2 import Sam2TinySegmenter
from ui_auto_gen.adapters.segmenter import PlaceholderSegmenter, SegmenterAdapter
from ui_auto_gen.adapters.style import LightweightStyleTransferAdapter, PlaceholderStyleAdapter, StyleAdapter

__all__ = [
    "BackgroundRepairAdapter",
    "ContractReviewer",
    "DetectorAdapter",
    "LightweightStyleTransferAdapter",
    "LightweightDetector",
    "OcrProtectAdapter",
    "PlaceholderBackgroundRepair",
    "PlaceholderDetector",
    "PlaceholderOcrProtector",
    "PlaceholderSegmenter",
    "PlaceholderStyleAdapter",
    "RapidOcrProtector",
    "ReviewAdapter",
    "Sam2TinySegmenter",
    "SegmenterAdapter",
    "StyleAdapter",
]
