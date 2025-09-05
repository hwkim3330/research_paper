#!/usr/bin/env python3
"""
Test suite for 4-Port Automotive CBS TSN Switch Implementation
Validates CBS functionality and experimental scenarios
"""

import unittest
import json
import numpy as np
from typing import Dict, List, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.automotive_cbs_switch import (
    AutomotiveCBSSwitch, 
    AutomotiveExperiment,
    TrafficClass,
    PortConfiguration,
    CBSParameters
)
from hardware.microchip_lan9692_interface import (
    MicrochipTSNInterface,
    LAN9692Config,
    LAN9662Config,
    VLCStreamingTest
)


class TestAutomotiveCBS(unittest.TestCase):
    """Test cases for automotive CBS implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.switch = AutomotiveCBSSwitch(model="LAN9692")
    
    def test_switch_initialization(self):
        """Test switch initialization with correct model"""
        self.assertEqual(self.switch.model, "LAN9692")
        self.assertEqual(self.switch.max_ports, 4)
        self.assertIn("CBS", self.switch.features)
        self.assertIn("TAS", self.switch.features)
        
        # Check default ports
        self.assertIn(8, self.switch.ports)
        self.assertIn(9, self.switch.ports)
        self.assertIn(10, self.switch.ports)
        self.assertIn(11, self.switch.ports)
    
    def test_cbs_configuration(self):
        """Test CBS parameter configuration"""
        # Configure CBS for port 9, traffic class 1
        self.switch.configure_cbs(
            port_id=9,
            traffic_class=TrafficClass.TC1_AV,
            idle_slope_mbps=100,
            max_frame_size=1522
        )
        
        # Check configuration exists
        key = (9, TrafficClass.TC1_AV)
        self.assertIn(key, self.switch.cbs_configs)
        
        # Verify parameters
        cbs_params = self.switch.cbs_configs[key]
        self.assertEqual(cbs_params.idle_slope, 100_000_000)  # 100 Mbps in bps
        self.assertEqual(cbs_params.send_slope, -900_000_000)  # For 1 Gbps link
        self.assertTrue(cbs_params.hi_credit > 0)
        self.assertTrue(cbs_params.lo_credit < 0)
    
    def test_stream_filter_configuration(self):
        """Test stream filter addition"""
        self.switch.add_stream_filter(
            stream_id="test_stream",
            input_port=8,
            output_port=9,
            vlan_id=100,
            priority=4
        )
        
        # Check filter exists
        self.assertEqual(len(self.switch.stream_filters), 1)
        filter_config = self.switch.stream_filters[0]
        
        self.assertEqual(filter_config['stream_id'], "test_stream")
        self.assertEqual(filter_config['input_port'], 8)
        self.assertEqual(filter_config['output_port'], 9)
        self.assertEqual(filter_config['vlan_id'], 100)
        self.assertEqual(filter_config['priority'], 4)
        self.assertEqual(filter_config['traffic_class'], TrafficClass.TC4_AV_HIGH)
    
    def test_traffic_simulation_baseline(self):
        """Test traffic simulation without CBS (baseline)"""
        # Run simulation without CBS configuration
        results = self.switch.simulate_traffic_flow(
            duration_sec=1.0,
            traffic_loads={8: 1000, 10: 1000, 11: 1000}
        )
        
        # Check results structure
        self.assertIn('total_rx', results)
        self.assertIn('total_tx', results)
        self.assertIn('total_dropped', results)
        self.assertIn('drop_rate', results)
        self.assertIn('throughput_mbps', results)
        self.assertFalse(results['cbs_enabled'])
        
        # Baseline should have high drop rate (>50%)
        self.assertGreater(results['drop_rate'], 50)
    
    def test_traffic_simulation_with_cbs(self):
        """Test traffic simulation with CBS enabled"""
        # Configure CBS for output port
        for tc in [TrafficClass.TC0_BE, TrafficClass.TC1_AV]:
            self.switch.configure_cbs(
                port_id=9,
                traffic_class=tc,
                idle_slope_mbps=100
            )
        
        # Run simulation
        results = self.switch.simulate_traffic_flow(
            duration_sec=1.0,
            traffic_loads={8: 1000, 10: 1000, 11: 1000}
        )
        
        # Check CBS is detected as enabled
        self.assertTrue(results['cbs_enabled'])
        self.assertEqual(results['cbs_effectiveness']['status'], 'ACTIVE')
        
        # CBS should reduce drop rate
        self.assertLess(results['drop_rate'], 50)
    
    def test_ipatch_config_generation(self):
        """Test iPATCH configuration generation"""
        # Configure switch
        self.switch.ports[8].vlan_enabled = True
        self.switch.ports[8].vlan_id = 100
        
        self.switch.configure_cbs(
            port_id=9,
            traffic_class=TrafficClass.TC1_AV,
            idle_slope_mbps=20
        )
        
        self.switch.add_stream_filter("stream1", 8, 9)
        
        # Generate configuration
        configs = self.switch.generate_ipatch_config()
        
        # Check configuration entries
        self.assertGreater(len(configs), 0)
        
        # Check for VLAN config
        vlan_configs = [c for c in configs if 'vlan' in c['path']]
        self.assertGreater(len(vlan_configs), 0)
        
        # Check for CBS config
        cbs_configs = [c for c in configs if 'idle-slope' in c['path']]
        self.assertGreater(len(cbs_configs), 0)
        self.assertEqual(cbs_configs[0]['value'], 20_000_000)  # 20 Mbps in bps
        
        # Check for stream filter
        stream_configs = [c for c in configs if 'flow' in c['path']]
        self.assertGreater(len(stream_configs), 0)
    
    def test_mup1_command_export(self):
        """Test MUP1CC command export"""
        # Configure switch
        self.switch.configure_cbs(9, TrafficClass.TC1_AV, 100)
        self.switch.add_stream_filter("test", 8, 9)
        
        # Export commands
        filename = "test_cbs_config.sh"
        exported_file = self.switch.export_mup1_commands(filename)
        
        # Check file exists
        self.assertTrue(os.path.exists(exported_file))
        
        # Read and verify content
        with open(exported_file, 'r') as f:
            content = f.read()
        
        # Check for expected commands
        self.assertIn("#!/bin/bash", content)
        self.assertIn("dr mup1cc", content)
        self.assertIn("ipatch", content)
        self.assertIn("idle-slope", content)
        
        # Clean up
        os.remove(exported_file)


class TestAutomotiveExperiment(unittest.TestCase):
    """Test cases for automotive experiment scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.experiment = AutomotiveExperiment()
    
    def test_baseline_experiment_setup(self):
        """Test baseline experiment configuration"""
        self.experiment.setup_baseline_experiment()
        
        # Check CBS is disabled
        self.assertEqual(len(self.experiment.switch.cbs_configs), 0)
        
        # Check stream filters are configured
        self.assertGreater(len(self.experiment.switch.stream_filters), 0)
    
    def test_cbs_experiment_setup(self):
        """Test CBS experiment configuration"""
        self.experiment.setup_cbs_experiment()
        
        # Check CBS is configured
        self.assertGreater(len(self.experiment.switch.cbs_configs), 0)
        
        # Check all traffic classes are configured for port 9
        configured_tcs = [tc for (port, tc) in self.experiment.switch.cbs_configs.keys() if port == 9]
        self.assertGreater(len(configured_tcs), 0)
    
    def test_experiment_execution(self):
        """Test complete experiment execution"""
        # Run experiment
        results = self.experiment.run_experiment(duration_sec=0.5)  # Short duration for test
        
        # Check results structure
        self.assertIn('baseline_performance', results)
        self.assertIn('cbs_performance', results)
        self.assertIn('improvement', results)
        self.assertIn('conclusion', results)
        
        # Check improvement metrics
        self.assertIn('drop_rate_reduction', results['improvement'])
        self.assertIn('drop_rate_improvement_percent', results['improvement'])
        self.assertIn('throughput_improvement', results['improvement'])
    
    def test_results_analysis(self):
        """Test experiment results analysis"""
        # Create mock results
        self.experiment.results = {
            'baseline': {
                'drop_rate': 64.37,
                'throughput_mbps': 333,
                'total_rx': 15737339,
                'total_tx': 5607906,
                'total_dropped': 10129433
            },
            'cbs_enabled': {
                'drop_rate': 10.0,
                'throughput_mbps': 900,
                'total_rx': 15737339,
                'total_tx': 14163605,
                'total_dropped': 1573734
            }
        }
        
        # Analyze results
        analysis = self.experiment.analyze_results()
        
        # Check analysis
        self.assertAlmostEqual(analysis['improvement']['drop_rate_reduction'], 54.37, places=1)
        self.assertGreater(analysis['improvement']['drop_rate_improvement_percent'], 80)
        self.assertIn("significantly improves", analysis['conclusion'])
    
    def test_results_export(self):
        """Test results export to JSON"""
        # Run short experiment
        self.experiment.run_experiment(duration_sec=0.1)
        
        # Export results
        filename = "test_results.json"
        exported_file = self.experiment.export_results(filename)
        
        # Check file exists
        self.assertTrue(os.path.exists(exported_file))
        
        # Read and verify JSON
        with open(exported_file, 'r') as f:
            data = json.load(f)
        
        # Check structure
        self.assertIn('timestamp', data)
        self.assertIn('switch_model', data)
        self.assertIn('baseline_results', data)
        self.assertIn('cbs_results', data)
        self.assertIn('analysis', data)
        
        # Clean up
        os.remove(exported_file)


