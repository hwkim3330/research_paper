# TSN CBS 실험 스크립트 모음

이 디렉토리는 TSN Credit-Based Shaper 실험을 위한 자동화 스크립트들을 포함합니다.

## 📁 스크립트 목록

### 1. setup_sender.sh
**목적**: 송신 PC의 네트워크 설정 및 CBS 구성

**주요 기능**:
- VLAN 인터페이스 생성 (VLAN ID 100)
- PCP (Priority Code Point) 매핑 설정
- TC (Traffic Control) 필터 구성
- 성능 최적화 (버퍼 크기, 오프로드 기능)

**사용법**:
```bash
sudo ./setup_sender.sh -i eth0 -v 100 -a 10.0.100.1/24
```

**옵션**:
- `-i INTERFACE`: 네트워크 인터페이스 지정
- `-v VLAN_ID`: VLAN ID 설정 (기본: 100)
- `-a IP_ADDR`: IP 주소 설정 (기본: 10.0.100.1/24)
- `-c`: 기존 설정 정리만 수행
- `-h`: 도움말 표시

### 2. send_video.sh
**목적**: H.264 영상 스트림을 UDP/MPEG-TS로 전송

**주요 기능**:
- VLC를 사용한 H.264 인코딩 및 스트리밍
- 두 개의 수신기로 동시 전송
- 실시간 전송 통계 모니터링
- 네트워크 연결 상태 확인

**사용법**:
```bash
./send_video.sh -f video.mp4 -b 15000 -d1 10.0.100.2 -d2 10.0.100.3
```

**옵션**:
- `-f FILE`: 영상 파일 경로 (필수)
- `-d1 DEST1`: 첫 번째 수신기 IP (기본: 10.0.100.2)
- `-d2 DEST2`: 두 번째 수신기 IP (기본: 10.0.100.3)
- `-p1 PORT1`: 첫 번째 포트 (기본: 5005)
- `-p2 PORT2`: 두 번째 포트 (기본: 5006)
- `-b BITRATE`: 비디오 비트레이트 kbps (기본: 15000)
- `-m MTU`: MTU 크기 (기본: 1400)
- `-v`: 상세 로그 출력

### 3. run_experiment.sh
**목적**: CBS 성능 실험 자동화 및 데이터 수집

**주요 기능**:
- CBS 설정 자동 적용
- 다양한 배경 트래픽 레벨 테스트
- 성능 메트릭 자동 수집
- 결과 분석 및 리포트 생성

**사용법**:
```bash
./run_experiment.sh --duration 300 --output results/
```

**실험 시나리오**:
1. CBS 효과성 검증 (CBS on/off 비교)
2. 확장성 테스트 (BE 트래픽 100-700 Mbps)
3. 버스트 처리 테스트
4. 장시간 안정성 테스트

### 4. setup_receiver.sh
**목적**: 수신 PC 네트워크 설정

**주요 기능**:
- VLAN 인터페이스 구성
- 수신 버퍼 최적화
- 패킷 캡처 환경 설정

**사용법**:
```bash
sudo ./setup_receiver.sh -i eth0 -v 100 -a 10.0.100.2/24
```

### 5. setup_switch_cbs.sh
**목적**: TSN 스위치 CBS 파라미터 구성

**주요 기능**:
- NETCONF를 통한 CBS 설정
- idleSlope, sendSlope 계산 및 적용
- 트래픽 클래스별 파라미터 설정

**사용법**:
```bash
./setup_switch_cbs.sh -h 192.168.1.100 -p 8 -t 7 -b 150
```

**옵션**:
- `-h HOST`: 스위치 IP 주소
- `-p PORT`: 포트 번호
- `-t TC`: 트래픽 클래스 (0-7)
- `-b BW`: 예약 대역폭 (Mbps)

### 6. monitor_cbs.sh
**목적**: 실시간 CBS 상태 모니터링

**주요 기능**:
- 크레딧 값 실시간 추적
- 큐 깊이 모니터링
- 처리량 및 손실률 표시
- 그래프 생성 (gnuplot 사용)

**사용법**:
```bash
./monitor_cbs.sh -i 1 -d 300
```

**옵션**:
- `-i INTERVAL`: 모니터링 간격 (초)
- `-d DURATION`: 모니터링 기간 (초)

### 7. analyze_results.py
**목적**: 실험 결과 분석 및 시각화

**주요 기능**:
- pcap 파일 분석
- 지연, 지터, 손실률 계산
- 그래프 생성 (matplotlib)
- LaTeX 테이블 생성

