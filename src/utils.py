"""
Utility functions for the Hierarchical Temporal ROI-VVC framework
"""

import os
import yaml
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load default config and merge
    default_config_path = Path(config_path).parent / "default_config.yaml"
    if default_config_path.exists() and config_path != str(default_config_path):
        with open(default_config_path, 'r') as f:
            default_config = yaml.safe_load(f)
        config = merge_configs(default_config, config)
    
    return config


def merge_configs(default: Dict, override: Dict) -> Dict:
    """
    Merge two configuration dictionaries
    
    Args:
        default: Default configuration
        override: Override configuration
        
    Returns:
        Merged configuration
    """
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def setup_logging(config: Dict) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Logger instance
    """
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    
    # Create logger
    logger = logging.getLogger('HT-ROI-VVC')
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    if log_config.get('console', True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_config.get('file', True):
        log_dir = Path(log_config.get('log_dir', './results/logs'))
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"{config['experiment']['name']}.log"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def create_output_dirs(config: Dict) -> Dict[str, Path]:
    """
    Create output directories
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary of output paths
    """
    output_config = config.get('output', {})
    
    dirs = {
        'results': Path(output_config.get('results_dir', './results')),
        'plots': Path(output_config.get('plots_dir', './results/plots')),
        'metrics': Path(output_config.get('metrics_dir', './results/metrics')),
        'encoded': Path(output_config.get('encoded_dir', './data/encoded')),
        'logs': Path(config['logging'].get('log_dir', './results/logs')),
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs


def bbox_iou(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
    """
    Calculate IoU between two bounding boxes
    
    Args:
        bbox1: [x1, y1, x2, y2]
        bbox2: [x1, y1, x2, y2]
        
    Returns:
        IoU value
    """
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0


def calculate_texture_complexity(frame: np.ndarray, 
                                 roi_mask: Optional[np.ndarray] = None) -> float:
    """
    Calculate texture complexity using gradient magnitude
    
    Args:
        frame: Input frame (H, W, 3) or (H, W)
        roi_mask: Optional ROI mask (H, W)
        
    Returns:
        Texture complexity score [0, 1]
    """
    # Convert to grayscale if needed
    if len(frame.shape) == 3:
        gray = np.mean(frame, axis=2)
    else:
        gray = frame
    
    # Calculate gradients
    gx = np.gradient(gray, axis=1)
    gy = np.gradient(gray, axis=0)
    gradient_magnitude = np.sqrt(gx**2 + gy**2)
    
    # Apply ROI mask if provided
    if roi_mask is not None:
        gradient_magnitude = gradient_magnitude * roi_mask
        n_pixels = np.sum(roi_mask > 0)
    else:
        n_pixels = gradient_magnitude.size
    
    # Normalize
    complexity = np.sum(gradient_magnitude) / (n_pixels * 255.0) if n_pixels > 0 else 0
    
    return min(1.0, complexity)


def calculate_motion_complexity(motion_vectors: np.ndarray) -> float:
    """
    Calculate motion complexity from motion vectors
    
    Args:
        motion_vectors: Motion vectors (H, W, 2)
        
    Returns:
        Motion complexity score [0, 1]
    """
    # Calculate motion magnitude
    motion_magnitude = np.sqrt(motion_vectors[..., 0]**2 + motion_vectors[..., 1]**2)
    
    # Calculate statistics
    mean_motion = np.mean(motion_magnitude)
    std_motion = np.std(motion_magnitude)
    
    # Normalize (assuming max motion of 50 pixels)
    complexity = (mean_motion + std_motion) / 50.0
    
    return min(1.0, complexity)


def resize_maintain_aspect(frame: np.ndarray, 
                           target_size: Tuple[int, int]) -> Tuple[np.ndarray, Tuple[float, float]]:
    """
    Resize frame while maintaining aspect ratio
    
    Args:
        frame: Input frame (H, W, C)
        target_size: Target size (width, height)
        
    Returns:
        Resized frame and scale factors (scale_x, scale_y)
    """
    import cv2
    
    h, w = frame.shape[:2]
    target_w, target_h = target_size
    
    # Calculate scale factors
    scale_w = target_w / w
    scale_h = target_h / h
    scale = min(scale_w, scale_h)
    
    # Calculate new size
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # Resize
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Pad to target size
    pad_w = target_w - new_w
    pad_h = target_h - new_h
    
    if pad_w > 0 or pad_h > 0:
        resized = cv2.copyMakeBorder(
            resized, 0, pad_h, 0, pad_w,
            cv2.BORDER_CONSTANT, value=(0, 0, 0)
        )
    
    return resized, (scale, scale)


def scale_bboxes(bboxes: np.ndarray, 
                 scale_factors: Tuple[float, float]) -> np.ndarray:
    """
    Scale bounding boxes
    
    Args:
        bboxes: Bounding boxes (N, 4) [x1, y1, x2, y2]
        scale_factors: Scale factors (scale_x, scale_y)
        
    Returns:
        Scaled bounding boxes
    """
    scale_x, scale_y = scale_factors
    scaled_bboxes = bboxes.copy()
    scaled_bboxes[:, [0, 2]] /= scale_x
    scaled_bboxes[:, [1, 3]] /= scale_y
    return scaled_bboxes


def save_roi_visualization(frame: np.ndarray,
                           roi_map: np.ndarray,
                           bboxes: np.ndarray,
                           output_path: str) -> None:
    """
    Save ROI visualization
    
    Args:
        frame: Input frame (H, W, 3)
        roi_map: ROI map (H, W) with levels 0, 1, 2
        bboxes: Bounding boxes (N, 4)
        output_path: Output file path
    """
    import cv2
    
    # Create visualization
    vis = frame.copy()
    
    # Overlay ROI map with transparency
    colors = {
        0: (128, 128, 128),  # Gray for background
        1: (0, 255, 255),    # Yellow for context
        2: (0, 255, 0),      # Green for core
    }
    
    overlay = np.zeros_like(vis)
    for level, color in colors.items():
        mask = roi_map == level
        overlay[mask] = color
    
    vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)
    
    # Draw bounding boxes
    for bbox in bboxes:
        x1, y1, x2, y2 = bbox.astype(int)
        cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 0, 0), 2)
    
    # Save
    cv2.imwrite(output_path, vis)


def calculate_ctu_statistics(roi_map: np.ndarray, 
                             ctu_size: int = 128) -> Dict[str, Any]:
    """
    Calculate CTU-level statistics
    
    Args:
        roi_map: ROI map (H, W) with levels 0, 1, 2
        ctu_size: CTU size
        
    Returns:
        Dictionary of statistics
    """
    h, w = roi_map.shape
    n_ctu_h = h // ctu_size
    n_ctu_w = w // ctu_size
    n_total = n_ctu_h * n_ctu_w
    
    # Count CTUs by level
    level_counts = {0: 0, 1: 0, 2: 0}
    
    for i in range(n_ctu_h):
        for j in range(n_ctu_w):
            ctu_roi = roi_map[i*ctu_size:(i+1)*ctu_size, 
                             j*ctu_size:(j+1)*ctu_size]
            dominant_level = np.argmax(np.bincount(ctu_roi.flatten(), minlength=3))
            level_counts[dominant_level] += 1
    
    return {
        'total_ctus': n_total,
        'background_ctus': level_counts[0],
        'context_ctus': level_counts[1],
        'core_ctus': level_counts[2],
        'background_ratio': level_counts[0] / n_total,
        'context_ratio': level_counts[1] / n_total,
        'core_ratio': level_counts[2] / n_total,
    }


def format_time(seconds: float) -> str:
    """
    Format time in seconds to human-readable string
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs:.1f}s"
    elif minutes > 0:
        return f"{minutes}m {secs:.1f}s"
    else:
        return f"{secs:.1f}s"


def check_file_exists(file_path: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Check if file exists and log warning if not
    
    Args:
        file_path: File path to check
        logger: Logger instance
        
    Returns:
        True if file exists, False otherwise
    """
    exists = os.path.exists(file_path)
    if not exists and logger:
        logger.warning(f"File not found: {file_path}")
    return exists
