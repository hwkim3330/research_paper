# TSN CBS 설정 파일 (YAML)

이 디렉토리는 Microchip LAN9692 TSN 스위치의 CBS (Credit-Based Shaper) 구성을 위한 YAML 설정 파일들을 포함합니다.

## 📁 설정 파일 목록

### 1. ipatch-cbs-idle-slope.yaml
**목적**: CBS idleSlope 파라미터 설정

**내용**:
```yaml
# CBS idleSlope 설정
# 각 트래픽 클래스별 대역폭 예약
cbs-config:
  port-8:
    traffic-class-7:
      enabled: true
      idle-slope: 150000000  # 150 Mbps
      send-slope: -850000000  # -850 Mbps
      hi-credit: 1826         # bits
      lo-credit: -10350       # bits
    traffic-class-6:
      enabled: true
      idle-slope: 150000000
      send-slope: -850000000
      hi-credit: 1826
      lo-credit: -10350
```

**적용 방법**:
```bash
netconf-console --host 192.168.1.100 --port 830 \
    --edit-config ipatch-cbs-idle-slope.yaml
```

### 2. ipatch-vlan-set.yaml
**목적**: VLAN 및 PCP 매핑 설정

**내용**:
```yaml
# VLAN 설정 및 PCP 매핑
vlan-config:
  vlan-100:
    vid: 100
    name: "TSN_CBS_VLAN"
    ports:
      - port: 8
        mode: tagged
        pvid: false
      - port: 10
        mode: tagged
        pvid: false
      - port: 11
        mode: tagged
        pvid: false
    
  pcp-mapping:
    # PCP to Traffic Class 매핑
    map:
      - pcp: 7
        tc: 7
        desc: "Video Stream 1"
      - pcp: 6
        tc: 6
        desc: "Video Stream 2"
      - pcp: 5
        tc: 5
        desc: "Data Traffic 1"
      - pcp: 4
        tc: 4
        desc: "Data Traffic 2"
      - pcp: 3
        tc: 3
        desc: "Best Effort High"
      - pcp: 2
        tc: 2
        desc: "Best Effort Med"
      - pcp: 1
        tc: 1
        desc: "Best Effort Low"
      - pcp: 0
        tc: 0
        desc: "Background"
```

### 3. ipatch-p8-deco-p10-enco.yaml
**목적**: 포트 8 → 포트 10 트래픽 흐름 설정

**내용**:
```yaml
# 포트 8 (Sender) → 포트 10 (Receiver 1) 설정
flow-config:
  flow-1:
    name: "Video_Stream_1_to_Receiver_1"
    source:
      port: 8
      vlan: 100
      pcp: 7
    destination:
      port: 10
      ip: "10.0.100.2"
      udp-port: 5005
    cbs:
      enabled: true
      traffic-class: 7
    qos:
      dscp: 56  # CS7
      ecn: capable
```

### 4. ipatch-p8-deco-p11-enco.yaml
**목적**: 포트 8 → 포트 11 트래픽 흐름 설정

**내용**:
```yaml
# 포트 8 (Sender) → 포트 11 (Receiver 2) 설정
flow-config:
  flow-2:
    name: "Video_Stream_2_to_Receiver_2"
    source:
      port: 8
      vlan: 100
      pcp: 6
    destination:
      port: 11
      ip: "10.0.100.3"
      udp-port: 5006
    cbs:
      enabled: true
      traffic-class: 6
    qos:
      dscp: 48  # CS6
      ecn: capable
```

### 5. ipatch-p9-deco-p11-enco.yaml
**목적**: 포트 9 (BE 트래픽) → 포트 11 설정

**내용**:
```yaml
# 포트 9 (BE Generator) → 포트 11 (Receiver 2) 설정
flow-config:
  flow-be:
    name: "Best_Effort_to_Receiver_2"
    source:
      port: 9
      vlan: 100
      pcp: 0
    destination:
      port: 11
      ip: "10.0.100.3"
    cbs:
      enabled: false  # BE 트래픽은 CBS 미적용
    qos:
      dscp: 0  # BE
```

