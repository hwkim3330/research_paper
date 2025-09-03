#!/usr/bin/env python3
"""
CBS Performance Benchmarking Tool
Comprehensive benchmarking and performance testing for CBS implementations
"""

import time
import json
import csv
import logging
import statistics
import threading
import subprocess
import psutil
import socket
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import argparse
import sys
import os

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent))

from cbs_calculator import CBSCalculator, StreamConfig, TrafficType, CBSParameters
from traffic_generator import TrafficGenerator, TrafficProfile

@dataclass
class BenchmarkResult:
    """Benchmark test result"""
    test_name: str
    timestamp: str
    duration_seconds: float
    iterations: int
    success_rate: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_mbps: float
    packet_loss_rate: float
    cpu_usage_percent: float
    memory_usage_mb: float
    error_count: int
    warnings: List[str]
    raw_data: Dict[str, Any]

@dataclass
class BenchmarkConfig:
    """Benchmark configuration"""
    name: str
    description: str
    duration_seconds: int = 60
    iterations: int = 3
    link_speed_mbps: int = 1000
    streams: List[StreamConfig] = None
    background_loads: List[float] = None
    enable_cpu_monitoring: bool = True
    enable_memory_monitoring: bool = True
    output_dir: str = "benchmark_results"

class CBSPerformanceBenchmark:
    """CBS Performance Benchmarking Suite"""
    
    def __init__(self, config_file: str = None):
        """Initialize benchmark suite"""
        self.logger = self._setup_logging()
        self.results: List[BenchmarkResult] = []
        self.calculator = CBSCalculator()
        self.traffic_generator = TrafficGenerator()
        
        # System monitoring
        self.system_stats = []
        self.monitoring_active = False
        
        # Load configuration
        if config_file:
            self.load_config(config_file)
        else:
            self.config = self._default_config()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _default_config(self) -> BenchmarkConfig:
        """Create default benchmark configuration"""
        # Create realistic automotive streams
        streams = [
            StreamConfig("Emergency_Control", TrafficType.SAFETY_CRITICAL, 2, 100, "N/A", 7, 5, 0.5),
            StreamConfig("Front_4K_Camera", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
            StreamConfig("Surround_HD_1", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
            StreamConfig("Surround_HD_2", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
            StreamConfig("LiDAR_Main", TrafficType.LIDAR, 100, 10, "N/A", 4, 40, 4),
            StreamConfig("Radar_Fusion", TrafficType.RADAR, 16, 50, "N/A", 3, 20, 2),
            StreamConfig("V2X_Safety", TrafficType.V2X, 10, 10, "N/A", 2, 100, 10),
            StreamConfig("Infotainment", TrafficType.INFOTAINMENT, 50, 30, "N/A", 1, 500, 50)
        ]
        
        return BenchmarkConfig(
            name="Default CBS Benchmark",
            description="Comprehensive CBS performance testing suite",
            duration_seconds=60,
            iterations=3,
            streams=streams,
            background_loads=[0, 100, 200, 400, 600, 800, 1000]
        )
    
    def load_config(self, config_file: str) -> None:
        """Load benchmark configuration from file"""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Parse streams
            streams = []
            for stream_data in config_data.get('streams', []):
                stream = StreamConfig(**stream_data)
                streams.append(stream)
            
            self.config = BenchmarkConfig(
                name=config_data.get('name', 'Custom Benchmark'),
                description=config_data.get('description', ''),
                duration_seconds=config_data.get('duration_seconds', 60),
                iterations=config_data.get('iterations', 3),
                link_speed_mbps=config_data.get('link_speed_mbps', 1000),
                streams=streams,
                background_loads=config_data.get('background_loads', [0, 200, 400, 600, 800]),
                enable_cpu_monitoring=config_data.get('enable_cpu_monitoring', True),
                enable_memory_monitoring=config_data.get('enable_memory_monitoring', True),
                output_dir=config_data.get('output_dir', 'benchmark_results')
            )
            
            self.logger.info(f"Configuration loaded from {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise
    
    def _start_system_monitoring(self) -> None:
        """Start system resource monitoring"""
        if not (self.config.enable_cpu_monitoring or self.config.enable_memory_monitoring):
            return
        
        def monitor():
            while self.monitoring_active:
                try:
                    stats = {
                        'timestamp': time.time(),
                        'cpu_percent': psutil.cpu_percent() if self.config.enable_cpu_monitoring else 0,
                        'memory_mb': psutil.virtual_memory().used / 1024 / 1024 if self.config.enable_memory_monitoring else 0,
                        'memory_percent': psutil.virtual_memory().percent if self.config.enable_memory_monitoring else 0
                    }
                    self.system_stats.append(stats)
                    time.sleep(1)  # Monitor every second
                except Exception as e:
                    self.logger.warning(f"System monitoring error: {e}")
        
        self.monitoring_active = True
        self.system_stats.clear()
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _stop_system_monitoring(self) -> Dict[str, float]:
        """Stop system monitoring and return statistics"""
        self.monitoring_active = False
        time.sleep(1.1)  # Wait for monitoring thread to finish
        
        if not self.system_stats:
            return {'avg_cpu_percent': 0, 'avg_memory_mb': 0, 'max_memory_mb': 0}
        
        cpu_values = [s['cpu_percent'] for s in self.system_stats]
        memory_values = [s['memory_mb'] for s in self.system_stats]
        
        return {
            'avg_cpu_percent': statistics.mean(cpu_values) if cpu_values else 0,
            'avg_memory_mb': statistics.mean(memory_values) if memory_values else 0,
            'max_memory_mb': max(memory_values) if memory_values else 0,
            'min_memory_mb': min(memory_values) if memory_values else 0
        }
    
    def benchmark_cbs_calculation_performance(self) -> BenchmarkResult:
        """Benchmark CBS parameter calculation performance"""
        test_name = "CBS_Calculation_Performance"
        self.logger.info(f"Running benchmark: {test_name}")
        
        streams = self.config.streams
        iterations = self.config.iterations * 100  # More iterations for calculation benchmark
        latencies = []
        warnings = []
        error_count = 0
        
        self._start_system_monitoring()
        
        start_time = time.time()
        
        for i in range(iterations):
            try:
                calc_start = time.perf_counter()
                
                # Calculate CBS parameters
                results = self.calculator.calculate_multi_stream(streams)
                
                # Validate results
                validation_warnings = self.calculator.validate_configuration(results)
                if validation_warnings:
                    warnings.extend(validation_warnings)
                
                calc_end = time.perf_counter()
                latency_ms = (calc_end - calc_start) * 1000
                latencies.append(latency_ms)
                
            except Exception as e:
                error_count += 1
                self.logger.error(f"Calculation error in iteration {i}: {e}")
        
        end_time = time.time()
        system_stats = self._stop_system_monitoring()
        
        # Calculate statistics
        success_rate = (iterations - error_count) / iterations * 100
        avg_latency = statistics.mean(latencies) if latencies else 0
        throughput = iterations / (end_time - start_time) if (end_time - start_time) > 0 else 0
        
        result = BenchmarkResult(
            test_name=test_name,
            timestamp=datetime.now().isoformat(),
            duration_seconds=end_time - start_time,
            iterations=iterations,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=statistics.median(latencies) if latencies else 0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0,
            p99_latency_ms=np.percentile(latencies, 99) if latencies else 0,
            throughput_mbps=0,  # Not applicable for calculation benchmark
            packet_loss_rate=0,  # Not applicable
            cpu_usage_percent=system_stats['avg_cpu_percent'],
            memory_usage_mb=system_stats['avg_memory_mb'],
            error_count=error_count,
            warnings=list(set(warnings)),
            raw_data={
                'latencies_ms': latencies,
                'calculations_per_second': throughput,
                'system_stats': self.system_stats.copy()
            }
        )
        
        self.results.append(result)
        self.logger.info(f"Benchmark {test_name} completed: {success_rate:.1f}% success, "
                        f"{avg_latency:.3f}ms avg latency, {throughput:.1f} calc/sec")
        
        return result
    
    def benchmark_parameter_optimization(self) -> BenchmarkResult:
        """Benchmark CBS parameter optimization performance"""
        test_name = "CBS_Optimization_Performance"
        self.logger.info(f"Running benchmark: {test_name}")
        
        streams = self.config.streams
        target_utilizations = [50, 60, 70, 75, 80, 85]
        latencies = []
        warnings = []
        error_count = 0
        
        self._start_system_monitoring()
        
        start_time = time.time()
        
        for target_util in target_utilizations:
            for _ in range(self.config.iterations):
                try:
                    opt_start = time.perf_counter()
                    
                    # Run optimization
                    results = self.calculator.optimize_parameters(streams, target_util)
                    
                    # Validate optimized results
                    validation_warnings = self.calculator.validate_configuration(results)
                    if validation_warnings:
                        warnings.extend(validation_warnings)
                    
                    opt_end = time.perf_counter()
                    latency_ms = (opt_end - opt_start) * 1000
                    latencies.append(latency_ms)
                    
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"Optimization error: {e}")
        
        end_time = time.time()
        system_stats = self._stop_system_monitoring()
        
        # Calculate statistics
        iterations = len(target_utilizations) * self.config.iterations
        success_rate = (iterations - error_count) / iterations * 100
        avg_latency = statistics.mean(latencies) if latencies else 0
        
        result = BenchmarkResult(
            test_name=test_name,
            timestamp=datetime.now().isoformat(),
            duration_seconds=end_time - start_time,
            iterations=iterations,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=statistics.median(latencies) if latencies else 0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0,
            p99_latency_ms=np.percentile(latencies, 99) if latencies else 0,
            throughput_mbps=0,
            packet_loss_rate=0,
            cpu_usage_percent=system_stats['avg_cpu_percent'],
            memory_usage_mb=system_stats['avg_memory_mb'],
            error_count=error_count,
            warnings=list(set(warnings)),
            raw_data={
                'latencies_ms': latencies,
                'target_utilizations': target_utilizations,
                'optimizations_per_second': iterations / (end_time - start_time) if (end_time - start_time) > 0 else 0
            }
        )
        
        self.results.append(result)
        self.logger.info(f"Benchmark {test_name} completed: {success_rate:.1f}% success, "
                        f"{avg_latency:.3f}ms avg latency")
        
        return result
    
    def benchmark_scalability(self) -> BenchmarkResult:
        """Benchmark CBS scalability with increasing number of streams"""
        test_name = "CBS_Scalability_Test"
        self.logger.info(f"Running benchmark: {test_name}")
        
        base_streams = self.config.streams
        stream_counts = [1, 2, 4, 8, 16, 32, 64] if len(base_streams) >= 8 else [1, 2, 4, len(base_streams)]
        latencies = []
        warnings = []
        error_count = 0
        scalability_data = []
        
        self._start_system_monitoring()
        start_time = time.time()
        
        for stream_count in stream_counts:
            # Create subset of streams
            test_streams = base_streams[:stream_count] if stream_count <= len(base_streams) else base_streams * (stream_count // len(base_streams) + 1)
            test_streams = test_streams[:stream_count]
            
            for _ in range(self.config.iterations):
                try:
                    calc_start = time.perf_counter()
                    
                    # Calculate parameters
                    results = self.calculator.calculate_multi_stream(test_streams)
                    validation_warnings = self.calculator.validate_configuration(results)
                    
                    calc_end = time.perf_counter()
                    latency_ms = (calc_end - calc_start) * 1000
                    latencies.append(latency_ms)
                    
                    scalability_data.append({
                        'stream_count': stream_count,
                        'latency_ms': latency_ms,
                        'warnings_count': len(validation_warnings) if validation_warnings else 0
                    })
                    
                    if validation_warnings:
                        warnings.extend(validation_warnings)
                    
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"Scalability error with {stream_count} streams: {e}")
        
        end_time = time.time()
        system_stats = self._stop_system_monitoring()
        
        # Calculate statistics
        total_iterations = sum(self.config.iterations for _ in stream_counts)
        success_rate = (total_iterations - error_count) / total_iterations * 100
        avg_latency = statistics.mean(latencies) if latencies else 0
        
        result = BenchmarkResult(
            test_name=test_name,
            timestamp=datetime.now().isoformat(),
            duration_seconds=end_time - start_time,
            iterations=total_iterations,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            min_latency_ms=min(latencies) if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            p50_latency_ms=statistics.median(latencies) if latencies else 0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0,
            p99_latency_ms=np.percentile(latencies, 99) if latencies else 0,
            throughput_mbps=0,
            packet_loss_rate=0,
            cpu_usage_percent=system_stats['avg_cpu_percent'],
            memory_usage_mb=system_stats['avg_memory_mb'],
            error_count=error_count,
            warnings=list(set(warnings)),
            raw_data={
                'scalability_data': scalability_data,
                'stream_counts': stream_counts,
                'latencies_by_count': {count: [d['latency_ms'] for d in scalability_data if d['stream_count'] == count] for count in stream_counts}
            }
        )
        
        self.results.append(result)
        self.logger.info(f"Benchmark {test_name} completed: {success_rate:.1f}% success")
        
        return result
    
    def benchmark_memory_usage(self) -> BenchmarkResult:
        """Benchmark memory usage patterns"""
        test_name = "Memory_Usage_Test"
        self.logger.info(f"Running benchmark: {test_name}")
        
        streams = self.config.streams
        memory_samples = []
        error_count = 0
        
        # Extended monitoring for memory test
        self._start_system_monitoring()
        start_time = time.time()
        
        # Run calculations repeatedly to test for memory leaks
        for i in range(1000):  # Many iterations to detect leaks
            try:
                # Calculate CBS parameters multiple times
                for _ in range(10):
                    results = self.calculator.calculate_multi_stream(streams)
                    optimized = self.calculator.optimize_parameters(streams)
                
                # Sample memory usage
                if i % 50 == 0:  # Sample every 50 iterations
                    current_memory = psutil.virtual_memory().used / 1024 / 1024
                    memory_samples.append({
                        'iteration': i,
                        'memory_mb': current_memory,
                        'timestamp': time.time()
                    })
                
            except Exception as e:
                error_count += 1
                self.logger.error(f"Memory test error in iteration {i}: {e}")
        
        end_time = time.time()
        system_stats = self._stop_system_monitoring()
        
        # Analyze memory usage
        if memory_samples:
            initial_memory = memory_samples[0]['memory_mb']
            final_memory = memory_samples[-1]['memory_mb']
            memory_growth = final_memory - initial_memory
            max_memory = max(s['memory_mb'] for s in memory_samples)
            min_memory = min(s['memory_mb'] for s in memory_samples)
        else:
            memory_growth = 0
            max_memory = system_stats['max_memory_mb']
            min_memory = system_stats['min_memory_mb']
        
        result = BenchmarkResult(
            test_name=test_name,
            timestamp=datetime.now().isoformat(),
            duration_seconds=end_time - start_time,
            iterations=1000,
            success_rate=(1000 - error_count) / 1000 * 100,
            avg_latency_ms=0,
            min_latency_ms=0,
            max_latency_ms=0,
            p50_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            throughput_mbps=0,
            packet_loss_rate=0,
            cpu_usage_percent=system_stats['avg_cpu_percent'],
            memory_usage_mb=system_stats['avg_memory_mb'],
            error_count=error_count,
            warnings=[f"Memory growth: {memory_growth:.1f} MB"] if abs(memory_growth) > 10 else [],
            raw_data={
                'memory_samples': memory_samples,
                'memory_growth_mb': memory_growth,
                'max_memory_mb': max_memory,
                'min_memory_mb': min_memory
            }
        )
        
        self.results.append(result)
        self.logger.info(f"Benchmark {test_name} completed: Memory growth {memory_growth:.1f} MB")
        
        return result
    
    def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all benchmark tests"""
        self.logger.info("Starting comprehensive CBS performance benchmark suite")
        
        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(exist_ok=True)
        
        # Run individual benchmarks
        benchmarks = [
            self.benchmark_cbs_calculation_performance,
            self.benchmark_parameter_optimization,
            self.benchmark_scalability,
            self.benchmark_memory_usage
        ]
        
        for benchmark_func in benchmarks:
            try:
                result = benchmark_func()
                self.logger.info(f"Completed benchmark: {result.test_name}")
            except Exception as e:
                self.logger.error(f"Benchmark failed: {benchmark_func.__name__}: {e}")
        
        # Generate reports
        self.generate_benchmark_report()
        self.generate_csv_results()
        self.generate_visualizations()
        
        self.logger.info(f"Benchmark suite completed. Results in {self.config.output_dir}/")
        
        return self.results
    
    def generate_benchmark_report(self) -> None:
        """Generate comprehensive benchmark report"""
        report_path = Path(self.config.output_dir) / "benchmark_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# CBS Performance Benchmark Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Configuration:** {self.config.name}\n")
            f.write(f"**Description:** {self.config.description}\n\n")
            
            f.write("## Executive Summary\n\n")
            
            if self.results:
                avg_success_rate = statistics.mean([r.success_rate for r in self.results])
                total_iterations = sum([r.iterations for r in self.results])
                total_duration = sum([r.duration_seconds for r in self.results])
                
                f.write(f"- **Total Tests:** {len(self.results)}\n")
                f.write(f"- **Total Iterations:** {total_iterations:,}\n")
                f.write(f"- **Total Duration:** {total_duration:.1f} seconds\n")
                f.write(f"- **Average Success Rate:** {avg_success_rate:.1f}%\n\n")
            
            f.write("## Detailed Results\n\n")
            
            for result in self.results:
                f.write(f"### {result.test_name}\n\n")
                f.write(f"**Timestamp:** {result.timestamp}\n")
                f.write(f"**Duration:** {result.duration_seconds:.2f} seconds\n")
                f.write(f"**Iterations:** {result.iterations:,}\n")
                f.write(f"**Success Rate:** {result.success_rate:.1f}%\n\n")
                
                if result.avg_latency_ms > 0:
                    f.write("**Latency Statistics:**\n")
                    f.write(f"- Average: {result.avg_latency_ms:.3f} ms\n")
                    f.write(f"- Minimum: {result.min_latency_ms:.3f} ms\n")
                    f.write(f"- Maximum: {result.max_latency_ms:.3f} ms\n")
                    f.write(f"- P95: {result.p95_latency_ms:.3f} ms\n")
                    f.write(f"- P99: {result.p99_latency_ms:.3f} ms\n\n")
                
                f.write("**Resource Usage:**\n")
                f.write(f"- CPU: {result.cpu_usage_percent:.1f}%\n")
                f.write(f"- Memory: {result.memory_usage_mb:.1f} MB\n\n")
                
                if result.error_count > 0:
                    f.write(f"**Errors:** {result.error_count}\n\n")
                
                if result.warnings:
                    f.write("**Warnings:**\n")
                    for warning in result.warnings[:5]:  # Show first 5 warnings
                        f.write(f"- {warning}\n")
                    if len(result.warnings) > 5:
                        f.write(f"- ... and {len(result.warnings) - 5} more\n")
                    f.write("\n")
                
                f.write("---\n\n")
            
            f.write("## Recommendations\n\n")
            
            # Generate recommendations based on results
            recommendations = self._generate_recommendations()
            for rec in recommendations:
                f.write(f"- {rec}\n")
            
            f.write(f"\n*Report generated by CBS Performance Benchmark Tool*\n")
        
        self.logger.info(f"Benchmark report generated: {report_path}")
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations based on benchmark results"""
        recommendations = []
        
        if not self.results:
            return ["No benchmark results available for analysis."]
        
        # Check success rates
        low_success_tests = [r for r in self.results if r.success_rate < 95]
        if low_success_tests:
            recommendations.append("Some tests had low success rates. Review error logs for stability issues.")
        
        # Check memory usage
        high_memory_tests = [r for r in self.results if r.memory_usage_mb > 1000]  # >1GB
        if high_memory_tests:
            recommendations.append("High memory usage detected. Consider optimizing data structures.")
        
        # Check for memory leaks
        memory_test = next((r for r in self.results if r.test_name == "Memory_Usage_Test"), None)
        if memory_test and memory_test.raw_data:
            memory_growth = memory_test.raw_data.get('memory_growth_mb', 0)
            if abs(memory_growth) > 50:  # >50MB growth
                recommendations.append(f"Potential memory leak detected: {memory_growth:.1f} MB growth during test.")
        
        # Check CPU usage
        high_cpu_tests = [r for r in self.results if r.cpu_usage_percent > 80]
        if high_cpu_tests:
            recommendations.append("High CPU usage detected. Consider algorithm optimization.")
        
        # Check latency performance
        high_latency_tests = [r for r in self.results if r.avg_latency_ms > 100]  # >100ms
        if high_latency_tests:
            recommendations.append("High latencies detected. Review calculation efficiency.")
        
        # Scalability recommendations
        scalability_test = next((r for r in self.results if r.test_name == "CBS_Scalability_Test"), None)
        if scalability_test and scalability_test.raw_data:
            scalability_data = scalability_test.raw_data.get('latencies_by_count', {})
            if scalability_data:
                # Check if latency grows significantly with stream count
                min_streams = min(scalability_data.keys())
                max_streams = max(scalability_data.keys())
                min_latency = statistics.mean(scalability_data[min_streams])
                max_latency = statistics.mean(scalability_data[max_streams])
                
                if max_latency > min_latency * 10:  # 10x increase
                    recommendations.append(f"Poor scalability: latency increased {max_latency/min_latency:.1f}x with more streams.")
        
        if not recommendations:
            recommendations.append("All benchmark results look good. No performance issues detected.")
        
        return recommendations
    
    def generate_csv_results(self) -> None:
        """Generate CSV file with benchmark results"""
        csv_path = Path(self.config.output_dir) / "benchmark_results.csv"
        
        if not self.results:
            return
        
        # Convert results to dictionaries
        csv_data = []
        for result in self.results:
            row = asdict(result)
            # Convert complex fields to strings
            row['warnings'] = '; '.join(result.warnings)
            row['raw_data'] = json.dumps(result.raw_data) if result.raw_data else ''
            csv_data.append(row)
        
        # Write CSV
        fieldnames = csv_data[0].keys()
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        self.logger.info(f"CSV results generated: {csv_path}")
    
    def generate_visualizations(self) -> None:
        """Generate performance visualization plots"""
        if not self.results:
            return
        
        # Setup matplotlib
        plt.style.use('default')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('CBS Performance Benchmark Results', fontsize=16, fontweight='bold')
        
        # Plot 1: Success Rates
        ax1 = axes[0, 0]
        test_names = [r.test_name.replace('_', '\n') for r in self.results]
        success_rates = [r.success_rate for r in self.results]
        bars1 = ax1.bar(test_names, success_rates, color='lightgreen', alpha=0.7)
        ax1.set_title('Test Success Rates')
        ax1.set_ylabel('Success Rate (%)')
        ax1.set_ylim(0, 105)
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, rate in zip(bars1, success_rates):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{rate:.1f}%', ha='center', va='bottom')
        
        # Plot 2: Latency Statistics
        ax2 = axes[0, 1]
        latency_tests = [r for r in self.results if r.avg_latency_ms > 0]
        if latency_tests:
            names = [r.test_name.replace('_', '\n') for r in latency_tests]
            avg_latencies = [r.avg_latency_ms for r in latency_tests]
            p95_latencies = [r.p95_latency_ms for r in latency_tests]
            
            x_pos = np.arange(len(names))
            bars2 = ax2.bar(x_pos - 0.2, avg_latencies, 0.4, label='Average', alpha=0.7)
            bars3 = ax2.bar(x_pos + 0.2, p95_latencies, 0.4, label='P95', alpha=0.7)
            
            ax2.set_title('Latency Performance')
            ax2.set_ylabel('Latency (ms)')
            ax2.set_xlabel('Test')
            ax2.set_xticks(x_pos)
            ax2.set_xticklabels(names, rotation=45, ha='right')
            ax2.legend()
            ax2.set_yscale('log')
        else:
            ax2.text(0.5, 0.5, 'No latency data available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax2.transAxes, fontsize=12)
            ax2.set_title('Latency Performance (No Data)')
        
        # Plot 3: Resource Usage
        ax3 = axes[1, 0]
        cpu_usage = [r.cpu_usage_percent for r in self.results]
        memory_usage = [r.memory_usage_mb for r in self.results]
        
        ax3_twin = ax3.twinx()
        
        bars4 = ax3.bar([i - 0.2 for i in range(len(test_names))], cpu_usage, 0.4, 
                       label='CPU %', color='lightcoral', alpha=0.7)
        bars5 = ax3_twin.bar([i + 0.2 for i in range(len(test_names))], memory_usage, 0.4, 
                            label='Memory MB', color='lightblue', alpha=0.7)
        
        ax3.set_title('Resource Usage')
        ax3.set_ylabel('CPU Usage (%)', color='red')
        ax3_twin.set_ylabel('Memory Usage (MB)', color='blue')
        ax3.set_xlabel('Test')
        ax3.set_xticks(range(len(test_names)))
        ax3.set_xticklabels(test_names, rotation=45, ha='right')
        
        # Plot 4: Scalability Analysis
        ax4 = axes[1, 1]
        scalability_test = next((r for r in self.results if r.test_name == "CBS_Scalability_Test"), None)
        
        if scalability_test and scalability_test.raw_data:
            scalability_data = scalability_test.raw_data.get('latencies_by_count', {})
            if scalability_data:
                stream_counts = sorted(scalability_data.keys())
                avg_latencies = [statistics.mean(scalability_data[count]) for count in stream_counts]
                
                ax4.plot(stream_counts, avg_latencies, 'o-', linewidth=2, markersize=6)
                ax4.set_title('Scalability: Latency vs Stream Count')
                ax4.set_xlabel('Number of Streams')
                ax4.set_ylabel('Average Latency (ms)')
                ax4.grid(True, alpha=0.3)
                ax4.set_yscale('log')
            else:
                ax4.text(0.5, 0.5, 'No scalability data available', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax4.transAxes, fontsize=12)
                ax4.set_title('Scalability Analysis (No Data)')
        else:
            ax4.text(0.5, 0.5, 'Scalability test not run', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax4.transAxes, fontsize=12)
            ax4.set_title('Scalability Analysis (Not Run)')
        
        plt.tight_layout()
        
        # Save plot
        plot_path = Path(self.config.output_dir) / "benchmark_visualization.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Visualization generated: {plot_path}")
    
    def create_config_template(self, filename: str) -> None:
        """Create benchmark configuration template"""
        template = {
            "name": "Custom CBS Benchmark",
            "description": "Custom benchmark configuration for CBS testing",
            "duration_seconds": 60,
            "iterations": 3,
            "link_speed_mbps": 1000,
            "background_loads": [0, 100, 200, 400, 600, 800],
            "enable_cpu_monitoring": True,
            "enable_memory_monitoring": True,
            "output_dir": "benchmark_results",
            "streams": [
                {
                    "name": "Emergency_Control",
                    "traffic_type": "safety_critical",
                    "bitrate_mbps": 2.0,
                    "fps": 100,
                    "resolution": "N/A",
                    "priority": 7,
                    "max_latency_ms": 5.0,
                    "max_jitter_ms": 0.5
                },
                {
                    "name": "Video_4K",
                    "traffic_type": "video_4k",
                    "bitrate_mbps": 25.0,
                    "fps": 60,
                    "resolution": "3840x2160",
                    "priority": 6,
                    "max_latency_ms": 20.0,
                    "max_jitter_ms": 3.0
                }
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(template, f, indent=2)
        
        print(f"Benchmark configuration template created: {filename}")

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='CBS Performance Benchmark Tool')
    parser.add_argument('--config', help='Benchmark configuration file')
    parser.add_argument('--output-dir', default='benchmark_results', help='Output directory')
    parser.add_argument('--create-template', help='Create configuration template file')
    parser.add_argument('--test', choices=['all', 'calculation', 'optimization', 'scalability', 'memory'],
                       default='all', help='Specific test to run')
    parser.add_argument('--iterations', type=int, default=3, help='Number of iterations per test')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    
    args = parser.parse_args()
    
    # Create configuration template
    if args.create_template:
        benchmark = CBSPerformanceBenchmark()
        benchmark.create_config_template(args.create_template)
        return
    
    # Initialize benchmark suite
    benchmark = CBSPerformanceBenchmark(args.config)
    
    # Override configuration from command line
    if args.output_dir != 'benchmark_results':
        benchmark.config.output_dir = args.output_dir
    if args.iterations != 3:
        benchmark.config.iterations = args.iterations
    if args.duration != 60:
        benchmark.config.duration_seconds = args.duration
    
    try:
        print(f"🚀 Starting CBS Performance Benchmark Suite")
        print(f"📊 Configuration: {benchmark.config.name}")
        print(f"⏱️  Iterations: {benchmark.config.iterations}")
        print(f"📁 Output: {benchmark.config.output_dir}/")
        print()
        
        # Run specific test or all tests
        if args.test == 'all':
            benchmark.run_all_benchmarks()
        elif args.test == 'calculation':
            benchmark.benchmark_cbs_calculation_performance()
        elif args.test == 'optimization':
            benchmark.benchmark_parameter_optimization()
        elif args.test == 'scalability':
            benchmark.benchmark_scalability()
        elif args.test == 'memory':
            benchmark.benchmark_memory_usage()
        
        # Summary
        print(f"\n📈 Benchmark Suite Complete!")
        if benchmark.results:
            avg_success = statistics.mean([r.success_rate for r in benchmark.results])
            print(f"✅ Average Success Rate: {avg_success:.1f}%")
            print(f"📊 Tests Completed: {len(benchmark.results)}")
            print(f"📁 Results: {benchmark.config.output_dir}/")
        
    except KeyboardInterrupt:
        print("\n🛑 Benchmark interrupted by user")
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()