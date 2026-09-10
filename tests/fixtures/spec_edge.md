---
schema: lab-spec/v2
experiment: 6
title: Latch & Flip-Flop
source_manual: from_the_past/정리/강의노트/실험6.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E6.P1
    title: R-S Latch with Enable (Gate 이용)
    device: [LED]
    ics: ["74HC00"]
    tables: [T1]
  - id: E6.P2
    title: D Latch with Enable (Gate 이용)
    device: [LED]
    ics: ["74HC00", "74HC04"]
    tables: [T2]
  - id: E6.P3
    title: D F/F (IC 이용)
    device: [LED]
    ics: ["74HC74"]
    tables: [T3]
  - id: E6.P4
    title: J-K Latch with Enable (Gate 이용)
    device: [LED]
    ics: ["74HC10", "74HC00"]
    tables: [T4]
  - id: E6.P5
    title: J-K F/F (IC 이용)
    device: [LED]
    ics: ["74HC76"]
    tables: [T5]
---

<!--
`compare_specs` 검사의 기본 씨앗. 표 T1~T5·항목 다섯을 갖고,
머리말에 토큰 규약표(`0->1` 을 라이징 엣지로 정의하는 자리)가 하나 있다.
테스트가 라이징 엣지 셀·encoding 줄·source 줄을 한 군데씩 변형해 검사기가
그 자리를 짚는지 본다 — 그 값들이 본문에 있다는 것 자체가 계약이다.

**이 주석에는 본문 토큰을 그대로 적지 않는다.** `_mutated` 가 첫 한 번만
치환하므로, 주석이 같은 문자열을 담으면 본문 대신 주석이 바뀌어 검사기가
아무 차이도 못 보고 조용히 통과한다.

**살아 있는 실험 폴더가 아니라 픽스처다.** 2026-09-10 이전에는
`보고서/실험06/체크리스트/명세.md` 실물을 읽었다. 실험02~10 을 2026-2 교안
기준으로 다시 쓰려고 지우면서, 검사기 동작을 보는 테스트가 살아 있는 주차에
묶여 있던 결합을 끊었다 — 코퍼스가 학기 내내 갈아엎히는 저장소에서 그 결합
자체가 결함이었다.

내용은 그때의 실험06 명세에서 가져온 **표본**이지 근거 문서가 아니다.
쪽 번호·소자값은 검사기가 그 자리를 짚는지 보려고 남긴 것이지 교안 대조용이
아니다. 새 실험06 명세를 저작해도 이 파일은 따라 고치지 않는다.
-->

교안 준비물(p6): `74HC04` 1개, `74HC00` 2개, `74HC76` 1개, `74HC10` 1개, `74HC74` 1개,
LED 4개, 330Ω 4개.

**셀 값 표기 규약 — 교안 원문을 그대로 보존한다.**

| 토큰 | 뜻 | 근거 |
|---|---|---|
| `0` `1` | 비트 (`encoding: 0/1`) | 교안 표 원문 |
| `x` | don't care. 파서가 `X` 로 정규화한다 | 교안이 소문자 `x` 로 쓴다 |
| `0->1` | 라이징 엣지. 교안은 계단 기호(⌐)를 그림으로 넣어 텍스트 추출에서 사라진다 | p9·p11 을 300 DPI 렌더 후 vision 판독. p5 본문 "C가 0에서 1이 되는 riging edge" 와 일치 |
| `Q(t-1)` | 이전 상태 유지 | 교안 표 원문 |
| `Q(t-1)'` | 이전 상태의 보수 | 교안은 타이포그래피 어포스트로피(’)를 쓰지만 R5 저작 규칙대로 ASCII `'` 로 적는다 |
| `0 : Reset` `1 : Set` `Q(t-1)' : Toggle` | 비트/보수 + 라벨 복합 토큰 | 교안 표 원문 |

