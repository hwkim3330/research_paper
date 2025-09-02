# 4-포트 크레딧 기반 셰이퍼(CBS) TSN 스위치를 활용한 차량용 QoS 보장 구현 및 성능 평가

## Implementation and Performance Evaluation of a 4-Port Credit-Based Shaper TSN Switch for QoS Provisioning in Automotive Ethernet

### 저자: 김현우, 송현수, 안종화, 박부식
### TSN Team, Automotive Electronics Research Division

---

## 요약

최근 전기/전자(E/E) 아키텍처가 영역(존) 기반 구조로 진화함에 따라, 차량 내 네트워크는 고대역폭 멀티미디어 스트림과 중요 제어 데이터를 포함한 다양한 트래픽 유형의 신뢰성 있는 전송을 요구받고 있다. 이 논문은 이러한 요구에 대응하기 위해 크레딧 기반 셰이퍼(Credit-Based Shaper, CBS)를 이용해 시스템을 구현하고, 이를 4포트 차량용 TSN(Time-Sensitive Networking) 스위치를 이용해 시험 및 성능 평가를 수행하였다.

**Keywords:** Automotive Ethernet, Credit-Based Shaper, Quality of Service, Zonal Architecture, Infotainment

---

## 1. 서론

현대 자동차의 전기/전자(E/E) 아키텍처는 도메인 기반 구조에서 존(Zone) 기반 구조로 빠르게 진화하고 있다. IEEE 802.1 TSN(Time-Sensitive Networking) 표준은 이러한 과제를 해결하기 위한 핵심 기술로 주목받고 있으며, 그 중에서도 IEEE 802.1Qav에 정의된 크레딧 기반 셰이퍼(CBS)는 시간 민감성 트래픽에 대한 대역폭 보장과 지연 제한을 제공한다.

---

## 2. 크레딧 기반 셰이퍼(CBS) 이론

### 2.1 CBS 동작 원리

CBS는 각 트래픽 클래스에 대해 '크레딧(credit)'이라는 값을 실시간으로 관리하며 전송 가능 여부를 결정한다.

**핵심 파라미터:**
- **idleSlope**: 큐가 비어있을 때 크레딧이 증가하는 속도 (bps)
- **sendSlope**: 프레임 전송 중 크레딧이 감소하는 속도
  - `sendSlope = idleSlope - portRate`

**크레딧 변화 규칙:**
```
credit_c 변화율 = {
  idleSlope_c  (큐가 idle 상태일 때)
  sendSlope_c  (전송 중일 때)
}
```

CBS는 `credit_c ≥ 0`인 경우에만 해당 트래픽 클래스의 프레임 전송을 허용한다.

---

## 3. 시스템 구현

### 3.1 하드웨어 플랫폼

**EVB-LAN9692-LM 주요 사양:**

| 구성요소 | 사양 |
|---------|------|
| CPU | ARM Cortex-A53 @ 1GHz |
| Memory | 2MiB ECC SRAM |
| Network | 4× SFP+ ports |
| TSN Features | IEEE 802.1Qav (CBS), 802.1Qbv (TAS), 802.1AS-2020 (gPTP) |
| Management | UART (MUP1), YANG/CoAP |

### 3.2 네트워크 토폴로지

```
[PC1: Video Source] --Port8--> [TSN Switch]
                                     |
                                     +-Port10--> [PC2: Receiver 1]
                                     |
                                     +-Port11--> [PC3: Receiver 2]
                                     |
[PC4: BE Traffic] ----Port9---------+
```

### 3.3 소프트웨어 구성

VelocityDRIVE-SP 펌웨어 기반 YANG 모델 설정:
- VLAN 기반 트래픽 분류 (VLAN ID 100)
- PCP 기반 트래픽 클래스 매핑 (TC0-TC7)
- CBS 파라미터 설정 (idleSlope, hiCredit, loCredit)
- 스트림 필터 및 포트 매핑

---

## 4. 실험 설계

### 4.1 실험 시나리오

#### 시나리오 1: CBS 비활성화 (Baseline)
- 모든 트래픽이 FIFO 방식으로 처리
- BE 트래픽(500-800Mbps)과 영상 스트림(각 15Mbps) 경쟁
- 예상: 영상 품질 저하, 높은 프레임 손실

#### 시나리오 2: CBS 활성화
- 영상 스트림: TC6, TC7 (각 idleSlope=20Mbps)
- BE 트래픽: TC0 (잔여 대역폭)
- 예상: 안정적인 영상 재생, 최소 프레임 손실

