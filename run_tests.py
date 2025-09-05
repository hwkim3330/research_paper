#!/usr/bin/env python3
"""
실제 CBS 테스트 실행 스크립트
1 기가비트 이더넷 환경 테스트
"""

import sys
import os
import time
import json
import numpy as np
from datetime import datetime

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_cbs_calculator():
    """CBS 계산기 테스트"""
    print("\n" + "="*60)
    print("1. CBS 계산기 테스트")
    print("="*60)
    
    try:
        from src.cbs_calculator import CBSCalculator
        
        # 1 기가비트 이더넷 설정
        calc = CBSCalculator(link_speed_mbps=1000)
        
        # 테스트 케이스들
        test_cases = [
            {"name": "AVB Class A (75%)", "bandwidth": 75},
            {"name": "AVB Class B (25%)", "bandwidth": 25},
            {"name": "Video Stream (50%)", "bandwidth": 50},
            {"name": "Control (10%)", "bandwidth": 10}
        ]
        
        for test in test_cases:
            print(f"\n테스트: {test['name']}")
            print("-" * 40)
            
            idle_slope = calc.calculate_idle_slope(test['bandwidth'])
            send_slope = calc.calculate_send_slope(idle_slope)
            credits = calc.calculate_credits(idle_slope, 1500, 3)
            
            print(f"  Idle Slope: {idle_slope/1e6:.1f} Mbps")
            print(f"  Send Slope: {send_slope/1e6:.1f} Mbps")
            print(f"  Hi Credit: {credits['hi_credit']:.0f} bits")
            print(f"  Lo Credit: {credits['lo_credit']:.0f} bits")
            
            # 지연 시간 계산
            latency = calc.calculate_max_latency(1500, idle_slope, credits['lo_credit'])
            print(f"  최대 지연: {latency*1000:.2f} ms")
            
        print("\n✅ CBS 계산기 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ CBS 계산기 테스트 실패: {e}")
        return False

def test_network_simulator():
    """네트워크 시뮬레이터 테스트"""
    print("\n" + "="*60)
    print("2. 네트워크 시뮬레이터 테스트")
    print("="*60)
    
    try:
        from src.network_simulator import NetworkSimulator
        
        # 시뮬레이터 생성
        sim = NetworkSimulator(link_speed_mbps=1000)
        
        # CBS 큐 추가
        sim.add_cbs_queue(
            queue_id=0,
            idle_slope=750,
            send_slope=-250,
            hi_credit=2000,
            lo_credit=-1000
        )
        
        # 트래픽 생성
        sim.generate_traffic(
            pattern='cbr',
            duration=1.0,
            rate_mbps=500,
            frame_size=1500,
            queue_id=0
        )
        
        print("\n시뮬레이션 실행 중...")
        
        # 시뮬레이션 실행
        results = sim.run(duration=1.0)
        
        # 결과 출력
        stats = results['statistics']
        print("\n시뮬레이션 결과:")
        print("-" * 40)
        print(f"  전송 프레임: {stats['total_transmitted']}")
        print(f"  손실 프레임: {stats['total_dropped']}")
        print(f"  평균 지연: {stats['avg_latency']*1000:.2f} ms")
        print(f"  최대 지연: {stats['max_latency']*1000:.2f} ms")
        print(f"  지터: {stats['jitter']*1000:.3f} ms")
        print(f"  링크 사용률: {stats['avg_utilization']*100:.1f}%")
        
        print("\n✅ 네트워크 시뮬레이터 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 네트워크 시뮬레이터 테스트 실패: {e}")
        return False

def test_ml_optimizer():
    """머신러닝 최적화 테스트"""
    print("\n" + "="*60)
    print("3. 머신러닝 최적화 테스트")
    print("="*60)
    
    try:
        from src.ml_optimizer import CBSOptimizer
        
        # 최적화기 생성
        optimizer = CBSOptimizer()
        
        # 트래픽 프로필
        traffic_profile = {
            'rate': 600,
            'burst_size': 10,
            'frame_size': 1500,
            'pattern': 'mixed'
        }
        
        print("\n트래픽 프로필:")
        print(f"  속도: {traffic_profile['rate']} Mbps")
        print(f"  버스트 크기: {traffic_profile['burst_size']}")
        print(f"  프레임 크기: {traffic_profile['frame_size']} bytes")
        print(f"  패턴: {traffic_profile['pattern']}")
        
        print("\n최적화 실행 중...")
        
        # 최적화 수행
        optimal_params = optimizer.optimize(traffic_profile)
        
        print("\n최적화 결과:")
        print("-" * 40)
        print(f"  Idle Slope: {optimal_params['idle_slope']:.1f} Mbps")
        print(f"  Send Slope: {optimal_params['send_slope']:.1f} Mbps")
        print(f"  Hi Credit: {optimal_params['hi_credit']:.0f} bits")
        print(f"  Lo Credit: {optimal_params['lo_credit']:.0f} bits")
        
        print("\n✅ 머신러닝 최적화 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 머신러닝 최적화 테스트 실패: {e}")
        return False

