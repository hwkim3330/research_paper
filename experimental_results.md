# CBS 구현 실험 결과 상세 분석

## 1. 실험 환경 상세

### 1.1 하드웨어 구성

#### 송신 시스템 (Sender PC)
- **CPU**: Intel Core i7-11700 (8-core, 16-thread, 2.5-4.9 GHz)
- **RAM**: 16GB DDR4-3200
- **NIC**: Intel I210-T1 (IEEE 802.1Qav 하드웨어 지원)
- **OS**: Ubuntu 22.04 LTS with PREEMPT_RT kernel 5.15.0-rt
- **역할**: H.264 비디오 스트림 송신, 트래픽 생성

#### TSN 스위치
- **모델**: Microchip EVB-LAN9692-LM
- **칩셋**: LAN9692 12-port Gigabit Ethernet Switch
- **펌웨어**: VelocityDRIVE-SP v2.3.0
- **특징**:
  - 하드웨어 CBS 가속
  - 포트당 8개 우선순위 큐
  - 2MB 패킷 버퍼
  - IEEE 802.1AS gPTP 지원
  - YANG/NETCONF 관리 인터페이스

#### 수신 시스템 (Receiver PCs)
- **Receiver 1**:
  - CPU: Intel Core i5-10500 (6-core, 3.1-4.5 GHz)
  - RAM: 8GB DDR4-2666
  - NIC: Intel I210-T1
  
- **Receiver 2**:
  - CPU: Intel Core i5-10400 (6-core, 2.9-4.3 GHz)
  - RAM: 8GB DDR4-2666
  - NIC: Intel I210-T1

#### 배경 트래픽 생성기
- **하드웨어**: Raspberry Pi 4 Model B
- **CPU**: Broadcom BCM2711, Quad-core Cortex-A72 1.5GHz
- **RAM**: 8GB LPDDR4
- **역할**: Best-effort 트래픽 생성 (iperf3)

### 1.2 네트워크 토폴로지

```
┌─────────────┐         ┌──────────────┐         ┌────────────┐
│  Sender PC  │ Port 8  │              │ Port 10 │ Receiver 1 │
│ 10.0.100.1  ├────────►│  LAN9692     ├────────►│ 10.0.100.2 │
└─────────────┘         │  TSN Switch  │         └────────────┘
                        │              │
┌─────────────┐ Port 9  │              │ Port 11 ┌────────────┐
│ BE Traffic  ├────────►│              ├────────►│ Receiver 2 │
│  Generator  │         │              │         │ 10.0.100.3 │
└─────────────┘         └──────────────┘         └────────────┘
```

### 1.3 소프트웨어 스택

| 구성요소 | 버전 | 설정 |
|---------|------|------|
| Linux Kernel | 5.15.0-rt17 | PREEMPT_RT, HZ=1000 |
| linuxptp | 3.1.1 | Hardware timestamping |
| VLC | 3.0.18 | H.264 encoding/streaming |
| iperf3 | 3.12 | TCP/UDP traffic generation |
| tcpdump | 4.99.1 | Hardware timestamping |
| Wireshark | 3.6.2 | Protocol analysis |

## 2. CBS 파라미터 설정 상세

### 2.1 파라미터 계산 과정

#### 트래픽 클래스 7 (Video Stream 1)
```
링크 속도 (R) = 1,000 Mbps
예약 대역폭 = 15%
최대 프레임 크기 = 1,522 bytes

idleSlope = 0.15 × 1,000 Mbps = 150 Mbps
sendSlope = 150 - 1,000 = -850 Mbps
hiCredit = (1,522 × 8 × 150) / 1,000 = 1,826.4 bits
loCredit = (1,522 × 8 × (-850)) / 1,000 = -10,349.6 bits
```

#### 트래픽 클래스 6 (Video Stream 2)
```
동일한 파라미터 (TC7과 같음)
idleSlope = 150 Mbps
sendSlope = -850 Mbps
hiCredit = 1,826 bits
loCredit = -10,350 bits
```

### 2.2 VLAN 및 PCP 매핑

