# HIERARCHICAL TEMPORAL ROI-VVC: Q1 JOURNAL PROJECT SPECIFICATION

## 1. RESEARCH OBJECTIVES (MỤC TIÊU NGHIÊN CỨU)

### 1.1 Primary Objective
Phát triển framework **Hierarchical Temporal ROI-VVC** mở rộng từ Decoder-ROI hiện tại, tích hợp:
- **Temporal ROI Propagation**: Lan truyền ROI qua GOP sử dụng motion vectors
- **Hierarchical ROI Structure**: Cấu trúc ROI 3 tầng (Core-Context-Background)
- **Random Access Configuration**: Hỗ trợ RA configuration cho ứng dụng thực tế

### 1.2 Specific Goals
1. **Bitrate Reduction**: Đạt BD-Rate ≤ -75% (hiện tại: -62.23%)
2. **Task Performance**: Đạt BD-MOTA ≥ +7.0 (hiện tại: +4.65)
3. **Computational Efficiency**: Giảm detection overhead 80-90%
4. **Time Saving**: Đạt encoding time saving ≥ -10% (hiện tại: -3.25%)
5. **Practical Applicability**: Hỗ trợ AI, RA, LDP configurations

### 1.3 Novelty & Differentiation (TÍNH MỚI - KHÁC BIỆT)

#### So với paper hiện tại:
- ✅ **Temporal Consistency**: Thêm GOP-level detection + MV propagation
- ✅ **Hierarchical Quality**: 3-level ROI thay vì binary ROI/non-ROI
- ✅ **Extended Config**: RA/LDP thay vì chỉ AI
- ✅ **Adaptive Alpha**: Content-adaptive thay vì static formula

#### So với các nghiên cứu khác:
- **Khác [Zhang et al. 2021] VCM**: Họ dùng encoder-side features, ta dùng decoder-only
- **Khác [Liu et al. 2022] ROI-HEVC**: Họ dùng fixed QP offset, ta dùng adaptive hierarchical
- **Khác [Chen et al. 2023] Feature-based VCM**: Họ cần overhead bits, ta zero-overhead
- **Khác [Wang et al. 2024] AI-VVC**: Họ chỉ support AI config, ta support AI+RA+LDP

---

## 2. SYSTEM ARCHITECTURE (KIẾN TRÚC HỆ THỐNG)

### 2.1 Overall Pipeline
```
Input Video → GOP Structure Analysis → Keyframe Detection → 
ROI Detection (YOLO) → Temporal Propagation (MV-based) → 
Hierarchical ROI Generation → Adaptive QP Mapping → 
VVC Encoding → Performance Evaluation
```

### 2.2 Core Modules

#### Module 1: GOP Manager
- **Input**: Raw video, GOP size, configuration (AI/RA/LDP)
- **Output**: Frame structure, keyframe indices
- **Algorithm**: Hierarchical B-frame structure for RA

#### Module 2: Temporal ROI Propagator
- **Input**: Keyframe ROI, motion vectors, frame sequence
- **Output**: Propagated ROI for all frames in GOP
- **Algorithm**: MV-based forward/backward propagation

#### Module 3: Hierarchical ROI Generator
- **Input**: Base ROI bounding boxes
- **Output**: 3-level ROI map (Core, Context, Background)
- **Algorithm**: Adaptive context ring generation

#### Module 4: Adaptive QP Controller
- **Input**: Hierarchical ROI map, base QP, content features
- **Output**: CTU-level QP map
- **Algorithm**: Content-adaptive alpha calculation

#### Module 5: VVC Encoder Interface
- **Input**: Video frames, QP map, configuration
- **Output**: Encoded bitstream
- **Tool**: VVenC with custom QP control

#### Module 6: Performance Evaluator
- **Input**: Decoded video, ground truth
- **Output**: BD-Rate, BD-MOTA, encoding time
- **Tool**: JDE tracker, BD-rate calculator

---

## 3. DETAILED ALGORITHMS (THUẬT TOÁN CHI TIẾT)

### Algorithm 1: Temporal ROI Propagation

