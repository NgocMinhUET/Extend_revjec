# IMPLEMENTATION GUIDE - HIERARCHICAL TEMPORAL ROI-VVC

## HƯỚNG DẪN TRIỂN KHAI CHI TIẾT

Tài liệu này cung cấp hướng dẫn từng bước để triển khai dự án từ đầu đến khi có kết quả thực tế cho bài báo Q1.

---

## PHASE 1: SETUP ENVIRONMENT (Tuần 1)

### Bước 1.1: Cài đặt môi trường Python

```bash
# Tạo virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### Bước 1.2: Cài đặt VVenC Encoder

```bash
# Clone VVenC repository
git clone https://github.com/fraunhoferhhi/vvenc.git
cd vvenc

# Build (Windows - Visual Studio)
mkdir build
cd build
cmake .. -G "Visual Studio 16 2019" -A x64
cmake --build . --config Release

# Build (Linux)
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j8

# Add to PATH
export PATH=$PATH:/path/to/vvenc/bin
```

### Bước 1.3: Download Datasets

```bash
# MOT16
wget https://motchallenge.net/data/MOT16.zip
unzip MOT16.zip -d data/

# MOT17
wget https://motchallenge.net/data/MOT17.zip
unzip MOT17.zip -d data/

# MOT20
wget https://motchallenge.net/data/MOT20.zip
unzip MOT20.zip -d data/
```

### Bước 1.4: Download Pre-trained Models

```python
# models/download_models.py
from ultralytics import YOLO

# Download YOLOv8 models
models = ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt']
for model_name in models:
    model = YOLO(model_name)
    print(f"Downloaded {model_name}")

# Download JDE tracker
# Manual download from: https://github.com/Zhongdao/Towards-Realtime-MOT
```

### Bước 1.5: Verify Installation

```python
# scripts/verify_installation.py
import torch
import cv2
import numpy as np
from ultralytics import YOLO

print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("OpenCV version:", cv2.__version__)

# Test YOLO
model = YOLO('yolov8n.pt')
print("YOLO loaded successfully")

# Test VVenC
import subprocess
result = subprocess.run(['vvencapp', '--help'], capture_output=True)
print("VVenC available:", result.returncode == 0)
```

---

## PHASE 2: IMPLEMENT BASELINE (Tuần 1)

### Bước 2.1: Implement Baseline VVC Encoder

```python
# src/vvc_encoder.py (baseline)
import subprocess
import os
from pathlib import Path

class VVCEncoder:
    def __init__(self, config):
        self.config = config
        self.encoder_config = config['encoder']
        
    def encode_video(self, input_video, output_bitstream, qp):
        """Encode video with VVenC"""
        cmd = [
            'vvencapp',
            '-i', input_video,
            '-o', output_bitstream,
            '-q', str(qp),
            '-c', self._get_config_file(),
            '--threads', str(self.encoder_config['threads']),
        ]
        
        # Run encoding
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse encoding time and bitrate
        encoding_time = self._parse_encoding_time(result.stderr)
        bitrate = self._parse_bitrate(result.stderr)
        
        return {
            'encoding_time': encoding_time,
            'bitrate': bitrate,
            'output_file': output_bitstream
        }
```

### Bước 2.2: Implement Baseline Experiment

```python
# experiments/exp1_baseline.py
import sys
sys.path.append('src')

from vvc_encoder import VVCEncoder
from performance_evaluator import PerformanceEvaluator
from utils import load_config, setup_logging

def run_baseline_experiment(config_path):
    # Load config
    config = load_config(config_path)
    logger = setup_logging(config)
    
    # Initialize encoder
    encoder = VVCEncoder(config)
    
    # Get sequences
    sequences = config['dataset']['sequences']
    qp_values = config['encoder']['qp_values']
    
    results = []
    
    for seq in sequences:
        logger.info(f"Processing {seq}...")
        
        for qp in qp_values:
            # Encode
            input_video = f"data/MOT16/train/{seq}/img1/%06d.jpg"
            output_bitstream = f"data/encoded/baseline_{seq}_qp{qp}.266"
            
            result = encoder.encode_video(input_video, output_bitstream, qp)
            results.append(result)
            
            logger.info(f"  QP={qp}: {result['bitrate']:.2f} kbps, "
                       f"{result['encoding_time']:.2f}s")
    
    # Save results
    save_results(results, 'results/metrics/baseline.csv')

