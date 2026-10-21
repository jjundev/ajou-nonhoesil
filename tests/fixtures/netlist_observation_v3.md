---
schema: lab-netlist/v3
experiment: 7
spec: spec_observation_stepped.md
---
# C1 · 순차 관측 계약 표본
- kind: circuit
- id: C1
- item: E7.P1
- tables: [T1]

- U1 = 74HC00
  - pin 14 → VCC
- U2 = 74HC76
  - pin 5 → VCC

## 노드

| 노드 | 유형 | 식 | 핀 |
|---|---|---|---|
| SERIAL DATA 보수 | expression | SERIAL_DATA' | U1 pin 11 |
| BIT1 | observed | - | U2 pin 15 |

## 단계

| 단계 | 그림 | 이 단계에서 | 확인 |
|---|---|---|---|
| 1 | | 첫 FF를 연결한다 | 노드 `BIT1` · 절차 `V1` — 프로브 확인 |

## 확인 절차 V1 · BIT1 초기화 및 입력 확인

- source: manual:p9
- provenance: derived
- rationale: p8~10의 초기화와 하강 에지 동작을 부분 배선 순서로 구체화했다.
- setup: CLK을 0에 정지하고 PR1을 1에 둔다. 첫 행부터 실행한다.
- encoding: 0/1
- inputs: [SERIAL_DATA, CLK, CLR, PR1]
- clocks: [CLK]
- observe: [BIT1]

| 순서 | 조작 | SERIAL_DATA | CLK | CLR | PR1 | BIT1 |
|---|---|---|---|---|---|---|
| 1 | 초기화 | 0 | 0 | 0 | 1 | 0 |
| 2 | CLR 해제 | 0 | 0 | 1 | 1 | 0 |
| 3 | 데이터 설정 | 1 | 0 | 1 | 1 | 0 |
| 4 | 클럭 상승 | 1 | 0->1 | 1 | 1 | 0 |
| 5 | 클럭 하강 | 1 | 1->0 | 1 | 1 | 1 |
