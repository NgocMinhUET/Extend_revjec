# Contributing to Hierarchical Temporal ROI-VVC

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- VVenC encoder
- CUDA-capable GPU (recommended)
- MOT datasets

### Setup
```bash
# Clone repository
git clone https://github.com/yourusername/Extend_revjec.git
cd Extend_revjec

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install VVenC
bash scripts/install_vvenc.sh  # Linux/Mac
scripts\install_vvenc.bat      # Windows

# Verify installation
python scripts/verify_installation.py
```

## 📝 How to Contribute

### Reporting Bugs
- Use GitHub Issues
- Describe the bug clearly
- Provide steps to reproduce
- Include system information
- Attach logs if possible

### Suggesting Enhancements
- Open a GitHub Issue
- Describe the enhancement
- Explain why it's useful
- Provide examples if possible

### Pull Requests
1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit your changes (`git commit -am 'Add new feature'`)
7. Push to the branch (`git push origin feature/your-feature`)
8. Open a Pull Request

## 📋 Coding Standards

### Python Style
- Follow PEP 8
- Use type hints
- Write docstrings (Google style)
- Keep functions focused and small
- Maximum line length: 100 characters

### Example
```python
def calculate_qp(roi_level: int, base_qp: int, alpha: float) -> int:
    """
    Calculate QP value for a given ROI level
    
    Args:
        roi_level: ROI level (0=background, 1=context, 2=core)
        base_qp: Base QP value
        alpha: Alpha adjustment factor
        
    Returns:
        Adjusted QP value
    """
    if roi_level == 2:
        return max(0, base_qp - int(alpha))
    elif roi_level == 1:
        return base_qp
    else:
        return min(51, base_qp + int(alpha))
```

### Documentation
- Update README.md for new features
- Add docstrings to all functions/classes
- Update configuration documentation
- Add examples if applicable

### Testing
- Write unit tests for new features
- Ensure existing tests pass
- Add integration tests if needed
- Test on multiple datasets

## 🔍 Code Review Process

1. All submissions require review
2. Maintainers will review PRs
3. Address feedback promptly
4. Once approved, PR will be merged

## 📊 Project Structure

```
Extend_revjec/
├── src/                    # Core modules
├── experiments/            # Experiment scripts
├── scripts/                # Utility scripts
├── config/                 # Configuration files
├── tests/                  # Unit tests
└── docs/                   # Documentation
```

## 🎯 Development Priorities

### High Priority
- Core modules implementation
- Experiment scripts
- Performance optimization
- Bug fixes

### Medium Priority
- Additional features
- Documentation improvements
- Code refactoring
- Test coverage

### Low Priority
- UI improvements
- Additional visualizations
- Optional features

## 📧 Contact

For questions or discussions:
- Open a GitHub Issue
- Email: [your-email@example.com]

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