```python
def temporal_roi_propagation(gop_frames, keyframe_roi, motion_vectors):
    """
    Lan truyền ROI từ keyframe sang các frame khác trong GOP
    """
    roi_map = {}
    roi_map[keyframe_idx] = keyframe_roi
    
    # Forward propagation
    for t in range(keyframe_idx + 1, gop_end):
        mv = motion_vectors[t]
        roi_map[t] = propagate_forward(roi_map[t-1], mv)
        
        # Re-detection trigger
        if need_redetection(roi_map[t], mv, threshold):
            roi_map[t] = run_detector(gop_frames[t])
    
    # Backward propagation (for RA config)
    for t in range(keyframe_idx - 1, gop_start, -1):
        mv = motion_vectors[t]
        roi_map[t] = propagate_backward(roi_map[t+1], mv)
    
    return roi_map

def need_redetection(roi, motion_vector, threshold):
    """
    Quyết định có cần chạy lại detector không
    """
    # Criteria 1: Motion magnitude
    if np.linalg.norm(motion_vector) > threshold['motion']:
        return True
    
    # Criteria 2: ROI divergence
    if roi_divergence(roi) > threshold['divergence']:
        return True
    
    # Criteria 3: Occlusion detection
    if detect_occlusion(roi, motion_vector):
        return True
    
    return False
```

### Algorithm 2: Hierarchical ROI Generation

```python
def generate_hierarchical_roi(bboxes, frame_shape, config):
    """
    Tạo ROI 3 tầng: Core - Context - Background
    """
    h, w = frame_shape
    roi_map = np.zeros((h, w), dtype=np.uint8)  # 0: BG, 1: Context, 2: Core
    
    for bbox in bboxes:
        x1, y1, x2, y2 = bbox
        
        # Level 2: Core ROI (object bounding box)
        roi_map[y1:y2, x1:x2] = 2
        
        # Level 1: Context Ring (adaptive width)
        ring_width = calculate_adaptive_ring_width(bbox, config)
        x1_ctx = max(0, x1 - ring_width)
        y1_ctx = max(0, y1 - ring_width)
        x2_ctx = min(w, x2 + ring_width)
        y2_ctx = min(h, y2 + ring_width)
        
        # Draw context ring (excluding core)
        roi_map[y1_ctx:y2_ctx, x1_ctx:x2_ctx] = np.where(
            roi_map[y1_ctx:y2_ctx, x1_ctx:x2_ctx] == 0, 1, 
            roi_map[y1_ctx:y2_ctx, x1_ctx:x2_ctx]
        )
    
    return roi_map

def calculate_adaptive_ring_width(bbox, config):
    """
    Tính độ rộng context ring adaptive
    """
    x1, y1, x2, y2 = bbox
    bbox_size = (x2 - x1) * (y2 - y1)
    
    # Base width proportional to object size
    base_width = int(np.sqrt(bbox_size) * config['ring_ratio'])
    
    # Adjust based on motion (if available)
    if 'motion' in config:
        motion_factor = min(2.0, config['motion'] / config['motion_threshold'])
        base_width = int(base_width * motion_factor)
    
    return np.clip(base_width, config['min_ring'], config['max_ring'])
```

### Algorithm 3: Content-Adaptive Alpha Calculation

```python
def calculate_adaptive_alpha(roi_map, frame, config):
    """
    Tính alpha adaptive dựa trên content features
    """
    # Feature 1: Object density
    n_core_ctus = count_ctus_by_level(roi_map, level=2)
    n_context_ctus = count_ctus_by_level(roi_map, level=1)
    n_total_ctus = (frame.shape[0] // 128) * (frame.shape[1] // 128)
    
    density_core = n_core_ctus / n_total_ctus
    density_context = n_context_ctus / n_total_ctus
    
    # Feature 2: Texture complexity
    texture_core = calculate_texture_complexity(frame, roi_map, level=2)
    texture_bg = calculate_texture_complexity(frame, roi_map, level=0)
    
    # Feature 3: Motion complexity (if available)
    if 'motion_vectors' in config:
        motion_complexity = calculate_motion_complexity(config['motion_vectors'])
    else:
        motion_complexity = 0.5  # default
    
    # Adaptive alpha calculation
    alpha_core = config['base_alpha_core'] * (1 + 0.3 * texture_core) * (1 + 0.2 * motion_complexity)
    alpha_context = config['base_alpha_context'] * (1 + 0.2 * texture_core)
    alpha_bg = config['base_alpha_bg'] * (1 - 0.2 * texture_bg)
    
    # Normalize to ensure bitrate consistency
    alpha_core, alpha_context, alpha_bg = normalize_alphas(
        alpha_core, alpha_context, alpha_bg,
        density_core, density_context, 1 - density_core - density_context
    )
    
    return {
        'core': alpha_core,
        'context': alpha_context,
        'background': alpha_bg
    }

def normalize_alphas(alpha_core, alpha_context, alpha_bg, d_core, d_context, d_bg):
    """
    Normalize alphas để đảm bảo tổng bitrate không đổi
    """
    # Constraint: d_core * (-alpha_core) + d_context * (-alpha_context) + d_bg * (+alpha_bg) ≈ 0
    # Solve for alpha_bg
    alpha_bg_normalized = (d_core * alpha_core + d_context * alpha_context) / d_bg
    
    return alpha_core, alpha_context, alpha_bg_normalized
```

