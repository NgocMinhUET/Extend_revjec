"""
Experiment 2: Decoder-ROI based VVC Encoding
Reproduce original paper results with YOLO-based ROI detection and adaptive QP mapping

CHECKLIST:
[x] ROIDetector available (src/roi_detector.py)
[x] VVCEncoder.encode_with_qp_map available (src/vvc_encoder.py)
[x] QP map format verified (CTU-level grid)
[x] Detection workflow clear (YOLO -> bboxes -> QP map)
[ ] Test with sample sequence
[ ] Verify QP map generation
[ ] Compare with baseline results

WORKFLOW:
1. Load video sequence
2. Detect ROI with YOLOv8 for each frame
3. Generate CTU-level QP map (ROI: lower QP, Background: base QP)
4. Encode with VVenC using QP map
5. Compare bitrate/PSNR with baseline

EXPECTED RESULTS (from paper):
- Bitrate reduction: 15-25%
- PSNR degradation: < 1 dB
- Detection overhead: minimal
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

from src.vvc_encoder import VVCEncoder
from src.roi_detector import ROIDetector
from src.utils import load_config


def create_experiment_logger(name: str, log_file: Path, debug: bool = False) -> logging.Logger:
    """Create a simple logger for experiments with console + file handlers."""
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # Avoid duplicate handlers when rerunning
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
    parser = argparse.ArgumentParser(description='Decoder-ROI VVC Encoding Experiment')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to configuration file')
    parser.add_argument('--sequence', type=str, default=None,
                        help='Specific sequence to encode (default: all)')
    parser.add_argument('--qp', type=int, nargs='+', default=[22, 27, 32, 37],
                        help='QP values to test')
    parser.add_argument('--max-frames', type=int, default=None,
                        help='Maximum frames to encode (for testing, default: all)')
    parser.add_argument('--delta-qp-roi', type=int, default=5,
                        help='QP offset for ROI regions (default: -5)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--save-qp-maps', action='store_true',
                        help='Save QP maps as images for visualization')
    return parser.parse_args()


def load_sequence(sequence_path, max_frames=None):
    """Load image sequence from MOT dataset"""
    img_dir = Path(sequence_path) / 'img1'
    if not img_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {img_dir}")
    
    # Get all images
    images = sorted(img_dir.glob('*.jpg'))
    if not images:
        raise ValueError(f"No images found in {img_dir}")
    
    # Limit frames if specified
    if max_frames is not None and max_frames > 0:
        images = images[:max_frames]
    
    return images


def images_to_yuv(images, output_yuv, logger):
    """Convert image sequence to YUV format for VVenC"""
    logger.info(f"Converting {len(images)} images to YUV...")
    
    # Read first image to get dimensions
    first_frame = cv2.imread(str(images[0]))
    height, width = first_frame.shape[:2]
    
    # Create YUV file
    with open(output_yuv, 'wb') as f:
        for img_path in tqdm(images, desc="Converting to YUV"):
            # Read image
            bgr = cv2.imread(str(img_path))
            
            # Convert BGR to YUV420
            yuv = cv2.cvtColor(bgr, cv2.COLOR_BGR2YUV_I420)
            
            # Write to file
            f.write(yuv.tobytes())
    
    logger.info(f"YUV file created: {output_yuv}")
    return width, height, len(images)


def generate_qp_map(bboxes: np.ndarray, width: int, height: int, 
                    base_qp: int, delta_qp_roi: int, ctu_size: int) -> np.ndarray:
    """
    Generate CTU-level QP map from bounding boxes
    
    Args:
        bboxes: Detection bounding boxes (N, 4) [x1, y1, x2, y2]
        width: Frame width
        height: Frame height
        base_qp: Base QP value for background
        delta_qp_roi: QP offset for ROI (negative to reduce QP)
        ctu_size: CTU size (typically 128)
        
    Returns:
        QP map array (n_ctu_h, n_ctu_w)
        
    NOTE:
        - ROI regions get lower QP (higher quality): base_qp - delta_qp_roi
        - Background regions get base QP
        - CTU is marked as ROI if it has ANY overlap with bbox
    """
    # Calculate CTU grid dimensions
    n_ctu_w = (width + ctu_size - 1) // ctu_size
    n_ctu_h = (height + ctu_size - 1) // ctu_size
    
    # Initialize QP map with base QP (background)
    qp_map = np.full((n_ctu_h, n_ctu_w), base_qp, dtype=np.int32)
    
    # Process each bounding box
    for bbox in bboxes:
        x1, y1, x2, y2 = bbox
        
        # Convert pixel coordinates to CTU coordinates
        ctu_x1 = int(x1 // ctu_size)
        ctu_y1 = int(y1 // ctu_size)
        ctu_x2 = int(x2 // ctu_size)
        ctu_y2 = int(y2 // ctu_size)
        
        # Clip to valid range
        ctu_x1 = max(0, ctu_x1)
        ctu_y1 = max(0, ctu_y1)
        ctu_x2 = min(n_ctu_w - 1, ctu_x2)
        ctu_y2 = min(n_ctu_h - 1, ctu_y2)
        
        # Mark ROI CTUs with lower QP (higher quality)
        qp_map[ctu_y1:ctu_y2+1, ctu_x1:ctu_x2+1] = base_qp - delta_qp_roi
    
    return qp_map


def save_qp_map_visualization(qp_map: np.ndarray, output_path: Path, 
                               frame: np.ndarray = None):
    """
    Save QP map as visualization image
    
    Args:
        qp_map: QP map array (n_ctu_h, n_ctu_w)
        output_path: Output image path
        frame: Optional original frame for overlay
    """
    # Normalize QP map to 0-255 for visualization
    qp_min, qp_max = qp_map.min(), qp_map.max()
    if qp_max > qp_min:
        qp_vis = ((qp_map - qp_min) / (qp_max - qp_min) * 255).astype(np.uint8)
    else:
        qp_vis = np.zeros_like(qp_map, dtype=np.uint8)
    
    # Apply colormap (lower QP = warmer color)
    qp_vis = cv2.applyColorMap(255 - qp_vis, cv2.COLORMAP_JET)
    
    # Resize to match frame size if provided
    if frame is not None:
        h, w = frame.shape[:2]
        qp_vis = cv2.resize(qp_vis, (w, h), interpolation=cv2.INTER_NEAREST)
        
        # Overlay on frame with transparency
        overlay = cv2.addWeighted(frame, 0.6, qp_vis, 0.4, 0)
        cv2.imwrite(str(output_path), overlay)
    else:
        cv2.imwrite(str(output_path), qp_vis)


def encode_sequence_with_roi(images, yuv_path, output_path, qp, 
                             width, height, encoder, detector, 
                             delta_qp_roi, ctu_size, logger,
                             save_qp_maps=False):
    """
    Encode sequence with ROI-based QP mapping
    
    Args:
        images: List of image paths
        yuv_path: Path to YUV file
        output_path: Output bitstream path
        qp: Base QP value
        width: Frame width
        height: Frame height
        encoder: VVCEncoder instance
        detector: ROIDetector instance
        delta_qp_roi: QP offset for ROI
        ctu_size: CTU size
        logger: Logger instance
        save_qp_maps: Whether to save QP map visualizations
        
    Returns:
        Encoding statistics
    """
    logger.info(f"Encoding with Decoder-ROI (QP={qp}, delta_ROI={delta_qp_roi})...")
    
    # Detect ROI for all frames
    logger.info("Detecting ROI in all frames...")
    all_detections = []
    
    for img_path in tqdm(images, desc="ROI Detection"):
        frame = cv2.imread(str(img_path))
        bboxes, scores, class_ids = detector.detect(frame)
        all_detections.append(bboxes)
        
        # Save first frame QP map for visualization
        if save_qp_maps and len(all_detections) == 1:
            qp_map = generate_qp_map(bboxes, width, height, qp, delta_qp_roi, ctu_size)
            vis_dir = Path('results/visualizations/qp_maps')
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            seq_name = output_path.stem.replace('_decoder_roi', '').replace(f'_qp{qp}', '')
            vis_path = vis_dir / f'{seq_name}_qp{qp}_frame0.jpg'
            save_qp_map_visualization(qp_map, vis_path, frame)
            logger.info(f"QP map visualization saved: {vis_path}")
    
    # Calculate average QP map across all frames
    logger.info("Generating averaged QP map...")
    qp_maps = []
    for bboxes in all_detections:
        qp_map = generate_qp_map(bboxes, width, height, qp, delta_qp_roi, ctu_size)
        qp_maps.append(qp_map)
    
    # Average QP maps (simple averaging for now)
    # NOTE: For more advanced methods, can use temporal consistency
    avg_qp_map = np.mean(qp_maps, axis=0).astype(np.int32)
    
    # Count ROI vs background CTUs
    n_roi_ctus = np.sum(avg_qp_map < qp)
    n_total_ctus = avg_qp_map.size
    roi_percentage = (n_roi_ctus / n_total_ctus) * 100
    
    logger.info(f"QP Map statistics:")
    logger.info(f"  Total CTUs: {n_total_ctus}")
    logger.info(f"  ROI CTUs: {n_roi_ctus} ({roi_percentage:.1f}%)")
    logger.info(f"  Background CTUs: {n_total_ctus - n_roi_ctus} ({100-roi_percentage:.1f}%)")
    logger.info(f"  QP range: {avg_qp_map.min()} - {avg_qp_map.max()}")
    
    # Encode with QP map
    stats = encoder.encode_with_qp_map(
        input_file=str(yuv_path),
        output_file=str(output_path),
        base_qp=qp,
        qp_map_array=avg_qp_map,
        width=width,
        height=height
    )
    
    # Add ROI statistics to results
    stats['roi_percentage'] = roi_percentage
    stats['n_roi_ctus'] = n_roi_ctus
    stats['n_total_ctus'] = n_total_ctus
    
    return stats


def run_decoder_roi_experiment(config_path, sequence_name=None, qp_values=[22, 27, 32, 37], 
                               max_frames=None, delta_qp_roi=5, debug=False, save_qp_maps=False):
    """Run Decoder-ROI VVC encoding experiment"""
    
    # Load configuration (automatically merges with default_config.yaml)
    config = load_config(config_path)
    
    # Setup logging
    log_dir = Path('results/logs/decoder_roi')
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = create_experiment_logger('decoder_roi', log_dir / 'decoder_roi.log', debug=debug)
    
    logger.info("="*60)
    logger.info("EXPERIMENT 2: DECODER-ROI VVC ENCODING")
    logger.info("="*60)
    logger.info(f"Configuration: {config_path}")
    logger.info(f"QP values: {qp_values}")
    logger.info(f"Delta QP ROI: -{delta_qp_roi}")
    if max_frames:
        logger.info(f"Max frames: {max_frames} (test mode)")
    
    # Initialize encoder
    encoder = VVCEncoder(config, logger)
    encoder_info = encoder.get_encoder_info()
    logger.info(f"Encoder: {encoder_info['software']} v{encoder_info['version']}")
    
    # Initialize ROI detector
    detector = ROIDetector(config, logger)
    
    # Get CTU size
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
        # Process all training sequences
        train_dir = dataset_path / 'train'
        if train_dir.exists():
            sequences_to_process = sorted([d for d in train_dir.iterdir() if d.is_dir()])
        else:
            logger.error(f"Training directory not found: {train_dir}")
            return
    
    # Results storage
    all_results = []
    
    # Process each sequence
    for seq_path in sequences_to_process:
        seq_name = seq_path.name
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing sequence: {seq_name}")
        logger.info(f"{'='*60}")
        
        try:
            # Load images
            images = load_sequence(seq_path, max_frames)
            logger.info(f"Found {len(images)} frames")
            
            # Convert to YUV
            yuv_path = Path('data/encoded') / f'{seq_name}_decoder_roi.yuv'
            yuv_path.parent.mkdir(parents=True, exist_ok=True)
            
            width, height, num_frames = images_to_yuv(images, yuv_path, logger)
            logger.info(f"Resolution: {width}x{height}")
            
            # Encode with different QP values
            for qp in qp_values:
                output_path = Path('data/encoded') / f'{seq_name}_decoder_roi_qp{qp}.266'
                
                stats = encode_sequence_with_roi(
                    images=images,
                    yuv_path=yuv_path,
                    output_path=output_path,
                    qp=qp,
                    width=width,
                    height=height,
                    encoder=encoder,
                    detector=detector,
                    delta_qp_roi=delta_qp_roi,
                    ctu_size=ctu_size,
                    logger=logger,
                    save_qp_maps=save_qp_maps
                )
                
                # Save results
                result = {
                    'sequence': seq_name,
                    'qp': qp,
                    'delta_qp_roi': delta_qp_roi,
                    'bitrate': stats['bitrate'],
                    'psnr_y': stats['psnr_y'],
                    'psnr_u': stats['psnr_u'],
                    'psnr_v': stats['psnr_v'],
                    'encoding_time': stats['encoding_time'],
                    'frames': num_frames,
                    'width': width,
                    'height': height,
                    'roi_percentage': stats['roi_percentage'],
                    'n_roi_ctus': stats['n_roi_ctus'],
                    'n_total_ctus': stats['n_total_ctus'],
                }
                
                all_results.append(result)
                logger.info(f"QP={qp}: {stats['bitrate']:.2f} kbps, "
                           f"PSNR={stats['psnr_y']:.2f} dB, "
                           f"Time={stats['encoding_time']:.2f}s, "
                           f"ROI={stats['roi_percentage']:.1f}%")
        
        except Exception as e:
            logger.error(f"Error processing {seq_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    # Save results to CSV
    df = pd.DataFrame(all_results)
    results_dir = Path('results/metrics')
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / 'decoder_roi.csv'
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
                avg_time = qp_results['encoding_time'].mean()
                avg_roi = qp_results['roi_percentage'].mean()
                logger.info(f"QP={qp}: {avg_bitrate:.2f} kbps, "
                           f"PSNR={avg_psnr:.2f} dB, "
                           f"Time={avg_time:.2f}s, "
                           f"ROI={avg_roi:.1f}%")
    else:
        logger.warning("No results to summarize - all sequences failed to process")


if __name__ == '__main__':
    args = parse_args()
    run_decoder_roi_experiment(
        args.config, 
        args.sequence, 
        args.qp, 
        args.max_frames, 
        args.delta_qp_roi,
        args.debug,
        args.save_qp_maps
    )
