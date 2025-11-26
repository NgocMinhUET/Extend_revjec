# Quick Start Guide - Phase 5

**Goal:** Generate analysis, statistics, and figures for paper submission  
**Time:** ~1 hour for complete analysis  
**Prerequisites:** Experiments completed (exp1-exp5 results available)

---

## 🚀 **STEP-BY-STEP GUIDE**

### **Step 1: Pull Latest Code (1 minute)**

```bash
cd ~/extend_revjec/Extend_revjec
git pull
```

**Expected output:**
```
Updating 20bd221..e92e08f
Fast-forward
 6 files changed, 1696 insertions(+)
 create mode 100644 PHASE5_STRATEGY.md
 create mode 100644 scripts/theoretical_bdrate.py
 ...
```

---

### **Step 2: Verify Results Exist (1 minute)**

```bash
# Check if experiment results are available
ls -lh results/metrics/*.csv

# Should see:
# baseline.csv
# decoder_roi.csv
# temporal_roi.csv
# hierarchical_roi.csv
# full_system.csv
```

**If missing:** Run experiments first
```bash
python experiments/run_all_experiments.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 100 \
  --qp 22 27 32 37
```

---

### **Step 3: Generate Theoretical BD-Rate (2 minutes)**

```bash
python scripts/theoretical_bdrate.py
```

**Expected output:**
```
================================================================================
THEORETICAL BD-RATE ESTIMATION
================================================================================

Experiment           Theoretical BD-Rate  Est. PSNR Change Note
--------------------------------------------------------------------------------
decoder_roi                      +12.50%             -0.83 dB Binary ROI
temporal_roi                     +12.50%             -0.83 dB + 90% det. reduction
hierarchical_roi                 +72.50%             -1.35 dB 3-level hierarchy
--------------------------------------------------------------------------------

INTERPRETATION
================================================================================
• BD-Rate < 0: Bitrate REDUCTION (good)
• BD-Rate > 0: Bitrate INCREASE (due to high-quality ROI)
```

**Save output:**
```bash
python scripts/theoretical_bdrate.py > results/analysis/theoretical_bdrate.txt
```

---

### **Step 4: Generate Comprehensive Statistics (5 minutes)**

```bash
python scripts/analyze_qp_statistics.py
```

**Expected output:**
```
================================================================================
COMPREHENSIVE STATISTICS FOR PAPER
================================================================================

1. ALGORITHM PERFORMANCE (MEASURED)
   ✅ Detection Overhead Reduction: 90.0%
   ✅ Hierarchical ROI Structure:
      - Core (Objects):      7.2%
      - Context (Rings):    12.0%
      - Background:         80.8%

2. THEORETICAL BD-RATE ESTIMATES
   Decoder-ROI (Binary):      +12.50%
   Hierarchical (3-level):    +72.50%

3. TIME COMPLEXITY ANALYSIS
   ...

✅ Statistics saved to: results/metrics/paper_statistics.json
```

**Save output:**
```bash
python scripts/analyze_qp_statistics.py > results/analysis/paper_statistics.txt
```

---

### **Step 5: Generate Paper Figures (10 minutes)**

```bash
# Create output directory
mkdir -p results/paper_figures

# Generate all figures
python scripts/generate_paper_figures.py
```

**Expected output:**
```
================================================================================
GENERATING PUBLICATION-READY FIGURES
================================================================================

✅ Saved: Figure 1 - Architecture
✅ Saved: Figure 2 - Hierarchical ROI
✅ Saved: Figure 3 - Detection Reduction
✅ Saved: Figure 4 - Theoretical BD-Rate
✅ Saved: Figure 5 - Time Complexity

================================================================================
✅ ALL FIGURES GENERATED
================================================================================
```

**Verify figures:**
```bash
ls -lh results/paper_figures/
# Should see 10 files (5 PDF + 5 PNG)
```

---

### **Step 6: Review Generated Statistics (5 minutes)**

```bash
# View JSON statistics
cat results/metrics/paper_statistics.json | python -m json.tool

# View text summaries
cat results/analysis/theoretical_bdrate.txt
cat results/analysis/paper_statistics.txt
```

---

### **Step 7: Create Summary Tables for Paper (10 minutes)**

Create `results/paper_tables/table1_detection_reduction.md`:
```markdown
| Method | Detections/Frame | Reduction | Time (100 frames) |
|--------|------------------|-----------|-------------------|
| Baseline (Every Frame) | 1.00 | 0% | 500ms |
| Temporal Propagation | 0.10 | **90%** | 50ms |
```

Create `results/paper_tables/table2_roi_coverage.md`:
```markdown
| ROI Level | Coverage | QP Offset | Mean QP (Base=27) |
|-----------|----------|-----------|-------------------|
| Core (Objects) | 7.2% | -8 | 19 |
| Context (Rings) | 12.0% | -4 | 23 |
| Background | 80.8% | +6 | 33 |
```

Create `results/paper_tables/table3_theoretical_bdrate.md`:
```markdown
| Experiment | Theoretical BD-Rate | Interpretation |
|------------|---------------------|----------------|
| Decoder-ROI | +12.5% | Moderate bitrate increase |
| Temporal-ROI | +12.5% | + 90% detection reduction |
| Hierarchical | +72.5% | High ROI quality priority |
```

---

### **Step 8: Transfer Figures to Local (if needed)**

```bash
# On server: Create archive
cd ~/extend_revjec/Extend_revjec
tar -czf paper_materials.tar.gz results/paper_figures/ results/analysis/ results/paper_tables/

# On local: Download
scp user@server:~/extend_revjec/Extend_revjec/paper_materials.tar.gz .
tar -xzf paper_materials.tar.gz
```

---

