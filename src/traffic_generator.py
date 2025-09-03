#!/usr/bin/env python3
"""
Advanced Traffic Generator for CBS Testing
Generates realistic automotive network traffic patterns for CBS validation
"""

import time
import socket
import struct
import random
import threading
import logging
import argparse
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import numpy as np
from pathlib import Path

class TrafficType(Enum):
    """Traffic type classification"""
    CRITICAL_CONTROL = "critical_control"
    VIDEO_4K = "video_4k"
    VIDEO_1080P = "video_1080p" 
    VIDEO_720P = "video_720p"
    LIDAR_DATA = "lidar_data"
    RADAR_DATA = "radar_data"
    V2X_MESSAGE = "v2x_message"
    INFOTAINMENT = "infotainment"
    DIAGNOSTICS = "diagnostics"
    BEST_EFFORT = "best_effort"

@dataclass
class TrafficProfile:
    """Traffic profile configuration"""
    name: str
    traffic_type: TrafficType
    bitrate_mbps: float
    packet_size_bytes: int
    interval_ms: float
    priority: int
    burst_probability: float = 0.0
    burst_multiplier: float = 1.0
    jitter_ms: float = 0.0
    destination: Tuple[str, int] = ("localhost", 5000)
    vlan_id: Optional[int] = None
    dscp: Optional[int] = None

