# Results Directory

This directory stores experiment results, logs, metrics, and visualizations.

## 📁 Structure

```
results/
├── logs/                   # Encoding logs
├── metrics/                # Performance metrics (CSV)
├── plots/                  # Visualizations (PNG)
└── analysis/               # Statistical analysis
```

## 📊 Expected Files

- `metrics/baseline.csv` - Baseline VVC results
- `metrics/decoder_roi.csv` - Decoder-ROI results
- `metrics/full_system.csv` - Full system results
- `metrics/summary.xlsx` - Summary statistics
- `plots/rd_curves.png` - Rate-Distortion curves
- `plots/comparison.png` - Method comparison

## 🎯 Target Results

| Method | BD-Rate | BD-MOTA |
|--------|---------|---------|
| Baseline | 0.0% | 0.0 |
| Decoder-ROI | -62% | +4.65 |
| Full System | -78% | +7.5 |

## 🔧 Generate Results

```bash
# Extract metrics
python scripts/extract_results.py

# Generate plots
python scripts/generate_plots.py
```

## ⚠️ Note

Results will be generated after running experiments.
