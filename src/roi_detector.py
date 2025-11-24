"""
ROI Detector Module
Handles object detection using YOLO for ROI extraction
"""

import numpy as np
import torch
import cv2
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import logging


class ROIDetector:
    """
    ROI Detector using YOLOv8 for object detection
    """
    
    def __init__(self, config: Dict, logger: Optional[logging.Logger] = None):
        """
        Initialize ROI Detector
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.roi_config = config['roi_detection']
        self.logger = logger or logging.getLogger(__name__)
        
        # Detection parameters
        self.detector_type = self.roi_config['detector']
        self.model_size = self.roi_config['model_size']
        self.confidence_threshold = self.roi_config['confidence_threshold']
        self.nms_threshold = self.roi_config['nms_threshold']
        self.device = self.roi_config['device']
        
        # Load model
        self.model = self._load_model()
        
        self.logger.info(f"ROI Detector initialized: {self.detector_type}{self.model_size}")
    
    def _load_model(self):
        """
        Load detection model
        
        Returns:
            Loaded model
        """
        try:
            from ultralytics import YOLO
            
            # Model path
            model_name = f"{self.detector_type}{self.model_size}.pt"
            model_path = Path("models") / model_name
            
            if not model_path.exists():
                self.logger.info(f"Downloading {model_name}...")
                model = YOLO(model_name)  # Will download automatically
            else:
                model = YOLO(str(model_path))
            
            # Move to device
            model.to(self.device)
            
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Detect objects in frame
        
        Args:
            frame: Input frame (H, W, 3) in BGR format
            
        Returns:
            Tuple of (bboxes, scores, class_ids)
            - bboxes: (N, 4) array of [x1, y1, x2, y2]
            - scores: (N,) array of confidence scores
            - class_ids: (N,) array of class IDs
        """
        try:
            # Run detection
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                iou=self.nms_threshold,
                verbose=False
            )
            
            # Extract results
            if len(results) > 0 and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                bboxes = boxes.xyxy.cpu().numpy()  # (N, 4) [x1, y1, x2, y2]
                scores = boxes.conf.cpu().numpy()  # (N,)
                class_ids = boxes.cls.cpu().numpy().astype(int)  # (N,)
            else:
                bboxes = np.empty((0, 4))
                scores = np.empty((0,))
                class_ids = np.empty((0,), dtype=int)
            
            return bboxes, scores, class_ids
            
        except Exception as e:
            self.logger.error(f"Detection failed: {e}")
            return np.empty((0, 4)), np.empty((0,)), np.empty((0,), dtype=int)
    
    def detect_batch(self, frames: List[np.ndarray]) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """
        Detect objects in batch of frames
        
        Args:
            frames: List of frames
            
        Returns:
            List of (bboxes, scores, class_ids) tuples
        """
        batch_size = self.roi_config.get('batch_size', 1)
        results = []
        
        for i in range(0, len(frames), batch_size):
            batch = frames[i:i+batch_size]
            
            try:
                # Run batch detection
                batch_results = self.model(
                    batch,
                    conf=self.confidence_threshold,
                    iou=self.nms_threshold,
                    verbose=False
                )
                
                # Extract results for each frame
                for result in batch_results:
                    if len(result.boxes) > 0:
                        boxes = result.boxes
                        bboxes = boxes.xyxy.cpu().numpy()
                        scores = boxes.conf.cpu().numpy()
                        class_ids = boxes.cls.cpu().numpy().astype(int)
                    else:
                        bboxes = np.empty((0, 4))
                        scores = np.empty((0,))
                        class_ids = np.empty((0,), dtype=int)
                    
                    results.append((bboxes, scores, class_ids))
                    
            except Exception as e:
                self.logger.error(f"Batch detection failed: {e}")
                # Return empty results for failed batch
                for _ in range(len(batch)):
                    results.append((np.empty((0, 4)), np.empty((0,)), np.empty((0,), dtype=int)))
        
        return results
    
    def filter_by_class(self,
                       bboxes: np.ndarray,
                       scores: np.ndarray,
                       class_ids: np.ndarray,
                       target_classes: Optional[List[int]] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Filter detections by class
        
        Args:
            bboxes: Bounding boxes (N, 4)
            scores: Confidence scores (N,)
            class_ids: Class IDs (N,)
            target_classes: List of target class IDs (None = all classes)
            
        Returns:
            Filtered (bboxes, scores, class_ids)
        """
        if target_classes is None or len(bboxes) == 0:
            return bboxes, scores, class_ids
        
        # Filter by class
        mask = np.isin(class_ids, target_classes)
        return bboxes[mask], scores[mask], class_ids[mask]
    
    def filter_by_size(self,
                      bboxes: np.ndarray,
                      scores: np.ndarray,
                      class_ids: np.ndarray,
                      min_size: int = 10,
                      max_size: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Filter detections by bounding box size
        
        Args:
            bboxes: Bounding boxes (N, 4)
            scores: Confidence scores (N,)
            class_ids: Class IDs (N,)
            min_size: Minimum box size (width or height)
            max_size: Maximum box size (None = no limit)
            
        Returns:
            Filtered (bboxes, scores, class_ids)
        """
        if len(bboxes) == 0:
            return bboxes, scores, class_ids
        
        # Calculate box sizes
        widths = bboxes[:, 2] - bboxes[:, 0]
        heights = bboxes[:, 3] - bboxes[:, 1]
        
        # Filter by size
        mask = (widths >= min_size) & (heights >= min_size)
        if max_size is not None:
            mask &= (widths <= max_size) & (heights <= max_size)
        
        return bboxes[mask], scores[mask], class_ids[mask]
    
    def visualize_detections(self,
                            frame: np.ndarray,
                            bboxes: np.ndarray,
                            scores: np.ndarray,
                            class_ids: np.ndarray,
                            class_names: Optional[Dict[int, str]] = None) -> np.ndarray:
        """
        Visualize detections on frame
        
        Args:
            frame: Input frame (H, W, 3)
            bboxes: Bounding boxes (N, 4)
            scores: Confidence scores (N,)
            class_ids: Class IDs (N,)
            class_names: Dictionary mapping class IDs to names
            
        Returns:
            Visualized frame
        """
        vis_frame = frame.copy()
        
        for bbox, score, class_id in zip(bboxes, scores, class_ids):
            x1, y1, x2, y2 = bbox.astype(int)
            
            # Draw bounding box
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            if class_names is not None and class_id in class_names:
                label = f"{class_names[class_id]}: {score:.2f}"
            else:
                label = f"Class {class_id}: {score:.2f}"
            
            # Draw label background
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(vis_frame, (x1, y1 - label_h - 5), (x1 + label_w, y1), (0, 255, 0), -1)
            
            # Draw label text
            cv2.putText(vis_frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        return vis_frame
    
    def get_model_info(self) -> Dict:
        """
        Get model information
        
        Returns:
            Dictionary with model info
        """
        return {
            'detector': self.detector_type,
            'model_size': self.model_size,
            'device': self.device,
            'confidence_threshold': self.confidence_threshold,
            'nms_threshold': self.nms_threshold,
        }
    
    def benchmark(self, frame: np.ndarray, n_runs: int = 100) -> Dict:
        """
        Benchmark detection speed
        
        Args:
            frame: Test frame
            n_runs: Number of runs
            
        Returns:
            Dictionary with benchmark results
        """
        import time
        
        # Warmup
        for _ in range(10):
            self.detect(frame)
        
        # Benchmark
        times = []
        for _ in range(n_runs):
            start = time.time()
            self.detect(frame)
            end = time.time()
            times.append(end - start)
        
        times = np.array(times)
        
        return {
            'mean_time': np.mean(times),
            'std_time': np.std(times),
            'min_time': np.min(times),
            'max_time': np.max(times),
            'fps': 1.0 / np.mean(times),
        }
