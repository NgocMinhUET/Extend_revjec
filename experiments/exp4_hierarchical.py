"""
Experiment 4: Hierarchical ROI with Adaptive QP
3-level ROI hierarchy with content-adaptive QP control

IMPROVEMENTS over Exp3:
- 3-level ROI: Core, Context, Background
- Adaptive context ring based on object size
- Content-adaptive QP adjustment (texture + motion)
- Bitrate normalization

EXPECTED RESULTS:
- Better perceptual quality (smooth transitions)
- More efficient bitrate allocation
- Improved PSNR-MOTA tradeoff

WORKFLOW:
1. Load video sequence
2. Temporal ROI propagation (from Exp3)
3. Generate hierarchical ROI maps (3 levels)
4. Calculate adaptive QP for each level
5. Generate CTU-level QP maps
6. Encode with VVenC (uniform QP due to limitation)
7. Compare with baseline, exp2, exp3

NOTE: Same VVenC limitation (no CTU-level QP support)
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
from src.hierarchical_roi import HierarchicalROI
from src.qp_controller import QPController
from src.utils import load_config


def create_experiment_logger(name: str, log_file: Path, debug: bool = False) -> logging.Logger:
    """Create experiment logger"""
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
    parser = argparse.ArgumentParser(description='Hierarchical ROI Experiment')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to configuration file')
    parser.add_argument('--sequence', type=str, default=None,
                        help='Specific sequence to encode')
    parser.add_argument('--qp', type=int, nargs='+', default=[22, 27, 32, 37],
                        help='QP values to test')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Maximum frames to encode')
    parser.add_argument('--keyframe-interval', type=int, default=10,
                        help='Keyframe interval for detection')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--save-visualizations', action='store_true',
                        help='Save ROI and QP visualizations')
    return parser.parse_args()


def load_sequence(sequence_path, max_frames=None):
    """Load image sequence"""
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
    """Load all frames to memory"""
    frames = []
    for img_path in tqdm(image_paths, desc="Loading frames"):
        frame = cv2.imread(str(img_path))
        frames.append(frame)
    return frames


def images_to_yuv(images, output_yuv, logger):
    """Convert images to YUV"""
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


def run_hierarchical_roi_experiment(config_path, sequence_name=None, qp_values=[22, 27, 32, 37],
                                    max_frames=None, keyframe_interval=10,
                                    debug=False, save_visualizations=False):
    """Run Hierarchical ROI experiment"""
    
    config = load_config(config_path)
    
    # Override temporal config
    if 'roi_detection' not in config:
        config['roi_detection'] = {}
    if 'temporal' not in config['roi_detection']:
        config['roi_detection']['temporal'] = {}
    config['roi_detection']['temporal']['keyframe_interval'] = keyframe_interval
    
    # Setup logging
    log_dir = Path('results/logs/hierarchical_roi')
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = create_experiment_logger('hierarchical_roi', log_dir / 'hierarchical_roi.log', debug=debug)
    
    logger.info("="*60)
    logger.info("EXPERIMENT 4: HIERARCHICAL ROI + ADAPTIVE QP")
    logger.info("="*60)
    logger.warning("⚠️  LIMITATION: VVenC CLI does not support CTU-level QP maps")
    logger.warning("⚠️  This experiment demonstrates hierarchical ROI generation")
    logger.warning("⚠️  Actual encoding uses UNIFORM QP (results = baseline)")
    logger.info("="*60)
    logger.info(f"Configuration: {config_path}")
    logger.info(f"QP values: {qp_values}")
    logger.info(f"Keyframe interval: {keyframe_interval}")
    if max_frames:
        logger.info(f"Max frames: {max_frames} (test mode)")
    
    # Initialize components
    encoder = VVCEncoder(config, logger)
    encoder_info = encoder.get_encoder_info()
    logger.info(f"Encoder: {encoder_info['software']} v{encoder_info['version']}")
    
    detector = ROIDetector(config, logger)
    propagator = TemporalPropagator(config, logger)
    hierarchical_roi = HierarchicalROI(config, logger)
    qp_controller = QPController(config, logger)
    
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
            
            # Load frames to memory
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
            
            # Get propagation statistics
            prop_stats = propagator.get_statistics(all_detections, keyframe_interval)
            logger.info(f"Propagation: {prop_stats['keyframes']} keyframes, "
                       f"{prop_stats['propagations']} propagations "
                       f"({prop_stats['detection_reduction']:.1f}% reduction)")
            
            # Generate hierarchical ROI maps
            logger.info("Generating hierarchical ROI maps...")
            hierarchical_start = time.time()
            all_roi_maps = []
            all_qp_maps = []
            
            for i, (bboxes, _, _) in enumerate(tqdm(all_detections, desc="ROI generation")):
                # Generate hierarchical ROI
                roi_map = hierarchical_roi.generate_hierarchical_roi(
                    bboxes, width, height, motion_map=None
                )
                all_roi_maps.append(roi_map)
                
                # Generate QP map (will be averaged later)
                qp_map = qp_controller.generate_qp_map(
                    roi_map, base_qp=27, frame=frames[i], motion_map=None
                )
                all_qp_maps.append(qp_map)
            
            hierarchical_time = time.time() - hierarchical_start
            logger.info(f"Hierarchical ROI generation: {hierarchical_time:.2f}s")
            
            # Get ROI statistics from first frame
            roi_stats = hierarchical_roi.get_level_statistics(all_roi_maps[0])
            logger.info(f"ROI levels: Core={roi_stats['core']['percentage']:.1f}%, "
                       f"Context={roi_stats['context']['percentage']:.1f}%, "
                       f"Background={roi_stats['background']['percentage']:.1f}%")
            
            # Save visualizations if requested
            if save_visualizations:
                vis_dir = Path('results/visualizations/hierarchical_roi') / seq_name
                vis_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Saving visualizations to {vis_dir}")
                
                # Save every Nth frame
                vis_interval = max(1, len(frames) // 10)
                for i in range(0, len(frames), vis_interval):
                    # ROI visualization
                    roi_vis_path = vis_dir / f'roi_frame_{i:04d}.jpg'
                    hierarchical_roi.visualize_hierarchical_roi(
                        frames[i], all_roi_maps[i], str(roi_vis_path)
                    )
                    
                    # QP visualization
                    qp_vis_path = vis_dir / f'qp_frame_{i:04d}.jpg'
                    qp_controller.visualize_qp_map(
                        all_qp_maps[i], base_qp=27, output_path=str(qp_vis_path)
                    )
            
            # Convert to YUV
            yuv_path = Path('data/encoded') / f'{seq_name}_hierarchical.yuv'
            yuv_path.parent.mkdir(parents=True, exist_ok=True)
            
            images_to_yuv(image_paths, yuv_path, logger)
            
            # Encode with different QP values
            for qp in qp_values:
                output_path = Path('data/encoded') / f'{seq_name}_hierarchical_qp{qp}.266'
                
                logger.info(f"Encoding with QP={qp}...")
                
                # Generate averaged QP maps for this base QP
                qp_maps_for_qp = []
                for i, roi_map in enumerate(all_roi_maps):
                    qp_map = qp_controller.generate_qp_map(
                        roi_map, base_qp=qp, frame=frames[i], motion_map=None
                    )
                    # Convert to CTU level
                    ctu_qp_map = qp_controller.convert_to_ctu_qp_map(qp_map, ctu_size)
                    qp_maps_for_qp.append(ctu_qp_map)
                
                # Average QP map
                avg_ctu_qp_map = np.mean(qp_maps_for_qp, axis=0).astype(np.int32)
                
                # Get QP statistics
                sample_roi_ctu = hierarchical_roi.roi_map_to_ctu_map(all_roi_maps[0], ctu_size)
                qp_stats = qp_controller.get_qp_statistics(avg_ctu_qp_map, sample_roi_ctu)
                
                logger.info(f"  QP stats: Core={qp_stats['core']['mean_qp']:.1f}, "
                           f"Context={qp_stats['context']['mean_qp']:.1f}, "
                           f"BG={qp_stats['background']['mean_qp']:.1f}")
                
                # Encode
                stats = encoder.encode_with_qp_map(
                    input_file=str(yuv_path),
                    output_file=str(output_path),
                    base_qp=qp,
                    qp_map_array=avg_ctu_qp_map,
                    width=width,
                    height=height
                )
                
                # Save results
                result = {
                    'sequence': seq_name,
                    'qp': qp,
                    'keyframe_interval': keyframe_interval,
                    'bitrate': stats['bitrate'],
                    'psnr_y': stats['psnr_y'],
                    'psnr_u': stats['psnr_u'],
                    'psnr_v': stats['psnr_v'],
                    'encoding_time': stats['encoding_time'],
                    'detection_time': detection_time,
                    'hierarchical_time': hierarchical_time,
                    'total_time': stats['encoding_time'] + detection_time + hierarchical_time,
                    'frames': len(frames),
                    'width': width,
                    'height': height,
                    'roi_core_pct': roi_stats['core']['percentage'],
                    'roi_context_pct': roi_stats['context']['percentage'],
                    'roi_bg_pct': roi_stats['background']['percentage'],
                    'qp_core_mean': qp_stats['core']['mean_qp'],
                    'qp_context_mean': qp_stats['context']['mean_qp'],
                    'qp_bg_mean': qp_stats['background']['mean_qp'],
                    'n_keyframes': prop_stats['keyframes'],
                    'detection_reduction': prop_stats['detection_reduction'],
                }
                
                all_results.append(result)
                logger.info(f"QP={qp}: {stats['bitrate']:.2f} kbps, "
                           f"PSNR={stats['psnr_y']:.2f} dB, "
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
    results_file = results_dir / 'hierarchical_roi.csv'
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
                avg_total_time = qp_results['total_time'].mean()
                avg_core_pct = qp_results['roi_core_pct'].mean()
                logger.info(f"QP={qp}: {avg_bitrate:.2f} kbps, "
                           f"PSNR={avg_psnr:.2f} dB, "
                           f"Total={avg_total_time:.2f}s, "
                           f"Core ROI={avg_core_pct:.1f}%")


if __name__ == '__main__':
    args = parse_args()
    run_hierarchical_roi_experiment(
        args.config,
        args.sequence,
        args.qp,
        args.max_frames,
        args.keyframe_interval,
        args.debug,
        args.save_visualizations
    )
