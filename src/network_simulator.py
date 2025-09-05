#!/usr/bin/env python3
"""
Advanced Network Simulator for CBS Performance Evaluation
Simulates realistic network conditions for IEEE 802.1Qav testing
"""

import asyncio
import random
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
from enum import Enum
import heapq
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Network event types"""
    FRAME_ARRIVAL = "frame_arrival"
    FRAME_DEPARTURE = "frame_departure"
    CREDIT_UPDATE = "credit_update"
    LINK_FAILURE = "link_failure"
    LINK_RECOVERY = "link_recovery"
    MEASUREMENT = "measurement"


@dataclass
class Frame:
    """Network frame representation"""
    id: int
    source: str
    destination: str
    size: int  # bytes
    priority: int  # 0-7
    arrival_time: float
    deadline: Optional[float] = None
    transmission_time: Optional[float] = None
    completion_time: Optional[float] = None
    dropped: bool = False
    
    def __lt__(self, other):
        """Priority comparison for heap operations"""
        return self.priority > other.priority  # Higher priority first


@dataclass
class CBSQueue:
    """Credit-Based Shaper Queue implementation"""
    priority: int
    idle_slope: float  # bps
    send_slope: float  # bps
    hi_credit: float  # bits
    lo_credit: float  # bits
    credit: float = 0.0
    frames: deque = field(default_factory=deque)
    last_update_time: float = 0.0
    
    def update_credit(self, current_time: float, is_transmitting: bool) -> None:
        """Update credit based on current state"""
        time_delta = current_time - self.last_update_time
        
        if len(self.frames) == 0:
            self.credit = 0
        elif is_transmitting:
            self.credit += self.send_slope * time_delta
            self.credit = max(self.credit, self.lo_credit)
        else:
            self.credit += self.idle_slope * time_delta
            self.credit = min(self.credit, self.hi_credit)
        
        self.last_update_time = current_time
    
    def can_transmit(self) -> bool:
        """Check if queue can transmit"""
        return len(self.frames) > 0 and self.credit >= 0


class NetworkNode:
    """Network node with CBS capabilities"""
    
    def __init__(self, node_id: str, link_speed_mbps: float = 1000):
        self.node_id = node_id
        self.link_speed_bps = link_speed_mbps * 1_000_000
        self.cbs_queues: Dict[int, CBSQueue] = {}
        self.is_transmitting = False
        self.current_frame: Optional[Frame] = None
        self.transmission_end_time: Optional[float] = None
        self.statistics = {
            'frames_transmitted': 0,
            'frames_dropped': 0,
            'bytes_transmitted': 0,
            'total_latency': 0.0,
            'max_latency': 0.0,
            'jitter_samples': []
        }
    
    def configure_cbs(self, priority: int, idle_slope_mbps: float,
                      max_frame_size: int = 1522) -> None:
        """Configure CBS for a priority queue"""
        idle_slope = idle_slope_mbps * 1_000_000
        send_slope = idle_slope - self.link_speed_bps
        
        # Calculate credit limits
        hi_credit = (max_frame_size * 8 * idle_slope) / self.link_speed_bps
        lo_credit = (max_frame_size * 8 * send_slope) / self.link_speed_bps
        
        self.cbs_queues[priority] = CBSQueue(
            priority=priority,
            idle_slope=idle_slope,
            send_slope=send_slope,
            hi_credit=hi_credit,
            lo_credit=lo_credit
        )
        
        logger.info(f"Node {self.node_id}: CBS configured for priority {priority}")
    
    def enqueue_frame(self, frame: Frame, current_time: float) -> bool:
        """Enqueue frame to appropriate CBS queue"""
        if frame.priority not in self.cbs_queues:
            logger.warning(f"No CBS queue for priority {frame.priority}")
            return False
        
        queue = self.cbs_queues[frame.priority]
        
        # Check queue size limit (optional)
        if len(queue.frames) >= 100:  # Max queue size
            self.statistics['frames_dropped'] += 1
            frame.dropped = True
            return False
        
        queue.frames.append(frame)
        return True
    
    def select_next_frame(self, current_time: float) -> Optional[Tuple[Frame, CBSQueue]]:
        """Select next frame to transmit based on CBS"""
        # Update all queue credits
        for queue in self.cbs_queues.values():
            queue.update_credit(current_time, self.is_transmitting)
        
        # Find highest priority queue that can transmit
        eligible_queues = [q for q in self.cbs_queues.values() if q.can_transmit()]
        
        if not eligible_queues:
            return None
        
        # Select highest priority
        selected_queue = max(eligible_queues, key=lambda q: q.priority)
        frame = selected_queue.frames.popleft()
        
        return frame, selected_queue
    
    def start_transmission(self, frame: Frame, current_time: float) -> float:
        """Start frame transmission"""
        transmission_time = (frame.size * 8) / self.link_speed_bps
        self.is_transmitting = True
        self.current_frame = frame
        self.transmission_end_time = current_time + transmission_time
        
        frame.transmission_time = current_time
        
        return self.transmission_end_time
    
    def complete_transmission(self, current_time: float) -> Frame:
        """Complete frame transmission"""
        frame = self.current_frame
        frame.completion_time = current_time
        
        # Update statistics
        self.statistics['frames_transmitted'] += 1
        self.statistics['bytes_transmitted'] += frame.size
        
        latency = frame.completion_time - frame.arrival_time
        self.statistics['total_latency'] += latency
        self.statistics['max_latency'] = max(self.statistics['max_latency'], latency)
        
        # Calculate jitter (variation in latency)
        if self.statistics['jitter_samples']:
            prev_latency = self.statistics['jitter_samples'][-1]
            jitter = abs(latency - prev_latency)
            self.statistics['jitter_samples'].append(latency)
        else:
            self.statistics['jitter_samples'] = [latency]
        
        self.is_transmitting = False
        self.current_frame = None
        self.transmission_end_time = None
        
        return frame


class NetworkSimulator:
    """Discrete event network simulator"""
    
    def __init__(self):
        self.nodes: Dict[str, NetworkNode] = {}
        self.current_time = 0.0
        self.event_queue: List[Tuple[float, EventType, Any]] = []
        self.results = {
            'frames': [],
            'statistics': {},
            'events': []
        }
    
    def add_node(self, node_id: str, link_speed_mbps: float = 1000) -> NetworkNode:
        """Add network node"""
        node = NetworkNode(node_id, link_speed_mbps)
        self.nodes[node_id] = node
        return node
    
    def schedule_event(self, time: float, event_type: EventType, data: Any) -> None:
        """Schedule network event"""
        heapq.heappush(self.event_queue, (time, event_type, data))
    
    def generate_traffic(self, source: str, destination: str, 
                         traffic_pattern: str, duration: float,
                         rate_mbps: float, priority: int,
                         frame_size: int = 1500) -> None:
        """Generate traffic based on pattern"""
        
        if traffic_pattern == "cbr":  # Constant Bit Rate
            interval = (frame_size * 8) / (rate_mbps * 1_000_000)
            next_time = 0.0
            frame_id = 0
            
            while next_time < duration:
                frame = Frame(
                    id=frame_id,
                    source=source,
                    destination=destination,
                    size=frame_size,
                    priority=priority,
                    arrival_time=next_time
                )
                self.schedule_event(next_time, EventType.FRAME_ARRIVAL, frame)
                next_time += interval
                frame_id += 1
                
        elif traffic_pattern == "poisson":  # Poisson arrivals
            avg_interval = (frame_size * 8) / (rate_mbps * 1_000_000)
            next_time = 0.0
            frame_id = 0
            
            while next_time < duration:
                frame = Frame(
                    id=frame_id,
                    source=source,
                    destination=destination,
                    size=random.randint(64, frame_size),
                    priority=priority,
                    arrival_time=next_time
                )
                self.schedule_event(next_time, EventType.FRAME_ARRIVAL, frame)
                next_time += random.expovariate(1 / avg_interval)
                frame_id += 1
                
        elif traffic_pattern == "burst":  # Bursty traffic
            burst_size = 10
            burst_interval = 0.1  # 100ms between bursts
            next_burst_time = 0.0
            frame_id = 0
            
            while next_burst_time < duration:
                for i in range(burst_size):
                    frame_time = next_burst_time + i * 0.001  # 1ms apart
                    frame = Frame(
                        id=frame_id,
                        source=source,
                        destination=destination,
                        size=frame_size,
                        priority=priority,
                        arrival_time=frame_time
                    )
                    self.schedule_event(frame_time, EventType.FRAME_ARRIVAL, frame)
                    frame_id += 1
                next_burst_time += burst_interval
    
    def process_frame_arrival(self, frame: Frame) -> None:
        """Process frame arrival event"""
        source_node = self.nodes.get(frame.source)
        
        if source_node:
            success = source_node.enqueue_frame(frame, self.current_time)
            
            if success and not source_node.is_transmitting:
                # Try to start transmission immediately
                next_frame = source_node.select_next_frame(self.current_time)
                if next_frame:
                    frame_to_send, queue = next_frame
                    end_time = source_node.start_transmission(frame_to_send, self.current_time)
                    self.schedule_event(end_time, EventType.FRAME_DEPARTURE, 
                                      {'node': source_node, 'frame': frame_to_send})
    
    def process_frame_departure(self, data: Dict) -> None:
        """Process frame departure event"""
        node = data['node']
        frame = node.complete_transmission(self.current_time)
        
        self.results['frames'].append({
            'frame_id': frame.id,
            'priority': frame.priority,
            'size': frame.size,
            'arrival_time': frame.arrival_time,
            'transmission_time': frame.transmission_time,
            'completion_time': frame.completion_time,
            'latency': frame.completion_time - frame.arrival_time,
            'dropped': frame.dropped
        })
        
        # Check if there are more frames to transmit
        next_frame = node.select_next_frame(self.current_time)
        if next_frame:
            frame_to_send, queue = next_frame
            end_time = node.start_transmission(frame_to_send, self.current_time)
            self.schedule_event(end_time, EventType.FRAME_DEPARTURE,
                              {'node': node, 'frame': frame_to_send})
    
    def run(self, duration: float) -> Dict:
        """Run simulation"""
        logger.info(f"Starting simulation for {duration} seconds")
        
        # Schedule periodic measurements
        measurement_interval = 0.1  # 100ms
        next_measurement = measurement_interval
        while next_measurement <= duration:
            self.schedule_event(next_measurement, EventType.MEASUREMENT, None)
            next_measurement += measurement_interval
        
        # Process events
        while self.event_queue:
            event_time, event_type, data = heapq.heappop(self.event_queue)
            
            if event_time > duration:
                break
            
            self.current_time = event_time
            
            if event_type == EventType.FRAME_ARRIVAL:
                self.process_frame_arrival(data)
            elif event_type == EventType.FRAME_DEPARTURE:
                self.process_frame_departure(data)
            elif event_type == EventType.MEASUREMENT:
                self.collect_statistics()
        
        # Final statistics
        self.compile_results()
        
        return self.results
    
    def collect_statistics(self) -> None:
        """Collect periodic statistics"""
        snapshot = {
            'time': self.current_time,
            'nodes': {}
        }
        
        for node_id, node in self.nodes.items():
            snapshot['nodes'][node_id] = {
                'frames_transmitted': node.statistics['frames_transmitted'],
                'frames_dropped': node.statistics['frames_dropped'],
                'utilization': node.statistics['bytes_transmitted'] * 8 / (node.link_speed_bps * self.current_time) if self.current_time > 0 else 0
            }
        
        self.results['events'].append(snapshot)
    
    def compile_results(self) -> None:
        """Compile final simulation results"""
        total_frames = len(self.results['frames'])
        dropped_frames = sum(1 for f in self.results['frames'] if f['dropped'])
        
        latencies = [f['latency'] for f in self.results['frames'] if not f['dropped']]
        
        if latencies:
            self.results['statistics'] = {
                'total_frames': total_frames,
                'dropped_frames': dropped_frames,
                'drop_rate': dropped_frames / total_frames if total_frames > 0 else 0,
                'avg_latency': np.mean(latencies),
                'max_latency': np.max(latencies),
                'min_latency': np.min(latencies),
                'p50_latency': np.percentile(latencies, 50),
                'p95_latency': np.percentile(latencies, 95),
                'p99_latency': np.percentile(latencies, 99),
                'latency_std': np.std(latencies)
            }
            
            # Calculate jitter
            if len(latencies) > 1:
                jitter = [abs(latencies[i] - latencies[i-1]) for i in range(1, len(latencies))]
                self.results['statistics']['avg_jitter'] = np.mean(jitter)
                self.results['statistics']['max_jitter'] = np.max(jitter)


def run_automotive_scenario():
    """Run automotive ADAS scenario simulation"""
    
    sim = NetworkSimulator()
    
    # Create network nodes
    ecu = sim.add_node("ECU", link_speed_mbps=1000)
    
    # Configure CBS for different traffic classes
    ecu.configure_cbs(priority=7, idle_slope_mbps=5)    # Control messages
    ecu.configure_cbs(priority=6, idle_slope_mbps=100)  # Camera streams
    ecu.configure_cbs(priority=5, idle_slope_mbps=150)  # LiDAR data
    ecu.configure_cbs(priority=3, idle_slope_mbps=50)   # Diagnostics
    ecu.configure_cbs(priority=0, idle_slope_mbps=100)  # Best effort
    
    # Generate traffic
    duration = 10.0  # 10 second simulation
    
    # Control messages (high priority, low bandwidth)
    sim.generate_traffic("ECU", "Actuator", "cbr", duration, 
                        rate_mbps=2, priority=7, frame_size=256)
    
    # Camera streams (4 cameras)
    for i in range(4):
        sim.generate_traffic("ECU", f"Display{i}", "cbr", duration,
                           rate_mbps=25, priority=6, frame_size=1500)
    
    # LiDAR data (bursty)
    sim.generate_traffic("ECU", "Processor", "burst", duration,
                        rate_mbps=100, priority=5, frame_size=9000)
    
    # Background traffic
    sim.generate_traffic("ECU", "Logger", "poisson", duration,
                        rate_mbps=200, priority=0, frame_size=1500)
    
    # Run simulation
    results = sim.run(duration)
    
    # Print results
    print("\n" + "="*60)
    print("Automotive ADAS Simulation Results")
    print("="*60)
    
    stats = results['statistics']
    print(f"Total frames: {stats['total_frames']}")
    print(f"Dropped frames: {stats['dropped_frames']} ({stats['drop_rate']*100:.2f}%)")
    print(f"Average latency: {stats['avg_latency']*1000:.2f} ms")
    print(f"95th percentile latency: {stats['p95_latency']*1000:.2f} ms")
    print(f"99th percentile latency: {stats['p99_latency']*1000:.2f} ms")
    print(f"Maximum latency: {stats['max_latency']*1000:.2f} ms")
    print(f"Average jitter: {stats.get('avg_jitter', 0)*1000:.2f} ms")
    
    # Save results
    with open('simulation_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results


if __name__ == "__main__":
    results = run_automotive_scenario()
    
    # Additional analysis
    print("\n" + "="*60)
    print("Per-Priority Analysis")
    print("="*60)
    
    for priority in range(8):
        priority_frames = [f for f in results['frames'] if f['priority'] == priority]
        if priority_frames:
            latencies = [f['latency'] for f in priority_frames if not f['dropped']]
            if latencies:
                print(f"Priority {priority}:")
                print(f"  Frames: {len(priority_frames)}")
                print(f"  Avg latency: {np.mean(latencies)*1000:.2f} ms")
                print(f"  Max latency: {np.max(latencies)*1000:.2f} ms")