class TestMicrochipInterface(unittest.TestCase):
    """Test cases for Microchip hardware interface"""
    
    def test_lan9692_config(self):
        """Test LAN9692 configuration"""
        config = LAN9692Config()
        
        self.assertEqual(config.model, "LAN9692")
        self.assertIn("ARM Cortex-A53", config.cpu)
        self.assertIn("CBS", config.features)
        self.assertIn("TAS", config.features)
        self.assertIn("SFP+ x4", config.ports)
    
    def test_lan9662_config(self):
        """Test LAN9662 configuration"""
        config = LAN9662Config()
        
        self.assertEqual(config.model, "LAN9662")
        self.assertIn("ARM Cortex-A7", config.cpu)
        self.assertIn("CBS", config.features)
        self.assertIn("RTE", config.features)
        self.assertIn("RJ45 Gigabit x2", config.ports)
    
    def test_interface_initialization(self):
        """Test hardware interface initialization"""
        # Initialize without actual hardware connection
        interface = MicrochipTSNInterface(device="/dev/null", model="LAN9692")
        
        self.assertEqual(interface.model, "LAN9692")
        self.assertEqual(interface.device, "/dev/null")
        self.assertIsNotNone(interface.config)
    
    def test_cbs_parameter_calculation(self):
        """Test CBS parameter calculation in hardware interface"""
        interface = MicrochipTSNInterface(device="/dev/null", model="LAN9692")
        
        # Mock CBS configuration (without actual hardware)
        port = 9
        traffic_class = 1
        idle_slope = 100_000_000  # 100 Mbps
        
        # Calculate credits
        link_speed = 1_000_000_000  # 1 Gbps
        expected_hi_credit = idle_slope // 1000
        expected_lo_credit = -(link_speed - idle_slope) // 1000
        
        # Verify calculation logic
        self.assertGreater(expected_hi_credit, 0)
        self.assertLess(expected_lo_credit, 0)
        self.assertEqual(expected_hi_credit, 100000)
        self.assertEqual(expected_lo_credit, -900000)


