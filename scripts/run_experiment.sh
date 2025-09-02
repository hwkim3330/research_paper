#!/bin/bash
################################################################################
# run_experiment.sh - TSN CBS 성능 실험 자동화 스크립트
#
# 작성자: TSN Research Team  
# 날짜: 2025-09-02
# 버전: 1.0
#
# 설명:
#   CBS 활성화/비활성화 상태에서 다양한 BE 트래픽 부하를 생성하고
#   영상 스트림의 성능 지표를 자동으로 측정합니다.
#
# 사용법:
#   sudo ./run_experiment.sh [옵션]
#
################################################################################

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 실험 설정
EXPERIMENT_NAME="CBS_Performance_$(date +%Y%m%d_%H%M%S)"
RESULT_DIR="./results/${EXPERIMENT_NAME}"
LOG_FILE="${RESULT_DIR}/experiment.log"

# 네트워크 설정
VIDEO_IP="10.0.100.1"
RECEIVER1_IP="10.0.100.2"
RECEIVER2_IP="10.0.100.3"
VIDEO_PORT1=5005
VIDEO_PORT2=5006
IPERF_PORT=5201

# 실험 파라미터
BE_LOADS=(0 100 200 400 600 800)  # Mbps
TEST_DURATION=60  # seconds
WARMUP_TIME=5     # seconds
COOLDOWN_TIME=10  # seconds

# 측정 데이터
declare -A RESULTS

# 로그 함수
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)
            echo -e "${GREEN}[INFO]${NC} ${message}"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${message}"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${message}"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} ${message}"
            ;;
        HEADER)
            echo -e "${BLUE}${message}${NC}"
            ;;
    esac
    
    echo "[${timestamp}] [${level}] ${message}" >> "$LOG_FILE"
}

# 진행 상황 표시
show_progress() {
    local current=$1
    local total=$2
    local width=50
    local percent=$((current * 100 / total))
    local filled=$((width * current / total))
    
    printf "\r["
    printf "%${filled}s" | tr ' ' '='
    printf "%$((width - filled))s" | tr ' ' ' '
    printf "] %3d%%" "$percent"
}

# 결과 디렉토리 생성
setup_directories() {
    log INFO "실험 환경 준비 중..."
    
    mkdir -p "$RESULT_DIR"/{captures,stats,graphs}
    
    # 실험 정보 저장
    cat > "${RESULT_DIR}/experiment_info.txt" << EOF
실험명: $EXPERIMENT_NAME
날짜: $(date)
호스트: $(hostname)
커널: $(uname -r)

네트워크 설정:
- Video Source: $VIDEO_IP
- Receiver 1: $RECEIVER1_IP
- Receiver 2: $RECEIVER2_IP
- Video Ports: $VIDEO_PORT1, $VIDEO_PORT2

실험 파라미터:
- BE Loads: ${BE_LOADS[*]} Mbps
- Test Duration: $TEST_DURATION seconds
- Warmup/Cooldown: $WARMUP_TIME/$COOLDOWN_TIME seconds
EOF
    
    log SUCCESS "실험 디렉토리 생성: $RESULT_DIR"
}

# CBS 상태 변경
set_cbs_state() {
    local state=$1  # "on" or "off"
    
    log INFO "CBS 상태 변경: $state"
    
    if [[ "$state" == "on" ]]; then
        # CBS 활성화 명령 (실제 환경에 맞게 수정)
        echo "CBS 활성화 중..." 
        # dr mup1cc -d /dev/ttyACM0 -m ipatch -i cbs_enable.yaml
    else
        # CBS 비활성화 명령
        echo "CBS 비활성화 중..."
        # dr mup1cc -d /dev/ttyACM0 -m ipatch -i cbs_disable.yaml
    fi
    
    sleep 2
}

# 패킷 캡처 시작
start_capture() {
    local test_name=$1
    local interface=${2:-eth0.100}
    
    log INFO "패킷 캡처 시작: $test_name"
    
    sudo tcpdump -i "$interface" -w "${RESULT_DIR}/captures/${test_name}.pcap" \
        -s 0 -n "vlan and (port $VIDEO_PORT1 or port $VIDEO_PORT2)" &
    
    echo $! > /tmp/tcpdump.pid
}

# 패킷 캡처 중지
stop_capture() {
    if [[ -f /tmp/tcpdump.pid ]]; then
        local pid=$(cat /tmp/tcpdump.pid)
        if kill -0 "$pid" 2>/dev/null; then
            sudo kill "$pid"
            wait "$pid" 2>/dev/null || true
        fi
        rm -f /tmp/tcpdump.pid
    fi
}

