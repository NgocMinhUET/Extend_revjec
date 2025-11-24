# Data Directory

This directory contains datasets for training and evaluation.

## 📥 Download Datasets

### MOT16 (Required)
```bash
# Download MOT16
wget https://motchallenge.net/data/MOT16.zip
unzip MOT16.zip -d data/

# Or use script
bash scripts/download_datasets.sh
```

### MOT17 (Recommended)
```bash
wget https://motchallenge.net/data/MOT17.zip
unzip MOT17.zip -d data/
```

### MOT20 (Optional)
```bash
wget https://motchallenge.net/data/MOT20.zip
unzip MOT20.zip -d data/
```

## 📁 Expected Structure

```
data/
├── MOT16/
│   ├── train/
│   │   ├── MOT16-02/
│   │   │   ├── img1/          # Images
│   │   │   ├── gt/            # Ground truth
│   │   │   └── seqinfo.ini    # Sequence info
│   │   ├── MOT16-04/
│   │   ├── MOT16-05/
│   │   ├── MOT16-09/
│   │   ├── MOT16-10/
│   │   ├── MOT16-11/
│   │   └── MOT16-13/
│   └── test/                  # Test sequences (no GT)
│
├── MOT17/
│   ├── train/                 # Similar structure
│   └── test/
│
├── MOT20/
│   ├── train/                 # Similar structure
│   └── test/
│
└── encoded/                   # Encoded videos (generated)
    ├── baseline/
    ├── decoder_roi/
    └── full_system/
```

## 📊 Dataset Statistics

### MOT16
- **Train sequences:** 7
- **Total frames:** 5,316
- **Resolution:** Various (720p, 1080p)
- **FPS:** 30
- **Scenarios:** Urban, sports, pedestrian

### MOT17
- **Train sequences:** 7 (same as MOT16 but 3 detectors)
- **Total frames:** 5,316 × 3
- **Detectors:** DPM, FRCNN, SDP

### MOT20
- **Train sequences:** 4
- **Total frames:** 8,931
- **Resolution:** 1080p
- **FPS:** 25
- **Scenarios:** Crowded scenes

## 🎯 Usage

### For Training/Validation
Use `train/` sequences with ground truth annotations.

### For Testing
Use `test/` sequences (no ground truth provided).

### For Baseline Experiments
Minimum requirement: MOT16 train sequences.

## 📝 File Formats

### Image Sequences
- Format: JPEG
- Naming: `000001.jpg`, `000002.jpg`, ...
- Location: `{sequence}/img1/`

### Ground Truth
- Format: CSV
- Columns: `frame, id, left, top, width, height, conf, class, vis`
- Location: `{sequence}/gt/gt.txt`

### Sequence Info
- Format: INI
- Contains: name, imDir, frameRate, seqLength, imWidth, imHeight
- Location: `{sequence}/seqinfo.ini`

## 🔧 Data Processing

### Extract Frames
```python
from src.utils import extract_frames
extract_frames('sequence_path', 'output_dir')
```

### Load Ground Truth
```python
from src.utils import load_gt
gt = load_gt('sequence_path/gt/gt.txt')
```

### Encode Video
```python
from src.vvc_encoder import VVCEncoder
encoder = VVCEncoder(config)
encoder.encode('input.yuv', 'output.266', qp=27)
```

## 💾 Storage Requirements

- **MOT16:** ~2 GB
- **MOT17:** ~6 GB
- **MOT20:** ~5 GB
- **Encoded videos:** ~10-20 GB (depends on experiments)

**Total:** ~25-35 GB

## ⚠️ Notes

1. **License:** Check MOT Challenge license before use
2. **Citation:** Cite MOT Challenge papers if you use these datasets
3. **Privacy:** Follow data usage guidelines
4. **Backup:** Keep original data separate from encoded results

## 📚 References

- MOT Challenge: https://motchallenge.net/
- Paper: Milan et al., "MOT16: A Benchmark for Multi-Object Tracking", arXiv:1603.00831

## 📞 Support

If you have issues downloading or processing data:
1. Check network connection
2. Verify dataset URLs
3. Check disk space
4. Review error logs
5. Open a GitHub issue