## 📋 통합 설정 파일

### master-config.yaml (전체 시스템 설정)
```yaml
# TSN CBS 마스터 설정 파일
system-config:
  name: "LAN9692_TSN_Switch"
  version: "2.3.0"
  location: "Lab_Rack_1"
  
time-sync:
  protocol: "gPTP"
  domain: 0
  priority1: 128
  priority2: 128
  
ports:
  - number: 8
    name: "Sender"
    speed: 1000
    duplex: full
    auto-neg: false
    
  - number: 9
    name: "BE_Generator"
    speed: 1000
    duplex: full
    auto-neg: false
    
  - number: 10
    name: "Receiver_1"
    speed: 1000
    duplex: full
    auto-neg: false
    
  - number: 11
    name: "Receiver_2"
    speed: 1000
    duplex: full
    auto-neg: false

cbs-global:
  enabled: true
  classes:
    - tc: 7
      name: "AVB_SR_A"
      bandwidth-percent: 15
      max-frame-size: 1522
      
    - tc: 6
      name: "AVB_SR_B"
      bandwidth-percent: 15
      max-frame-size: 1522
      
    - tc: 5
      name: "Data_High"
      bandwidth-percent: 10
      max-frame-size: 1522
      
    - tc: 4
      name: "Data_Low"
      bandwidth-percent: 10
      max-frame-size: 1522
```

## 🚀 설정 적용 절차

### 1. 전체 설정 적용
```bash
#!/bin/bash
# apply_all_configs.sh

SWITCH_IP="192.168.1.100"
CONFIG_DIR="/path/to/config"

# 1. VLAN 설정
netconf-console --host $SWITCH_IP --port 830 \
    --edit-config $CONFIG_DIR/ipatch-vlan-set.yaml

# 2. CBS 파라미터 설정
netconf-console --host $SWITCH_IP --port 830 \
    --edit-config $CONFIG_DIR/ipatch-cbs-idle-slope.yaml

# 3. 플로우 설정
for flow in ipatch-p8-deco-p10-enco.yaml \
            ipatch-p8-deco-p11-enco.yaml \
            ipatch-p9-deco-p11-enco.yaml; do
    netconf-console --host $SWITCH_IP --port 830 \
        --edit-config $CONFIG_DIR/$flow
done

echo "All configurations applied successfully!"
```

### 2. 설정 검증
```bash
# 현재 설정 확인
netconf-console --host 192.168.1.100 --port 830 \
    --get-config --source running \
    --filter '<cbs-config xmlns="urn:microchip:params:xml:ns:cbs"/>'
```

### 3. 설정 백업
```bash
# 실행 중인 설정을 백업
netconf-console --host 192.168.1.100 --port 830 \
    --get-config --source running > backup_$(date +%Y%m%d_%H%M%S).xml
```

## 📊 CBS 파라미터 계산 도구

### cbs_calculator.py
```python
#!/usr/bin/env python3
"""
CBS 파라미터 계산 도구
"""

def calculate_cbs_params(link_speed_mbps, bandwidth_percent, max_frame_bytes):
    """
    CBS 파라미터 계산
    
    Args:
        link_speed_mbps: 링크 속도 (Mbps)
        bandwidth_percent: 예약 대역폭 (%)
        max_frame_bytes: 최대 프레임 크기 (bytes)
    
    Returns:
        dict: CBS 파라미터
    """
    link_speed_bps = link_speed_mbps * 1_000_000
    idle_slope = int(link_speed_bps * bandwidth_percent / 100)
    send_slope = idle_slope - link_speed_bps
    hi_credit = int((max_frame_bytes * 8 * idle_slope) / link_speed_bps)
    lo_credit = int((max_frame_bytes * 8 * send_slope) / link_speed_bps)
    
    return {
        'idle_slope': idle_slope,
        'send_slope': send_slope,
        'hi_credit': hi_credit,
        'lo_credit': lo_credit
    }

# 사용 예시
if __name__ == "__main__":
    params = calculate_cbs_params(
        link_speed_mbps=1000,
        bandwidth_percent=15,
        max_frame_bytes=1522
    )
    
    print(f"idleSlope: {params['idle_slope']} bps")
    print(f"sendSlope: {params['send_slope']} bps")
    print(f"hiCredit: {params['hi_credit']} bits")
    print(f"loCredit: {params['lo_credit']} bits")
```

