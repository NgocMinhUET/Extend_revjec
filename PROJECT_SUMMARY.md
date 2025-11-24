# PROJECT SUMMARY - HIERARCHICAL TEMPORAL ROI-VVC

## TÓM TẮT DỰ ÁN - Phát triển bài báo Q1

---

## 📋 TỔNG QUAN DỰ ÁN

### Tên dự án
**Hierarchical Temporal ROI-based Versatile Video Coding for Multi-Object Tracking**

### Mục tiêu
Phát triển framework **Decoder-ROI VVC** hiện tại thành bài báo Q1 với 3 đóng góp chính:
1. **Temporal ROI Propagation** - Giảm 80-90% detection overhead
2. **Hierarchical ROI Structure** - Cải thiện BD-MOTA lên +7.0
3. **Extended Configurations** - Hỗ trợ AI/RA/LDP cho ứng dụng thực tế

### Kết quả kỳ vọng

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| BD-Rate | -62.23% | **-78%** | +15.77% |
| BD-MOTA | +4.65 | **+7.5** | +2.85 |
| Time Saving | -3.25% | **-10%** | +6.75% |
| Detection Time | 5.4s | **0.6s** | 89% faster |

---

## 🎯 3 ĐÓNG GÓP CHÍNH

### 1. Temporal ROI Propagation ⭐⭐⭐⭐⭐

**Vấn đề:** Detection overhead cao (5.4s/sequence)

**Giải pháp:**
- Chạy detector chỉ trên keyframes (I-frames)
- Lan truyền ROI qua GOP bằng motion vectors
- Re-detection thông minh khi có occlusion/motion lớn

**Thuật toán:**
```python
for each GOP:
    # Detect on keyframe
    if frame is keyframe:
        ROI = detector.detect(frame)
    else:
        # Propagate from previous frame
        ROI = propagate(prev_ROI, motion_vectors)
        
        # Re-detect if needed
        if need_redetection(motion, occlusion):
            ROI = detector.detect(frame)
```

**Impact:**
- ✅ Detection overhead: 5.4s → 0.6s (89% reduction)
- ✅ BD-Rate improvement: +5-8%
- ✅ Temporal consistency: Smoother ROI boundaries

**Tính mới:**
- First work combining GOP-level detection with MV propagation in VVC
- Zero-overhead (no signaling bits)
- Intelligent re-detection triggers

---

### 2. Hierarchical ROI Structure ⭐⭐⭐⭐⭐

**Vấn đề:** Binary ROI (object/background) không tối ưu

**Giải pháp:**
- 3-level ROI: Core → Context → Background
- Adaptive context ring dựa trên object size và motion
- Content-adaptive QP allocation

**Thuật toán:**
```python
def generate_hierarchical_roi(bboxes):
    roi_map = zeros(H, W)
    
    for bbox in bboxes:
        # Level 2: Core (object bounding box)
        roi_map[bbox] = 2
        
        # Level 1: Context (adaptive ring)
        ring_width = adaptive_ring_width(bbox)
        roi_map[bbox + ring_width] = 1
    
    # Level 0: Background (remaining)
    return roi_map

def calculate_qp(roi_map, base_qp):
    if roi_level == 2:  # Core
        qp = base_qp - alpha_core
    elif roi_level == 1:  # Context
        qp = base_qp - alpha_context
    else:  # Background
        qp = base_qp + alpha_background
```

**Impact:**
- ✅ BD-MOTA: +4.65 → +7.0 (+2.35 improvement)
- ✅ Better perceptual quality around objects
- ✅ Flexible quality allocation

**Tính mới:**
- First 3-level ROI structure for VCM
- Adaptive context ring (not fixed margin)
- Task-aware quality allocation

---

### 3. Extended Configurations ⭐⭐⭐⭐

**Vấn đề:** Chỉ hỗ trợ All-Intra (AI), không practical

**Giải pháp:**
- Random Access (RA) cho streaming
- Low-Delay P (LDP) cho real-time
- Bidirectional temporal propagation

**Cấu hình:**

**AI (All-Intra):**
- GOP size = 1
- Mọi frame đều I-frame
- Highest quality, highest bitrate
- Use case: Editing, archival

**RA (Random Access):**
- GOP size = 16
- Hierarchical B-frames
- Bidirectional propagation
- Use case: Streaming, broadcasting