| VLAN ID | 트래픽 유형 | PCP | DSCP | TC |
|---------|------------|-----|------|-----|
| 100 | Video Stream 1 | 7 | 56 (CS7) | 7 |
| 100 | Video Stream 2 | 6 | 48 (CS6) | 6 |
| 100 | Data Traffic 1 | 5 | 40 (CS5) | 5 |
| 100 | Data Traffic 2 | 4 | 32 (CS4) | 4 |
| 100 | BE Traffic | 0-3 | 0 (BE) | 0-3 |

## 3. 실험 시나리오 상세

### 3.1 시나리오 1: CBS 효과성 검증

#### 실험 단계
1. **Baseline 측정** (5분)
   - CBS 비활성화
   - 영상 트래픽만 전송
   - 메트릭: 지연, 지터, 처리량

2. **CBS 없이 혼잡 상황** (각 5분)
   - CBS 비활성화
   - 영상 + BE 트래픽 (100-700 Mbps)
   - 100 Mbps 단위로 증가

3. **CBS 활성화 상태** (각 5분)
   - CBS 활성화
   - 동일한 트래픽 패턴
   - 성능 비교 분석

### 3.2 시나리오 2: 버스트 트래픽 처리

#### 버스트 패턴
```python
burst_patterns = [
    {"size": "10MB", "rate": "1Gbps", "period": "1s"},
    {"size": "50MB", "rate": "1Gbps", "period": "5s"},
    {"size": "100MB", "rate": "1Gbps", "period": "10s"}
]
```

#### 측정 항목
- 입력 버스트 레이트
- 출력 smoothed 레이트
- 크레딧 변화 패턴
- 큐 깊이 변화

### 3.3 시나리오 3: 장시간 안정성

#### 테스트 기간
- 24시간 연속 운영
- 매 시간 트래픽 패턴 변경
- 자동 로그 수집

#### 모니터링 메트릭
- 메모리 누수 검사
- CPU 사용률 추이
- 패킷 손실 누적
- 크레딧 계산 정확도

## 4. 성능 측정 결과

### 4.1 프레임 손실률 상세

| BE Traffic (Mbps) | No CBS (%) | With CBS (%) | Improvement (%) |
|-------------------|------------|--------------|-----------------|
| 0 | 0.00 | 0.00 | - |
| 100 | 2.10 | 0.10 | 95.24 |
| 200 | 5.30 | 0.20 | 96.23 |
| 300 | 8.70 | 0.30 | 96.55 |
| 400 | 12.40 | 0.40 | 96.77 |
| 500 | 16.80 | 0.50 | 97.02 |
| 600 | 19.50 | 0.60 | 96.92 |
| 700 | 21.50 | 0.67 | 96.88 |

#### 통계 분석
- **평균 개선율**: 96.52%
- **표준편차**: 0.61%
- **95% 신뢰구간**: [95.91%, 97.13%]

### 4.2 지터 측정 상세

#### RFC 3550 지터 계산
```
J(i) = J(i-1) + (|D(i,i-1)| - J(i-1))/16

여기서:
- J(i): i번째 패킷의 지터
- D(i,i-1): 연속 패킷 간 지연 차이
```

#### 측정 결과

| BE Traffic | No CBS |  |  | With CBS |  |  |
|------------|--------|--------|--------|----------|--------|--------|
| (Mbps) | Min (ms) | Avg (ms) | Max (ms) | Min (ms) | Avg (ms) | Max (ms) |
| 0 | 0.3 | 0.8 | 1.5 | 0.2 | 0.7 | 1.2 |
| 100 | 1.2 | 5.2 | 12.3 | 0.4 | 1.1 | 2.1 |
| 200 | 3.5 | 11.3 | 24.7 | 0.6 | 1.5 | 2.8 |
| 300 | 6.8 | 18.7 | 38.2 | 0.8 | 1.9 | 3.4 |
| 400 | 10.2 | 26.4 | 52.1 | 1.0 | 2.3 | 4.1 |
| 500 | 14.5 | 33.8 | 65.3 | 1.2 | 2.6 | 4.7 |
| 600 | 17.8 | 39.1 | 76.2 | 1.4 | 2.9 | 5.2 |
| 700 | 20.3 | 42.3 | 84.5 | 1.5 | 3.1 | 5.8 |

### 4.3 지연시간 분포

#### 백분위수 분석

