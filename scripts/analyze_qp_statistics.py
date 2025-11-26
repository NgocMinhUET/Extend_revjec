"""
Analyze QP Map Statistics from Experiments
Extract theoretical performance metrics for paper
"""

import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import setup_logger

def analyze_qp_statistics(results_dir: Path) -> Dict:
    """
    Analyze QP map statistics from experiment results
    
    Returns comprehensive statistics for paper presentation
    """
    logger = setup_logger('qp_analysis')
    
    stats = {
        'decoder_roi': {},
        'temporal_roi': {},
        'hierarchical_roi': {},
        'full_system': {}
    }
    
    # Analyze decoder-roi
    decoder_csv = results_dir / 'decoder_roi.csv'
    if decoder_csv.exists():
        df = pd.read_csv(decoder_csv)
        stats['decoder_roi'] = {
            'avg_bitrate': df['bitrate'].mean(),
            'avg_psnr_y': df['psnr_y'].mean(),
            'encoding_time': df['encoding_time'].mean(),
            'detection_time': df.get('detection_time', pd.Series([0])).mean(),
            'num_frames': len(df),
        }
    
    # Analyze temporal-roi
    temporal_csv = results_dir / 'temporal_roi.csv'
    if temporal_csv.exists():
        df = pd.read_csv(temporal_csv)
        stats['temporal_roi'] = {
            'avg_bitrate': df['bitrate'].mean(),
            'avg_psnr_y': df['psnr_y'].mean(),
            'encoding_time': df['encoding_time'].mean(),
            'detection_time': df.get('detection_time', pd.Series([0])).mean(),
            'propagation_time': df.get('propagation_time', pd.Series([0])).mean(),
            'num_frames': len(df),
            'num_detections': df.get('num_detections', pd.Series([0])).sum(),
            'detection_reduction': 1 - (df.get('num_detections', pd.Series([0])).sum() / len(df))
        }
    
    # Analyze hierarchical-roi
    hierarchical_csv = results_dir / 'hierarchical_roi.csv'
    if hierarchical_csv.exists():
        df = pd.read_csv(hierarchical_csv)
        stats['hierarchical_roi'] = {
            'avg_bitrate': df['bitrate'].mean(),
            'avg_psnr_y': df['psnr_y'].mean(),
            'encoding_time': df['encoding_time'].mean(),
            'core_roi_pct': df.get('core_roi_percentage', pd.Series([0])).mean(),
            'context_roi_pct': df.get('context_roi_percentage', pd.Series([0])).mean(),
            'bg_roi_pct': df.get('background_roi_percentage', pd.Series([0])).mean(),
            'num_frames': len(df),
        }
    
    # Analyze full-system
    full_csv = results_dir / 'full_system.csv'
    if full_csv.exists():
        df = pd.read_csv(full_csv)
        stats['full_system'] = {
            'avg_bitrate': df['bitrate'].mean(),
            'avg_psnr_y': df['psnr_y'].mean(),
            'encoding_time': df['encoding_time'].mean(),
            'total_time': df.get('total_time', pd.Series([0])).mean(),
            'num_frames': len(df),
        }
    
    return stats

def calculate_theoretical_bdrate(roi_coverage: float, qp_roi: int, qp_non_roi: int, base_qp: int = 27) -> float:
    """
    Calculate theoretical BD-Rate using rate-QP exponential model
    
    Formula: Rate ∝ 2^((QP - QP_base) / 6)
    """
    rate_ratio_roi = 2 ** ((qp_roi - base_qp) / 6.0)
    rate_ratio_non_roi = 2 ** ((qp_non_roi - base_qp) / 6.0)
    
    weighted_rate_ratio = roi_coverage * rate_ratio_roi + (1 - roi_coverage) * rate_ratio_non_roi
    
    bd_rate = (weighted_rate_ratio - 1.0) * 100.0
    return bd_rate

def calculate_hierarchical_bdrate(core_pct: float, context_pct: float, bg_pct: float,
                                  qp_core: int, qp_context: int, qp_bg: int, base_qp: int = 27) -> float:
    """Calculate theoretical BD-Rate for hierarchical ROI"""
    rate_core = 2 ** ((qp_core - base_qp) / 6.0)
    rate_context = 2 ** ((qp_context - base_qp) / 6.0)
    rate_bg = 2 ** ((qp_bg - base_qp) / 6.0)
    
    weighted_rate = core_pct * rate_core + context_pct * rate_context + bg_pct * rate_bg
    
    bd_rate = (weighted_rate - 1.0) * 100.0
    return bd_rate