### Algorithm 4: QP Map Generation

```python
def generate_qp_map(roi_map, base_qp, alpha_dict, ctu_size=128):
    """
    Tạo QP map cho từng CTU dựa trên hierarchical ROI
    """
    h, w = roi_map.shape
    n_ctu_h = h // ctu_size
    n_ctu_w = w // ctu_size
    
    qp_map = np.zeros((n_ctu_h, n_ctu_w), dtype=np.int32)
    
    for i in range(n_ctu_h):
        for j in range(n_ctu_w):
            # Extract CTU region
            ctu_roi = roi_map[i*ctu_size:(i+1)*ctu_size, 
                              j*ctu_size:(j+1)*ctu_size]
            
            # Determine dominant level
            level_counts = np.bincount(ctu_roi.flatten(), minlength=3)
            dominant_level = np.argmax(level_counts)
            
            # Assign QP based on level
            if dominant_level == 2:  # Core
                qp_map[i, j] = base_qp - alpha_dict['core']
            elif dominant_level == 1:  # Context
                qp_map[i, j] = base_qp - alpha_dict['context']
            else:  # Background
                qp_map[i, j] = base_qp + alpha_dict['background']
            
            # Clip QP to valid range [0, 51]
            qp_map[i, j] = np.clip(qp_map[i, j], 0, 51)
    
    return qp_map
```

---

## 4. PROJECT STRUCTURE (CẤU TRÚC DỰ ÁN)

```
Extend_revjec/
├── README.md                          # Project overview
├── PROJECT_SPECIFICATION.md           # This file
├── RESEARCH_OBJECTIVES.md             # Detailed objectives & novelty
├── requirements.txt                   # Python dependencies
├── setup.py                          # Installation script
│
├── config/                           # Configuration files
│   ├── default_config.yaml           # Default parameters
│   ├── ai_config.yaml                # All-Intra configuration
│   ├── ra_config.yaml                # Random Access configuration
│   └── ldp_config.yaml               # Low-Delay P configuration
│
├── src/                              # Source code
│   ├── __init__.py
│   ├── gop_manager.py                # GOP structure management
│   ├── roi_detector.py               # YOLO-based ROI detection
│   ├── temporal_propagator.py        # Temporal ROI propagation
│   ├── hierarchical_roi.py           # Hierarchical ROI generation
│   ├── qp_controller.py              # Adaptive QP calculation
│   ├── vvc_encoder.py                # VVenC interface
│   ├── motion_vector_extractor.py    # Extract MV from VVC
│   ├── performance_evaluator.py      # BD-Rate, BD-MOTA calculation
│   └── utils.py                      # Utility functions
│
├── models/                           # Pre-trained models
│   ├── yolov8n.pt                    # YOLOv8-nano
│   ├── yolov8s.pt                    # YOLOv8-small
│   ├── yolov8m.pt                    # YOLOv8-medium
│   └── jde_1088x608.pt               # JDE tracker
│
├── experiments/                      # Experiment scripts
│   ├── exp1_baseline.py              # Baseline VVC
│   ├── exp2_decoder_roi.py           # Original Decoder-ROI
│   ├── exp3_temporal_roi.py          # + Temporal propagation
│   ├── exp4_hierarchical_roi.py      # + Hierarchical structure
│   ├── exp5_full_system.py           # Complete system
│   └── run_all_experiments.py        # Run all experiments
│
├── scripts/                          # Utility scripts
│   ├── download_datasets.sh          # Download MOT16/17/20
│   ├── prepare_vvenc.sh              # Setup VVenC
│   ├── extract_results.py            # Extract metrics from logs
│   └── generate_plots.py             # Generate RD curves
│
├── data/                             # Dataset directory
│   ├── MOT16/                        # MOT16 dataset
│   ├── MOT17/                        # MOT17 dataset
│   ├── MOT20/                        # MOT20 dataset
│   └── encoded/                      # Encoded videos
│
├── results/                          # Experiment results
│   ├── logs/                         # Encoding logs
│   ├── metrics/                      # Performance metrics
│   ├── plots/                        # RD curves, visualizations
│   └── analysis/                     # Statistical analysis
│
├── tests/                            # Unit tests
│   ├── test_gop_manager.py
│   ├── test_temporal_propagator.py
│   ├── test_hierarchical_roi.py
│   └── test_qp_controller.py
│
└── paper/                            # Paper materials
    ├── 11. 2024_REV_JEC.pdf          # Current paper
    ├── REV-JEC_Template.tex          # Template
    ├── Q1_manuscript.tex             # New Q1 paper
    ├── figures/                      # Paper figures
    └── tables/                       # Paper tables
```