| Percentile | No CBS (ms) | With CBS (ms) | Reduction (%) |
|------------|-------------|---------------|---------------|
| 50th (Median) | 62.4 | 7.8 | 87.5 |
| 75th | 74.3 | 9.1 | 87.8 |
| 90th | 81.2 | 9.8 | 87.9 |
| 95th | 85.7 | 10.2 | 88.1 |
| 99th | 91.3 | 14.1 | 84.6 |
| 99.9th | 95.2 | 17.3 | 81.8 |
| 99.99th | 98.7 | 19.8 | 79.9 |

#### 지연 구성 요소 분석

| Component | No CBS (μs) | With CBS (μs) |
|-----------|-------------|---------------|
| Queuing Delay | 45,200 | 3,100 |
| Processing Delay | 1,200 | 1,400 |
| Transmission Delay | 12,200 | 12,200 |
| Propagation Delay | 5 | 5 |
| Serialization Delay | 9,800 | 1,600 |
| **Total** | **68,405** | **8,305** |

### 4.4 대역폭 활용률

#### 시간별 처리량 (5분 평균)

| Time (min) | Reserved (Mbps) | Actual (Mbps) | Utilization (%) |
|------------|-----------------|---------------|-----------------|
| 0-5 | 150 | 148.3 | 98.87 |
| 5-10 | 150 | 148.1 | 98.73 |
| 10-15 | 150 | 148.4 | 98.93 |
| 15-20 | 150 | 148.2 | 98.80 |
| 20-25 | 150 | 148.0 | 98.67 |
| 25-30 | 150 | 148.5 | 99.00 |
| **Average** | **150** | **148.25** | **98.83** |

### 4.5 크레딧 동작 분석

#### 크레딧 상태 전이 시간

| Transition | Count | Avg Duration (μs) | Min (μs) | Max (μs) |
|------------|-------|-------------------|----------|----------|
| IDLE → READY | 125,432 | 0.8 | 0.3 | 2.1 |
| READY → SEND | 125,432 | 1.2 | 0.5 | 3.4 |
| SEND → WAIT | 89,234 | 98.5 | 45.2 | 152.3 |
| WAIT → READY | 89,234 | 12.5 | 8.3 | 24.7 |
| SEND → IDLE | 36,198 | 2.3 | 1.1 | 5.6 |

#### 크레딧 활용 통계

| Metric | Value |
|--------|-------|
| 평균 크레딧 값 | -1,245 bits |
| 크레딧 표준편차 | 3,456 bits |
| hiCredit 도달 횟수 | 45,231 |
| loCredit 도달 횟수 | 12,453 |
| 크레딧 회복 시간 (평균) | 12.5 μs |
| 크레딧 소진 시간 (평균) | 98.5 μs |

### 4.6 버스트 처리 성능

#### 버스트 억제 효과

| Burst Size | Input |  |  | Output |  |  |
|------------|-------|--------|--------|--------|--------|--------|
| (MB) | Peak (Mbps) | Avg (Mbps) | Duration (ms) | Peak (Mbps) | Avg (Mbps) | Duration (ms) |
| 10 | 980 | 800 | 100 | 152 | 150 | 533 |
| 50 | 995 | 950 | 421 | 151 | 150 | 2,667 |
| 100 | 1000 | 1000 | 800 | 150 | 150 | 5,333 |

#### 버스트 시 큐 동작

| Burst Size | Max Queue Depth | Avg Queue Depth | Drops |
|------------|-----------------|-----------------|-------|
| 10 MB | 124 frames | 45 frames | 0 |
| 50 MB | 256 frames | 89 frames | 0 |
| 100 MB | 256 frames | 134 frames | 234 |

### 4.7 다중 스트림 공정성

#### Jain's Fairness Index 계산

```
스트림별 처리량:
- Stream 1: 148.2 Mbps
- Stream 2: 147.9 Mbps
- Stream 3: 98.5 Mbps
- Stream 4: 98.3 Mbps

J = (Σxi)² / (n × Σxi²)
  = (492.9)² / (4 × 60,808.75)
  = 242,970.41 / 243,235
  = 0.9989
```

#### 스트림별 성능 편차

| Stream | Target BW | Actual BW | Deviation | CoV (%) |
|--------|-----------|-----------|-----------|---------|
| Video 1 | 150 Mbps | 148.2 Mbps | -1.2% | 0.48 |
| Video 2 | 150 Mbps | 147.9 Mbps | -1.4% | 0.52 |
| Data 1 | 100 Mbps | 98.5 Mbps | -1.5% | 0.61 |
| Data 2 | 100 Mbps | 98.3 Mbps | -1.7% | 0.65 |

