"""
Experiment 5: Full System - Hierarchical Temporal ROI-VVC
Complete integration of all components
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import logging
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import cv2
import numpy as np
import time

from src.vvc_encoder import VVCEncoder
from src.roi_detector import ROIDetector
from src.temporal_propagator import TemporalPropagator
from src.hierarchical_roi import HierarchicalROI
from src.qp_controller import QPController
from src.utils import load_config

def create_experiment_logger(name, log_file, debug=False):
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    if logger.handlers:
        logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    file_h = logging.FileHandler(log_file)
    file_h.setLevel(level)
    file_h.setFormatter(formatter)
    logger.addHandler(file_h)
    return logger

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--sequence', default=None)
    parser.add_argument('--qp', type=int, nargs='+', default=[22,27,32,37])
    parser.add_argument('--max-frames', type=int, default=None)
    parser.add_argument('--keyframe-interval', type=int, default=10)
    parser.add_argument('--debug', action='store_true')
    return parser.parse_args()

def load_sequence(path, max_frames):
    img_dir = Path(path) / 'img1'
    images = sorted(img_dir.glob('*.jpg'))
    if max_frames: images = images[:max_frames]
    return images

def load_frames(paths):
    return [cv2.imread(str(p)) for p in tqdm(paths, desc="Loading")]

def to_yuv(images, output, logger):
    logger.info(f"Converting {len(images)} to YUV...")
    h, w = cv2.imread(str(images[0])).shape[:2]
    with open(output, 'wb') as f:
        for p in tqdm(images, desc="YUV"):
            yuv = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2YUV_I420)
            f.write(yuv.tobytes())
    return w, h, len(images)

def run_full_system(config_path, sequence_name=None, qp_values=[22,27,32,37],
                    max_frames=None, keyframe_interval=10, debug=False):
    config = load_config(config_path)
    if 'roi_detection' not in config: config['roi_detection'] = {}
    if 'temporal' not in config['roi_detection']: config['roi_detection']['temporal'] = {}
    config['roi_detection']['temporal']['keyframe_interval'] = keyframe_interval
    
    log_dir = Path('results/logs/full_system')
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = create_experiment_logger('full_system', log_dir/'full_system.log', debug)
    
    logger.info("="*60)
    logger.info("EXPERIMENT 5: FULL SYSTEM")
    logger.info("="*60)
    
    encoder = VVCEncoder(config, logger)
    detector = ROIDetector(config, logger)
    propagator = TemporalPropagator(config, logger)
    hierarchical = HierarchicalROI(config, logger)
    qp_controller = QPController(config, logger)
    
    ctu_size = config['encoder'].get('ctu_size', 128)
    dataset_root = Path(config['dataset']['root_dir'])
    dataset_name = config['dataset']['name']
    dataset_path = dataset_root / dataset_name
    
    sequences = [dataset_path/'train'/sequence_name] if sequence_name else \
                sorted([d for d in (dataset_path/'train').iterdir() if d.is_dir()])
    
    all_results = []
    
    for seq_path in sequences:
        seq_name = seq_path.name
        logger.info(f"\nProcessing: {seq_name}")
        
        try:
            image_paths = load_sequence(seq_path, max_frames)
            frames = load_frames(image_paths)
            h, w = frames[0].shape[:2]
            
            # Temporal propagation
            det_start = time.time()
            detections = propagator.propagate_roi_sequence(frames, detector, keyframe_interval)
            det_time = time.time() - det_start
            
            # Hierarchical ROI
            hier_start = time.time()
            roi_maps = [hierarchical.generate_hierarchical_roi(d[0], w, h) for d in tqdm(detections, desc="ROI")]
            hier_time = time.time() - hier_start
            
            # YUV conversion
            yuv_path = Path('data/encoded')/f'{seq_name}_full.yuv'
            yuv_path.parent.mkdir(parents=True, exist_ok=True)
            to_yuv(image_paths, yuv_path, logger)
            
            # Encode with different QPs
            for qp in qp_values:
                output = Path('data/encoded')/f'{seq_name}_full_qp{qp}.266'
                
                # Generate QP maps
                qp_maps = [qp_controller.generate_qp_map(roi, qp, frames[i]) 
                          for i, roi in enumerate(tqdm(roi_maps, desc=f"QP{qp}"))]
                ctu_qp_maps = [qp_controller.convert_to_ctu_qp_map(qm, ctu_size) for qm in qp_maps]
                avg_ctu_qp = np.mean(ctu_qp_maps, axis=0).astype(np.int32)
                
                # Encode
                stats = encoder.encode_with_qp_map(str(yuv_path), str(output), qp, avg_ctu_qp, w, h)
                
                result = {
                    'sequence': seq_name, 'qp': qp, 'bitrate': stats['bitrate'],
                    'psnr_y': stats['psnr_y'], 'encoding_time': stats['encoding_time'],
                    'detection_time': det_time, 'hierarchical_time': hier_time,
                    'total_time': stats['encoding_time'] + det_time + hier_time,
                    'frames': len(frames), 'keyframe_interval': keyframe_interval
                }
                all_results.append(result)
                logger.info(f"QP={qp}: {stats['bitrate']:.2f}kbps, PSNR={stats['psnr_y']:.2f}dB")
        
        except Exception as e:
            logger.error(f"Error: {e}")
            continue
    
    # Save results
    df = pd.DataFrame(all_results)
    results_file = Path('results/metrics/full_system.csv')
    results_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(results_file, index=False)
    logger.info(f"Results saved: {results_file}")

if __name__ == '__main__':
    args = parse_args()
    run_full_system(args.config, args.sequence, args.qp, args.max_frames, 
                    args.keyframe_interval, args.debug)
