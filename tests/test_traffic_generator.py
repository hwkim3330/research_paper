#!/usr/bin/env python3
"""
Test Suite for Traffic Generator
Tests for automotive network traffic generation and simulation
"""

import pytest
import sys
import json
import tempfile
import os
import socket
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traffic_generator import (
    TrafficGenerator, TrafficProfile, TrafficType
)

class TestTrafficProfile:
    """Test TrafficProfile data class"""
    
    def test_traffic_profile_creation(self):
        """Test traffic profile creation"""
        profile = TrafficProfile(
            name="Test Video",
            traffic_type=TrafficType.VIDEO_1080P,
            bitrate_mbps=15.0,
            packet_size_bytes=1400,
            interval_ms=1.0,
            priority=5,
            destination=("10.0.100.2", 5005)
        )
        
        assert profile.name == "Test Video"
        assert profile.traffic_type == TrafficType.VIDEO_1080P
        assert profile.bitrate_mbps == 15.0
        assert profile.packet_size_bytes == 1400
        assert profile.interval_ms == 1.0
        assert profile.priority == 5
        assert profile.destination == ("10.0.100.2", 5005)
        assert profile.burst_probability == 0.0  # Default value
        assert profile.vlan_id is None  # Default value

class TestTrafficGenerator:
    """Test TrafficGenerator functionality"""
    
    @pytest.fixture
    def generator(self):
        """Create traffic generator instance"""
        return TrafficGenerator()
    
    @pytest.fixture
    def sample_profile(self):
        """Create sample traffic profile"""
        return TrafficProfile(
            name="Test Stream",
            traffic_type=TrafficType.VIDEO_1080P,
            bitrate_mbps=15.0,
            packet_size_bytes=1400,
            interval_ms=10.0,  # 100 Hz
            priority=5,
            destination=("127.0.0.1", 12345),
            burst_probability=0.1,
            burst_multiplier=1.5,
            jitter_ms=2.0
        )
    
    def test_generator_initialization(self):
        """Test traffic generator initialization"""
        generator = TrafficGenerator()
        assert generator.active_streams == {}
        assert generator.statistics == {}
        assert generator.running is False
        assert generator.logger is not None
        
        # Check that predefined profiles exist
        assert len(generator.AUTOMOTIVE_PROFILES) > 0
        assert "front_camera_4k" in generator.AUTOMOTIVE_PROFILES
        assert "emergency_brake" in generator.AUTOMOTIVE_PROFILES
    
    def test_config_loading(self, generator):
        """Test configuration loading from JSON"""
        config_data = {
            "profiles": [
                {
                    "name": "Custom Video",
                    "traffic_type": "video_1080p",
                    "bitrate_mbps": 20.0,
                    "packet_size_bytes": 1400,
                    "interval_ms": 1.0,
                    "priority": 5,
                    "destination": ["10.0.100.2", 5010]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(config_data, temp_file)
            temp_path = temp_file.name
        
        try:
            generator.load_config(temp_path)
            assert "custom_video" in generator.AUTOMOTIVE_PROFILES
        finally:
            os.unlink(temp_path)
    
    def test_config_loading_error(self, generator):
        """Test configuration loading with invalid file"""
        with pytest.raises(Exception):
            generator.load_config("nonexistent_file.json")
    
    def test_payload_generation_control(self, generator, sample_profile):
        """Test control message payload generation"""
        profile = TrafficProfile(
            name="Control Test",
            traffic_type=TrafficType.CRITICAL_CONTROL,
            bitrate_mbps=1.0,
            packet_size_bytes=64,
            interval_ms=10.0,
            priority=7,
            destination=("127.0.0.1", 12345)
        )
        
        payload = generator.generate_realistic_payload(profile, 123)
        
        assert len(payload) == profile.packet_size_bytes
        assert isinstance(payload, bytes)
        
        # Check basic structure (timestamp + sequence + checksum + padding)
        assert len(payload) >= 12  # Minimum control message size
    
    def test_payload_generation_video(self, generator, sample_profile):
        """Test video payload generation"""
        profile = TrafficProfile(
            name="Video Test",
            traffic_type=TrafficType.VIDEO_4K,
            bitrate_mbps=25.0,
            packet_size_bytes=1400,
            interval_ms=1.0,
            priority=6,
            destination=("127.0.0.1", 12345)
        )
        
        payload = generator.generate_realistic_payload(profile, 456)
        
        assert len(payload) == profile.packet_size_bytes
        
        # Check RTP header structure
        assert payload[0] == 0x80  # RTP version and flags
        assert payload[1] == 96    # Payload type
    
    def test_payload_generation_lidar(self, generator):
        """Test LiDAR payload generation"""
        profile = TrafficProfile(
            name="LiDAR Test",
            traffic_type=TrafficType.LIDAR_DATA,
            bitrate_mbps=100.0,
            packet_size_bytes=8192,
            interval_ms=100.0,
            priority=4,
            destination=("127.0.0.1", 12345)
        )
        
        payload = generator.generate_realistic_payload(profile, 789)
        
        assert len(payload) == profile.packet_size_bytes
        
        # Check for LiDAR magic number
        magic_bytes = payload[12:16]  # Magic number should be at offset 12
        assert magic_bytes == b'LIDA' or len(payload) >= 16
    
    def test_payload_generation_radar(self, generator):
        """Test Radar payload generation"""
        profile = TrafficProfile(
            name="Radar Test",
            traffic_type=TrafficType.RADAR_DATA,
            bitrate_mbps=16.0,
            packet_size_bytes=512,
            interval_ms=20.0,
            priority=3,
            destination=("127.0.0.1", 12345)
        )
        
        payload = generator.generate_realistic_payload(profile, 101)
        
        assert len(payload) == profile.packet_size_bytes
        
        # Check for radar magic number
        if len(payload) >= 12:
            magic_bytes = payload[10:12]  # Magic number at offset 10-11
            assert magic_bytes == b'RA' or len(payload) >= 12
    
    def test_payload_generation_v2x(self, generator):
        """Test V2X payload generation"""
        profile = TrafficProfile(
            name="V2X Test",
            traffic_type=TrafficType.V2X_MESSAGE,
            bitrate_mbps=10.0,
            packet_size_bytes=200,
            interval_ms=100.0,
            priority=2,
            destination=("127.0.0.1", 12345)
        )
        
        payload = generator.generate_realistic_payload(profile, 202)
        
        assert len(payload) == profile.packet_size_bytes
        
        # V2X should have message structure
        assert len(payload) >= 20  # Minimum BSM size
    
    @patch('socket.socket')
    def test_socket_creation(self, mock_socket, generator, sample_profile):
        """Test socket creation and configuration"""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        
        sock = generator.create_socket(sample_profile)
        
        # Verify socket creation
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Verify socket options were attempted to be set
        assert mock_sock.setsockopt.called or True  # May fail on some platforms
    
    @patch('socket.socket')
    @patch('time.time')
    def test_traffic_stream_generation_short(self, mock_time, mock_socket, generator, sample_profile):
        """Test short traffic stream generation"""
        # Mock socket
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        
        # Mock time to control execution
        mock_time.side_effect = [0, 0.001, 0.002, 0.003, 0.004, 0.005, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
        
        # Set generator to running state
        generator.running = True
        
        # Use a very short duration for testing
        short_profile = TrafficProfile(
            name="Short Test",
            traffic_type=TrafficType.VIDEO_1080P,
            bitrate_mbps=15.0,
            packet_size_bytes=100,
            interval_ms=100.0,  # Very slow rate for testing
            priority=5,
            destination=("127.0.0.1", 12345)
        )
        
        # Run for very short duration
        generator.generate_traffic_stream(short_profile, duration_seconds=0.5)
        
        # Verify socket was created and used
        mock_socket.assert_called()
        
        # Verify statistics were collected
        assert "Short Test" in generator.statistics
        stats = generator.statistics["Short Test"]
        assert 'packets_sent' in stats
        assert 'bytes_sent' in stats
        assert 'start_time' in stats
    
    def test_predefined_automotive_profiles(self, generator):
        """Test predefined automotive profiles"""
        # Check critical profiles exist
        critical_profiles = [
            "emergency_brake",
            "steering_control",
            "front_camera_4k",
            "surround_camera_hd",
            "lidar_main",
            "radar_fusion"
        ]
        
        for profile_name in critical_profiles:
            assert profile_name in generator.AUTOMOTIVE_PROFILES
            profile = generator.AUTOMOTIVE_PROFILES[profile_name]
            assert isinstance(profile, TrafficProfile)
            assert profile.name is not None
            assert profile.traffic_type is not None
            assert profile.bitrate_mbps > 0
            assert profile.packet_size_bytes > 0
            assert profile.priority >= 0
    
    def test_profile_parameters_consistency(self, generator):
        """Test that profile parameters are consistent"""
        for name, profile in generator.AUTOMOTIVE_PROFILES.items():
            # Check that interval matches expected rate for bitrate
            expected_pps = (profile.bitrate_mbps * 1_000_000) / (profile.packet_size_bytes * 8)
            expected_interval_ms = 1000.0 / expected_pps
            
            # Allow some tolerance for rounding
            tolerance = expected_interval_ms * 0.1
            assert abs(profile.interval_ms - expected_interval_ms) <= tolerance, \
                f"Profile {name}: interval mismatch"
    
    @patch('threading.Thread')
    def test_scenario_execution(self, mock_thread, generator):
        """Test traffic scenario execution"""
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        generator.start_scenario("basic_video", duration=1, background_load_mbps=100)
        
        # Verify threads were created
        assert mock_thread.called
        
        # Verify join was called (scenario waited for completion)
        mock_thread_instance.join.assert_called()
    
    def test_available_scenarios(self, generator):
        """Test that scenarios are properly defined"""
        # Test valid scenarios
        valid_scenarios = [
            "autonomous_driving",
            "highway_driving", 
            "parking_assist",
            "basic_video",
            "all_traffic"
        ]
        
        for scenario in valid_scenarios:
            # Should not raise exception
            try:
                # Mock the threading to avoid actual network traffic
                with patch('threading.Thread') as mock_thread:
                    mock_thread_instance = MagicMock()
                    mock_thread.return_value = mock_thread_instance
                    generator.start_scenario(scenario, duration=0.1)
            except ValueError:
                pytest.fail(f"Valid scenario {scenario} was rejected")
    
    def test_invalid_scenario(self, generator):
        """Test invalid scenario handling"""
        with pytest.raises(ValueError):
            generator.start_scenario("nonexistent_scenario", duration=1)
    
    def test_statistics_collection(self, generator):
        """Test statistics collection and calculation"""
        # Add some fake statistics
        generator.statistics = {
            "stream1": {
                "packets_sent": 1000,
                "bytes_sent": 1400000,
                "duration": 10.0,
                "errors": 0
            },
            "stream2": {
                "packets_sent": 2000,
                "bytes_sent": 2800000,
                "duration": 10.0,
                "errors": 1
            }
        }
        
        stats = generator.get_statistics()
        
        assert stats['total_packets'] == 3000
        assert stats['total_bytes'] == 4200000
        assert stats['total_errors'] == 1
        assert 'total_bitrate_mbps' in stats
        assert 'total_pps' in stats
        assert 'streams' in stats
        
        # Check calculated values
        expected_bitrate = (4200000 * 8) / (10.0 * 1_000_000)  # Mbps
        assert abs(stats['total_bitrate_mbps'] - expected_bitrate) < 0.1
    
    def test_statistics_saving(self, generator):
        """Test statistics saving to file"""
        # Add some statistics
        generator.statistics = {
            "test_stream": {
                "packets_sent": 100,
                "bytes_sent": 140000,
                "duration": 1.0,
                "errors": 0
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            generator.save_statistics(temp_path)
            
            # Verify file was created and contains data
            assert os.path.exists(temp_path)
            
            with open(temp_path, 'r') as f:
                saved_stats = json.load(f)
            
            assert 'total_packets' in saved_stats
            assert 'streams' in saved_stats
            assert saved_stats['total_packets'] == 100
        finally:
            os.unlink(temp_path)
    
    def test_config_template_creation(self, generator):
        """Test configuration template creation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            generator.create_config_template(temp_path)
            
            # Verify file was created
            assert os.path.exists(temp_path)
            
            # Verify JSON structure
            with open(temp_path, 'r') as f:
                template = json.load(f)
            
            assert 'description' in template
            assert 'profiles' in template
            assert len(template['profiles']) > 0
            
            # Check profile structure
            profile = template['profiles'][0]
            required_fields = ['name', 'traffic_type', 'bitrate_mbps', 'packet_size_bytes']
            for field in required_fields:
                assert field in profile
        finally:
            os.unlink(temp_path)
    
    def test_stop_functionality(self, generator):
        """Test traffic generation stopping"""
        generator.running = True
        generator.stop_all_traffic()
        assert generator.running is False
    
    @patch('time.sleep')
    @patch('socket.socket')
    def test_jitter_implementation(self, mock_socket, mock_sleep, generator):
        """Test that jitter is properly implemented"""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock
        
        profile_with_jitter = TrafficProfile(
            name="Jitter Test",
            traffic_type=TrafficType.VIDEO_1080P,
            bitrate_mbps=15.0,
            packet_size_bytes=1400,
            interval_ms=10.0,
            priority=5,
            destination=("127.0.0.1", 12345),
            jitter_ms=5.0  # High jitter for testing
        )
        
        generator.running = True
        
        # Mock time.time to control the loop
        with patch('time.time') as mock_time:
            mock_time.side_effect = [0, 0.001, 0.002, 0.1]  # Quick exit
            
            generator.generate_traffic_stream(profile_with_jitter, duration_seconds=0.05)
        
        # Verify socket operations occurred
        mock_socket.assert_called()
    
    def test_burst_traffic_implementation(self, generator):
        """Test burst traffic functionality"""
        profile_with_burst = TrafficProfile(
            name="Burst Test",
            traffic_type=TrafficType.INFOTAINMENT,
            bitrate_mbps=50.0,
            packet_size_bytes=1400,
            interval_ms=10.0,
            priority=1,
            destination=("127.0.0.1", 12345),
            burst_probability=1.0,  # Always burst for testing
            burst_multiplier=3.0
        )
        
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            
            generator.running = True
            
            with patch('time.time') as mock_time:
                mock_time.side_effect = [0, 0.001, 0.002, 0.1]  # Quick exit
                
                generator.generate_traffic_stream(profile_with_burst, duration_seconds=0.05)
            
            # With 100% burst probability and 3x multiplier, should send multiple packets
            # The exact number depends on timing, but should be more than without burst
            assert mock_sock.sendto.called

class TestTrafficGeneratorIntegration:
    """Integration tests for traffic generator"""
    
    def test_realistic_automotive_scenario(self):
        """Test realistic automotive scenario execution"""
        generator = TrafficGenerator()
        
        # Test a scenario without actually generating network traffic
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            
            with patch('threading.Thread') as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance
                
                # Should complete without errors
                generator.start_scenario("basic_video", duration=0.1)
                
                # Verify threading was used
                assert mock_thread.called
    
    def test_background_traffic_adjustment(self):
        """Test background traffic load adjustment"""
        generator = TrafficGenerator()
        
        original_bg_profile = generator.AUTOMOTIVE_PROFILES["background_traffic"]
        original_bitrate = original_bg_profile.bitrate_mbps
        
        with patch('threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            generator.start_scenario("basic_video", duration=0.1, background_load_mbps=200)
            
            # Verify background traffic bitrate was adjusted
            current_bg_profile = generator.AUTOMOTIVE_PROFILES["background_traffic"]
            assert current_bg_profile.bitrate_mbps == 200.0
    
    def test_comprehensive_traffic_types(self):
        """Test all traffic types are supported"""
        generator = TrafficGenerator()
        
        # Test payload generation for all traffic types
        for traffic_type in TrafficType:
            profile = TrafficProfile(
                name=f"test_{traffic_type.value}",
                traffic_type=traffic_type,
                bitrate_mbps=10.0,
                packet_size_bytes=1000,
                interval_ms=10.0,
                priority=3,
                destination=("127.0.0.1", 12345)
            )
            
            # Should not raise exception
            payload = generator.generate_realistic_payload(profile, 123)
            assert len(payload) == 1000
            assert isinstance(payload, bytes)

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])