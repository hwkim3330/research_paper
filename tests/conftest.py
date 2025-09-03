#!/usr/bin/env python3
"""
Pytest Configuration and Shared Fixtures
Common test configuration and fixtures for the CBS research project
"""

import pytest
import sys
import json
import tempfile
import os
from pathlib import Path
import logging

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging for tests
logging.basicConfig(level=logging.WARNING)

@pytest.fixture(scope="session")
def sample_experiment_data():
    """Create comprehensive sample experimental data for testing"""
    return {
        "experiment_metadata": {
            "date": "2025-09-02",
            "duration_hours": 24,
            "test_vehicles": 5,
            "total_distance_km": 2000,
            "environments": ["highway", "urban", "parking"],
            "temperature_range_c": [-10, 45]
        },
        "video_streams": {
            "4k_cameras": {
                "count": 3,
                "resolution": "3840x2160",
                "fps": 60,
                "codec": "H.265",
                "bitrate_mbps": 25,
                "actual_bitrates": {
                    "front_center": [24.8, 24.9, 25.1, 24.7, 25.0],
                    "front_left": [24.7, 24.8, 24.9, 25.0, 24.8],
                    "front_right": [24.9, 25.0, 24.8, 24.9, 24.7]
                }
            },
            "1080p_cameras": {
                "count": 6,
                "resolution": "1920x1080",
                "fps": 30,
                "codec": "H.264",
                "bitrate_mbps": 15,
                "actual_bitrates": {
                    "left_front": [14.8, 14.9, 15.1, 14.7, 15.0],
                    "left_rear": [14.7, 14.8, 14.9, 15.0, 14.8],
                    "right_front": [14.9, 15.0, 14.8, 14.9, 14.7]
                }
            }
        },
        "performance_metrics": {
            "frame_loss_rate": {
                "background_traffic_mbps": [0, 200, 400, 600, 800, 1000],
                "without_cbs": [0.0, 5.2, 12.7, 18.3, 25.8, 32.1],
                "with_cbs": [0.0, 0.1, 0.3, 0.8, 1.2, 1.8],
                "with_cbs_and_tas": [0.0, 0.0, 0.1, 0.3, 0.7, 1.1]
            },
            "latency_ms": {
                "percentiles": {
                    "without_cbs": {
                        "p50": 65.4,
                        "p75": 78.3,
                        "p90": 85.2,
                        "p95": 89.7,
                        "p99": 95.3,
                        "p99.9": 98.2,
                        "max": 102.7
                    },
                    "with_cbs": {
                        "p50": 8.8,
                        "p75": 10.1,
                        "p90": 11.2,
                        "p95": 12.1,
                        "p99": 14.8,
                        "p99.9": 16.5,
                        "max": 18.3
                    },
                    "with_cbs_and_tas": {
                        "p50": 4.2,
                        "p75": 5.1,
                        "p90": 6.3,
                        "p95": 7.2,
                        "p99": 9.1,
                        "p99.9": 10.5,
                        "max": 12.2
                    }
                },
                "time_series": {
                    "timestamps_sec": [0, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600],
                    "without_cbs": [45.2, 62.3, 71.8, 68.4, 75.2, 69.1, 72.3, 70.5, 73.8, 71.2, 74.6],
                    "with_cbs": [6.8, 6.9, 7.1, 6.7, 7.0, 6.9, 6.8, 7.1, 6.9, 6.8, 7.0]
                }
            },
            "jitter_ms": {
                "traffic_load_mbps": [0, 200, 400, 600, 800, 1000],
                "video_4k": {
                    "without_cbs": [2.1, 15.3, 28.7, 38.8, 45.3, 52.4],
                    "with_cbs": [0.8, 1.5, 2.1, 2.8, 3.2, 3.6]
                },
                "video_1080p": {
                    "without_cbs": [1.8, 12.7, 23.3, 32.4, 39.2, 45.8],
                    "with_cbs": [0.7, 1.3, 1.9, 2.6, 2.9, 3.2]
                },
                "sensor_data": {
                    "without_cbs": [0.5, 4.2, 9.1, 15.3, 20.7, 26.1],
                    "with_cbs": [0.2, 0.4, 0.7, 1.1, 1.4, 1.7]
                }
            },
            "bandwidth_utilization": {
                "reserved_mbps": {
                    "video_4k": 90,
                    "video_1080p": 108,
                    "lidar": 120,
                    "radar": 20,
                    "control": 10,
                    "v2x": 30,
                    "total": 378
                },
                "actual_mbps": {
                    "video_4k": 89.1,
                    "video_1080p": 106.8,
                    "lidar": 118.7,
                    "radar": 19.8,
                    "control": 9.9,
                    "v2x": 29.6,
                    "total": 373.9
                },
                "efficiency_percent": {
                    "video_4k": 99.0,
                    "video_1080p": 98.9,
                    "lidar": 98.9,
                    "radar": 99.0,
                    "control": 99.0,
                    "v2x": 98.7,
                    "average": 98.9
                }
            },
            "credit_dynamics": {
                "sample_duration_us": 1000,
                "timestamps_us": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                "credit_values": [0, 300, 365, 365, -2000, -6000, -10000, -11814, -9000, -5000, -1000],
                "state_transitions": ["IDLE", "WAIT", "WAIT", "READY", "SEND", "SEND", "SEND", "SEND", "WAIT", "WAIT", "WAIT"],
                "queue_depth": [0, 3, 5, 5, 4, 3, 2, 1, 2, 4, 5]
            }
        },
        "scenario_tests": {
            "highway_autonomous": {
                "speed_kmh": [80, 100, 120, 140, 160],
                "video_bitrate_mbps": [225, 240, 255, 270, 285],
                "sensor_bitrate_mbps": [116, 120, 125, 130, 135],
                "frame_loss_percent": [0.18, 0.20, 0.23, 0.26, 0.30],
                "latency_ms": [6.5, 6.8, 7.1, 7.4, 7.8],
                "cbs_efficiency_percent": [99.1, 99.0, 98.8, 98.5, 98.2]
            },
            "urban_congestion": {
                "vehicles_nearby": [10, 50, 100, 200, 500],
                "v2x_traffic_mbps": [5, 25, 50, 100, 250],
                "total_network_load_mbps": [380, 450, 520, 610, 780],
                "frame_loss_percent": [0.15, 0.22, 0.31, 0.42, 0.58],
                "v2x_latency_ms": [12, 18, 25, 38, 52]
            }
        },
        "comparison_with_competitors": {
            "vendors": ["Microchip_LAN9692", "Intel_I210", "Broadcom_BCM53134", "Marvell_88E6390"],
            "latency_ms": [6.9, 9.1, 8.7, 9.5],
            "jitter_ms": [2.8, 3.5, 3.2, 3.8],
            "frame_loss_percent": [0.52, 0.68, 0.61, 0.74],
            "cpu_usage_percent": [27.2, 45.3, 32.1, 38.7],
            "power_consumption_w": [15.2, 18.7, 16.3, 17.1]
        }
    }

