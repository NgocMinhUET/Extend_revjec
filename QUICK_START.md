# QUICK START GUIDE

## Bắt đầu nhanh - Hướng dẫn từng bước

---

## Bước 1: Setup môi trường (5 phút)

```bash
# Clone/Navigate to project
cd d:\NCS\propose\Extend_revjec

# Tạo virtual environment
python -m venv venv
venv\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy setup script
python scripts/setup_project.py
```

---

## Bước 2: Cài đặt VVenC (10 phút)

### Windows:
```bash
# Download pre-built binary
# https://github.com/fraunhoferhhi/vvenc/releases

# Hoặc build từ source với Visual Studio
git clone https://github.com/fraunhoferhhi/vvenc.git
cd vvenc
mkdir build && cd build
cmake .. -G "Visual Studio 16 2019" -A x64
cmake --build . --config Release

# Thêm vào PATH
set PATH=%PATH%;C:\path\to\vvenc\bin
```

### Linux:
```bash
git clone https://github.com/fraunhoferhhi/vvenc.git
cd vvenc
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j8
sudo make install
```

---

## Bước 3: Download datasets (30 phút)

```bash
# Tạo thư mục data
mkdir -p data

# Download MOT16 (required)
wget https://motchallenge.net/data/MOT16.zip
unzip MOT16.zip -d data/

# Download MOT17 (optional)
wget https://motchallenge.net/data/MOT17.zip
unzip MOT17.zip -d data/

# Cấu trúc thư mục:
# data/
#   MOT16/
#     train/
#       MOT16-02/
#         img1/
#         gt/
#       MOT16-04/
#       ...
```

---

## Bước 4: Verify installation (2 phút)

```python
# Chạy verification script
python scripts/verify_installation.py
```

**Expected output:**
```
✓ PyTorch: 2.0.0
✓ CUDA available: True
✓ OpenCV: 4.8.0
✓ YOLOv8 loaded
✓ VVenC available
✓ All checks passed!
```

---

## Bước 5: Chạy baseline experiment (1 giờ)

```bash
# Chạy baseline VVC encoding
python experiments/exp1_baseline.py --config config/ai_config.yaml

# Kết quả sẽ được lưu trong:
# - results/logs/baseline.log
# - results/metrics/baseline.csv
```

**Expected output:**
```
Processing MOT16-02...
  QP=22: 5234.56 kbps, 145.23s, MOTA=0.45
  QP=27: 3456.78 kbps, 132.45s, MOTA=0.43
  QP=32: 2123.45 kbps, 125.67s, MOTA=0.40
  QP=37: 1234.56 kbps, 118.89s, MOTA=0.36
...
```

---

## Bước 6: Chạy Decoder-ROI (2 giờ)

```bash
# Reproduce paper results
python experiments/exp2_decoder_roi.py --config config/ai_config.yaml
```

**Target results:**
- BD-Rate: -60% to -65%
- BD-MOTA: +4.0 to +5.0
- Time Saving: -3% to -4%

---

## Bước 7: Chạy full system (3 giờ)

```bash
# Chạy với temporal propagation + hierarchical ROI
python experiments/exp5_full_system.py --config config/ai_config.yaml
```

**Target results:**
- BD-Rate: -75% to -80%
- BD-MOTA: +7.0 to +7.5
- Time Saving: -10% to -12%

---

## Bước 8: Generate results (10 phút)

```bash
# Extract metrics
python scripts/extract_results.py

# Generate plots
python scripts/generate_plots.py

# Kết quả:
# - results/metrics/summary.xlsx
# - results/plots/rd_curves.png
# - results/plots/comparison.png
```

---

## Troubleshooting

### Issue: VVenC not found
```bash
# Check PATH
echo %PATH%  # Windows
echo $PATH   # Linux

# Add to PATH
set PATH=%PATH%;C:\path\to\vvenc\bin  # Windows
export PATH=$PATH:/path/to/vvenc/bin  # Linux
```

### Issue: CUDA out of memory
```yaml
# Edit config/default_config.yaml
roi_detection:
  device: "cpu"  # Change from "cuda" to "cpu"
  batch_size: 1  # Reduce batch size
```

### Issue: Dataset not found
```bash
# Check data structure
ls data/MOT16/train/

# Should see:
# MOT16-02/
# MOT16-04/
# MOT16-05/
# ...
```

### Issue: Slow encoding
```yaml
# Edit config/default_config.yaml
encoder:
  preset: "fast"  # Change from "medium" to "fast"
  threads: 16     # Increase threads
```

---

## File Structure Overview

```
Extend_revjec/
├── README.md                    # Project overview
├── QUICK_START.md              # This file
├── PROJECT_SPECIFICATION.md    # Technical details
├── RESEARCH_OBJECTIVES.md      # Research goals
├── IMPLEMENTATION_GUIDE.md     # Detailed guide
│
├── config/                     # Configurations
│   ├── default_config.yaml
│   ├── ai_config.yaml
│   ├── ra_config.yaml
│   └── ldp_config.yaml
│
├── src/                        # Source code
│   ├── gop_manager.py
│   ├── roi_detector.py
│   ├── temporal_propagator.py
│   ├── hierarchical_roi.py
│   ├── qp_controller.py
│   └── ...
│
├── experiments/                # Experiment scripts
│   ├── exp1_baseline.py
│   ├── exp2_decoder_roi.py
│   ├── exp5_full_system.py
│   └── ...
│
└── results/                    # Results
    ├── logs/
    ├── metrics/
    └── plots/
```

---

## Next Steps

1. **Đọc documentation:**
   - `PROJECT_SPECIFICATION.md` - Chi tiết kỹ thuật
   - `RESEARCH_OBJECTIVES.md` - Mục tiêu và tính mới
   - `IMPLEMENTATION_GUIDE.md` - Hướng dẫn triển khai

2. **Chạy experiments:**
   - Baseline → Decoder-ROI → Temporal → Hierarchical → Full

3. **Analyze results:**
   - Check BD-Rate, BD-MOTA
   - Compare with targets
   - Debug if needed

4. **Write paper:**
   - Use results from experiments
   - Follow Q1 journal format
   - Submit to IEEE TIP/TCSVT

---

## Expected Timeline

| Task | Duration | Status |
|------|----------|--------|
| Setup environment | 1 hour | ⏳ |
| Run baseline | 2 hours | ⏳ |
| Implement temporal | 1 week | ⏳ |
| Implement hierarchical | 1 week | ⏳ |
| Run all experiments | 1 week | ⏳ |
| Write paper | 2 weeks | ⏳ |
| **Total** | **~6 weeks** | ⏳ |

---

## Support

Nếu gặp vấn đề:
1. Check logs: `results/logs/`
2. Review config: `config/`
3. Read docs: `*.md` files
4. Debug: Add `--debug` flag

---

**Good luck! 🚀**
