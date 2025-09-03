# Basic Usage Tutorial

This tutorial will walk you through the basic usage of the CBS Research Project tools. You'll learn how to calculate CBS parameters, analyze performance data, and generate traffic for testing.

## Prerequisites

Make sure you have completed the [Getting Started](../getting_started.html) guide and have the project installed and working.

## Tutorial Overview

In this tutorial, we'll:

1. Calculate CBS parameters for a single video stream
2. Optimize parameters for multiple streams
3. Generate realistic automotive traffic
4. Analyze experimental results
5. Create performance reports

## Part 1: Single Stream CBS Calculation

Let's start with the most basic use case - calculating CBS parameters for a single video stream.

### Step 1: Import Required Modules

```python
from src.cbs_calculator import CBSCalculator, StreamConfig, TrafficType
import json
```

### Step 2: Create a CBS Calculator

```python
# Create calculator for 1 Gbps Ethernet link
calculator = CBSCalculator(link_speed_mbps=1000)

print(f"Calculator initialized for {calculator.link_speed_mbps} Mbps link")
print(f"Link speed: {calculator.link_speed_bps:,} bps")
```

### Step 3: Define a Video Stream

```python
# Define a 4K front camera stream for autonomous vehicle
front_camera = StreamConfig(
    name="Front_Camera_4K",
    traffic_type=TrafficType.VIDEO_4K,
    bitrate_mbps=25.0,                    # 25 Mbps for 4K H.265 video
    fps=60,                               # 60 frames per second
    resolution="3840x2160",               # 4K resolution
    priority=6,                           # High priority (TC6)
    max_latency_ms=20.0,                 # Max 20ms latency requirement
    max_jitter_ms=3.0                    # Max 3ms jitter requirement
)

print(f"Stream defined: {front_camera.name}")
print(f"  Type: {front_camera.traffic_type.value}")
print(f"  Bitrate: {front_camera.bitrate_mbps} Mbps")
print(f"  Priority: TC{front_camera.priority}")
```

### Step 4: Calculate CBS Parameters

```python
# Calculate CBS parameters for the stream
params = calculator.calculate_cbs_params(front_camera)

print("\n" + "="*50)
print("CBS PARAMETERS CALCULATED")  
print("="*50)
print(f"Stream: {front_camera.name}")
print(f"idleSlope: {params.idle_slope:,} bps ({params.idle_slope/1_000_000:.1f} Mbps)")
print(f"sendSlope: {params.send_slope:,} bps ({params.send_slope/1_000_000:.1f} Mbps)")
print(f"hiCredit: {params.hi_credit:,} bits")
print(f"loCredit: {params.lo_credit:,} bits")
print(f"Reserved BW: {params.reserved_bandwidth_mbps:.1f} Mbps")
print(f"Actual BW: {params.actual_bandwidth_mbps:.1f} Mbps") 
print(f"Efficiency: {params.efficiency_percent:.1f}%")
```

**Expected Output:**
```
==================================================
CBS PARAMETERS CALCULATED
==================================================
Stream: Front_Camera_4K
idleSlope: 30,000,000 bps (30.0 Mbps)
sendSlope: -970,000,000 bps (-970.0 Mbps)
hiCredit: 365 bits
loCredit: -365 bits
Reserved BW: 30.0 Mbps
Actual BW: 25.0 Mbps
Efficiency: 83.3%
```

### Step 5: Understand the Results

The CBS parameters have specific meanings:

- **idleSlope**: Rate at which credits accumulate when the queue is idle (30 Mbps)
- **sendSlope**: Rate at which credits decrease during transmission (-970 Mbps)
- **hiCredit**: Maximum credit accumulation (365 bits)
- **loCredit**: Maximum credit depletion (-365 bits)

The 30 Mbps reserved bandwidth includes 20% headroom over the actual 25 Mbps requirement, providing robust QoS guarantees.

### Step 6: Analyze Performance Characteristics

```python
# Calculate theoretical delay for this stream
delay_analysis = calculator.calculate_theoretical_delay(front_camera, params)

print("\n" + "="*50)
print("DELAY ANALYSIS")
print("="*50)
for component, value in delay_analysis.items():
    print(f"{component.replace('_', ' ').title()}: {value:.3f} ms")

# Check if delay requirements are met
total_delay = delay_analysis['total_delay_ms']
meets_requirement = total_delay <= front_camera.max_latency_ms

print(f"\nDelay Requirement: ≤ {front_camera.max_latency_ms} ms")
print(f"Actual Delay: {total_delay:.3f} ms")
print(f"Status: {'✅ PASS' if meets_requirement else '❌ FAIL'}")
```