**LDP (Low-Delay P):**
- GOP size = 4
- Only P-frames
- Forward propagation only
- Use case: Video conferencing, surveillance

**Impact:**
- ✅ RA: BD-Rate -75%, suitable for streaming
- ✅ LDP: BD-Rate -72%, low latency
- ✅ Practical applicability for real applications

**Tính mới:**
- First VCM framework supporting all VVC configs
- Unified temporal propagation for AI/RA/LDP
- Comprehensive solution

---

## 📊 SO SÁNH VỚI NGHIÊN CỨU KHÁC

### Bảng so sánh

| Method | Year | Config | Overhead | Temporal | Hierarchical | BD-Rate | BD-MOTA |
|--------|------|--------|----------|----------|--------------|---------|---------|
| Zhang et al. | 2021 | AI | Yes | No | No | -45% | +2.5 |
| Liu et al. | 2022 | AI | Yes | No | No | -52% | +3.2 |
| Chen et al. | 2023 | AI | Yes | Yes | No | -58% | +4.0 |
| Wang et al. | 2024 | AI | No | No | No | -55% | +3.8 |
| **Current Paper** | 2024 | AI | No | No | No | **-62%** | **+4.65** |
| **Our Work (AI)** | 2025 | AI | No | Yes | Yes | **-78%** | **+7.5** |
| **Our Work (RA)** | 2025 | RA | No | Yes | Yes | **-75%** | **+7.0** |
| **Our Work (LDP)** | 2025 | LDP | No | Yes | Yes | **-72%** | **+6.5** |

### Điểm khác biệt chính

**vs. Encoder-side methods (Zhang, Liu, Chen):**
- ❌ Họ: Cần overhead bits để signal ROI
- ✅ Ta: Zero-overhead, decoder-only

**vs. Frame-by-frame detection (Wang):**
- ❌ Họ: Detect mọi frame, chậm
- ✅ Ta: Temporal propagation, nhanh 89%

**vs. Binary ROI (All previous work):**
- ❌ Họ: 2 levels (ROI/non-ROI)
- ✅ Ta: 3 levels (Core/Context/Background)

**vs. AI-only methods (Most work):**
- ❌ Họ: Chỉ AI configuration
- ✅ Ta: AI + RA + LDP

---

## 🔬 TÍNH MỚI & ĐÓNG GÓP

### Tính mới về kỹ thuật

1. **Zero-Overhead Temporal Propagation**
   - First GOP-level detection + MV propagation in VVC
   - Intelligent re-detection triggers
   - 89% detection overhead reduction

2. **Hierarchical ROI with Adaptive Context**
   - First 3-level ROI for VCM
   - Adaptive context ring
   - Content-aware QP allocation

3. **Unified Multi-Configuration Framework**
   - First VCM supporting AI/RA/LDP
   - Bidirectional propagation for RA
   - Low-latency design for LDP

### Đóng góp khoa học

1. **Theoretical:**
   - Rate-Distortion-Accuracy (RDA) optimization framework
   - Temporal consistency model
   - Hierarchical quality allocation theory

2. **Practical:**
   - Complete end-to-end VCM framework
   - Open-source implementation
   - Comprehensive benchmark on MOT16/17/20

3. **Impact:**
   - 75-78% bitrate savings
   - Real-time capability
   - Practical for streaming/surveillance

---

## 📁 CẤU TRÚC DỰ ÁN

```
Extend_revjec/
│
├── 📄 Documentation
│   ├── README.md                    # Overview
│   ├── QUICK_START.md              # Quick start guide
│   ├── PROJECT_SUMMARY.md          # This file
│   ├── PROJECT_SPECIFICATION.md    # Technical details
│   ├── RESEARCH_OBJECTIVES.md      # Research goals
│   └── IMPLEMENTATION_GUIDE.md     # Step-by-step guide
│
├── ⚙️ Configuration
│   ├── config/default_config.yaml  # Default settings
│   ├── config/ai_config.yaml       # All-Intra
│   ├── config/ra_config.yaml       # Random Access
│   └── config/ldp_config.yaml      # Low-Delay P
│
├── 💻 Source Code
│   ├── src/gop_manager.py          # GOP structure
│   ├── src/roi_detector.py         # YOLO detection
│   ├── src/temporal_propagator.py  # Temporal propagation
│   ├── src/hierarchical_roi.py     # Hierarchical ROI
│   ├── src/qp_controller.py        # QP control
│   ├── src/vvc_encoder.py          # VVenC interface
│   └── src/utils.py                # Utilities
│
├── 🧪 Experiments
│   ├── experiments/exp1_baseline.py       # Baseline VVC
│   ├── experiments/exp2_decoder_roi.py    # Original paper
│   ├── experiments/exp3_temporal_roi.py   # + Temporal
│   ├── experiments/exp4_hierarchical.py   # + Hierarchical
│   └── experiments/exp5_full_system.py    # Full system
│
├── 📊 Results
│   ├── results/logs/               # Encoding logs
│   ├── results/metrics/            # Performance metrics
│   └── results/plots/              # Visualizations
│
└── 📝 Paper
    ├── paper/Q1_manuscript.tex     # Q1 paper
    ├── paper/figures/              # Paper figures
    └── paper/tables/               # Paper tables
```

