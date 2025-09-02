#!/bin/bash
# VLAN100 수신 인터페이스(r100) 구성 + iperf3 서버 8포트 리슨(터미널 출력)
set -euo pipefail

DEV_RCV=enx606d3c4d3cb7
VLAN_ID=100
VLAN_IF=r100
R_IP=10.0.100.3
SERVER_INTERVAL=1

# === QoS 맵 적용 토글/커스터마이즈 ===
APPLY_QOS_MAP=1          # 1이면 아래 맵 적용
# Ingress: PCP -> skb priority (디코딩 맵)
INGRESS_MAP="0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7"
# Egress: skb priority -> PCP (인코딩 맵)
EGRESS_MAP="0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7"

# === NIC 오프로딩 토글(의심될 때만 1로 바꿔서 테스트) ===
TOGGLE_VLAN_OFFLOAD=0  # 1=off로 내려 테스트

# === 종료 시 정리(iperf3 서버/임시 설정 종료) ===
cleanup() {
  pkill -P $$ 2>/dev/null || true   # 이 스크립트가 띄운 자식 프로세스 종료
}
trap cleanup EXIT

# NIC 자동탐지
if [[ -z "${DEV_RCV:-}" ]]; then
  DEV_RCV=$(ip -br link | awk '$1 ~ /^enx/ && $1 !~ /\./ {print $1; exit}')
fi
[[ -n "${DEV_RCV:-}" ]] || { echo "상위 NIC(USB-LAN) 탐지 실패. DEV_RCV를 지정하세요."; exit 1; }

echo "== 0) 커널 모듈 확인 =="
lsmod | grep -q 8021q || sudo modprobe 8021q

echo "== 1) NetworkManager 간섭 방지(선택) =="
command -v nmcli >/dev/null && sudo nmcli dev set "$DEV_RCV" managed no || true

if [[ "$TOGGLE_VLAN_OFFLOAD" == "1" ]]; then
  echo "== 1.5) VLAN 오프로딩 일시 비활성화(드라이버 변수 배제 테스트) =="
  sudo ethtool -K "$DEV_RCV" tx-vlan-offload off rx-vlan-offload off || true
fi

echo "== 2) 잔여 정리 =="
sudo pkill -f "iperf3 -s" 2>/dev/null || true
sudo ip link del "$VLAN_IF" 2>/dev/null || true

echo "== 3) VLAN 인터페이스 생성 =="
sudo ip link add link "$DEV_RCV" name "$VLAN_IF" type vlan id "$VLAN_ID"
sudo ip addr add "$R_IP/24" dev "$VLAN_IF" 2>/dev/null || true
sudo ip link set "$VLAN_IF" up

if [[ "$APPLY_QOS_MAP" == "1" ]]; then
  echo "== 3.5) QoS 맵 적용 (PCP<->priority) =="
  # Ingress(PCP->prio), Egress(prio->PCP)
  sudo ip link set dev "$VLAN_IF" type vlan ingress-qos-map $INGRESS_MAP
  sudo ip link set dev "$VLAN_IF" type vlan egress-qos-map  $EGRESS_MAP
fi

echo "== 4) 상태 확인 =="
ip -br addr show "$VLAN_IF"
ip -d link show "$VLAN_IF" | sed -n '1,999p' | egrep -i 'vlan|egress-qos-map|ingress-qos-map|mtu|state' || true

echo "== 5) iperf3 서버 시작 (UDP, 6000~6007, 바인드 ${R_IP}) =="
for i in $(seq 0 7); do
  p=$((6000 + i))
  lbl="srv:$p"
  # 서버는 -u 없이; 클라이언트가 -u로 접속하면 UDP로 동작
  stdbuf -oL -eL iperf3 -s -B "$R_IP" -p "$p" -i "$SERVER_INTERVAL" \
    | sed -u "s/^/[${lbl}] /" &
  echo "[receiver] liste:wq!ning UDP on $p (bind $R_IP)"
done

echo "== 수신 준비 완료 =="
wait
