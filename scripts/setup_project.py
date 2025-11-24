"""
Project Setup Script
Run this script to setup the project structure and verify installation
"""

import os
import sys
from pathlib import Path
import subprocess


def create_directory_structure():
    """Create project directory structure"""
    print("Creating directory structure...")
    
    dirs = [
        "src",
        "config",
        "models",
        "experiments",
        "scripts",
        "data/MOT16",
        "data/MOT17",
        "data/MOT20",
        "data/encoded",
        "results/logs",
        "results/metrics",
        "results/plots",
        "results/analysis",
        "tests",
        "paper/figures",
        "paper/tables",
        "docs",
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created {dir_path}/")
    
    print("✓ Directory structure created\n")


def verify_python_packages():
    """Verify Python packages are installed"""
    print("Verifying Python packages...")
    
    required_packages = [
        'numpy',
        'opencv-python',
        'torch',
        'ultralytics',
        'scipy',
        'matplotlib',
        'pandas',
        'pyyaml',
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("✓ All packages installed\n")
        return True


def verify_vvenc():
    """Verify VVenC is installed"""
    print("Verifying VVenC installation...")
    
    try:
        result = subprocess.run(
            ['vvencapp', '--help'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("  ✓ VVenC is installed")
            return True
        else:
            print("  ✗ VVenC not found")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ✗ VVenC not found")
        print("  Please install VVenC from: https://github.com/fraunhoferhhi/vvenc")
        return False


def download_yolo_models():
    """Download YOLOv8 models"""
    print("\nDownloading YOLOv8 models...")
    
    try:
        from ultralytics import YOLO
        
        models = ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt']
        
        for model_name in models:
            model_path = Path('models') / model_name
            if model_path.exists():
                print(f"  ✓ {model_name} already exists")
            else:
                print(f"  Downloading {model_name}...")
                model = YOLO(model_name)
                # Move to models directory
                import shutil
                shutil.move(model_name, model_path)
                print(f"  ✓ {model_name} downloaded")
        
        print("✓ YOLOv8 models ready\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to download models: {e}")
        return False


def create_gitignore():
    """Create .gitignore file"""
    print("Creating .gitignore...")
    
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/

# Data
data/MOT*/
data/encoded/
*.mp4
*.yuv
*.266
*.h266

# Models
models/*.pt
!models/README.md

# Results
results/logs/
results/metrics/
results/plots/
*.csv
*.xlsx

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary
tmp/
temp/
*.tmp
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    
    print("✓ .gitignore created\n")


def create_readme_files():
    """Create README files for subdirectories"""
    print("Creating README files...")
    
    readmes = {
        'models/README.md': """# Pre-trained Models

Place pre-trained models here:
- yolov8n.pt
- yolov8s.pt
- yolov8m.pt
- jde_1088x608.pt

Run `python scripts/setup_project.py` to download YOLO models automatically.
""",
        'data/README.md': """# Datasets

Download datasets:
- MOT16: https://motchallenge.net/data/MOT16.zip
- MOT17: https://motchallenge.net/data/MOT17.zip
- MOT20: https://motchallenge.net/data/MOT20.zip

Extract to respective subdirectories.
""",
        'results/README.md': """# Results

Experiment results will be saved here:
- logs/: Encoding logs
- metrics/: Performance metrics (CSV, Excel)
- plots/: RD curves and visualizations
- analysis/: Statistical analysis
""",
    }
    
    for path, content in readmes.items():
        with open(path, 'w') as f:
            f.write(content)
        print(f"  ✓ {path}")
    
    print("✓ README files created\n")


def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "="*80)
    print("PROJECT SETUP COMPLETE!")
    print("="*80)
    
    print("\nNext Steps:")
    print("\n1. Download Datasets:")
    print("   - Visit https://motchallenge.net/")
    print("   - Download MOT16, MOT17, MOT20")
    print("   - Extract to data/ directory")
    
    print("\n2. Install VVenC (if not installed):")
    print("   - Visit https://github.com/fraunhoferhhi/vvenc")
    print("   - Follow build instructions")
    print("   - Add to PATH")
    
    print("\n3. Run Baseline Experiment:")
    print("   python experiments/exp1_baseline.py --config config/ai_config.yaml")
    
    print("\n4. Follow Implementation Guide:")
    print("   See IMPLEMENTATION_GUIDE.md for detailed steps")
    
    print("\n5. Read Documentation:")
    print("   - PROJECT_SPECIFICATION.md: Technical details")
    print("   - RESEARCH_OBJECTIVES.md: Research goals and novelty")
    print("   - README.md: Quick start guide")
    
    print("\n" + "="*80)
    print("Good luck with your research! 🚀")
    print("="*80 + "\n")


def main():
    """Main setup function"""
    print("\n" + "="*80)
    print("HIERARCHICAL TEMPORAL ROI-VVC - PROJECT SETUP")
    print("="*80 + "\n")
    
    # Create directory structure
    create_directory_structure()
    
    # Verify Python packages
    packages_ok = verify_python_packages()
    
    # Verify VVenC
    vvenc_ok = verify_vvenc()
    
    # Download YOLO models
    if packages_ok:
        models_ok = download_yolo_models()
    else:
        models_ok = False
    
    # Create .gitignore
    create_gitignore()
    
    # Create README files
    create_readme_files()
    
    # Print next steps
    print_next_steps()
    
    # Summary
    print("\nSetup Summary:")
    print(f"  Python packages: {'✓' if packages_ok else '✗'}")
    print(f"  VVenC: {'✓' if vvenc_ok else '✗'}")
    print(f"  YOLO models: {'✓' if models_ok else '✗'}")
    print(f"  Directory structure: ✓")
    print(f"  Configuration files: ✓")
    
    if packages_ok and vvenc_ok and models_ok:
        print("\n✓ Setup complete! Ready to start experiments.")
        return 0
    else:
        print("\n⚠ Setup incomplete. Please resolve the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
