#!/usr/bin/env python3
"""
Comprehensive Test Suite for CBS Calculator
Tests for CBS parameter calculations, validation, and optimization
"""

import pytest
import sys
import os
from pathlib import Path
import json
import yaml
import tempfile
import numpy as np
from unittest.mock import patch, mock_open

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cbs_calculator import (
    CBSCalculator, CBSParameters, StreamConfig, TrafficType
)

class TestCBSCalculator:
    """Test suite for CBS Calculator functionality"""
    
    @pytest.fixture
    def calculator(self):
        """Create CBS calculator instance for testing"""
        return CBSCalculator(link_speed_mbps=1000)
    
    @pytest.fixture
    def sample_stream(self):
        """Create sample stream configuration"""
        return StreamConfig(
            name="test_video",
            traffic_type=TrafficType.VIDEO_1080P,
            bitrate_mbps=15.0,
            fps=30,
            resolution="1920x1080",
            priority=5,
            max_latency_ms=30.0,
            max_jitter_ms=5.0
        )
    
    @pytest.fixture
    def multi_streams(self):
        """Create multiple stream configurations"""
        return [
            StreamConfig("safety_critical", TrafficType.SAFETY_CRITICAL, 2.0, 100, "N/A", 7, 5.0, 0.5),
            StreamConfig("front_4k", TrafficType.VIDEO_4K, 25.0, 60, "3840x2160", 6, 20.0, 3.0),
            StreamConfig("surround_hd", TrafficType.VIDEO_1080P, 15.0, 30, "1920x1080", 5, 30.0, 5.0),
            StreamConfig("lidar", TrafficType.LIDAR, 100.0, 10, "N/A", 4, 40.0, 4.0),
            StreamConfig("v2x", TrafficType.V2X, 10.0, 10, "N/A", 2, 100.0, 10.0),
        ]
    
    def test_calculator_initialization(self):
        """Test CBS calculator initialization"""
        calc = CBSCalculator()
        assert calc.link_speed_mbps == 1000
        assert calc.link_speed_bps == 1_000_000_000
        
        calc_custom = CBSCalculator(link_speed_mbps=100)
        assert calc_custom.link_speed_mbps == 100
        assert calc_custom.link_speed_bps == 100_000_000
    
    def test_basic_cbs_calculation(self, calculator, sample_stream):
        """Test basic CBS parameter calculation"""
        params = calculator.calculate_cbs_params(sample_stream)
        
        assert isinstance(params, CBSParameters)
        assert params.idle_slope > 0
        assert params.send_slope < 0
        assert params.hi_credit > 0
        assert params.lo_credit < 0
        assert params.reserved_bandwidth_mbps >= sample_stream.bitrate_mbps
        assert params.actual_bandwidth_mbps == sample_stream.bitrate_mbps
        assert 0 < params.efficiency_percent <= 100
    
    def test_cbs_parameter_ranges(self, calculator, sample_stream):
        """Test CBS parameters are within expected ranges"""
        params = calculator.calculate_cbs_params(sample_stream)
        
        # idleSlope should be bitrate with headroom
        expected_min_idle = sample_stream.bitrate_mbps * 1_000_000 * 1.05  # At least 5% headroom
        assert params.idle_slope >= expected_min_idle
        
        # sendSlope should be negative and equal to idleSlope - linkSpeed
        assert params.send_slope == params.idle_slope - calculator.link_speed_bps
        
        # Credits should be proportional to max frame size and slopes
        assert abs(params.lo_credit) == params.hi_credit
    
    def test_traffic_type_defaults(self, calculator):
        """Test traffic type specific default parameters"""
        # Test safety critical stream
        safety_stream = StreamConfig("safety", TrafficType.SAFETY_CRITICAL, 1.0, 100, "N/A", 7, 5, 0.5)
        safety_params = calculator.calculate_cbs_params(safety_stream)
        
        # Safety critical should have high headroom (100%)
        assert safety_params.reserved_bandwidth_mbps >= safety_stream.bitrate_mbps * 1.8
        
        # Test video stream
        video_stream = StreamConfig("video", TrafficType.VIDEO_1080P, 15.0, 30, "1920x1080", 5, 30, 5)
        video_params = calculator.calculate_cbs_params(video_stream)
        
        # Video should have moderate headroom (25%)
        expected_video_reserved = video_stream.bitrate_mbps * 1.25
        assert abs(video_params.reserved_bandwidth_mbps - expected_video_reserved) < 0.1
    
    def test_custom_headroom(self, calculator, sample_stream):
        """Test custom headroom parameter"""
        params_default = calculator.calculate_cbs_params(sample_stream)
        params_custom = calculator.calculate_cbs_params(sample_stream, custom_headroom=50)
        
        # Custom headroom should result in different reserved bandwidth
        assert params_custom.reserved_bandwidth_mbps != params_default.reserved_bandwidth_mbps
        
        # With 50% headroom, reserved should be 1.5x actual
        expected_reserved = sample_stream.bitrate_mbps * 1.5
        assert abs(params_custom.reserved_bandwidth_mbps - expected_reserved) < 0.1
    
    def test_multi_stream_calculation(self, calculator, multi_streams):
        """Test multi-stream CBS calculation"""
        results = calculator.calculate_multi_stream(multi_streams)
        
        assert len(results) == len(multi_streams)
        
        # Check that all streams have parameters
        for stream in multi_streams:
            assert stream.name in results
            assert isinstance(results[stream.name], CBSParameters)
        
        # Check priority ordering (higher priority processed first)
        stream_names = list(results.keys())
        priorities = [next(s.priority for s in multi_streams if s.name == name) for name in stream_names]
        
        # Verify streams are processed in priority order
        for i in range(len(priorities) - 1):
            assert priorities[i] >= priorities[i + 1]
    
    def test_bandwidth_limits(self, calculator):
        """Test bandwidth limit warnings and constraints"""
        # Create streams that exceed link capacity
        high_bandwidth_streams = [
            StreamConfig("stream1", TrafficType.VIDEO_4K, 400.0, 60, "4K", 6, 20, 3),
            StreamConfig("stream2", TrafficType.VIDEO_4K, 400.0, 60, "4K", 5, 20, 3),
            StreamConfig("stream3", TrafficType.VIDEO_4K, 400.0, 60, "4K", 4, 20, 3),
        ]
        
        # Should still calculate parameters but log warnings
        with patch('builtins.print') as mock_print:
            results = calculator.calculate_multi_stream(high_bandwidth_streams)
            
            # Verify warnings were printed
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            warning_messages = [msg for msg in print_calls if "경고" in str(msg)]
            assert len(warning_messages) > 0
        
        # Verify all streams still have parameters
        assert len(results) == len(high_bandwidth_streams)
    
    def test_optimization(self, calculator, multi_streams):
        """Test CBS parameter optimization"""
        # Test optimization with different target utilizations
        optimized_75 = calculator.optimize_parameters(multi_streams, target_utilization=75)
        optimized_60 = calculator.optimize_parameters(multi_streams, target_utilization=60)
        
        # Calculate total reserved bandwidth for each
        total_75 = sum(p.reserved_bandwidth_mbps for p in optimized_75.values())
        total_60 = sum(p.reserved_bandwidth_mbps for p in optimized_60.values())
        
        # Lower target utilization should result in lower total reserved bandwidth
        assert total_60 <= total_75
        
        # Both should be within reasonable bounds
        utilization_75 = (total_75 / calculator.link_speed_mbps) * 100
        utilization_60 = (total_60 / calculator.link_speed_mbps) * 100
        
        assert utilization_75 <= 80  # Should be close to target
        assert utilization_60 <= 65  # Should be close to target
    
    def test_validation(self, calculator, multi_streams):
        """Test CBS configuration validation"""
        params = calculator.calculate_multi_stream(multi_streams)
        warnings = calculator.validate_configuration(params)
        
        assert isinstance(warnings, list)
        
        # Test with problematic configuration
        problematic_stream = StreamConfig("problematic", TrafficType.VIDEO_4K, 600.0, 60, "4K", 6, 20, 3)
        problematic_params = calculator.calculate_cbs_params(problematic_stream)
        problematic_warnings = calculator.validate_configuration({"problematic": problematic_params})
        
        # Should generate warnings for high bandwidth usage
        assert len(problematic_warnings) > 0
    
    def test_config_file_generation(self, calculator, multi_streams):
        """Test YAML configuration file generation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            calculator.generate_config_file(multi_streams, temp_path)
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify YAML structure
            with open(temp_path, 'r') as f:
                config = yaml.safe_load(f)
            
            assert 'cbs-configuration' in config
            assert 'link-speed-mbps' in config['cbs-configuration']
            assert 'streams' in config['cbs-configuration']
            assert len(config['cbs-configuration']['streams']) == len(multi_streams)
            
            # Verify stream parameters
            for stream_config in config['cbs-configuration']['streams']:
                assert 'name' in stream_config
                assert 'cbs-parameters' in stream_config
                cbs_params = stream_config['cbs-parameters']
                assert 'idle-slope' in cbs_params
                assert 'send-slope' in cbs_params
                assert 'hi-credit' in cbs_params
                assert 'lo-credit' in cbs_params
        
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_edge_cases(self, calculator):
        """Test edge cases and error conditions"""
        # Test with zero bitrate
        zero_stream = StreamConfig("zero", TrafficType.VIDEO_1080P, 0.0, 30, "1080p", 5, 30, 5)
        params = calculator.calculate_cbs_params(zero_stream)
        assert params.idle_slope > 0  # Should still have minimum reservation
        
        # Test with very high bitrate
        high_stream = StreamConfig("high", TrafficType.VIDEO_4K, 999.0, 60, "4K", 6, 20, 3)
        params = calculator.calculate_cbs_params(high_stream)
        assert params.idle_slope < calculator.link_speed_bps  # Should not exceed link speed
    
    def test_parameter_consistency(self, calculator, sample_stream):
        """Test parameter consistency and relationships"""
        params = calculator.calculate_cbs_params(sample_stream)
        
        # Test fundamental CBS relationships
        assert params.send_slope == params.idle_slope - calculator.link_speed_bps
        assert params.lo_credit == -params.hi_credit
        
        # Test bandwidth relationships
        assert params.reserved_bandwidth_mbps >= params.actual_bandwidth_mbps
        efficiency = (params.actual_bandwidth_mbps / params.reserved_bandwidth_mbps) * 100
        assert abs(efficiency - params.efficiency_percent) < 0.1
    
    @pytest.mark.parametrize("link_speed", [100, 1000, 10000])
    def test_different_link_speeds(self, link_speed, sample_stream):
        """Test CBS calculation with different link speeds"""
        calc = CBSCalculator(link_speed_mbps=link_speed)
        params = calc.calculate_cbs_params(sample_stream)
        
        # sendSlope should scale with link speed
        assert params.send_slope == params.idle_slope - (link_speed * 1_000_000)
        
        # Credits should scale appropriately
        assert params.hi_credit > 0
        assert params.lo_credit < 0
    
    @pytest.mark.parametrize("traffic_type", list(TrafficType))
    def test_all_traffic_types(self, calculator, traffic_type):
        """Test CBS calculation for all traffic types"""
        stream = StreamConfig(
            name=f"test_{traffic_type.value}",
            traffic_type=traffic_type,
            bitrate_mbps=10.0,
            fps=30,
            resolution="test",
            priority=3,
            max_latency_ms=50.0,
            max_jitter_ms=10.0
        )
        
        params = calculator.calculate_cbs_params(stream)
        
        # Basic validations for all traffic types
        assert params.idle_slope > 0
        assert params.send_slope < 0
        assert params.reserved_bandwidth_mbps >= stream.bitrate_mbps
        assert 0 < params.efficiency_percent <= 100

class TestCBSParametersDataClass:
    """Test CBS Parameters data class"""
    
    def test_cbs_parameters_creation(self):
        """Test CBS parameters object creation"""
        params = CBSParameters(
            idle_slope=20_000_000,
            send_slope=-980_000_000,
            hi_credit=243,
            lo_credit=-243,
            reserved_bandwidth_mbps=20.0,
            actual_bandwidth_mbps=15.0,
            efficiency_percent=75.0
        )
        
        assert params.idle_slope == 20_000_000
        assert params.send_slope == -980_000_000
        assert params.hi_credit == 243
        assert params.lo_credit == -243
        assert params.reserved_bandwidth_mbps == 20.0
        assert params.actual_bandwidth_mbps == 15.0
        assert params.efficiency_percent == 75.0

class TestStreamConfigDataClass:
    """Test Stream Configuration data class"""
    
    def test_stream_config_creation(self):
        """Test stream configuration creation"""
        stream = StreamConfig(
            name="test_stream",
            traffic_type=TrafficType.VIDEO_1080P,
            bitrate_mbps=15.0,
            fps=30,
            resolution="1920x1080",
            priority=5,
            max_latency_ms=30.0,
            max_jitter_ms=5.0
        )
        
        assert stream.name == "test_stream"
        assert stream.traffic_type == TrafficType.VIDEO_1080P
        assert stream.bitrate_mbps == 15.0
        assert stream.fps == 30
        assert stream.resolution == "1920x1080"
        assert stream.priority == 5
        assert stream.max_latency_ms == 30.0
        assert stream.max_jitter_ms == 5.0

class TestAutonomousVehicleExample:
    """Test the autonomous vehicle example function"""
    
    @patch('builtins.print')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_autonomous_vehicle_example(self, mock_yaml_dump, mock_file, mock_print):
        """Test autonomous vehicle example execution"""
        from cbs_calculator import example_autonomous_vehicle
        
        # Should run without errors
        example_autonomous_vehicle()
        
        # Verify output was generated
        assert mock_print.called
        assert mock_file.called
        assert mock_yaml_dump.called
        
        # Check that relevant information was printed
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        printed_text = ' '.join(str(call) for call in print_calls)
        
        assert "자율주행" in printed_text or "CBS" in printed_text

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])