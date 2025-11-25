# Experiment 2 Testing Checklist
**File:** `experiments/exp2_decoder_roi.py`  
**Purpose:** Verify Decoder-ROI implementation works correctly

---

## 🔍 PRE-FLIGHT CHECK

### Dependencies
- [x] `src/roi_detector.py` - YOLOv8 detection
- [x] `src/vvc_encoder.py` - VVenC with QP map support
- [x] `src/utils.py` - Configuration loading
- [x] YOLOv8 model downloaded (yolov8n.pt)
- [x] MOT16 dataset available
- [x] VVenC encoder working

### Configuration
- [x] `config/ai_config.yaml` - All-Intra configuration
- [x] `config/default_config.yaml` - Base configuration with dataset paths
- [x] CTU size defined (default: 128)
- [x] ROI detection parameters set

---

## 🧪 TEST PLAN

### Test 1: Quick Smoke Test (5 minutes)
**Purpose:** Verify basic functionality

```bash
cd ~/extend_revjec/Extend_revjec
python experiments/exp2_decoder_roi.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 10 \
  --qp 27 \
  --debug
```

**Expected Output:**
- [ ] ROI detector initialized successfully
- [ ] Detections found in frames
- [ ] QP map generated (should show CTU counts)
- [ ] Encoding completed
- [ ] Results saved to CSV
- [ ] No errors or crashes

**Check Logs:**
```bash
tail -50 results/logs/decoder_roi/decoder_roi.log
```

**Look for:**
- "ROI Detector initialized: yolov8n"
- "Detecting ROI in all frames..."
- "QP Map statistics: Total CTUs: XXX, ROI CTUs: YYY"
- "Encoded: XX.XX kbps, XX.XX dB"

---

### Test 2: QP Map Visualization (10 minutes)
**Purpose:** Verify QP map generation and visualization

```bash
python experiments/exp2_decoder_roi.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 50 \
  --qp 27 \
  --save-qp-maps \
  --debug
```

**Check Files:**
```bash
# QP map visualization should be created
ls -lh results/visualizations/qp_maps/

# Should see something like: MOT16-02_qp27_frame0.jpg
```

**Verify QP Map:**
- [ ] File created in `results/visualizations/qp_maps/`
- [ ] Image shows colored overlay on frame
- [ ] ROI regions (objects) have different color than background
- [ ] Warm colors (red/yellow) = lower QP (ROI)
- [ ] Cool colors (blue/green) = higher QP (background)

**Visual Inspection:**
```bash
# View the QP map (if X11 forwarding or copy to local)
# Warmer colors should be around detected objects
```

---

### Test 3: Compare with Baseline (15 minutes)
**Purpose:** Verify bitrate savings and PSNR trade-off

**Step 1: Run both experiments**
```bash
# Baseline
python experiments/exp1_baseline.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 50 \
  --qp 27

# Decoder-ROI
python experiments/exp2_decoder_roi.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 50 \
  --qp 27 \
  --delta-qp-roi 5
```

**Step 2: Check results**
```bash
# View baseline results
cat results/metrics/baseline.csv

# View decoder-ROI results
cat results/metrics/decoder_roi.csv
```

**Step 3: Compare metrics**
```python
# Quick comparison (Python)
import pandas as pd

baseline = pd.read_csv('results/metrics/baseline.csv')
decoder_roi = pd.read_csv('results/metrics/decoder_roi.csv')

# Filter same sequence and QP
b = baseline[(baseline['sequence']=='MOT16-02') & (baseline['qp']==27)]
d = decoder_roi[(decoder_roi['sequence']=='MOT16-02') & (decoder_roi['qp']==27)]

bitrate_savings = (1 - d['bitrate'].values[0]/b['bitrate'].values[0]) * 100
psnr_diff = d['psnr_y'].values[0] - b['psnr_y'].values[0]

print(f"Bitrate savings: {bitrate_savings:.1f}%")
print(f"PSNR difference: {psnr_diff:.2f} dB")
print(f"ROI percentage: {d['roi_percentage'].values[0]:.1f}%")
```

**Expected Results (from paper):**
- [ ] Bitrate savings: 15-25%
- [ ] PSNR difference: -1.0 to 0.0 dB (slight degradation acceptable)
- [ ] ROI percentage: 5-20% (depends on sequence)

---

### Test 4: Multiple QP Values (20 minutes)
**Purpose:** Verify consistency across different QP values

```bash
python experiments/exp2_decoder_roi.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 50 \
  --qp 22 27 32 37 \
  --delta-qp-roi 5
```

**Check Results:**
```bash
cat results/metrics/decoder_roi.csv
```

**Verify:**
- [ ] 4 rows created (one per QP)
- [ ] Bitrate decreases as QP increases
- [ ] PSNR decreases as QP increases
- [ ] ROI percentage consistent across QPs
- [ ] All encodings completed successfully

---

