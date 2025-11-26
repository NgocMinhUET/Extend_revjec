"""
Run All Experiments - Batch execution
Executes all experiments and generates comparison report
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import logging
from pathlib import Path
import subprocess
from datetime import datetime
import pandas as pd

from src.performance_evaluator import PerformanceEvaluator
from src.utils import load_config

def setup_logger():
    log_dir = Path('results/logs/batch')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger('batch')
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    log_file = log_dir / f'batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def run_experiment(script, config, sequence, max_frames, qp_values, keyframe_interval, logger):
    """Run a single experiment"""
    logger.info(f"Running {script}...")
    
    cmd = [
        'python', f'experiments/{script}',
        '--config', config,
        '--max-frames', str(max_frames),
        '--qp', *[str(q) for q in qp_values]
    ]
    
    if sequence:
        cmd.extend(['--sequence', sequence])
    
    if 'exp3' in script or 'exp4' in script or 'exp5' in script:
        cmd.extend(['--keyframe-interval', str(keyframe_interval)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            logger.info(f"✅ {script} completed successfully")
            return True
        else:
            logger.error(f"❌ {script} failed:")
            logger.error(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ {script} timed out (>1 hour)")
        return False
    except Exception as e:
        logger.error(f"❌ {script} error: {e}")
        return False

def generate_comparison_report(logger):
    """Generate comparison report from all results"""
    logger.info("\nGenerating comparison report...")
    
    results_dir = Path('results/metrics')
    
    # Load all results
    experiments = {
        'baseline': 'baseline.csv',
        'decoder_roi': 'decoder_roi.csv',
        'temporal_roi': 'temporal_roi.csv',
        'hierarchical_roi': 'hierarchical_roi.csv',
        'full_system': 'full_system.csv'
    }
    
    available_results = {}
    for name, filename in experiments.items():
        filepath = results_dir / filename
        if filepath.exists():
            available_results[name] = pd.read_csv(filepath)
            logger.info(f"  Loaded {name}: {len(available_results[name])} results")
        else:
            logger.warning(f"  Missing {name}")
    
    if 'baseline' not in available_results:
        logger.error("Baseline results not found - cannot compare")
        return
    
    # Calculate BD-Rate for all experiments
    evaluator = PerformanceEvaluator(logger)
    comparisons = []
    
    baseline = available_results['baseline']
    
    for name, data in available_results.items():
        if name == 'baseline':
            continue
        
        logger.info(f"\nComparing {name} vs baseline...")
        comparison = evaluator.compare_experiments(
            results_dir / 'baseline.csv',
            results_dir / experiments[name],
            name
        )
        comparisons.append(comparison)
        
        logger.info(f"  BD-Rate: {comparison['bd_rate']:.2f}%")
        logger.info(f"  BD-PSNR: {comparison['bd_psnr_y']:.2f} dB")
        logger.info(f"  Time Saving: {comparison['encoding_time_saving']:.2f}%")
    
    # Generate comparison table
    if comparisons:
        comparison_table = evaluator.generate_comparison_table(
            comparisons,
            output_path=results_dir / 'comparison_table.md',
            format='markdown'
        )
        
        logger.info("\n" + "="*60)
        logger.info("COMPARISON TABLE")
        logger.info("="*60)
        logger.info("\n" + comparison_table)
        
        # Also save as CSV and LaTeX
        evaluator.generate_comparison_table(comparisons, results_dir/'comparison.csv', 'csv')
        evaluator.generate_comparison_table(comparisons, results_dir/'comparison.tex', 'latex')
        
        logger.info(f"\nComparison saved to:")
        logger.info(f"  - {results_dir}/comparison_table.md")
        logger.info(f"  - {results_dir}/comparison.csv")
        logger.info(f"  - {results_dir}/comparison.tex")

def parse_args():
    parser = argparse.ArgumentParser(description='Run all experiments')
    parser.add_argument('--config', default='config/ai_config.yaml', help='Config file')
    parser.add_argument('--sequence', default=None, help='Single sequence (default: all)')
    parser.add_argument('--max-frames', type=int, default=100, help='Max frames per sequence')
    parser.add_argument('--qp', type=int, nargs='+', default=[22, 27, 32, 37], help='QP values')
    parser.add_argument('--keyframe-interval', type=int, default=10, help='Keyframe interval')
    parser.add_argument('--skip-baseline', action='store_true', help='Skip baseline (if already run)')
    parser.add_argument('--only-comparison', action='store_true', help='Only generate comparison report')
    return parser.parse_args()

def main():
    args = parse_args()
    logger = setup_logger()
    
    logger.info("="*60)
    logger.info("BATCH EXPERIMENT EXECUTION")
    logger.info("="*60)
    logger.info(f"Config: {args.config}")
    logger.info(f"Sequence: {args.sequence or 'ALL'}")
    logger.info(f"Max frames: {args.max_frames}")
    logger.info(f"QP values: {args.qp}")
    logger.info(f"Keyframe interval: {args.keyframe_interval}")
    logger.info("="*60)
    
    if not args.only_comparison:
        # List of experiments to run
        experiments_to_run = []
        
        if not args.skip_baseline:
            experiments_to_run.append('exp1_baseline.py')
        
        experiments_to_run.extend([
            'exp2_decoder_roi.py',
            'exp3_temporal_roi.py',
            'exp4_hierarchical.py',
            'exp5_full_system.py'
        ])
        
        # Run all experiments
        results = {}
        start_time = datetime.now()
        
        for exp_script in experiments_to_run:
            exp_start = datetime.now()
            success = run_experiment(
                exp_script, args.config, args.sequence, args.max_frames,
                args.qp, args.keyframe_interval, logger
            )
            exp_time = (datetime.now() - exp_start).total_seconds()
            results[exp_script] = {'success': success, 'time': exp_time}
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("EXECUTION SUMMARY")
        logger.info("="*60)
        
        for exp, result in results.items():
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            logger.info(f"{exp:30s} {status:15s} {result['time']:.1f}s")
        
        logger.info("="*60)
        logger.info(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        
        successful = sum(1 for r in results.values() if r['success'])
        logger.info(f"Success rate: {successful}/{len(results)} experiments")
    
    # Generate comparison report
    generate_comparison_report(logger)
    
    logger.info("\n" + "="*60)
    logger.info("BATCH EXECUTION COMPLETE")
    logger.info("="*60)

if __name__ == '__main__':
    main()
