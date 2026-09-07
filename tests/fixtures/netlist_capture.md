---
schema: lab-netlist/v2
experiment: 10
spec: ../체크리스트/명세.md
---

# 공통 규칙

- kind: common

- 모든 IC: VCC 와 GND 를 먼저 물린다
- 미사용 입력핀은 전부 GND

# C1 · DAC — 계단 파형 관찰

- kind: circuit
- id: C1
- item: E10.P1
- tables: [T1]

- U1 = 7490 (decade counter)
  - pin 5 → VCC(+5V)
  - 미사용 입력핀: pin 6, 7 → GND

# C2 · ADC — 전이점 기록 및 출력 전압 측정

- kind: circuit
- id: C2
- item: E10.P2
- tables: [T2]

- U5 = 741 (비교기)
  - pin 7 → +15V
  - 미사용 입력핀: 없음 → GND