class TrafficGenerator:
    """Advanced traffic generator for automotive network simulation"""
    
    # Predefined traffic profiles for automotive scenarios
    AUTOMOTIVE_PROFILES = {
        "emergency_brake": TrafficProfile(
            name="Emergency Brake Control",
            traffic_type=TrafficType.CRITICAL_CONTROL,
            bitrate_mbps=2.0,
            packet_size_bytes=64,
            interval_ms=10,
            priority=7,
            jitter_ms=0.5,
            destination=("10.0.100.2", 6001),
            vlan_id=100,
            dscp=46
        ),
        
        "steering_control": TrafficProfile(
            name="Steering Control",
            traffic_type=TrafficType.CRITICAL_CONTROL,
            bitrate_mbps=1.0,
            packet_size_bytes=32,
            interval_ms=5,
            priority=7,
            jitter_ms=0.2,
            destination=("10.0.100.2", 6002),
            vlan_id=100,
            dscp=46
        ),
        
        "front_camera_4k": TrafficProfile(
            name="Front Camera 4K",
            traffic_type=TrafficType.VIDEO_4K,
            bitrate_mbps=25.0,
            packet_size_bytes=1400,
            interval_ms=0.448,  # ~60fps, calculated for target bitrate
            priority=6,
            burst_probability=0.1,
            burst_multiplier=1.5,
            jitter_ms=2.0,
            destination=("10.0.100.2", 5005),
            vlan_id=100,
            dscp=34
        ),
        
        "surround_camera_hd": TrafficProfile(
            name="Surround Camera HD",
            traffic_type=TrafficType.VIDEO_1080P,
            bitrate_mbps=15.0,
            packet_size_bytes=1400,
            interval_ms=0.747,  # ~30fps, calculated for target bitrate
            priority=5,
            burst_probability=0.05,
            burst_multiplier=1.3,
            jitter_ms=3.0,
            destination=("10.0.100.2", 5006),
            vlan_id=100,
            dscp=26
        ),
        
        "lidar_main": TrafficProfile(
            name="Main LiDAR",
            traffic_type=TrafficType.LIDAR_DATA,
            bitrate_mbps=100.0,
            packet_size_bytes=8192,  # Large packets for point cloud data
            interval_ms=8.192,  # 10Hz, calculated for target bitrate
            priority=4,
            burst_probability=0.2,
            burst_multiplier=1.8,
            jitter_ms=1.0,
            destination=("10.0.100.2", 7001),
            vlan_id=100,
            dscp=26
        ),
        
        "radar_fusion": TrafficProfile(
            name="Radar Fusion",
            traffic_type=TrafficType.RADAR_DATA,
            bitrate_mbps=16.0,
            packet_size_bytes=512,
            interval_ms=2.56,  # 50Hz, calculated for target bitrate
            priority=3,
            jitter_ms=0.5,
            destination=("10.0.100.2", 7002),
            vlan_id=100,
            dscp=26
        ),
        
        "v2x_safety": TrafficProfile(
            name="V2X Safety Messages",
            traffic_type=TrafficType.V2X_MESSAGE,
            bitrate_mbps=10.0,
            packet_size_bytes=200,
            interval_ms=1.6,  # 10Hz, calculated for target bitrate
            priority=2,
            jitter_ms=5.0,
            destination=("10.0.100.2", 8001),
            vlan_id=100,
            dscp=18
        ),
        
        "infotainment": TrafficProfile(
            name="Infotainment Stream",
            traffic_type=TrafficType.INFOTAINMENT,
            bitrate_mbps=50.0,
            packet_size_bytes=1400,
            interval_ms=2.24,  # ~30fps, calculated for target bitrate
            priority=1,
            burst_probability=0.3,
            burst_multiplier=2.0,
            jitter_ms=10.0,
            destination=("10.0.100.2", 9001),
            vlan_id=100,
            dscp=10
        ),
        
        "diagnostics": TrafficProfile(
            name="Vehicle Diagnostics",
            traffic_type=TrafficType.DIAGNOSTICS,
            bitrate_mbps=5.0,
            packet_size_bytes=256,
            interval_ms=4.096,  # 1Hz burst, calculated for target bitrate
            priority=0,
            jitter_ms=50.0,
            destination=("10.0.100.2", 9002),
            vlan_id=100,
            dscp=0
        ),
        
        "background_traffic": TrafficProfile(
            name="Background Best Effort",
            traffic_type=TrafficType.BEST_EFFORT,
            bitrate_mbps=100.0,  # Variable load
            packet_size_bytes=1400,
            interval_ms=1.12,  # Calculated for target bitrate
            priority=0,
            burst_probability=0.1,
            burst_multiplier=3.0,
            jitter_ms=20.0,
            destination=("10.0.100.2", 9999),
            vlan_id=100,
            dscp=0
        )
    }
    
    def __init__(self, config_file: str = None):
        """Initialize traffic generator"""
        self.logger = self._setup_logging()
        self.active_streams = {}
        self.statistics = {}
        self.running = False
        
        # Load configuration if provided
        if config_file:
            self.load_config(config_file)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def load_config(self, config_file: str) -> None:
        """Load traffic configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Parse profiles from config
            for profile_data in config.get('profiles', []):
                profile = TrafficProfile(**profile_data)
                self.AUTOMOTIVE_PROFILES[profile.name.lower().replace(' ', '_')] = profile
            
            self.logger.info(f"Configuration loaded from {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise
    
    def generate_realistic_payload(self, profile: TrafficProfile, sequence: int) -> bytes:
        """Generate realistic payload based on traffic type"""
        base_size = profile.packet_size_bytes
        
        if profile.traffic_type == TrafficType.CRITICAL_CONTROL:
            # Control messages: timestamp + command + checksum
            payload = struct.pack('!QHH', int(time.time() * 1000000), sequence % 65536, 0xFFFF)
            payload += b'\x00' * (base_size - len(payload))
            
        elif profile.traffic_type in [TrafficType.VIDEO_4K, TrafficType.VIDEO_1080P, TrafficType.VIDEO_720P]:
            # Video data: RTP-like header + pseudo H.264 data
            rtp_header = struct.pack('!BBHII', 
                                   0x80,  # Version + flags
                                   96,    # Payload type
                                   sequence % 65536,  # Sequence
                                   int(time.time() * 90000) % (2**32),  # Timestamp (90kHz)
                                   0x12345678)  # SSRC
            
            # Add pseudo NAL units for realistic video patterns
            video_data = self._generate_video_pattern(base_size - len(rtp_header))
            payload = rtp_header + video_data
            
        elif profile.traffic_type == TrafficType.LIDAR_DATA:
            # LiDAR: point cloud header + 3D points
            header = struct.pack('!IIIII', 
                               int(time.time() * 1000000),  # Timestamp
                               sequence,  # Frame ID
                               (base_size - 20) // 12,  # Number of points
                               0x4C494441,  # "LIDA" magic
                               0)  # Flags
            
            # Generate pseudo point cloud data (x,y,z coordinates)
            num_points = (base_size - len(header)) // 12
            points_data = b''
            for _ in range(num_points):
                x = struct.pack('!f', random.uniform(-50, 50))
                y = struct.pack('!f', random.uniform(-50, 50))
                z = struct.pack('!f', random.uniform(-5, 5))
                points_data += x + y + z
            
            payload = header + points_data
            
        elif profile.traffic_type == TrafficType.RADAR_DATA:
            # Radar: detection header + target list
            header = struct.pack('!IIHH', 
                               int(time.time() * 1000000),  # Timestamp
                               sequence,  # Frame ID
                               (base_size - 12) // 16,  # Number of targets
                               0x5241)  # "RA" magic
            
            # Generate pseudo target data
            num_targets = (base_size - len(header)) // 16
            targets_data = b''
            for _ in range(num_targets):
                range_m = struct.pack('!f', random.uniform(1, 200))
                velocity = struct.pack('!f', random.uniform(-50, 50))
                angle = struct.pack('!f', random.uniform(-60, 60))
                rcs = struct.pack('!f', random.uniform(-40, 20))
                targets_data += range_m + velocity + angle + rcs
                
            payload = header + targets_data
            
        elif profile.traffic_type == TrafficType.V2X_MESSAGE:
            # V2X: Basic Safety Message (BSM) structure
            payload = struct.pack('!BBIIIIHHBB',
                                0x00,  # Message ID
                                0x20,  # DSRCmsgID
                                int(time.time() * 1000000) % (2**32),  # Timestamp
                                random.randint(-1800000000, 1800000000),  # Latitude
                                random.randint(-1800000000, 1800000000),  # Longitude
                                random.randint(0, 4095),  # Elevation
                                random.randint(0, 8191),  # Speed
                                random.randint(0, 28800),  # Heading
                                random.randint(0, 127),   # Steering wheel angle
                                random.randint(0, 200))   # Acceleration
            payload += b'\x00' * (base_size - len(payload))
            
        else:
            # Default: random data with pattern
            payload = bytearray(base_size)
            for i in range(base_size):
                payload[i] = (sequence + i) % 256
        
        return bytes(payload)
    
    def _generate_video_pattern(self, size: int) -> bytes:
        """Generate pseudo H.264 video pattern"""
        data = bytearray(size)
        
        # Add some NAL unit start codes and realistic patterns
        pos = 0
        while pos < size - 4:
            # NAL start code
            if pos < size - 4:
                data[pos:pos+4] = b'\x00\x00\x00\x01'
                pos += 4
            
            # Random NAL unit type
            if pos < size:
                data[pos] = random.choice([0x67, 0x68, 0x65, 0x41, 0x01])  # SPS, PPS, IDR, P, B frames
                pos += 1
            
            # Fill with pseudo-compressed data
            chunk_size = min(random.randint(50, 200), size - pos)
            for i in range(chunk_size):
                if pos + i < size:
                    data[pos + i] = random.randint(0, 255)
            pos += chunk_size
        
        return bytes(data)
    
    def create_socket(self, profile: TrafficProfile) -> socket.socket:
        """Create and configure socket for traffic profile"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set socket options for QoS
        if profile.priority > 0:
            # Set socket priority (SO_PRIORITY)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_PRIORITY, profile.priority)
            except:
                pass  # Not supported on all platforms
        
        # Set DSCP if specified
        if profile.dscp is not None:
            try:
                # Set IP_TOS (Type of Service)
                tos = profile.dscp << 2
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, tos)
            except:
                pass  # Not supported on all platforms
        
        return sock
    
    def generate_traffic_stream(self, profile: TrafficProfile, duration_seconds: int = 60) -> None:
        """Generate traffic stream for a specific profile"""
        self.logger.info(f"Starting traffic stream: {profile.name}")
        
        sock = self.create_socket(profile)
        sequence = 0
        start_time = time.time()
        next_send_time = start_time
        
        # Initialize statistics
        stream_stats = {
            'packets_sent': 0,
            'bytes_sent': 0,
            'start_time': start_time,
            'last_send_time': start_time,
            'errors': 0
        }
        
        try:
            while self.running and (time.time() - start_time) < duration_seconds:
                current_time = time.time()
                
                # Wait until next send time
                if current_time < next_send_time:
                    time.sleep(next_send_time - current_time)
                    current_time = time.time()
                
                # Check for burst condition
                is_burst = random.random() < profile.burst_probability
                packets_to_send = int(profile.burst_multiplier) if is_burst else 1
                
                for _ in range(packets_to_send):
                    try:
                        # Generate payload
                        payload = self.generate_realistic_payload(profile, sequence)
                        
                        # Send packet
                        sock.sendto(payload, profile.destination)
                        
                        # Update statistics
                        stream_stats['packets_sent'] += 1
                        stream_stats['bytes_sent'] += len(payload)
                        stream_stats['last_send_time'] = current_time
                        sequence += 1
                        
                    except Exception as e:
                        stream_stats['errors'] += 1
                        self.logger.error(f"Send error in {profile.name}: {e}")
                
                # Calculate next send time with jitter
                base_interval = profile.interval_ms / 1000.0
                jitter_range = profile.jitter_ms / 1000.0
                jitter = random.uniform(-jitter_range/2, jitter_range/2)
                next_send_time += base_interval + jitter
                
                # Prevent drift
                if next_send_time < current_time:
                    next_send_time = current_time + base_interval
        
        finally:
            sock.close()
            
        # Final statistics
        duration = time.time() - start_time
        stream_stats['duration'] = duration
        stream_stats['avg_bitrate_mbps'] = (stream_stats['bytes_sent'] * 8) / (duration * 1_000_000)
        stream_stats['avg_pps'] = stream_stats['packets_sent'] / duration
        
        self.statistics[profile.name] = stream_stats
        self.logger.info(f"Completed traffic stream: {profile.name} "
                        f"({stream_stats['packets_sent']} packets, "
                        f"{stream_stats['avg_bitrate_mbps']:.2f} Mbps)")
    
    def start_scenario(self, scenario_name: str, duration: int = 60, 
                      background_load_mbps: float = 0) -> None:
        """Start a complete traffic scenario"""
        self.logger.info(f"Starting scenario: {scenario_name}")
        self.running = True
        
        # Define scenarios
        scenarios = {
            "autonomous_driving": [
                "emergency_brake", "steering_control", "front_camera_4k", 
                "surround_camera_hd", "lidar_main", "radar_fusion"
            ],
            "highway_driving": [
                "front_camera_4k", "surround_camera_hd", "radar_fusion", 
                "v2x_safety", "infotainment"
            ],
            "parking_assist": [
                "surround_camera_hd", "lidar_main", "infotainment"
            ],
            "basic_video": [
                "front_camera_4k", "surround_camera_hd"
            ],
            "all_traffic": list(self.AUTOMOTIVE_PROFILES.keys())
        }
        
        if scenario_name not in scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        # Add background traffic if specified
        if background_load_mbps > 0:
            bg_profile = self.AUTOMOTIVE_PROFILES["background_traffic"]
            # Adjust background profile for specified load
            bg_profile.bitrate_mbps = background_load_mbps
            # Recalculate interval for new bitrate
            packets_per_second = (bg_profile.bitrate_mbps * 1_000_000) / (bg_profile.packet_size_bytes * 8)
            bg_profile.interval_ms = 1000.0 / packets_per_second
            
            scenarios[scenario_name].append("background_traffic")
        
        # Start all traffic streams in parallel
        threads = []
        for profile_name in scenarios[scenario_name]:
            if profile_name in self.AUTOMOTIVE_PROFILES:
                profile = self.AUTOMOTIVE_PROFILES[profile_name]
                thread = threading.Thread(
                    target=self.generate_traffic_stream,
                    args=(profile, duration)
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
                self.active_streams[profile_name] = thread
        
        # Wait for all streams to complete
        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            self.logger.info("Stopping traffic generation...")
            self.running = False
            for thread in threads:
                thread.join(timeout=5)
        
        self.logger.info(f"Scenario {scenario_name} completed")
    
    def stop_all_traffic(self) -> None:
        """Stop all active traffic streams"""
        self.running = False
        self.logger.info("Stopping all traffic streams...")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive traffic statistics"""
        total_stats = {
            'total_packets': sum(s['packets_sent'] for s in self.statistics.values()),
            'total_bytes': sum(s['bytes_sent'] for s in self.statistics.values()),
            'total_errors': sum(s['errors'] for s in self.statistics.values()),
            'streams': self.statistics.copy()
        }
        
        if self.statistics:
            total_duration = max(s['duration'] for s in self.statistics.values())
            total_stats['total_bitrate_mbps'] = (total_stats['total_bytes'] * 8) / (total_duration * 1_000_000)
            total_stats['total_pps'] = total_stats['total_packets'] / total_duration
        
        return total_stats
    
    def save_statistics(self, filename: str) -> None:
        """Save statistics to JSON file"""
        stats = self.get_statistics()
        with open(filename, 'w') as f:
            json.dump(stats, f, indent=2)
        self.logger.info(f"Statistics saved to {filename}")
    
    def create_config_template(self, filename: str) -> None:
        """Create configuration template file"""
        config = {
            "description": "Traffic Generator Configuration for CBS Testing",
            "profiles": [
                {
                    "name": "Custom Video Stream",
                    "traffic_type": "video_1080p",
                    "bitrate_mbps": 20.0,
                    "packet_size_bytes": 1400,
                    "interval_ms": 0.56,
                    "priority": 5,
                    "burst_probability": 0.1,
                    "burst_multiplier": 1.5,
                    "jitter_ms": 2.0,
                    "destination": ["10.0.100.2", 5010],
                    "vlan_id": 100,
                    "dscp": 26
                }
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"Configuration template created: {filename}")

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Automotive Traffic Generator for CBS Testing')
    parser.add_argument('--scenario', default='basic_video', 
                       choices=['autonomous_driving', 'highway_driving', 'parking_assist', 
                               'basic_video', 'all_traffic'],
                       help='Traffic scenario to generate')
    parser.add_argument('--duration', type=int, default=60, help='Duration in seconds')
    parser.add_argument('--background-load', type=float, default=0, 
                       help='Background traffic load in Mbps')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--stats-output', help='Statistics output file')
    parser.add_argument('--create-template', help='Create configuration template file')
    parser.add_argument('--list-profiles', action='store_true', 
                       help='List available traffic profiles')
    
    args = parser.parse_args()
    
    # Create configuration template
    if args.create_template:
        generator = TrafficGenerator()
        generator.create_config_template(args.create_template)
        return
    
    # List profiles
    if args.list_profiles:
        generator = TrafficGenerator()
        print("\n📋 Available Traffic Profiles:")
        print("-" * 50)
        for name, profile in generator.AUTOMOTIVE_PROFILES.items():
            print(f"• {profile.name}")
            print(f"  Type: {profile.traffic_type.value}")
            print(f"  Bitrate: {profile.bitrate_mbps} Mbps")
            print(f"  Priority: {profile.priority}")
            print(f"  Destination: {profile.destination[0]}:{profile.destination[1]}")
            print()
        return
    
    # Initialize traffic generator
    generator = TrafficGenerator(args.config)
    
    try:
        print(f"🚀 Starting traffic generation...")
        print(f"📊 Scenario: {args.scenario}")
        print(f"⏱️  Duration: {args.duration} seconds")
        if args.background_load > 0:
            print(f"📡 Background load: {args.background_load} Mbps")
        print()
        
        # Start scenario
        generator.start_scenario(args.scenario, args.duration, args.background_load)
        
        # Print statistics
        stats = generator.get_statistics()
        print(f"\n📈 Traffic Generation Complete!")
        print(f"📦 Total packets sent: {stats['total_packets']:,}")
        print(f"💾 Total bytes sent: {stats['total_bytes']:,} ({stats['total_bytes']/1024/1024:.1f} MB)")
        print(f"🚀 Average bitrate: {stats.get('total_bitrate_mbps', 0):.2f} Mbps")
        print(f"📊 Average PPS: {stats.get('total_pps', 0):.1f}")
        if stats['total_errors'] > 0:
            print(f"⚠️  Errors: {stats['total_errors']}")
        
        # Save statistics if requested
        if args.stats_output:
            generator.save_statistics(args.stats_output)
            print(f"💾 Statistics saved to: {args.stats_output}")
    
    except KeyboardInterrupt:
        print("\n🛑 Traffic generation interrupted by user")
        generator.stop_all_traffic()
    except Exception as e:
        print(f"❌ Error: {e}")
        generator.stop_all_traffic()

if __name__ == "__main__":
    main()