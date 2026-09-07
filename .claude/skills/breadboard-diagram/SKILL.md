---
name: breadboard-diagram
description: Generate accurate, publication-quality breadboard circuit wiring diagrams on physical breadboard templates for logic circuit labs. Use when drawing breadboard wiring diagrams, rendering IC pin connections, jumper wires, LED/resistors, or preparing pre-lab hand-drawing guides.
---

# Breadboard Diagram Skill (`breadboard-diagram`)

아주대학교 논리회로실험 표준 브레드보드 템플릿(`Breadboard.jpg`)을 기반으로, 회로 소자(IC), 점퍼선, 저항, LED를 물리적 홀 격자 규격에 맞춰 정밀하게 렌더링하는 스킬입니다.

## 1. 개요 및 목적
- **목적**: 학부 논리회로실험 운영계획서 규정(손스케치 첨부 필수, 미사용 핀 처리 규정, 보호 저항 필수)을 100% 충족하면서, 학생이 태블릿(GoodNotes 등)이나 종이에 따라 그릴 수 있는 오차 없는 정답 결선도 이미지를 제공합니다.
- **주요 기능**:
  1. 표준 브레드보드 템플릿 행/열 좌표 기반 정밀 안착.
  2. 칩별 정확한 DIP-14 핀아웃 매핑 (74HC00, 74HC02, 74HC04, 74HC08, 74HC32 등).
  3. **전기적/안전 규칙 강제**:
     - VCC(14번) -> +5V 적색 레일, GND(7번) -> 0V 청색 레일.
     - **미사용 입력 핀**: 노이즈 및 플로팅 방지를 위해 반드시 GND 레일로 개별 접지.
     - **미사용 출력 핀**: 내부 소손(Burn-out) 방지를 위해 **절대 접지 금지, 완전 개방(NC)** 처리.
     - **LED 및 330Ω 보호저항**: 단순 텍스트가 아닌 실제 다리 위치와 저항 색띠(주-주-갈-금)를 갖춘 실물 그래픽 배치.
  4. 브레드보드 물리 규칙 준수 (단자대 세로 절연, 동일 행 5홀 도통).
  5. 활성 행 영역(Active Rows) 자동 줌인 크롭 및 고대비 타이포그래피.

## 2. 브레드보드 물리 좌표계 (`Breadboard.jpg`)

**정본은 `.claude/assets/Breadboard.jpg` 한 장이다.** 아래 좌표는 전부 이 판본
(998x1345)에 맞춰 떠 놓은 것이라, "같은 브레드보드 그림"이면 아무거나 써도
되는 게 아니다. 렌더러는 저장소 루트 기준으로 이 파일을 먼저 찾고, 크기가
998x1345 가 아니면 그리기 전에 멈춘다.

> **2026-2 배포본으로 갈아끼우지 마라.** `강의노트/공지사항/Breadboard.pdf`
> 는 같은 도면이고 세로 좌표까지 일치하지만(보드 상하단 y=242·1317)
> **가로가 중앙 기준 약 5% 넓다.** 중앙 레일은 0~2px 차이인데 좌우 끝 레일이
> 최대 19px 밀린다 — 홀 간격이 17px 이니 한 열을 넘는다. 갈아끼우면 결선이
> 옆 홀에 그려지는데, 그림 자체는 멀쩡해 보여서 눈으로는 안 잡힌다. 배포본을
> 쓰려면 아래 좌표를 전부 다시 떠야 한다.
>
> `from_the_past/정리/강의노트/Breadboard.jpg` 는 정본과 바이트가 같은 과거
> 학기 사본이다. 최후 대체물로만 남아 있고, 본문·보고서에서는 인용하지 않는다.

- 캔버스 원본 크기: 998 x 1345 px
- 행 간격: 17.15 px (1행 y=243, r행 y = 243 + (r-1) * 17.15)
- 열 좌표:
  - **좌측 블록**:
    - GND(-) 레일: x = 163
    - VCC(+) 레일: x = 193
    - 단자대 a~e: x = [236, 252, 269, 286, 302]
    - 중앙 홈(Center Divider): x = 310 ~ 350 (IC 안착 부위)
    - 단자대 f~j: x = [358, 375, 392, 408, 425]
  - **중앙 전원 레일**:
    - GND(-) 레일: x = 458
    - VCC(+) 레일: x = 488

## 3. CLI 사용법
```bash
python3 .claude/skills/breadboard-diagram/scripts/render_breadboard.py \
    --circuit <circuit_id> \
    --output <output_path> \
    [--template <template_path>]
```

### 지원 회로 ID (`--circuit`):
- **실험 1 (기본 게이트 및 조합논리)**:
  - `e1_and`: 실험 1-1 3입력 AND 게이트 (74HC08)
  - `e1_or`: 실험 1-2 3입력 OR 게이트 (74HC32)
  - `e1_nand`: 실험 2-1 3입력 NAND 게이트 (74HC08 + 74HC00)
  - `e1_nor`: 실험 2-2 3입력 NOR 게이트 (74HC32 + 74HC02, 출력 1번 핀)
  - `e1_comb`: 실험 3 복합 논리회로 (74HC04 + 74HC08 + 74HC32, X, Y, Z 3출력)

**OR·NOR 은 2026-09-06 에 되살렸다.** 그 전에는 `e1_or`·`e1_nor` 가 각각
AND·NAND 빌더를 가리키는 별칭이라 **틀린 그림을 OR·NOR 이름으로 냈다.**
별칭을 지웠다가, `74HC32` 전용 빌더(`build_e1_or`)와 `74HC02` 빌더
(`build_e1_nor`, 출력이 1번 핀)를 실제로 작성해 복원했다. 두 회로가 한 빌더를
공유하지 않는지는 `tests/test_breadboard_diagram_cli.py` 가 검사한다.
- **실험 2 (CMOS 전기적 특성 및 전파지연)**:
  - `e2_inv`: 실험 2-1 Inverter 입출력 특성 회로 (74HC04 VTC, X-Y 모드)
  - `e2_schmitt`: 실험 2-2 Schmitt-trigger 입출력 특성 회로 (74HC14 Hysteresis)
  - `e2_rn`: 실험 2-3 (1) CMOS DC 특성 측정 — Rn (NMOS 온저항, 1kΩ 풀업)
  - `e2_rp`: 실험 2-3 (2) CMOS DC 특성 측정 — Rp (PMOS 온저항, 1kΩ 풀다운)
  - `e2_tpd`: 실험 2-4 CMOS AC 특성 측정 — 전파지연 tpd (74HC04 x 2개, 6단 체인 + 부하)
  - `e2_all`: 실험 2 결선도 5종 전체를 출력 디렉토리에 일괄 렌더링

## 4. 손스케치 활용 가이드 (학생용)
1. 생성된 고해상도 PNG를 필기 앱(GoodNotes, Notability, Samsung Notes 등)에 삽입합니다.
2. 이미지 불투명도를 40~50%로 설정한 후 상단 레이어에서 펜으로 점퍼선과 칩을 트레이싱합니다.
3. 우측 상단/하단 여백에 `작성일자 / 학번 / 성명`을 자필로 기재합니다.