@pytest.fixture
def temp_experiment_data_file(sample_experiment_data):
    """Create temporary file with sample experiment data"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        json.dump(sample_experiment_data, temp_file)
        temp_path = temp_file.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)

@pytest.fixture(scope="session") 
def test_output_dir():
    """Create temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_socket():
    """Mock socket for network testing"""
    import socket
    from unittest.mock import MagicMock, patch
    
    with patch('socket.socket') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def suppress_network_calls():
    """Suppress actual network calls during testing"""
    import socket
    from unittest.mock import patch
    
    with patch('socket.socket') as mock_socket:
        mock_instance = mock_socket.return_value
        mock_instance.sendto = lambda *args: len(args[0]) if args else 0
        mock_instance.close = lambda: None
        yield mock_socket

# Test markers
pytest_plugins = ["pytest-timeout"]

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "network: mark test as requiring network access")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "visualization: mark test as generating visualizations")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add timeout and skip network tests if needed"""
    import pytest
    
    skip_network = pytest.mark.skip(reason="Network tests disabled")
    slow_timeout = pytest.mark.timeout(30)
    
    for item in items:
        # Add timeout to slow tests
        if "slow" in item.keywords:
            item.add_marker(slow_timeout)
        
        # Skip network tests in CI or when flag is set
        if "network" in item.keywords:
            if config.getoption("--disable-network", default=False):
                item.add_marker(skip_network)

def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--disable-network",
        action="store_true",
        default=False,
        help="Disable network-dependent tests"
    )
    parser.addoption(
        "--run-slow",
        action="store_true", 
        default=False,
        help="Run slow tests"
    )

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test"""
    # Set environment variables for testing
    os.environ['TESTING'] = '1'
    os.environ['LOG_LEVEL'] = 'WARNING'
    
    yield
    
    # Cleanup after test
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
    if 'LOG_LEVEL' in os.environ:
        del os.environ['LOG_LEVEL']

@pytest.fixture
def capture_logs(caplog):
    """Capture and return log messages"""
    with caplog.at_level(logging.INFO):
        yield caplog

class TestHelpers:
    """Helper utilities for testing"""
    
    @staticmethod
    def assert_cbs_parameters_valid(params):
        """Assert that CBS parameters are valid"""
        assert params.idle_slope > 0, "idleSlope must be positive"
        assert params.send_slope < 0, "sendSlope must be negative" 
        assert params.hi_credit > 0, "hiCredit must be positive"
        assert params.lo_credit < 0, "loCredit must be negative"
        assert params.reserved_bandwidth_mbps >= params.actual_bandwidth_mbps, \
            "Reserved bandwidth must be >= actual bandwidth"
        assert 0 < params.efficiency_percent <= 100, "Efficiency must be between 0 and 100%"
    
    @staticmethod
    def assert_statistics_valid(stats):
        """Assert that traffic statistics are valid"""
        assert 'total_packets' in stats, "Statistics must include total_packets"
        assert 'total_bytes' in stats, "Statistics must include total_bytes"
        assert stats['total_packets'] >= 0, "Packet count must be non-negative"
        assert stats['total_bytes'] >= 0, "Byte count must be non-negative"
        
        if 'streams' in stats:
            for stream_name, stream_stats in stats['streams'].items():
                assert 'packets_sent' in stream_stats
                assert 'bytes_sent' in stream_stats
                assert stream_stats['packets_sent'] >= 0
                assert stream_stats['bytes_sent'] >= 0

# Make helper available globally
@pytest.fixture
def test_helpers():
    """Provide test helper utilities"""
    return TestHelpers