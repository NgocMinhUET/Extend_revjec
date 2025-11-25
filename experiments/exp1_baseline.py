"""
Experiment 1: Baseline VVC Encoding
Standard VVC encoding without ROI optimization
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
from src.utils import load_config


def create_experiment_logger(name: str, log_file: Path) -> logging.Logger:
    """Create a simple logger for experiments with console + file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers when rerunning
    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def parse_args():
    parser = argparse.ArgumentParser(description='Baseline VVC Encoding Experiment')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to configuration file')
    parser.add_argument('--sequence', type=str, default=None,
                        help='Specific sequence to encode (default: all)')
    parser.add_argument('--qp', type=int, nargs='+', default=[22, 27, 32, 37],
                        help='QP values to test')
    return parser.parse_args()


def load_sequence(sequence_path):
    """Load image sequence from MOT dataset"""
    img_dir = Path(sequence_path) / 'img1'
    if not img_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {img_dir}")
    
    # Get all images
    images = sorted(img_dir.glob('*.jpg'))
    if not images:
        raise ValueError(f"No images found in {img_dir}")
    
    return images


def images_to_yuv(images, output_yuv, logger):
    """Convert image sequence to YUV format for VVenC"""
    logger.info(f"Converting {len(images)} images to YUV...")
    
    # Read first image to get dimensions
    first_frame = cv2.imread(str(images[0]))
    height, width = first_frame.shape[:2]
    
    with open(output_yuv, 'wb') as f:
        for img_path in tqdm(images, desc="Converting to YUV"):
            frame = cv2.imread(str(img_path))
            # Convert BGR to YUV420
            yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV_I420)
            f.write(yuv.tobytes())
    
    logger.info(f"YUV file created: {output_yuv}")
    return width, height, len(images)


def encode_sequence(encoder, yuv_path, output_path, qp, width, height, logger):
    """Encode YUV sequence with VVenC"""
    logger.info(f"Encoding with QP={qp}...")
    
    stats = encoder.encode(
        input_file=str(yuv_path),
        output_file=str(output_path),
        qp=qp,
        width=width,
        height=height
    )
    
    return stats


def run_baseline_experiment(config_path, sequence_name=None, qp_values=[22, 27, 32, 37]):
    """Run baseline VVC encoding experiment"""
    
    # Load configuration (automatically merges with default_config.yaml)
    config = load_config(config_path)
    
    # Setup logging
    log_dir = Path('results/logs/baseline')
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = create_experiment_logger('baseline', log_dir / 'baseline.log')
    
    logger.info("="*60)
    logger.info("EXPERIMENT 1: BASELINE VVC ENCODING")
    logger.info("="*60)
    logger.info(f"Configuration: {config_path}")
    logger.info(f"QP values: {qp_values}")
    
    # Initialize encoder
    encoder = VVCEncoder(config, logger)
    encoder_info = encoder.get_encoder_info()
    logger.info(f"Encoder: {encoder_info['software']} v{encoder_info['version']}")
    
    # Get dataset path
    dataset_path = Path(config['dataset']['root_dir'])
    sequences_to_process = []
    
    if sequence_name:
        sequences_to_process = [dataset_path / 'train' / sequence_name]
    else:
        # Process all training sequences
        train_dir = dataset_path / 'train'
        sequences_to_process = sorted([d for d in train_dir.iterdir() if d.is_dir()])
    
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
            images = load_sequence(seq_path)
            logger.info(f"Found {len(images)} frames")
            
            # Convert to YUV
            yuv_path = Path('data/encoded') / f'{seq_name}_baseline.yuv'
            yuv_path.parent.mkdir(parents=True, exist_ok=True)
            
            width, height, num_frames = images_to_yuv(images, yuv_path, logger)
            logger.info(f"Resolution: {width}x{height}")
            
            # Encode with different QP values
            for qp in qp_values:
                output_path = Path('data/encoded') / f'{seq_name}_baseline_qp{qp}.266'
                
                stats = encode_sequence(
                    encoder, yuv_path, output_path, qp, width, height, logger
                )
                
                # Store results
                result = {
                    'sequence': seq_name,
                    'method': 'baseline',
                    'qp': qp,
                    'width': width,
                    'height': height,
                    'frames': num_frames,
                    'bitrate': stats['bitrate'],
                    'psnr_y': stats['psnr_y'],
                    'psnr_u': stats['psnr_u'],
                    'psnr_v': stats['psnr_v'],
                    'encoding_time': stats['encoding_time'],
                    'output_file': str(output_path)
                }
                all_results.append(result)
                
                logger.info(f"QP={qp}: {stats['bitrate']:.2f} kbps, "
                           f"PSNR={stats['psnr_y']:.2f} dB, "
                           f"Time={stats['encoding_time']:.2f}s")
            
            # Clean up YUV file
            yuv_path.unlink()
            
        except Exception as e:
            logger.error(f"Error processing {seq_name}: {e}")
            continue
    
    # Save results
    results_dir = Path('results/metrics')
    results_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.DataFrame(all_results)
    results_file = results_dir / 'baseline.csv'
    df.to_csv(results_file, index=False)
    
    logger.info(f"\n{'='*60}")
    logger.info("EXPERIMENT COMPLETED")
    logger.info(f"{'='*60}")
    logger.info(f"Results saved to: {results_file}")
    logger.info(f"Total sequences processed: {len(sequences_to_process)}")
    
    # Print summary
    logger.info("\nSummary by QP:")
    for qp in qp_values:
        qp_results = df[df['qp'] == qp]
        avg_bitrate = qp_results['bitrate'].mean()
        avg_psnr = qp_results['psnr_y'].mean()
        avg_time = qp_results['encoding_time'].mean()
        logger.info(f"QP={qp}: {avg_bitrate:.2f} kbps, "
                   f"PSNR={avg_psnr:.2f} dB, "
                   f"Time={avg_time:.2f}s")


if __name__ == '__main__':
    args = parse_args()
    run_baseline_experiment(args.config, args.sequence, args.qp)