# VLC 통계 수집
collect_vlc_stats() {
    local test_name=$1
    local duration=$2
    
    log INFO "VLC 통계 수집 중..."
    
    # VLC 수신 통계 수집 (수신기에서 실행)
    ssh "$RECEIVER1_IP" "cvlc udp://@:${VIDEO_PORT1} --intf dummy --sout '#stat' --stop-time=${duration}" \
        > "${RESULT_DIR}/stats/${test_name}_receiver1.log" 2>&1 &
    
    ssh "$RECEIVER2_IP" "cvlc udp://@:${VIDEO_PORT2} --intf dummy --sout '#stat' --stop-time=${duration}" \
        > "${RESULT_DIR}/stats/${test_name}_receiver2.log" 2>&1 &
}

# iperf3 BE 트래픽 생성
generate_be_traffic() {
    local load=$1  # Mbps
    local duration=$2
    
    if [[ $load -eq 0 ]]; then
        log INFO "BE 트래픽 없음"
        return
    fi
    
    log INFO "BE 트래픽 생성: ${load} Mbps"
    
    iperf3 -c "$RECEIVER1_IP" -u -b "${load}M" -t "$duration" -i 1 \
        > "${RESULT_DIR}/stats/iperf_${load}M.log" 2>&1 &
    
    echo $! > /tmp/iperf.pid
}

