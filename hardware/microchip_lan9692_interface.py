#!/usr/bin/env python3
"""
Microchip LAN9692/LAN9662 Hardware Interface for CBS TSN Implementation
Direct hardware control interface for automotive TSN switches
"""

import serial
import yaml
import json
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MUP1Command(Enum):
    """MUP1CC command types for Microchip boards"""
    FETCH = "fetch"
    IPATCH = "ipatch"
    DELETE = "delete"
    COMMIT = "commit"
    REBOOT = "reboot"


@dataclass
class LAN9692Config:
    """Configuration for LAN9692 EVB board"""
    model: str = "LAN9692"
    cpu: str = "ARM Cortex-A53 @ 1GHz"
    memory: str = "2 MiB ECC SRAM"
    flash: str = "8 MB QSPI NOR"
    ports: List[str] = None
    features: List[str] = None
    
    def __post_init__(self):
        if self.ports is None:
            self.ports = ["SFP+ x4", "MATEnet x7", "RJ45 x1"]
        if self.features is None:
            self.features = ["CBS", "TAS", "PSFP", "gPTP", "802.1AS-2020"]


@dataclass
class LAN9662Config:
    """Configuration for LAN9662 EVB board"""
    model: str = "LAN9662"
    cpu: str = "ARM Cortex-A7 @ 600MHz"
    memory: str = "512 MB DDR3L"
    flash: str = "4 GB eMMC NAND"
    ports: List[str] = None
    features: List[str] = None
    
    def __post_init__(self):
        if self.ports is None:
            self.ports = ["RJ45 Gigabit x2"]
        if self.features is None:
            self.features = ["CBS", "TAS", "PSFP", "gPTP", "RTE"]


