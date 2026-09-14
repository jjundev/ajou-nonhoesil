---
schema: lab-spec/v2
experiment: 3
title: 가산기 & 감산기
source_manual: 강의노트/실험3. 가산기 & 감산기 (25.03.25 수정).pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E3.P2-1
    title: 실험 2-1) 반감산기
    device: [LED]
    ics: ["74HC86", "74HC04", "74HC08"]
    tables: [T5, T6]
---

<!--
입력과 출력이 같은 글자인 표의 씨앗. 교안 p6 반감산기의 `Truth Table` 은
`입력 A B / 출력 D B` 2단 헤더다 — 내림 수가 입력 `B` 와 같은 글자 `B` 다.

2026-09-14 전에는 파서가 한 표 안의 같은 이름을 전부 거절해서, 실험03 명세가
출력 쪽을 p7 의 `Bo` 로 바꿔 적었다. 실험01 조교 감점("회로도의 출력 이름을
표에 보여야 한다") 뒤로 교안 표기를 그대로 싣도록 바꿨다 — 같은 글자는 자리로
가른다. 앞의 `B` 가 입력, 뒤의 `B` 가 출력이다.

**살아 있는 실험 폴더가 아니라 픽스처다.** 실험03 명세를 다시 저작해도
이 파일은 따라 고치지 않는다.
-->

# E3.P2-1 · 실험 2-1) 반감산기

## T5 · 반감산기 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (D = A⊕B ; B = A'·B)

| A | B | D | B |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 1 | 1 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 0 |

## T6 · 반감산기 Truth Table

- kind: truth-table
- encoding: 0/1
- source: manual:p6
- role: reference
- outputs: [D, B]

| A | B | D | B |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 1 | 1 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 0 |