`Q(t-1)'` 은 **상태 토큰이지 부울식이 아니므로 오버바 승격 대상이 아니다**
(`docs/schema/lab-spec-v2.md` 의 R5 적용 범위 참조).

`x x 0` 행이 있는 표는 행 수가 `2^n` 이 아니다 — T1·T4·T5 는 3입력인데 5행이다.
행 수 검사는 `X` 가 있는 표에서 건너뛴다.

# E6.P1 · R-S Latch with Enable (Gate 이용)

교안 p7. `74HC00` 쿼드 NAND 한 개로 게이트 4개를 다 쓴다. C 가 HIGH 인 동안 입력이
출력에 반영된다.

`S=R=1, C=1` 행의 `Q(t)` 가 `1` 로 적혀 있다 — NAND 구성 R-S 래치의 금지 상태라
`Q`·`Q'` 가 동시에 1 이 되는 조건이다. 교안 값을 그대로 옮긴다.

## T1 · R-S Latch with Enable 특성표

- kind: truth-table
- encoding: 0/1
- source: manual:p7

| S | R | C | Q(t) |
|---|---|---|------|
| 0 | 0 | 1 | Q(t-1) |
| 0 | 1 | 1 | 0 : Reset |
| 1 | 0 | 1 | 1 : Set |
| 1 | 1 | 1 | 1 |
| x | x | 0 | Q(t-1) |

# E6.P2 · D Latch with Enable (Gate 이용)

교안 p8. R-S 래치의 `S` 를 `D` 로, `R` 을 `D'` 로 묶은 변형. `74HC04` 인버터 1개가
`D'` 를 만든다.

## T2 · D Latch with Enable 특성표

- kind: truth-table
- encoding: 0/1
- source: manual:p8

| D | C | Q(t) |
|---|---|------|
| 0 | 1 | 0 |
| 1 | 1 | 1 |
| x | 0 | Q(t-1) |

# E6.P3 · D F/F (IC 이용)

교안 p9. `74HC74` 로 구성한다. **`C` 열이 p8 과 달리 라이징 엣지 기호다** — 래치가
아니라 엣지 트리거 F/F 이기 때문이다. 텍스트 추출에서는 이 칸이 빈칸으로 나온다.

## T3 · D F/F 특성표

- kind: truth-table
- encoding: 0/1
- source: manual:p9

| D | C | Q(t) |
|---|---|------|
| 0 | 0->1 | 0 |
| 1 | 0->1 | 1 |
| x | 0 | Q(t-1) |

# E6.P4 · J-K Latch with Enable (Gate 이용)

교안 p10. `74HC10`(3입력 NAND) 2개와 `74HC00` 2개로 구성한다. `J=K=1` 에서 출력이
이전 값의 보수가 되는 것이 R-S 와의 차이다.

## T4 · J-K Latch with Enable 특성표

- kind: truth-table
- encoding: 0/1
- source: manual:p10

| J | K | C | Q(t) |
|---|---|---|------|
| 0 | 0 | 1 | Q(t-1) |
| 0 | 1 | 1 | 0 : Reset |
| 1 | 0 | 1 | 1 : Set |
| 1 | 1 | 1 | Q(t-1)' : Toggle |
| x | x | 0 | Q(t-1) |

# E6.P5 · J-K F/F (IC 이용)

교안 p11. `74HC76` 으로 구성한다. T4 와 표 내용이 같고 `C` 열만 레벨(`1`)에서
라이징 엣지(`0->1`)로 바뀐다 — 래치와 F/F 의 차이가 그 한 열에 있다.

## T5 · J-K F/F 특성표

- kind: truth-table
- encoding: 0/1
- source: manual:p11

| J | K | C | Q(t) |
|---|---|---|------|
| 0 | 0 | 0->1 | Q(t-1) |
| 0 | 1 | 0->1 | 0 : Reset |
| 1 | 0 | 0->1 | 1 : Set |
| 1 | 1 | 0->1 | Q(t-1)' : Toggle |
| x | x | 0 | Q(t-1) |
