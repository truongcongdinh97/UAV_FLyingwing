"""
AI module initialization
"""

from .object_detector import ObjectDetector, Detection
from .adaptive_detector import AdaptiveDetector

__all__ = ['ObjectDetector', 'Detection', 'AdaptiveDetector']