def test_performance_benchmark():
    """성능 벤치마크 테스트"""
    print("\n" + "="*60)
    print("4. 성능 벤치마크 테스트")
    print("="*60)
    
    try:
        from src.performance_benchmark import PerformanceBenchmark
        
        # 벤치마크 생성
        benchmark = PerformanceBenchmark()
        
        print("\n벤치마크 실행 중...")
        
        # 지연시간 측정
        latency_results = benchmark.measure_latency(
            duration=0.5,
            frame_rate=1000
        )
        
        print("\n지연시간 측정 결과:")
        print("-" * 40)
        print(f"  최소: {latency_results.get('min', 0)*1000:.3f} ms")
        print(f"  최대: {latency_results.get('max', 0)*1000:.3f} ms")
        print(f"  평균: {latency_results.get('avg', 0)*1000:.3f} ms")
        print(f"  P99: {latency_results.get('p99', 0)*1000:.3f} ms")
        
        # 처리량 측정
        throughput_results = benchmark.measure_throughput(
            duration=0.5,
            frame_size=1500
        )
        
        print("\n처리량 측정 결과:")
        print("-" * 40)
        print(f"  속도: {throughput_results.get('mbps', 0):.1f} Mbps")
        print(f"  FPS: {throughput_results.get('fps', 0):.0f}")
        print(f"  총 바이트: {throughput_results.get('bytes_total', 0)/1e6:.1f} MB")
        
        print("\n✅ 성능 벤치마크 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 성능 벤치마크 테스트 실패: {e}")
        return False

def generate_test_report(results):
    """테스트 보고서 생성"""
    print("\n" + "="*60)
    print("테스트 보고서")
    print("="*60)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = {
        "timestamp": timestamp,
        "platform": "1 Gigabit Ethernet",
        "tests": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results.values() if r),
            "failed": sum(1 for r in results.values() if not r)
        }
    }
    
    print(f"\n실행 시간: {timestamp}")
    print(f"플랫폼: {report['platform']}")
    print(f"\n테스트 결과:")
    print("-" * 40)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\n요약:")
    print(f"  전체: {report['summary']['total']}")
    print(f"  성공: {report['summary']['passed']}")
    print(f"  실패: {report['summary']['failed']}")
    
    success_rate = (report['summary']['passed'] / report['summary']['total']) * 100
    print(f"  성공률: {success_rate:.1f}%")
    
    # 보고서 파일로 저장
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 보고서 저장: {report_file}")
    except:
        pass
    
    return report

def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print(" CBS 1 기가비트 이더넷 구현 테스트 스위트 ")
    print("="*80)
    print("\n테스트 시작...\n")
    
    # 테스트 실행
    results = {}
    
    # 1. CBS 계산기
    results["CBS 계산기"] = test_cbs_calculator()
    
    # 2. 네트워크 시뮬레이터
    results["네트워크 시뮬레이터"] = test_network_simulator()
    
    # 3. 머신러닝 최적화
    results["ML 최적화"] = test_ml_optimizer()
    
    # 4. 성능 벤치마크
    results["성능 벤치마크"] = test_performance_benchmark()
    
    # 보고서 생성
    report = generate_test_report(results)
    
    # 최종 결과
    if report['summary']['failed'] == 0:
        print("\n🎉 모든 테스트 통과! CBS 구현이 정상 작동합니다.")
    else:
        print(f"\n⚠️ {report['summary']['failed']}개 테스트 실패. 확인이 필요합니다.")
    
    print("\n" + "="*80)
    print(" 테스트 완료 ")
    print("="*80)

if __name__ == "__main__":
    main()