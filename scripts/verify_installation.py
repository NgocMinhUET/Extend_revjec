"""
Verify Installation Script
Checks if all dependencies are properly installed
"""

import sys
import subprocess
import importlib
from pathlib import Path


def print_header(text):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def check_python_version():
    """Check Python version"""
    print("Checking Python version...")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ✗ Python 3.8+ required")
        return False
    else:
        print("  ✓ Python version OK")
        return True


def check_python_packages():
    """Check Python packages"""
    print("\nChecking Python packages...")
    
    required_packages = {
        'numpy': 'numpy',
        'opencv-python': 'cv2',
        'torch': 'torch',
        'torchvision': 'torchvision',
        'ultralytics': 'ultralytics',
        'scipy': 'scipy',
        'matplotlib': 'matplotlib',
        'pandas': 'pandas',
        'yaml': 'yaml',
        'tqdm': 'tqdm',
    }
    
    all_ok = True
    
    for package_name, import_name in required_packages.items():
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"  ✓ {package_name}: {version}")
        except ImportError:
            print(f"  ✗ {package_name}: NOT INSTALLED")
            all_ok = False
    
    return all_ok


def check_cuda():
    """Check CUDA availability"""
    print("\nChecking CUDA...")
    
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  ✓ CUDA available")
            print(f"    Version: {torch.version.cuda}")
            print(f"    Devices: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"      [{i}] {torch.cuda.get_device_name(i)}")
            return True
        else:
            print("  ⚠ CUDA not available (will use CPU)")
            return True  # Not critical
    except Exception as e:
        print(f"  ✗ Error checking CUDA: {e}")
        return False


def check_vvenc():
    """Check VVenC installation"""
    print("\nChecking VVenC...")
    
    executables = ['vvencapp', 'vvencapp.exe']
    
    for exe in executables:
        try:
            result = subprocess.run(
                [exe, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
                version = version_match.group(1) if version_match else 'unknown'
                
                print(f"  ✓ VVenC found: {exe}")
                print(f"    Version: {version}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    print("  ✗ VVenC not found")
    print("    Install with:")
    print("      Linux/Mac: bash scripts/install_vvenc.sh")
    print("      Windows:   scripts\\install_vvenc.bat")
    return False


def check_yolo_models():
    """Check YOLO models"""
    print("\nChecking YOLO models...")
    
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)
    
    required_models = ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt']
    
    all_ok = True
    for model_name in required_models:
        model_path = models_dir / model_name
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            print(f"  ✓ {model_name}: {size_mb:.1f} MB")
        else:
            print(f"  ✗ {model_name}: NOT FOUND")
            all_ok = False
    
    if not all_ok:
        print("\n  Download with:")
        print("    python scripts/setup_project.py")
    
    return all_ok


def check_datasets():
    """Check datasets"""
    print("\nChecking datasets...")
    
    data_dir = Path('data')
    datasets = ['MOT16', 'MOT17', 'MOT20']
    
    found_any = False
    for dataset in datasets:
        dataset_path = data_dir / dataset
        if dataset_path.exists():
            # Check if train directory exists
            train_path = dataset_path / 'train'
            if train_path.exists():
                n_sequences = len(list(train_path.glob('MOT*')))
                print(f"  ✓ {dataset}: {n_sequences} sequences")
                found_any = True
            else:
                print(f"  ⚠ {dataset}: exists but no train data")
        else:
            print(f"  ✗ {dataset}: NOT FOUND")
    
    if not found_any:
        print("\n  Download from:")
        print("    https://motchallenge.net/data/MOT16.zip")
        print("    https://motchallenge.net/data/MOT17.zip")
    
    return found_any


def check_project_structure():
    """Check project structure"""
    print("\nChecking project structure...")
    
    required_dirs = [
        'src',
        'config',
        'experiments',
        'scripts',
        'models',
        'data',
        'results',
    ]
    
    all_ok = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ NOT FOUND")
            all_ok = False
    
    return all_ok


def check_config_files():
    """Check configuration files"""
    print("\nChecking configuration files...")
    
    config_files = [
        'config/default_config.yaml',
        'config/ai_config.yaml',
        'config/ra_config.yaml',
        'config/ldp_config.yaml',
    ]
    
    all_ok = True
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            print(f"  ✓ {config_file}")
        else:
            print(f"  ✗ {config_file} NOT FOUND")
            all_ok = False
    
    return all_ok


def test_yolo_detection():
    """Test YOLO detection"""
    print("\nTesting YOLO detection...")
    
    try:
        from ultralytics import YOLO
        import numpy as np
        
        # Create dummy image
        dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        # Load model
        model = YOLO('yolov8n.pt')
        
        # Run detection
        results = model(dummy_image, verbose=False)
        
        print("  ✓ YOLO detection working")
        return True
        
    except Exception as e:
        print(f"  ✗ YOLO detection failed: {e}")
        return False


def main():
    """Main verification function"""
    print_header("INSTALLATION VERIFICATION")
    
    results = {}
    
    # Run checks
    results['python_version'] = check_python_version()
    results['python_packages'] = check_python_packages()
    results['cuda'] = check_cuda()
    results['vvenc'] = check_vvenc()
    results['yolo_models'] = check_yolo_models()
    results['datasets'] = check_datasets()
    results['project_structure'] = check_project_structure()
    results['config_files'] = check_config_files()
    results['yolo_test'] = test_yolo_detection()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    critical_checks = [
        'python_version',
        'python_packages',
        'vvenc',
        'project_structure',
        'config_files',
    ]
    
    optional_checks = [
        'cuda',
        'yolo_models',
        'datasets',
        'yolo_test',
    ]
    
    print("Critical Components:")
    critical_ok = True
    for check in critical_checks:
        status = "✓" if results[check] else "✗"
        print(f"  {status} {check.replace('_', ' ').title()}")
        if not results[check]:
            critical_ok = False
    
    print("\nOptional Components:")
    for check in optional_checks:
        status = "✓" if results[check] else "⚠"
        print(f"  {status} {check.replace('_', ' ').title()}")
    
    print("\n" + "="*60)
    
    if critical_ok:
        print("✓ All critical components installed!")
        print("\nYou can now:")
        print("  1. Download datasets (if not done)")
        print("  2. Run baseline experiment:")
        print("     python experiments/exp1_baseline.py")
        return 0
    else:
        print("✗ Some critical components missing!")
        print("\nPlease:")
        print("  1. Install missing packages: pip install -r requirements.txt")
        print("  2. Install VVenC: bash scripts/install_vvenc.sh")
        print("  3. Run this script again")
        return 1


if __name__ == '__main__':
    sys.exit(main())