## 🔧 설정 템플릿

### CBS 설정 템플릿 생성기
```python
#!/usr/bin/env python3
"""
CBS YAML 설정 템플릿 생성기
"""

import yaml
import argparse

def generate_cbs_config(port, tc, bandwidth_mbps):
    """CBS 설정 YAML 생성"""
    
    # CBS 파라미터 계산
    idle_slope = bandwidth_mbps * 1_000_000
    send_slope = idle_slope - 1_000_000_000
    hi_credit = int((1522 * 8 * idle_slope) / 1_000_000_000)
    lo_credit = int((1522 * 8 * send_slope) / 1_000_000_000)
    
    config = {
        'cbs-config': {
            f'port-{port}': {
                f'traffic-class-{tc}': {
                    'enabled': True,
                    'idle-slope': idle_slope,
                    'send-slope': send_slope,
                    'hi-credit': hi_credit,
                    'lo-credit': lo_credit
                }
            }
        }
    }
    
    return yaml.dump(config, default_flow_style=False)

# CLI 인터페이스
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, required=True)
    parser.add_argument('-t', '--tc', type=int, required=True)
    parser.add_argument('-b', '--bandwidth', type=int, required=True)
    
    args = parser.parse_args()
    
    config = generate_cbs_config(args.port, args.tc, args.bandwidth)
    
    filename = f'cbs_port{args.port}_tc{args.tc}.yaml'
    with open(filename, 'w') as f:
        f.write(config)
    
    print(f"Configuration saved to {filename}")
```

## ⚙️ 고급 설정

### 1. 다중 도메인 TSN
```yaml
multi-domain:
  domains:
    - id: 0
      name: "Automotive"
      priority: high
      ports: [8, 10, 11]
      
    - id: 1
      name: "Infotainment"
      priority: medium
      ports: [9, 12]
```

### 2. 페일오버 설정
```yaml
redundancy:
  mode: "active-standby"
  primary-path:
    ports: [8, 10]
  backup-path:
    ports: [8, 12, 10]
  switchover-time: 50  # ms
```

### 3. 모니터링 알람
```yaml
monitoring:
  alarms:
    - name: "High Frame Loss"
      metric: "frame-loss-rate"
      threshold: 1.0  # percent
      action: "snmp-trap"
      
    - name: "Credit Exhaustion"
      metric: "min-credit"
      threshold: -10000  # bits
      action: "log-warning"
```

## 📝 설정 검증 체크리스트

- [ ] VLAN ID가 모든 포트에서 일치하는가?
- [ ] PCP 매핑이 올바르게 설정되었는가?
- [ ] idleSlope 합이 링크 용량을 초과하지 않는가?
- [ ] hiCredit/loCredit이 적절한 범위인가?
- [ ] 시간 동기화가 활성화되어 있는가?
- [ ] 포트 속도/듀플렉스가 올바른가?
- [ ] 트래픽 클래스 우선순위가 적절한가?

## 🔍 문제 해결

### 일반적인 설정 오류

| 증상 | 원인 | 해결 방법 |
|------|------|-----------|
| 설정 적용 실패 | YANG 모델 불일치 | 스위치 펌웨어 버전 확인 |
| CBS 미동작 | 포트 비활성화 | 포트 상태 확인 및 활성화 |
| 높은 프레임 손실 | idleSlope 부족 | 대역폭 예약 증가 |
| 불균등 분배 | PCP 매핑 오류 | VLAN/PCP 설정 검토 |

## 📚 참고 문서

- [YANG 데이터 모델 명세](../docs/yang_models.md)
- [NETCONF 프로토콜 가이드](../docs/netconf_guide.md)
- [CBS 파라미터 계산 가이드](../docs/cbs_parameters.md)

## 📄 라이센스

이 설정 파일들은 MIT 라이센스 하에 제공됩니다.