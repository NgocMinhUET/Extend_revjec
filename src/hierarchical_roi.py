"""
Hierarchical ROI Generation Module
Generate 3-level ROI hierarchy: Core, Context, Background

LEVELS:
- Level 2 (Core): Object bounding boxes - HIGHEST quality
- Level 1 (Context): Adaptive ring around objects - MEDIUM quality  
- Level 0 (Background): Rest of frame - LOWEST quality

ADVANTAGES:
- Better perceptual quality (smooth transition)
- More efficient bitrate allocation
- Reduced blocking artifacts at ROI boundaries

IMPLEMENTATION:
- Adaptive context ring width based on object size and motion
- Texture-aware QP adjustment
- Bitrate normalization to maintain target rate
"""

import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional
import logging


class HierarchicalROI:
    """
    Hierarchical ROI generation with 3 levels
    """
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """
        Initialize Hierarchical ROI generator
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Hierarchical ROI parameters
        h_config = config.get('hierarchical_roi', {})
        self.enabled = h_config.get('enabled', True)
        self.n_levels = h_config.get('levels', 3)
        
        # Context ring parameters
        ring_config = h_config.get('context_ring', {})
        self.adaptive_ring = ring_config.get('adaptive', True)
        self.base_ring_ratio = ring_config.get('base_ratio', 0.2)
        self.min_ring_width = ring_config.get('min_width', 10)
        self.max_ring_width = ring_config.get('max_width', 50)
        self.motion_factor = ring_config.get('motion_factor', 0.3)
        
        self.logger.info(f"Hierarchical ROI initialized:")
        self.logger.info(f"  Levels: {self.n_levels}")
        self.logger.info(f"  Adaptive ring: {self.adaptive_ring}")
        self.logger.info(f"  Ring ratio: {self.base_ring_ratio}")
    
    def generate_hierarchical_roi(self,
                                  bboxes: np.ndarray,
                                  width: int,
                                  height: int,
                                  motion_map: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Generate hierarchical ROI map from bounding boxes
        
        Args:
            bboxes: Bounding boxes (N, 4) [x1, y1, x2, y2]
            width: Frame width
            height: Frame height
            motion_map: Optional motion magnitude map for adaptive ring
            
        Returns:
            ROI map (H, W) with values:
              0 = Background
              1 = Context
              2 = Core
        """
        # Initialize ROI map (all background)
        roi_map = np.zeros((height, width), dtype=np.uint8)
        
        if len(bboxes) == 0:
            return roi_map
        
        # Process each bbox
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox.astype(int)
            
            # Clip to frame bounds
            x1 = max(0, min(x1, width - 1))
            y1 = max(0, min(y1, height - 1))
            x2 = max(0, min(x2, width))
            y2 = max(0, min(y2, height))
            
            # Skip invalid boxes
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Calculate adaptive ring width
            if self.adaptive_ring:
                ring_width = self._calculate_adaptive_ring_width(
                    bbox, motion_map, width, height
                )
            else:
                ring_width = int((x2 - x1 + y2 - y1) / 2 * self.base_ring_ratio)
                ring_width = np.clip(ring_width, self.min_ring_width, self.max_ring_width)
            
            # Level 1: Context Ring (draw first, will be overwritten by core)
            ctx_x1 = max(0, x1 - ring_width)
            ctx_y1 = max(0, y1 - ring_width)
            ctx_x2 = min(width, x2 + ring_width)
            ctx_y2 = min(height, y2 + ring_width)
            
            # Only mark as context if not already core
            roi_map[ctx_y1:ctx_y2, ctx_x1:ctx_x2] = np.where(
                roi_map[ctx_y1:ctx_y2, ctx_x1:ctx_x2] == 0,
                1,  # Context
                roi_map[ctx_y1:ctx_y2, ctx_x1:ctx_x2]
            )
            
            # Level 2: Core (overwrite context)
            roi_map[y1:y2, x1:x2] = 2
        
        return roi_map
    
    def _calculate_adaptive_ring_width(self,
                                       bbox: np.ndarray,
                                       motion_map: Optional[np.ndarray],
                                       width: int,
                                       height: int) -> int:
        """
        Calculate adaptive context ring width
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            motion_map: Motion magnitude map
            width: Frame width
            height: Frame height
            
        Returns:
            Ring width in pixels
        """
        x1, y1, x2, y2 = bbox.astype(int)
        
        # Base width proportional to object size
        bbox_w = x2 - x1
        bbox_h = y2 - y1
        bbox_size = np.sqrt(bbox_w * bbox_h)
        base_width = int(bbox_size * self.base_ring_ratio)
        
        # Adjust based on motion if available
        if motion_map is not None:
            # Sample motion in bbox region
            x1_clip = max(0, min(x1, width - 1))
            y1_clip = max(0, min(y1, height - 1))
            x2_clip = max(0, min(x2, width))
            y2_clip = max(0, min(y2, height))
            
            if x2_clip > x1_clip and y2_clip > y1_clip:
                bbox_motion = motion_map[y1_clip:y2_clip, x1_clip:x2_clip]
                avg_motion = np.mean(bbox_motion)
                
                # Increase ring width for high motion objects
                motion_adjustment = 1.0 + self.motion_factor * (avg_motion / 10.0)
                base_width = int(base_width * motion_adjustment)
        
        # Clip to min/max
        return np.clip(base_width, self.min_ring_width, self.max_ring_width)
    
    def roi_map_to_ctu_map(self,
                           roi_map: np.ndarray,
                           ctu_size: int = 128) -> np.ndarray:
        """
        Convert pixel-level ROI map to CTU-level map
        
        Args:
            roi_map: Pixel-level ROI map (H, W)
            ctu_size: CTU size in pixels
            
        Returns:
            CTU-level ROI map (n_ctu_h, n_ctu_w)
        """
        height, width = roi_map.shape
        n_ctu_h = (height + ctu_size - 1) // ctu_size
        n_ctu_w = (width + ctu_size - 1) // ctu_size
        
        ctu_map = np.zeros((n_ctu_h, n_ctu_w), dtype=np.uint8)
        
        for i in range(n_ctu_h):
            for j in range(n_ctu_w):
                # Get CTU region
                y1 = i * ctu_size
                y2 = min((i + 1) * ctu_size, height)
                x1 = j * ctu_size
                x2 = min((j + 1) * ctu_size, width)
                
                # Get ROI values in this CTU
                ctu_roi = roi_map[y1:y2, x1:x2]
                
                # Assign CTU level based on majority vote
                unique, counts = np.unique(ctu_roi, return_counts=True)
                ctu_map[i, j] = unique[np.argmax(counts)]
        
        return ctu_map
    
    def visualize_hierarchical_roi(self,
                                   frame: np.ndarray,
                                   roi_map: np.ndarray,
                                   output_path: Optional[str] = None) -> np.ndarray:
        """
        Visualize hierarchical ROI on frame
        
        Args:
            frame: Input frame (BGR)
            roi_map: ROI map (H, W) with levels 0, 1, 2
            output_path: Optional path to save visualization
            
        Returns:
            Annotated frame
        """
        vis = frame.copy()
        
        # Create colored overlay
        overlay = np.zeros_like(frame)
        
        # Background: Blue tint
        overlay[roi_map == 0] = [128, 0, 0]
        
        # Context: Yellow tint
        overlay[roi_map == 1] = [0, 128, 128]
        
        # Core: Green tint
        overlay[roi_map == 2] = [0, 128, 0]
        
        # Blend with original frame
        vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)
        
        # Add legend
        legend_height = 80
        legend = np.zeros((legend_height, frame.shape[1], 3), dtype=np.uint8)
        
        cv2.rectangle(legend, (10, 10), (30, 30), (128, 0, 0), -1)
        cv2.putText(legend, "Background (Level 0)", (40, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.rectangle(legend, (10, 40), (30, 60), (0, 128, 128), -1)
        cv2.putText(legend, "Context (Level 1)", (40, 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.rectangle(legend, (250, 10), (270, 30), (0, 128, 0), -1)
        cv2.putText(legend, "Core (Level 2)", (280, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Combine
        vis = np.vstack([vis, legend])
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis
    
    def get_level_statistics(self, roi_map: np.ndarray) -> Dict:
        """
        Get statistics for each ROI level
        
        Args:
            roi_map: ROI map (H, W)
            
        Returns:
            Dictionary with statistics per level
        """
        total_pixels = roi_map.size
        
        stats = {}
        for level in range(self.n_levels):
            n_pixels = np.sum(roi_map == level)
            percentage = (n_pixels / total_pixels) * 100
            
            level_names = {0: 'background', 1: 'context', 2: 'core'}
            stats[level_names[level]] = {
                'pixels': int(n_pixels),
                'percentage': float(percentage)
            }
        
        return stats
    
    def merge_temporal_rois(self,
                           roi_maps: List[np.ndarray],
                           weights: Optional[List[float]] = None) -> np.ndarray:
        """
        Merge multiple ROI maps with optional temporal weighting
        
        Args:
            roi_maps: List of ROI maps
            weights: Optional weights for each map
            
        Returns:
            Merged ROI map
        """
        if len(roi_maps) == 0:
            raise ValueError("No ROI maps provided")
        
        if len(roi_maps) == 1:
            return roi_maps[0]
        
        # Stack maps
        stacked = np.stack(roi_maps, axis=0)
        
        if weights is None:
            # Simple majority vote
            merged = np.median(stacked, axis=0).astype(np.uint8)
        else:
            # Weighted average
            weights = np.array(weights).reshape(-1, 1, 1)
            weighted_sum = np.sum(stacked * weights, axis=0)
            merged = np.round(weighted_sum).astype(np.uint8)
        
        return merged
