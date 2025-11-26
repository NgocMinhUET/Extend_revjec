"""
Adaptive QP Controller Module
Content-adaptive QP adjustment for hierarchical ROI encoding

FEATURES:
- Texture-aware QP adjustment
- Motion-adaptive QP control
- Bitrate normalization
- Per-CTU QP generation

ALGORITHM:
1. Analyze frame content (texture, motion)
2. Calculate adaptive alpha values for each ROI level
3. Generate CTU-level QP map
4. Normalize to maintain target bitrate

QP CALCULATION:
  QP_core = base_QP - alpha_core
  QP_context = base_QP - alpha_context  
  QP_background = base_QP + alpha_bg
"""

import numpy as np
import cv2
from typing import Dict, Optional, Tuple
import logging


class QPController:
    """
    Adaptive QP controller for hierarchical ROI encoding
    """
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """
        Initialize QP Controller
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # QP control parameters
        qp_config = config.get('qp_control', {})
        self.method = qp_config.get('method', 'adaptive')
        
        # Base alpha values
        base_alpha = qp_config.get('base_alpha', {})
        self.base_alpha_core = base_alpha.get('core', 8)
        self.base_alpha_context = base_alpha.get('context', 4)
        self.base_alpha_bg = base_alpha.get('background', 6)
        
        # Adaptive settings
        adaptive = qp_config.get('adaptive', {})
        self.adaptive_enabled = adaptive.get('enabled', True)
        self.texture_weight = adaptive.get('texture_weight', 0.3)
        self.motion_weight = adaptive.get('motion_weight', 0.2)
        self.normalize = adaptive.get('normalize', True)
        
        # QP constraints
        self.qp_min = qp_config.get('qp_min', 0)
        self.qp_max = qp_config.get('qp_max', 51)
        
        self.logger.info(f"QP Controller initialized:")
        self.logger.info(f"  Method: {self.method}")
        self.logger.info(f"  Base alpha: core={self.base_alpha_core}, "
                        f"context={self.base_alpha_context}, bg={self.base_alpha_bg}")
        self.logger.info(f"  Adaptive: {self.adaptive_enabled}")
    
    def generate_qp_map(self,
                       roi_map: np.ndarray,
                       base_qp: int,
                       frame: Optional[np.ndarray] = None,
                       motion_map: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Generate QP map from hierarchical ROI map
        
        Args:
            roi_map: ROI map (H, W) with levels 0, 1, 2
            base_qp: Base QP value
            frame: Optional frame for texture analysis
            motion_map: Optional motion map for adaptive QP
            
        Returns:
            QP map (H, W) with QP value for each pixel/CTU
        """
        # Calculate alpha values
        if self.adaptive_enabled and frame is not None:
            alphas = self._calculate_adaptive_alpha(roi_map, frame, motion_map)
        else:
            alphas = {
                'core': self.base_alpha_core,
                'context': self.base_alpha_context,
                'background': self.base_alpha_bg
            }
        
        # Generate QP map
        qp_map = np.full(roi_map.shape, base_qp, dtype=np.float32)
        
        # Apply alpha values
        qp_map[roi_map == 2] = base_qp - alphas['core']  # Core: Lower QP
        qp_map[roi_map == 1] = base_qp - alphas['context']  # Context: Medium QP
        qp_map[roi_map == 0] = base_qp + alphas['background']  # Background: Higher QP
        
        # Clip to valid range
        qp_map = np.clip(qp_map, self.qp_min, self.qp_max)
        
        return qp_map.astype(np.int32)
    
    def _calculate_adaptive_alpha(self,
                                  roi_map: np.ndarray,
                                  frame: np.ndarray,
                                  motion_map: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Calculate content-adaptive alpha values
        
        Args:
            roi_map: ROI map
            frame: Input frame (BGR)
            motion_map: Optional motion map
            
        Returns:
            Dictionary with alpha values for each level
        """
        # Calculate ROI densities
        total_pixels = roi_map.size
        density_core = np.sum(roi_map == 2) / total_pixels
        density_context = np.sum(roi_map == 1) / total_pixels
        density_bg = np.sum(roi_map == 0) / total_pixels
        
        # Calculate texture complexity for each level
        texture_core = self._calculate_texture_complexity(frame, roi_map, level=2)
        texture_context = self._calculate_texture_complexity(frame, roi_map, level=1)
        texture_bg = self._calculate_texture_complexity(frame, roi_map, level=0)
        
        # Calculate motion complexity if available
        if motion_map is not None:
            motion_complexity = self._calculate_motion_complexity(motion_map)
        else:
            motion_complexity = 0.5  # Default neutral value
        
        # Adaptive alpha calculation
        alpha_core = self.base_alpha_core * (1.0 + self.texture_weight * texture_core) * \
                     (1.0 + self.motion_weight * motion_complexity)
        
        alpha_context = self.base_alpha_context * (1.0 + 0.5 * self.texture_weight * texture_context)
        
        alpha_bg = self.base_alpha_bg * (1.0 - 0.5 * self.texture_weight * texture_bg)
        
        # Normalize if enabled
        if self.normalize and density_core > 0:
            alpha_core, alpha_context, alpha_bg = self._normalize_alphas(
                alpha_core, alpha_context, alpha_bg,
                density_core, density_context, density_bg
            )
        
        # Clip alphas to reasonable range
        alpha_core = np.clip(alpha_core, 2, 15)
        alpha_context = np.clip(alpha_context, 1, 10)
        alpha_bg = np.clip(alpha_bg, 2, 12)
        
        return {
            'core': alpha_core,
            'context': alpha_context,
            'background': alpha_bg
        }
    
    def _calculate_texture_complexity(self,
                                     frame: np.ndarray,
                                     roi_map: np.ndarray,
                                     level: int) -> float:
        """
        Calculate texture complexity for a specific ROI level
        
        Args:
            frame: Input frame (BGR)
            roi_map: ROI map
            level: ROI level (0, 1, 2)
            
        Returns:
            Normalized texture complexity [0, 1]
        """
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Get mask for this level
        mask = (roi_map == level).astype(np.uint8)
        
        if np.sum(mask) == 0:
            return 0.5  # Default for empty regions
        
        # Calculate Laplacian variance (edge strength)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian_masked = laplacian * mask
        
        # Variance as texture measure
        variance = np.var(laplacian_masked[mask > 0])
        
        # Normalize to [0, 1] range (typical variance range: 0-1000)
        normalized = np.clip(variance / 1000.0, 0.0, 1.0)
        
        return float(normalized)
    
    def _calculate_motion_complexity(self, motion_map: np.ndarray) -> float:
        """
        Calculate motion complexity from motion magnitude map
        
        Args:
            motion_map: Motion magnitude map
            
        Returns:
            Normalized motion complexity [0, 1]
        """
        avg_motion = np.mean(motion_map)
        
        # Normalize (typical motion range: 0-50 pixels)
        normalized = np.clip(avg_motion / 50.0, 0.0, 1.0)
        
        return float(normalized)
    
    def _normalize_alphas(self,
                         alpha_core: float,
                         alpha_context: float,
                         alpha_bg: float,
                         density_core: float,
                         density_context: float,
                         density_bg: float) -> Tuple[float, float, float]:
        """
        Normalize alpha values to maintain target bitrate
        
        Ensures that weighted sum of QP adjustments is near zero:
          d_core * (-alpha_core) + d_context * (-alpha_context) + d_bg * (+alpha_bg) ≈ 0
        
        Args:
            alpha_core, alpha_context, alpha_bg: Alpha values
            density_core, density_context, density_bg: Area densities
            
        Returns:
            Normalized (alpha_core, alpha_context, alpha_bg)
        """
        # Calculate current weighted sum
        weighted_sum = (density_core * (-alpha_core) + 
                       density_context * (-alpha_context) + 
                       density_bg * alpha_bg)
        
        # If weighted sum is negative (bitrate would increase), adjust background
        if weighted_sum < 0:
            # Increase alpha_bg to compensate
            needed_adjustment = -weighted_sum / density_bg if density_bg > 0 else 0
            alpha_bg = alpha_bg + needed_adjustment
        
        # If weighted sum is positive (bitrate would decrease), adjust core/context
        elif weighted_sum > 0:
            # Decrease alphas proportionally
            if density_core + density_context > 0:
                factor = weighted_sum / (density_core + density_context)
                alpha_core = max(1.0, alpha_core - factor * 0.7)
                alpha_context = max(0.5, alpha_context - factor * 0.3)
        
        return alpha_core, alpha_context, alpha_bg
    
    def convert_to_ctu_qp_map(self,
                              qp_map: np.ndarray,
                              ctu_size: int = 128) -> np.ndarray:
        """
        Convert pixel-level QP map to CTU-level QP map
        
        Args:
            qp_map: Pixel-level QP map (H, W)
            ctu_size: CTU size in pixels
            
        Returns:
            CTU-level QP map (n_ctu_h, n_ctu_w)
        """
        height, width = qp_map.shape
        n_ctu_h = (height + ctu_size - 1) // ctu_size
        n_ctu_w = (width + ctu_size - 1) // ctu_size
        
        ctu_qp_map = np.zeros((n_ctu_h, n_ctu_w), dtype=np.int32)
        
        for i in range(n_ctu_h):
            for j in range(n_ctu_w):
                # Get CTU region
                y1 = i * ctu_size
                y2 = min((i + 1) * ctu_size, height)
                x1 = j * ctu_size
                x2 = min((j + 1) * ctu_size, width)
                
                # Average QP in this CTU
                ctu_qp = qp_map[y1:y2, x1:x2]
                avg_qp = int(np.round(np.mean(ctu_qp)))
                
                ctu_qp_map[i, j] = np.clip(avg_qp, self.qp_min, self.qp_max)
        
        return ctu_qp_map
    
    def visualize_qp_map(self,
                        qp_map: np.ndarray,
                        base_qp: int,
                        output_path: Optional[str] = None) -> np.ndarray:
        """
        Visualize QP map as heatmap
        
        Args:
            qp_map: QP map (H, W) or (n_ctu_h, n_ctu_w)
            base_qp: Base QP for reference
            output_path: Optional path to save visualization
            
        Returns:
            Colored QP visualization
        """
        # Normalize QP values to [0, 255] for colormap
        qp_normalized = ((qp_map - self.qp_min) / (self.qp_max - self.qp_min) * 255).astype(np.uint8)
        
        # Apply colormap (blue=low QP/high quality, red=high QP/low quality)
        qp_colored = cv2.applyColorMap(qp_normalized, cv2.COLORMAP_JET)
        
        # Add text annotations for base QP
        h, w = qp_colored.shape[:2]
        
        # Add legend
        legend_height = 60
        legend = np.ones((legend_height, w, 3), dtype=np.uint8) * 255
        
        cv2.putText(legend, f"Base QP: {base_qp}", (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(legend, f"Blue=Low QP (High Quality), Red=High QP (Low Quality)",
                   (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Combine
        vis = np.vstack([qp_colored, legend])
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis
    
    def get_qp_statistics(self, qp_map: np.ndarray, roi_map: np.ndarray) -> Dict:
        """
        Get QP statistics for each ROI level
        
        Args:
            qp_map: QP map
            roi_map: ROI map
            
        Returns:
            Dictionary with statistics per level
        """
        stats = {}
        
        level_names = {0: 'background', 1: 'context', 2: 'core'}
        
        for level in range(3):
            mask = (roi_map == level)
            if np.sum(mask) > 0:
                qp_values = qp_map[mask]
                stats[level_names[level]] = {
                    'mean_qp': float(np.mean(qp_values)),
                    'min_qp': int(np.min(qp_values)),
                    'max_qp': int(np.max(qp_values)),
                    'std_qp': float(np.std(qp_values))
                }
            else:
                stats[level_names[level]] = {
                    'mean_qp': 0.0,
                    'min_qp': 0,
                    'max_qp': 0,
                    'std_qp': 0.0
                }
        
        return stats