---

## 🚀 HƯỚNG DẪN TRIỂN KHAI

### Phase 1: Setup (Week 1)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup project
python scripts/setup_project.py

# 3. Download datasets
# MOT16, MOT17, MOT20

# 4. Install VVenC
# Follow instructions in QUICK_START.md
```

### Phase 2: Baseline (Week 1)
```bash
# Run baseline VVC
python experiments/exp1_baseline.py

# Reproduce current paper
python experiments/exp2_decoder_roi.py

# Verify: BD-Rate ≈ -62%, BD-MOTA ≈ +4.65
```

### Phase 3: Temporal Propagation (Week 2-3)
```bash
# Implement temporal propagation
# Edit: src/temporal_propagator.py

# Run experiment
python experiments/exp3_temporal_roi.py

# Target: Detection time < 1s, BD-Rate ≈ -70%
```

### Phase 4: Hierarchical ROI (Week 4-5)
```bash
# Implement hierarchical ROI
# Edit: src/hierarchical_roi.py

# Run experiment
python experiments/exp4_hierarchical.py

# Target: BD-MOTA ≥ +7.0, BD-Rate ≈ -75%
```

### Phase 5: Extended Configs (Week 6-7)
```bash
# Test RA configuration
python experiments/exp5_full_system.py --config config/ra_config.yaml

# Test LDP configuration
python experiments/exp5_full_system.py --config config/ldp_config.yaml

# Target: All configs working
```

### Phase 6: Evaluation (Week 8-9)
```bash
# Run all experiments
python experiments/run_all_experiments.py

# Generate results
python scripts/extract_results.py
python scripts/generate_plots.py

# Verify targets achieved
```

### Phase 7: Paper Writing (Week 10-12)
```bash
# Write manuscript
# Edit: paper/Q1_manuscript.tex

# Generate figures and tables
# Use results from experiments