### 4.2 트래픽 생성

**영상 스트림 (VLC):**
```bash
cvlc --loop video.mp4 \
  --sout "#duplicate{
    dst=std{access=udp{mtu=1400},mux=ts,dst=10.0.100.2:5005},
    dst=std{access=udp{mtu=1400},mux=ts,dst=10.0.100.3:5005}}"
```

**BE 트래픽 (iperf3):**
```bash
iperf3 -u -c 10.0.100.2 -b 800M -t 60
```

---

## 5. 실험 결과

### 5.1 처리량 비교

| 트래픽 유형 | CBS 비활성화 | CBS 활성화 |
|------------|-------------|-----------|
| Video Stream 1 | 8.3 Mbps | 14.8 Mbps |
| Video Stream 2 | 7.9 Mbps | 14.7 Mbps |
| BE Traffic | 783 Mbps | 710 Mbps |
| **Total** | 799.2 Mbps | 739.5 Mbps |

CBS 활성화 시 영상 스트림이 요구 대역폭의 98% 이상을 안정적으로 확보

### 5.2 프레임 손실률 분석

| 측정 항목 | CBS 비활성화 | CBS 활성화 |
|----------|-------------|-----------|
| 총 전송 프레임 | 1,800 | 1,800 |
| 손실 프레임 | 387 | 12 |
| **손실률 (%)** | **21.5** | **0.67** |
| 평균 지터 (ms) | 42.3 | 3.1 |
| 최대 지터 (ms) | 185 | 8.5 |

### 5.3 주관적 품질 평가 (5점 척도)

- **CBS 비활성화**: 2.1점 (빈번한 끊김, 블록 현상, 음성 동기화 문제)
- **CBS 활성화**: 4.8점 (원활한 재생, 간헐적 미세 지연)

---

## 6. 성능 개선 효과

### 주요 성과:
- ✅ **프레임 손실률**: 21.5% → 0.67% (96.9% 개선)
- ✅ **평균 지터**: 42.3ms → 3.1ms (92.7% 개선)
- ✅ **대역폭 보장**: 55% → 98% (영상 스트림)
- ✅ **영상 품질**: 2.1점 → 4.8점 (주관적 평가)

---

## 7. 결론

본 연구는 차량용 이더넷 환경에서 CBS를 활용한 QoS 보장 시스템을 구현하고 성능을 검증하였다. 실험 결과, CBS는 네트워크 혼잡 상황에서도 시간 민감성 트래픽에 대해 안정적인 대역폭과 낮은 손실률을 보장함을 확인하였다.

### 핵심 기여:
1. Microchip LAN9692 기반 CBS 구현 및 검증
2. 실제 차량 인포테인먼트 시나리오 모사 실험
3. 정량적 성능 지표를 통한 CBS 효과 입증

### 향후 연구:
- 더 복잡한 네트워크 토폴로지 실험
- TAS와 CBS 조합 효과 분석
- 실시간 제어 트래픽 추가 검증

---

## 파일 구조

```
research_paper/
├── README.md                    # 이 파일 (논문 요약)
├── paper_latex.tex             # LaTeX 형식 논문 전체
├── 통신학회(구현논문지)_CBS구현_v1_250902_1.hwp  # 원본 HWP 논문
├── receiver_pc1_test.sh        # 수신측 테스트 스크립트
├── ipatch-*.yaml              # TSN 스위치 설정 파일들
└── EVB-LAN9692-LM-User-Guide-DS50003848 (2).pdf  # 보드 사용자 가이드
```

---

## Acknowledgment

본 논문은 산업통상자원부 재원으로 한국산업기술기획평가원(KEIT)의 지원을 받아 수행된 연구 결과입니다.

**과제 정보:**
- 사업명: 자동차산업기술개발사업(스마트카)
- 과제명: 자율주행차 전장부품 결함·오류 대응을 위한 기능 가변형 아키텍처 및 평가·검증기술 개발
- 과제 번호: RS-2024-00404601

---

## 참고문헌

1. IEEE 802.1Qav - Forwarding and Queuing Enhancements for Time-Sensitive Streams
2. Microchip LAN9692 - Automotive Ethernet Switch with TSN Support
3. S. Kehrer et al., "A comparison of fault-tolerance concepts for IEEE 802.1 TSN"
4. J. Imtiaz et al., "A performance study of Ethernet AVB for Industrial real-time communication"