## Part 2: Multi-Stream Optimization

Real automotive networks have multiple concurrent streams. Let's optimize parameters for a complete autonomous vehicle scenario.

### Step 1: Define Multiple Streams

```python
# Define comprehensive automotive stream set
automotive_streams = [
    # Safety-critical control streams
    StreamConfig("Emergency_Brake", TrafficType.SAFETY_CRITICAL, 2, 100, "N/A", 7, 5, 0.5),
    StreamConfig("Steering_Control", TrafficType.SAFETY_CRITICAL, 1, 100, "N/A", 7, 5, 0.5),
    
    # Video streams
    StreamConfig("Front_Center_4K", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
    StreamConfig("Front_Left_4K", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
    StreamConfig("Front_Right_4K", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
    
    # Surround view cameras  
    StreamConfig("Left_Side_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
    StreamConfig("Right_Side_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
    StreamConfig("Rear_View_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
    
    # Sensor streams
    StreamConfig("LiDAR_Main", TrafficType.LIDAR, 100, 10, "N/A", 4, 40, 4),
    StreamConfig("Radar_Fusion", TrafficType.RADAR, 16, 50, "N/A", 3, 20, 2),
    
    # Communication
    StreamConfig("V2X_Safety", TrafficType.V2X, 10, 10, "N/A", 2, 100, 10),
    
    # Infotainment
    StreamConfig("Infotainment", TrafficType.INFOTAINMENT, 50, 30, "N/A", 1, 500, 50),
]

print(f"Defined {len(automotive_streams)} automotive streams")

# Calculate total bandwidth requirement
total_bitrate = sum(stream.bitrate_mbps for stream in automotive_streams)
print(f"Total raw bitrate: {total_bitrate} Mbps")
print(f"Link utilization: {(total_bitrate/1000)*100:.1f}%")
```

### Step 2: Optimize Parameters  

```python
# Optimize parameters for 75% target utilization
print("\nOptimizing CBS parameters...")
optimized_params = calculator.optimize_parameters(automotive_streams, target_utilization=75)

# Calculate total reserved bandwidth after optimization
total_reserved = sum(param.reserved_bandwidth_mbps for param in optimized_params.values())
final_utilization = (total_reserved / 1000) * 100

print(f"\nOptimization Results:")
print(f"Target utilization: 75%")
print(f"Achieved utilization: {final_utilization:.1f}%")
print(f"Total reserved bandwidth: {total_reserved:.1f} Mbps")
print(f"Bandwidth savings: {1000 - total_reserved:.1f} Mbps")
```

### Step 3: Validate Configuration

```python
# Validate the optimized configuration
warnings = calculator.validate_configuration(optimized_params)

print("\n" + "="*50)
print("CONFIGURATION VALIDATION")
print("="*50)

if warnings:
    print("⚠️  Validation Warnings:")
    for warning in warnings:
        print(f"  - {warning}")
else:
    print("✅ Configuration passed all validation checks")

# Show per-stream efficiency
print("\nPer-Stream Efficiency:")
for stream in sorted(automotive_streams, key=lambda x: x.priority, reverse=True):
    param = optimized_params[stream.name]
    print(f"  {stream.name}: {param.efficiency_percent:.1f}% "
          f"(Reserved: {param.reserved_bandwidth_mbps:.1f} Mbps)")
```

## Part 3: Generate Configuration Files

Export the optimized parameters to industry-standard formats.

### Step 1: Generate YAML Configuration

```python
# Generate YAML configuration file for network hardware
calculator.generate_config_file(automotive_streams, "autonomous_vehicle_cbs.yaml")

print("✅ YAML configuration generated: autonomous_vehicle_cbs.yaml")
```

### Step 2: Generate CSV Export

```python  
# Export to CSV for analysis and documentation
calculator.export_to_csv(automotive_streams, "cbs_parameters.csv")

print("✅ CSV export generated: cbs_parameters.csv")
```

### Step 3: Generate Performance Report

