# 프로젝트 구조

```
research_paper/
│
├── README.md                    # 프로젝트 개요 및 주요 결과
├── PROJECT_STRUCTURE.md         # 이 파일 - 프로젝트 구조 설명
├── index.html                   # GitHub Pages 웹사이트
├── experimental_results.md      # 상세 실험 결과 및 분석
│
├── papers/                      # 논문 파일
│   ├── paper_korean_final.tex   # 한국어 논문 (한국통신학회)
│   ├── paper_english_final.tex  # 영문 논문 (IEEE)
│   ├── paper_complete.tex       # 초기 완성본
│   └── paper.md                 # Markdown 버전
│
├── config/                      # YAML 설정 파일
│   ├── README.md               # 설정 파일 문서
│   ├── ipatch-cbs-idle-slope.yaml
│   ├── ipatch-vlan-set.yaml
│   ├── ipatch-p8-deco-p10-enco.yaml
│   ├── ipatch-p8-deco-p11-enco.yaml
│   └── ipatch-p9-deco-p11-enco.yaml
│
├── scripts/                     # 실험 자동화 스크립트
│   ├── README.md               # 스크립트 문서
│   ├── setup_sender.sh         # 송신 PC 설정
│   ├── setup_receiver.sh       # 수신 PC 설정
│   ├── send_video.sh           # 영상 스트리밍
│   ├── run_experiment.sh       # 실험 자동화
│   ├── setup_switch_cbs.sh     # CBS 스위치 설정
│   ├── monitor_cbs.sh          # 실시간 모니터링
│   ├── generate_traffic.sh     # 트래픽 생성
│   └── analyze_results.py      # 결과 분석
│
├── docs/                        # 문서 및 참고자료
│   ├── EVB-LAN9692-LM-User-Guide.pdf
│   ├── tsn_configuration_guide.md
│   ├── yang_models.md
│   ├── netconf_guide.md
│   ├── cbs_parameters.md
│   └── troubleshooting.md
│
├── results/                     # 실험 결과 데이터
│   ├── captures/               # pcap 파일
│   ├── metrics/                # 성능 메트릭 CSV
│   ├── graphs/                 # 생성된 그래프
│   └── reports/                # 분석 리포트
│
├── src/                        # 소스 코드
│   ├── cbs_implementation.c    # CBS 구현 코드
│   ├── cbs_implementation.h    # 헤더 파일
│   ├── netconf_client.py       # NETCONF 클라이언트
│   ├── traffic_generator.py    # 트래픽 생성기
│   └── data_analyzer.py        # 데이터 분석 도구
│
├── tests/                      # 테스트 코드
│   ├── test_cbs_params.py     # CBS 파라미터 테스트
│   ├── test_network_setup.sh  # 네트워크 설정 테스트
│   └── test_performance.py    # 성능 테스트
│
└── .github/                    # GitHub 설정
    ├── workflows/              # GitHub Actions
    │   └── pages.yml          # Pages 자동 배포
    └── ISSUE_TEMPLATE/        # 이슈 템플릿
```

## 📂 주요 디렉토리 설명

### `/papers`
- 학술 논문 파일들 (LaTeX, Markdown)
- 한국어 및 영문 버전
- IEEE 및 한국통신학회 형식

### `/config`
- TSN 스위치 설정을 위한 YAML 파일
- CBS 파라미터, VLAN, 플로우 설정
- NETCONF/YANG 기반 구성

### `/scripts`
- 실험 자동화를 위한 Shell/Python 스크립트
- 네트워크 설정, 트래픽 생성, 모니터링
- 결과 분석 및 시각화

### `/docs`
- 기술 문서 및 가이드
- 하드웨어 매뉴얼
- 구성 및 문제 해결 가이드

### `/results`
- 실험 결과 데이터
- 패킷 캡처, 성능 메트릭
- 분석 그래프 및 리포트

### `/src`
- CBS 구현 소스 코드
- NETCONF 클라이언트
- 분석 도구

### `/tests`
- 단위 테스트 및 통합 테스트
- 성능 벤치마크
- 검증 스크립트

## 🔄 워크플로우

1. **설정 단계**
   - `/config`의 YAML 파일로 스위치 구성
   - `/scripts/setup_*.sh`로 호스트 설정

2. **실험 실행**
   - `/scripts/run_experiment.sh`로 자동화 실험
   - 결과는 `/results`에 저장

3. **분석 단계**
   - `/scripts/analyze_results.py`로 데이터 분석
   - 그래프 및 리포트 생성

4. **문서화**
   - 결과를 `/papers`의 논문에 반영
   - GitHub Pages (`index.html`)에 게시

## 🚀 빠른 시작

```bash
# 1. 프로젝트 클론
git clone https://github.com/hwkim3330/research_paper.git
cd research_paper

# 2. 의존성 설치
pip install -r requirements.txt
sudo apt-get install -y vlc iperf3 tcpdump

# 3. 실험 실행
cd scripts
./run_experiment.sh --duration 300

# 4. 결과 분석
python3 analyze_results.py --input ../results/captures/*.pcap

# 5. 웹 보기
open ../index.html
```

## 📋 체크리스트

### 초기 설정
- [ ] 네트워크 하드웨어 연결 확인
- [ ] IP 주소 설정 (10.0.100.0/24)
- [ ] VLAN 100 구성
- [ ] 시간 동기화 (PTP/NTP)

### 실험 준비
- [ ] 비디오 파일 준비 (H.264, 1080p)
- [ ] CBS 파라미터 계산
- [ ] 스크립트 실행 권한 설정
- [ ] 디스크 공간 확인 (최소 10GB)

### 실험 실행
- [ ] 기본 연결성 테스트
- [ ] CBS 설정 적용
- [ ] 트래픽 생성 시작
- [ ] 모니터링 활성화

### 결과 검증
- [ ] 패킷 캡처 파일 확인
- [ ] 메트릭 CSV 생성
- [ ] 그래프 생성
- [ ] 통계 분석 완료

## 🔧 개발 환경

### 필수 도구
- Python 3.8+
- Bash 4.0+
- LaTeX (논문 컴파일)
- Git

### Python 패키지
```txt
numpy==1.21.0
pandas==1.3.0
matplotlib==3.4.2
scapy==2.4.5
pyyaml==5.4.1
```

### 시스템 요구사항
- Ubuntu 20.04+ 또는 Debian 11+
- 최소 8GB RAM
- 10GB 여유 디스크 공간
- Gigabit Ethernet NIC

## 📝 기여 가이드라인

1. Fork 후 feature 브랜치 생성
2. 코드 작성 및 테스트
3. 문서 업데이트
4. Pull Request 제출

## 📄 라이센스

MIT License - 자세한 내용은 LICENSE 파일 참조

## 📧 연락처

- 주저자: 김현우 (hwkim@etri.re.kr)
- GitHub: https://github.com/hwkim3330/research_paper
- Issues: https://github.com/hwkim3330/research_paper/issues