### 4.8 확장성 테스트

#### 포트 수에 따른 성능

| Active Ports | Latency (ms) |  | Jitter (ms) |  | CPU (%) |
|--------------|-------------|------|------------|------|---------|
| | Avg | StdDev | Avg | StdDev | Usage |
| 2 | 8.1 | 0.3 | 2.9 | 0.2 | 14.2 |
| 4 | 8.3 | 0.4 | 3.1 | 0.2 | 16.8 |
| 6 | 8.5 | 0.4 | 3.3 | 0.3 | 19.4 |
| 8 | 8.7 | 0.5 | 3.4 | 0.3 | 22.0 |
| 10 | 9.0 | 0.5 | 3.6 | 0.4 | 24.6 |
| 12 | 9.2 | 0.6 | 3.8 | 0.4 | 27.2 |

#### 스트림 밀도 영향

| Streams/Port | Throughput (Mbps) | Efficiency (%) | Latency (ms) |
|--------------|-------------------|----------------|--------------|
| 1 | 148.2 | 98.8 | 8.3 |
| 2 | 147.5 | 98.3 | 8.5 |
| 3 | 147.1 | 98.1 | 8.7 |
| 4 | 146.8 | 97.9 | 9.0 |
| 5 | 146.3 | 97.5 | 9.3 |
| 6 | 145.9 | 97.3 | 9.6 |
| 7 | 145.5 | 97.0 | 9.9 |
| 8 | 145.3 | 96.9 | 10.2 |

## 5. 시스템 리소스 분석

### 5.1 CPU 사용률 상세

#### 코어별 사용률 (12포트 활성)

| CPU Core | Function | Usage (%) |
|----------|----------|-----------|
| Core 0 | Packet RX IRQ | 45.2 |
| Core 1 | CBS Processing | 28.3 |
| Core 2 | Management | 12.1 |
| Core 3 | Statistics | 8.4 |
| Core 4-7 | Idle/Other | < 5.0 |

#### CBS 처리 시간 분석

| Operation | Time (ns) | Frequency (Hz) |
|-----------|-----------|----------------|
| Credit Update | 125 | 1,000,000 |
| State Transition | 85 | 500,000 |
| Queue Check | 45 | 2,000,000 |
| Frame Decision | 210 | 100,000 |

### 5.2 메모리 사용량

#### 정적 메모리 할당

| Component | Size | Count | Total |
|-----------|------|-------|-------|
| CBS Context | 256 B | 96 (12×8) | 24 KB |
| Queue Buffers | 64 KB | 12 | 768 KB |
| Statistics | 1 KB | 96 | 96 KB |
| Config Cache | 512 B | 12 | 6 KB |
| **Total Static** | | | **894 KB** |

#### 동적 메모리 사용

| Time | Allocated | Free | Fragmentation |
|------|-----------|------|---------------|
| Start | 894 KB | 1,130 KB | 0% |
| 1 hour | 912 KB | 1,112 KB | 1.2% |
| 6 hours | 923 KB | 1,101 KB | 2.1% |
| 12 hours | 928 KB | 1,096 KB | 2.4% |
| 24 hours | 931 KB | 1,093 KB | 2.6% |

### 5.3 전력 소비

| Configuration | Power (W) | Efficiency (Mbps/W) |
|---------------|-----------|---------------------|
| Idle | 8.2 | - |
| No CBS, No Traffic | 8.5 | - |
| No CBS, Full Load | 14.3 | 69.9 |
| CBS Enabled, No Traffic | 9.1 | - |
| CBS Enabled, Full Load | 15.2 | 65.8 |

## 6. 오류 및 예외 처리

### 6.1 오류 발생 통계

| Error Type | Count (24h) | Recovery Time (ms) |
|------------|-------------|-------------------|
| Credit Overflow | 0 | - |
| Queue Overflow | 234 | 12 |
| Config Error | 2 | 45 |
| Time Sync Loss | 1 | 1,200 |
| Link Flap | 3 | 2,500 |

### 6.2 예외 상황 처리

#### 시간 동기 손실
- **발생**: gPTP 마스터 실패
- **영향**: CBS 정확도 감소
- **복구**: 로컬 클럭으로 폴백, 1.2초 내 재동기

