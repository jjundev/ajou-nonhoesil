---
schema: lab-spec/v2
experiment: 7
title: Shift Register 관측 계약 표본
source_manual: 강의노트/실험7. Shift Register.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E7.P1
    title: 6bit Shift Right Register
    device: [LED]
    ics: ["74HC00", "74HC76"]
    tables: [T1]
---
# E7.P1 · 측정 빈칸 보존

## T1 · 직렬 입력 측정

- kind: stepped
- source: manual:p10

| 스텝 | 조작 | BIT1 | BIT2 | BIT3 | BIT4 | BIT5 | BIT6 |
|---|---|---|---|---|---|---|---|
| 1 | 초기화 | | | | | | |
| 2 | 클럭 하강 | | | | | | |
