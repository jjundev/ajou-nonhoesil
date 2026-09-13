---
schema: lab-spec/v2
experiment: 3
title: 가산기 & 감산기
source_manual: 강의노트/실험3. 가산기 & 감산기 (25.03.25 수정).pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E3.P1-1
    title: 실험 1-1) 반가산기
    device: [LED]
    ics: ["74HC86", "74HC08"]
    tables: [T1, T2]
  - id: E3.P1-2
    title: 실험 1-2) 전가산기
    device: [LED]
    ics: ["74HC86", "74HC08", "74HC32"]
    tables: [T3, T4]
  - id: E3.P2-1
    title: 실험 2-1) 반감산기
    device: [LED]
    ics: ["74HC86", "74HC04", "74HC08"]
    tables: [T5, T6]
  - id: E3.P2-2
    title: 실험 2-2) 전감산기
    device: [LED]
    ics: ["74HC86", "74HC04", "74HC08", "74HC32"]
    tables: [T7, T8]
---

<!--
`outputs` 속성의 씨앗. 2026-09-14 의 실험03 명세(2026-2 배포본 기준)에서
표 여덟 개를 셀 그대로 가져왔다 — 항목마다 기록표(`derived`)와 교안 원문
참조표(`manual:pN`, `role: reference`)가 짝이고, 참조표는 출력 열이 둘이다.

`outputs` 가 생기기 전에는 `split_columns` 가 참조표의 마지막 열 하나만
출력으로 봐서 `S`·`D` 를 입력으로 셌다. 그래서 T2·T6 에 "8행이어야
하는데 4행" warn, T4·T8 에 16행 warn, `S`·`D` 에 열 역할 info 가 났다.
`tests/test_lab_validate.py::TestDeclaredOutputs` 가 이 파일에서 `outputs`
줄만 걷어 그 오탐이 되살아나는지 본다 — 픽스처가 결함 자리를 실제로
지나는지를 그걸로 확인한다.

**살아 있는 실험 폴더가 아니라 픽스처다.** 실험03 명세를 다시 저작해도
이 파일은 따라 고치지 않는다.
-->

# E3.P1-1 · 실험 1-1) 반가산기

## T1 · 반가산기 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (S = A⊕B ; C = A·B)

| A | B | S | C |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 1 |

## T2 · 반가산기 Truth Table

- kind: truth-table
- encoding: 0/1
- source: manual:p4
- role: reference
- outputs: [S, C]

| A | B | S | C |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 1 |

# E3.P1-2 · 실험 1-2) 전가산기

## T3 · 전가산기 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (S = A⊕B⊕Ci ; Co = A·B + (A⊕B)·Ci)

| A | B | Ci | S | Co |
|---|---|----|---|----|
| 0 | 0 | 0  | 0 | 0  |
| 0 | 0 | 1  | 1 | 0  |
| 0 | 1 | 0  | 1 | 0  |
| 0 | 1 | 1  | 0 | 1  |
| 1 | 0 | 0  | 1 | 0  |
| 1 | 0 | 1  | 0 | 1  |
| 1 | 1 | 0  | 0 | 1  |
| 1 | 1 | 1  | 1 | 1  |

## T4 · 전가산기 Truth Table

- kind: truth-table
- encoding: 0/1
- source: manual:p5
- role: reference
- outputs: [S, Co]

| A | B | Ci | S | Co |
|---|---|----|---|----|
| 0 | 0 | 0  | 0 | 0  |
| 0 | 0 | 1  | 1 | 0  |
| 0 | 1 | 0  | 1 | 0  |
| 0 | 1 | 1  | 0 | 1  |
| 1 | 0 | 0  | 1 | 0  |
| 1 | 0 | 1  | 0 | 1  |
| 1 | 1 | 0  | 0 | 1  |
| 1 | 1 | 1  | 1 | 1  |

# E3.P2-1 · 실험 2-1) 반감산기

## T5 · 반감산기 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (D = A⊕B ; Bo = A'·B)

| A | B | D | Bo |
|---|---|---|----|
| 0 | 0 | 0 | 0  |
| 0 | 1 | 1 | 1  |
| 1 | 0 | 1 | 0  |
| 1 | 1 | 0 | 0  |

## T6 · 반감산기 Truth Table

- kind: truth-table
- encoding: 0/1
- source: manual:p6
- role: reference
- outputs: [D, Bo]

| A | B | D | Bo |
|---|---|---|----|
| 0 | 0 | 0 | 0  |
| 0 | 1 | 1 | 1  |
| 1 | 0 | 1 | 0  |
| 1 | 1 | 0 | 0  |

# E3.P2-2 · 실험 2-2) 전감산기

## T7 · 전감산기 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (D = A⊕B⊕Bi ; Bo = A'·B + (A⊕B)'·Bi)

| A | B | Bi | D | Bo |
|---|---|----|---|----|
| 0 | 0 | 0  | 0 | 0  |
| 0 | 0 | 1  | 1 | 1  |
| 0 | 1 | 0  | 1 | 1  |
| 0 | 1 | 1  | 0 | 1  |
| 1 | 0 | 0  | 1 | 0  |
| 1 | 0 | 1  | 0 | 0  |
| 1 | 1 | 0  | 0 | 0  |
| 1 | 1 | 1  | 1 | 1  |

## T8 · 전감산기 Truth Table

- kind: truth-table
- encoding: 0/1
- source: manual:p7
- role: reference
- outputs: [D, Bo]

| A | B | Bi | D | Bo |
|---|---|----|---|----|
| 0 | 0 | 0  | 0 | 0  |
| 0 | 0 | 1  | 1 | 1  |
| 0 | 1 | 0  | 1 | 1  |
| 0 | 1 | 1  | 0 | 1  |
| 1 | 0 | 0  | 1 | 0  |
| 1 | 0 | 1  | 0 | 0  |
| 1 | 1 | 0  | 0 | 0  |
| 1 | 1 | 1  | 1 | 1  |
