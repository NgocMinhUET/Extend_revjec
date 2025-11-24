"""
Motion Vector Extractor Module
Extracts motion vectors from VVC decoder or uses optical flow
"""

import numpy as np
import cv2
import subprocess
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging


class MotionVectorExtractor:
    """
    Extract motion vectors from VVC bitstream or compute optical flow
    """
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """
        Initialize Motion Vector Extractor
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.mv_config = config.get('motion_vectors', {})
        self.logger = logger or logging.getLogger(__name__)
        
        self.enabled = self.mv_config.get('enabled', True)
        self.method = self.mv_config.get('extraction_method', 'optical_flow')
        self.block_size = self.mv_config.get('block_size', 16)
        
        self.logger.info(f"Motion Vector Extractor initialized: method={self.method}")
    
    def extract_from_frames(self,
                           frame1: np.ndarray,
                           frame2: np.ndarray,
                           method: str = 'farneback') -> np.ndarray:
        """
        Extract motion vectors using optical flow
        
        Args:
            frame1: Previous frame (H, W, 3) or (H, W)
            frame2: Current frame (H, W, 3) or (H, W)
            method: Optical flow method ('farneback', 'lucas_kanade')
            
        Returns:
            Motion vectors (H, W, 2) - [dx, dy] for each pixel
        """
        # Convert to grayscale if needed
        if len(frame1.shape) == 3:
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        else:
            gray1 = frame1
        
        if len(frame2.shape) == 3:
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        else:
            gray2 = frame2
        
        if method == 'farneback':
            flow = cv2.calcOpticalFlowFarneback(
                gray1, gray2, None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0
            )
        elif method == 'lucas_kanade':
            # Sparse optical flow (Lucas-Kanade)
            # Detect features in first frame
            corners = cv2.goodFeaturesToTrack(
                gray1,
                maxCorners=1000,
                qualityLevel=0.01,
                minDistance=10
            )
            
            if corners is not None:
                # Calculate optical flow
                next_corners, status, _ = cv2.calcOpticalFlowPyrLK(
                    gray1, gray2, corners, None
                )
                
                # Create dense flow from sparse points
                flow = self._sparse_to_dense_flow(
                    corners, next_corners, status, gray1.shape
                )
            else:
                flow = np.zeros((*gray1.shape, 2), dtype=np.float32)
        else:
            raise ValueError(f"Unknown optical flow method: {method}")
        
        return flow
    
    def _sparse_to_dense_flow(self,
                              corners: np.ndarray,
                              next_corners: np.ndarray,
                              status: np.ndarray,
                              shape: Tuple[int, int]) -> np.ndarray:
        """
        Convert sparse optical flow to dense flow field
        
        Args:
            corners: Original corner points (N, 1, 2)
            next_corners: Tracked corner points (N, 1, 2)
            status: Tracking status (N, 1)
            shape: Image shape (H, W)
            
        Returns:
            Dense flow field (H, W, 2)
        """
        h, w = shape
        flow = np.zeros((h, w, 2), dtype=np.float32)
        
        # Filter good points
        good_old = corners[status == 1]
        good_new = next_corners[status == 1]
        
        if len(good_old) == 0:
            return flow
        
        # Calculate motion vectors
        motion = good_new - good_old
        
        # Interpolate to dense grid
        from scipy.interpolate import griddata
        
        points = good_old.reshape(-1, 2)
        values_x = motion[:, 0]
        values_y = motion[:, 1]
        
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        
        flow[:, :, 0] = griddata(points, values_x, (grid_x, grid_y), method='linear', fill_value=0)
        flow[:, :, 1] = griddata(points, values_y, (grid_x, grid_y), method='linear', fill_value=0)
        
        return flow
    
    def extract_from_bitstream(self,
                               bitstream_path: str,
                               output_dir: Optional[str] = None) -> Dict[int, np.ndarray]:
        """
        Extract motion vectors from VVC bitstream using decoder
        
        Args:
            bitstream_path: Path to VVC bitstream
            output_dir: Directory to save MV files
            
        Returns:
            Dictionary mapping frame_idx -> motion_vectors (H, W, 2)
        """
        if output_dir is None:
            output_dir = Path(bitstream_path).parent / 'mv_output'
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run VVC decoder with MV output
        # Note: This requires modified VVC decoder that outputs MVs
        # For now, we'll use optical flow as fallback
        
        self.logger.warning(
            "MV extraction from bitstream not yet implemented. "
            "Using optical flow instead."
        )
        
        return {}
    
    def downsample_to_blocks(self,
                            flow: np.ndarray,
                            block_size: Optional[int] = None) -> np.ndarray:
        """
        Downsample dense flow to block-level motion vectors
        
        Args:
            flow: Dense optical flow (H, W, 2)
            block_size: Block size (default: from config)
            
        Returns:
            Block-level motion vectors (n_blocks_h, n_blocks_w, 2)
        """
        if block_size is None:
            block_size = self.block_size
        
        h, w = flow.shape[:2]
        n_blocks_h = h // block_size
        n_blocks_w = w // block_size
        
        block_mvs = np.zeros((n_blocks_h, n_blocks_w, 2), dtype=np.float32)
        
        for i in range(n_blocks_h):
            for j in range(n_blocks_w):
                # Extract block
                y1 = i * block_size
                y2 = (i + 1) * block_size
                x1 = j * block_size
                x2 = (j + 1) * block_size
                
                block_flow = flow[y1:y2, x1:x2]
                
                # Calculate median motion vector for block
                block_mvs[i, j] = np.median(
                    block_flow.reshape(-1, 2), axis=0
                )
        
        return block_mvs
    
    def upsample_to_pixels(self,
                          block_mvs: np.ndarray,
                          target_shape: Tuple[int, int],
                          block_size: Optional[int] = None) -> np.ndarray:
        """
        Upsample block-level MVs to pixel-level flow
        
        Args:
            block_mvs: Block-level motion vectors (n_blocks_h, n_blocks_w, 2)
            target_shape: Target shape (H, W)
            block_size: Block size (default: from config)
            
        Returns:
            Pixel-level flow (H, W, 2)
        """
        if block_size is None:
            block_size = self.block_size
        
        h, w = target_shape
        flow = np.zeros((h, w, 2), dtype=np.float32)
        
        n_blocks_h, n_blocks_w = block_mvs.shape[:2]
        
        for i in range(n_blocks_h):
            for j in range(n_blocks_w):
                y1 = i * block_size
                y2 = min((i + 1) * block_size, h)
                x1 = j * block_size
                x2 = min((j + 1) * block_size, w)
                
                flow[y1:y2, x1:x2] = block_mvs[i, j]
        
        return flow
    
    def visualize_flow(self,
                      flow: np.ndarray,
                      frame: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Visualize optical flow as color-coded image
        
        Args:
            flow: Optical flow (H, W, 2)
            frame: Optional background frame
            
        Returns:
            Visualization image (H, W, 3)
        """
        h, w = flow.shape[:2]
        
        # Convert flow to HSV
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        hsv = np.zeros((h, w, 3), dtype=np.uint8)
        hsv[..., 0] = ang * 180 / np.pi / 2  # Hue: direction
        hsv[..., 1] = 255  # Saturation: full
        hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)  # Value: magnitude
        
        # Convert to BGR
        flow_vis = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # Overlay on frame if provided
        if frame is not None:
            flow_vis = cv2.addWeighted(frame, 0.5, flow_vis, 0.5, 0)
        
        return flow_vis
    
    def calculate_motion_statistics(self, flow: np.ndarray) -> Dict:
        """
        Calculate motion statistics from optical flow
        
        Args:
            flow: Optical flow (H, W, 2)
            
        Returns:
            Dictionary with motion statistics
        """
        # Calculate magnitude
        magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        
        return {
            'mean_magnitude': np.mean(magnitude),
            'max_magnitude': np.max(magnitude),
            'std_magnitude': np.std(magnitude),
            'median_magnitude': np.median(magnitude),
            'mean_dx': np.mean(flow[..., 0]),
            'mean_dy': np.mean(flow[..., 1]),
        }