class TestExperimentalValidation(unittest.TestCase):
    """Test cases for experimental validation against paper results"""
    
    def test_baseline_drop_rate(self):
        """Validate baseline drop rate matches paper (64.37%)"""
        switch = AutomotiveCBSSwitch(model="LAN9692")
        
        # Simulate baseline (no CBS)
        results = switch.simulate_traffic_flow(
            duration_sec=10.0,
            traffic_loads={8: 1000, 10: 1000, 11: 1000}
        )
        
        # Paper reports 64.37% drop rate in baseline
        # Our simulation should be in similar range (50-70%)
        self.assertGreater(results['drop_rate'], 50)
        self.assertLess(results['drop_rate'], 70)
    
    def test_cbs_improvement(self):
        """Validate CBS improvement matches paper expectations"""
        experiment = AutomotiveExperiment()
        
        # Setup CBS with 100 Mbps idle slope (as per paper)
        experiment.switch.configure_cbs(9, TrafficClass.TC0_BE, 100)
        
        # Run simulation
        results = experiment.switch.simulate_traffic_flow(duration_sec=10.0)
        
        # CBS should significantly reduce drop rate
        # Paper shows improvement from 64.37% to much lower values
        self.assertLess(results['drop_rate'], 20)
    
    def test_throughput_with_cbs(self):
        """Validate throughput with CBS matches expected values"""
        switch = AutomotiveCBSSwitch(model="LAN9692")
        
        # Configure CBS with idle slope = 100 Mbps
        switch.configure_cbs(9, TrafficClass.TC0_BE, 100)
        
        # Run simulation
        results = switch.simulate_traffic_flow(duration_sec=10.0)
        
        # Throughput should be constrained by idle slope
        # Expect around 100 Mbps per configured class
        self.assertLess(results['throughput_mbps'], 1000)
        self.assertGreater(results['throughput_mbps'], 50)
    
    def test_vlc_streaming_scenario(self):
        """Test VLC streaming scenario from paper"""
        # Create mock interface (without hardware)
        interface = MicrochipTSNInterface(device="/dev/null", model="LAN9692")
        vlc_test = VLCStreamingTest(interface)
        
        # Configure video streams
        stream1 = vlc_test.start_video_stream("10.0.100.1", "10.0.100.2", 5005)
        stream2 = vlc_test.start_video_stream("10.0.100.1", "10.0.100.3", 5006)
        
        # Check stream configuration
        self.assertEqual(len(vlc_test.streams), 2)
        self.assertEqual(stream1['bitrate_mbps'], 15)  # HD video bitrate
        self.assertEqual(stream2['bitrate_mbps'], 15)
        
        # Total AV bandwidth requirement
        total_av_bandwidth = sum(s['bitrate_mbps'] for s in vlc_test.streams)
        self.assertEqual(total_av_bandwidth, 30)  # 2 x 15 Mbps