**사용법**:
```python
python3 analyze_results.py --input capture.pcap --output results/
```

### 8. generate_traffic.sh
**목적**: 배경 트래픽 생성

**주요 기능**:
- iperf3를 사용한 TCP/UDP 트래픽 생성
- 다양한 패킷 크기 및 패턴
- 버스트 트래픽 생성

**사용법**:
```bash
./generate_traffic.sh -t udp -r 500 -d 300
```

**옵션**:
- `-t TYPE`: 트래픽 유형 (tcp/udp)
- `-r RATE`: 전송 레이트 (Mbps)
- `-d DURATION`: 지속 시간 (초)

## 📋 실험 워크플로우

### 전체 실험 수행 절차

```bash
# 1. 네트워크 설정
sudo ./setup_sender.sh -i eth0
sudo ./setup_receiver.sh -i eth0  # 수신 PC에서
./setup_switch_cbs.sh -h 192.168.1.100

# 2. 실험 실행
./run_experiment.sh --duration 300 --output results/

# 3. 결과 분석
python3 analyze_results.py --input results/*.pcap

# 4. 정리
sudo ./setup_sender.sh -c
```

### 개별 테스트

#### CBS 효과성 테스트
```bash
# CBS 없이
./send_video.sh -f test.mp4 &
./generate_traffic.sh -r 500 -d 60
killall vlc

# CBS 활성화
./setup_switch_cbs.sh -h 192.168.1.100 -t 7 -b 150
./send_video.sh -f test.mp4 &
./generate_traffic.sh -r 500 -d 60
```

#### 버스트 처리 테스트
```bash
# 버스트 트래픽 생성
./generate_traffic.sh -t burst -s 100M -p 5
```

## 🛠️ 필수 패키지

### Ubuntu/Debian
```bash
sudo apt-get install -y \
    vlc \
    iperf3 \
    tcpdump \
    ethtool \
    iproute2 \
    python3-pip \
    gnuplot

pip3 install \
    scapy \
    matplotlib \
    pandas \
    numpy
```

### 커널 설정
```bash
# PREEMPT_RT 커널 설치 (선택사항, 성능 향상)
sudo apt-get install linux-image-rt-amd64

# 네트워크 버퍼 크기 조정
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728
```

## 📊 출력 파일 형식

### 실험 결과 디렉토리 구조
```
results/
├── experiment_<timestamp>/
│   ├── config.json         # 실험 설정
│   ├── cbs_on/
│   │   ├── capture.pcap    # 패킷 캡처
│   │   ├── metrics.csv     # 성능 메트릭
│   │   └── stats.json      # 통계 요약
│   ├── cbs_off/
│   │   └── ...
│   ├── graphs/
│   │   ├── latency.png     # 지연 그래프
│   │   ├── jitter.png      # 지터 그래프
│   │   └── throughput.png  # 처리량 그래프
│   └── report.pdf          # 종합 리포트
```

### 메트릭 CSV 형식
```csv
timestamp,frame_id,latency_ms,jitter_ms,lost,bandwidth_mbps
1693526400.123,1001,8.234,2.145,0,148.2
1693526400.234,1002,8.345,2.234,0,148.1
...
```

## ⚠️ 주의사항

1. **권한**: 대부분의 스크립트는 root 권한이 필요합니다
2. **네트워크 간섭**: 실험 중 다른 네트워크 트래픽 최소화
3. **시간 동기화**: NTP/PTP로 모든 시스템 시간 동기화 필수
4. **버퍼 오버플로우**: 큰 버스트 테스트 시 메모리 확인
5. **CPU 친화도**: 성능 향상을 위해 CPU 코어 바인딩 권장

## 📚 참고 문서

- [IEEE 802.1Qav 표준](https://standards.ieee.org/standard/802_1Qav-2009.html)
- [TSN 구성 가이드](../docs/tsn_configuration_guide.md)
- [실험 결과 분석](../experimental_results.md)
- [문제 해결 가이드](../docs/troubleshooting.md)

## 🤝 기여 방법

1. 이슈 등록: 버그나 개선사항 제안
2. Pull Request: 코드 개선 제출
3. 문서 개선: 오타 수정, 설명 추가
4. 테스트: 다양한 환경에서 테스트 및 피드백

## 📄 라이센스

MIT License - 자유롭게 사용, 수정, 배포 가능

## 📧 문의

- 이메일: hwkim@etri.re.kr
- GitHub Issues: [research_paper/issues](https://github.com/hwkim3330/research_paper/issues)