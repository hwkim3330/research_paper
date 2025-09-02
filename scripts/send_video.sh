#!/bin/bash
################################################################################
# send_video.sh - H.264 영상 스트림 전송 스크립트
#
# 작성자: TSN Research Team
# 날짜: 2025-09-02
# 버전: 1.0
#
# 설명:
#   VLC를 사용하여 H.264 영상을 UDP/MPEG-TS로 전송합니다.
#   CBS 테스트를 위해 두 개의 수신기로 동시 전송합니다.
#
# 사용법:
#   ./send_video.sh [옵션]
#
# 옵션:
#   -f FILE       : 영상 파일 경로 (필수)
#   -d1 DEST1     : 첫 번째 수신기 IP (기본: 10.0.100.2)
#   -d2 DEST2     : 두 번째 수신기 IP (기본: 10.0.100.3)
#   -p1 PORT1     : 첫 번째 포트 (기본: 5005)
#   -p2 PORT2     : 두 번째 포트 (기본: 5006)
#   -b BITRATE    : 비트레이트 (kbps, 기본: 15000)
#   -m MTU        : MTU 크기 (기본: 1400)
#   -l            : 반복 재생 (기본: 활성화)
#   -v            : 상세 로그 출력
#   -h            : 도움말 표시
#
################################################################################

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 기본 설정
VIDEO_FILE=""
DEST1="10.0.100.2"
DEST2="10.0.100.3"
PORT1=5005
PORT2=5006
BITRATE=15000
AUDIO_BITRATE=128
MTU=1400
TTL=16
LOOP=true
VERBOSE=false
NETWORK_CACHING=100

# 전송 통계
START_TIME=""
PID_VLC=""

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

# 도움말
show_help() {
    cat << EOF
H.264 영상 스트림 전송 스크립트

사용법: $0 -f VIDEO_FILE [옵션]

필수:
  -f FILE       영상 파일 경로

옵션:
  -d1 DEST1     첫 번째 수신기 IP (기본: 10.0.100.2)
  -d2 DEST2     두 번째 수신기 IP (기본: 10.0.100.3)
  -p1 PORT1     첫 번째 포트 (기본: 5005)
  -p2 PORT2     두 번째 포트 (기본: 5006)
  -b BITRATE    비디오 비트레이트 kbps (기본: 15000)
  -a AUDIO_BR   오디오 비트레이트 kbps (기본: 128)
  -m MTU        MTU 크기 (기본: 1400)
  -t TTL        TTL 값 (기본: 16)
  -c CACHE      네트워크 캐싱 ms (기본: 100)
  -n            반복 재생 비활성화
  -v            상세 로그 출력
  -h            이 도움말 표시

예시:
  $0 -f video.mp4
  $0 -f video.mp4 -b 20000 -d1 192.168.1.100 -p1 5000

네트워크 최적화:
  - MTU 1400: IP 단편화 방지
  - TTL 16: 멀티홉 환경 지원
  - 캐싱 100ms: 지연과 안정성 균형

EOF
    exit 0
}

# VLC 설치 확인
check_vlc() {
    if ! command -v cvlc &> /dev/null; then
        log_error "VLC가 설치되어 있지 않습니다."
        log_info "설치: sudo apt-get install vlc"
        exit 1
    fi
    
    # root 실행 방지
    if [[ $EUID -eq 0 ]]; then
        log_warn "VLC를 root로 실행하는 것은 권장하지 않습니다."
    fi
}

# 영상 파일 확인
check_video_file() {
    if [[ ! -f "$VIDEO_FILE" ]]; then
        log_error "영상 파일을 찾을 수 없습니다: $VIDEO_FILE"
        exit 1
    fi
    
    # 파일 정보 출력
    local file_size
    file_size=$(du -h "$VIDEO_FILE" | cut -f1)
    log_info "영상 파일: $VIDEO_FILE ($file_size)"
    
    # 코덱 정보 확인 (ffprobe 있는 경우)
    if command -v ffprobe &> /dev/null; then
        log_info "영상 정보:"
        ffprobe -v quiet -show_streams "$VIDEO_FILE" | grep -E "codec_name|width|height|r_frame_rate" | head -8
    fi
}

# 네트워크 연결 확인
check_network() {
    log_info "네트워크 연결 확인 중..."
    
    # 수신기 1 ping 테스트
    if ping -c 1 -W 1 "$DEST1" &> /dev/null; then
        log_success "수신기 1 ($DEST1) 연결 확인"
    else
        log_warn "수신기 1 ($DEST1) 응답 없음"
    fi
    
    # 수신기 2 ping 테스트
    if ping -c 1 -W 1 "$DEST2" &> /dev/null; then
        log_success "수신기 2 ($DEST2) 연결 확인"
    else
        log_warn "수신기 2 ($DEST2) 응답 없음"
    fi
}

