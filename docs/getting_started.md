# Getting Started

This guide will help you get up and running with the CBS Research Project quickly.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.8 or higher**
- **pip** (Python package manager)  
- **Git** (for cloning the repository)

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+
- **Memory**: Minimum 4GB RAM, recommended 8GB+
- **Storage**: At least 2GB free space for installation and results
- **Network**: For traffic generation and testing scenarios

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/cbs-research.git
cd cbs-research
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Installation

Run the test suite to ensure everything is working:

```bash
python -m pytest tests/ -v
```

If all tests pass, you're ready to start using the CBS tools!

## Quick Tour

### CBS Parameter Calculator

The heart of the project is the CBS calculator that computes optimal parameters for automotive network streams:

```python
from src.cbs_calculator import CBSCalculator, StreamConfig, TrafficType

# Initialize calculator for 1 Gbps link
calculator = CBSCalculator(link_speed_mbps=1000)

# Define a 4K video stream
front_camera = StreamConfig(
    name="Front_Camera_4K",
    traffic_type=TrafficType.VIDEO_4K, 
    bitrate_mbps=25.0,
    fps=60,
    resolution="3840x2160",
    priority=6,
    max_latency_ms=20.0,
    max_jitter_ms=3.0
)

# Calculate CBS parameters
params = calculator.calculate_cbs_params(front_camera)

print(f"Stream: {front_camera.name}")
print(f"idleSlope: {params.idle_slope:,} bps")
print(f"sendSlope: {params.send_slope:,} bps") 
print(f"hiCredit: {params.hi_credit:,} bits")
print(f"loCredit: {params.lo_credit:,} bits")
print(f"Reserved BW: {params.reserved_bandwidth_mbps:.1f} Mbps")
print(f"Efficiency: {params.efficiency_percent:.1f}%")
```

### Multi-Stream Scenarios

Calculate parameters for multiple streams with automatic optimization:

```python
from src.cbs_calculator import CBSCalculator, StreamConfig, TrafficType

calculator = CBSCalculator(link_speed_mbps=1000)

# Define multiple automotive streams
streams = [
    StreamConfig("Emergency_Control", TrafficType.SAFETY_CRITICAL, 2, 100, "N/A", 7, 5, 0.5),
    StreamConfig("Front_4K_Camera", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
    StreamConfig("Surround_HD_Left", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
    StreamConfig("LiDAR_Main", TrafficType.LIDAR, 100, 10, "N/A", 4, 40, 4),
    StreamConfig("V2X_Safety", TrafficType.V2X, 10, 10, "N/A", 2, 100, 10),
]

# Calculate optimized parameters
optimized_params = calculator.optimize_parameters(streams, target_utilization=75)

# Generate configuration file
calculator.generate_config_file(streams, "automotive_config.yaml")

# Generate detailed report
calculator.generate_performance_report(streams, "performance_report.md")
```

### Data Analysis and Visualization  

Analyze experimental results with interactive visualizations:

```python
from src.data_analyzer import CBSDataAnalyzer

# Load experimental data
analyzer = CBSDataAnalyzer('results/experiment_data.json')

# Generate comprehensive dashboard
analyzer.create_comprehensive_dashboard('analysis_results')

# Create specific visualizations
analyzer.plot_frame_loss_comparison('frame_loss.html')
analyzer.plot_latency_analysis('latency_analysis.html')
analyzer.plot_jitter_analysis('jitter_analysis.html')
```

### Traffic Generation

Generate realistic automotive network traffic for testing:

```bash
# Generate autonomous driving scenario traffic
python src/traffic_generator.py --scenario autonomous_driving --duration 60

# Generate traffic with specific background load
python src/traffic_generator.py --scenario highway_driving --duration 120 --background-load 500

# List available traffic profiles  
python src/traffic_generator.py --list-profiles
```

### Performance Benchmarking

Run comprehensive performance benchmarks:

```bash
# Run all benchmarks
python src/performance_benchmark.py --test all --iterations 5

# Run specific benchmark
python src/performance_benchmark.py --test scalability --iterations 3 --duration 60

# Create custom benchmark configuration
python src/performance_benchmark.py --create-template custom_benchmark.json
```

## Example Workflows

### 1. Automotive Network Design

```bash
# Step 1: Define your traffic streams (edit streams configuration)
# Step 2: Calculate CBS parameters
python src/cbs_calculator.py

# Step 3: Generate configuration for hardware
# (YAML files are created automatically)

# Step 4: Validate with traffic simulation  
python src/traffic_generator.py --scenario autonomous_driving --duration 300

# Step 5: Analyze performance
python src/data_analyzer.py --data results/experiment_data.json
```

### 2. Research and Development

```bash
# Run comprehensive performance analysis
python src/performance_benchmark.py --test all --output-dir research_results

# Generate research datasets
python src/traffic_generator.py --scenario all_traffic --duration 600 --stats-output traffic_stats.json

# Create publication-ready visualizations
python src/data_analyzer.py --data results/experiment_data.json --format both
```

### 3. Continuous Integration

```bash
# Run all tests
pytest tests/ -v --cov=src --cov-report=html

# Performance regression testing  
python src/performance_benchmark.py --test all --iterations 3 --duration 30

# Generate documentation
cd docs && sphinx-build -b html . _build/html
```

## Configuration

### Environment Variables

You can configure the tools using environment variables:

```bash
export CBS_DEFAULT_LINK_SPEED=1000  # Default link speed in Mbps
export CBS_OUTPUT_DIR=results       # Default output directory
export CBS_LOG_LEVEL=INFO          # Logging level
export CBS_ENABLE_VALIDATION=true  # Enable parameter validation
```

### Configuration Files

Create custom configuration files for repeated use:

**config/automotive_scenario.json**
```json
{
  "name": "Autonomous Vehicle Scenario",
  "description": "Complete autonomous driving network configuration",
  "link_speed_mbps": 1000,
  "streams": [
    {
      "name": "Emergency_Brake",
      "traffic_type": "safety_critical", 
      "bitrate_mbps": 2.0,
      "fps": 100,
      "resolution": "N/A",
      "priority": 7,
      "max_latency_ms": 5.0,
      "max_jitter_ms": 0.5
    }
  ]
}
```

Load and use configuration:

```python
from src.cbs_calculator import CBSCalculator

calculator = CBSCalculator()
calculator.load_config('config/automotive_scenario.json')
```

## Next Steps

Now that you have the basics working, explore these advanced topics:

- **[API Reference](api_reference.html)**: Detailed documentation of all classes and functions
- **[Tutorials](tutorials/index.html)**: Step-by-step guides for common tasks  
- **[Benchmarking](benchmarking.html)**: Performance testing and optimization
- **[Development](development/index.html)**: Contributing to the project

## Troubleshooting

### Common Issues

**Import errors when running scripts:**
```bash
# Make sure you're in the project root directory
cd /path/to/cbs-research
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

**Permission errors with network tools:**
```bash
# Some network tools require elevated privileges
sudo python src/traffic_generator.py --scenario basic_video
```

**Missing system dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install tcpdump iperf3 vlc

# macOS
brew install tcpdump iperf3 vlc

# Windows
# Install from official websites or use WSL
```

**Performance issues:**
```bash
# For better performance, install optimized numerical libraries
pip install numpy[mkl] scipy[mkl]
```

### Getting Help

If you encounter issues:

1. Check the [FAQ](faq.html) section
2. Search [existing issues](https://github.com/your-org/cbs-research/issues)
3. Create a new issue with detailed information
4. Join our [discussions](https://github.com/your-org/cbs-research/discussions)

## What's Next?

Continue with the [Basic Usage Tutorial](tutorials/basic_usage.html) for a more detailed walkthrough of the core functionality.