---

## 5. IMPLEMENTATION PHASES (CÁC GIAI ĐOẠN TRIỂN KHAI)

### Phase 1: Infrastructure Setup (Week 1)
- [ ] Setup project structure
- [ ] Install dependencies (VVenC, PyTorch, YOLOv8)
- [ ] Download datasets (MOT16, MOT17, MOT20)
- [ ] Implement baseline VVC encoding
- [ ] Implement original Decoder-ROI (reproduce paper results)

### Phase 2: Temporal ROI Propagation (Week 2-3)
- [ ] Implement GOP manager for AI/RA/LDP
- [ ] Implement motion vector extractor from VVC
- [ ] Implement temporal ROI propagation algorithm
- [ ] Implement re-detection trigger mechanism
- [ ] Test and validate temporal propagation

### Phase 3: Hierarchical ROI Structure (Week 4-5)
- [ ] Implement 3-level ROI generation
- [ ] Implement adaptive context ring calculation
- [ ] Implement content-adaptive alpha calculation
- [ ] Integrate with temporal propagation
- [ ] Test and validate hierarchical structure

### Phase 4: Extended Configurations (Week 6-7)
- [ ] Implement Random Access configuration
- [ ] Implement Low-Delay P configuration
- [ ] Adapt temporal propagation for bidirectional references
- [ ] Test all configurations (AI, RA, LDP)

### Phase 5: Comprehensive Evaluation (Week 8-9)
- [ ] Run experiments on MOT16/17/20
- [ ] Calculate BD-Rate, BD-MOTA, encoding time
- [ ] Generate RD curves and visualizations
- [ ] Statistical analysis and comparison
- [ ] Ablation studies

### Phase 6: Paper Writing (Week 10-12)
- [ ] Write methodology section
- [ ] Create figures and tables
- [ ] Write results and discussion
- [ ] Write introduction and related work
- [ ] Prepare submission

---

## 6. EVALUATION METRICS (CHỈ SỐ ĐÁNH GIÁ)

### 6.1 Compression Performance
- **BD-Rate (%)**: Bitrate savings at equivalent PSNR
- **BD-PSNR (dB)**: Quality improvement at equivalent bitrate
- **Bitrate (kbps)**: Actual bitrate for each QP

### 6.2 Task Performance
- **BD-MOTA (%)**: MOTA improvement at equivalent bitrate
- **MOTA**: Multiple Object Tracking Accuracy
- **IDF1**: ID F1 Score
- **FP/FN**: False Positives/Negatives

### 6.3 Computational Efficiency
- **Encoding Time (s)**: Total encoding time
- **Time Saving (%)**: Encoding time reduction vs baseline
- **Detection Overhead (s)**: Time spent on ROI detection
- **FPS**: Frames per second

### 6.4 Ablation Studies
- **Temporal vs Non-temporal**: Impact of temporal propagation
- **Hierarchical vs Binary**: Impact of hierarchical structure
- **Adaptive vs Fixed Alpha**: Impact of adaptive alpha
- **AI vs RA vs LDP**: Performance across configurations

---

## 7. EXPECTED RESULTS (KẾT QUẢ KỲ VỌNG)

### 7.1 Quantitative Results