# VLC 명령 생성
build_vlc_command() {
    local cmd="cvlc"
    
    # 반복 재생
    if [[ "$LOOP" == true ]]; then
        cmd+=" --loop"
    fi
    
    # 상세 로그
    if [[ "$VERBOSE" == true ]]; then
        cmd+=" -vvv"
    else
        cmd+=" --quiet"
    fi
    
    # 입력 파일
    cmd+=" \"$VIDEO_FILE\""
    
    # 트랜스코딩 및 스트리밍 설정
    cmd+=" --sout \"#transcode{"
    cmd+="vcodec=h264,vb=${BITRATE},"
    cmd+="acodec=mp4a,ab=${AUDIO_BITRATE},"
    cmd+="channels=2,samplerate=44100"
    cmd+="}:duplicate{"
    
    # 첫 번째 수신기
    cmd+="dst=std{access=udp{ttl=${TTL},mtu=${MTU}},"
    cmd+="mux=ts,dst=${DEST1}:${PORT1}},"
    
    # 두 번째 수신기
    cmd+="dst=std{access=udp{ttl=${TTL},mtu=${MTU}},"
    cmd+="mux=ts,dst=${DEST2}:${PORT2}}"
    cmd+="}\""
    
    # 추가 옵션
    cmd+=" --network-caching=${NETWORK_CACHING}"
    cmd+=" --sout-keep"
    cmd+=" --drop-late-frames"
    cmd+=" --skip-frames"
    
    echo "$cmd"
}

# 전송 시작
start_streaming() {
    log_info "영상 스트리밍 시작..."
    
    # 스트리밍 정보 출력
    echo -e "\n${BLUE}=== 스트리밍 설정 ===${NC}"
    echo "  비디오 비트레이트: ${BITRATE} kbps"
    echo "  오디오 비트레이트: ${AUDIO_BITRATE} kbps"
    echo "  수신기 1: ${DEST1}:${PORT1}"
    echo "  수신기 2: ${DEST2}:${PORT2}"
    echo "  MTU: ${MTU}, TTL: ${TTL}"
    echo "  네트워크 캐싱: ${NETWORK_CACHING}ms"
    echo ""
    
    # VLC 명령 실행
    local vlc_cmd
    vlc_cmd=$(build_vlc_command)
    
    if [[ "$VERBOSE" == true ]]; then
        log_info "실행 명령:"
        echo "$vlc_cmd"
    fi
    
    # 백그라운드로 실행
    eval "$vlc_cmd" &
    PID_VLC=$!
    START_TIME=$(date +%s)
    
    log_success "스트리밍 시작됨 (PID: $PID_VLC)"
    
    # 상태 모니터링
    monitor_streaming
}

# 스트리밍 모니터링
monitor_streaming() {
    log_info "스트리밍 모니터링 중... (Ctrl+C로 중지)"
    
    # 트랩 설정
    trap cleanup SIGINT SIGTERM
    
    while kill -0 $PID_VLC 2>/dev/null; do
        if [[ "$VERBOSE" == true ]]; then
            # 네트워크 통계 출력
            local elapsed=$(($(date +%s) - START_TIME))
            printf "\r전송 시간: %02d:%02d:%02d" $((elapsed/3600)) $((elapsed%3600/60)) $((elapsed%60))
        fi
        sleep 1
    done
}

# 정리 함수
cleanup() {
    echo ""
    log_info "스트리밍 중지 중..."
    
    if [[ -n "$PID_VLC" ]] && kill -0 $PID_VLC 2>/dev/null; then
        kill $PID_VLC
        wait $PID_VLC 2>/dev/null || true
    fi
    
    # 전송 통계 출력
    if [[ -n "$START_TIME" ]]; then
        local elapsed=$(($(date +%s) - START_TIME))
        echo -e "\n${BLUE}=== 전송 통계 ===${NC}"
        echo "  총 전송 시간: ${elapsed}초"
        echo "  예상 전송량: $((elapsed * BITRATE / 8 / 1024)) MB"
    fi
    
    log_success "스트리밍 종료됨"
    exit 0
}

# 옵션 파싱
parse_options() {
    while getopts "f:d:e:p:q:b:a:m:t:c:nvh" opt; do
        case $opt in
            f)
                VIDEO_FILE="$OPTARG"
                ;;
            d)
                DEST1="$OPTARG"
                ;;
            e)
                DEST2="$OPTARG"
                ;;
            p)
                PORT1="$OPTARG"
                ;;
            q)
                PORT2="$OPTARG"
                ;;
            b)
                BITRATE="$OPTARG"
                ;;
            a)
                AUDIO_BITRATE="$OPTARG"
                ;;
            m)
                MTU="$OPTARG"
                ;;
            t)
                TTL="$OPTARG"
                ;;
            c)
                NETWORK_CACHING="$OPTARG"
                ;;
            n)
                LOOP=false
                ;;
            v)
                VERBOSE=true
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
    
    # 간단한 형식 지원 (이전 버전 호환)
    if [[ -z "$VIDEO_FILE" ]] && [[ $# -eq 2 ]]; then
        DEST1="$1"
        DEST2="$2"
        shift 2
    fi
}

# 메인 함수
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  H.264 영상 스트림 전송 스크립트 ${NC}"
    echo -e "${BLUE}================================${NC}\n"
    
    parse_options "$@"
    
    # 필수 파라미터 확인
    if [[ -z "$VIDEO_FILE" ]]; then
        log_error "영상 파일을 지정하세요 (-f FILE)"
        show_help
    fi
    
    # 환경 확인
    check_vlc
    check_video_file
    check_network
    
    # 스트리밍 시작
    start_streaming
}

# 스크립트 실행
main "$@"