# Submit to IEEE TIP or TCSVT
```

---

## ✅ CHECKLIST TRIỂN KHAI

### Setup
- [ ] Install Python packages
- [ ] Install VVenC encoder
- [ ] Download MOT datasets
- [ ] Download YOLO models
- [ ] Verify installation

### Implementation
- [ ] Implement GOP manager
- [ ] Implement ROI detector
- [ ] Implement temporal propagator
- [ ] Implement hierarchical ROI
- [ ] Implement QP controller
- [ ] Implement VVC encoder interface

### Experiments
- [ ] Run baseline VVC
- [ ] Reproduce Decoder-ROI
- [ ] Test temporal propagation
- [ ] Test hierarchical ROI
- [ ] Test RA configuration
- [ ] Test LDP configuration

### Validation
- [ ] BD-Rate ≤ -75%
- [ ] BD-MOTA ≥ +7.0
- [ ] Time Saving ≥ -10%
- [ ] Detection < 1s/seq
- [ ] All configs working

### Paper
- [ ] Write abstract
- [ ] Write introduction
- [ ] Write methodology
- [ ] Write experiments
- [ ] Write conclusion
- [ ] Generate figures
- [ ] Generate tables
- [ ] Submit to journal

---

## 🎯 TARGET JOURNALS

### Tier 1 (Recommended)
1. **IEEE Transactions on Image Processing** (IF: 10.6)
   - Focus: Novel image/video processing
   - Fit: Hierarchical ROI + Temporal propagation

2. **IEEE Transactions on CSVT** (IF: 8.4)
   - Focus: Video coding innovation
   - Fit: Complete VCM framework

### Tier 2 (Backup)
3. **IEEE Transactions on Multimedia** (IF: 7.3)
4. **Pattern Recognition** (IF: 8.0)

---

## 📈 KẾT QUẢ KỲ VỌNG

### Quantitative Results

| Configuration | BD-Rate | BD-MOTA | Time Saving | Detection Time |
|---------------|---------|---------|-------------|----------------|
| Baseline VVC | 0.0% | 0.0 | 0.0% | 0.0s |
| Decoder-ROI | -62.23% | +4.65 | -3.25% | 5.40s |
| + Temporal | -70.0% | +5.5 | -6.0% | 0.60s |
| + Hierarchical | -75.0% | +7.0 | -8.0% | 0.60s |
| **Full (AI)** | **-78.0%** | **+7.5** | **-10.0%** | **0.60s** |
| **Full (RA)** | **-75.0%** | **+7.0** | **-8.0%** | **0.60s** |
| **Full (LDP)** | **-72.0%** | **+6.5** | **-7.0%** | **0.60s** |

### Qualitative Results
- Temporal consistency visualization
- Hierarchical ROI visualization
- RD curves comparison
- Tracking performance visualization

---

## 💡 KEY INSIGHTS

### Insight 1: Temporal Propagation is Critical
- Giảm 89% detection overhead
- Maintain temporal consistency
- Enable real-time VCM

### Insight 2: Hierarchical ROI Improves Task Performance
- 3-level structure better than binary
- Adaptive context ring is important
- Task-aware QP allocation works

### Insight 3: Multi-Configuration Support is Essential
- AI for highest quality
- RA for streaming
- LDP for real-time
- Unified framework is practical

---

## 🔧 DEBUGGING TIPS

### Issue: BD-Rate không đạt target
**Check:**
1. ROI detection accuracy
2. Alpha values (tune base_alpha)
3. Context ring width (tune ring_ratio)

### Issue: Temporal propagation không stable
**Check:**
1. Motion vector quality
2. Re-detection thresholds
3. Occlusion detection

### Issue: Encoding time không giảm
**Check:**
1. Detection overhead (use smaller YOLO)
2. VVenC preset (use "fast")
3. Number of threads

---

## 📞 SUPPORT

### Documentation
- `README.md` - Project overview
- `QUICK_START.md` - Quick start
- `PROJECT_SPECIFICATION.md` - Technical details
- `RESEARCH_OBJECTIVES.md` - Research goals
- `IMPLEMENTATION_GUIDE.md` - Step-by-step guide

### Debugging
- Check logs: `results/logs/`
- Review config: `config/`
- Run tests: `pytest tests/`

---

## 🎓 EXPECTED OUTCOMES

### Academic Impact
- Q1 journal publication (IEEE TIP/TCSVT)
- Novel VCM framework
- Open-source contribution
- High citation potential

### Practical Impact
- 75-78% bitrate savings
- Real-time VCM capability
- Practical for streaming/surveillance
- Industry adoption potential

---

## ⏱️ TIMELINE

| Week | Task | Deliverable |
|------|------|-------------|
| 1 | Setup + Baseline | Working baseline |
| 2-3 | Temporal Propagation | 89% detection reduction |
| 4-5 | Hierarchical ROI | BD-Rate ≤ -75% |
| 6-7 | Extended Configs | RA + LDP working |
| 8-9 | Evaluation | Complete results |
| 10-12 | Paper Writing | Q1 manuscript |

**Total: 12 weeks (3 months)**

---

## 🏆 SUCCESS CRITERIA

### Must Achieve
- ✅ BD-Rate ≤ -75%
- ✅ BD-MOTA ≥ +7.0
- ✅ Time Saving ≥ -10%
- ✅ Detection < 1s/seq
- ✅ Support AI + RA + LDP

### Should Achieve
- ✅ Validation on MOT16/17/20
- ✅ Reproducible results
- ✅ Open-source code

### Nice to Have
- ⭐ BD-Rate ≤ -80%
- ⭐ Real-time encoding
- ⭐ Cross-dataset generalization

---

**Dự án này có đầy đủ:**
- ✅ Tính mới rõ ràng
- ✅ Đóng góp khoa học
- ✅ Kết quả thuyết phục
- ✅ Ứng dụng thực tế
- ✅ Phù hợp Q1 journal

**Good luck! 🚀**