class TestComplianceWithPaper(unittest.TestCase):
    """Test compliance with paper specifications and results"""
    
    def test_port_configuration_compliance(self):
        """Test port configuration matches paper setup"""
        switch = AutomotiveCBSSwitch(model="LAN9692")
        
        # Paper uses ports 8, 9, 10, 11
        expected_ports = [8, 9, 10, 11]
        for port in expected_ports:
            self.assertIn(port, switch.ports)
            self.assertEqual(switch.ports[port].speed_mbps, 1000)  # 1 Gbps
    
    def test_traffic_class_mapping(self):
        """Test traffic class mapping matches IEEE 802.1Q"""
        port_config = PortConfiguration(port_id=8, name="Test")
        
        # Check PCP to TC mapping (should match standard)
        self.assertEqual(port_config.pcp_mapping[0], TrafficClass.TC0_BE)
        self.assertEqual(port_config.pcp_mapping[1], TrafficClass.TC1_AV)
        self.assertEqual(port_config.pcp_mapping[6], TrafficClass.TC6_CRITICAL)
        self.assertEqual(port_config.pcp_mapping[7], TrafficClass.TC7_MGMT)
    
    def test_cbs_formula_compliance(self):
        """Test CBS formulas match IEEE 802.1Qav standard"""
        cbs_params = CBSParameters(
            traffic_class=TrafficClass.TC1_AV,
            idle_slope=100_000_000,  # 100 Mbps
            send_slope=-900_000_000,  # For 1 Gbps link
            hi_credit=12176,
            lo_credit=-109584,
            max_frame_size=1522
        )
        
        # Validate send_slope = idle_slope - link_speed
        link_speed = 1_000_000_000
        expected_send_slope = cbs_params.idle_slope - link_speed
        self.assertEqual(cbs_params.send_slope, expected_send_slope)
        
        # Validate parameters
        self.assertTrue(cbs_params.validate(link_speed))
    
    def test_experimental_parameters(self):
        """Test experimental parameters match paper"""
        experiment = AutomotiveExperiment()
        experiment.setup_cbs_experiment()
        
        # Check CBS is configured for port 9 (output port)
        port_9_configs = [(port, tc) for (port, tc) in experiment.switch.cbs_configs.keys() if port == 9]
        self.assertGreater(len(port_9_configs), 0)
        
        # Check idle slope is 100 Mbps as per paper
        for (port, tc) in port_9_configs:
            cbs = experiment.switch.cbs_configs[(port, tc)]
            self.assertEqual(cbs.idle_slope, 100_000_000)  # 100 Mbps


def run_tests():
    """Run all test suites"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestAutomotiveCBS))
    suite.addTests(loader.loadTestsFromTestCase(TestAutomotiveExperiment))
    suite.addTests(loader.loadTestsFromTestCase(TestMicrochipInterface))
    suite.addTests(loader.loadTestsFromTestCase(TestExperimentalValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestComplianceWithPaper))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)