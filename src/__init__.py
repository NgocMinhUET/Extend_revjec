"""
Hierarchical Temporal ROI-VVC Framework
Main package initialization
"""

__version__ = "1.0.0"
__author__ = "Bui Thanh Huong, Do Ngoc Minh, Hoang Van Xiem"

# Import existing modules
from .gop_manager import GOPManager
from .roi_detector import ROIDetector
from .vvc_encoder import VVCEncoder
from .motion_vector_extractor import MotionVectorExtractor

# TODO: Uncomment when modules are implemented
# from .temporal_propagator import TemporalPropagator
# from .hierarchical_roi import HierarchicalROI
# from .qp_controller import QPController
# from .performance_evaluator import PerformanceEvaluator

__all__ = [
    "GOPManager",
    "ROIDetector",
    "VVCEncoder",
    "MotionVectorExtractor",
    # TODO: Add when implemented
    # "TemporalPropagator",
    # "HierarchicalROI",
    # "QPController",
    # "PerformanceEvaluator",
]