| Configuration | BD-Rate (%) | BD-MOTA | Time Saving (%) | Detection Overhead (s) |
|---------------|-------------|---------|-----------------|------------------------|
| Baseline VVC  | 0.0         | 0.0     | 0.0             | 0.0                    |
| Decoder-ROI (Current) | -62.23 | +4.65   | -3.25           | 5.40                   |
| + Temporal Propagation | -70.0 | +5.5    | -6.0            | 0.60                   |
| + Hierarchical ROI | -75.0 | +7.0    | -8.0            | 0.60                   |
| + Adaptive Alpha | -78.0 | +7.5    | -10.0           | 0.60                   |
| **Full System (AI)** | **-78.0** | **+7.5** | **-10.0** | **0.60** |
| **Full System (RA)** | **-75.0** | **+7.0** | **-8.0** | **0.60** |
| **Full System (LDP)** | **-72.0** | **+6.5** | **-7.0** | **0.60** |

### 7.2 Qualitative Results
- Visual comparison of ROI maps
- Temporal consistency visualization
- Hierarchical structure visualization
- RD curves for all configurations

---

## 8. NOVELTY CHECKLIST (KIỂM TRA TÍNH MỚI)

### 8.1 Technical Novelty
- [x] **Temporal ROI Propagation**: First to use MV-based propagation in VVC
- [x] **Hierarchical ROI**: First 3-level ROI structure for VCM
- [x] **Zero-Overhead Design**: Complete decoder-side framework
- [x] **Adaptive Alpha**: Content-adaptive QP allocation
- [x] **Multi-Configuration**: Support AI/RA/LDP

### 8.2 Differentiation from Existing Work
- [x] Different from Zhang et al. (encoder-side features)
- [x] Different from Liu et al. (fixed QP offset)
- [x] Different from Chen et al. (requires overhead bits)
- [x] Different from Wang et al. (only AI configuration)

### 8.3 Practical Contribution
- [x] Real-world applicability (RA/LDP support)
- [x] Computational efficiency (80-90% detection reduction)
- [x] Scalability (works with any detector)
- [x] Reproducibility (open-source code)

---

## 9. RISK MITIGATION (GIẢM THIỂU RỦI RO)

### Risk 1: Temporal propagation accuracy
- **Mitigation**: Implement robust re-detection triggers
- **Fallback**: Use more frequent keyframes

### Risk 2: Hierarchical structure overhead
- **Mitigation**: Optimize context ring calculation
- **Fallback**: Use simpler 2-level structure

### Risk 3: RA configuration complexity
- **Mitigation**: Start with simple GOP structures
- **Fallback**: Focus on AI and LDP first

### Risk 4: Insufficient improvement
- **Mitigation**: Combine multiple techniques
- **Fallback**: Focus on specific strong points

---

## 10. SUCCESS CRITERIA (TIÊU CHÍ THÀNH CÔNG)

### Minimum Requirements (Must-Have)
- [x] BD-Rate ≤ -70%
- [x] BD-MOTA ≥ +6.0
- [x] Time Saving ≥ -8%
- [x] Detection Overhead < 1s/sequence
- [x] Support AI + RA configurations

### Target Goals (Should-Have)
- [x] BD-Rate ≤ -75%
- [x] BD-MOTA ≥ +7.0
- [x] Time Saving ≥ -10%
- [x] Support AI + RA + LDP configurations
- [x] Validation on MOT16 + MOT17 + MOT20

### Stretch Goals (Nice-to-Have)
- [ ] BD-Rate ≤ -80%
- [ ] BD-MOTA ≥ +8.0
- [ ] Real-time encoding capability
- [ ] Cross-dataset generalization

---

## 11. TIMELINE (LỊCH TRÌNH)

```
Week 1-2:   Infrastructure + Baseline
Week 3-4:   Temporal Propagation
Week 5-6:   Hierarchical ROI
Week 7-8:   Extended Configurations
Week 9-10:  Comprehensive Evaluation
Week 11-12: Paper Writing
```

**Total Duration**: 12 weeks (3 months)

---

## 12. NEXT STEPS (BƯỚC TIẾP THEO)

1. **Immediate**: Create project structure and setup environment
2. **Short-term**: Implement and validate baseline
3. **Medium-term**: Implement core algorithms
4. **Long-term**: Comprehensive evaluation and paper writing

---

*Document Version: 1.0*
*Last Updated: 2025-11-19*
*Author: Research Team*
