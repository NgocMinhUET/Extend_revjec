# Models Directory

This directory contains pre-trained models for object detection and tracking.

## 📥 Download Models

### YOLOv8 (Auto-download)
Models will be automatically downloaded when first used:

```python
from ultralytics import YOLO

# Auto-download on first use
model = YOLO('yolov8n.pt')  # Nano
model = YOLO('yolov8s.pt')  # Small
model = YOLO('yolov8m.pt')  # Medium
```

Or manually download:
```bash
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt
```

### JDE Tracker (Optional)
For tracking evaluation:
```bash
git clone https://github.com/Zhongdao/Towards-Realtime-MOT.git
# Download pre-trained weights from repository
```

## 📁 Expected Structure

```
models/
├── yolov8n.pt          # YOLOv8 Nano (6.3 MB)
├── yolov8s.pt          # YOLOv8 Small (21.5 MB)
├── yolov8m.pt          # YOLOv8 Medium (49.7 MB)
├── yolov8l.pt          # YOLOv8 Large (83.7 MB) - Optional
├── yolov8x.pt          # YOLOv8 Extra Large (130.5 MB) - Optional
└── jde_1088x608.pth    # JDE tracker - Optional
```

## 📊 Model Comparison

### YOLOv8 Variants

| Model | Size (MB) | Params (M) | Speed (ms) | mAP | Recommended Use |
|-------|-----------|------------|------------|-----|-----------------|
| YOLOv8n | 6.3 | 3.2 | 1.4 | 37.3 | Fast detection, real-time |
| YOLOv8s | 21.5 | 11.2 | 2.3 | 44.9 | **Default**, balanced |
| YOLOv8m | 49.7 | 25.9 | 4.0 | 50.2 | High accuracy |
| YOLOv8l | 83.7 | 43.7 | 5.8 | 52.9 | Best accuracy |
| YOLOv8x | 130.5 | 68.2 | 7.9 | 53.9 | Research only |

**Speed measured on NVIDIA RTX 3090

## 🎯 Usage

### Load Model

```python
from src.roi_detector import ROIDetector

# Initialize detector
config = {'roi_detection': {'model': 'yolov8s.pt'}}
detector = ROIDetector(config)

# Detect objects
bboxes = detector.detect(frame)
```

### Custom Model

```python
# Use your own trained model
detector = ROIDetector(config, model_path='models/custom_yolo.pt')
```

## ⚙️ Configuration

In `config/default_config.yaml`:

```yaml
roi_detection:
  enabled: true
  model: "yolov8s.pt"          # Model file
  confidence: 0.5               # Detection threshold
  iou_threshold: 0.45           # NMS threshold
  device: "cuda"                # cuda or cpu
  classes: [0, 2]               # 0=person, 2=car
```

## 🔧 Model Training (Optional)

### Fine-tune YOLOv8

```python
from ultralytics import YOLO

# Load pre-trained model
model = YOLO('yolov8s.pt')

# Train on custom data
model.train(
    data='data.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)
```

### Export Model

```python
# Export to ONNX for deployment
model.export(format='onnx')
```

## 💾 Storage Requirements

- **Minimum:** ~28 MB (yolov8n + yolov8s)
- **Recommended:** ~78 MB (yolov8n + yolov8s + yolov8m)
- **Full:** ~292 MB (all YOLOv8 variants)

## 🚀 Performance Optimization

### GPU Acceleration
```python
config = {
    'roi_detection': {
        'device': 'cuda',
        'batch_size': 8  # Process multiple frames
    }
}
```

### Half Precision
```python
# Use FP16 for faster inference
model.to('cuda').half()
```

### TensorRT (Advanced)
```python
# Export to TensorRT for maximum speed
model.export(format='engine', device=0)
```

## 📚 Model Details

### YOLOv8 Architecture
- Backbone: CSPDarknet
- Neck: PANet
- Head: Decoupled head
- Anchors: Anchor-free
- Loss: BCE + CIoU

### Supported Classes (COCO)
- 0: person
- 1: bicycle
- 2: car
- 3: motorcycle
- 5: bus
- 7: truck
- ... (80 classes total)

## ⚠️ Notes

1. **License:** Check Ultralytics license for commercial use
2. **Citation:** Cite YOLOv8 paper if used in publications
3. **Updates:** Models may be updated by Ultralytics
4. **Memory:** Larger models require more GPU memory

## 📖 References

- YOLOv8: https://github.com/ultralytics/ultralytics
- Paper: https://arxiv.org/abs/2305.09972 (if available)
- Docs: https://docs.ultralytics.com/

## 📞 Support

If you have issues with models:
1. Verify model files exist
2. Check CUDA/PyTorch compatibility
3. Try smaller model (yolov8n)
4. Check GPU memory
5. Review error logs
6. Open a GitHub issue
