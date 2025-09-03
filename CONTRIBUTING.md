# Contributing to CBS TSN Research

First off, thank you for considering contributing to our CBS TSN research project! 🎉

This document provides guidelines and instructions for contributing to the IEEE 802.1Qav Credit-Based Shaper implementation on Microchip TSN switches.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Process](#development-process)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
- Git
- A GitHub account
- Basic knowledge of TSN and CBS concepts
- (Optional) Access to Microchip TSN hardware

### Setting Up Your Development Environment

1. **Fork the Repository**
   ```bash
   # Click the 'Fork' button on GitHub
   ```

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/research_paper.git
   cd research_paper
   ```

3. **Add Upstream Remote**
   ```bash
   git remote add upstream https://github.com/hwkim3330/research_paper.git
   ```

4. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

6. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**How to Submit a Good Bug Report:**

1. Use a clear and descriptive title
2. Describe the exact steps to reproduce the problem
3. Provide specific examples
4. Include system information:
   - OS and version
   - Python version
   - Hardware setup (if applicable)
5. Attach relevant logs or screenshots

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**How to Submit a Good Enhancement Suggestion:**

1. Use a clear and descriptive title
2. Provide a detailed description of the proposed enhancement
3. Explain why this enhancement would be useful
4. List any alternative solutions you've considered
5. Include mockups or examples if applicable

### Contributing Code

#### Areas Where We Need Help

- **CBS Algorithm Improvements**: Optimization and edge cases
- **Performance Testing**: New test scenarios and benchmarks
- **Documentation**: Tutorials, guides, and API documentation
- **Visualization**: New charts and dashboard features
- **Hardware Support**: Additional TSN switch models
- **Integration**: Support for more streaming platforms

#### First-Time Contributors

Look for issues labeled with:
- `good first issue` - Simple issues for beginners
- `help wanted` - Issues where we need community help
- `documentation` - Documentation improvements

### Contributing Research

- **Experimental Data**: Share your CBS performance measurements
- **Use Cases**: Document real-world applications
- **Theoretical Analysis**: Mathematical proofs and analysis
- **Comparative Studies**: CBS vs other shapers

## Development Process

### Branch Naming Convention

- `feature/` - New features (e.g., `feature/add-tas-support`)
- `bugfix/` - Bug fixes (e.g., `bugfix/credit-calculation`)
- `docs/` - Documentation (e.g., `docs/update-readme`)
- `test/` - Testing (e.g., `test/add-benchmark`)

### Commit Message Format

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Testing
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes

**Example:**
```
feat(calculator): add support for multiple traffic classes

- Implement multi-class CBS calculation
- Add validation for class priorities
- Update tests for new functionality

Closes #123
```

## Style Guidelines

### Python Code Style

We use [PEP 8](https://www.python.org/dev/peps/pep-0008/) with the following tools:

- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking
- **isort** for import sorting

Run all checks:
```bash
make lint  # Or manually:
black src/ tests/
flake8 src/ tests/
mypy src/
isort src/ tests/
```

### Code Guidelines

```python
# Good example
def calculate_idle_slope(
    bandwidth_mbps: float,
    link_speed_bps: int = 1_000_000_000
) -> int:
    """
    Calculate CBS idle slope parameter.
    
    Args:
        bandwidth_mbps: Required bandwidth in Mbps
        link_speed_bps: Link speed in bits per second
        
    Returns:
        Idle slope value in bits per second
        
    Raises:
        ValueError: If bandwidth exceeds link speed
    """
    if bandwidth_mbps * 1_000_000 > link_speed_bps:
        raise ValueError("Bandwidth exceeds link speed")
    
    return int(bandwidth_mbps * 1_000_000)
```

### Documentation Style

- Use Google-style docstrings
- Include type hints
- Provide examples in docstrings
- Keep line length under 88 characters

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_cbs_calculator.py

# Run with verbose output
pytest tests/ -v
```

### Writing Tests

```python
# tests/test_example.py
import pytest
from src.cbs_calculator import CBSCalculator

class TestCBSCalculator:
    @pytest.fixture
    def calculator(self):
        return CBSCalculator(link_speed=1_000_000_000)
    
    def test_idle_slope_calculation(self, calculator):
        params = calculator.calculate_params(
            bandwidth_mbps=100,
            max_frame_size=1522
        )
        assert params['idle_slope'] == 100_000_000
        assert params['send_slope'] == -900_000_000
```

### Test Coverage Requirements

- Minimum 80% code coverage for new features
- 100% coverage for critical algorithms
- Include edge cases and error conditions

## Documentation

### Types of Documentation

1. **Code Documentation**: Docstrings and comments
2. **User Documentation**: Guides and tutorials in `docs/`
3. **API Documentation**: Generated from docstrings
4. **Research Documentation**: Papers and technical reports

### Building Documentation

```bash
cd docs
make html  # Build HTML documentation
make latexpdf  # Build PDF documentation
```

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Keep documentation up-to-date with code changes

## Pull Request Process

### Before Submitting

1. **Update Your Fork**
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

4. **Run Tests**
   ```bash
   pytest tests/
   make lint
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

### Submitting Pull Request

1. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature
   ```

2. **Create Pull Request**
   - Go to GitHub and click "New Pull Request"
   - Select your branch
   - Fill out the PR template

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Updated documentation

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] No new warnings
```

### Review Process

1. Automated checks run (CI/CD)
2. Code review by maintainers
3. Address feedback
4. Approval and merge

## Community

### Getting Help

- **GitHub Issues**: For bugs and features
- **Discussions**: For questions and ideas
- **Email**: research@example.com

### Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Research papers (for significant contributions)
- Release notes

### Becoming a Maintainer

Active contributors may be invited to become maintainers based on:
- Quality of contributions
- Consistency of participation
- Understanding of the project
- Community involvement

## Additional Resources

- [CBS Theory Guide](docs/cbs_theory.md)
- [Hardware Setup Guide](docs/hardware_setup.md)
- [API Reference](https://hwkim3330.github.io/research_paper/api)
- [IEEE 802.1Qav Standard](https://www.ieee802.org/1/pages/802.1av.html)
- [Microchip TSN Resources](https://www.microchip.com/design-centers/ethernet/tsn)

## Questions?

Feel free to open an issue or contact the maintainers if you have any questions!

---

Thank you for contributing! 🚀