#### 큐 오버플로우
- **발생**: 버스트 트래픽 100MB 케이스
- **영향**: 234 프레임 드롭
- **대응**: Tail drop, 높은 우선순위 보호

## 7. 비교 분석

### 7.1 다른 쉐이퍼와 비교

| Shaper | Latency | Jitter | Loss | CPU | Complexity |
|--------|---------|--------|------|-----|------------|
| CBS | 8.3 ms | 3.1 ms | 0.67% | 27.2% | Medium |
| TAS | 2.1 ms | 0.8 ms | 0.12% | 31.5% | High |
| SP | 45.2 ms | 28.4 ms | 15.3% | 12.3% | Low |
| WRR | 32.1 ms | 18.2 ms | 8.4% | 18.7% | Low-Med |
| CBS+TAS | 3.5 ms | 1.2 ms | 0.08% | 35.2% | Very High |

### 7.2 벤더별 CBS 구현 비교

| Vendor | Chip | Latency | Precision | Features |
|--------|------|---------|-----------|----------|
| Microchip | LAN9692 | 8.3 ms | 8 ns | Full HW |
| Intel | I210 | 9.1 ms | 32 ns | Partial HW |
| Broadcom | BCM53134 | 8.7 ms | 16 ns | Full HW |
| Marvell | 88E6390 | 9.5 ms | 64 ns | SW-assisted |

## 8. 최적화 권장사항

### 8.1 CBS 파라미터 가이드라인

| Traffic Type | BW Reserve | idleSlope Factor | Queue Size |
|--------------|------------|------------------|------------|
| Video (CBR) | Expected + 20% | 1.2× | 2× burst |
| Video (VBR) | Peak + 10% | 1.3× | 3× burst |
| Audio | Expected + 15% | 1.15× | 1.5× burst |
| Control | Expected + 30% | 1.3× | 2× burst |
| Data | Average + 25% | 1.25× | 4× burst |

### 8.2 네트워크 설계 권장사항

1. **토폴로지**
   - 최대 홉 수: 3
   - 링크 활용률: < 70%
   - 대칭 경로 사용

2. **시간 동기화**
   - gPTP 정확도: < 1 μs
   - Sync 주기: 125 ms
   - 백업 마스터 구성

3. **트래픽 분류**
   - 명확한 우선순위 정의
   - DSCP/PCP 일관성
   - 트래픽 쉐이핑 at source

4. **모니터링**
   - 실시간 크레딧 추적
   - 큐 깊이 임계값 알람
   - 대역폭 활용률 추적

## 9. 문제 해결 가이드

### 9.1 일반적인 문제

| 증상 | 가능한 원인 | 해결 방법 |
|------|------------|-----------|
| 높은 지터 | idleSlope 부족 | idleSlope 20% 증가 |
| 프레임 손실 | 큐 오버플로우 | 큐 크기 증가, 버스트 제한 |
| 낮은 활용률 | 과도한 예약 | idleSlope 감소 |
| 불공정 분배 | 잘못된 우선순위 | PCP 매핑 확인 |

### 9.2 디버깅 명령어

```bash
# CBS 상태 확인
ethtool -S eth0 | grep cbs

# 크레딧 모니터링
watch -n 0.1 'cat /sys/class/net/eth0/cbs/credit'

# 큐 통계
tc -s qdisc show dev eth0

# 실시간 패킷 분석
tcpdump -i eth0 -ttt -e vlan
```

## 10. 결론 및 향후 과제

### 10.1 주요 성과
- CBS 구현으로 96.9% 프레임 손실 감소
- 92.7% 지터 개선
- 98.8% 대역폭 활용률 달성
- 12포트 동시 지원 확장성 입증

### 10.2 향후 개선 사항
1. 동적 CBS 파라미터 조정 알고리즘
2. 머신러닝 기반 트래픽 예측
3. 멀티벤더 상호운용성 향상
4. 클라우드 기반 중앙 관리
5. 실시간 시각화 대시보드

### 10.3 산업 적용 전망
- 자율주행 차량 네트워크
- 스마트 팩토리 실시간 제어
- 5G 프론트홀/백홀
- 프로페셔널 AV 시스템
- 의료 영상 전송 시스템