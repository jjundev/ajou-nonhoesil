---
schema: lab-netlist/v3
experiment: 6
spec: spec_observation_jk.md
---
# C1 · JK 프로토콜 표본
- kind: circuit
- id: C1
- item: E6.P1
- tables: [T1]

- U1 = 74HC76
  - pin 5 → VCC
  - pin 13 → GND

## 노드

| 노드 | 유형 | 식 | 핀 |
|---|---|---|---|
| Q | observed | - | U1 pin 15 |
| Qbar | observed | - | U1 pin 14 |

## 단계

| 단계 | 그림 | 이 단계에서 | 확인 |
|---|---|---|---|
| 1 | | U1 pin 15→LED Q 급전 | 노드 `Q` · 절차 `V1` — 하강 에지 확인 |

## 확인 절차 V1 · JK 유지·반전

- source: manual:p11
- provenance: derived
- rationale: 74HC76의 CLR 초기화와 J=K=0 유지, J=K=1 하강 에지 반전을 유도했다. 표본은 승인본이 아니다.
- setup: PR을 1에 고정하고 CLK을 0에 정지한다. CLR 초기화부터 시작한다.
- encoding: 0/1
- inputs: [J, K, CLK, CLR]
- clocks: [CLK]
- observe: [Q, Qbar]

| 순서 | 조작 | J | K | CLK | CLR | Q | Qbar |
|---|---|---|---|---|---|---|---|
| 1 | CLR 초기화 | 0 | 0 | 0 | 0 | 0 | 1 |
| 2 | CLR 해제 | 0 | 0 | 0 | 1 | 유지 | 유지 |
| 3 | 유지 상승 | 0 | 0 | 0->1 | 1 | 유지 | 유지 |
| 4 | 유지 하강 | 0 | 0 | 1->0 | 1 | 유지 | 유지 |
| 5 | J와 K 설정 | 1 | 1 | 0 | 1 | 유지 | 유지 |
| 6 | 반전 상승 | 1 | 1 | 0->1 | 1 | 유지 | 유지 |
| 7 | 반전 하강 | 1 | 1 | 1->0 | 1 | 반전 | 반전 |