def generate_paper_statistics():
    """Generate comprehensive statistics for paper"""
    
    logger = setup_logger('paper_stats')
    results_dir = Path('results/metrics')
    
    logger.info("="*80)
    logger.info("COMPREHENSIVE STATISTICS FOR PAPER")
    logger.info("="*80)
    
    # Load experimental data
    stats = analyze_qp_statistics(results_dir)
    
    # Print summary
    print("\n" + "="*80)
    print("1. ALGORITHM PERFORMANCE (MEASURED)")
    print("="*80)
    
    if 'temporal_roi' in stats and stats['temporal_roi']:
        detection_reduction = stats['temporal_roi'].get('detection_reduction', 0) * 100
        print(f"\n✅ Detection Overhead Reduction: {detection_reduction:.1f}%")
        print(f"   - Baseline: 100% (every frame)")
        print(f"   - Temporal: {100-detection_reduction:.1f}% (with propagation)")
        print(f"   - Frames: {stats['temporal_roi']['num_frames']}")
    
    if 'hierarchical_roi' in stats and stats['hierarchical_roi']:
        core_pct = stats['hierarchical_roi'].get('core_roi_pct', 0)
        context_pct = stats['hierarchical_roi'].get('context_roi_pct', 0)
        bg_pct = stats['hierarchical_roi'].get('bg_roi_pct', 0)
        print(f"\n✅ Hierarchical ROI Structure:")
        print(f"   - Core (Objects):      {core_pct:5.1f}%")
        print(f"   - Context (Rings):     {context_pct:5.1f}%")
        print(f"   - Background:          {bg_pct:5.1f}%")
    
    # Theoretical BD-Rate
    print("\n" + "="*80)
    print("2. THEORETICAL BD-RATE ESTIMATES")
    print("="*80)
    print("\nAssumptions:")
    print("  - ROI coverage: 15% (from measurements)")
    print("  - QP offset: ΔQP_ROI = -5, ΔQP_non-ROI = +5")
    print("  - Base QP: 27")
    print("  - Rate model: Bitrate ∝ 2^((QP - QP_base)/6)")
    
    # Binary ROI
    bd_rate_binary = calculate_theoretical_bdrate(0.15, 22, 32, 27)
    print(f"\n  Decoder-ROI (Binary):      {bd_rate_binary:+6.2f}%")
    
    # Hierarchical ROI
    if 'hierarchical_roi' in stats and stats['hierarchical_roi']:
        core = stats['hierarchical_roi'].get('core_roi_pct', 7.2) / 100
        context = stats['hierarchical_roi'].get('context_roi_pct', 12.0) / 100
        bg = stats['hierarchical_roi'].get('bg_roi_pct', 80.8) / 100
        
        bd_rate_hier = calculate_hierarchical_bdrate(core, context, bg, 19, 23, 33, 27)
        print(f"  Hierarchical (3-level):    {bd_rate_hier:+6.2f}%")
    
    print("\n  Note: Positive BD-Rate = bitrate increase due to high-quality ROI")
    print("        For task-oriented coding, quality >> bitrate")
    
    # Time analysis
    print("\n" + "="*80)
    print("3. TIME COMPLEXITY ANALYSIS")
    print("="*80)
    
    for exp_name, exp_stats in stats.items():
        if exp_stats:
            enc_time = exp_stats.get('encoding_time', 0)
            det_time = exp_stats.get('detection_time', 0)
            prop_time = exp_stats.get('propagation_time', 0)
            total = enc_time + det_time + prop_time
            
            print(f"\n{exp_name:20s}:")
            print(f"  Encoding:     {enc_time:6.2f}s")
            if det_time > 0:
                print(f"  Detection:    {det_time:6.2f}s")
            if prop_time > 0:
                print(f"  Propagation:  {prop_time:6.2f}s")
            print(f"  Total:        {total:6.2f}s")
    
    # Save to JSON
    output_file = results_dir / 'paper_statistics.json'
    with open(output_file, 'w') as f:
        json.dump({
            'measured_performance': stats,
            'theoretical_bdrate': {
                'decoder_roi': bd_rate_binary,
                'hierarchical_roi': bd_rate_hier if 'hierarchical_roi' in stats else None
            },
            'assumptions': {
                'roi_coverage': 0.15,
                'qp_offsets': {'roi': -5, 'non_roi': +5},
                'base_qp': 27,
                'rate_model': 'exponential_2_6'
            }
        }, f, indent=2)
    
    logger.info(f"\n✅ Statistics saved to: {output_file}")
    print("\n" + "="*80)

if __name__ == '__main__':
    generate_paper_statistics()
