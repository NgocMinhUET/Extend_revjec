# GitHub Setup Guide

Hướng dẫn đẩy dự án lên GitHub và setup trên server.

## 📦 Chuẩn bị trước khi Push

### 1. Kiểm tra Files quan trọng
- [x] .gitignore - Đã tạo
- [x] LICENSE - Đã tạo
- [x] README.md - Đã tạo
- [x] requirements.txt - Đã tạo
- [x] All documentation files
- [x] All source code files

### 2. Tạo các thư mục cần thiết

```bash
# Tạo thư mục (Git không track empty folders)
mkdir -p data models results/{logs,metrics,plots,analysis} experiments tests
```

### 3. Xóa files không cần thiết

```bash
# Xóa cache và temp files
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -delete
find . -type f -name ".DS_Store" -delete
```

---

## 🚀 Push lên GitHub

### Bước 1: Initialize Git (nếu chưa có)

```bash
cd d:\NCS\propose\Extend_revjec

# Initialize Git
git init

# Add remote
git remote add origin https://github.com/yourusername/Extend_revjec.git
```

### Bước 2: Add và Commit

```bash
# Check status
git status

# Add all files
git add .

# Commit
git commit -m "Initial commit: Hierarchical Temporal ROI-VVC framework

- Complete documentation (8 MD files)
- VVenC integration (encoder wrapper + installation scripts)
- Core modules (GOP manager, ROI detector, utilities)
- Configuration files (AI/RA/LDP)
- Project structure and README files
"
```

### Bước 3: Push

```bash
# Push to main branch
git push -u origin main

# Or master
git push -u origin master
```

---

## 🖥️ Setup trên Server

### Bước 1: Clone Repository

```bash
# SSH to server
ssh user@your-server.com

# Clone repository
git clone https://github.com/yourusername/Extend_revjec.git
cd Extend_revjec
```

### Bước 2: Setup Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Bước 3: Install VVenC

```bash
# Linux/Mac
bash scripts/install_vvenc.sh

# Add to PATH
export PATH=$PATH:$HOME/vvenc/build/bin/release-static

# Add to ~/.bashrc for permanent
echo 'export PATH=$PATH:$HOME/vvenc/build/bin/release-static' >> ~/.bashrc
```

### Bước 4: Download Datasets

```bash
# Create data directory
mkdir -p data

# Download MOT16
cd data
wget https://motchallenge.net/data/MOT16.zip
unzip MOT16.zip
cd ..
```

### Bước 5: Download Models

```bash
# Models will auto-download on first use
# Or manually:
mkdir -p models
cd models
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt
cd ..
```

### Bước 6: Verify Installation

```bash
python scripts/verify_installation.py
```

Expected output:
```
✓ Python version OK
✓ All packages installed
✓ VVenC found
✓ YOLO models downloaded
✓ All checks passed!
```

---

## 📋 Git Workflow cho Development

### Pull latest changes

```bash
git pull origin main
```

### Create feature branch

```bash
git checkout -b feature/temporal-propagation
# Make changes
git add .
git commit -m "Implement temporal propagation"
git push origin feature/temporal-propagation
```

### Merge back to main

```bash
git checkout main
git merge feature/temporal-propagation
git push origin main
```

---

## 🔐 Security Notes

### Không commit những files này:

- ✅ Đã có .gitignore
- Datasets (data/*.zip)
- Model weights (models/*.pt)
- Results (results/*)
- Virtual environment (venv/)
- API keys, passwords
- Large binary files

### Kiểm tra trước khi push:

```bash
# Check what will be committed
git status

# Check .gitignore working
git check-ignore data/MOT16.zip
# Should show: data/MOT16.zip (if working)
```

---

## 📊 GitHub Repository Settings

### 1. Repository Description
```
Hierarchical Temporal ROI-based Versatile Video Coding for Multi-Object Tracking - Q1 Journal Research Project
```

### 2. Topics/Tags
```
video-coding, vvc, h266, object-detection, multi-object-tracking, 
yolo, deep-learning, computer-vision, roi-encoding, pytorch
```

### 3. Branch Protection (Optional)
- Protect main branch
- Require pull request reviews
- Require status checks

### 4. GitHub Actions (Optional - cho CI/CD)
Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/
```

---

## 🔄 Update workflow trên Server

### Kéo code mới nhất:

```bash
cd ~/Extend_revjec
git pull origin main

# Restart services if needed
# Activate venv if needed
source venv/bin/activate

# Update dependencies if changed
pip install -r requirements.txt
```

### Auto-update script (Optional):

Create `update.sh`:
```bash
#!/bin/bash
cd ~/Extend_revjec
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python scripts/verify_installation.py
```

Make executable:
```bash
chmod +x update.sh
```

---

## ✅ Checklist trước khi Push

- [ ] Đã tạo .gitignore
- [ ] Đã tạo LICENSE
- [ ] Đã tạo README.md (informative)
- [ ] Đã test locally
- [ ] Đã xóa sensitive data
- [ ] Đã commit với clear message
- [ ] Đã check git status
- [ ] Repository description đã set
- [ ] Topics/tags đã thêm

---

## 📞 Troubleshooting

### Issue: Large file error
```bash
# Remove from Git history
git filter-branch --tree-filter 'rm -f large_file.bin' HEAD
```

### Issue: Wrong remote URL
```bash
# Check current remote
git remote -v

# Change remote URL
git remote set-url origin https://github.com/newuser/newrepo.git
```

### Issue: Permission denied
```bash
# Use HTTPS instead of SSH
git remote set-url origin https://github.com/user/repo.git

# Or setup SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub
# Add to GitHub Settings > SSH Keys
```

---

**Dự án đã sẵn sàng để push lên GitHub và deploy trên server!** 🚀
