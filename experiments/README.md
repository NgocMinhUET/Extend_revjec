# Experiments Directory

This directory contains experiment scripts for evaluating the Hierarchical Temporal ROI-VVC framework.

## 📁 Structure

```
experiments/
├── exp1_baseline.py           # Baseline VVC encoding
├── exp2_decoder_roi.py        # Original Decoder-ROI (reproduce paper)
├── exp3_temporal_roi.py       # Add temporal propagation
├── exp4_hierarchical.py       # Add hierarchical ROI
├── exp5_full_system.py        # Full system (all features)
└── run_all_experiments.py     # Run all experiments
```

## 🚀 Usage

### Run Single Experiment

```bash
# Baseline VVC
python experiments/exp1_baseline.py --config config/ai_config.yaml

# Decoder-ROI
python experiments/exp2_decoder_roi.py --config config/ai_config.yaml

# Full system
python experiments/exp5_full_system.py --config config/ai_config.yaml
```

### Run All Experiments

```bash
python experiments/run_all_experiments.py --config config/ai_config.yaml
```

## ⚙️ Configuration

Each experiment can use different configurations:
- `config/ai_config.yaml` - All-Intra
- `config/ra_config.yaml` - Random Access
- `config/ldp_config.yaml` - Low-Delay P

## 📊 Results

Results are saved in:
- `results/logs/` - Encoding logs
- `results/metrics/` - Performance metrics (CSV)
- `results/plots/` - RD curves and visualizations

## 📝 Experiment Details

### exp1_baseline.py
- Standard VVC encoding
- Multiple QP values (22, 27, 32, 37)
- Baseline for comparison

### exp2_decoder_roi.py
- Reproduce original paper results
- YOLO-based ROI detection
- Frame-by-frame encoding
- Target: BD-Rate ≈ -62%, BD-MOTA ≈ +4.65

### exp3_temporal_roi.py
- Add temporal ROI propagation
- GOP-level detection
- Motion vector propagation
- Target: BD-Rate ≈ -70%, Detection time < 1s

### exp4_hierarchical.py
- Add 3-level hierarchical ROI
- Adaptive context ring
- Content-adaptive QP
- Target: BD-Rate ≈ -75%, BD-MOTA ≈ +7.0

### exp5_full_system.py
- Complete system
- All features enabled
- Multiple configurations (AI/RA/LDP)
- Target: BD-Rate ≈ -78%, BD-MOTA ≈ +7.5

## 🎯 Expected Results

| Experiment | BD-Rate | BD-MOTA | Time Saving |
|-----------|---------|---------|-------------|
| Baseline | 0.0% | 0.0 | 0.0% |
| Decoder-ROI | -62% | +4.65 | -3% |
| +Temporal | -70% | +5.5 | -6% |
| +Hierarchical | -75% | +7.0 | -8% |
| Full System | -78% | +7.5 | -10% |

## ⚠️ Status

**Current Status:** ⚠️ Not yet implemented

These experiment scripts need to be created. They are planned but not yet available in the repository.

## 📞 Support

If you encounter issues:
1. Check logs in `results/logs/`
2. Verify configuration in `config/`
3. Review documentation in root directory
4. Open a GitHub issue