if __name__ == '__main__':
    run_baseline_experiment('config/ai_config.yaml')
```

### Bước 2.3: Run Baseline

```bash
python experiments/exp1_baseline.py
```

**Expected Output:**
```
Processing MOT16-02...
  QP=22: 5234.56 kbps, 145.23s
  QP=27: 3456.78 kbps, 132.45s
  QP=32: 2123.45 kbps, 125.67s
  QP=37: 1234.56 kbps, 118.89s
...
```

---

## PHASE 3: IMPLEMENT DECODER-ROI (Tuần 2)

### Bước 3.1: Implement Original Decoder-ROI

Mục tiêu: **Reproduce kết quả paper hiện tại** (BD-Rate: -62.23%, BD-MOTA: +4.65)

```python
# experiments/exp2_decoder_roi.py
def run_decoder_roi_experiment(config_path):
    config = load_config(config_path)
    logger = setup_logging(config)
    
    # Initialize components
    detector = ROIDetector(config, logger)
    qp_controller = QPController(config)
    encoder = VVCEncoder(config)
    
    for seq in config['dataset']['sequences']:
        # Load video frames
        frames = load_video_frames(seq)
        
        for qp in config['encoder']['qp_values']:
            # Process each frame
            for i, frame in enumerate(frames):
                # Detect ROI
                bboxes, scores, class_ids = detector.detect(frame)
                
                # Generate QP map
                qp_map = qp_controller.generate_qp_map(
                    frame.shape, bboxes, qp
                )
                
                # Encode with QP map
                # ... (encoding logic)
