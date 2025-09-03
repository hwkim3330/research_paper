#!/usr/bin/env python3
"""
CBS Configuration Validation and Optimization Tool
Advanced validation, optimization, and configuration management for CBS implementations
"""

import json
import yaml
import logging
import argparse
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import math
import copy
import itertools

import pandas as pd
import numpy as np
from jsonschema import validate, ValidationError
import networkx as nx

# Local imports
import sys
sys.path.append(str(Path(__file__).parent))

from cbs_calculator import CBSCalculator, StreamConfig, TrafficType, CBSParameters

class ValidationLevel(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class OptimizationObjective(Enum):
    """Optimization objectives"""
    MINIMIZE_LATENCY = "minimize_latency"
    MAXIMIZE_EFFICIENCY = "maximize_efficiency"
    MINIMIZE_BANDWIDTH = "minimize_bandwidth"
    BALANCE_QOS = "balance_qos"

@dataclass
class ValidationResult:
    """Validation result for a single check"""
    level: ValidationLevel
    category: str
    message: str
    details: Dict[str, Any]
    suggestions: List[str]
    affected_streams: List[str]

@dataclass  
class OptimizationResult:
    """Optimization result"""
    objective: OptimizationObjective
    original_score: float
    optimized_score: float
    improvement_percent: float
    optimized_streams: List[StreamConfig]
    optimization_log: List[str]

class CBSConfigValidator:
    """Advanced CBS configuration validator and optimizer"""
    
    # JSON Schema for stream configuration validation
    STREAM_CONFIG_SCHEMA = {
        "type": "object",
        "required": ["streams", "network"],
        "properties": {
            "streams": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "traffic_type", "bitrate_mbps", "priority"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "traffic_type": {"type": "string", "enum": [t.value for t in TrafficType]},
                        "bitrate_mbps": {"type": "number", "minimum": 0.001, "maximum": 10000},
                        "fps": {"type": "integer", "minimum": 1, "maximum": 1000},
                        "resolution": {"type": "string"},
                        "priority": {"type": "integer", "minimum": 0, "maximum": 7},
                        "max_latency_ms": {"type": "number", "minimum": 0.001, "maximum": 10000},
                        "max_jitter_ms": {"type": "number", "minimum": 0.001, "maximum": 1000}
                    }
                }
            },
            "network": {
                "type": "object",
                "required": ["link_speed_mbps"],
                "properties": {
                    "link_speed_mbps": {"type": "number", "enum": [10, 100, 1000, 10000]},
                    "topology": {"type": "string", "enum": ["point_to_point", "switched", "ring", "daisy_chain"]},
                    "max_hops": {"type": "integer", "minimum": 1, "maximum": 10}
                }
            }
        }
    }
    
    def __init__(self):
        """Initialize validator"""
        self.logger = self._setup_logging()
        self.calculator = CBSCalculator()
        self.validation_rules = self._load_validation_rules()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules and thresholds"""
        return {
            # Traffic-specific validation rules
            "traffic_rules": {
                TrafficType.SAFETY_CRITICAL: {
                    "max_latency_ms": 10,
                    "max_jitter_ms": 1,
                    "min_priority": 6,
                    "required_redundancy": True
                },
                TrafficType.VIDEO_4K: {
                    "max_latency_ms": 50,
                    "max_jitter_ms": 5,
                    "min_priority": 4,
                    "min_bitrate_mbps": 15,
                    "max_bitrate_mbps": 100
                },
                TrafficType.VIDEO_1080P: {
                    "max_latency_ms": 100,
                    "max_jitter_ms": 10,
                    "min_priority": 3,
                    "min_bitrate_mbps": 5,
                    "max_bitrate_mbps": 50
                }
            },
            
            # Network-level rules
            "network_rules": {
                "max_utilization_percent": 80,
                "min_efficiency_percent": 70,
                "max_streams_per_priority": 8,
                "priority_separation_required": True
            },
            
            # CBS-specific rules
            "cbs_rules": {
                "max_idle_slope_ratio": 0.5,  # idleSlope / linkSpeed
                "max_credit_ratio": 0.1,      # hiCredit / max_frame_size
                "min_headroom_percent": 5,
                "max_headroom_percent": 200
            }
        }
    
    def validate_configuration(self, config_data: Dict[str, Any]) -> List[ValidationResult]:
        """Comprehensive configuration validation"""
        results = []
        
        try:
            # Step 1: Schema validation
            results.extend(self._validate_schema(config_data))
            
            # Step 2: Parse configuration
            streams, network_config = self._parse_configuration(config_data)
            
            if not streams:
                results.append(ValidationResult(
                    level=ValidationLevel.CRITICAL,
                    category="Configuration",
                    message="No valid streams found in configuration",
                    details={},
                    suggestions=["Check stream definitions for correct format"],
                    affected_streams=[]
                ))
                return results
            
            # Step 3: Individual stream validation
            results.extend(self._validate_streams(streams))
            
            # Step 4: Network-level validation
            results.extend(self._validate_network_constraints(streams, network_config))
            
            # Step 5: CBS parameter validation
            results.extend(self._validate_cbs_parameters(streams))
            
            # Step 6: QoS requirement validation
            results.extend(self._validate_qos_requirements(streams))
            
            # Step 7: Topology and routing validation
            results.extend(self._validate_topology(streams, network_config))
            
            # Step 8: Performance prediction validation
            results.extend(self._validate_performance_predictions(streams))
            
        except Exception as e:
            results.append(ValidationResult(
                level=ValidationLevel.CRITICAL,
                category="Validation",
                message=f"Validation failed with error: {str(e)}",
                details={"error": str(e)},
                suggestions=["Check configuration format and content"],
                affected_streams=[]
            ))
        
        return results
    
    def _validate_schema(self, config_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate configuration against JSON schema"""
        results = []
        
        try:
            validate(instance=config_data, schema=self.STREAM_CONFIG_SCHEMA)
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                category="Schema",
                message="Configuration schema validation passed",
                details={},
                suggestions=[],
                affected_streams=[]
            ))
        except ValidationError as e:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="Schema",
                message=f"Schema validation failed: {e.message}",
                details={"path": list(e.absolute_path), "schema_path": list(e.schema_path)},
                suggestions=["Fix configuration format according to schema requirements"],
                affected_streams=[]
            ))
        
        return results
    
    def _parse_configuration(self, config_data: Dict[str, Any]) -> Tuple[List[StreamConfig], Dict[str, Any]]:
        """Parse configuration data into StreamConfig objects"""
        streams = []
        
        for stream_data in config_data.get("streams", []):
            try:
                stream = StreamConfig(
                    name=stream_data["name"],
                    traffic_type=TrafficType(stream_data["traffic_type"]),
                    bitrate_mbps=float(stream_data["bitrate_mbps"]),
                    fps=int(stream_data.get("fps", 30)),
                    resolution=stream_data.get("resolution", "N/A"),
                    priority=int(stream_data["priority"]),
                    max_latency_ms=float(stream_data.get("max_latency_ms", 100)),
                    max_jitter_ms=float(stream_data.get("max_jitter_ms", 10))
                )
                streams.append(stream)
            except (ValueError, KeyError) as e:
                self.logger.error(f"Failed to parse stream {stream_data.get('name', 'unknown')}: {e}")
        
        network_config = config_data.get("network", {})
        
        return streams, network_config
    
    def _validate_streams(self, streams: List[StreamConfig]) -> List[ValidationResult]:
        """Validate individual stream configurations"""
        results = []
        
        for stream in streams:
            # Traffic type specific validation
            if stream.traffic_type in self.validation_rules["traffic_rules"]:
                rules = self.validation_rules["traffic_rules"][stream.traffic_type]
                
                # Latency requirement check
                if stream.max_latency_ms > rules.get("max_latency_ms", float('inf')):
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="QoS",
                        message=f"Latency requirement too high for {stream.traffic_type.value}",
                        details={
                            "stream_latency": stream.max_latency_ms,
                            "recommended_max": rules["max_latency_ms"]
                        },
                        suggestions=[f"Consider reducing latency requirement to ≤{rules['max_latency_ms']}ms"],
                        affected_streams=[stream.name]
                    ))
                
                # Priority check
                if stream.priority < rules.get("min_priority", 0):
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="Priority",
                        message=f"Priority too low for {stream.traffic_type.value}",
                        details={
                            "stream_priority": stream.priority,
                            "recommended_min": rules["min_priority"]
                        },
                        suggestions=[f"Consider increasing priority to ≥{rules['min_priority']}"],
                        affected_streams=[stream.name]
                    ))
                
                # Bitrate range check
                if "min_bitrate_mbps" in rules and stream.bitrate_mbps < rules["min_bitrate_mbps"]:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="Bandwidth",
                        message=f"Bitrate too low for {stream.traffic_type.value}",
                        details={
                            "stream_bitrate": stream.bitrate_mbps,
                            "recommended_min": rules["min_bitrate_mbps"]
                        },
                        suggestions=[f"Consider increasing bitrate to ≥{rules['min_bitrate_mbps']}Mbps"],
                        affected_streams=[stream.name]
                    ))
        
        # Check for duplicate stream names
        stream_names = [s.name for s in streams]
        duplicates = set([name for name in stream_names if stream_names.count(name) > 1])
        if duplicates:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="Configuration",
                message="Duplicate stream names found",
                details={"duplicate_names": list(duplicates)},
                suggestions=["Ensure all stream names are unique"],
                affected_streams=list(duplicates)
            ))
        
        return results
    
    def _validate_network_constraints(self, streams: List[StreamConfig], 
                                    network_config: Dict[str, Any]) -> List[ValidationResult]:
        """Validate network-level constraints"""
        results = []
        
        # Set up calculator with network configuration
        link_speed_mbps = network_config.get("link_speed_mbps", 1000)
        calculator = CBSCalculator(link_speed_mbps=link_speed_mbps)
        
        # Calculate CBS parameters
        try:
            cbs_params = calculator.calculate_multi_stream(streams)
            
            # Check total bandwidth utilization
            total_reserved = sum(params.reserved_bandwidth_mbps for params in cbs_params.values())
            utilization_percent = (total_reserved / link_speed_mbps) * 100
            
            max_utilization = self.validation_rules["network_rules"]["max_utilization_percent"]
            if utilization_percent > max_utilization:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="Bandwidth",
                    message="Network utilization exceeds recommended threshold",
                    details={
                        "utilization_percent": utilization_percent,
                        "max_recommended": max_utilization,
                        "total_reserved_mbps": total_reserved,
                        "link_speed_mbps": link_speed_mbps
                    },
                    suggestions=[
                        "Reduce stream bitrates",
                        "Increase link speed",
                        "Distribute streams across multiple links"
                    ],
                    affected_streams=[s.name for s in streams]
                ))
            
            # Check bandwidth efficiency
            total_actual = sum(s.bitrate_mbps for s in streams)
            efficiency_percent = (total_actual / total_reserved) * 100 if total_reserved > 0 else 0
            
            min_efficiency = self.validation_rules["network_rules"]["min_efficiency_percent"]
            if efficiency_percent < min_efficiency:
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    category="Efficiency",
                    message="Low bandwidth efficiency detected",
                    details={
                        "efficiency_percent": efficiency_percent,
                        "min_recommended": min_efficiency,
                        "wasted_bandwidth_mbps": total_reserved - total_actual
                    },
                    suggestions=[
                        "Optimize headroom parameters",
                        "Review traffic type classifications"
                    ],
                    affected_streams=[]
                ))
            
            # Check priority distribution
            priority_counts = {}
            for stream in streams:
                priority_counts[stream.priority] = priority_counts.get(stream.priority, 0) + 1
            
            max_per_priority = self.validation_rules["network_rules"]["max_streams_per_priority"]
            for priority, count in priority_counts.items():
                if count > max_per_priority:
                    affected_streams = [s.name for s in streams if s.priority == priority]
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="Priority",
                        message=f"Too many streams in priority class {priority}",
                        details={
                            "priority": priority,
                            "stream_count": count,
                            "max_recommended": max_per_priority
                        },
                        suggestions=[
                            "Distribute streams across different priority levels",
                            "Combine related streams if possible"
                        ],
                        affected_streams=affected_streams
                    ))
        
        except Exception as e:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="Calculation",
                message=f"Failed to calculate CBS parameters: {str(e)}",
                details={"error": str(e)},
                suggestions=["Check stream configuration validity"],
                affected_streams=[s.name for s in streams]
            ))
        
        return results
    
    def _validate_cbs_parameters(self, streams: List[StreamConfig]) -> List[ValidationResult]:
        """Validate CBS parameters against implementation constraints"""
        results = []
        
        calculator = CBSCalculator()
        
        try:
            for stream in streams:
                params = calculator.calculate_cbs_params(stream)
                
                # Check idle slope ratio
                idle_slope_ratio = params.idle_slope / calculator.link_speed_bps
                max_ratio = self.validation_rules["cbs_rules"]["max_idle_slope_ratio"]
                
                if idle_slope_ratio > max_ratio:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="CBS",
                        message=f"idleSlope ratio too high for stream {stream.name}",
                        details={
                            "idle_slope_ratio": idle_slope_ratio,
                            "max_recommended": max_ratio,
                            "idle_slope_mbps": params.idle_slope / 1_000_000
                        },
                        suggestions=[
                            "Reduce stream bitrate",
                            "Increase link speed",
                            "Reduce headroom percentage"
                        ],
                        affected_streams=[stream.name]
                    ))
                
                # Check credit range
                max_frame_bits = 1518 * 8
                credit_ratio = abs(params.hi_credit) / max_frame_bits
                max_credit_ratio = self.validation_rules["cbs_rules"]["max_credit_ratio"]
                
                if credit_ratio > max_credit_ratio:
                    results.append(ValidationResult(
                        level=ValidationLevel.INFO,
                        category="CBS",
                        message=f"Credit range large for stream {stream.name}",
                        details={
                            "credit_ratio": credit_ratio,
                            "hi_credit": params.hi_credit,
                            "max_frame_bits": max_frame_bits
                        },
                        suggestions=["Review burst requirements and frame sizes"],
                        affected_streams=[stream.name]
                    ))
                
                # Check efficiency
                min_efficiency = self.validation_rules["network_rules"]["min_efficiency_percent"]
                if params.efficiency_percent < min_efficiency:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="Efficiency",
                        message=f"Low efficiency for stream {stream.name}",
                        details={
                            "efficiency_percent": params.efficiency_percent,
                            "min_recommended": min_efficiency,
                            "actual_mbps": params.actual_bandwidth_mbps,
                            "reserved_mbps": params.reserved_bandwidth_mbps
                        },
                        suggestions=["Optimize headroom parameters for better efficiency"],
                        affected_streams=[stream.name]
                    ))
        
        except Exception as e:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="CBS",
                message=f"CBS parameter validation failed: {str(e)}",
                details={"error": str(e)},
                suggestions=["Check stream configuration"],
                affected_streams=[]
            ))
        
        return results
    
    def _validate_qos_requirements(self, streams: List[StreamConfig]) -> List[ValidationResult]:
        """Validate QoS requirements and feasibility"""
        results = []
        
        calculator = CBSCalculator()
        
        try:
            for stream in streams:
                params = calculator.calculate_cbs_params(stream)
                delay_analysis = calculator.calculate_theoretical_delay(stream, params)
                
                # Check latency requirement
                predicted_latency = delay_analysis["total_delay_ms"]
                if predicted_latency > stream.max_latency_ms:
                    results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        category="QoS",
                        message=f"Latency requirement cannot be met for {stream.name}",
                        details={
                            "required_latency_ms": stream.max_latency_ms,
                            "predicted_latency_ms": predicted_latency,
                            "violation_ms": predicted_latency - stream.max_latency_ms,
                            "delay_components": delay_analysis
                        },
                        suggestions=[
                            "Increase stream priority",
                            "Reduce other traffic loads",
                            "Increase link speed",
                            "Relax latency requirement"
                        ],
                        affected_streams=[stream.name]
                    ))
                elif predicted_latency > stream.max_latency_ms * 0.8:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="QoS",
                        message=f"Latency close to limit for {stream.name}",
                        details={
                            "required_latency_ms": stream.max_latency_ms,
                            "predicted_latency_ms": predicted_latency,
                            "margin_ms": stream.max_latency_ms - predicted_latency
                        },
                        suggestions=["Consider increasing priority or reducing other loads"],
                        affected_streams=[stream.name]
                    ))
                
                # Check jitter feasibility (simplified check)
                # In real implementation, this would require more complex analysis
                burst_analysis = calculator.calculate_burst_capacity(params)
                if burst_analysis["max_burst_duration_ms"] > stream.max_jitter_ms * 2:
                    results.append(ValidationResult(
                        level=ValidationLevel.INFO,
                        category="QoS",
                        message=f"Jitter requirement may be challenging for {stream.name}",
                        details={
                            "required_jitter_ms": stream.max_jitter_ms,
                            "burst_duration_ms": burst_analysis["max_burst_duration_ms"]
                        },
                        suggestions=["Review burst characteristics and jitter requirements"],
                        affected_streams=[stream.name]
                    ))
        
        except Exception as e:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="QoS",
                message=f"QoS validation failed: {str(e)}",
                details={"error": str(e)},
                suggestions=["Check QoS requirement specifications"],
                affected_streams=[]
            ))
        
        return results
    
    def _validate_topology(self, streams: List[StreamConfig], 
                          network_config: Dict[str, Any]) -> List[ValidationResult]:
        """Validate network topology constraints"""
        results = []
        
        topology = network_config.get("topology", "point_to_point")
        max_hops = network_config.get("max_hops", 1)
        
        # Multi-hop latency analysis
        if max_hops > 1:
            for stream in streams:
                # Estimate additional latency per hop (simplified)
                per_hop_latency = 0.01  # 10μs processing + forwarding delay
                additional_latency = (max_hops - 1) * per_hop_latency
                
                total_latency_budget = stream.max_latency_ms - additional_latency
                
                if total_latency_budget < 0:
                    results.append(ValidationResult(
                        level=ValidationLevel.ERROR,
                        category="Topology",
                        message=f"Multi-hop latency exceeds budget for {stream.name}",
                        details={
                            "max_hops": max_hops,
                            "per_hop_latency_ms": per_hop_latency,
                            "additional_latency_ms": additional_latency,
                            "stream_budget_ms": stream.max_latency_ms
                        },
                        suggestions=[
                            "Reduce number of hops",
                            "Use direct connections for critical streams",
                            "Relax latency requirements"
                        ],
                        affected_streams=[stream.name]
                    ))
                elif total_latency_budget < stream.max_latency_ms * 0.5:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="Topology",
                        message=f"Limited latency budget remaining for {stream.name}",
                        details={
                            "remaining_budget_ms": total_latency_budget,
                            "budget_utilization_percent": ((stream.max_latency_ms - total_latency_budget) / stream.max_latency_ms) * 100
                        },
                        suggestions=["Consider optimizing topology for critical streams"],
                        affected_streams=[stream.name]
                    ))
        
        # Topology-specific validations
        if topology == "ring":
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                category="Topology",
                message="Ring topology detected - ensure redundancy paths are configured",
                details={"topology": topology},
                suggestions=["Configure rapid spanning tree or equivalent for redundancy"],
                affected_streams=[]
            ))
        
        return results
    
    def _validate_performance_predictions(self, streams: List[StreamConfig]) -> List[ValidationResult]:
        """Validate performance predictions and constraints"""
        results = []
        
        calculator = CBSCalculator()
        
        # Analyze interference between streams
        try:
            # Group streams by priority
            priority_groups = {}
            for stream in streams:
                if stream.priority not in priority_groups:
                    priority_groups[stream.priority] = []
                priority_groups[stream.priority].append(stream)
            
            # Check for potential interference
            for priority in sorted(priority_groups.keys(), reverse=True):
                group_streams = priority_groups[priority]
                
                if len(group_streams) > 1:
                    # Calculate total bandwidth for this priority
                    total_bandwidth = sum(s.bitrate_mbps for s in group_streams)
                    
                    # Simple interference check
                    for stream in group_streams:
                        other_bandwidth = total_bandwidth - stream.bitrate_mbps
                        
                        # Estimate interference impact (simplified model)
                        interference_factor = other_bandwidth / calculator.link_speed_mbps
                        
                        if interference_factor > 0.1:  # >10% interference
                            results.append(ValidationResult(
                                level=ValidationLevel.INFO,
                                category="Performance",
                                message=f"Potential interference detected for {stream.name}",
                                details={
                                    "stream_priority": priority,
                                    "other_streams_bandwidth": other_bandwidth,
                                    "interference_factor": interference_factor
                                },
                                suggestions=[
                                    "Consider separating streams into different priority classes",
                                    "Analyze detailed interference patterns"
                                ],
                                affected_streams=[stream.name]
                            ))
            
        except Exception as e:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category="Performance",
                message=f"Performance prediction validation incomplete: {str(e)}",
                details={"error": str(e)},
                suggestions=["Manual performance analysis recommended"],
                affected_streams=[]
            ))
        
        return results
    
    def optimize_configuration(self, streams: List[StreamConfig], 
                             objective: OptimizationObjective = OptimizationObjective.BALANCE_QOS) -> OptimizationResult:
        """Optimize stream configuration for specified objective"""
        
        self.logger.info(f"Starting optimization with objective: {objective.value}")
        
        original_streams = copy.deepcopy(streams)
        original_score = self._calculate_objective_score(streams, objective)
        
        optimization_log = [f"Starting optimization: {objective.value}"]
        optimization_log.append(f"Original score: {original_score:.3f}")
        
        optimized_streams = copy.deepcopy(streams)
        
        try:
            if objective == OptimizationObjective.MINIMIZE_LATENCY:
                optimized_streams = self._optimize_for_latency(optimized_streams, optimization_log)
            elif objective == OptimizationObjective.MAXIMIZE_EFFICIENCY:
                optimized_streams = self._optimize_for_efficiency(optimized_streams, optimization_log)
            elif objective == OptimizationObjective.MINIMIZE_BANDWIDTH:
                optimized_streams = self._optimize_for_bandwidth(optimized_streams, optimization_log)
            elif objective == OptimizationObjective.BALANCE_QOS:
                optimized_streams = self._optimize_for_balanced_qos(optimized_streams, optimization_log)
            
            # Calculate optimized score
            optimized_score = self._calculate_objective_score(optimized_streams, objective)
            improvement_percent = ((optimized_score - original_score) / abs(original_score)) * 100 if original_score != 0 else 0
            
            optimization_log.append(f"Optimized score: {optimized_score:.3f}")
            optimization_log.append(f"Improvement: {improvement_percent:.1f}%")
            
            return OptimizationResult(
                objective=objective,
                original_score=original_score,
                optimized_score=optimized_score,
                improvement_percent=improvement_percent,
                optimized_streams=optimized_streams,
                optimization_log=optimization_log
            )
        
        except Exception as e:
            optimization_log.append(f"Optimization failed: {str(e)}")
            self.logger.error(f"Optimization failed: {e}")
            
            return OptimizationResult(
                objective=objective,
                original_score=original_score,
                optimized_score=original_score,
                improvement_percent=0,
                optimized_streams=original_streams,
                optimization_log=optimization_log
            )
    
    def _calculate_objective_score(self, streams: List[StreamConfig], 
                                 objective: OptimizationObjective) -> float:
        """Calculate objective function score"""
        calculator = CBSCalculator()
        
        try:
            # Calculate CBS parameters
            params = calculator.optimize_parameters(streams)
            
            if objective == OptimizationObjective.MINIMIZE_LATENCY:
                # Score = negative average latency (minimize)
                total_latency = 0
                for stream in streams:
                    delay_analysis = calculator.calculate_theoretical_delay(stream, params[stream.name])
                    total_latency += delay_analysis["total_delay_ms"]
                return -total_latency / len(streams) if streams else 0
            
            elif objective == OptimizationObjective.MAXIMIZE_EFFICIENCY:
                # Score = average efficiency
                total_efficiency = sum(p.efficiency_percent for p in params.values())
                return total_efficiency / len(params) if params else 0
            
            elif objective == OptimizationObjective.MINIMIZE_BANDWIDTH:
                # Score = negative total reserved bandwidth
                total_reserved = sum(p.reserved_bandwidth_mbps for p in params.values())
                return -total_reserved
            
            elif objective == OptimizationObjective.BALANCE_QOS:
                # Score = weighted combination of metrics
                avg_efficiency = sum(p.efficiency_percent for p in params.values()) / len(params) if params else 0
                total_reserved = sum(p.reserved_bandwidth_mbps for p in params.values())
                utilization = (total_reserved / calculator.link_speed_mbps) * 100
                
                # Penalty for high utilization
                utilization_penalty = max(0, utilization - 80) * 2
                
                return avg_efficiency - utilization_penalty
        
        except Exception:
            return 0
    
    def _optimize_for_latency(self, streams: List[StreamConfig], log: List[str]) -> List[StreamConfig]:
        """Optimize configuration to minimize latency"""
        log.append("Optimizing for minimum latency...")
        
        # Strategy: Increase priorities for latency-sensitive streams
        for stream in streams:
            if stream.max_latency_ms < 20 and stream.priority < 6:
                old_priority = stream.priority
                stream.priority = min(7, stream.priority + 2)
                log.append(f"Increased priority for {stream.name}: {old_priority} → {stream.priority}")
        
        return streams
    
    def _optimize_for_efficiency(self, streams: List[StreamConfig], log: List[str]) -> List[StreamConfig]:
        """Optimize configuration to maximize bandwidth efficiency"""
        log.append("Optimizing for maximum efficiency...")
        
        # Strategy: Adjust traffic type classifications for better headroom
        calculator = CBSCalculator()
        
        for stream in streams:
            # Try different traffic type classifications to improve efficiency
            original_type = stream.traffic_type
            
            # Test more aggressive classification for some streams
            if stream.traffic_type == TrafficType.VIDEO_1080P and stream.bitrate_mbps < 20:
                stream.traffic_type = TrafficType.VIDEO_720P
                
                # Calculate efficiency improvement
                original_params = calculator.calculate_cbs_params(StreamConfig(
                    stream.name, original_type, stream.bitrate_mbps, stream.fps,
                    stream.resolution, stream.priority, stream.max_latency_ms, stream.max_jitter_ms
                ))
                new_params = calculator.calculate_cbs_params(stream)
                
                if new_params.efficiency_percent > original_params.efficiency_percent + 5:
                    log.append(f"Improved efficiency for {stream.name}: {original_type.value} → {stream.traffic_type.value}")
                else:
                    stream.traffic_type = original_type  # Revert if no significant improvement
        
        return streams
    
    def _optimize_for_bandwidth(self, streams: List[StreamConfig], log: List[str]) -> List[StreamConfig]:
        """Optimize configuration to minimize total bandwidth usage"""
        log.append("Optimizing for minimum bandwidth usage...")
        
        # Strategy: Reduce bitrates where possible while meeting QoS
        for stream in streams:
            if stream.traffic_type in [TrafficType.INFOTAINMENT, TrafficType.DIAGNOSTICS]:
                original_bitrate = stream.bitrate_mbps
                # Reduce by 10-20% for non-critical streams
                stream.bitrate_mbps = stream.bitrate_mbps * 0.85
                log.append(f"Reduced bitrate for {stream.name}: {original_bitrate:.1f} → {stream.bitrate_mbps:.1f} Mbps")
        
        return streams
    
    def _optimize_for_balanced_qos(self, streams: List[StreamConfig], log: List[str]) -> List[StreamConfig]:
        """Optimize for balanced QoS across all streams"""
        log.append("Optimizing for balanced QoS...")
        
        # Strategy: Balance priorities and adjust parameters for overall system optimization
        calculator = CBSCalculator()
        
        # Calculate current parameters and identify issues
        try:
            params = calculator.optimize_parameters(streams, target_utilization=75)
            
            # Adjust priorities to balance the load
            priority_loads = {}
            for stream in streams:
                if stream.priority not in priority_loads:
                    priority_loads[stream.priority] = 0
                priority_loads[stream.priority] += stream.bitrate_mbps
            
            # Redistribute if some priorities are overloaded
            for priority, load in priority_loads.items():
                if load > 100:  # More than 100 Mbps in one priority
                    # Find streams to move to lower priority
                    priority_streams = [s for s in streams if s.priority == priority]
                    priority_streams.sort(key=lambda s: s.max_latency_ms, reverse=True)  # Most tolerant first
                    
                    for i, stream in enumerate(priority_streams):
                        if i > 0 and stream.priority > 0:  # Keep at least one in current priority
                            old_priority = stream.priority
                            stream.priority = max(0, stream.priority - 1)
                            log.append(f"Rebalanced priority for {stream.name}: {old_priority} → {stream.priority}")
                            break
        
        except Exception as e:
            log.append(f"Balanced optimization encountered issue: {str(e)}")
        
        return streams
    
    def generate_validation_report(self, results: List[ValidationResult], 
                                 output_file: str = "validation_report.md") -> None:
        """Generate comprehensive validation report"""
        
        # Categorize results by level
        critical_results = [r for r in results if r.level == ValidationLevel.CRITICAL]
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        warning_results = [r for r in results if r.level == ValidationLevel.WARNING]
        info_results = [r for r in results if r.level == ValidationLevel.INFO]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# CBS Configuration Validation Report\n\n")
            f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Issues:** {len(results)}\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"- 🔴 **Critical Issues:** {len(critical_results)}\n")
            f.write(f"- ❌ **Errors:** {len(error_results)}\n") 
            f.write(f"- ⚠️  **Warnings:** {len(warning_results)}\n")
            f.write(f"- ℹ️  **Information:** {len(info_results)}\n\n")
            
            # Overall status
            if critical_results or error_results:
                f.write("**Status:** ❌ Configuration has critical issues that must be resolved\n\n")
            elif warning_results:
                f.write("**Status:** ⚠️ Configuration has warnings that should be addressed\n\n") 
            else:
                f.write("**Status:** ✅ Configuration validation passed\n\n")
            
            # Detailed results by category
            for level_name, level_results, icon in [
                ("Critical Issues", critical_results, "🔴"),
                ("Errors", error_results, "❌"),
                ("Warnings", warning_results, "⚠️"),
                ("Information", info_results, "ℹ️")
            ]:
                if level_results:
                    f.write(f"## {icon} {level_name}\n\n")
                    
                    for i, result in enumerate(level_results, 1):
                        f.write(f"### {i}. {result.message}\n\n")
                        f.write(f"**Category:** {result.category}\n")
                        
                        if result.affected_streams:
                            f.write(f"**Affected Streams:** {', '.join(result.affected_streams)}\n")
                        
                        if result.details:
                            f.write("**Details:**\n")
                            for key, value in result.details.items():
                                f.write(f"- {key}: {value}\n")
                        
                        if result.suggestions:
                            f.write("**Suggestions:**\n")
                            for suggestion in result.suggestions:
                                f.write(f"- {suggestion}\n")
                        
                        f.write("\n---\n\n")
            
            f.write("## Validation Rules Applied\n\n")
            f.write("This validation used the following rule categories:\n")
            f.write("- **Schema Validation:** JSON schema compliance\n")
            f.write("- **Traffic Rules:** Traffic-type specific constraints\n")
            f.write("- **Network Rules:** Network-level limitations\n")
            f.write("- **CBS Rules:** Credit-Based Shaper parameter constraints\n")
            f.write("- **QoS Rules:** Quality of Service requirement feasibility\n")
            f.write("- **Topology Rules:** Network topology considerations\n")
            f.write("- **Performance Rules:** Performance prediction validation\n\n")
            
            f.write(f"*Report generated by CBS Configuration Validator v1.0*\n")
        
        self.logger.info(f"Validation report generated: {output_file}")
    
    def create_config_template(self, filename: str) -> None:
        """Create configuration template file"""
        template = {
            "description": "CBS Configuration Template",
            "network": {
                "link_speed_mbps": 1000,
                "topology": "switched",
                "max_hops": 2
            },
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
                    "name": "Front_Camera_4K",
                    "traffic_type": "video_4k",
                    "bitrate_mbps": 25.0,
                    "fps": 60,
                    "resolution": "3840x2160",
                    "priority": 6,
                    "max_latency_ms": 20.0,
                    "max_jitter_ms": 3.0
                },
                {
                    "name": "Surround_Camera_HD",
                    "traffic_type": "video_1080p", 
                    "bitrate_mbps": 15.0,
                    "fps": 30,
                    "resolution": "1920x1080",
                    "priority": 5,
                    "max_latency_ms": 30.0,
                    "max_jitter_ms": 5.0
                },
                {
                    "name": "LiDAR_Main",
                    "traffic_type": "lidar",
                    "bitrate_mbps": 100.0,
                    "fps": 10,
                    "resolution": "N/A",
                    "priority": 4,
                    "max_latency_ms": 40.0,
                    "max_jitter_ms": 4.0
                }
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(template, f, indent=2)
        
        print(f"Configuration template created: {filename}")

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='CBS Configuration Validator and Optimizer')
    parser.add_argument('config_file', help='Configuration file to validate')
    parser.add_argument('--optimize', choices=['latency', 'efficiency', 'bandwidth', 'balance'],
                       help='Run optimization with specified objective')
    parser.add_argument('--output', default='validation_report.md', help='Output report file')
    parser.add_argument('--create-template', help='Create configuration template file')
    parser.add_argument('--format', choices=['yaml', 'json'], default='json', 
                       help='Configuration file format')
    
    args = parser.parse_args()
    
    # Create configuration template
    if args.create_template:
        validator = CBSConfigValidator()
        validator.create_config_template(args.create_template)
        return
    
    # Initialize validator
    validator = CBSConfigValidator()
    
    try:
        print(f"🔍 Validating configuration: {args.config_file}")
        
        # Load configuration
        with open(args.config_file, 'r') as f:
            if args.format == 'yaml':
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        # Run validation
        validation_results = validator.validate_configuration(config_data)
        
        # Count issues by level
        critical_count = len([r for r in validation_results if r.level == ValidationLevel.CRITICAL])
        error_count = len([r for r in validation_results if r.level == ValidationLevel.ERROR])
        warning_count = len([r for r in validation_results if r.level == ValidationLevel.WARNING])
        info_count = len([r for r in validation_results if r.level == ValidationLevel.INFO])
        
        print(f"\n📊 Validation Results:")
        print(f"  🔴 Critical: {critical_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  ⚠️  Warnings: {warning_count}")
        print(f"  ℹ️  Info: {info_count}")
        
        # Overall status
        if critical_count > 0 or error_count > 0:
            print(f"\n❌ Configuration has critical issues")
            exit_code = 1
        elif warning_count > 0:
            print(f"\n⚠️  Configuration has warnings")
            exit_code = 0
        else:
            print(f"\n✅ Configuration validation passed")
            exit_code = 0
        
        # Generate report
        validator.generate_validation_report(validation_results, args.output)
        print(f"📄 Detailed report: {args.output}")
        
        # Run optimization if requested
        if args.optimize:
            print(f"\n🚀 Running optimization: {args.optimize}")
            
            streams, _ = validator._parse_configuration(config_data)
            objective_map = {
                'latency': OptimizationObjective.MINIMIZE_LATENCY,
                'efficiency': OptimizationObjective.MAXIMIZE_EFFICIENCY,
                'bandwidth': OptimizationObjective.MINIMIZE_BANDWIDTH,
                'balance': OptimizationObjective.BALANCE_QOS
            }
            
            optimization_result = validator.optimize_configuration(streams, objective_map[args.optimize])
            
            print(f"📈 Optimization Results:")
            print(f"  Original score: {optimization_result.original_score:.3f}")
            print(f"  Optimized score: {optimization_result.optimized_score:.3f}")
            print(f"  Improvement: {optimization_result.improvement_percent:.1f}%")
            
            # Save optimized configuration
            optimized_filename = args.config_file.replace('.json', '_optimized.json').replace('.yaml', '_optimized.yaml')
            optimized_config = config_data.copy()
            optimized_config['streams'] = [asdict(stream) for stream in optimization_result.optimized_streams]
            
            with open(optimized_filename, 'w') as f:
                if args.format == 'yaml':
                    yaml.dump(optimized_config, f, default_flow_style=False)
                else:
                    json.dump(optimized_config, f, indent=2)
            
            print(f"💾 Optimized configuration saved: {optimized_filename}")
        
        exit(exit_code)
        
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {args.config_file}")
        exit(1)
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()