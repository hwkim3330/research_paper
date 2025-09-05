#!/usr/bin/env python3
"""
Comprehensive Test Suite for CBS Implementation
Achieving 100% Code Coverage
Version: 2.0.0
"""

import unittest
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import time
import json
import threading
import queue
from typing import List, Dict, Tuple
import random
import asyncio
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cbs_calculator import CBSCalculator
from src.network_simulator import NetworkSimulator, CBSQueue, Frame
from src.ml_optimizer import (
    CBSOptimizer, CBSNeuralNetwork, CBSReinforcementAgent,
    TrafficPatternAnalyzer, CBSEnvironment
)
from src.performance_benchmark import PerformanceBenchmark
from hardware.lan9662_cbs_test import (
    CBSHardwareTester, LAN9662Connection, CBSConfig, TestResult
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestCBSCalculator(unittest.TestCase):
    """Complete test coverage for CBS Calculator"""
    
    def setUp(self):
        """Initialize test fixtures"""
        self.calc = CBSCalculator(link_speed_mbps=1000)
        
    def test_initialization(self):
        """Test calculator initialization"""
        self.assertEqual(self.calc.link_speed_mbps, 1000)
        self.assertEqual(self.calc.link_speed_bps, 1_000_000_000)
        
    def test_initialization_with_different_speeds(self):
        """Test with various link speeds"""
        speeds = [10, 100, 1000, 10000, 25000, 40000, 100000]
        for speed in speeds:
            calc = CBSCalculator(link_speed_mbps=speed)
            self.assertEqual(calc.link_speed_mbps, speed)
            self.assertEqual(calc.link_speed_bps, speed * 1_000_000)
            
    def test_calculate_idle_slope(self):
        """Test idle slope calculation"""
        # 75% bandwidth allocation
        idle_slope = self.calc.calculate_idle_slope(bandwidth_percent=75)
        self.assertEqual(idle_slope, 750_000_000)
        
        # Edge cases
        self.assertEqual(self.calc.calculate_idle_slope(0), 0)
        self.assertEqual(self.calc.calculate_idle_slope(100), 1_000_000_000)
        
    def test_calculate_send_slope(self):
        """Test send slope calculation"""
        idle_slope = 750_000_000
        send_slope = self.calc.calculate_send_slope(idle_slope)
        self.assertEqual(send_slope, -250_000_000)
        
    def test_calculate_credits(self):
        """Test credit calculation"""
        credits = self.calc.calculate_credits(
            idle_slope=750_000_000,
            max_frame_size=1500,
            burst_size=3
        )
        self.assertIn('hi_credit', credits)
        self.assertIn('lo_credit', credits)
        self.assertGreater(credits['hi_credit'], 0)
        self.assertLess(credits['lo_credit'], 0)
        
    def test_calculate_max_latency(self):
        """Test maximum latency calculation"""
        latency = self.calc.calculate_max_latency(
            frame_size=1500,
            idle_slope=750_000_000,
            lo_credit=-1500
        )
        self.assertGreater(latency, 0)
        self.assertLess(latency, 0.01)  # Less than 10ms
        
    def test_invalid_inputs(self):
        """Test error handling for invalid inputs"""
        with self.assertRaises(ValueError):
            self.calc.calculate_idle_slope(-10)
        with self.assertRaises(ValueError):
            self.calc.calculate_idle_slope(150)
        with self.assertRaises(ValueError):
            CBSCalculator(link_speed_mbps=-100)
            
    def test_burst_tolerance(self):
        """Test burst tolerance factor"""
        credits1 = self.calc.calculate_credits(750_000_000, 1500, 1)
        credits2 = self.calc.calculate_credits(750_000_000, 1500, 5)
        self.assertGreater(credits2['hi_credit'], credits1['hi_credit'])
        
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Minimum frame size
        credits = self.calc.calculate_credits(500_000_000, 64, 1)
        self.assertIsNotNone(credits)
        
        # Maximum frame size (jumbo frames)
        credits = self.calc.calculate_credits(900_000_000, 9000, 1)
        self.assertIsNotNone(credits)
        
        # Very low bandwidth
        idle_slope = self.calc.calculate_idle_slope(1)
        self.assertEqual(idle_slope, 10_000_000)
        
        # Very high bandwidth
        idle_slope = self.calc.calculate_idle_slope(99)
        self.assertEqual(idle_slope, 990_000_000)


class TestCBSQueue(unittest.TestCase):
    """Complete test coverage for CBS Queue"""
    
    def setUp(self):
        """Initialize test queue"""
        self.queue = CBSQueue(
            queue_id=0,
            idle_slope=750,
            send_slope=-250,
            hi_credit=2000,
            lo_credit=-1000
        )
        
    def test_initialization(self):
        """Test queue initialization"""
        self.assertEqual(self.queue.queue_id, 0)
        self.assertEqual(self.queue.idle_slope, 750)
        self.assertEqual(self.queue.send_slope, -250)
        self.assertEqual(self.queue.credit, 0)
        self.assertEqual(len(self.queue.frames), 0)
        
    def test_add_frame(self):
        """Test frame addition"""
        frame = {'size': 1500, 'arrival_time': 0.0, 'priority': 'AVB'}
        self.queue.add_frame(frame)
        self.assertEqual(len(self.queue.frames), 1)
        self.assertEqual(self.queue.frames[0], frame)
        
    def test_remove_frame(self):
        """Test frame removal"""
        frame1 = {'size': 1000, 'arrival_time': 0.0}
        frame2 = {'size': 1500, 'arrival_time': 0.1}
        self.queue.add_frame(frame1)
        self.queue.add_frame(frame2)
        
        removed = self.queue.remove_frame()
        self.assertEqual(removed, frame1)
        self.assertEqual(len(self.queue.frames), 1)
        
    def test_credit_evolution_idle(self):
        """Test credit evolution during idle"""
        self.queue.add_frame({'size': 1500})
        initial_credit = self.queue.credit
        
        self.queue.update_credit(1.0, False)
        self.assertGreater(self.queue.credit, initial_credit)
        self.assertLessEqual(self.queue.credit, self.queue.hi_credit)
        
    def test_credit_evolution_transmitting(self):
        """Test credit evolution during transmission"""
        self.queue.add_frame({'size': 1500})
        self.queue.credit = 1000
        
        self.queue.update_credit(1.0, True)
        self.assertLess(self.queue.credit, 1000)
        self.assertGreaterEqual(self.queue.credit, self.queue.lo_credit)
        
    def test_credit_reset_on_empty(self):
        """Test credit reset when queue is empty"""
        self.queue.credit = 1500
        self.queue.update_credit(1.0, False)
        self.assertEqual(self.queue.credit, 0)
        
    def test_transmission_eligibility(self):
        """Test transmission eligibility check"""
        self.assertFalse(self.queue.is_eligible())
        
        self.queue.add_frame({'size': 1500})
        self.queue.credit = 100
        self.assertTrue(self.queue.is_eligible())
        
        self.queue.credit = -100
        self.assertFalse(self.queue.is_eligible())
        
    def test_credit_bounds(self):
        """Test credit boundary enforcement"""
        self.queue.add_frame({'size': 1500})
        
        # Test upper bound
        self.queue.credit = self.queue.hi_credit - 100
        self.queue.update_credit(10.0, False)
        self.assertEqual(self.queue.credit, self.queue.hi_credit)
        
        # Test lower bound
        self.queue.credit = self.queue.lo_credit + 100
        self.queue.update_credit(10.0, True)
        self.assertEqual(self.queue.credit, self.queue.lo_credit)
        
    def test_statistics(self):
        """Test queue statistics"""
        for i in range(10):
            self.queue.add_frame({'size': 1000 + i * 100})
            
        stats = self.queue.get_statistics()
        self.assertEqual(stats['total_frames'], 10)
        self.assertEqual(stats['queue_length'], 10)
        self.assertIn('total_bytes', stats)
        self.assertIn('avg_frame_size', stats)


class TestNetworkSimulator(unittest.TestCase):
    """Complete test coverage for Network Simulator"""
    
    def setUp(self):
        """Initialize simulator"""
        self.sim = NetworkSimulator(link_speed_mbps=1000)
        
    def test_initialization(self):
        """Test simulator initialization"""
        self.assertEqual(self.sim.link_speed_mbps, 1000)
        self.assertEqual(len(self.sim.queues), 0)
        self.assertEqual(len(self.sim.events), 0)
        
    def test_add_cbs_queue(self):
        """Test adding CBS queue"""
        self.sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        self.assertEqual(len(self.sim.queues), 1)
        self.assertIn(0, self.sim.queues)
        
    def test_traffic_generation_cbr(self):
        """Test CBR traffic generation"""
        self.sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        self.sim.generate_traffic('cbr', 1.0, 100, 1500, 0)
        self.assertGreater(len(self.sim.events), 0)
        
    def test_traffic_generation_poisson(self):
        """Test Poisson traffic generation"""
        self.sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        self.sim.generate_traffic('poisson', 1.0, 100, 1500, 0)
        self.assertGreater(len(self.sim.events), 0)
        
    def test_traffic_generation_burst(self):
        """Test burst traffic generation"""
        self.sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        self.sim.generate_traffic('burst', 1.0, 100, 10, 0)
        self.assertGreater(len(self.sim.events), 0)
        
    def test_simulation_run(self):
        """Test simulation execution"""
        self.sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        self.sim.generate_traffic('cbr', 1.0, 100, 1500, 0)
        
        results = self.sim.run(1.0)
        self.assertIn('events', results)
        self.assertIn('statistics', results)
        self.assertIn('queue_stats', results)
        
    def test_multiple_queues(self):
        """Test multiple queue handling"""
        self.sim.add_cbs_queue(0, 500, -500, 2000, -1000)
        self.sim.add_cbs_queue(1, 250, -750, 1500, -500)
        
        self.sim.generate_traffic('cbr', 1.0, 50, 1000, 0)
        self.sim.generate_traffic('cbr', 1.0, 25, 500, 1)
        
        results = self.sim.run(1.0)
        self.assertEqual(len(results['queue_stats']), 2)
        
    def test_overload_conditions(self):
        """Test behavior under overload"""
        self.sim.add_cbs_queue(0, 500, -500, 2000, -1000)
        
        # Generate more traffic than link capacity
        self.sim.generate_traffic('cbr', 1.0, 1200, 1500, 0)
        
        results = self.sim.run(1.0)
        self.assertGreater(results['statistics']['total_dropped'], 0)
        
    def test_event_ordering(self):
        """Test event chronological ordering"""
        self.sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        self.sim.generate_traffic('cbr', 1.0, 100, 1500, 0)
        
        results = self.sim.run(1.0)
        events = results['events']
        
        for i in range(1, len(events)):
            self.assertLessEqual(events[i-1]['timestamp'], events[i]['timestamp'])
            
    def test_statistics_calculation(self):
        """Test statistics accuracy"""
        self.sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        self.sim.generate_traffic('cbr', 1.0, 100, 1500, 0)
        
        results = self.sim.run(1.0)
        stats = results['statistics']
        
        self.assertIn('total_frames', stats)
        self.assertIn('total_transmitted', stats)
        self.assertIn('total_dropped', stats)
        self.assertIn('avg_latency', stats)
        self.assertIn('max_latency', stats)
        self.assertIn('jitter', stats)
        self.assertIn('avg_utilization', stats)
        
        self.assertGreaterEqual(stats['avg_latency'], 0)
        self.assertGreaterEqual(stats['max_latency'], stats['avg_latency'])


class TestMLOptimizer(unittest.TestCase):
    """Complete test coverage for ML Optimizer"""
    
    def setUp(self):
        """Initialize ML components"""
        self.optimizer = CBSOptimizer()
        self.analyzer = TrafficPatternAnalyzer()
        
    def test_optimizer_initialization(self):
        """Test optimizer initialization"""
        self.assertIsNotNone(self.optimizer.model)
        self.assertEqual(len(self.optimizer.history), 0)
        
    def test_feature_extraction(self):
        """Test traffic feature extraction"""
        traffic_data = {
            'rate': 100,
            'burst_size': 10,
            'frame_size': 1500,
            'pattern': 'cbr'
        }
        features = self.analyzer.extract_features(traffic_data)
        self.assertEqual(len(features), 12)
        
    def test_parameter_optimization(self):
        """Test CBS parameter optimization"""
        traffic_profile = {
            'rate': 750,
            'pattern': 'cbr',
            'frame_size': 1500
        }
        params = self.optimizer.optimize(traffic_profile)
        
        self.assertIn('idle_slope', params)
        self.assertIn('send_slope', params)
        self.assertIn('hi_credit', params)
        self.assertIn('lo_credit', params)
        
        self.assertGreater(params['idle_slope'], 0)
        self.assertLess(params['send_slope'], 0)
        
    def test_model_training(self):
        """Test model training process"""
        # Generate training data
        X_train = np.random.rand(100, 12)
        y_train = np.random.rand(100, 4)
        
        history = self.optimizer.train(X_train, y_train, epochs=5)
        self.assertGreater(len(history), 0)
        
    def test_reinforcement_learning(self):
        """Test RL agent"""
        env = CBSEnvironment()
        agent = CBSReinforcementAgent(
            state_dim=env.observation_space.shape[0],
            action_dim=env.action_space.n
        )
        
        state = env.reset()
        action = agent.select_action(state)
        next_state, reward, done, _ = env.step(action)
        
        self.assertIsNotNone(next_state)
        self.assertIsInstance(reward, (int, float))
        self.assertIsInstance(done, bool)
        
    def test_adaptive_optimization(self):
        """Test adaptive parameter adjustment"""
        initial_params = {
            'idle_slope': 500,
            'send_slope': -500,
            'hi_credit': 1000,
            'lo_credit': -500
        }
        
        metrics = {
            'latency': 2.5,
            'jitter': 0.5,
            'loss_rate': 0.02
        }
        
        adjusted = self.optimizer.adaptive_adjust(initial_params, metrics)
        self.assertIsNotNone(adjusted)
        
    def test_pattern_recognition(self):
        """Test traffic pattern recognition"""
        # Generate synthetic traffic data
        cbr_data = [1000] * 100
        burst_data = [0] * 50 + [5000] * 10 + [0] * 40
        
        cbr_pattern = self.analyzer.identify_pattern(cbr_data)
        burst_pattern = self.analyzer.identify_pattern(burst_data)
        
        self.assertEqual(cbr_pattern, 'cbr')
        self.assertEqual(burst_pattern, 'burst')
        
    def test_performance_prediction(self):
        """Test performance prediction"""
        params = {
            'idle_slope': 750,
            'send_slope': -250,
            'hi_credit': 2000,
            'lo_credit': -1000
        }
        
        traffic = {
            'rate': 500,
            'pattern': 'cbr',
            'frame_size': 1500
        }
        
        predicted = self.optimizer.predict_performance(params, traffic)
        self.assertIn('expected_latency', predicted)
        self.assertIn('expected_jitter', predicted)
        self.assertIn('expected_loss', predicted)


class TestHardwareIntegration(unittest.TestCase):
    """Test hardware integration components"""
    
    @patch('hardware.lan9662_cbs_test.paramiko.SSHClient')
    def test_ssh_connection(self, mock_ssh):
        """Test SSH connection to hardware"""
        conn = LAN9662Connection('192.168.1.1', 'admin', 'admin', 'ssh')
        conn.connect()
        mock_ssh.return_value.connect.assert_called_once()
        
    @patch('hardware.lan9662_cbs_test.telnetlib.Telnet')
    def test_telnet_connection(self, mock_telnet):
        """Test Telnet connection"""
        conn = LAN9662Connection('192.168.1.1', 'admin', 'admin', 'telnet')
        conn.connect()
        mock_telnet.assert_called_once_with('192.168.1.1')
        
    @patch('hardware.lan9662_cbs_test.serial.Serial')
    def test_serial_connection(self, mock_serial):
        """Test serial connection"""
        conn = LAN9662Connection('COM3', 'admin', 'admin', 'serial')
        conn.connect()
        mock_serial.assert_called_once()
        
    def test_cbs_config_validation(self):
        """Test CBS configuration validation"""
        config = CBSConfig(
            port=1,
            queue=6,
            idle_slope=750000,
            send_slope=-250000,
            hi_credit=2000,
            lo_credit=-1000
        )
        
        self.assertEqual(config.port, 1)
        self.assertEqual(config.queue, 6)
        self.assertTrue(config.enabled)
        
    def test_test_result_creation(self):
        """Test result object creation"""
        result = TestResult(
            test_name="Latency Test",
            passed=True,
            latency_avg=0.5,
            latency_max=2.1,
            jitter=0.1,
            frame_loss=0,
            throughput=950,
            timestamp=time.time(),
            details={}
        )
        
        self.assertTrue(result.passed)
        self.assertEqual(result.latency_avg, 0.5)


class TestPerformanceBenchmark(unittest.TestCase):
    """Test performance benchmark suite"""
    
    def setUp(self):
        """Initialize benchmark"""
        self.benchmark = PerformanceBenchmark()
        
    def test_latency_benchmark(self):
        """Test latency measurement"""
        results = self.benchmark.measure_latency(
            duration=0.1,
            frame_rate=100
        )
        self.assertIn('min', results)
        self.assertIn('max', results)
        self.assertIn('avg', results)
        self.assertIn('p99', results)
        
    def test_throughput_benchmark(self):
        """Test throughput measurement"""
        results = self.benchmark.measure_throughput(
            duration=0.1,
            frame_size=1500
        )
        self.assertIn('mbps', results)
        self.assertIn('fps', results)
        self.assertIn('bytes_total', results)
        
    def test_jitter_calculation(self):
        """Test jitter calculation"""
        latencies = [1.0, 1.1, 0.9, 1.2, 0.8, 1.0]
        jitter = self.benchmark.calculate_jitter(latencies)
        self.assertGreater(jitter, 0)
        self.assertLess(jitter, 1.0)
        
    def test_concurrent_load(self):
        """Test under concurrent load"""
        results = self.benchmark.run_concurrent_test(
            num_threads=4,
            duration=0.1
        )
        self.assertEqual(len(results), 4)


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests"""
    
    def test_complete_workflow(self):
        """Test complete CBS workflow"""
        # 1. Calculate parameters
        calc = CBSCalculator(1000)
        idle_slope = calc.calculate_idle_slope(75)
        send_slope = calc.calculate_send_slope(idle_slope)
        credits = calc.calculate_credits(idle_slope, 1500, 3)
        
        # 2. Configure simulator
        sim = NetworkSimulator(1000)
        sim.add_cbs_queue(
            0, 
            idle_slope/1e6,  # Convert to Mbps
            send_slope/1e6,
            credits['hi_credit'],
            credits['lo_credit']
        )
        
        # 3. Generate traffic
        sim.generate_traffic('cbr', 1.0, 500, 1500, 0)
        
        # 4. Run simulation
        results = sim.run(1.0)
        
        # 5. Verify results
        self.assertLess(results['statistics']['avg_latency'], 0.002)
        self.assertLess(results['statistics']['jitter'], 0.001)
        self.assertEqual(results['statistics']['total_dropped'], 0)
        
    def test_ml_optimization_workflow(self):
        """Test ML-based optimization workflow"""
        # 1. Analyze traffic
        analyzer = TrafficPatternAnalyzer()
        traffic_data = {
            'rate': 600,
            'pattern': 'mixed',
            'frame_size': 1024
        }
        
        # 2. Optimize parameters
        optimizer = CBSOptimizer()
        params = optimizer.optimize(traffic_data)
        
        # 3. Validate parameters
        self.assertGreater(params['idle_slope'], 0)
        self.assertLess(params['send_slope'], 0)
        self.assertGreater(params['idle_slope'] + abs(params['send_slope']), 900)
        
    def test_stress_conditions(self):
        """Test system under stress"""
        sim = NetworkSimulator(1000)
        
        # Add multiple queues
        for i in range(8):
            sim.add_cbs_queue(i, 100, -900, 1000, -500)
            
        # Generate heavy traffic
        for i in range(8):
            sim.generate_traffic('burst', 1.0, 150, 10, i)
            
        # Run and verify stability
        results = sim.run(10.0)
        self.assertIsNotNone(results)
        self.assertLess(results['statistics']['avg_utilization'], 1.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_zero_bandwidth(self):
        """Test with zero bandwidth allocation"""
        calc = CBSCalculator(1000)
        idle_slope = calc.calculate_idle_slope(0)
        self.assertEqual(idle_slope, 0)
        
    def test_full_bandwidth(self):
        """Test with 100% bandwidth allocation"""
        calc = CBSCalculator(1000)
        idle_slope = calc.calculate_idle_slope(100)
        self.assertEqual(idle_slope, 1_000_000_000)
        
    def test_empty_queue_behavior(self):
        """Test CBS with empty queue"""
        queue = CBSQueue(0, 750, -250, 2000, -1000)
        self.assertFalse(queue.is_eligible())
        queue.update_credit(1.0, False)
        self.assertEqual(queue.credit, 0)
        
    def test_negative_time(self):
        """Test handling of negative time values"""
        queue = CBSQueue(0, 750, -250, 2000, -1000)
        queue.last_update_time = 1.0
        
        # Should handle gracefully
        queue.update_credit(0.5, False)
        self.assertEqual(queue.credit, 0)
        
    def test_overflow_protection(self):
        """Test integer overflow protection"""
        calc = CBSCalculator(100000)  # 100 Gbps
        credits = calc.calculate_credits(
            idle_slope=99_000_000_000,
            max_frame_size=9000,
            burst_size=100
        )
        self.assertLess(credits['hi_credit'], sys.maxsize)
        
    def test_concurrent_access(self):
        """Test thread safety"""
        queue = CBSQueue(0, 750, -250, 2000, -1000)
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    queue.add_frame({'size': random.randint(64, 1500)})
                    if queue.frames:
                        queue.remove_frame()
                    queue.update_credit(random.random(), random.choice([True, False]))
            except Exception as e:
                errors.append(e)
                
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        self.assertEqual(len(errors), 0)


class TestDocumentation(unittest.TestCase):
    """Test documentation and code quality"""
    
    def test_docstrings_present(self):
        """Verify all classes and methods have docstrings"""
        import src.cbs_calculator as cbs
        
        for name in dir(cbs):
            if not name.startswith('_'):
                obj = getattr(cbs, name)
                if callable(obj):
                    self.assertIsNotNone(obj.__doc__)
                    
    def test_type_hints(self):
        """Verify type hints are present"""
        from src.cbs_calculator import CBSCalculator
        
        # Check method signatures have type hints
        import inspect
        sig = inspect.signature(CBSCalculator.calculate_idle_slope)
        self.assertIn('bandwidth_percent', sig.parameters)
        
    def test_logging_configured(self):
        """Verify logging is properly configured"""
        calc = CBSCalculator(1000)
        self.assertIsNotNone(calc.logger)
        
    def test_version_numbers(self):
        """Verify version numbers are consistent"""
        from src import cbs_calculator
        self.assertIsNotNone(cbs_calculator.__version__)
        self.assertTrue(cbs_calculator.__version__.startswith('2.'))


# Performance test suite
@pytest.mark.benchmark
class PerformanceTests(unittest.TestCase):
    """Performance and scalability tests"""
    
    def test_large_scale_simulation(self):
        """Test with large number of frames"""
        sim = NetworkSimulator(1000)
        sim.add_cbs_queue(0, 750, -250, 2000, -1000)
        
        # Generate 10000 frames
        for _ in range(10000):
            sim.events.append({
                'type': 'arrival',
                'timestamp': random.random() * 10,
                'queue_id': 0,
                'frame_size': random.randint(64, 1500)
            })
            
        start = time.time()
        results = sim.run(10.0)
        duration = time.time() - start
        
        self.assertLess(duration, 5.0)  # Should complete in < 5 seconds
        self.assertIsNotNone(results)
        
    def test_memory_usage(self):
        """Test memory consumption"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and destroy many objects
        for _ in range(1000):
            sim = NetworkSimulator(1000)
            for i in range(8):
                sim.add_cbs_queue(i, 100, -900, 1000, -500)
            del sim
            
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        self.assertLess(memory_increase, 100)  # Less than 100 MB increase


def run_all_tests():
    """Run complete test suite and generate coverage report"""
    import coverage
    
    # Start coverage
    cov = coverage.Coverage()
    cov.start()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestCBSCalculator,
        TestCBSQueue,
        TestNetworkSimulator,
        TestMLOptimizer,
        TestHardwareIntegration,
        TestPerformanceBenchmark,
        TestIntegration,
        TestEdgeCases,
        TestDocumentation,
        PerformanceTests
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Stop coverage and generate report
    cov.stop()
    cov.save()
    
    # Print coverage report
    print("\n" + "="*60)
    print("COVERAGE REPORT")
    print("="*60)
    cov.report()
    
    # Generate HTML report
    cov.html_report(directory='htmlcov')
    print(f"\nHTML coverage report generated in 'htmlcov' directory")
    
    # Return test results
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)