"""
Temporal ROI Propagation Module
Propagate ROI from keyframes to other frames using motion tracking

ALGORITHM:
1. Detect ROI on keyframes (I-frames)
2. Propagate ROI to P-frames using optical flow
3. Re-detect when motion is large or tracking fails
4. Support both forward and backward propagation

ADVANTAGES vs frame-by-frame detection:
- Reduced computational cost (detect only keyframes)
- Temporal consistency (smoother ROI transitions)
- Better for low-latency applications

IMPLEMENTATION:
- Uses OpenCV optical flow (Lucas-Kanade or Farneback)
- Adaptive re-detection based on motion magnitude
- Configurable keyframe interval
"""

import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional
import logging
from pathlib import Path


class TemporalPropagator:
    """
    Temporal ROI Propagation using motion tracking
    """
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """
        Initialize Temporal Propagator
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Propagation parameters
        temporal_cfg = config.get('roi_detection', {}).get('temporal', {})
        self.keyframe_interval = temporal_cfg.get('keyframe_interval', 10)
        self.motion_threshold = temporal_cfg.get('redetection_triggers', {}).get('motion_threshold', 30.0)
        self.redetection_threshold = temporal_cfg.get('redetection_triggers', {}).get('redetection_threshold', 50.0)
        self.optical_flow_method = temporal_cfg.get('optical_flow_method', 'farneback')
        
        # Optical flow parameters
        self.flow_params = self._init_flow_params()
        
        self.logger.info(f"Temporal Propagator initialized:")
        self.logger.info(f"  Keyframe interval: {self.keyframe_interval}")
        self.logger.info(f"  Motion threshold: {self.motion_threshold}")
        self.logger.info(f"  Optical flow method: {self.optical_flow_method}")
    
    def _init_flow_params(self) -> Dict:
        """Initialize optical flow parameters"""
        if self.optical_flow_method == 'farneback':
            return {
                'pyr_scale': 0.5,
                'levels': 3,
                'winsize': 15,
                'iterations': 3,
                'poly_n': 5,
                'poly_sigma': 1.2,
                'flags': 0
            }
        elif self.optical_flow_method == 'lucas_kanade':
            return {
                'winSize': (15, 15),
                'maxLevel': 2,
                'criteria': (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
            }
        else:
            return {}
    
    def propagate_roi_sequence(self, 
                               frames: List[np.ndarray],
                               detector,
                               detector_interval: Optional[int] = None) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """
        Propagate ROI across entire sequence with adaptive re-detection
        
        Args:
            frames: List of frames (BGR format)
            detector: ROI detector instance (with detect() method)
            detector_interval: How often to run detector (None = use keyframe_interval)
            
        Returns:
            List of (bboxes, scores, class_ids) for each frame
        """
        if detector_interval is None:
            detector_interval = self.keyframe_interval
        
        n_frames = len(frames)
        all_detections = []
        prev_gray = None
        
        self.logger.info(f"Propagating ROI across {n_frames} frames (interval={detector_interval})")
        
        for i, frame in enumerate(frames):
            # Convert to grayscale for optical flow
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Keyframe: run detector
            if i == 0 or i % detector_interval == 0:
                bboxes, scores, class_ids = detector.detect(frame)
                all_detections.append((bboxes, scores, class_ids))
                self.logger.debug(f"Frame {i}: Keyframe detection - {len(bboxes)} objects")
                prev_gray = gray
                continue
            
            # Non-keyframe: propagate from previous frame
            if prev_gray is not None and len(all_detections[-1][0]) > 0:
                # Compute optical flow
                flow = self._compute_optical_flow(prev_gray, gray)
                
                # Propagate bounding boxes
                prev_bboxes, prev_scores, prev_class_ids = all_detections[-1]
                prop_bboxes = self._propagate_bboxes(prev_bboxes, flow)
                
                # Check if re-detection needed
                if self._need_redetection(flow, prop_bboxes):
                    self.logger.debug(f"Frame {i}: Re-detection triggered")
                    bboxes, scores, class_ids = detector.detect(frame)
                else:
                    # Use propagated bboxes
                    bboxes = prop_bboxes
                    scores = prev_scores.copy()  # Keep previous scores
                    class_ids = prev_class_ids.copy()
                    self.logger.debug(f"Frame {i}: Propagated - {len(bboxes)} objects")
                
                all_detections.append((bboxes, scores, class_ids))
            else:
                # No previous detections, run detector
                bboxes, scores, class_ids = detector.detect(frame)
                all_detections.append((bboxes, scores, class_ids))
                self.logger.debug(f"Frame {i}: No prev detections - running detector")
            
            prev_gray = gray
        
        # Statistics
        n_detections = sum(1 for i in range(n_frames) if i == 0 or i % detector_interval == 0)
        n_propagations = n_frames - n_detections
        self.logger.info(f"Propagation complete: {n_detections} detections, {n_propagations} propagations")
        
        return all_detections
    
    def _compute_optical_flow(self, prev_gray: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        Compute optical flow between two frames
        
        Args:
            prev_gray: Previous frame (grayscale)
            gray: Current frame (grayscale)
            
        Returns:
            Flow field (H, W, 2) - dx, dy for each pixel
        """
        if self.optical_flow_method == 'farneback':
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray,
                None,
                self.flow_params['pyr_scale'],
                self.flow_params['levels'],
                self.flow_params['winsize'],
                self.flow_params['iterations'],
                self.flow_params['poly_n'],
                self.flow_params['poly_sigma'],
                self.flow_params['flags']
            )
        else:
            # Fallback to simple dense flow
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        
        return flow
    
    def _propagate_bboxes(self, bboxes: np.ndarray, flow: np.ndarray) -> np.ndarray:
        """
        Propagate bounding boxes using optical flow
        
        Args:
            bboxes: Bounding boxes (N, 4) [x1, y1, x2, y2]
            flow: Optical flow field (H, W, 2)
            
        Returns:
            Propagated bounding boxes (N, 4)
        """
        if len(bboxes) == 0:
            return bboxes
        
        prop_bboxes = []
        h, w = flow.shape[:2]
        
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            
            # Get flow in bbox region (sample center and corners)
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            
            # Ensure coordinates are within bounds
            cx = np.clip(cx, 0, w - 1)
            cy = np.clip(cy, 0, h - 1)
            
            # Sample flow at center
            dx, dy = flow[cy, cx]
            
            # Apply flow to bbox
            new_x1 = x1 + dx
            new_y1 = y1 + dy
            new_x2 = x2 + dx
            new_y2 = y2 + dy
            
            # Clip to frame bounds
            new_x1 = np.clip(new_x1, 0, w)
            new_y1 = np.clip(new_y1, 0, h)
            new_x2 = np.clip(new_x2, 0, w)
            new_y2 = np.clip(new_y2, 0, h)
            
            prop_bboxes.append([new_x1, new_y1, new_x2, new_y2])
        
        return np.array(prop_bboxes)
    
    def _need_redetection(self, flow: np.ndarray, bboxes: np.ndarray) -> bool:
        """
        Determine if re-detection is needed based on flow magnitude
        
        Args:
            flow: Optical flow field
            bboxes: Current bounding boxes
            
        Returns:
            True if re-detection needed
        """
        # Compute average flow magnitude
        flow_mag = np.sqrt(flow[:, :, 0]**2 + flow[:, :, 1]**2)
        avg_flow = np.mean(flow_mag)
        max_flow = np.max(flow_mag)
        
        # Trigger re-detection if motion is too large
        if max_flow > self.redetection_threshold:
            self.logger.debug(f"Re-detection: max_flow={max_flow:.1f} > threshold={self.redetection_threshold}")
            return True
        
        # Check if any bbox goes out of bounds significantly
        if len(bboxes) > 0:
            h, w = flow.shape[:2]
            for bbox in bboxes:
                x1, y1, x2, y2 = bbox
                # Check if bbox is too small or malformed
                if x2 - x1 < 10 or y2 - y1 < 10:
                    self.logger.debug(f"Re-detection: bbox too small")
                    return True
                # Check if bbox is mostly out of frame
                if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                    out_of_bound_ratio = max(
                        abs(min(0, x1)) + abs(max(0, x2 - w)),
                        abs(min(0, y1)) + abs(max(0, y2 - h))
                    ) / max(x2 - x1, y2 - y1)
                    if out_of_bound_ratio > 0.3:
                        self.logger.debug(f"Re-detection: bbox out of bounds")
                        return True
        
        return False
    
    def visualize_propagation(self, 
                             frame: np.ndarray,
                             bboxes: np.ndarray,
                             is_keyframe: bool = False,
                             output_path: Optional[Path] = None) -> np.ndarray:
        """
        Visualize ROI propagation on frame
        
        Args:
            frame: Input frame
            bboxes: Bounding boxes
            is_keyframe: Whether this is a keyframe (detected) or propagated
            output_path: Optional path to save visualization
            
        Returns:
            Annotated frame
        """
        vis = frame.copy()
        
        # Color: Green for keyframe, Yellow for propagated
        color = (0, 255, 0) if is_keyframe else (0, 255, 255)
        thickness = 3 if is_keyframe else 2
        
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox.astype(int)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, thickness)
        
        # Add label
        label = "KEYFRAME" if is_keyframe else "PROPAGATED"
        cv2.putText(vis, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        if output_path:
            cv2.imwrite(str(output_path), vis)
        
        return vis
    
    def get_statistics(self, all_detections: List[Tuple], keyframe_interval: int) -> Dict:
        """
        Get propagation statistics
        
        Args:
            all_detections: List of detections for all frames
            keyframe_interval: Keyframe interval used
            
        Returns:
            Dictionary with statistics
        """
        n_frames = len(all_detections)
        n_keyframes = (n_frames + keyframe_interval - 1) // keyframe_interval
        n_propagations = n_frames - n_keyframes
        
        # Count detections per frame
        detection_counts = [len(det[0]) for det in all_detections]
        avg_detections = np.mean(detection_counts) if detection_counts else 0
        
        stats = {
            'total_frames': n_frames,
            'keyframes': n_keyframes,
            'propagations': n_propagations,
            'avg_detections_per_frame': avg_detections,
            'detection_reduction': (n_propagations / n_frames * 100) if n_frames > 0 else 0,
        }
        
        return stats