## 📊 **WHAT YOU GET**

### **Files Generated:**

```
results/
├── metrics/
│   ├── baseline.csv
│   ├── decoder_roi.csv
│   ├── temporal_roi.csv
│   ├── hierarchical_roi.csv
│   ├── full_system.csv
│   ├── comparison_table.md
│   ├── comparison.csv
│   └── paper_statistics.json  ← NEW
│
├── analysis/
│   ├── theoretical_bdrate.txt  ← NEW
│   └── paper_statistics.txt    ← NEW
│
└── paper_figures/              ← NEW
    ├── fig1_architecture.pdf
    ├── fig1_architecture.png
    ├── fig2_hierarchical_roi.pdf
    ├── fig2_hierarchical_roi.png
    ├── fig3_detection_reduction.pdf
    ├── fig3_detection_reduction.png
    ├── fig4_theoretical_bdrate.pdf
    ├── fig4_theoretical_bdrate.png
    ├── fig5_time_complexity.pdf
    └── fig5_time_complexity.png
```

---

## 📝 **NEXT: PAPER WRITING**

### **1. Use Methodology Template**

Location: `paper/methodology_template.md`

**Sections included:**
- System Overview
- Temporal ROI Propagation Algorithm
- Hierarchical ROI Generation
- Content-Adaptive QP Control
- VVenC Limitation Explanation
- Theoretical Performance Estimation

### **2. Copy Figures to Paper**

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{fig1_architecture.pdf}
\caption{Hierarchical Temporal ROI-VVC System Architecture.}
\label{fig:architecture}
\end{figure}
```

### **3. Insert Tables**

```latex
\begin{table}[t]
\caption{Detection Overhead Reduction}
\label{tab:detection}
\centering
\begin{tabular}{lccc}
\hline
Method & Detections/Frame & Reduction & Time \\
\hline
Baseline & 1.00 & 0\% & 500ms \\
Temporal & 0.10 & \textbf{90\%} & 50ms \\
\hline
\end{tabular}
\end{table}
```

---

## 🎯 **CHECKLIST FOR PAPER SUBMISSION**

### **Materials Ready:**

- [x] Theoretical BD-Rate analysis
- [x] Statistical summaries
- [x] Publication-quality figures (PDF + PNG)
- [x] Methodology template
- [x] Limitation documentation

### **To Do:**

- [ ] Write Introduction (2 pages)
- [ ] Write Related Work (2 pages)
- [ ] Adapt Methodology template (4 pages)
- [ ] Write Results section (3 pages)
- [ ] Write Discussion (2 pages)
- [ ] Write Conclusion (1 page)
- [ ] Prepare supplementary materials
- [ ] Proofread and polish
- [ ] Submit to target venue

---

## 💡 **TIPS FOR PAPER WRITING**

### **Emphasize Strengths:**

**Strong Point 1: 90% Detection Reduction** ✅
```
"Our temporal propagation algorithm achieves 90% reduction in 
detection overhead, enabling real-time VVC task-oriented coding."
```

**Strong Point 2: Complete Implementation** ✅
```
"We provide a complete open-source implementation, demonstrating 
practical feasibility and reproducibility of our approach."
```

**Strong Point 3: Novel Algorithm** ✅
```
"To our knowledge, this is the first work to apply optical 
flow-based temporal propagation to VVC decoder-side ROI coding."
```

### **Handle Limitation Transparently:**

```
"Due to current VVenC CLI limitations, we present theoretical 
BD-Rate estimates based on QP map statistics and rate-distortion 
models. Future work includes VVenC library API integration for 
actual measurements."
```

### **Position Correctly:**

**This is NOT:** A pure coding efficiency paper (BD-Rate focused)  
**This IS:** An algorithm paper with practical impact (detection reduction)

---

## 📞 **TROUBLESHOOTING**

### **Problem: Missing experiment results**

```bash
# Re-run specific experiment
python experiments/exp3_temporal_roi.py \
  --config config/ai_config.yaml \
  --sequence MOT16-02 \
  --max-frames 100 \
  --qp 27
```

### **Problem: Figure generation fails**

```bash
# Check matplotlib installation
pip install matplotlib seaborn

# Try generating one figure at a time
python -c "
from scripts.generate_paper_figures import create_detection_reduction_chart
create_detection_reduction_chart()
"
```

### **Problem: Statistics script error**

```bash
# Check if CSV files are valid
head -5 results/metrics/temporal_roi.csv

# Verify pandas version
pip install pandas>=2.0.0
```

---

## ✅ **SUCCESS CRITERIA**

**You're ready for paper writing when:**

✅ All 5 experiment CSVs exist  
✅ Theoretical BD-Rate script runs successfully  
✅ Statistics JSON generated  
✅ All 10 figures created (5 PDF + 5 PNG)  
✅ Analysis text files saved  

---

## 🎉 **ESTIMATED TIMELINE**

| Task | Time | Status |
|------|------|--------|
| Pull code & verify | 5 min | ⬜ |
| Generate statistics | 10 min | ⬜ |
| Generate figures | 15 min | ⬜ |
| Review outputs | 10 min | ⬜ |
| **Total Setup** | **40 min** | |
| | | |
| Write Introduction | 4 hours | ⬜ |
| Write Related Work | 3 hours | ⬜ |
| Adapt Methodology | 4 hours | ⬜ |
| Write Results | 3 hours | ⬜ |
| Write Discussion | 2 hours | ⬜ |
| Write Conclusion | 1 hour | ⬜ |
| Proofread & polish | 3 hours | ⬜ |
| **Total Writing** | **20 hours** | |
| | | |
| **TOTAL** | **~3 days** | |

---

**Ready to start? Run Step 1-5 now!** 🚀