# BE 트래픽 중지
stop_be_traffic() {
    if [[ -f /tmp/iperf.pid ]]; then
        local pid=$(cat /tmp/iperf.pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            wait "$pid" 2>/dev/null || true
        fi
        rm -f /tmp/iperf.pid
    fi
}

# 네트워크 통계 수집
collect_network_stats() {
    local test_name=$1
    local interface=${2:-eth0.100}
    
    # 인터페이스 통계
    ip -s link show "$interface" > "${RESULT_DIR}/stats/${test_name}_interface.txt"
    
    # TC 통계
    tc -s filter show dev "$interface" egress > "${RESULT_DIR}/stats/${test_name}_tc.txt"
    
    # netstat 통계
    netstat -su > "${RESULT_DIR}/stats/${test_name}_netstat.txt"
}

# 단일 테스트 실행
run_single_test() {
    local cbs_state=$1
    local be_load=$2
    local test_name="cbs_${cbs_state}_be_${be_load}M"
    
    log HEADER "\n=== 테스트: CBS=$cbs_state, BE Load=${be_load}Mbps ==="
    
    # CBS 상태 설정
    set_cbs_state "$cbs_state"
    
    # 패킷 캡처 시작
    start_capture "$test_name"
    
    # VLC 통계 수집 시작
    collect_vlc_stats "$test_name" $((TEST_DURATION + WARMUP_TIME + COOLDOWN_TIME))
    
    # Warmup
    log INFO "Warmup 시간: ${WARMUP_TIME}초"
    sleep "$WARMUP_TIME"
    
    # BE 트래픽 생성
    generate_be_traffic "$be_load" "$TEST_DURATION"
    
    # 테스트 진행
    log INFO "테스트 진행 중: ${TEST_DURATION}초"
    for i in $(seq 1 "$TEST_DURATION"); do
        show_progress "$i" "$TEST_DURATION"
        sleep 1
    done
    echo ""
    
    # BE 트래픽 중지
    stop_be_traffic
    
    # Cooldown
    log INFO "Cooldown 시간: ${COOLDOWN_TIME}초"
    sleep "$COOLDOWN_TIME"
    
    # 통계 수집
    collect_network_stats "$test_name"
    
    # 패킷 캡처 중지
    stop_capture
    
    log SUCCESS "테스트 완료: $test_name"
}

# 결과 분석
analyze_results() {
    log HEADER "\n=== 결과 분석 ==="
    
    # Python 스크립트 실행 (별도 작성 필요)
    if command -v python3 &>/dev/null; then
        python3 analyze_pcap.py "$RESULT_DIR" || true
    fi
    
    # 기본 통계 생성
    generate_basic_stats
}

# 기본 통계 생성
generate_basic_stats() {
    local stats_file="${RESULT_DIR}/summary.txt"
    
    log INFO "통계 요약 생성 중..."
    
    cat > "$stats_file" << EOF
================================================================================
실험 결과 요약
실험명: $EXPERIMENT_NAME
날짜: $(date)
================================================================================

테스트 케이스:
EOF
    
    # 각 pcap 파일 분석
    for pcap in "${RESULT_DIR}"/captures/*.pcap; do
        if [[ -f "$pcap" ]]; then
            local basename=$(basename "$pcap" .pcap)
            echo -e "\n--- $basename ---" >> "$stats_file"
            
            # 패킷 수 계산
            local packet_count=$(tcpdump -r "$pcap" 2>/dev/null | wc -l)
            echo "총 패킷 수: $packet_count" >> "$stats_file"
            
            # 프로토콜별 통계
            tcpdump -r "$pcap" -nn 2>/dev/null | \
                awk '{print $3}' | cut -d. -f5 | sort | uniq -c | \
                sort -rn | head -5 >> "$stats_file"
        fi
    done
    
    log SUCCESS "통계 요약 저장: $stats_file"
}

# 그래프 생성
generate_graphs() {
    log INFO "그래프 생성 중..."
    
    # gnuplot 스크립트 생성 및 실행 (예시)
    cat > "${RESULT_DIR}/plot.gp" << 'EOF'
set terminal png size 1200,800
set output "graphs/throughput.png"
set title "Throughput vs BE Load"
set xlabel "BE Traffic Load (Mbps)"
set ylabel "Video Stream Throughput (Mbps)"
set grid
set key top right

# 데이터 파일에서 플롯 (실제 데이터 형식에 맞게 수정 필요)
plot "stats/throughput_cbs_off.dat" using 1:2 with linespoints title "CBS OFF", \
     "stats/throughput_cbs_on.dat" using 1:2 with linespoints title "CBS ON"
EOF
    
    if command -v gnuplot &>/dev/null; then
        cd "$RESULT_DIR"
        gnuplot plot.gp 2>/dev/null || true
        cd - > /dev/null
    fi
}

# 실험 보고서 생성
generate_report() {
    local report_file="${RESULT_DIR}/report.html"
    
    log INFO "HTML 보고서 생성 중..."
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>TSN CBS 실험 결과 - $EXPERIMENT_NAME</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #2563eb; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #2563eb; color: white; }
        .success { color: #10b981; font-weight: bold; }
        .warning { color: #f59e0b; font-weight: bold; }
        .error { color: #ef4444; font-weight: bold; }
    </style>
</head>
<body>
    <h1>TSN CBS 성능 실험 결과</h1>
    <p>실험 날짜: $(date)</p>
    
    <h2>실험 구성</h2>
    <ul>
        <li>BE 트래픽 부하: ${BE_LOADS[*]} Mbps</li>
        <li>테스트 시간: ${TEST_DURATION}초</li>
        <li>영상 포트: ${VIDEO_PORT1}, ${VIDEO_PORT2}</li>
    </ul>
    
    <h2>테스트 결과</h2>
    <table>
        <tr>
            <th>CBS 상태</th>
            <th>BE Load (Mbps)</th>
            <th>패킷 수</th>
            <th>상태</th>
        </tr>
EOF
    
    # 결과 추가
    for pcap in "${RESULT_DIR}"/captures/*.pcap; do
        if [[ -f "$pcap" ]]; then
            local basename=$(basename "$pcap" .pcap)
            local packet_count=$(tcpdump -r "$pcap" 2>/dev/null | wc -l)
            local cbs_state=$(echo "$basename" | cut -d_ -f2)
            local be_load=$(echo "$basename" | cut -d_ -f4 | tr -d 'M')
            
            echo "<tr>" >> "$report_file"
            echo "<td>$cbs_state</td>" >> "$report_file"
            echo "<td>$be_load</td>" >> "$report_file"
            echo "<td>$packet_count</td>" >> "$report_file"
            
            if [[ $packet_count -gt 1000 ]]; then
                echo "<td class='success'>정상</td>" >> "$report_file"
            else
                echo "<td class='warning'>확인 필요</td>" >> "$report_file"
            fi
            echo "</tr>" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF
    </table>
    
    <h2>그래프</h2>
    <img src="graphs/throughput.png" alt="Throughput Graph" style="max-width: 100%;">
    
    <p>전체 결과는 <a href="summary.txt">summary.txt</a> 참조</p>
</body>
</html>
EOF
    
    log SUCCESS "보고서 생성: $report_file"
}

# 정리 함수
cleanup() {
    log WARN "실험 중단됨. 정리 중..."
    
    stop_be_traffic
    stop_capture
    
    # 임시 파일 정리
    rm -f /tmp/tcpdump.pid /tmp/iperf.pid
    
    log INFO "정리 완료"
    exit 1
}

# 메인 함수
main() {
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   TSN CBS 성능 실험 자동화 스크립트    ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}\n"
    
    # 트랩 설정
    trap cleanup SIGINT SIGTERM
    
    # 실험 준비
    setup_directories
    
    # 실험 시작 시간 기록
    local start_time=$(date +%s)
    
    # CBS OFF 테스트
    log HEADER "\n╔══════════════════════════════╗"
    log HEADER "║      CBS OFF 테스트 시작      ║"
    log HEADER "╚══════════════════════════════╝"
    
    for load in "${BE_LOADS[@]}"; do
        run_single_test "off" "$load"
    done
    
    # CBS ON 테스트
    log HEADER "\n╔══════════════════════════════╗"
    log HEADER "║      CBS ON 테스트 시작       ║"
    log HEADER "╚══════════════════════════════╝"
    
    for load in "${BE_LOADS[@]}"; do
        run_single_test "on" "$load"
    done
    
    # 결과 분석
    analyze_results
    generate_graphs
    generate_report
    
    # 실험 완료
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           실험 완료!                   ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo -e "\n총 실험 시간: $((duration / 60))분 $((duration % 60))초"
    echo -e "결과 디렉토리: ${BLUE}${RESULT_DIR}${NC}"
    echo -e "보고서: ${BLUE}${RESULT_DIR}/report.html${NC}\n"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi