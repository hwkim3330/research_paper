#!/bin/bash
################################################################################
# setup_sender.sh - TSN CBS 실험을 위한 송신 PC 설정 스크립트
#
# 작성자: TSN Research Team
# 날짜: 2025-09-02
# 버전: 1.0
#
# 설명:
#   이 스크립트는 TSN CBS 실험에서 송신 PC를 설정합니다.
#   VLAN 인터페이스를 생성하고, PCP 매핑을 설정하며,
#   트래픽 클래스별 우선순위를 지정합니다.
#
# 사용법:
#   sudo ./setup_sender.sh [옵션]
#
# 옵션:
#   -i INTERFACE  : 네트워크 인터페이스 (기본: 자동 탐지)
#   -v VLAN_ID    : VLAN ID (기본: 100)
#   -a IP_ADDR    : IP 주소 (기본: 10.0.100.1/24)
#   -c            : 기존 설정 정리만 수행
#   -h            : 도움말 표시
#
# 예시:
#   sudo ./setup_sender.sh -i eth0 -v 100 -a 10.0.100.1/24
#
################################################################################

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본 설정값
DEV_SND=""
VLAN_ID=100
VLAN_IF="vlan${VLAN_ID}"
IP_ADDR="10.0.100.1/24"
CLEANUP_ONLY=false

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 도움말 표시
show_help() {
    cat << EOF
TSN CBS 송신 PC 설정 스크립트

사용법: sudo $0 [옵션]

옵션:
  -i INTERFACE  네트워크 인터페이스 (기본: 자동 탐지)
  -v VLAN_ID    VLAN ID (기본: 100)
  -a IP_ADDR    IP 주소 (기본: 10.0.100.1/24)
  -c            기존 설정 정리만 수행
  -h            이 도움말 표시

예시:
  sudo $0 -i eth0 -v 100 -a 10.0.100.1/24
  sudo $0 -c  # 설정 정리

필요 패키지:
  - iproute2
  - ethtool
  - tcpdump (선택)

EOF
    exit 0
}

# root 권한 확인
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "이 스크립트는 root 권한이 필요합니다. sudo를 사용하세요."
        exit 1
    fi
}

# 필요 패키지 확인
check_dependencies() {
    local deps=("ip" "tc" "ethtool")
    local missing=()
    
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing+=("$cmd")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "필요한 명령어가 없습니다: ${missing[*]}"
        log_info "설치: sudo apt-get install iproute2 ethtool"
        exit 1
    fi
}

# 네트워크 인터페이스 자동 탐지
auto_detect_interface() {
    local iface
    iface=$(ip -br link | awk '$1 !~ /^(lo|docker|veth|br-)/ && $2 == "UP" {print $1; exit}')
    
    if [[ -z "$iface" ]]; then
        log_error "활성 네트워크 인터페이스를 찾을 수 없습니다."
        exit 1
    fi
    
    echo "$iface"
}

# 기존 설정 정리
cleanup_config() {
    log_info "기존 설정 정리 중..."
    
    # tc 필터 제거
    tc qdisc del dev "$VLAN_IF" clsact 2>/dev/null || true
    
    # VLAN 인터페이스 제거
    if ip link show "$VLAN_IF" &>/dev/null; then
        ip link del "$VLAN_IF"
        log_info "VLAN 인터페이스 $VLAN_IF 제거됨"
    fi
    
    # NetworkManager 재활성화 (있는 경우)
    if command -v nmcli &>/dev/null && [[ -n "$DEV_SND" ]]; then
        nmcli dev set "$DEV_SND" managed yes 2>/dev/null || true
    fi
    
    log_success "정리 완료"
}

# VLAN 인터페이스 생성
create_vlan_interface() {
    log_info "VLAN 인터페이스 생성 중..."
    
    # 8021q 모듈 로드
    if ! lsmod | grep -q 8021q; then
        modprobe 8021q
        log_info "8021q 커널 모듈 로드됨"
    fi
    
    # NetworkManager 간섭 방지
    if command -v nmcli &>/dev/null; then
        nmcli dev set "$DEV_SND" managed no 2>/dev/null || true
    fi
    
    # VLAN 인터페이스 생성
    ip link add link "$DEV_SND" name "$VLAN_IF" type vlan id "$VLAN_ID"
    ip addr add "$IP_ADDR" dev "$VLAN_IF"
    ip link set "$VLAN_IF" up
    
    log_success "VLAN 인터페이스 $VLAN_IF 생성됨 (ID: $VLAN_ID)"
}

# PCP 매핑 설정
setup_pcp_mapping() {
    log_info "PCP 매핑 설정 중..."
    
    # Egress QoS 맵: skb priority → VLAN PCP (1:1 매핑)
    ip link set dev "$VLAN_IF" type vlan \
        egress-qos-map 0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7
    
    # Ingress QoS 맵: VLAN PCP → skb priority (선택)
    ip link set dev "$VLAN_IF" type vlan \
        ingress-qos-map 0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7
    
    log_success "PCP 매핑 설정 완료"
}

# 트래픽 클래스 필터 설정
setup_traffic_filters() {
    log_info "트래픽 클래스 필터 설정 중..."
    
    # clsact qdisc 추가
    tc qdisc add dev "$VLAN_IF" clsact
    
    # 포트별 우선순위 매핑
    # 5005: 영상 스트림 1 (Priority 7)
    tc filter add dev "$VLAN_IF" egress protocol ip prio 10 u32 \
        match ip dport 5005 0xffff \
        action skbedit priority 7
    
    # 5006: 영상 스트림 2 (Priority 6)
    tc filter add dev "$VLAN_IF" egress protocol ip prio 20 u32 \
        match ip dport 5006 0xffff \
        action skbedit priority 6
    
    # 6000-6007: iperf3 테스트 (Priority 0-7)
    for i in {0..7}; do
        port=$((6000 + i))
        tc filter add dev "$VLAN_IF" egress protocol ip prio $((30 + i)) u32 \
            match ip dport $port 0xffff \
            action skbedit priority $i
    done
    
    log_success "트래픽 필터 설정 완료"
}

# 설정 확인
verify_config() {
    log_info "설정 확인 중..."
    
    echo -e "\n${BLUE}=== 인터페이스 정보 ===${NC}"
    ip -br addr show "$VLAN_IF"
    
    echo -e "\n${BLUE}=== VLAN 설정 ===${NC}"
    ip -d link show "$VLAN_IF" | grep -E "vlan|qos"
    
    echo -e "\n${BLUE}=== TC 필터 ===${NC}"
    tc -s filter show dev "$VLAN_IF" egress | head -20
    
    echo -e "\n${BLUE}=== 인터페이스 통계 ===${NC}"
    ip -s link show "$VLAN_IF"
}

# 성능 최적화
optimize_performance() {
    log_info "성능 최적화 중..."
    
    # 인터페이스 버퍼 크기 증가
    ethtool -G "$DEV_SND" rx 4096 tx 4096 2>/dev/null || true
    
    # TCP 오프로드 기능 활성화
    ethtool -K "$DEV_SND" gso on tso on gro on 2>/dev/null || true
    
    # 인터럽트 조정
    if [[ -f /proc/irq/default_smp_affinity ]]; then
        echo ff > /proc/irq/default_smp_affinity
    fi
    
    log_success "성능 최적화 완료"
}

# 옵션 파싱
parse_options() {
    while getopts "i:v:a:ch" opt; do
        case $opt in
            i)
                DEV_SND="$OPTARG"
                ;;
            v)
                VLAN_ID="$OPTARG"
                VLAN_IF="vlan${VLAN_ID}"
                ;;
            a)
                IP_ADDR="$OPTARG"
                ;;
            c)
                CLEANUP_ONLY=true
                ;;
            h)
                show_help
                ;;
            \?)
                log_error "잘못된 옵션: -$OPTARG"
                show_help
                ;;
        esac
    done
}

# 메인 함수
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  TSN CBS 송신 PC 설정 스크립트  ${NC}"
    echo -e "${BLUE}================================${NC}\n"
    
    check_root
    check_dependencies
    parse_options "$@"
    
    # 인터페이스 자동 탐지
    if [[ -z "$DEV_SND" ]]; then
        DEV_SND=$(auto_detect_interface)
        log_info "자동 탐지된 인터페이스: $DEV_SND"
    fi
    
    # 정리만 수행
    if [[ "$CLEANUP_ONLY" == true ]]; then
        cleanup_config
        exit 0
    fi
    
    # 기존 설정 정리
    cleanup_config
    
    # 새 설정 적용
    create_vlan_interface
    setup_pcp_mapping
    setup_traffic_filters
    optimize_performance
    
    # 설정 확인
    verify_config
    
    echo -e "\n${GREEN}================================${NC}"
    echo -e "${GREEN}     설정이 완료되었습니다!      ${NC}"
    echo -e "${GREEN}================================${NC}"
    echo -e "\n다음 명령으로 영상 스트림을 전송하세요:"
    echo -e "${YELLOW}./send_video.sh${NC}"
}

# 스크립트 실행
main "$@"