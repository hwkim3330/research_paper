#!/usr/bin/env python3
"""
CBS 파라미터 계산 및 최적화 도구
실제 차량 네트워크의 다중 영상 스트림을 위한 CBS 설정 계산
"""

import math
import json
import yaml
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import time
import csv

class TrafficType(Enum):
    """트래픽 유형 정의"""
    SAFETY_CRITICAL = "safety_critical"
    VIDEO_4K = "video_4k"
    VIDEO_1080P = "video_1080p"
    VIDEO_720P = "video_720p"
    LIDAR = "lidar"
    RADAR = "radar"
    CONTROL = "control"
    V2X = "v2x"
    INFOTAINMENT = "infotainment"
    DIAGNOSTICS = "diagnostics"
    OTA = "ota"

@dataclass
class StreamConfig:
    """스트림 구성 정보"""
    name: str
    traffic_type: TrafficType
    bitrate_mbps: float
    fps: int
    resolution: str
    priority: int
    max_latency_ms: float
    max_jitter_ms: float
    
@dataclass
class CBSParameters:
    """CBS 파라미터"""
    idle_slope: int  # bits per second
    send_slope: int  # bits per second (negative)
    hi_credit: int   # bits
    lo_credit: int   # bits
    reserved_bandwidth_mbps: float
    actual_bandwidth_mbps: float
    efficiency_percent: float

class CBSCalculator:
    """CBS 파라미터 계산기"""
    
    # 트래픽 유형별 기본 설정
    TRAFFIC_DEFAULTS = {
        TrafficType.SAFETY_CRITICAL: {
            "headroom_percent": 100,  # 100% 여유
            "burst_factor": 2.0,
            "max_frame_size": 256
        },
        TrafficType.VIDEO_4K: {
            "headroom_percent": 20,   # 20% 여유
            "burst_factor": 1.5,
            "max_frame_size": 1522
        },
        TrafficType.VIDEO_1080P: {
            "headroom_percent": 25,   # 25% 여유
            "burst_factor": 1.3,
            "max_frame_size": 1522
        },
        TrafficType.VIDEO_720P: {
            "headroom_percent": 30,   # 30% 여유
            "burst_factor": 1.2,
            "max_frame_size": 1522
        },
        TrafficType.LIDAR: {
            "headroom_percent": 15,   # 15% 여유
            "burst_factor": 1.8,
            "max_frame_size": 9000    # Jumbo frames
        },
        TrafficType.RADAR: {
            "headroom_percent": 50,   # 50% 여유
            "burst_factor": 1.5,
            "max_frame_size": 512
        },
        TrafficType.CONTROL: {
            "headroom_percent": 100,  # 100% 여유
            "burst_factor": 2.0,
            "max_frame_size": 128
        },
        TrafficType.V2X: {
            "headroom_percent": 40,   # 40% 여유
            "burst_factor": 1.6,
            "max_frame_size": 1024
        },
        TrafficType.INFOTAINMENT: {
            "headroom_percent": 10,   # 10% 여유
            "burst_factor": 1.1,
            "max_frame_size": 1522
        },
        TrafficType.DIAGNOSTICS: {
            "headroom_percent": 20,   # 20% 여유
            "burst_factor": 1.2,
            "max_frame_size": 1522
        },
        TrafficType.OTA: {
            "headroom_percent": 5,    # 5% 여유
            "burst_factor": 1.0,
            "max_frame_size": 1522
        }
    }
    
    def __init__(self, link_speed_mbps: float = 1000):
        """
        초기화
        
        Args:
            link_speed_mbps: 링크 속도 (Mbps)
        """
        self.link_speed_mbps = link_speed_mbps
        self.link_speed_bps = link_speed_mbps * 1_000_000
        
    def calculate_cbs_params(self, 
                           stream: StreamConfig,
                           custom_headroom: float = None) -> CBSParameters:
        """
        스트림에 대한 CBS 파라미터 계산
        
        Args:
            stream: 스트림 구성
            custom_headroom: 사용자 정의 헤드룸 (%)
            
        Returns:
            CBS 파라미터
        """
        # 트래픽 유형별 기본값 가져오기
        defaults = self.TRAFFIC_DEFAULTS[stream.traffic_type]
        
        # 헤드룸 결정
        headroom = custom_headroom if custom_headroom else defaults["headroom_percent"]
        
        # 예약 대역폭 계산 (헤드룸 포함)
        reserved_mbps = stream.bitrate_mbps * (1 + headroom / 100)
        reserved_bps = reserved_mbps * 1_000_000
        
        # idleSlope 계산
        idle_slope = int(reserved_bps)
        
        # sendSlope 계산
        send_slope = int(idle_slope - self.link_speed_bps)
        
        # 최대 프레임 크기
        max_frame_size = defaults["max_frame_size"]
        
        # hiCredit 계산 (버스트 허용량)
        burst_factor = defaults["burst_factor"]
        hi_credit = int((max_frame_size * 8 * idle_slope * burst_factor) / self.link_speed_bps)
        
        # loCredit 계산
        lo_credit = int((max_frame_size * 8 * send_slope) / self.link_speed_bps)
        
        # 효율성 계산
        efficiency = (stream.bitrate_mbps / reserved_mbps) * 100
        
        return CBSParameters(
            idle_slope=idle_slope,
            send_slope=send_slope,
            hi_credit=hi_credit,
            lo_credit=lo_credit,
            reserved_bandwidth_mbps=reserved_mbps,
            actual_bandwidth_mbps=stream.bitrate_mbps,
            efficiency_percent=efficiency
        )
    
    def calculate_multi_stream(self, 
                              streams: List[StreamConfig]) -> Dict[str, CBSParameters]:
        """
        다중 스트림에 대한 CBS 파라미터 계산
        
        Args:
            streams: 스트림 목록
            
        Returns:
            스트림별 CBS 파라미터
        """
        results = {}
        total_reserved = 0
        
        # 우선순위 순으로 정렬
        sorted_streams = sorted(streams, key=lambda x: x.priority, reverse=True)
        
        for stream in sorted_streams:
            # 남은 대역폭 확인
            remaining_bw = self.link_speed_mbps - total_reserved
            
            if remaining_bw < stream.bitrate_mbps * 1.1:  # 최소 10% 여유 필요
                print(f"경고: {stream.name}에 대한 대역폭 부족 (남은: {remaining_bw:.1f} Mbps)")
                
            params = self.calculate_cbs_params(stream)
            results[stream.name] = params
            total_reserved += params.reserved_bandwidth_mbps
            
        # 전체 사용률 확인
        total_utilization = (total_reserved / self.link_speed_mbps) * 100
        
        if total_utilization > 80:
            print(f"경고: 전체 대역폭 사용률 {total_utilization:.1f}% (권장: < 80%)")
        
        return results
    
    def optimize_parameters(self, 
                          streams: List[StreamConfig],
                          target_utilization: float = 75) -> Dict[str, CBSParameters]:
        """
        CBS 파라미터 최적화
        
        Args:
            streams: 스트림 목록
            target_utilization: 목표 사용률 (%)
            
        Returns:
            최적화된 CBS 파라미터
        """
        # 초기 계산
        initial_params = self.calculate_multi_stream(streams)
        
        # 전체 예약 대역폭 계산
        total_reserved = sum(p.reserved_bandwidth_mbps for p in initial_params.values())
        current_utilization = (total_reserved / self.link_speed_mbps) * 100
        
        # 최적화 필요 여부 확인
        if current_utilization <= target_utilization:
            return initial_params
        
        # 헤드룸 조정을 통한 최적화
        optimization_factor = target_utilization / current_utilization
        optimized_results = {}
        
        for stream in streams:
            # 기존 파라미터
            original = initial_params[stream.name]
            
            # 조정된 예약 대역폭
            adjusted_reserved = original.reserved_bandwidth_mbps * optimization_factor
            
            # 최소 요구사항 확인
            if adjusted_reserved < stream.bitrate_mbps * 1.05:  # 최소 5% 여유
                adjusted_reserved = stream.bitrate_mbps * 1.05
            
            # 재계산
            adjusted_headroom = ((adjusted_reserved / stream.bitrate_mbps) - 1) * 100
            optimized = self.calculate_cbs_params(stream, adjusted_headroom)
            optimized_results[stream.name] = optimized
            
        return optimized_results
    
    def validate_configuration(self, params: Dict[str, CBSParameters]) -> List[str]:
        """
        CBS 구성 검증
        
        Args:
            params: CBS 파라미터 딕셔너리
            
        Returns:
            경고 메시지 목록
        """
        warnings = []
        
        # 전체 대역폭 확인
        total_reserved = sum(p.reserved_bandwidth_mbps for p in params.values())
        utilization = (total_reserved / self.link_speed_mbps) * 100
        
        if utilization > 95:
            warnings.append(f"매우 높은 대역폭 사용률: {utilization:.1f}%")
        elif utilization > 80:
            warnings.append(f"높은 대역폭 사용률: {utilization:.1f}%")
        
        # 개별 파라미터 확인
        for name, param in params.items():
            # idleSlope 검증
            if param.idle_slope > self.link_speed_bps * 0.5:
                warnings.append(f"{name}: idleSlope이 링크 속도의 50% 초과")
            
            # 크레딧 범위 검증
            if abs(param.lo_credit) > 100000:
                warnings.append(f"{name}: loCredit이 매우 큼 ({param.lo_credit} bits)")
            
            # 효율성 검증
            if param.efficiency_percent < 70:
                warnings.append(f"{name}: 낮은 효율성 ({param.efficiency_percent:.1f}%)")
        
        return warnings
    
    def generate_config_file(self, 
                            streams: List[StreamConfig],
                            output_file: str = "cbs_config.yaml"):
        """
        YAML 구성 파일 생성
        
        Args:
            streams: 스트림 목록
            output_file: 출력 파일명
        """
        # CBS 파라미터 계산
        params = self.optimize_parameters(streams)
        
        # YAML 구조 생성
        config = {
            "cbs-configuration": {
                "link-speed-mbps": self.link_speed_mbps,
                "timestamp": "2025-09-02T10:00:00Z",
                "streams": []
            }
        }
        
        for stream in streams:
            param = params[stream.name]
            stream_config = {
                "name": stream.name,
                "type": stream.traffic_type.value,
                "priority": stream.priority,
                "bitrate-mbps": stream.bitrate_mbps,
                "cbs-parameters": {
                    "idle-slope": param.idle_slope,
                    "send-slope": param.send_slope,
                    "hi-credit": param.hi_credit,
                    "lo-credit": param.lo_credit,
                    "reserved-bandwidth-mbps": param.reserved_bandwidth_mbps,
                    "efficiency-percent": param.efficiency_percent
                },
                "qos-requirements": {
                    "max-latency-ms": stream.max_latency_ms,
                    "max-jitter-ms": stream.max_jitter_ms
                }
            }
            config["cbs-configuration"]["streams"].append(stream_config)
        
        # 파일 저장
        with open(output_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"구성 파일 생성: {output_file}")
        
        # 검증
        warnings = self.validate_configuration(params)
        if warnings:
            print("\n검증 경고:")
            for warning in warnings:
                print(f"  - {warning}")
    
    def calculate_theoretical_delay(self, 
                                  stream: StreamConfig,
                                  cbs_params: CBSParameters) -> Dict[str, float]:
        """
        이론적 지연 시간 계산
        
        Args:
            stream: 스트림 구성
            cbs_params: CBS 파라미터
            
        Returns:
            지연 시간 메트릭 딕셔너리
        """
        # Maximum frame transmission time
        max_frame_bits = 1518 * 8  # Maximum Ethernet frame
        max_tx_time = max_frame_bits / self.link_speed_bps
        
        # CBS queue delay calculation
        interference_delay = abs(cbs_params.lo_credit) / cbs_params.idle_slope
        shaping_delay = (max_frame_bits * (self.link_speed_bps - cbs_params.idle_slope)) / (self.link_speed_bps * cbs_params.idle_slope)
        
        # Total delay components
        propagation_delay = 0.000001  # 1μs for short links
        processing_delay = 0.00001   # 10μs for switch processing
        queuing_delay = interference_delay + shaping_delay
        
        total_delay = propagation_delay + processing_delay + queuing_delay
        
        return {
            "propagation_delay_ms": propagation_delay * 1000,
            "processing_delay_ms": processing_delay * 1000,
            "queuing_delay_ms": queuing_delay * 1000,
            "shaping_delay_ms": shaping_delay * 1000,
            "interference_delay_ms": interference_delay * 1000,
            "total_delay_ms": total_delay * 1000,
            "max_tx_time_ms": max_tx_time * 1000
        }
    
    def calculate_burst_capacity(self, 
                               cbs_params: CBSParameters,
                               burst_duration_ms: float = 1.0) -> Dict[str, Any]:
        """
        버스트 처리 능력 계산
        
        Args:
            cbs_params: CBS 파라미터
            burst_duration_ms: 버스트 지속 시간 (ms)
            
        Returns:
            버스트 메트릭
        """
        burst_duration_s = burst_duration_ms / 1000.0
        
        # Credit available for burst
        available_credit = cbs_params.hi_credit
        
        # Burst capacity in bits
        burst_bits = available_credit
        burst_bytes = burst_bits / 8
        
        # Maximum burst rate
        max_burst_rate_bps = cbs_params.idle_slope
        max_burst_rate_mbps = max_burst_rate_bps / 1_000_000
        
        # Burst duration at max rate
        max_burst_duration_s = burst_bits / max_burst_rate_bps
        
        return {
            "available_credit_bits": available_credit,
            "burst_capacity_bytes": burst_bytes,
            "burst_capacity_packets": int(burst_bytes / 1500),  # Assume 1500B packets
            "max_burst_rate_mbps": max_burst_rate_mbps,
            "max_burst_duration_ms": max_burst_duration_s * 1000,
            "sustainable_rate_mbps": cbs_params.reserved_bandwidth_mbps
        }
    
    def analyze_interference_impact(self, 
                                  streams: List[StreamConfig],
                                  interfering_traffic_mbps: float = 0) -> Dict[str, Any]:
        """
        간섭 트래픽 영향 분석
        
        Args:
            streams: 스트림 목록
            interfering_traffic_mbps: 간섭 트래픽 (Mbps)
            
        Returns:
            간섭 영향 분석 결과
        """
        results = {}
        
        for stream in streams:
            cbs_params = self.calculate_cbs_params(stream)
            
            # Calculate interference delay
            interference_bits = (interfering_traffic_mbps * 1_000_000) / (1000 / stream.max_latency_ms)  # Bits per latency window
            interference_delay_s = interference_bits / self.link_speed_bps
            
            # Impact on latency
            baseline_delay = self.calculate_theoretical_delay(stream, cbs_params)
            additional_delay_ms = interference_delay_s * 1000
            
            # Performance degradation
            latency_increase_percent = (additional_delay_ms / baseline_delay["total_delay_ms"]) * 100
            
            results[stream.name] = {
                "baseline_delay_ms": baseline_delay["total_delay_ms"],
                "interference_delay_ms": additional_delay_ms,
                "total_delay_ms": baseline_delay["total_delay_ms"] + additional_delay_ms,
                "latency_increase_percent": latency_increase_percent,
                "meets_requirements": (baseline_delay["total_delay_ms"] + additional_delay_ms) <= stream.max_latency_ms
            }
        
        return results
    
    def generate_performance_report(self, 
                                  streams: List[StreamConfig],
                                  output_file: str = "cbs_performance_report.md") -> None:
        """
        상세 성능 리포트 생성
        
        Args:
            streams: 스트림 목록
            output_file: 출력 파일명
        """
        params = self.optimize_parameters(streams)
        
        # Generate comprehensive analysis
        report_content = []
        report_content.append("# CBS 성능 분석 리포트\n")
        report_content.append(f"생성 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_content.append(f"링크 속도: {self.link_speed_mbps} Mbps\n\n")
        
        # Summary table
        report_content.append("## 개요\n\n")
        report_content.append("| 항목 | 값 |\n")
        report_content.append("|------|----|\n")
        report_content.append(f"| 총 스트림 수 | {len(streams)} |\n")
        
        total_actual = sum(s.bitrate_mbps for s in streams)
        total_reserved = sum(p.reserved_bandwidth_mbps for p in params.values())
        utilization = (total_reserved / self.link_speed_mbps) * 100
        
        report_content.append(f"| 실제 트래픽 | {total_actual:.1f} Mbps |\n")
        report_content.append(f"| 예약 대역폭 | {total_reserved:.1f} Mbps |\n")
        report_content.append(f"| 링크 사용률 | {utilization:.1f}% |\n\n")
        
        # Detailed stream analysis
        report_content.append("## 스트림별 상세 분석\n\n")
        
        for stream in sorted(streams, key=lambda x: x.priority, reverse=True):
            param = params[stream.name]
            delay_analysis = self.calculate_theoretical_delay(stream, param)
            burst_analysis = self.calculate_burst_capacity(param)
            
            report_content.append(f"### {stream.name}\n\n")
            report_content.append("#### 기본 정보\n")
            report_content.append(f"- **트래픽 유형**: {stream.traffic_type.value}\n")
            report_content.append(f"- **우선순위**: TC{stream.priority}\n")
            report_content.append(f"- **비트레이트**: {stream.bitrate_mbps} Mbps\n")
            report_content.append(f"- **요구 지연**: ≤ {stream.max_latency_ms} ms\n")
            report_content.append(f"- **요구 지터**: ≤ {stream.max_jitter_ms} ms\n\n")
            
            report_content.append("#### CBS 파라미터\n")
            report_content.append(f"- **idleSlope**: {param.idle_slope:,} bps ({param.idle_slope/1_000_000:.1f} Mbps)\n")
            report_content.append(f"- **sendSlope**: {param.send_slope:,} bps\n")
            report_content.append(f"- **hiCredit**: {param.hi_credit:,} bits\n")
            report_content.append(f"- **loCredit**: {param.lo_credit:,} bits\n")
            report_content.append(f"- **예약 대역폭**: {param.reserved_bandwidth_mbps:.1f} Mbps\n")
            report_content.append(f"- **효율성**: {param.efficiency_percent:.1f}%\n\n")
            
            report_content.append("#### 지연 시간 분석\n")
            report_content.append(f"- **처리 지연**: {delay_analysis['processing_delay_ms']:.3f} ms\n")
            report_content.append(f"- **셰이핑 지연**: {delay_analysis['shaping_delay_ms']:.3f} ms\n")
            report_content.append(f"- **간섭 지연**: {delay_analysis['interference_delay_ms']:.3f} ms\n")
            report_content.append(f"- **총 지연**: {delay_analysis['total_delay_ms']:.3f} ms\n")
            meets_latency = delay_analysis['total_delay_ms'] <= stream.max_latency_ms
            report_content.append(f"- **요구사항 만족**: {'✅' if meets_latency else '❌'}\n\n")
            
            report_content.append("#### 버스트 처리 능력\n")
            report_content.append(f"- **버스트 용량**: {burst_analysis['burst_capacity_bytes']:.0f} bytes ({burst_analysis['burst_capacity_packets']} packets)\n")
            report_content.append(f"- **최대 버스트 속도**: {burst_analysis['max_burst_rate_mbps']:.1f} Mbps\n")
            report_content.append(f"- **버스트 지속 시간**: {burst_analysis['max_burst_duration_ms']:.3f} ms\n\n")
            
            report_content.append("---\n\n")
        
        # Interference analysis
        report_content.append("## 간섭 트래픽 영향 분석\n\n")
        
        for load in [0, 100, 200, 400, 600, 800]:
            interference_results = self.analyze_interference_impact(streams, load)
            report_content.append(f"### 간섭 트래픽: {load} Mbps\n\n")
            report_content.append("| 스트림 | 기본 지연 (ms) | 간섭 지연 (ms) | 총 지연 (ms) | 증가율 (%) | 요구사항 |\n")
            report_content.append("|--------|---------------|---------------|-------------|-----------|----------|\n")
            
            for stream_name, result in interference_results.items():
                meets = "✅" if result["meets_requirements"] else "❌"
                report_content.append(f"| {stream_name} | {result['baseline_delay_ms']:.3f} | {result['interference_delay_ms']:.3f} | {result['total_delay_ms']:.3f} | {result['latency_increase_percent']:.1f} | {meets} |\n")
            
            report_content.append("\n")
        
        # Recommendations
        warnings = self.validate_configuration(params)
        if warnings:
            report_content.append("## ⚠️ 경고 및 권장사항\n\n")
            for warning in warnings:
                report_content.append(f"- {warning}\n")
            report_content.append("\n")
        
        report_content.append("## ✅ 권장사항\n\n")
        
        if utilization > 80:
            report_content.append("- 링크 사용률이 높습니다. 트래픽 분산을 고려하세요.\n")
        if utilization < 50:
            report_content.append("- 링크 사용률이 낮습니다. 추가 트래픽을 수용할 수 있습니다.\n")
        
        high_latency_streams = [s for s in streams if 
                               self.calculate_theoretical_delay(s, params[s.name])["total_delay_ms"] > s.max_latency_ms * 0.8]
        if high_latency_streams:
            report_content.append("- 다음 스트림들의 지연 시간이 요구사항에 근접합니다:\n")
            for stream in high_latency_streams:
                report_content.append(f"  - {stream.name}\n")
        
        report_content.append("\n---\n\n")
        report_content.append(f"*리포트 생성: CBS Calculator v2.0*\n")
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(''.join(report_content))
        
        print(f"성능 리포트 생성: {output_file}")
    
    def export_to_csv(self, 
                     streams: List[StreamConfig],
                     output_file: str = "cbs_parameters.csv") -> None:
        """
        CBS 파라미터를 CSV로 내보내기
        
        Args:
            streams: 스트림 목록
            output_file: 출력 파일명
        """
        params = self.calculate_multi_stream(streams)
        
        csv_data = []
        for stream in streams:
            param = params[stream.name]
            delay_analysis = self.calculate_theoretical_delay(stream, param)
            
            row = {
                'stream_name': stream.name,
                'traffic_type': stream.traffic_type.value,
                'priority': stream.priority,
                'actual_bitrate_mbps': stream.bitrate_mbps,
                'reserved_bitrate_mbps': param.reserved_bandwidth_mbps,
                'idle_slope_bps': param.idle_slope,
                'send_slope_bps': param.send_slope,
                'hi_credit_bits': param.hi_credit,
                'lo_credit_bits': param.lo_credit,
                'efficiency_percent': param.efficiency_percent,
                'theoretical_delay_ms': delay_analysis['total_delay_ms'],
                'latency_requirement_ms': stream.max_latency_ms,
                'jitter_requirement_ms': stream.max_jitter_ms,
                'meets_latency_req': delay_analysis['total_delay_ms'] <= stream.max_latency_ms
            }
            csv_data.append(row)
        
        # Write CSV
        fieldnames = csv_data[0].keys() if csv_data else []
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"CSV 파일 생성: {output_file}")
    
    def compare_configurations(self, 
                             streams: List[StreamConfig],
                             scenarios: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        여러 구성 시나리오 비교
        
        Args:
            streams: 기본 스트림 목록
            scenarios: 시나리오별 설정 딕셔너리
            
        Returns:
            비교 결과 DataFrame
        """
        comparison_results = []
        
        for scenario_name, scenario_config in scenarios.items():
            # Apply scenario modifications
            modified_streams = streams.copy()
            
            if 'link_speed_mbps' in scenario_config:
                temp_calculator = CBSCalculator(scenario_config['link_speed_mbps'])
            else:
                temp_calculator = self
            
            # Calculate parameters for this scenario
            if 'target_utilization' in scenario_config:
                params = temp_calculator.optimize_parameters(modified_streams, scenario_config['target_utilization'])
            else:
                params = temp_calculator.calculate_multi_stream(modified_streams)
            
            # Collect metrics
            total_actual = sum(s.bitrate_mbps for s in modified_streams)
            total_reserved = sum(p.reserved_bandwidth_mbps for p in params.values())
            utilization = (total_reserved / temp_calculator.link_speed_mbps) * 100
            
            # Calculate average efficiency and delay
            avg_efficiency = np.mean([p.efficiency_percent for p in params.values()])
            
            total_delay = 0
            for stream in modified_streams:
                delay_analysis = temp_calculator.calculate_theoretical_delay(stream, params[stream.name])
                total_delay += delay_analysis['total_delay_ms']
            avg_delay = total_delay / len(modified_streams)
            
            comparison_results.append({
                'scenario': scenario_name,
                'link_speed_mbps': temp_calculator.link_speed_mbps,
                'streams_count': len(modified_streams),
                'total_actual_mbps': total_actual,
                'total_reserved_mbps': total_reserved,
                'utilization_percent': utilization,
                'avg_efficiency_percent': avg_efficiency,
                'avg_delay_ms': avg_delay
            })
        
        return pd.DataFrame(comparison_results)


def example_autonomous_vehicle():
    """자율주행 차량 예제"""
    
    # CBS 계산기 생성
    calculator = CBSCalculator(link_speed_mbps=1000)
    
    # 스트림 정의
    streams = [
        # 안전 Critical
        StreamConfig("Emergency_Brake", TrafficType.SAFETY_CRITICAL, 2, 100, "N/A", 7, 5, 0.5),
        StreamConfig("Steering_Control", TrafficType.SAFETY_CRITICAL, 1, 100, "N/A", 7, 5, 0.5),
        
        # 전방 4K 카메라
        StreamConfig("Front_Center_4K", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
        StreamConfig("Front_Left_4K", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
        StreamConfig("Front_Right_4K", TrafficType.VIDEO_4K, 25, 60, "3840x2160", 6, 20, 3),
        
        # 서라운드 1080p 카메라
        StreamConfig("Left_Front_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
        StreamConfig("Left_Rear_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
        StreamConfig("Right_Front_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
        StreamConfig("Right_Rear_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
        StreamConfig("Rear_Center_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
        StreamConfig("Rear_Wide_HD", TrafficType.VIDEO_1080P, 15, 30, "1920x1080", 5, 30, 5),
        
        # 센서 데이터
        StreamConfig("Lidar_Main", TrafficType.LIDAR, 100, 10, "N/A", 4, 40, 4),
        StreamConfig("Radar_Fusion", TrafficType.RADAR, 16, 50, "N/A", 3, 20, 2),
        
        # V2X
        StreamConfig("V2X_Safety", TrafficType.V2X, 10, 10, "N/A", 2, 100, 10),
        
        # 인포테인먼트
        StreamConfig("Infotainment", TrafficType.INFOTAINMENT, 50, 30, "N/A", 1, 500, 50),
        
        # 진단
        StreamConfig("Diagnostics", TrafficType.DIAGNOSTICS, 5, 1, "N/A", 0, 1000, 100),
    ]
    
    print("=" * 80)
    print("자율주행 차량 CBS 파라미터 계산")
    print("=" * 80)
    
    # 전체 트래픽 분석
    total_bitrate = sum(s.bitrate_mbps for s in streams)
    print(f"\n전체 트래픽: {total_bitrate:.1f} Mbps")
    print(f"링크 속도: {calculator.link_speed_mbps} Mbps")
    print(f"기본 사용률: {(total_bitrate/calculator.link_speed_mbps)*100:.1f}%")
    
    # CBS 파라미터 계산
    print("\n최적화된 CBS 파라미터 계산 중...")
    params = calculator.optimize_parameters(streams, target_utilization=75)
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("CBS 파라미터 (우선순위 순)")
    print("=" * 80)
    
    # 우선순위별로 정렬하여 출력
    sorted_streams = sorted(streams, key=lambda x: x.priority, reverse=True)
    
    for stream in sorted_streams:
        param = params[stream.name]
        print(f"\n[{stream.name}]")
        print(f"  트래픽 유형: {stream.traffic_type.value}")
        print(f"  우선순위: TC{stream.priority}")
        print(f"  실제 비트레이트: {stream.bitrate_mbps} Mbps")
        print(f"  예약 대역폭: {param.reserved_bandwidth_mbps:.1f} Mbps")
        print(f"  idleSlope: {param.idle_slope:,} bps")
        print(f"  sendSlope: {param.send_slope:,} bps")
        print(f"  hiCredit: {param.hi_credit:,} bits")
        print(f"  loCredit: {param.lo_credit:,} bits")
        print(f"  효율성: {param.efficiency_percent:.1f}%")
    
    # 전체 통계
    total_reserved = sum(p.reserved_bandwidth_mbps for p in params.values())
    total_utilization = (total_reserved / calculator.link_speed_mbps) * 100
    
    print("\n" + "=" * 80)
    print("전체 네트워크 통계")
    print("=" * 80)
    print(f"총 예약 대역폭: {total_reserved:.1f} Mbps")
    print(f"네트워크 사용률: {total_utilization:.1f}%")
    print(f"여유 대역폭: {calculator.link_speed_mbps - total_reserved:.1f} Mbps")
    
    # 구성 파일 생성
    calculator.generate_config_file(streams, "autonomous_vehicle_cbs.yaml")
    
    # 검증
    warnings = calculator.validate_configuration(params)
    if warnings:
        print("\n⚠️  검증 경고:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\n✅ 모든 검증 통과")


if __name__ == "__main__":
    example_autonomous_vehicle()