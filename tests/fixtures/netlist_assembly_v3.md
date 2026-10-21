---
schema: lab-netlist/v3
experiment: 7
spec: ../체크리스트/명세.md
---
# 회로
- kind: circuit
- id: C1
- item: I1
- tables: [T1]

U1 = 74HC00

## 조립 순서
| 소속 단계 | 순서 | 제목 | 그림 | 이번 작업 | 완료 확인 |
|---|---|---|---|---|---|
| 1 | 1 | 전원 | prep1.png | 레일 연결 | 극성 대조 |
| 1 | 2 | U2 | prep2.png | 입력 고정 | 핀 대조 |
| 1 | 3 | U3 | prep3.png | 입력 고정 | 핀 대조 |
| 1 | 4 | U4 | prep4.png | 입력 고정 | 핀 대조 |
| 1 | 5 | 위 LED | prep5.png | 사슬 연결 | 극성 대조 |
| 1 | 6 | 아래 LED | prep6.png | 사슬 연결 | 극성 대조 |

## 단계
| 단계 | 그림 | 이 단계에서 | 확인 |
|---|---|---|---|
| 1 | stage.png | D 입력 | 노드 `D` |