```

### Bước 3.2: Validate Decoder-ROI Results

**Kiểm tra:**
- BD-Rate phải đạt khoảng -60% đến -65%
- BD-MOTA phải đạt khoảng +4.0 đến +5.0
- Time saving khoảng -3% đến -4%

Nếu kết quả không khớp, cần debug:
1. Kiểm tra ROI detection accuracy
2. Kiểm tra QP map generation
3. Kiểm tra alpha calculation

---

## PHASE 4: IMPLEMENT TEMPORAL PROPAGATION (Tuần 3-4)

### Bước 4.1: Implement Motion Vector Extractor

```python
# src/motion_vector_extractor.py
class MotionVectorExtractor:
    """Extract motion vectors from VVC decoder"""
    
    def extract_from_bitstream(self, bitstream_path):
        """
        Extract MVs from VVC bitstream
        
        Returns:
            Dictionary mapping frame_idx -> motion_vectors (H, W, 2)
        """
        # Use VVC decoder with MV output
        cmd = [
            'vvdecapp',
            '-b', bitstream_path,
            '--SEIDecodedPictureHash', '0',
            '--OutputMV', 'mv_output.txt'
        ]
        
        subprocess.run(cmd)
        
        # Parse MV file
        mvs = self._parse_mv_file('mv_output.txt')
        return mvs
    
    def extract_optical_flow(self, frame1, frame2):
        """
        Extract optical flow as alternative to MVs
        """
        import cv2
        
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        flow = cv2.calcOpticalFlowFarneback(
            gray1, gray2, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        return flow
```

### Bước 4.2: Implement Temporal Propagator

```python
# src/temporal_propagator.py
class TemporalPropagator:
    """Propagate ROI across frames using motion vectors"""
    
    def propagate_forward(self, roi_bboxes, motion_vectors):
        """
        Propagate ROI from frame t to frame t+1
        
        Args:
            roi_bboxes: (N, 4) bounding boxes at frame t
            motion_vectors: (H, W, 2) motion vectors
            
        Returns:
            Propagated bboxes at frame t+1
        """
        propagated_bboxes = []
        
        for bbox in roi_bboxes:
            x1, y1, x2, y2 = bbox
            
            # Sample MVs within bbox
            mvs_in_bbox = motion_vectors[
                int(y1):int(y2), int(x1):int(x2)
            ]
            
            # Calculate median MV
            median_mv = np.median(mvs_in_bbox.reshape(-1, 2), axis=0)
            
            # Propagate bbox
            new_bbox = bbox + np.array([
                median_mv[0], median_mv[1],
                median_mv[0], median_mv[1]
            ])
            
            propagated_bboxes.append(new_bbox)
        
        return np.array(propagated_bboxes)
    
    def need_redetection(self, roi_bboxes, motion_vectors, threshold):
        """
        Determine if re-detection is needed
        
        Criteria:
        1. High motion magnitude
        2. ROI divergence
        3. Occlusion detection
        """
        # Criterion 1: Motion magnitude
        motion_magnitude = np.linalg.norm(motion_vectors, axis=2)
        mean_motion = np.mean(motion_magnitude)
        
        if mean_motion > threshold['motion']:
            return True
        
        # Criterion 2: ROI divergence
        if len(roi_bboxes) > 0:
            bbox_sizes = (roi_bboxes[:, 2] - roi_bboxes[:, 0]) * \
                        (roi_bboxes[:, 3] - roi_bboxes[:, 1])
            size_variation = np.std(bbox_sizes) / np.mean(bbox_sizes)
            
            if size_variation > threshold['divergence']:
                return True
        
        # Criterion 3: Occlusion (simplified)
        # Check for sudden MV changes
        mv_variance = np.var(motion_vectors)
        if mv_variance > threshold.get('mv_variance', 100):
            return True
        
        return False
```

### Bước 4.3: Integrate Temporal Propagation

```python
# experiments/exp3_temporal_roi.py
def run_temporal_roi_experiment(config_path):
    config = load_config(config_path)
    
    # Initialize
    gop_manager = GOPManager(config)
    detector = ROIDetector(config)
    propagator = TemporalPropagator(config)
    mv_extractor = MotionVectorExtractor(config)
    
    for seq in config['dataset']['sequences']:
        frames = load_video_frames(seq)
        n_frames = len(frames)
        
        # Get keyframe indices
        keyframe_indices = gop_manager.get_keyframe_indices(n_frames)
        
        # Initialize ROI cache
        roi_cache = {}
        
        for i, frame in enumerate(frames):
            if i in keyframe_indices:
                # Run detector on keyframe
                bboxes, _, _ = detector.detect(frame)
                roi_cache[i] = bboxes
            else:
                # Propagate from previous frame
                prev_idx = i - 1
                if prev_idx in roi_cache:
                    # Get motion vectors
                    mv = mv_extractor.extract_optical_flow(
                        frames[prev_idx], frame
                    )
                    
                    # Check if re-detection needed
                    if propagator.need_redetection(
                        roi_cache[prev_idx], mv, config['thresholds']
                    ):
                        # Re-detect
                        bboxes, _, _ = detector.detect(frame)
                        roi_cache[i] = bboxes
                    else:
                        # Propagate
                        roi_cache[i] = propagator.propagate_forward(
                            roi_cache[prev_idx], mv
                        )
```

### Bước 4.4: Measure Temporal Propagation Impact

**Expected Results:**
- Detection overhead: Giảm từ ~5.4s xuống ~0.6s (80-90% reduction)
- BD-Rate: Cải thiện thêm ~5-8% (từ -62% lên -70%)
- Temporal consistency: Smoother ROI boundaries

---

## PHASE 5: IMPLEMENT HIERARCHICAL ROI (Tuần 5-6)

### Bước 5.1: Implement Hierarchical ROI Generator

```python
# src/hierarchical_roi.py
class HierarchicalROI:
    """Generate 3-level hierarchical ROI structure"""
    
    def generate(self, frame_shape, bboxes, config):
        """
        Generate hierarchical ROI map
        
        Returns:
            roi_map: (H, W) array with values 0, 1, 2
                0 = Background
                1 = Context
                2 = Core
        """
        h, w = frame_shape[:2]
        roi_map = np.zeros((h, w), dtype=np.uint8)
        
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox.astype(int)
            
            # Level 2: Core ROI
            roi_map[y1:y2, x1:x2] = 2
            
            # Level 1: Context Ring
            ring_width = self._calculate_adaptive_ring_width(
                bbox, config
            )
            
            x1_ctx = max(0, x1 - ring_width)
            y1_ctx = max(0, y1 - ring_width)
            x2_ctx = min(w, x2 + ring_width)
            y2_ctx = min(h, y2 + ring_width)
            
            # Draw context (don't overwrite core)
            context_mask = np.zeros((h, w), dtype=bool)
            context_mask[y1_ctx:y2_ctx, x1_ctx:x2_ctx] = True
            context_mask[y1:y2, x1:x2] = False
            
            roi_map[context_mask] = 1
        
        return roi_map
    
    def _calculate_adaptive_ring_width(self, bbox, config):
        """Calculate adaptive context ring width"""
        x1, y1, x2, y2 = bbox
        bbox_area = (x2 - x1) * (y2 - y1)
        
        # Base width proportional to bbox size
        base_width = int(np.sqrt(bbox_area) * config['ring_ratio'])
        
        # Clip to min/max
        return np.clip(
            base_width,
            config['min_ring'],
            config['max_ring']
        )
```

### Bước 5.2: Implement Content-Adaptive Alpha

```python
# src/qp_controller.py
class QPController:
    """Control QP allocation with adaptive alpha"""
    
    def calculate_adaptive_alpha(self, frame, roi_map, config):
        """
        Calculate content-adaptive alpha values
        
        Returns:
            Dictionary with alpha for each level
        """
        # Calculate features
        texture_core = self._calculate_texture(
            frame, roi_map == 2
        )
        texture_bg = self._calculate_texture(
            frame, roi_map == 0
        )
        
        # Calculate densities
        n_core = np.sum(roi_map == 2)
        n_context = np.sum(roi_map == 1)
        n_bg = np.sum(roi_map == 0)
        n_total = roi_map.size
        
        density_core = n_core / n_total
        density_context = n_context / n_total
        density_bg = n_bg / n_total
        
        # Base alphas
        alpha_core = config['base_alpha']['core']
        alpha_context = config['base_alpha']['context']
        alpha_bg = config['base_alpha']['background']
        
        # Adjust by texture
        alpha_core *= (1 + 0.3 * texture_core)
        alpha_context *= (1 + 0.2 * texture_core)
        alpha_bg *= (1 - 0.2 * texture_bg)
        
        # Normalize to maintain bitrate
        alpha_bg = (density_core * alpha_core + 
                   density_context * alpha_context) / density_bg
        
        return {
            'core': alpha_core,
            'context': alpha_context,
            'background': alpha_bg
        }
```

### Bước 5.3: Test Hierarchical ROI

**Expected Results:**
- BD-Rate: Cải thiện thêm ~5% (từ -70% lên -75%)
- BD-MOTA: Cải thiện thêm ~1.5 (từ +5.5 lên +7.0)
- Visual quality: Better perceptual quality around objects

---

## PHASE 6: IMPLEMENT RA/LDP CONFIGURATIONS (Tuần 7-8)

### Bước 6.1: Adapt for Random Access

```python
# Modify temporal_propagator.py for bidirectional propagation
def propagate_bidirectional(self, roi_cache, frame_idx, gop_structure):
    """
    Propagate ROI bidirectionally for B-frames
    """
    # Get reference frames
    ref_frames = gop_structure[frame_idx].ref_frames
    
    if len(ref_frames) == 2:
        # Bidirectional (B-frame)
        ref_past, ref_future = ref_frames
        
        # Propagate from both references
        roi_from_past = self.propagate_forward(
            roi_cache[ref_past], mv_past_to_current
        )
        roi_from_future = self.propagate_backward(
            roi_cache[ref_future], mv_future_to_current
        )
        
        # Merge ROIs
        merged_roi = self.merge_rois(roi_from_past, roi_from_future)
        return merged_roi
```

### Bước 6.2: Test RA Configuration

```bash
python experiments/exp5_full_system.py --config config/ra_config.yaml
```

**Expected Results (RA):**
- BD-Rate: -75% (slightly lower than AI due to temporal prediction)
- BD-MOTA: +7.0
- Practical applicability: Suitable for streaming

### Bước 6.3: Test LDP Configuration

```bash
python experiments/exp5_full_system.py --config config/ldp_config.yaml
```

**Expected Results (LDP):**
- BD-Rate: -72% (lower due to low-delay constraints)
- BD-MOTA: +6.5
- Encoding latency: Suitable for real-time applications

---

## PHASE 7: COMPREHENSIVE EVALUATION (Tuần 9-10)

### Bước 7.1: Run All Experiments

```bash
# Run all configurations
python experiments/run_all_experiments.py

# This will run:
# 1. Baseline VVC
# 2. Decoder-ROI (original)
# 3. + Temporal Propagation
# 4. + Hierarchical ROI
# 5. + Adaptive Alpha
# 6. Full System (AI/RA/LDP)
```

### Bước 7.2: Calculate Metrics

```python
# src/performance_evaluator.py
class PerformanceEvaluator:
    def calculate_bd_rate(self, rate1, psnr1, rate2, psnr2):
        """Calculate BD-Rate using Bjontegaard metric"""
        # Implementation using pchip interpolation
        pass
    
    def calculate_bd_mota(self, rate1, mota1, rate2, mota2):
        """Calculate BD-MOTA"""
        pass
    
    def run_tracking_evaluation(self, decoded_video, gt_file):
        """Run JDE tracker and calculate MOTA"""
        # Run JDE tracker
        # Calculate MOTA, IDF1, FP, FN
        pass
```

### Bước 7.3: Generate Results Tables

```python
# scripts/generate_results.py
def generate_results_table():
    """
    Generate comprehensive results table
    
    Table format:
    | Method | BD-Rate (%) | BD-MOTA | Time Saving (%) | Detection Time (s) |
    """
    pass
```

**Expected Final Results:**

| Method | BD-Rate (%) | BD-MOTA | Time Saving (%) | Detection Time (s) |
|--------|-------------|---------|-----------------|-------------------|
| Baseline VVC | 0.0 | 0.0 | 0.0 | 0.0 |
| Decoder-ROI | -62.23 | +4.65 | -3.25 | 5.40 |
| + Temporal | -70.0 | +5.5 | -6.0 | 0.60 |
| + Hierarchical | -75.0 | +7.0 | -8.0 | 0.60 |
| + Adaptive Alpha | -78.0 | +7.5 | -10.0 | 0.60 |
| **Full (AI)** | **-78.0** | **+7.5** | **-10.0** | **0.60** |
| **Full (RA)** | **-75.0** | **+7.0** | **-8.0** | **0.60** |
| **Full (LDP)** | **-72.0** | **+6.5** | **-7.0** | **0.60** |

### Bước 7.4: Generate Plots

```python
# scripts/generate_plots.py
import matplotlib.pyplot as plt

def plot_rd_curves():
    """Plot Rate-Distortion curves"""
    # Plot bitrate vs PSNR
    # Plot bitrate vs MOTA
    pass

def plot_temporal_consistency():
    """Visualize temporal ROI consistency"""
    pass

def plot_hierarchical_structure():
    """Visualize 3-level ROI structure"""
    pass
```

---

## PHASE 8: PAPER WRITING (Tuần 11-12)

### Bước 8.1: Prepare Figures

**Figure 1:** System Architecture
- Overall pipeline diagram
- Show temporal propagation flow
- Show hierarchical ROI structure

**Figure 2:** Temporal Propagation
- Keyframe detection
- MV-based propagation
- Re-detection triggers

**Figure 3:** Hierarchical ROI
- 3-level structure visualization
- Adaptive context ring
- QP map generation

**Figure 4:** RD Curves
- Bitrate vs PSNR
- Bitrate vs MOTA
- Compare all methods

**Figure 5:** Qualitative Results
- Visual comparison of ROI maps
- Temporal consistency
- Tracking results

### Bước 8.2: Prepare Tables

**Table I:** Dataset Characteristics
**Table II:** Experimental Settings
**Table III:** Compression Performance (BD-Rate, BD-PSNR)
**Table IV:** Task Performance (BD-MOTA, MOTA, IDF1)
**Table V:** Computational Efficiency
**Table VI:** Ablation Study
**Table VII:** Comparison with State-of-the-Art

### Bước 8.3: Write Sections

**Abstract:** 150-200 words
- Problem statement
- Proposed method (3 key contributions)
- Results (quantitative)

**Introduction:** 2-3 pages
- Background on VCM
- Limitations of existing work
- Our contributions (numbered list)
- Paper organization

**Related Work:** 2 pages
- Video coding standards
- ROI-based coding
- VCM approaches
- Differentiate from existing work

**Proposed Method:** 4-5 pages
- Overall framework
- Temporal ROI propagation
- Hierarchical ROI structure
- Adaptive QP control
- Implementation details

**Experiments:** 3-4 pages
- Experimental setup
- Datasets and metrics
- Comparison with baselines
- Ablation studies
- Qualitative analysis

**Conclusion:** 1 page
- Summary of contributions
- Key findings
- Limitations
- Future work

---

## DEBUGGING TIPS

### Issue 1: BD-Rate không đạt target

**Possible causes:**
1. ROI detection không accurate
2. Alpha calculation không optimal
3. Context ring quá lớn/nhỏ

**Solutions:**
1. Tune confidence threshold
2. Adjust base alpha values
3. Tune ring_ratio parameter

### Issue 2: Temporal propagation không stable

**Possible causes:**
1. Motion vectors không accurate
2. Re-detection threshold không phù hợp
3. Occlusion không được xử lý

**Solutions:**
1. Use optical flow thay vì MVs
2. Tune motion_threshold
3. Implement better occlusion detection

### Issue 3: Encoding time không giảm

**Possible causes:**
1. Detection overhead vẫn cao
2. QP map generation chậm
3. VVenC configuration không optimal

**Solutions:**
1. Use smaller YOLO model (nano)
2. Optimize QP map generation
3. Use faster VVenC preset

---

## VALIDATION CHECKLIST

### Technical Validation
- [ ] Baseline VVC results match reference
- [ ] Decoder-ROI reproduces paper results
- [ ] Temporal propagation reduces detection overhead 80%+
- [ ] Hierarchical ROI improves BD-MOTA
- [ ] RA/LDP configurations work correctly

### Performance Validation
- [ ] BD-Rate ≤ -75%
- [ ] BD-MOTA ≥ +7.0
- [ ] Time Saving ≥ -10%
- [ ] Detection Overhead < 1s/sequence

### Code Quality
- [ ] All modules have unit tests
- [ ] Code follows PEP 8 style
- [ ] Documentation is complete
- [ ] No hardcoded paths

### Reproducibility
- [ ] All experiments can be reproduced
- [ ] Random seeds are fixed
- [ ] Configuration files are complete
- [ ] README has clear instructions

---

## TIMELINE SUMMARY

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1 | Setup + Baseline | Working baseline VVC |
| 2 | Decoder-ROI | Reproduced paper results |
| 3-4 | Temporal Propagation | 80% detection reduction |
| 5-6 | Hierarchical ROI | BD-Rate ≤ -75% |
| 7-8 | RA/LDP Configs | All configs working |
| 9-10 | Evaluation | Complete results |
| 11-12 | Paper Writing | Q1 manuscript ready |

---

## CONTACT & SUPPORT

Nếu gặp vấn đề trong quá trình triển khai:
1. Check logs trong `results/logs/`
2. Review configuration trong `config/`
3. Run unit tests: `pytest tests/`
4. Check GitHub issues (if available)

Good luck với dự án! 🚀
