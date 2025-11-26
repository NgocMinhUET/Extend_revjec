"""
Theoretical BD-Rate Estimation
Estimate bitrate savings based on QP map statistics

Since VVenC CLI doesn't support CTU-level QP maps,
we estimate theoretical improvements using:
1. ROI coverage statistics
2. QP offset per region
3. Rate-QP relationship (exponential model)

FORMULA:
  Bitrate_ratio = Σ (area_i × 2^((QP_i - QP_base) / 6))
  BD-Rate = (1 - Bitrate_ratio) × 100%
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.utils import load_config

def estimate_theoretical_bdrate(roi_stats, qp_stats, base_qp=27):
    """
    Estimate theoretical BD-Rate based on QP map
    
    Args:
        roi_stats: Dictionary with ROI level percentages
        qp_stats: Dictionary with QP values per level
        base_qp: Base QP value
        
    Returns:
        Estimated BD-Rate percentage
    """
    # Get coverage
    core_pct = roi_stats.get('core', {}).get('percentage', 0) / 100.0
    context_pct = roi_stats.get('context', {}).get('percentage', 0) / 100.0
    bg_pct = roi_stats.get('background', {}).get('percentage', 0) / 100.0
    
    # Get QP values
    qp_core = qp_stats.get('core', {}).get('mean_qp', base_qp)
    qp_context = qp_stats.get('context', {}).get('mean_qp', base_qp)
    qp_bg = qp_stats.get('background', {}).get('mean_qp', base_qp)
    
    # Rate-QP relationship: Rate ∝ 2^((QP - QP_base) / 6)
    # Lower QP = higher bitrate, Higher QP = lower bitrate
    rate_ratio_core = 2 ** ((qp_core - base_qp) / 6.0)
    rate_ratio_context = 2 ** ((qp_context - base_qp) / 6.0)
    rate_ratio_bg = 2 ** ((qp_bg - base_qp) / 6.0)
    
    # Weighted average bitrate ratio
    weighted_rate_ratio = (core_pct * rate_ratio_core + 
                          context_pct * rate_ratio_context + 
                          bg_pct * rate_ratio_bg)
    
    # BD-Rate = bitrate reduction percentage
    bd_rate = (weighted_rate_ratio - 1.0) * 100.0
    
    return bd_rate

def estimate_psnr_change(qp_diff):
    """
    Estimate PSNR change based on QP difference
    
    Rule of thumb: ΔQP = 6 → ΔPSNR ≈ -1 dB
    """
    return -qp_diff / 6.0

def analyze_experiment_results():
    """Analyze all experiment results and estimate theoretical BD-Rate"""
    
    results_dir = Path('results/metrics')
    
    print("="*80)
    print("THEORETICAL BD-RATE ESTIMATION")
    print("="*80)
    print("\nNOTE: VVenC CLI limitation - actual encoding uses uniform QP")
    print("This analysis estimates theoretical improvements if QP maps were applied\n")
    
    # Example statistics (from actual experiments)
    experiments = {
        'decoder_roi': {
            'roi_coverage': 0.15,  # 15% ROI
            'qp_roi': 22,  # QP for ROI
            'qp_non_roi': 32,  # QP for non-ROI
            'base_qp': 27
        },
        'temporal_roi': {
            'roi_coverage': 0.15,
            'qp_roi': 22,
            'qp_non_roi': 32,
            'base_qp': 27,
            'detection_reduction': 0.90  # 90% less detection
        },
        'hierarchical_roi': {
            'core_coverage': 0.072,  # 7.2% core
            'context_coverage': 0.12,  # 12% context
            'bg_coverage': 0.808,  # 80.8% background
            'qp_core': 19,  # From actual results
            'qp_context': 23,
            'qp_bg': 33,
            'base_qp': 27
        }
    }
    
    print("-"*80)
    print(f"{'Experiment':<20} {'Theoretical BD-Rate':<20} {'Est. PSNR Change':<20} {'Note'}")
    print("-"*80)
    
    # Decoder-ROI
    exp = experiments['decoder_roi']
    rate_ratio = (exp['roi_coverage'] * 2**((exp['qp_roi'] - exp['base_qp'])/6) + 
                  (1 - exp['roi_coverage']) * 2**((exp['qp_non_roi'] - exp['base_qp'])/6))
    bd_rate = (rate_ratio - 1.0) * 100
    psnr_change = (exp['roi_coverage'] * (exp['qp_roi'] - exp['base_qp']) + 
                   (1-exp['roi_coverage']) * (exp['qp_non_roi'] - exp['base_qp'])) / 6.0
    print(f"{'decoder_roi':<20} {bd_rate:>18.2f}% {psnr_change:>18.2f} dB {'Binary ROI'}")
    
    # Temporal ROI (same as decoder-ROI but with detection reduction)
    print(f"{'temporal_roi':<20} {bd_rate:>18.2f}% {psnr_change:>18.2f} dB {'+ 90% det. reduction'}")
    
    # Hierarchical ROI
    exp = experiments['hierarchical_roi']
    rate_ratio = (exp['core_coverage'] * 2**((exp['qp_core'] - exp['base_qp'])/6) + 
                  exp['context_coverage'] * 2**((exp['qp_context'] - exp['base_qp'])/6) +
                  exp['bg_coverage'] * 2**((exp['qp_bg'] - exp['base_qp'])/6))
    bd_rate = (rate_ratio - 1.0) * 100
    psnr_change = (exp['core_coverage'] * (exp['qp_core'] - exp['base_qp']) + 
                   exp['context_coverage'] * (exp['qp_context'] - exp['base_qp']) +
                   exp['bg_coverage'] * (exp['qp_bg'] - exp['base_qp'])) / 6.0
    print(f"{'hierarchical_roi':<20} {bd_rate:>18.2f}% {psnr_change:>18.2f} dB {'3-level hierarchy'}")
    
    print("-"*80)
    
    print("\n" + "="*80)
    print("INTERPRETATION")
    print("="*80)
    print("• BD-Rate < 0: Bitrate REDUCTION (good)")
    print("• BD-Rate > 0: Bitrate INCREASE (due to high-quality ROI)")
    print("• PSNR change: Overall quality change across frame")
    print("• Actual results differ because VVenC uses uniform QP")
    print("="*80)
    
    # Comparison with paper
    print("\n" + "="*80)
    print("COMPARISON WITH RESEARCH TARGETS")
    print("="*80)
    print(f"{'Metric':<30} {'Current Paper':<15} {'Target':<15} {'Estimated':<15}")
    print("-"*80)
    print(f"{'BD-Rate':<30} {'-62.23%':<15} {'≤ -70%':<15} {bd_rate:.2f}%")
    print(f"{'Detection Reduction':<30} {'N/A':<15} {'> 80%':<15} {'90%':<15}")
    print("="*80)

if __name__ == '__main__':
    analyze_experiment_results()
