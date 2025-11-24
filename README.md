# Hierarchical Temporal ROI-VVC for Multi-Object Tracking

## Overview
This project extends the Decoder-ROI based VVC framework with:
- **Temporal ROI Propagation**: GOP-level keyframe detection with motion vector-based propagation
- **Hierarchical ROI Structure**: 3-level ROI (Core-Context-Background) with adaptive QP allocation
- **Extended Configurations**: Support for AI, RA, and LDP configurations

## Key Features
- ✅ Zero-overhead decoder-side ROI extraction
- ✅ 80-90% reduction in detection overhead via temporal propagation
- ✅ Content-adaptive QP allocation with hierarchical structure
- ✅ Support for multiple VVC configurations (AI/RA/LDP)
- ✅ Comprehensive evaluation on MOT16/17/20 datasets

## Performance Targets
- **BD-Rate**: ≤ -75% (vs. baseline VVC)
- **BD-MOTA**: ≥ +7.0
- **Time Saving**: ≥ -10%
- **Detection Overhead**: < 1s per sequence

## Quick Start

### 1. Installation
```bash
# Clone repository
git clone <repository-url>
cd Extend_revjec

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup VVenC
bash scripts/prepare_vvenc.sh
```

### 2. Download Datasets
```bash
bash scripts/download_datasets.sh
```

### 3. Run Baseline Experiment
```bash
python experiments/exp1_baseline.py --config config/ai_config.yaml
```

### 4. Run Full System
```bash
python experiments/exp5_full_system.py --config config/ai_config.yaml
```

## Project Structure
```
Extend_revjec/
├── src/                    # Source code
├── experiments/            # Experiment scripts
├── config/                 # Configuration files
├── data/                   # Datasets
├── results/                # Experiment results
├── models/                 # Pre-trained models
└── paper/                  # Paper materials
```

## Documentation
- [Project Specification](PROJECT_SPECIFICATION.md) - Detailed technical specification
- [Research Objectives](RESEARCH_OBJECTIVES.md) - Research goals and novelty
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) - Step-by-step implementation

## Citation
If you use this code, please cite:
```bibtex
@article{bui2024hierarchical,
  title={Hierarchical Temporal ROI-based Versatile Video Coding for Multi-Object Tracking},
  author={Bui, Thanh Huong and Do, Ngoc Minh and Hoang, Van Xiem},
  journal={IEEE Transactions on Image Processing},
  year={2024}
}
```

## License
MIT License

## Contact
- Bui Thanh Huong: <email>
- Do Ngoc Minh: <email>
- Hoang Van Xiem: xiemhoang@vnu.edu.vn