```python
# Generate comprehensive performance report
calculator.generate_performance_report(automotive_streams, "performance_analysis.md")

print("✅ Performance report generated: performance_analysis.md")
```

## Part 4: Traffic Generation and Testing

Now let's generate realistic traffic to test our CBS configuration.

### Step 1: Import Traffic Generator

```python
from src.traffic_generator import TrafficGenerator

# Initialize traffic generator
traffic_gen = TrafficGenerator()
```

### Step 2: Generate Automotive Traffic

```python
# Generate autonomous driving traffic scenario
print("Starting traffic generation...")
print("This will generate realistic automotive network traffic")
print("Press Ctrl+C to stop early if needed\n")

try:
    # Generate traffic for autonomous driving scenario (60 seconds)
    traffic_gen.start_scenario("autonomous_driving", duration=60)
    
    # Get statistics
    stats = traffic_gen.get_statistics()
    
    print("\n" + "="*50)  
    print("TRAFFIC GENERATION RESULTS")
    print("="*50)
    print(f"Total packets sent: {stats['total_packets']:,}")
    print(f"Total bytes sent: {stats['total_bytes']:,} ({stats['total_bytes']/1024/1024:.1f} MB)")
    print(f"Average bitrate: {stats.get('total_bitrate_mbps', 0):.1f} Mbps")
    print(f"Average packet rate: {stats.get('total_pps', 0):.1f} pps")
    
    if stats['total_errors'] > 0:
        print(f"⚠️  Errors encountered: {stats['total_errors']}")
    else:
        print("✅ Traffic generation completed successfully")
        
    # Save traffic statistics
    traffic_gen.save_statistics("traffic_stats.json")
    
except KeyboardInterrupt:
    print("\n🛑 Traffic generation interrupted by user")
    traffic_gen.stop_all_traffic()
```

## Part 5: Data Analysis and Visualization

Finally, let's analyze experimental data and create visualizations.

### Step 1: Load Experimental Data

```python
from src.data_analyzer import CBSDataAnalyzer

# Load the experimental data
analyzer = CBSDataAnalyzer('results/experiment_data.json')
print("✅ Experimental data loaded")
```

### Step 2: Generate Performance Summary

```python
# Generate performance summary DataFrame
summary_df = analyzer.generate_performance_summary()

print("\n" + "="*50)
print("PERFORMANCE SUMMARY")
print("="*50)
print(summary_df.head())

# Show improvement statistics
if len(summary_df) > 0:
    avg_improvement = summary_df['improvement_cbs'].mean()
    max_improvement = summary_df['improvement_cbs'].max()
    
    print(f"\nCBS Performance Improvements:")
    print(f"  Average improvement: {avg_improvement:.1f}%")
    print(f"  Maximum improvement: {max_improvement:.1f}%")
```

### Step 3: Generate Visualizations

```python
# Create comprehensive analysis dashboard
print("\nGenerating analysis dashboard...")
analyzer.create_comprehensive_dashboard('analysis_results')

print("✅ Analysis dashboard created in 'analysis_results/' directory")
print("📊 Open 'analysis_results/dashboard.html' in your browser to view results")
```

### Step 4: Create Individual Plots

```python
# Generate individual analysis plots
print("Generating individual visualizations...")

# Frame loss analysis
analyzer.plot_frame_loss_comparison('frame_loss_analysis.html')
print("  ✅ Frame loss analysis: frame_loss_analysis.html")

# Latency analysis  
analyzer.plot_latency_analysis('latency_analysis.html')
print("  ✅ Latency analysis: latency_analysis.html")

# Jitter analysis
analyzer.plot_jitter_analysis('jitter_analysis.html')  
print("  ✅ Jitter analysis: jitter_analysis.html")

# CBS credit dynamics
analyzer.plot_credit_dynamics('credit_dynamics.html')
print("  ✅ Credit dynamics: credit_dynamics.html")
```

## Part 6: Running Everything Together

Let's put it all together in a complete workflow script:

```python
#!/usr/bin/env python3
"""
Complete CBS Analysis Workflow
This script demonstrates the complete CBS research workflow
"""

from src.cbs_calculator import CBSCalculator, StreamConfig, TrafficType
from src.traffic_generator import TrafficGenerator  
from src.data_analyzer import CBSDataAnalyzer
import time

def main():
    print("🚗 Starting Complete CBS Analysis Workflow")
    print("="*60)
    
    # Step 1: Initialize calculator
    print("\n1️⃣ Initializing CBS Calculator...")
    calculator = CBSCalculator(link_speed_mbps=1000)
    
    # Step 2: Define streams  
    print("2️⃣ Defining automotive streams...")
    streams = [
        StreamConfig("Emergency_Control", TrafficType.SAFETY_CRITICAL, 2, 100, "N/A", 7, 5, 0.5),
        StreamConfig("Front_Camera_4K", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
        StreamConfig("Surround_Camera_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
        StreamConfig("LiDAR_Main", TrafficType.LIDAR, 100, 10, "N/A", 4, 40, 4),
        StreamConfig("V2X_Safety", TrafficType.V2X, 10, 10, "N/A", 2, 100, 10),
    ]
    
    print(f"   Defined {len(streams)} streams")
    
    # Step 3: Calculate and optimize parameters
    print("3️⃣ Calculating optimized CBS parameters...")  
    params = calculator.optimize_parameters(streams, target_utilization=75)
    
    total_reserved = sum(p.reserved_bandwidth_mbps for p in params.values())
    utilization = (total_reserved / 1000) * 100
    print(f"   Network utilization: {utilization:.1f}%")
    
    # Step 4: Generate configuration files
    print("4️⃣ Generating configuration files...")
    calculator.generate_config_file(streams, "workflow_config.yaml")
    calculator.export_to_csv(streams, "workflow_params.csv") 
    calculator.generate_performance_report(streams, "workflow_report.md")
    print("   Configuration files generated")
    
    # Step 5: Validate configuration
    print("5️⃣ Validating configuration...")
    warnings = calculator.validate_configuration(params)
    if warnings:
        print(f"   ⚠️  {len(warnings)} warnings found")
        for warning in warnings[:3]:  # Show first 3
            print(f"     - {warning}")
    else:
        print("   ✅ Configuration validated successfully")
    
    # Step 6: Analyze experimental data
    print("6️⃣ Analyzing experimental data...")
    try:
        analyzer = CBSDataAnalyzer('results/experiment_data.json')
        analyzer.create_comprehensive_dashboard('workflow_analysis')
        print("   ✅ Analysis dashboard created")
    except FileNotFoundError:
        print("   ⚠️  No experimental data found, skipping analysis")
    
    print("\n🎉 Workflow completed successfully!")
    print("\nGenerated files:")
    print("  📄 workflow_config.yaml - CBS configuration")
    print("  📊 workflow_params.csv - Parameter table")  
    print("  📋 workflow_report.md - Performance report")
    print("  📈 workflow_analysis/ - Analysis dashboard")

if __name__ == "__main__":
    main()
```

Save this as `complete_workflow.py` and run it:

```bash
python complete_workflow.py
```

## Summary

In this tutorial, you learned how to:

1. ✅ **Calculate CBS parameters** for individual streams
2. ✅ **Optimize multi-stream configurations** for target network utilization  
3. ✅ **Generate configuration files** for network hardware
4. ✅ **Validate CBS configurations** and identify potential issues
5. ✅ **Generate realistic traffic** for testing scenarios
6. ✅ **Analyze experimental data** with interactive visualizations
7. ✅ **Create comprehensive reports** for documentation and research

## Next Steps

Now that you understand the basics, explore these advanced topics:

- **[Advanced Configuration](advanced_configuration.html)**: Custom traffic types and complex scenarios
- **[Custom Traffic Profiles](custom_traffic_profiles.html)**: Creating realistic automotive traffic patterns
- **[Performance Analysis](performance_analysis.html)**: Deep-dive into CBS performance characteristics
- **[Integration Guide](integration_guide.html)**: Integrating with real network hardware

## Troubleshooting

**Common Issues:**

1. **"Module not found" errors**: Make sure you're running from the project root directory
2. **Permission errors**: Some network tools may require elevated privileges
3. **Large memory usage**: Use smaller datasets or reduce visualization complexity
4. **Slow performance**: Consider using optimized numerical libraries (numpy[mkl])

**Getting Help:**

- Check the [API Reference](../api_reference.html) for detailed function documentation
- Browse [example scripts](https://github.com/your-org/cbs-research/tree/main/examples) 
- Create an issue on [GitHub](https://github.com/your-org/cbs-research/issues) for bugs or questions