class MicrochipTSNInterface:
    """
    Hardware interface for Microchip TSN switches
    Supports LAN9692 and LAN9662 EVB boards
    """
    
    def __init__(self, device: str = "/dev/ttyACM0", model: str = "LAN9692"):
        """
        Initialize TSN hardware interface
        
        Args:
            device: Serial device path (USB-C UART)
            model: Board model (LAN9692 or LAN9662)
        """
        self.device = device
        self.model = model
        self.serial = None
        
        # Load board configuration
        if model == "LAN9692":
            self.config = LAN9692Config()
        elif model == "LAN9662":
            self.config = LAN9662Config()
        else:
            raise ValueError(f"Unsupported model: {model}")
        
        logger.info(f"Initialized {model} interface on {device}")
    
    def connect(self, baudrate: int = 115200):
        """
        Connect to the TSN switch via serial interface
        
        Args:
            baudrate: Serial communication speed
        """
        try:
            self.serial = serial.Serial(
                port=self.device,
                baudrate=baudrate,
                timeout=5,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            logger.info(f"Connected to {self.model} at {self.device}")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the TSN switch"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info(f"Disconnected from {self.model}")
    
    def execute_mup1_command(self, command: MUP1Command, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute MUP1CC command on the board
        
        Args:
            command: MUP1 command type
            params: Command parameters
        
        Returns:
            Command response
        """
        cmd_str = f"dr mup1cc -d {self.device} -m {command.value}"
        
        # Add parameters based on command type
        if command == MUP1Command.FETCH:
            if 'path' in params:
                cmd_str += f" -p \"{params['path']}\""
        elif command == MUP1Command.IPATCH:
            if 'file' in params:
                cmd_str += f" -i {params['file']}"
        
        try:
            # Execute command via subprocess
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Command executed: {cmd_str}")
                return {
                    'success': True,
                    'output': result.stdout,
                    'command': cmd_str
                }
            else:
                logger.error(f"Command failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'command': cmd_str
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Command timeout")
            return {
                'success': False,
                'error': 'Command timeout',
                'command': cmd_str
            }
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': cmd_str
            }
    
    def configure_vlan(self, port: int, vlan_id: int, enabled: bool = True) -> bool:
        """
        Configure VLAN on a specific port
        
        Args:
            port: Port number (8-11 for LAN9692)
            vlan_id: VLAN identifier
            enabled: Enable/disable VLAN
        
        Returns:
            Configuration success
        """
        config = {
            f"/ietf-interfaces:interfaces/interface[name='swp{port}']/ieee802-dot1q-bridge:bridge-port/vlan/enable": enabled,
            f"/ietf-interfaces:interfaces/interface[name='swp{port}']/ieee802-dot1q-bridge:bridge-port/vlan/vlan-id": vlan_id
        }
        
        # Create YAML file
        yaml_file = f"vlan_port{port}.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(config, f)
        
        # Apply configuration
        result = self.execute_mup1_command(
            MUP1Command.IPATCH,
            {'file': yaml_file}
        )
        
        return result['success']
    
    def configure_cbs(self, port: int, traffic_class: int, 
                     idle_slope: int, hi_credit: int = None, lo_credit: int = None) -> bool:
        """
        Configure CBS parameters for a port and traffic class
        
        Args:
            port: Port number
            traffic_class: Traffic class (0-7)
            idle_slope: Idle slope in bps
            hi_credit: High credit limit
            lo_credit: Low credit limit
        
        Returns:
            Configuration success
        """
        # Calculate credits if not provided
        if hi_credit is None:
            hi_credit = idle_slope // 1000  # Simple estimation
        if lo_credit is None:
            lo_credit = -(1000000000 - idle_slope) // 1000  # For 1Gbps link
        
        config = [
            {
                f"/ietf-interfaces:interfaces/interface[name='swp{port}']/ieee802-dot1q-bridge:bridge-port/ieee802-dot1q-sched-bridge:traffic-class-table[traffic-class='{traffic_class}']/idle-slope": idle_slope
            },
            {
                f"/ietf-interfaces:interfaces/interface[name='swp{port}']/ieee802-dot1q-bridge:bridge-port/ieee802-dot1q-sched-bridge:traffic-class-table[traffic-class='{traffic_class}']/hi-credit": hi_credit
            },
            {
                f"/ietf-interfaces:interfaces/interface[name='swp{port}']/ieee802-dot1q-bridge:bridge-port/ieee802-dot1q-sched-bridge:traffic-class-table[traffic-class='{traffic_class}']/lo-credit": lo_credit
            }
        ]
        
        # Create YAML file
        yaml_file = f"cbs_port{port}_tc{traffic_class}.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(config, f)
        
        # Apply configuration
        result = self.execute_mup1_command(
            MUP1Command.IPATCH,
            {'file': yaml_file}
        )
        
        if result['success']:
            logger.info(f"CBS configured for Port {port}, TC {traffic_class}: idle_slope={idle_slope}")
        
        return result['success']
    
    def configure_stream_filter(self, stream_id: str, input_port: int, output_port: int) -> bool:
        """
        Configure stream filter for port mapping
        
        Args:
            stream_id: Unique stream identifier
            input_port: Input port number
            output_port: Output port number
        
        Returns:
            Configuration success
        """
        config = [
            {
                f"/tsn-device:device/tsn-psfp:decap-flow-table/flow[flow-id='{stream_id}']/input-port": f"swp{input_port}"
            },
            {
                f"/tsn-device:device/tsn-psfp:encap-flow-table/flow[flow-id='{stream_id}']/output-port": f"swp{output_port}"
            }
        ]
        
        # Create YAML file
        yaml_file = f"stream_{stream_id}.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(config, f)
        
        # Apply configuration
        result = self.execute_mup1_command(
            MUP1Command.IPATCH,
            {'file': yaml_file}
        )
        
        if result['success']:
            logger.info(f"Stream filter configured: {stream_id} ({input_port} -> {output_port})")
        
        return result['success']
    
    def fetch_port_statistics(self, port: int) -> Dict[str, Any]:
        """
        Fetch port statistics and counters
        
        Args:
            port: Port number
        
        Returns:
            Port statistics dictionary
        """
        path = f"/ietf-interfaces:interfaces/interface[name='swp{port}']/statistics"
        
        result = self.execute_mup1_command(
            MUP1Command.FETCH,
            {'path': path}
        )
        
        if result['success']:
            try:
                # Parse YANG output (simplified)
                stats = {
                    'rx_packets': 0,
                    'tx_packets': 0,
                    'rx_bytes': 0,
                    'tx_bytes': 0,
                    'rx_errors': 0,
                    'tx_errors': 0,
                    'rx_dropped': 0,
                    'tx_dropped': 0
                }
                
                # Parse output (actual implementation would parse YANG/JSON response)
                output_lines = result['output'].split('\n')
                for line in output_lines:
                    if 'rx-packets' in line:
                        stats['rx_packets'] = int(line.split(':')[-1].strip())
                    elif 'tx-packets' in line:
                        stats['tx_packets'] = int(line.split(':')[-1].strip())
                    # ... parse other statistics
                
                return stats
            except Exception as e:
                logger.error(f"Failed to parse statistics: {e}")
                return {}
        else:
            return {}
    
    def enable_gate_control(self, port: int, enabled: bool = True) -> bool:
        """
        Enable/disable gate control for Time-Aware Shaper
        
        Args:
            port: Port number
            enabled: Enable/disable gate
        
        Returns:
            Configuration success
        """
        config = {
            f"/ietf-interfaces:interfaces/interface[name='swp{port}']/ieee802-dot1q-bridge:bridge-port/ieee802-dot1q-sched-bridge:gate-parameter-table/gate-enabled": enabled
        }
        
        yaml_file = f"gate_port{port}.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(config, f)
        
        result = self.execute_mup1_command(
            MUP1Command.IPATCH,
            {'file': yaml_file}
        )
        
        return result['success']
    
    def set_queue_max_sdu(self, port: int, traffic_class: int, max_sdu: int = 1522) -> bool:
        """
        Set maximum SDU size for a queue
        
        Args:
            port: Port number
            traffic_class: Traffic class
            max_sdu: Maximum SDU size in bytes
        
        Returns:
            Configuration success
        """
        config = {
            f"/ietf-interfaces:interfaces/interface[name='swp{port}']/ieee802-dot1q-bridge:bridge-port/ieee802-dot1q-sched-bridge:gate-parameter-table/queue-max-sdu-table[traffic-class='{traffic_class}']/queue-max-sdu": max_sdu
        }
        
        yaml_file = f"sdu_port{port}_tc{traffic_class}.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(config, f)
        
        result = self.execute_mup1_command(
            MUP1Command.IPATCH,
            {'file': yaml_file}
        )
        
        return result['success']
    
    def apply_experimental_setup(self) -> bool:
        """
        Apply the complete experimental setup from the paper
        3-to-1 port congestion scenario with CBS
        """
        logger.info("Applying experimental setup for 3-to-1 congestion scenario")
        
        success = True
        
        # 1. Enable VLAN and gates on all ports
        for port in [8, 9, 10, 11]:
            success &= self.enable_gate_control(port, True)
            success &= self.set_queue_max_sdu(port, 0, 1522)  # TC0 for BE traffic
            success &= self.set_queue_max_sdu(port, 1, 1522)  # TC1 for AV traffic
        
        # 2. Configure stream filters (3 inputs to 1 output)
        success &= self.configure_stream_filter("streamA", 8, 9)
        success &= self.configure_stream_filter("streamB", 10, 9)
        success &= self.configure_stream_filter("streamC", 11, 9)
        
        # 3. Configure CBS on output port (Port 9)
        # Allocate 100 Mbps for each traffic class as per paper
        for tc in range(8):
            idle_slope = 100_000_000  # 100 Mbps in bps
            success &= self.configure_cbs(
                port=9,
                traffic_class=tc,
                idle_slope=idle_slope
            )
        
        if success:
            logger.info("Experimental setup applied successfully")
        else:
            logger.error("Failed to apply complete experimental setup")
        
        return success
    
    def monitor_experiment(self, duration_sec: int = 10, interval_sec: int = 1) -> List[Dict]:
        """
        Monitor port statistics during experiment
        
        Args:
            duration_sec: Monitoring duration
            interval_sec: Sampling interval
        
        Returns:
            List of statistics samples
        """
        samples = []
        start_time = time.time()
        
        logger.info(f"Starting monitoring for {duration_sec} seconds")
        
        while time.time() - start_time < duration_sec:
            sample = {
                'timestamp': time.time() - start_time,
                'ports': {}
            }
            
            # Collect statistics for all ports
            for port in [8, 9, 10, 11]:
                stats = self.fetch_port_statistics(port)
                sample['ports'][port] = stats
            
            samples.append(sample)
            time.sleep(interval_sec)
        
        logger.info(f"Collected {len(samples)} samples")
        
        return samples
    
    def calculate_drop_rate(self, samples: List[Dict]) -> Dict[str, float]:
        """
        Calculate drop rates from collected samples
        
        Args:
            samples: List of statistics samples
        
        Returns:
            Drop rate analysis
        """
        if len(samples) < 2:
            return {}
        
        # Get first and last samples
        first = samples[0]
        last = samples[-1]
        
        # Calculate total RX on input ports (8, 10, 11)
        total_rx = 0
        for port in [8, 10, 11]:
            if port in first['ports'] and port in last['ports']:
                rx_delta = last['ports'][port]['rx_packets'] - first['ports'][port]['rx_packets']
                total_rx += rx_delta
        
        # Calculate TX on output port (9)
        total_tx = 0
        if 9 in first['ports'] and 9 in last['ports']:
            total_tx = last['ports'][9]['tx_packets'] - first['ports'][9]['tx_packets']
        
        # Calculate drop rate
        total_dropped = max(0, total_rx - total_tx)
        drop_rate = (total_dropped / total_rx * 100) if total_rx > 0 else 0
        
        return {
            'total_rx_packets': total_rx,
            'total_tx_packets': total_tx,
            'total_dropped_packets': total_dropped,
            'drop_rate_percent': drop_rate,
            'throughput_mbps': (total_tx * 1500 * 8) / (samples[-1]['timestamp'] * 1_000_000)
        }


class VLCStreamingTest:
    """
    VLC-based video streaming test for CBS validation
    Implements the video streaming scenarios from the paper
    """
    
    def __init__(self, interface: MicrochipTSNInterface):
        """
        Initialize VLC streaming test
        
        Args:
            interface: Microchip TSN hardware interface
        """
        self.interface = interface
        self.streams = []
    
    def start_video_stream(self, source_ip: str, dest_ip: str, 
                          port: int = 5005, video_file: str = "sample.mp4") -> Dict:
        """
        Start VLC video stream
        
        Args:
            source_ip: Source IP address
            dest_ip: Destination IP address
            port: UDP port
            video_file: Video file to stream
        
        Returns:
            Stream information
        """
        # VLC command for streaming
        vlc_cmd = f"""cvlc --loop {video_file} \
            --sout "#duplicate{{
            dst=std{{access=udp{{ttl=16,mtu=1400}},mux=ts,dst={dest_ip}:{port}}}}" \
            --ttl=16"""
        
        stream_info = {
            'stream_id': f"video_{source_ip}_{dest_ip}",
            'source': source_ip,
            'destination': dest_ip,
            'port': port,
            'command': vlc_cmd,
            'bitrate_mbps': 15  # Typical HD video bitrate
        }
        
        self.streams.append(stream_info)
        logger.info(f"Configured video stream: {stream_info['stream_id']}")
        
        return stream_info
    
    def configure_av_priority(self, port: int, vlan_id: int = 100, pcp: int = 4):
        """
        Configure audio/video priority for streaming
        
        Args:
            port: Switch port
            vlan_id: VLAN ID for AV traffic
            pcp: Priority Code Point (0-7)
        """
        # Configure VLAN with PCP mapping
        self.interface.configure_vlan(port, vlan_id, enabled=True)
        
        # Map PCP to traffic class
        tc = pcp  # Direct mapping for simplicity
        
        # Configure CBS for AV traffic class
        # Allocate 20 Mbps for video stream (15 Mbps + overhead)
        self.interface.configure_cbs(
            port=port,
            traffic_class=tc,
            idle_slope=20_000_000  # 20 Mbps
        )
        
        logger.info(f"Configured AV priority on port {port}: VLAN {vlan_id}, PCP {pcp}")
    
    def run_streaming_test(self, duration_sec: int = 30) -> Dict:
        """
        Run video streaming test with CBS
        
        Args:
            duration_sec: Test duration
        
        Returns:
            Test results
        """
        logger.info("Starting video streaming test")
        
        # Configure streams
        self.start_video_stream("10.0.100.1", "10.0.100.2", 5005)
        self.start_video_stream("10.0.100.1", "10.0.100.3", 5006)
        
        # Configure AV priority on output ports
        self.configure_av_priority(10, vlan_id=100, pcp=4)
        self.configure_av_priority(11, vlan_id=100, pcp=4)
        
        # Monitor during streaming
        samples = self.interface.monitor_experiment(duration_sec, interval_sec=2)
        
        # Analyze results
        results = self.interface.calculate_drop_rate(samples)
        
        # Add streaming-specific metrics
        results['stream_count'] = len(self.streams)
        results['total_av_bitrate_mbps'] = sum(s['bitrate_mbps'] for s in self.streams)
        results['qos_guaranteed'] = results['drop_rate_percent'] < 1.0  # <1% loss for video
        
        logger.info(f"Streaming test complete: Drop rate = {results['drop_rate_percent']:.2f}%")
        
        return results


def main():
    """Main function to run hardware interface tests"""
    print("="*80)
    print("Microchip LAN9692/LAN9662 TSN Hardware Interface")
    print("Automotive CBS Implementation")
    print("="*80)
    
    # Initialize hardware interface
    interface = MicrochipTSNInterface(device="/dev/ttyACM0", model="LAN9692")
    
    # Connect to hardware
    if not interface.connect():
        print("Failed to connect to hardware")
        return
    
    try:
        # Apply experimental setup
        print("\nApplying experimental configuration...")
        if interface.apply_experimental_setup():
            print("Configuration applied successfully")
        else:
            print("Configuration failed")
            return
        
        # Run monitoring
        print("\nRunning 10-second experiment...")
        samples = interface.monitor_experiment(duration_sec=10)
        
        # Calculate results
        results = interface.calculate_drop_rate(samples)
        
        # Display results
        print("\n" + "="*80)
        print("EXPERIMENTAL RESULTS")
        print("="*80)
        print(f"Total RX Packets: {results.get('total_rx_packets', 0):,.0f}")
        print(f"Total TX Packets: {results.get('total_tx_packets', 0):,.0f}")
        print(f"Total Dropped: {results.get('total_dropped_packets', 0):,.0f}")
        print(f"Drop Rate: {results.get('drop_rate_percent', 0):.2f}%")
        print(f"Throughput: {results.get('throughput_mbps', 0):.1f} Mbps")
        
        # Run VLC streaming test
        print("\n" + "="*80)
        print("VIDEO STREAMING TEST")
        print("="*80)
        
        vlc_test = VLCStreamingTest(interface)
        stream_results = vlc_test.run_streaming_test(duration_sec=30)
        
        print(f"Stream Count: {stream_results['stream_count']}")
        print(f"Total AV Bitrate: {stream_results['total_av_bitrate_mbps']} Mbps")
        print(f"QoS Guaranteed: {stream_results['qos_guaranteed']}")
        
    finally:
        # Disconnect
        interface.disconnect()
        print("\nTest completed")


if __name__ == "__main__":
    main()