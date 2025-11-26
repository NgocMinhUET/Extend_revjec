"""
Performance Evaluation Module
BD-Rate, BD-PSNR, BD-MOTA calculation and comparison

METRICS:
- BD-Rate: Bjøntegaard Delta bitrate reduction (%)
- BD-PSNR: Bjøntegaard Delta PSNR improvement (dB)
- BD-MOTA: Bjøntegaard Delta MOTA (for tracking performance)
- Encoding time saving (%)

USAGE:
    evaluator = PerformanceEvaluator()
    bd_rate = evaluator.calculate_bd_rate(anchor_data, test_data)
    bd_psnr = evaluator.calculate_bd_psnr(anchor_data, test_data)
    bd_mota = evaluator.calculate_bd_mota(anchor_data, test_data)
"""

import numpy as np
import pandas as pd
from scipy import interpolate
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path


class PerformanceEvaluator:
    """
    Performance evaluation with BD-Rate and other metrics
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize Performance Evaluator
        
        Args:
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def calculate_bd_rate(self,
                         anchor_data: pd.DataFrame,
                         test_data: pd.DataFrame,
                         rate_col: str = 'bitrate',
                         psnr_col: str = 'psnr_y') -> float:
        """
        Calculate Bjøntegaard Delta Rate (BD-Rate)
        
        Positive value means bitrate increase
        Negative value means bitrate reduction (better)
        
        Args:
            anchor_data: Anchor (baseline) encoding data
            test_data: Test encoding data
            rate_col: Column name for bitrate
            psnr_col: Column name for PSNR
            
        Returns:
            BD-Rate in percentage
        """
        # Extract rate and PSNR
        anchor_rate = anchor_data[rate_col].values
        anchor_psnr = anchor_data[psnr_col].values
        test_rate = test_data[rate_col].values
        test_psnr = test_data[psnr_col].values
        
        # Sort by PSNR
        anchor_idx = np.argsort(anchor_psnr)
        test_idx = np.argsort(test_psnr)
        
        anchor_rate = anchor_rate[anchor_idx]
        anchor_psnr = anchor_psnr[anchor_idx]
        test_rate = test_rate[test_idx]
        test_psnr = test_psnr[test_idx]
        
        # Find common PSNR range
        min_psnr = max(anchor_psnr.min(), test_psnr.min())
        max_psnr = min(anchor_psnr.max(), test_psnr.max())
        
        if min_psnr >= max_psnr:
            self.logger.warning("No overlapping PSNR range")
            return 0.0
        
        # Interpolate in log domain (Bjøntegaard method)
        try:
            # Anchor curve
            anchor_interp = interpolate.PchipInterpolator(
                anchor_psnr, np.log(anchor_rate)
            )
            
            # Test curve
            test_interp = interpolate.PchipInterpolator(
                test_psnr, np.log(test_rate)
            )
            
            # Integrate over common range
            psnr_range = np.linspace(min_psnr, max_psnr, 1000)
            
            anchor_integral = np.trapz(anchor_interp(psnr_range), psnr_range)
            test_integral = np.trapz(test_interp(psnr_range), psnr_range)
            
            # BD-Rate calculation
            avg_diff = (test_integral - anchor_integral) / (max_psnr - min_psnr)
            bd_rate = (np.exp(avg_diff) - 1.0) * 100.0
            
            return float(bd_rate)
        
        except Exception as e:
            self.logger.error(f"BD-Rate calculation failed: {e}")
            return 0.0
    
    def calculate_bd_psnr(self,
                         anchor_data: pd.DataFrame,
                         test_data: pd.DataFrame,
                         rate_col: str = 'bitrate',
                         psnr_col: str = 'psnr_y') -> float:
        """
        Calculate Bjøntegaard Delta PSNR (BD-PSNR)
        
        Positive value means PSNR improvement (better)
        Negative value means PSNR degradation
        
        Args:
            anchor_data: Anchor encoding data
            test_data: Test encoding data
            rate_col: Column name for bitrate
            psnr_col: Column name for PSNR
            
        Returns:
            BD-PSNR in dB
        """
        # Extract rate and PSNR
        anchor_rate = anchor_data[rate_col].values
        anchor_psnr = anchor_data[psnr_col].values
        test_rate = test_data[rate_col].values
        test_psnr = test_data[psnr_col].values
        
        # Sort by rate
        anchor_idx = np.argsort(anchor_rate)
        test_idx = np.argsort(test_rate)
        
        anchor_rate = anchor_rate[anchor_idx]
        anchor_psnr = anchor_psnr[anchor_idx]
        test_rate = test_rate[test_idx]
        test_psnr = test_psnr[test_idx]
        
        # Find common rate range (in log domain)
        log_anchor_rate = np.log(anchor_rate)
        log_test_rate = np.log(test_rate)
        
        min_log_rate = max(log_anchor_rate.min(), log_test_rate.min())
        max_log_rate = min(log_anchor_rate.max(), log_test_rate.max())
        
        if min_log_rate >= max_log_rate:
            self.logger.warning("No overlapping rate range")
            return 0.0
        
        try:
            # Anchor curve
            anchor_interp = interpolate.PchipInterpolator(
                log_anchor_rate, anchor_psnr
            )
            
            # Test curve
            test_interp = interpolate.PchipInterpolator(
                log_test_rate, test_psnr
            )
            
            # Integrate over common range
            log_rate_range = np.linspace(min_log_rate, max_log_rate, 1000)
            
            anchor_integral = np.trapz(anchor_interp(log_rate_range), log_rate_range)
            test_integral = np.trapz(test_interp(log_rate_range), log_rate_range)
            
            # BD-PSNR calculation
            bd_psnr = (test_integral - anchor_integral) / (max_log_rate - min_log_rate)
            
            return float(bd_psnr)
        
        except Exception as e:
            self.logger.error(f"BD-PSNR calculation failed: {e}")
            return 0.0
    
    def calculate_bd_mota(self,
                         anchor_data: pd.DataFrame,
                         test_data: pd.DataFrame,
                         rate_col: str = 'bitrate',
                         mota_col: str = 'mota') -> float:
        """
        Calculate Bjøntegaard Delta MOTA (BD-MOTA)
        
        Similar to BD-PSNR but for tracking performance
        
        Args:
            anchor_data: Anchor tracking data
            test_data: Test tracking data
            rate_col: Column name for bitrate
            mota_col: Column name for MOTA
            
        Returns:
            BD-MOTA value
        """
        if mota_col not in anchor_data.columns or mota_col not in test_data.columns:
            self.logger.warning(f"MOTA column '{mota_col}' not found")
            return 0.0
        
        # Use same method as BD-PSNR
        return self.calculate_bd_psnr(anchor_data, test_data, rate_col, mota_col)
    
    def calculate_encoding_time_saving(self,
                                      anchor_data: pd.DataFrame,
                                      test_data: pd.DataFrame,
                                      time_col: str = 'encoding_time') -> float:
        """
        Calculate encoding time saving percentage
        
        Negative value means time reduction (better)
        Positive value means time increase
        
        Args:
            anchor_data: Anchor timing data
            test_data: Test timing data
            time_col: Column name for encoding time
            
        Returns:
            Time saving in percentage
        """
        anchor_time = anchor_data[time_col].mean()
        test_time = test_data[time_col].mean()
        
        if anchor_time == 0:
            return 0.0
        
        time_saving = ((test_time - anchor_time) / anchor_time) * 100.0
        
        return float(time_saving)
    
    def compare_experiments(self,
                           baseline_csv: Path,
                           test_csv: Path,
                           experiment_name: str = "Test") -> Dict:
        """
        Compare two experiments and calculate all metrics
        
        Args:
            baseline_csv: Path to baseline results CSV
            test_csv: Path to test results CSV
            experiment_name: Name of test experiment
            
        Returns:
            Dictionary with all comparison metrics
        """
        # Load data
        baseline = pd.read_csv(baseline_csv)
        test = pd.read_csv(test_csv)
        
        # Calculate metrics
        results = {
            'experiment': experiment_name,
            'bd_rate': self.calculate_bd_rate(baseline, test),
            'bd_psnr_y': self.calculate_bd_psnr(baseline, test, psnr_col='psnr_y'),
            'bd_psnr_u': self.calculate_bd_psnr(baseline, test, psnr_col='psnr_u'),
            'bd_psnr_v': self.calculate_bd_psnr(baseline, test, psnr_col='psnr_v'),
            'encoding_time_saving': self.calculate_encoding_time_saving(baseline, test),
        }
        
        # Calculate BD-MOTA if available
        if 'mota' in baseline.columns and 'mota' in test.columns:
            results['bd_mota'] = self.calculate_bd_mota(baseline, test)
        
        # Additional statistics
        results['avg_bitrate_baseline'] = baseline['bitrate'].mean()
        results['avg_bitrate_test'] = test['bitrate'].mean()
        results['avg_psnr_baseline'] = baseline['psnr_y'].mean()
        results['avg_psnr_test'] = test['psnr_y'].mean()
        
        return results
    
    def generate_comparison_table(self,
                                 comparisons: List[Dict],
                                 output_path: Optional[Path] = None,
                                 format: str = 'markdown') -> str:
        """
        Generate comparison table in various formats
        
        Args:
            comparisons: List of comparison results
            output_path: Optional path to save table
            format: Output format ('markdown', 'latex', 'csv')
            
        Returns:
            Formatted table string
        """
        df = pd.DataFrame(comparisons)
        
        if format == 'markdown':
            table = df.to_markdown(index=False, floatfmt='.2f')
        elif format == 'latex':
            table = df.to_latex(index=False, float_format='%.2f')
        elif format == 'csv':
            table = df.to_csv(index=False)
        else:
            table = df.to_string(index=False)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(table)
            self.logger.info(f"Comparison table saved to {output_path}")
        
        return table
    
    def generate_rd_curve_data(self,
                              data: pd.DataFrame,
                              rate_col: str = 'bitrate',
                              psnr_col: str = 'psnr_y') -> Dict:
        """
        Prepare data for RD curve plotting
        
        Args:
            data: Encoding results dataframe
            rate_col: Column name for bitrate
            psnr_col: Column name for PSNR
            
        Returns:
            Dictionary with rate and PSNR arrays
        """
        # Sort by rate
        sorted_data = data.sort_values(by=rate_col)
        
        return {
            'rate': sorted_data[rate_col].values,
            'psnr': sorted_data[psnr_col].values,
            'qp': sorted_data['qp'].values if 'qp' in sorted_data.columns else None
        }
    
    def calculate_statistics(self, data: pd.DataFrame) -> Dict:
        """
        Calculate basic statistics from results
        
        Args:
            data: Results dataframe
            
        Returns:
            Dictionary with statistics
        """
        stats = {}
        
        # Bitrate statistics
        if 'bitrate' in data.columns:
            stats['bitrate_mean'] = data['bitrate'].mean()
            stats['bitrate_std'] = data['bitrate'].std()
            stats['bitrate_min'] = data['bitrate'].min()
            stats['bitrate_max'] = data['bitrate'].max()
        
        # PSNR statistics
        if 'psnr_y' in data.columns:
            stats['psnr_mean'] = data['psnr_y'].mean()
            stats['psnr_std'] = data['psnr_y'].std()
            stats['psnr_min'] = data['psnr_y'].min()
            stats['psnr_max'] = data['psnr_y'].max()
        
        # Encoding time statistics
        if 'encoding_time' in data.columns:
            stats['encoding_time_mean'] = data['encoding_time'].mean()
            stats['encoding_time_std'] = data['encoding_time'].std()
        
        # Detection time statistics (if available)
        if 'detection_time' in data.columns:
            stats['detection_time_mean'] = data['detection_time'].mean()
            stats['detection_overhead'] = (data['detection_time'].sum() / 
                                          data['encoding_time'].sum() * 100)
        
        # ROI statistics (if available)
        if 'roi_percentage' in data.columns:
            stats['roi_coverage_mean'] = data['roi_percentage'].mean()
            stats['roi_coverage_std'] = data['roi_percentage'].std()
        
        return stats
