"""
Experiment 3: Temporal ROI Propagation
Reduce detection overhead by propagating ROI from keyframes

IMPROVEMENTS over Exp2:
- Detect ROI only on keyframes (every N frames)
- Propagate ROI to other frames using optical flow
- Adaptive re-detection when motion is large
- Significantly reduced computational cost

EXPECTED RESULTS:
- Detection overhead: 10x reduction (detect every 10 frames)
- Bitrate/PSNR: Similar to Exp2 (assuming good propagation)
- Total encoding time: Reduced due to less detection

WORKFLOW:
1. Load video sequence
2. Detect ROI on keyframes only (frame 0, 10, 20, ...)
3. Propagate ROI to intermediate frames using optical flow
4. Generate QP maps for all frames
5. Encode with VVenC (currently uniform QP due to limitation)
6. Compare with baseline and exp2

NOTE: Same VVenC limitation as Exp2 (no CTU-level QP support)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import logging
from pathlib import Path
from typing import List
import pandas as pd
from tqdm import tqdm
import cv2
import numpy as np
import time

from src.vvc_encoder import VVCEncoder
from src.roi_detector import ROIDetector
from src.temporal_propagator import TemporalPropagator
from src.utils import load_config


def create_experiment_logger(name: str, log_file: Path, debug: bool = False) -> logging.Logger:
    """Create a simple logger for experiments with console + file handlers."""
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def parse_args():
    parser = argparse.ArgumentParser(description='Temporal ROI Propagation Experiment')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to configuration file')
    parser.add_argument('--sequence', type=str, default=None,
                        help='Specific sequence to encode (default: all)')
    parser.add_argument('--qp', type=int, nargs='+', default=[22, 27, 32, 37],
                        help='QP values to test')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Maximum frames to encode (for testing, default: all)')
    parser.add_argument('--keyframe-interval', type=int, default=10,
                        help='Keyframe interval for detection (default: 10)')
    parser.add_argument('--delta-qp-roi', type=int, default=5,
                        help='QP offset for ROI regions (default: -5)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--save-visualizations', action='store_true',
                        help='Save propagation visualizations')
    return parser.parse_args()


def load_sequence(sequence_path, max_frames=None):
    """Load image sequence from MOT dataset"""
    img_dir = Path(sequence_path) / 'img1'
    if not img_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {img_dir}")
    
    images = sorted(img_dir.glob('*.jpg'))
    if not images:
        raise ValueError(f"No images found in {img_dir}")
    
    if max_frames is not None and max_frames > 0:
        images = images[:max_frames]
    
    return images


def load_frames_to_memory(image_paths: List[Path]) -> List[np.ndarray]:
    """Load all frames to memory for processing"""
    frames = []
    for img_path in tqdm(image_paths, desc="Loading frames"):
        frame = cv2.imread(str(img_path))
        frames.append(frame)
    return frames


def images_to_yuv(images, output_yuv, logger):
    """Convert image sequence to YUV format for VVenC"""
    logger.info(f"Converting {len(images)} images to YUV...")
    
    first_frame = cv2.imread(str(images[0]))
    height, width = first_frame.shape[:2]
    
    with open(output_yuv, 'wb') as f:
        for img_path in tqdm(images, desc="Converting to YUV"):
            bgr = cv2.imread(str(img_path))
            yuv = cv2.cvtColor(bgr, cv2.COLOR_BGR2YUV_I420)
            f.write(yuv.tobytes())
    
    logger.info(f"YUV file created: {output_yuv}")
    return width, height, len(images)


def generate_qp_map(bboxes: np.ndarray, width: int, height: int, 
                    base_qp: int, delta_qp_roi: int, ctu_size: int) -> np.ndarray:
    """Generate CTU-level QP map from bounding boxes"""
    n_ctu_w = (width + ctu_size - 1) // ctu_size
    n_ctu_h = (height + ctu_size - 1) // ctu_size
    
    qp_map = np.full((n_ctu_h, n_ctu_w), base_qp, dtype=np.int32)
    
    for bbox in bboxes:
        x1, y1, x2, y2 = bbox
        
        ctu_x1 = int(x1 // ctu_size)
        ctu_y1 = int(y1 // ctu_size)
        ctu_x2 = int(x2 // ctu_size)
        ctu_y2 = int(y2 // ctu_size)
        
        ctu_x1 = max(0, ctu_x1)
        ctu_y1 = max(0, ctu_y1)
        ctu_x2 = min(n_ctu_w - 1, ctu_x2)
        ctu_y2 = min(n_ctu_h - 1, ctu_y2)
        
        qp_map[ctu_y1:ctu_y2+1, ctu_x1:ctu_x2+1] = base_qp - delta_qp_roi
    
    return qp_map


def run_temporal_roi_experiment(config_path, sequence_name=None, qp_values=[22, 27, 32, 37], 
                                max_frames=None, keyframe_interval=10, delta_qp_roi=5, 
                                debug=False, save_visualizations=False):
    """Run Temporal ROI Propagation experiment"""
    
    config = load_config(config_path)
    
    # Override temporal config
    if 'roi_detection' not in config:
        config['roi_detection'] = {}
    if 'temporal' not in config['roi_detection']:
        config['roi_detection']['temporal'] = {}
    config['roi_detection']['temporal']['keyframe_interval'] = keyframe_interval
    
    # Setup logging
    log_dir = Path('results/logs/temporal_roi')
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = create_experiment_logger('temporal_roi', log_dir / 'temporal_roi.log', debug=debug)
    
    logger.info("="*60)
    logger.info("EXPERIMENT 3: TEMPORAL ROI PROPAGATION")
    logger.info("="*60)
    logger.warning("⚠️  LIMITATION: VVenC CLI does not support CTU-level QP maps")
    logger.warning("⚠️  This experiment demonstrates temporal propagation efficiency")
    logger.warning("⚠️  Actual encoding uses UNIFORM QP (results = baseline)")
    logger.info("="*60)
    logger.info(f"Configuration: {config_path}")
    logger.info(f"QP values: {qp_values}")
    logger.info(f"Keyframe interval: {keyframe_interval}")
    logger.info(f"Delta QP ROI: -{delta_qp_roi} (for QP map generation only)")
    if max_frames:
        logger.info(f"Max frames: {max_frames} (test mode)")
    
    # Initialize components
    encoder = VVCEncoder(config, logger)
    encoder_info = encoder.get_encoder_info()
    logger.info(f"Encoder: {encoder_info['software']} v{encoder_info['version']}")
    
    detector = ROIDetector(config, logger)
    propagator = TemporalPropagator(config, logger)
    
    ctu_size = config['encoder'].get('ctu_size', 128)
    logger.info(f"CTU size: {ctu_size}x{ctu_size}")
    
    # Get dataset path
    dataset_root = Path(config['dataset']['root_dir'])
    dataset_name = config['dataset']['name']
    dataset_path = dataset_root / dataset_name
    sequences_to_process = []
    
    if sequence_name:
        sequences_to_process = [dataset_path / 'train' / sequence_name]
    else:
        train_dir = dataset_path / 'train'
        if train_dir.exists():
            sequences_to_process = sorted([d for d in train_dir.iterdir() if d.is_dir()])
        else:
            logger.error(f"Training directory not found: {train_dir}")
            return
    
    all_results = []
    
    # Process each sequence
    for seq_path in sequences_to_process:
        seq_name = seq_path.name
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing sequence: {seq_name}")
        logger.info(f"{'='*60}")
        
        try:
            # Load images
            image_paths = load_sequence(seq_path, max_frames)
            logger.info(f"Found {len(image_paths)} frames")
            
            # Load frames to memory for propagation
            logger.info("Loading frames to memory...")
            frames = load_frames_to_memory(image_paths)
            height, width = frames[0].shape[:2]
            logger.info(f"Resolution: {width}x{height}")
            
            # Temporal ROI propagation
            logger.info(f"Running temporal propagation (interval={keyframe_interval})...")
            detection_start = time.time()
            all_detections = propagator.propagate_roi_sequence(
                frames, detector, detector_interval=keyframe_interval
            )
            detection_time = time.time() - detection_start
            
            # Get statistics
            prop_stats = propagator.get_statistics(all_detections, keyframe_interval)
            logger.info(f"Propagation statistics:")
            logger.info(f"  Total frames: {prop_stats['total_frames']}")
            logger.info(f"  Keyframes (detected): {prop_stats['keyframes']}")
            logger.info(f"  Propagated frames: {prop_stats['propagations']}")
            logger.info(f"  Detection reduction: {prop_stats['detection_reduction']:.1f}%")
            logger.info(f"  Detection time: {detection_time:.2f}s")
            logger.info(f"  Avg detections/frame: {prop_stats['avg_detections_per_frame']:.1f}")
            
            # Save visualizations if requested
            if save_visualizations:
                vis_dir = Path('results/visualizations/temporal_propagation') / seq_name
                vis_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Saving visualizations to {vis_dir}")
                
                # Save every Nth frame
                vis_interval = max(1, len(frames) // 10)
                for i in range(0, len(frames), vis_interval):
                    is_keyframe = (i % keyframe_interval == 0)
                    bboxes = all_detections[i][0]
                    vis_path = vis_dir / f'frame_{i:04d}.jpg'
                    propagator.visualize_propagation(frames[i], bboxes, is_keyframe, vis_path)
            
            # Convert to YUV
            yuv_path = Path('data/encoded') / f'{seq_name}_temporal_roi.yuv'
            yuv_path.parent.mkdir(parents=True, exist_ok=True)
            
            images_to_yuv(image_paths, yuv_path, logger)
            
            # Encode with different QP values
            for qp in qp_values:
                output_path = Path('data/encoded') / f'{seq_name}_temporal_roi_qp{qp}.266'
                
                logger.info(f"Encoding with QP={qp}...")
                
                # Generate averaged QP map (same as exp2, but with propagated detections)
                qp_maps = []
                for bboxes, _, _ in all_detections:
                    qp_map = generate_qp_map(bboxes, width, height, qp, delta_qp_roi, ctu_size)
                    qp_maps.append(qp_map)
                avg_qp_map = np.mean(qp_maps, axis=0).astype(np.int32)
                
                # ROI statistics
                n_roi_ctus = np.sum(avg_qp_map < qp)
                n_total_ctus = avg_qp_map.size
                roi_percentage = (n_roi_ctus / n_total_ctus) * 100
                
                logger.info(f"  ROI CTUs: {n_roi_ctus}/{n_total_ctus} ({roi_percentage:.1f}%)")
                
                # Encode
                stats = encoder.encode_with_qp_map(
                    input_file=str(yuv_path),
                    output_file=str(output_path),
                    base_qp=qp,
                    qp_map_array=avg_qp_map,
                    width=width,
                    height=height
                )
                
                # Save results
                result = {
                    'sequence': seq_name,
                    'qp': qp,
                    'keyframe_interval': keyframe_interval,
                    'delta_qp_roi': delta_qp_roi,
                    'bitrate': stats['bitrate'],
                    'psnr_y': stats['psnr_y'],
                    'psnr_u': stats['psnr_u'],
                    'psnr_v': stats['psnr_v'],
                    'encoding_time': stats['encoding_time'],
                    'detection_time': detection_time,
                    'total_time': stats['encoding_time'] + detection_time,
                    'frames': len(frames),
                    'width': width,
                    'height': height,
                    'roi_percentage': roi_percentage,
                    'n_keyframes': prop_stats['keyframes'],
                    'n_propagations': prop_stats['propagations'],
                    'detection_reduction': prop_stats['detection_reduction'],
                }
                
                all_results.append(result)
                logger.info(f"QP={qp}: {stats['bitrate']:.2f} kbps, "
                           f"PSNR={stats['psnr_y']:.2f} dB, "
                           f"Enc={stats['encoding_time']:.2f}s, "
                           f"Det={detection_time:.2f}s, "
                           f"Total={result['total_time']:.2f}s")
        
        except Exception as e:
            logger.error(f"Error processing {seq_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    # Save results to CSV
    df = pd.DataFrame(all_results)
    results_dir = Path('results/metrics')
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / 'temporal_roi.csv'
    df.to_csv(results_file, index=False)
    
    logger.info(f"\n{'='*60}")
    logger.info("EXPERIMENT COMPLETED")
    logger.info(f"{'='*60}")
    logger.info(f"Results saved to: {results_file}")
    logger.info(f"Total sequences processed: {len(sequences_to_process)}")
    
    # Print summary
    if not df.empty:
        logger.info("\nSummary by QP:")
        for qp in qp_values:
            qp_results = df[df['qp'] == qp]
            if not qp_results.empty:
                avg_bitrate = qp_results['bitrate'].mean()
                avg_psnr = qp_results['psnr_y'].mean()
                avg_detection_time = qp_results['detection_time'].mean()
                avg_total_time = qp_results['total_time'].mean()
                avg_detection_reduction = qp_results['detection_reduction'].mean()
                logger.info(f"QP={qp}: {avg_bitrate:.2f} kbps, "
                           f"PSNR={avg_psnr:.2f} dB, "
                           f"Det={avg_detection_time:.2f}s, "
                           f"Total={avg_total_time:.2f}s, "
                           f"Detection reduction={avg_detection_reduction:.1f}%")
    else:
        logger.warning("No results to summarize - all sequences failed to process")


if __name__ == '__main__':
    args = parse_args()
    run_temporal_roi_experiment(
        args.config, 
        args.sequence, 
        args.qp, 
        args.max_frames, 
        args.keyframe_interval,
        args.delta_qp_roi,
        args.debug,
        args.save_visualizations
    )
