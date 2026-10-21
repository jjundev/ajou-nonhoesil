---
schema: lab-netlist/v3
experiment: 7
spec: spec_observation_sixbit.md
---
# C1 · 여섯 출력 프로토콜 표본
- kind: circuit
- id: C1
- item: E7.P1
- tables: [T1]

- U1 = 74HC00
  - pin 14 → VCC
- U2 = 74HC76
  - pin 5 → VCC

- U3 = 74HC76
  - pin 5 → VCC
- U4 = 74HC76
  - pin 5 → VCC

## 노드

| 노드 | 유형 | 식 | 핀 |
|---|---|---|---|
| BIT1 | observed | - | U2 pin 15 |
| BIT2 | observed | - | U2 pin 11 |
| BIT3 | observed | - | U3 pin 15 |
| BIT4 | observed | - | U3 pin 11 |
| BIT5 | observed | - | U4 pin 15 |
| BIT6 | observed | - | U4 pin 11 |

## 단계

| 단계 | 그림 | 이 단계에서 | 확인 |
|---|---|---|---|
| 1 | | 여섯 FF의 출력 사슬을 연결한다 | 노드 `BIT1` · 절차 `V1` — 프로브 확인 |

## 확인 절차 V1 · 6비트 직렬 입력 확인

- source: manual:p9
- provenance: derived
- rationale: p8~10의 초기화와 하강 에지 동작을 여섯 FF 사슬의 확인 순서로 구체화했다.
- setup: CLK을 0에 정지하고 PR1을 1에 둔다. 첫 행부터 실행한다.
- encoding: 0/1
- inputs: [SERIAL_DATA, CLK, CLR, PR1]
- clocks: [CLK]
- observe: [BIT1, BIT2, BIT3, BIT4, BIT5, BIT6]

| 순서 | 조작 | SERIAL_DATA | CLK | CLR | PR1 | BIT1 | BIT2 | BIT3 | BIT4 | BIT5 | BIT6 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 초기화 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2 | CLR 해제 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | 첫 데이터 설정 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4 | 첫 상승 | 1 | 0->1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | 첫 하강 | 1 | 1->0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 6 | 다음 데이터 설정 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 7 | 둘째 상승 | 0 | 0->1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| 8 | 둘째 하강 | 0 | 1->0 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 |