### Test 5: Different Delta QP (Optional)
**Purpose:** Test different QP offsets for ROI

```bash
# More aggressive (larger quality difference)
python experiments/exp2_decoder_roi.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 50 \
  --qp 27 \
  --delta-qp-roi 8

# Less aggressive
python experiments/exp2_decoder_roi.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 50 \
  --qp 27 \
  --delta-qp-roi 3
```

**Expected:**
- [ ] Larger delta → more bitrate savings
- [ ] Larger delta → potentially more PSNR loss
- [ ] Results make sense

---

## 🐛 TROUBLESHOOTING

### Issue 1: ROI Detector Fails
**Symptoms:**
```
ERROR - Failed to load model: ...
```

**Solutions:**
- [ ] Check YOLO model exists: `ls -lh models/yolov8n.pt`
- [ ] Check CUDA availability if using GPU
- [ ] Try CPU mode: Edit config to set `device: 'cpu'`

### Issue 2: No Detections
**Symptoms:**
```
QP Map statistics: Total CTUs: XXX, ROI CTUs: 0 (0.0%)
```

**Solutions:**
- [ ] Check confidence threshold (may be too high)
- [ ] View first frame: Check if objects visible
- [ ] Lower confidence in config: `confidence_threshold: 0.3`
- [ ] Check YOLO classes (should detect person, car, etc.)

### Issue 3: QP Map Encoding Fails
**Symptoms:**
```
ERROR - Encoding failed: ...
```

**Solutions:**
- [ ] Check VVenC supports --qpmap option
- [ ] Verify QP map file format
- [ ] Check CTU size matches encoder expectations
- [ ] Try baseline encoding first to verify VVenC works

### Issue 4: Results Don't Match Expectations
**Symptoms:**
- Bitrate savings < 10% or > 40%
- PSNR difference > 2 dB

**Check:**
- [ ] ROI percentage (should be 5-20%)
- [ ] QP map visualization (ROIs in right places?)
- [ ] Delta QP value (should be 3-8)
- [ ] Sequence content (some sequences have more/less objects)

---

## ✅ SUCCESS CRITERIA

### Must Have
- [x] Code runs without errors
- [ ] ROI detection produces bounding boxes
- [ ] QP map generated with ROI/background regions
- [ ] Encoding completes successfully
- [ ] Results saved to CSV
- [ ] Bitrate < baseline (some savings)

### Should Have
- [ ] Bitrate savings 10-30%
- [ ] PSNR degradation < 2 dB
- [ ] QP map visualization shows reasonable ROIs
- [ ] ROI percentage 5-25%
- [ ] Consistent results across QP values

### Nice to Have
- [ ] Bitrate savings 15-25% (paper target)
- [ ] PSNR degradation < 1 dB (paper target)
- [ ] Clean debug logs
- [ ] Visualizations look good

---

## 📊 REPORTING

### After Testing, Document:

1. **Test Results Summary**
```markdown
## Exp2 Test Results - MOT16-02 (50 frames)

| QP | Baseline (kbps) | Decoder-ROI (kbps) | Savings (%) | PSNR Diff (dB) |
|----|-----------------|-------------------|-------------|----------------|
| 22 | XXX.XX          | YYY.YY            | ZZ.Z%       | -0.XX          |
| 27 | XXX.XX          | YYY.YY            | ZZ.Z%       | -0.XX          |
| 32 | XXX.XX          | YYY.YY            | ZZ.Z%       | -0.XX          |
| 37 | XXX.XX          | YYY.YY            | ZZ.Z%       | -0.XX          |

Average ROI percentage: XX.X%
Detection overhead: X.X seconds
```

2. **Issues Encountered**
- List any errors or unexpected behavior
- Solutions applied
- Remaining concerns

3. **Visual Evidence**
- QP map screenshots
- Log file snippets
- CSV file contents

---

## 🚀 NEXT STEPS AFTER SUCCESSFUL TESTING

### If Tests Pass (90%+ success criteria met):
1. ✅ Mark Phase 1 as COMPLETE
2. 📝 Update project documentation
3. 🎯 Plan Phase 2: Temporal ROI Propagation
4. 📊 Prepare baseline comparison report

### If Tests Need Fixes:
1. 🐛 Debug specific issues
2. 🔧 Apply fixes
3. 🔄 Re-test
4. 📝 Document changes

### If Tests Show Unexpected Results:
1. 🔍 Analyze why (detection, QP map, encoding)
2. 🧪 Run additional diagnostic tests
3. 📊 Compare with paper methodology
4. 💬 Discuss findings

---

## 📞 GETTING HELP

If stuck, check:
1. **Debug logs:** `results/logs/decoder_roi/decoder_roi.log`
2. **This checklist:** Re-read troubleshooting section
3. **Paper:** Original Decoder-ROI paper methodology
4. **Code comments:** Check inline documentation in exp2_decoder_roi.py

---

**Ready to test? Start with Test 1!** 🚀
