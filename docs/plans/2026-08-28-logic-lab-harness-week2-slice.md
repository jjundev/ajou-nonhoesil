# 논리회로실험 하네스 — 2주차 수직 슬라이스 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**설계 근거 문서(스펙):** [2026-08-28-logic-lab-harness-design.md](docs/plans/2026-08-28-logic-lab-harness-design.md) — 결정 근거(R1~R10)·검증 결과·자료 권위 서열은 전부 그 문서에 있다. 이 계획서는 그것을 **어떻게 만드는지**만 담는다.

**Goal:** 2주차(실험1 Basic Gates)를 개념설명 → 예비보고서 → 실험실 체크리스트 → 결과보고서까지 관통시키는 Claude Code 하네스 7종과, 그것을 떠받치는 검증된 Python 코어를 만든다.

**Architecture:** 단일 소스(`<N>주차/체크리스트/명세.md`)에서 기록 템플릿·인쇄용 체크리스트·netlist·예비보고서 재료가 전부 파생된다. 파싱·정규화·검증·렌더링은 `scripts/lab/` 의 순수 함수로 두고 `tests/` 의 unittest 로 고정하며, `.claude/skills/*/SKILL.md` 는 그 함수들을 부르는 얇은 오케스트레이터로 둔다. 보고서 양식은 스킬에 박지 않고 `.claude/보고서양식.md` 로 파라미터화한다.

**Tech Stack:** Python 3.14 (**표준 라이브러리만** — PyYAML·pytest 없음), unittest, pypdf 6.14.2 (교안 판독), Markdown + 자체 프론트매터 서브셋, HTML + CSS (A4 인쇄), Google Chrome headless (PDF), Claude Code 프로젝트 스킬

**이 계획서의 범위:** 스펙의 Task 0~6 (2주차 수직 슬라이스). 스펙의 Task 7(실험7·8·9 확산 검증)과 ⑧ 퀴즈 대비·⑨ FPGA 프로젝트는 **후속 계획서**로 분리한다.

---

## Global Constraints

모든 Task 의 요구사항에 아래가 암묵적으로 포함된다.

- **환경은 macOS.** Windows 종속(`.bat`, PowerShell `Get-Date`, Edge headless, `C:\Users\Hyunjun\...` 하드코딩)을 이식 과정에서 전부 걷어낸다. 날짜는 `date +%Y.%m.%d`, PDF 는 Chrome headless.
- **PyYAML 이 없다.** `python3 -c "import yaml"` 이 이 머신에서 `ModuleNotFoundError` 다. 프론트매터는 `scripts/lab/md.py` 의 자체 서브셋 파서로 읽는다. **`import yaml` 을 쓰지 말 것.**
- **pytest 가 없다.** 저장소 관행대로 `unittest` 를 쓴다. 전체 실행: `python3 -m unittest discover -s tests -t .` (착수 시점 기준 55개 통과).
- **`scripts/lab/` 는 표준 라이브러리만 쓴다.** 기존 `scripts/*.py` 와 동일한 관행이다. 예외: 교안 판독은 `pypdf` (설치 확인됨, 6.14.2).
- **원본 자료는 읽기 전용.** `from_the_past/`, `강의계획서/`, `docs/` 아래를 코드가 수정하지 않는다. 유일한 예외는 Task 3 Step 7 의 `from_the_past/정리/README.md` 오류 정정이며, 이는 사람이 하는 1회성 수정이다.
- **PDF 텍스트 추출은 수식·기호를 파괴한다.** 오버바는 벡터 선이라 추출되지 않고, 라이징 엣지 화살표(↑)는 통째로 사라진다(실험6 p5 Clk 컬럼이 빈칸으로 추출되는 것을 확인). **표기·회로도·기호에 관한 판단은 반드시 `Read` 로 해당 PDF 페이지를 vision 판독할 것.** `extract_text()` 결과만 믿고 명세를 쓰면 안 된다.
- **`H/L` ↔ `0/1` 변환 금지 (R3).** encoding 은 표의 속성이다. 실험1 교안의 이론표는 `H/L`, 실험6 교안의 표는 `0/1` 이며 서로 다른 표기 그대로 명세에 싣는다.
- **주차 폴더가 모든 스킬의 전제다.** 폴더가 없으면 스킬은 생성하지 말고 거절하고 `init-lab-week` 초기화를 안내한다.
- **from_the_past 는 정답지가 아니라 코퍼스다.** 자료 권위 서열(스펙 §자료 권위 R9)을 지키고, 과거 제출본은 **다수결로만** 근거로 쓴다.
- **AI 활용 로깅 자리를 비워둔다.** 표기 의무 여부가 미확인이므로, 산출물을 만드는 모든 스킬은 `.claude/과목정보.md` 의 `ai_usage_log` 필드를 읽어 값이 있을 때만 로그를 남긴다. 값이 `~` 면 아무것도 하지 않는다.
- **커밋 메시지는 한국어 `type: 요약` 형식** (저장소 관행: `feat:`, `chore:`, `fix:`, `test:`).

---

## 스펙 대비 정정 사항

계획 수립 중 교안을 직접 판독해 확인한 것들이다. **스펙 본문보다 이 표가 우선한다.**

| 스펙의 서술 | 실제 (근거) | 반영 위치 |
|---|---|---|
| 실험1 `ics: ["74HC08 ×2", "74HC32 ×2"]` | 교안 p10 준비물은 **74HC00, 74HC02, 74HC04(2개), 74HC08, 74HC32, 74HC86, LED 3개.** 74HC08 은 quad 2-input AND 라 3-input AND 의 게이트 2개가 **한 패키지에서** 나온다. p11 의 `74HC08 74HC08` 은 게이트 심볼 라벨이지 칩 2개가 아니다 | Task 1 Step 2 |
| 실험1 = 항목 1개 | **항목 3개.** 실험1-1(3-input AND → OR 반복), 실험1-2(3-input NAND → NOR 반복, p12 는 `74HC08`+`74HC00`), 실험2(p13 복합회로, `74HC04`·`74HC32`·`74HC08`) | Task 1 Step 2 |
| 실험1 예시 `encoding: 0/1` | 교안 pp.4~9 이론표는 전부 **`L`/`H`**. 파생 3-input 표의 encoding 은 명세에서 **명시적으로 선언**하고 이론표와 섞지 않는다 | Task 1 Step 3 |
| 실험10 kind = `capture` | **두 kind 가 필요하다.** 교안 p11 실험1(DAC)은 "계단 파형을 관찰하고 그려라" → `capture`. p16 실험2(ADC)는 "single pulse 를 계속 인가해 counter 를 증가시키며 전이 지점을 기록하고 출력 전압을 측정(7405 핀 8·6·4·2)" → **`stepped`**. kind 는 실험 단위가 아니라 **표 단위** 속성임이 여기서 확인된다 | Task 1 Step 5 |
| 교집합 프리셋 결과보고서 = 실험 결과 + 고찰 | 평가기준.txt(권위 2순위)는 결보에 **실험 결과, 예비 비교, 결과 분석, 고찰(배운점·목적 달성 여부), 추가 공부**를 요구한다. 교집합은 권위 1·2순위의 합집합이어야 한다 | Task 3 Step 3 |
| 실험1 p13 복합회로가 3입력(`A\|B\|C` → `Y1\|Y2\|Y3`) | **2입력 2출력구조다.** 입력 A·B, 출력 X·Y·Z. Task 1 의 vision 판독으로 확정했고, `X ≡ Z` 항등이 성립한다(실험실 자체 검산에 쓸 수 있다). 한 표가 출력을 여럿 갖는 경우가 실재하므로 `source` 가 `derived (X = … ; Y = … ; Z = …)` 형태를 지원해야 한다 | Task 1 완료분 · Task 4/6 코드 |
| 74HC08·74HC32 핀아웃을 데이터시트 폴더에서 | **그 폴더에 없다.** `1_데이터시트_및_핀아웃/` 에는 74HC04(`datasheet.pdf`)·74HC03·74HC20·74HC42·74HC670·74HC76 뿐이고, `ic칩.txt` 는 기능 목록일 뿐 핀 번호가 없다. netlist 는 표준 DIP-14 핀아웃을 근거로 쓰고 **출처를 정직하게 그렇게 적으며**, 실물 대조를 미확정 항목으로 남긴다 | Task 1 Step 4 |

---

## File Structure

### 새로 만드는 Python 코어 — `scripts/lab/`

기존 저장소 관행(`scripts/*.py` 순수 함수 + `tests/test_*.py` unittest)을 그대로 따른다. 스킬은 이 함수들을 부르기만 한다.

| 파일 | 책임 |
|---|---|
| `scripts/lab/__init__.py` | 패키지 표식 (빈 파일) |
| `scripts/lab/md.py` | 프론트매터·마크다운 표 **원시 파싱**. 다른 모든 모듈의 기반 |
| `scripts/lab/config.py` | `.claude/과목정보.md` · `.claude/보고서양식.md` 로더 |
| `scripts/lab/spec_parser.py` | `명세.md` → `LabSpec` 객체 |
| `scripts/lab/notation.py` | R3 셀 정규화 · R5 보수 오버바 승격 · R6 active-low 라벨 |
| `scripts/lab/boolexpr.py` | 부울식 재귀 하강 평가기 (`eval` 미사용) |
| `scripts/lab/validate.py` | 표 무결성 · 진리표 행 수 · **부울식 역검산** · source/encoding · netlist · 양식 대조 |
| `scripts/lab/record.py` | `LabSpec` → `기록.md` 파생 |
| `scripts/lab/render.py` | kind 별 인쇄 HTML 조각 + 템플릿 치환 |
| `scripts/lab/html2pdf.py` | Chrome headless 래퍼 (macOS 전용 성공 판정 규칙 포함) |

대응 테스트: `tests/test_lab_md.py`, `test_lab_config.py`, `test_lab_spec_parser.py`, `test_lab_notation.py`, `test_lab_boolexpr.py`, `test_lab_validate.py`, `test_lab_record.py`, `test_lab_render.py`, `test_lab_html2pdf.py`

### 하네스 — `.claude/`

```
.claude/
  과목정보.md                      학부·과목·교수·분반·조·학번·성명·PDF 명령·ai_usage_log
  보고서양식.md                    프리셋 3종 (교집합 | 배포양식형 | 항목반복형)
  assets/Breadboard.jpg            빈 브레드보드 템플릿 (원본에서 복사)
  skills/
    init-lab-week/SKILL.md                    ⑦ 주차 폴더 초기화
    make-lab-report-cover/{SKILL.md,template.html}   ⑥ 표지 (이식)
    explain-lab-preview/{SKILL.md,template.html}     ① 개념 설명 (이식)
    prep-lab-checklist/{SKILL.md,template.html}      ② 체크리스트
    write-pre-report/{SKILL.md,template.html}        ③ 예비보고서
    review-lab-report/SKILL.md                       ⑤ 검증
    write-result-report/{SKILL.md,template.html}     ④ 결과보고서
```

### 주차 산출물

```
2주차/{강의노트,체크리스트,결선도,실험사진,퀴즈,STT,output}/
  체크리스트/{명세.md, 기록.md, 체크리스트.html, 체크리스트.pdf}
  결선도/netlist.md
  output/{2주차_예비보고서.md, 2주차_예비보고서.pdf, pre_review_round1.md}
12주차/체크리스트/명세.md          스키마 시험용 (capture + stepped)
6주차/체크리스트/명세.md           스키마 시험용 (심볼릭 토큰)
docs/schema/lab-spec-v1.md         스키마 판정 기록
```

### 수정

- `from_the_past/정리/README.md` — L18(camui20), L28(가이드라인) 설명 오류 정정

---

## Task 의존 그래프

```
Task 1 (명세 3종, 코드 없음)
   └─> Task 2 (md.py) ─┬─> Task 3 (config.py + 설정파일 + init + README)
                       └─> Task 4 (spec_parser.py) ─┬─> Task 6 (validate.py + ⑤)
                                                    └─> Task 8 (record/render + ②)
Task 5 (notation.py)  ──────────────────────────────┴─> Task 10 (③)
Task 7 (html2pdf.py + ⑥) ─> Task 8, Task 10
Task 9 (① 이식) — 독립
Task 6 ─> Task 10 ─> Task 11 (④)
```

---

### Task 1: 스키마 선행 검증 — 실험1·10·6 명세 (코드 없음)

스킬도 코드도 한 줄 쓰기 전에 스키마를 실전에서 세 번 시험한다(R10). 지금 스키마가 깨지면 고치는 비용이 0 에 가깝고, 스킬 8개를 짠 뒤에 깨지면 전부 다시 짜야 한다.

셋을 고른 이유가 각각 다르다 — 실험1은 **2주차 실전 대상**, 실험10은 **`capture` 가 성립하는지**, 실험6은 **열린 토큰 모델(R3)이 심볼릭 값을 담는지**.

**Files:**
- Create: `2주차/체크리스트/명세.md`
- Create: `2주차/결선도/netlist.md`
- Create: `12주차/체크리스트/명세.md`
- Create: `6주차/체크리스트/명세.md`
- Create: `docs/schema/lab-spec-v1.md`

**Interfaces:**
- Consumes: 없음 (교안 PDF 만 읽는다)
- Produces: `lab-spec/v1` 스키마의 실물 3종. Task 2·4 의 파서 테스트가 **이 파일들을 픽스처로 직접 읽는다** — 별도의 합성 픽스처를 만들지 않는다. `docs/schema/lab-spec-v1.md` 가 필드 계약의 정본이 된다.

- [ ] **Step 1: 주차 폴더를 만든다**

`init-lab-week` 스킬은 Task 3 에서 만든다. 지금은 손으로 만든다.

```bash
mkdir -p 2주차/{강의노트,체크리스트,결선도,실험사진,퀴즈,STT,output} \
         6주차/체크리스트 12주차/체크리스트 docs/schema
```

- [ ] **Step 2: 실험1 교안 13쪽을 전수 판독한다**

먼저 텍스트를 훑고, **회로도가 있는 p11·p12·p13 은 반드시 `Read` 로 vision 판독한다.** 텍스트 추출은 IC 라벨만 주고 배선을 주지 않는다.

```bash
python3 -c "
from pypdf import PdfReader
r = PdfReader('from_the_past/정리/강의노트/실험1.pdf')
for i, p in enumerate(r.pages):
    print(f'--- p{i+1} ---'); print(p.extract_text())
"
```

그다음 `Read from_the_past/정리/강의노트/실험1.pdf` 로 p11·p12·p13 을 눈으로 확인한다.

확정해야 할 것 (텍스트 추출로 이미 확인된 값 — vision 으로 **반증되지 않는지**만 보면 된다):

| 항목 | 교안 근거 | 내용 |
|---|---|---|
| 준비물 | p10 | 5V 전압원, IC: 74HC00 / 74HC02 / 74HC04(2개) / 74HC08 / 74HC32 / 74HC86, 발광다이오드 3개 |
| `E1.P1-1` | p11 | 3-input AND 구성 → Truth table 작성 → **OR gate 로 반복**(IC 는 학생이 찾음 = 74HC32). LED 에 330Ω 직렬 필수 |
| `E1.P1-2` | p12 | 3-input NAND 구성(`74HC08` + `74HC00`) → **NOR 로 반복**(= 74HC02) |
| `E1.P2` | p13 | 복합회로. `74HC04`·`74HC32`·`74HC08` 이 섞이고 LED 3개. **배선 위상은 vision 으로만 확정 가능** |

> **주의:** 스펙 본문의 `ics: ["74HC08 ×2", "74HC32 ×2"]` 는 틀렸다. 74HC08 은 quad 2-input AND 이므로 3-input AND 에 쓰는 게이트 2개가 한 패키지에서 나온다. p10 준비물대로 **각 1개**로 적는다.

- [ ] **Step 3: 실험1 진리표를 도출하고 `2주차/체크리스트/명세.md` 를 쓴다**

3-input 정답표는 교안에 없다. 부울대수로 도출하고 `source: derived (...)` 에 **도출 근거를 식으로 남긴다** — Task 6 의 역검산기가 이 식을 파싱해 표를 되짚는다.

교안의 2-input 이론표는 `L`/`H` 인코딩이다. 파생 3-input 표는 실험실에서 LED 로 읽으므로 `0/1` 로 쓰되, **표마다 `encoding` 을 명시 선언**하고 둘을 섞지 않는다(R3).

`2주차/체크리스트/명세.md`:

````markdown
---
schema: lab-spec/v1
week: 2
experiment: 1
title: Basic Gates
source_manual: from_the_past/정리/강의노트/실험1.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E1.P1-1
    title: 3-input AND / OR gate 구성
    device: [LED]
    ics: ["74HC08", "74HC32"]
    tables: [T1, T2]
  - id: E1.P1-2
    title: 3-input NAND / NOR gate 구성
    device: [LED]
    ics: ["74HC08", "74HC00", "74HC02"]
    tables: [T3, T4]
  - id: E1.P2
    title: 복합 논리회로 구성
    device: [LED]
    ics: ["74HC04", "74HC32", "74HC08"]
    tables: [T5]
---

# E1.P1-1 · 3-input AND / OR gate 구성

교안 p11. 2입력 게이트 2개를 캐스케이드해 3입력을 만든다.

## T1 · 3-input AND 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (Y = A·B·C)

| A | B | C | Y |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 0 | 1 | 0 |
| 0 | 1 | 0 | 0 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 0 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 0 |
| 1 | 1 | 1 | 1 |

## T2 · 3-input OR 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (Y = A+B+C)

| A | B | C | Y |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 0 | 1 | 1 |
| 0 | 1 | 0 | 1 |
| 0 | 1 | 1 | 1 |
| 1 | 0 | 0 | 1 |
| 1 | 0 | 1 | 1 |
| 1 | 1 | 0 | 1 |
| 1 | 1 | 1 | 1 |

# E1.P1-2 · 3-input NAND / NOR gate 구성

교안 p12. 3-input AND 뒤에 인버팅 게이트를 붙이는 구조가 아니라 `74HC08` + `74HC00` 조합이다.

## T3 · 3-input NAND 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (Y = (A·B·C)')

| A | B | C | Y |
|---|---|---|---|
| 0 | 0 | 0 | 1 |
| 0 | 0 | 1 | 1 |
| 0 | 1 | 0 | 1 |
| 0 | 1 | 1 | 1 |
| 1 | 0 | 0 | 1 |
| 1 | 0 | 1 | 1 |
| 1 | 1 | 0 | 1 |
| 1 | 1 | 1 | 0 |

## T4 · 3-input NOR 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (Y = (A+B+C)')

| A | B | C | Y |
|---|---|---|---|
| 0 | 0 | 0 | 1 |
| 0 | 0 | 1 | 0 |
| 0 | 1 | 0 | 0 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 0 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 0 |
| 1 | 1 | 1 | 0 |

# E1.P2 · 복합 논리회로 구성

교안 p13. **표 T5 의 열 구성과 `source` 식은 vision 판독으로 확정한 배선 위상에 따라 채운다.** 위상을 확정하지 못했으면 이 항목을 비워두지 말고 `source: manual:p13 (배선 미확정 — vision 재판독 필요)` 로 적고 미확정 표에 올린다.

## T5 · 복합회로 진리표

- kind: truth-table
- encoding: 0/1
- source: derived (vision 판독으로 확정한 식을 여기에)

| A | B | C | Y1 | Y2 | Y3 |
|---|---|---|----|----|----|
````

- [ ] **Step 4: `2주차/결선도/netlist.md` 를 쓴다**

이 과목의 대표 실패 원인은 플로팅 입력이다. **VCC(14)·GND(7)·미사용 입력핀 처리를 항목마다 빠짐없이** 적는다. LED 는 330Ω 직렬(교안 p11 명시).

`74HC08`·`74HC32` 핀아웃은 저장소의 데이터시트 폴더에 **없다**(74HC04 만 있다). 표준 DIP-14 quad 2-input 핀아웃을 근거로 쓰되 **출처를 그렇게 정직하게 적고**, 실물 대조를 미확정 항목으로 남긴다.

`2주차/결선도/netlist.md`:

````markdown
---
schema: lab-netlist/v1
week: 2
experiment: 1
spec: ../체크리스트/명세.md
---

# 공통 규칙

- 모든 IC: pin 14 → VCC(+5V), pin 7 → GND
- **미사용 입력핀은 전부 GND 로 내린다.** 플로팅 금지
- LED 는 애노드 쪽에 330Ω 직렬 (교안 p11)
- 핀아웃 출처: 표준 74HC 시리즈 DIP-14 quad 2-input 배치.
  `1_데이터시트_및_핀아웃/` 에 74HC08·74HC32·74HC00·74HC02 데이터시트가 없어
  실물 칩 각인과 1주차에 대조할 것 (미확정 사항 표 참조)

# E1.P1-1 · 3-input AND (74HC08)

- U1 = 74HC08 (quad 2-input AND, DIP-14)
  - pin 14 → VCC(+5V)
  - pin 7  → GND
  - pin 1  ← 입력 A
  - pin 2  ← 입력 B
  - pin 3  → U1.pin4          (게이트1 출력 → 게이트2 입력)
  - pin 5  ← 입력 C
  - pin 6  → LED1 애노드 (330Ω 직렬) → GND
  - 미사용 입력핀: pin 9, 10, 12, 13 → GND

# E1.P1-1 · 3-input OR (74HC32)

- U2 = 74HC32 (quad 2-input OR, DIP-14)
  - pin 14 → VCC(+5V)
  - pin 7  → GND
  - pin 1  ← 입력 A
  - pin 2  ← 입력 B
  - pin 3  → U2.pin4
  - pin 5  ← 입력 C
  - pin 6  → LED2 애노드 (330Ω 직렬) → GND
  - 미사용 입력핀: pin 9, 10, 12, 13 → GND
````

나머지 항목(`E1.P1-2` NAND/NOR, `E1.P2` 복합회로)도 같은 형식으로 이어 쓴다. NAND 는 교안 p12 대로 `74HC08` 의 게이트 출력을 `74HC00` 입력으로 넣는 구성이고, NOR 는 `74HC32` → `74HC02` 구성이다.

- [ ] **Step 5: `12주차/체크리스트/명세.md` — `capture` 유형을 시험한다**

교안 실험10 을 읽는다.

```bash
python3 -c "
from pypdf import PdfReader
r = PdfReader('from_the_past/정리/강의노트/실험10.pdf')
for i, p in enumerate(r.pages):
    print(f'--- p{i+1} ---'); print(p.extract_text())
"
```

**여기서 스펙이 깨진다 — 그리고 깨지는 방향이 스키마를 강화한다.** 스펙은 실험10 전체를 `capture` 로 봤지만 교안은 둘로 갈린다:

| 교안 | 지시 | 판정 |
|---|---|---|
| p11 실험1 (DAC) | "주파수 발생기로 계단 파형(1KHz)이 나오는지 관찰하고 **파형을 그려라**" | `capture` — 예상값이 정성적 서술이다 |
| p16 실험2 (ADC) | "single pulse clock 을 계속 인가해 counter 를 증가시키며, ADC 3번 핀이 5~15V 로 변할 때 **출력이 변화되는 지점을 기록하고 출력 전압을 측정**(7405 핀 8·6·4·2)" | **`stepped`** — 스텝 축이 counter 값이다 |

따라서 **kind 는 실험 단위가 아니라 표 단위 속성**이라는 점이 확인된다. 명세에 항목 2개를 두고 kind 를 다르게 준다.

`capture` 표의 예상값 문제 — 스펙이 "무엇을 적을지가 여기서 판가름난다"고 한 부분이다. **해법: `capture` 표는 셀 표가 아니라 `expected` 산문 필드를 갖는다.**

````markdown
---
schema: lab-spec/v1
week: 12
experiment: 10
title: D/A & A/D converter
source_manual: from_the_past/정리/강의노트/실험10.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E10.P1
    title: DAC — 계단 파형 관찰
    device: [oscilloscope]
    ics: ["7490", "7404", "741 OP amp"]
    tables: [T1]
  - id: E10.P2
    title: ADC — 전이점 기록 및 출력 전압 측정
    device: [oscilloscope, DMM]
    ics: ["7490", "7405", "741 OP amp"]
    tables: [T2]
---

# E10.P1 · DAC — 계단 파형 관찰

## T1 · DAC 출력 계단 파형

- kind: capture
- source: manual:p11
- expected: 1KHz 입력에서 counter 가 0→9 로 증가하는 동안 출력이 균등 간격으로
  계단 상승한 뒤 리셋되는 톱니 형태. 계단 개수는 7490 의 모듈러스(10)를 따른다.
  계단 높이가 불균등하면 저항 사다리(R-2R 또는 가중 저항) 오차를 먼저 의심한다.

# E10.P2 · ADC — 전이점 기록 및 출력 전압 측정

## T2 · ADC 전이점

- kind: stepped
- encoding: 0/1
- source: manual:p16

| 스텝 | 조작 | 3번 핀 전압 | 7405 핀8 | 핀6 | 핀4 | 핀2 |
|------|------|-------------|----------|-----|-----|-----|
| S1 | counter reset(0), 가변저항 최소 | | | | | |
| S2 | single pulse 1회 → counter=1 | | | | | |
| S3 | single pulse 1회 → counter=2 | | | | | |
````

`expected` 가 `capture` 에서만 나타나는 필드다. 이것을 `lab-spec/v1` 에 정식으로 넣는다.

- [ ] **Step 6: `6주차/체크리스트/명세.md` — 열린 토큰 모델을 시험한다**

교안 실험6 을 읽는다. **p5 의 Clk 컬럼이 텍스트 추출에서 빈칸으로 나온다** — 라이징 엣지 화살표(↑)가 벡터라 추출되지 않기 때문이다. 반드시 `Read` 로 p5 를 vision 판독해서 실제 기호를 확인한다.

교안이 실제로 쓰는 셀 토큰 (p4·p7~p11 확인):

```
0  1              비트 (encoding: 0/1 — 실험1의 H/L 과 다르다)
x                 don't care  → 정규화하면 X
Q(t-1)            이전 상태 유지
Q(t-1)'           이전 상태의 보수 (J-K 토글)
0 : Reset         비트 + 라벨 복합
1 : Set
Q(t-1)' : Toggle  보수 + 라벨 복합
```

`0 : Reset` 같은 복합 토큰이 **닫힌 enum 으로는 절대 안 담긴다**는 것이 R3(열린 토큰)의 실증이다. 이 명세를 쓰면서 세 가지를 확인한다:

1. `Q(t-1)'` 이 R5 의 보수 표기 규칙과 충돌하지 않는가 → **충돌하지 않는다. 셀 값은 부울식이 아니므로 오버바 승격 대상이 아니다.** 이 구분을 `docs/schema/lab-spec-v1.md` 에 명문화한다.
2. `x x 0` 행이 있는 표는 행 수가 `2^n` 이 아니다(실험6 R-S Latch 는 3입력인데 5행). → Task 6 의 행 수 검사는 **error 가 아니라 warn 이고, `X` 가 있는 표에서는 건너뛴다.**
3. `0 : Reset` 의 콜론이 표 파싱을 깨지 않는가 → 안 깨진다. 셀 구분자는 `|` 다.

R-S Latch with Enable, D Latch, D F/F, J-K Latch, J-K F/F 다섯 표(교안 p7~p11)를 `truth-table` kind, `encoding: 0/1`, `source: manual:pN` 으로 명세에 옮긴다.

- [ ] **Step 7: 스키마를 판정하고 `docs/schema/lab-spec-v1.md` 에 박제한다**

세 명세가 깨지지 않았으면 `lab-spec/v1` 을 확정한다. 이 문서가 Task 4 파서의 **계약**이 된다.

````markdown
# lab-spec/v1 — 실험 명세 스키마

Task 1 에서 실험1(truth-table)·실험10(capture + stepped)·실험6(심볼릭 토큰)
세 건으로 시험해 확정했다. `scripts/lab/spec_parser.py` 가 이 계약을 구현한다.

## 문서 프론트매터

| 필드 | 필수 | 값 |
|---|---|---|
| `schema` | ● | `lab-spec/v1` 고정 |
| `week` | ● | 정수 |
| `experiment` | ● | 정수 |
| `title` | ● | 문자열 |
| `source_manual` | ● | 교안 PDF 경로 |
| `power` | ● | `{VCC: ..., GND: ...}` — 결선도 템플릿 단자 라벨. 연도마다 달라서 명시한다 |
| `items` | ● | 항목 리스트 |

## 항목 (`items[]`)

| 필드 | 필수 | 값 |
|---|---|---|
| `id` | ● | `E<실험>.P<항목>` (예: `E1.P1-1`) |
| `title` | ● | 문자열 |
| `device` | ● | `LED` \| `7segment` \| `oscilloscope` \| `DMM` (복수 가능) |
| `ics` | ● | IC 이름 리스트. **교안 준비물 페이지를 따른다** |
| `tables` | ● | 이 항목이 쓰는 표 ID 리스트 (`[T1, T2]`) |

## 표 (`## T<n> · 제목` 아래 속성 리스트)

| 필드 | 필수 | 값 |
|---|---|---|
| `kind` | ● | `truth-table` \| `stepped` \| `capture` — **표 단위 속성이다** (실험10 이 근거) |
| `encoding` | `capture` 외 ● | `0/1` \| `H/L` — **표의 속성이다. 서로 변환하지 말 것** |
| `source` | ● | `manual:p11` \| `derived (Y = A·B·C)` \| `past-report:2020` |
| `expected` | `capture` 만 | 정성 서술 산문. 셀 표가 없는 표의 예상값이 여기 들어간다 |

`capture` 를 뺀 모든 표는 속성 리스트 뒤에 마크다운 표가 하나 온다.

## 셀 값 — 닫힌 enum 이 아니라 열린 토큰 (R3)

실증된 토큰:

```
0 1                       비트 (encoding: 0/1)
L H                       비트 (encoding: H/L)
X                         don't care
0->1  1->0                엣지
Q(t-1)  Q(t-1)'           이전 상태 / 그 보수
0 : Reset  1 : Set        비트 + 라벨 복합
Q(t-1)' : Toggle          보수 + 라벨 복합
Q=D  Q0  Z                메모리 상태 / Hi-Z
D0 D1 D2 D3               신호 이름
```

**정규화는 이것만:** `x`→`X`, `-`→`X`, don't-care 열의 빈칸→`X`, 앞뒤 공백 정리.
**`H/L` ↔ `0/1` 변환 금지.**

## 표기 (R5·R6) — 적용 범위가 핵심이다

- **보수:** 저작은 `'` 를 쓰고 **괄호로 스코프를 명시**한다. `(A·B)'` 는 `A·B` 위에,
  `A'` 는 `A` 위에 바가 온다. PDF 렌더 시 **부울식만** 오버바로 승격한다.
- **오버바 승격을 하지 않는 곳:** 표 헤더, 신호명, **그리고 셀 값.**
  실험6 의 `Q(t-1)'` 은 상태 토큰이지 부울식이 아니다. 이 구분을 어기면
  진리표 셀이 렌더링에서 망가진다.
- **active-low:** 맨 이름을 쓰고 **첫 등장에만 `(Active Low)`** 를 붙인다.
  실험9 만 교안 표기(`GWN`/`GRN`)를 그대로 쓴다.
- XOR 는 `⊕`, don't care 는 `X`.

## v1 에 없는 것 (의도적)

- `value_type` — `kind` 와 토큰 집합으로 흡수됐다
- `numeric` / `DMM` kind — 전 코퍼스 실측 수치가 2개뿐이라 폐기 (스펙 §개정 근거)
- 신뢰도 필드 — `source` 하나로 충분하다
- FPGA(13~15주차·텀프로젝트) — 산출물이 HDL·시뮬레이션 파형·핀 할당이라
  이 스키마로 확장하지 말고 별개 파이프라인으로 설계한다
````

- [ ] **Step 8: 커밋**

```bash
git add 2주차 6주차 12주차 docs/schema
git commit -m "feat: lab-spec/v1 스키마 확정 및 실험1·6·10 명세 작성"
```

---

### Task 2: `md.py` — 프론트매터·마크다운 표 원시 파서

이 모듈이 틀리면 나머지 전부가 틀린다. 먼저 만들고 먼저 고정한다.

**PyYAML 이 없으므로 자체 서브셋 파서를 쓴다.** 지원 범위는 이 프로젝트가 실제로 쓰는 것만이다 — 인라인 매핑/시퀀스, 블록 시퀀스, **시퀀스 안의 블록 매핑**(`items:` 가 쓰는 형태), 블록 스칼라(`capture` 표의 `expected`).

**Files:**
- Create: `scripts/lab/__init__.py`
- Create: `scripts/lab/md.py`
- Test: `tests/test_lab_md.py`

**Interfaces:**
- Consumes: 없음 (stdlib 만)
- Produces:
  - `MdTable` 데이터클래스 — `.header: list[str]`, `.rows: list[list[str]]`, `.line: int` (구분선의 1-based 줄 번호)
  - `split_frontmatter(text: str) -> tuple[dict, str]`
  - `parse_block(src: str) -> dict`
  - `parse_value(s: str) -> Any`
  - `split_top(s: str) -> list[str]`
  - `parse_tables(body: str) -> list[MdTable]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

Task 1 이 만든 **실제 명세 파일을 픽스처로 쓴다.** 합성 픽스처를 따로 만들지 않는다 — 실물이 파싱되지 않으면 파서가 틀린 것이다.

`tests/test_lab_md.py`:

```python
import unittest
from pathlib import Path

from scripts.lab import md

ROOT = Path(__file__).resolve().parents[1]


class TestFrontmatter(unittest.TestCase):
    def test_scalars_and_inline_mapping(self):
        fm, body = md.split_frontmatter(
            '---\nweek: 2\ntitle: Basic Gates\n'
            'power: {VCC: "+5V", GND: "GND"}\n---\n본문\n'
        )
        self.assertEqual(fm["week"], 2)
        self.assertEqual(fm["title"], "Basic Gates")
        self.assertEqual(fm["power"], {"VCC": "+5V", "GND": "GND"})
        self.assertEqual(body, "본문\n")

    def test_block_mapping_inside_sequence(self):
        """`items:` 가 쓰는 형태. 시퀀스 원소가 여러 줄짜리 매핑이다."""
        fm, _ = md.split_frontmatter(
            "---\nitems:\n"
            "  - id: E1.P1-1\n"
            "    title: 3-input AND\n"
            "    device: [LED]\n"
            "    tables: [T1, T2]\n"
            "  - id: E1.P2\n"
            "    title: 복합회로\n"
            "    device: [LED]\n"
            "    tables: [T5]\n---\n"
        )
        self.assertEqual(len(fm["items"]), 2)
        self.assertEqual(fm["items"][0]["id"], "E1.P1-1")
        self.assertEqual(fm["items"][0]["device"], ["LED"])
        self.assertEqual(fm["items"][0]["tables"], ["T1", "T2"])
        self.assertEqual(fm["items"][1]["title"], "복합회로")

    def test_tilde_is_none(self):
        fm, _ = md.split_frontmatter("---\nfilled_by: ~\n---\n")
        self.assertIsNone(fm["filled_by"])

    def test_null_literal_is_none(self):
        self.assertIsNone(md.parse_value("null"))
        self.assertIsNone(md.parse_value(""))

    def test_booleans(self):
        self.assertIs(md.parse_value("false"), False)
        self.assertIs(md.parse_value("true"), True)

    def test_block_scalar_joins_lines(self):
        """`capture` 표의 `expected` 산문."""
        got = md.parse_block(
            "kind: capture\nexpected: |\n  첫 줄\n  둘째 줄\n"
        )
        self.assertEqual(got["expected"], "첫 줄 둘째 줄")

    def test_unclosed_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            md.split_frontmatter("---\nweek: 2\n본문만 있고 닫는 구분자가 없다\n")

    def test_no_frontmatter_returns_empty(self):
        fm, body = md.split_frontmatter("# 제목\n본문\n")
        self.assertEqual(fm, {})
        self.assertEqual(body, "# 제목\n본문\n")


class TestSplitTop(unittest.TestCase):
    def test_respects_brackets_and_quotes(self):
        self.assertEqual(
            md.split_top('a: 1, b: [x, y], c: "p, q"'),
            ["a: 1", " b: [x, y]", ' c: "p, q"'],
        )


class TestTables(unittest.TestCase):
    def test_parses_header_and_rows(self):
        tables = md.parse_tables(
            "머리말\n\n| A | B | Y |\n|---|---|---|\n"
            "| 0 | 0 | 0 |\n| 1 | 1 | 1 |\n\n꼬리말\n"
        )
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].header, ["A", "B", "Y"])
        self.assertEqual(tables[0].rows, [["0", "0", "0"], ["1", "1", "1"]])
        self.assertEqual(tables[0].line, 4)   # 구분선의 1-based 줄 번호

    def test_ignores_pipe_free_prose(self):
        self.assertEqual(md.parse_tables("표가 하나도 없다\n"), [])

    def test_finds_multiple_tables(self):
        body = ("| A | Y |\n|---|---|\n| 0 | 1 |\n\n"
                "| S | R | Q |\n|---|---|---|\n| 0 | 1 | 0 |\n")
        self.assertEqual([len(t.header) for t in md.parse_tables(body)], [2, 3])

    def test_adjacent_tables_with_no_blank_line_between(self):
        """두 번째 표의 헤더를 첫 표의 행으로 삼키면 안 된다."""
        body = ("| A | Y |\n|---|---|\n| 0 | 1 |\n"
                "| S | R |\n|---|---|\n| 1 | 0 |\n")
        tables = md.parse_tables(body)
        self.assertEqual([t.header for t in tables], [["A", "Y"], ["S", "R"]])
        self.assertEqual([t.rows for t in tables], [[["0", "1"]], [["1", "0"]]])

    def test_dash_only_row_is_data_not_a_separator(self):
        """`-` 는 이 프로젝트의 don't-care 표기다. 구분선으로 오인하면
        데이터 행이 통째로 조용히 사라진다."""
        body = "| A | B |\n|---|---|\n| - | - |\n| 0 | 1 |\n"
        self.assertEqual(md.parse_tables(body)[0].rows, [["-", "-"], ["0", "1"]])

    def test_escaped_pipe_stays_inside_its_cell(self):
        """쪼개 버리면 validate 의 `\\|` 검사가 영영 발화하지 못한다."""
        body = "| A | B |\n|---|---|\n| a\\|b | c |\n"
        self.assertEqual(md.parse_tables(body)[0].rows, [["a\\|b", "c"]])

    def test_symbolic_cells_survive_untouched(self):
        """실험6 의 복합 토큰. 콜론·괄호·어포스트로피가 셀 안에서 살아남아야 한다."""
        body = ("| J | K | C | Q(t) |\n|---|---|---|------|\n"
                "| 1 | 1 | 1 | Q(t-1)' : Toggle |\n"
                "| x | x | 0 | Q(t-1) |\n")
        rows = md.parse_tables(body)[0].rows
        self.assertEqual(rows[0][3], "Q(t-1)' : Toggle")
        self.assertEqual(rows[1][3], "Q(t-1)")


class TestRealSpecFiles(unittest.TestCase):
    """Task 1 이 손으로 쓴 실물 명세가 그대로 파싱되어야 한다."""

    def test_week2_spec_parses(self):
        text = (ROOT / "2주차/체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["schema"], "lab-spec/v1")
        self.assertEqual(fm["week"], 2)
        self.assertEqual(fm["experiment"], 1)
        self.assertEqual(len(fm["items"]), 3)
        # 느슨한 하한은 회귀를 놓친다 — Task 1 픽스처의 실제 개수로 고정한다
        self.assertEqual(len(md.parse_tables(body)), 9)

    def test_week6_spec_parses(self):
        text = (ROOT / "6주차/체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["experiment"], 6)
        self.assertEqual(len(md.parse_tables(body)), 6)   # 표 5개 + 토큰 참조표 1개

    def test_week12_spec_parses(self):
        text = (ROOT / "12주차/체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["experiment"], 10)
        # T1 은 capture 라 셀 표가 없다. 본문의 마크다운 표는 T2(stepped) 하나뿐
        self.assertEqual(len(md.parse_tables(body)), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_md -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab'`

- [ ] **Step 3: `scripts/lab/__init__.py` 와 `scripts/lab/md.py` 를 만든다**

```bash
touch scripts/lab/__init__.py
```

`scripts/lab/md.py` — **아래 코드는 실제 명세 3종·보고서양식 블록·`expected` 블록 스칼라로 검증된 것이다. 그대로 쓴다:**

```python
"""마크다운 프론트매터·표 파싱 원시 함수. 표준 라이브러리만 쓴다.

PyYAML 이 이 환경에 없으므로 프론트매터는 이 프로젝트가 실제로 쓰는 부분집합만
직접 파싱한다:

    key: scalar
    key: {a: 1, b: "x"}      인라인 매핑
    key: [a, b]              인라인 시퀀스
    key:                     블록 시퀀스
      - scalar
      - {a: 1}
    key: |                   블록 스칼라 (여러 줄 산문)
      첫 줄
      둘째 줄
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MdTable:
    header: list
    rows: list
    line: int  # 구분선의 1-based 줄 번호


_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")   # `\|` 는 셀 구분자가 아니다


def split_top(s: str) -> list:
    """괄호·따옴표 안을 건드리지 않고 최상위 쉼표로만 자른다."""
    parts, buf, depth, quote = [], [], 0, ""
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def parse_value(s: str) -> Any:
    s = s.strip()
    if s in ("", "~", "null"):
        return None
    if s.startswith("{") and s.endswith("}"):
        out = {}
        for part in split_top(s[1:-1]):
            k, _, v = part.partition(":")
            out[k.strip()] = parse_value(v)
        return out
    if s.startswith("[") and s.endswith("]"):
        return [parse_value(p) for p in split_top(s[1:-1])]
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    low = s.lower()
    if low in ("true", "false"):
        return low == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _mapping(lines, i, indent):
    """indent 수준의 매핑을 읽는다. (dict, 다음 인덱스) 반환."""
    out = {}
    while i < len(lines) and _indent(lines[i]) == indent:
        line = lines[i]
        key, sep, rest = line.strip().partition(":")
        if not sep:
            raise ValueError(f"'키: 값' 형태가 아닙니다: {line.strip()!r}")
        key, rest = key.strip(), rest.strip()

        if rest == "|":                       # 블록 스칼라
            i += 1
            chunk = []
            while i < len(lines) and _indent(lines[i]) > indent:
                chunk.append(lines[i].strip())
                i += 1
            out[key] = " ".join(chunk)
        elif rest:
            out[key] = parse_value(rest)
            i += 1
        else:                                  # 중첩 블록
            i += 1
            if i < len(lines) and _indent(lines[i]) > indent:
                out[key], i = _block(lines, i, _indent(lines[i]))
            else:
                out[key] = None
    return out, i


def _sequence(lines, i, indent):
    """indent 수준의 `- ` 시퀀스를 읽는다. (list, 다음 인덱스) 반환."""
    out = []
    while (i < len(lines) and _indent(lines[i]) == indent
           and lines[i].lstrip().startswith("- ")):
        rest = lines[i].lstrip()[2:]
        i += 1
        child = [rest]
        while i < len(lines) and _indent(lines[i]) > indent:
            child.append(lines[i][indent + 2:])
            i += 1
        if len(child) == 1:
            out.append(parse_value(child[0]))
        else:                                  # 시퀀스 안의 블록 매핑
            value, _ = _mapping(child, 0, 0)
            out.append(value)
    return out, i


def _block(lines, i, indent):
    if lines[i].lstrip().startswith("- "):
        return _sequence(lines, i, indent)
    return _mapping(lines, i, indent)


def parse_block(src: str) -> dict:
    """들여쓰기 기반 미니 YAML 블록을 dict 로 읽는다."""
    lines = [ln for ln in src.split("\n")
             if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return {}
    value, _ = _mapping(lines, 0, _indent(lines[0]))
    return value


def split_frontmatter(text: str):
    """`---` 로 감싼 프론트매터를 (dict, 본문) 으로 가른다."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
    if not m:
        raise ValueError("프론트매터가 닫히지 않았습니다 (`---` 짝이 맞지 않음)")
    return parse_block(m.group(1)), text[m.end():]


def _cells(line: str) -> list:
    """셀로 자른다. `\\|` 는 구분자가 아니라 셀 안의 문자다.

    쪼개 버리면 `validate` 의 "셀에 escape 된 파이프" 검사가 영영 발화하지 못한다
    — 검사가 찾는 문자열이 파싱 단계에서 사라지기 때문이다.
    """
    return [c.strip() for c in _CELL_SPLIT.split(_ROW.match(line).group(1))]


def parse_tables(body: str) -> list:
    """본문에서 마크다운 표를 전부 찾는다.

    구분선은 **위치로만** 판정한다 — 헤더 바로 다음 줄이어야 한다. 내용으로
    판정하면 `| - | - |` 같은 don't-care 행이 구분선과 구별되지 않아 데이터가
    조용히 사라진다 (`-` 는 이 프로젝트의 don't-care 표기 중 하나다).
    """
    lines = body.split("\n")
    tables, i = [], 0
    while i < len(lines):
        if not (_ROW.match(lines[i]) and not _SEP.match(lines[i])
                and i + 1 < len(lines) and _SEP.match(lines[i + 1])):
            i += 1
            continue
        header = _cells(lines[i])
        sep_line = i + 2                      # 구분선의 1-based 줄 번호
        i += 2
        rows = []
        while i < len(lines) and _ROW.match(lines[i]):
            if i + 1 < len(lines) and _SEP.match(lines[i + 1]):
                break                         # 이 줄은 다음 표의 헤더다
            rows.append(_cells(lines[i]))
            i += 1
        tables.append(MdTable(header=header, rows=rows, line=sep_line))
    return tables
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_md -v
```

기대: `OK` (19 tests)

- [ ] **Step 5: 기존 테스트가 깨지지 않았는지 확인한다**

```bash
python3 -m unittest discover -s tests -t .
```

기대: `OK` — 기존 55개 + 신규 16개

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/__init__.py scripts/lab/md.py tests/test_lab_md.py
git commit -m "feat: 표준 라이브러리 전용 프론트매터·마크다운 표 파서 추가"
```

---

### Task 3: 설정 파일 + `config.py` + ⑦ `init-lab-week` + README 정정

양식을 스킬에 박지 않는 것이 R1 의 핵심이다. 이번 학기 양식이 미확정이고 89편 판독 결과 양식이 연도마다·학생마다 달랐기 때문이다. 설정 파일 둘과 그 로더를 여기서 만든다.

**Files:**
- Create: `.claude/과목정보.md`
- Create: `.claude/보고서양식.md`
- Create: `.claude/assets/Breadboard.jpg` (복사)
- Create: `scripts/lab/config.py`
- Create: `.claude/skills/init-lab-week/SKILL.md`
- Test: `tests/test_lab_config.py`
- Modify: `from_the_past/정리/README.md` (L18, L28)

**Interfaces:**
- Consumes: `scripts.lab.md.split_frontmatter`, `scripts.lab.md.parse_block`
- Produces:
  - `Section` 데이터클래스 — `.name: str`, `.repeat: str | None`, `.generate: bool`
  - `ReportFormat` 데이터클래스 — `.preset: str`, `.pre: list[Section]`, `.result: list[Section]`
  - `load_course_info(root: Path) -> dict`
  - `load_report_format(root: Path) -> ReportFormat`
  - `find_project_root(start: Path) -> Path` — `.claude/` 를 가진 가장 가까운 상위 디렉토리

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_config.py`:

```python
import unittest
from pathlib import Path

from scripts.lab import config

ROOT = Path(__file__).resolve().parents[1]


class TestCourseInfo(unittest.TestCase):
    def test_reads_required_fields(self):
        info = config.load_course_info(ROOT)
        self.assertEqual(info["course"], "논리회로실험")
        self.assertEqual(info["professor"], "허용석 교수님")
        self.assertEqual(info["class_section"], "C082")
        self.assertIn("chrome", info)

    def test_ai_usage_log_defaults_to_none(self):
        """표기 의무가 미확인이므로 자리만 비워둔다. 값이 없으면 로깅하지 않는다."""
        self.assertIsNone(config.load_course_info(ROOT)["ai_usage_log"])


class TestReportFormat(unittest.TestCase):
    def test_default_preset_is_intersection(self):
        fmt = config.load_report_format(ROOT)
        self.assertEqual(fmt.preset, "교집합")

    def test_intersection_pre_report_sections(self):
        fmt = config.load_report_format(ROOT)
        self.assertEqual(
            [s.name for s in fmt.pre],
            ["실험 목적", "실험 이론", "실험 부품",
             "실험 과정 및 예상 결과", "회로 결선도", "출처 및 참고문헌"],
        )

    def test_intersection_result_report_covers_grading_rubric(self):
        """평가기준.txt(권위 2순위)가 요구하는 결보 섹션이 전부 있어야 한다."""
        fmt = config.load_report_format(ROOT)
        names = [s.name for s in fmt.result]
        for required in ["실험 결과", "예비 비교", "결과 분석", "고찰"]:
            self.assertIn(required, names)

    def test_optional_sections_are_not_generated(self):
        fmt = config.load_report_format(ROOT)
        optional = [s for s in fmt.result if s.name == "추가 공부"]
        self.assertEqual(len(optional), 1)
        self.assertFalse(optional[0].generate)

    def test_repeat_per_item_flag_survives(self):
        """항목반복형은 결보 29편 중 14편의 실제 구조다 (R2)."""
        fmt = config.load_report_format(ROOT, preset="항목반복형")
        repeated = [s.name for s in fmt.result if s.repeat == "per-item"]
        self.assertIn("고찰", repeated)
        self.assertIn("결선도", repeated)
        self.assertNotIn("전체적인 고찰", repeated)

    def test_distributed_form_preset(self):
        """예비보고서 양식.pdf 의 목차 (권위 1순위, 2017~2019 실증)."""
        fmt = config.load_report_format(ROOT, preset="배포양식형")
        self.assertEqual(
            [s.name for s in fmt.pre],
            ["실험목적", "실험이론", "실험부품",
             "실험과정 및 예상결과", "출처 및 참고문헌"],
        )

    def test_unknown_preset_raises(self):
        with self.assertRaises(ValueError):
            config.load_report_format(ROOT, preset="없는프리셋")


class TestProjectRoot(unittest.TestCase):
    def test_walks_up_to_dotclaude(self):
        self.assertEqual(config.find_project_root(ROOT / "2주차" / "체크리스트"), ROOT)

    def test_raises_outside_project(self):
        with self.assertRaises(FileNotFoundError):
            config.find_project_root(Path("/"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_config -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.config'`

- [ ] **Step 3: `.claude/과목정보.md` 를 만든다**

분반은 강의계획서의 `C082`. 조 편성은 1주차에 나오므로 플레이스홀더로 두고 주석을 단다. `ai_usage_log` 는 **비워둔다** — 표기 의무가 미확인이고, 나중에 붙이는 것보다 자리를 지금 비워두는 것이 싸다.

```markdown
---
department: 전자공학과
course: 논리회로실험
course_code: ECE253
professor: 허용석 교수님
class_section: C082
semester: 2026-2
# 조 편성은 1주차에 확정된다. 확정되면 아래 세 줄을 채운다.
team: ~
student_ids: ~
student_names: ~
date_format: "%Y.%m.%d"
chrome: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
# AI 활용 내역 표기 의무 여부가 미확인이다 (강의계획서 §13).
# 조교/교수님 안내로 확정되면 로그 파일 경로를 여기 적는다.
# 값이 ~ 인 동안에는 어떤 스킬도 로그를 남기지 않는다.
ai_usage_log: ~
---

# 과목 정보

이 파일은 하네스 전체의 단일 메타데이터 소스다. 표지·보고서·체크리스트가
학부·과목·교수·분반·학번·성명을 전부 여기서 읽는다. **스킬에 하드코딩하지 말 것.**

## PDF 변환

macOS 의 Chrome 헤드리스를 쓴다. 위 `chrome` 경로가 이 머신의 실제 위치다.

    "$CHROME" --headless --disable-gpu --no-pdf-header-footer \
      --print-to-pdf="출력.pdf" "file:///절대경로/입력.html"

Chrome 은 정상 동작 중에도 macOS 에서 `task_policy_set ... invalid argument`
를 stderr 로 뱉는다. **종료 코드가 아니라 PDF 파일 생성 여부로 성공을 판정한다.**
```

- [ ] **Step 4: `.claude/보고서양식.md` 를 만든다**

프리셋 3종을 담고 `교집합` 으로 시작한다(R1). **교집합은 권위 1순위(`예비보고서 양식.pdf`)와 2순위(`실험보고서 평가기준.txt`)의 합집합이다** — 스펙 본문의 교집합 결보 목록은 평가기준이 요구하는 `예비 비교`·`결과 분석` 을 빠뜨렸으므로 여기서 바로잡는다.

```markdown
---
schema: report-format/v1
preset: 교집합
---

# 교집합

권위 1순위(`예비보고서 양식.pdf`)와 2순위(`실험보고서 평가기준.txt`)를 합친 것.
이번 학기 조교 안내가 오기 전까지의 기본값이다.

예비보고서:
  - {name: 실험 목적}
  - {name: 실험 이론}
  - {name: 실험 부품}
  - {name: 실험 과정 및 예상 결과}
  - {name: 회로 결선도}
  - {name: 출처 및 참고문헌}
결과보고서:
  - {name: 실험 결과}
  - {name: 예비 비교}
  - {name: 결과 분석}
  - {name: 고찰}
  - {name: 추가 공부, generate: false}
  - {name: 퀴즈문제에 대한 해설, generate: false}

# 배포양식형

`가이드라인_및_기준/예비보고서 양식.pdf` 의 목차 그대로.
1쪽이 IEEE 윤리, 2~6쪽이 섹션 제목만 있는 빈 페이지다.
2017·2018·2019 제출본이 실제로 따르는 형태다.

예비보고서:
  - {name: 실험목적}
  - {name: 실험이론}
  - {name: 실험부품}
  - {name: 실험과정 및 예상결과}
  - {name: 출처 및 참고문헌}
결과보고서:
  - {name: 실험 결과}
  - {name: 고찰}

# 항목반복형

결과보고서 29편 중 14편의 실제 구조. 번호가 없고 **고찰이 항목마다 반복된다**.
마지막에 종합 고찰이 한 번 더 온다 (R2).

예비보고서:
  - {name: 실험 목적}
  - {name: 실험 이론}
  - {name: 실험 부품}
  - {name: 실험 과정 및 예상 결과}
  - {name: 회로 결선도}
  - {name: 출처 및 참고문헌}
결과보고서:
  - {name: 결선도, repeat: per-item}
  - {name: 구성한 회로, repeat: per-item}
  - {name: 실험 결과, repeat: per-item}
  - {name: 고찰, repeat: per-item}
  - {name: 전체적인 고찰}
```

> **프리셋을 바꾸는 법:** 프론트매터의 `preset:` 한 줄만 고친다. 스킬 코드는 건드리지 않는다.

- [ ] **Step 5: `scripts/lab/config.py` 를 만든다**

```python
"""`.claude/` 아래 설정 파일 로더.

양식을 스킬에 하드코딩하지 않기 위한 모듈이다 (R1). 양식이 연도마다·학생마다
다르고 이번 학기 것이 미확정이므로, 섹션 목록은 반드시 여기를 거쳐 읽는다.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import md

COURSE_INFO = ".claude/과목정보.md"
REPORT_FORMAT = ".claude/보고서양식.md"


@dataclass
class Section:
    name: str
    repeat: Optional[str] = None   # None | "per-item"
    generate: bool = True


@dataclass
class ReportFormat:
    preset: str
    pre: list
    result: list


def find_project_root(start) -> Path:
    """`.claude/` 를 가진 가장 가까운 상위 디렉토리를 찾는다."""
    cur = Path(start).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".claude").is_dir():
            return candidate
    raise FileNotFoundError(
        f"{start} 위쪽에서 `.claude/` 를 찾지 못했습니다. "
        "논회실 프로젝트 안에서 실행하세요."
    )


def load_course_info(root) -> dict:
    text = (Path(root) / COURSE_INFO).read_text(encoding="utf-8")
    info, _ = md.split_frontmatter(text)
    for required in ("department", "course", "professor", "class_section"):
        if not info.get(required):
            raise ValueError(f"과목정보.md 에 {required} 가 없습니다")
    info.setdefault("ai_usage_log", None)
    return info


def _section_body(body: str, name: str):
    """`# name` 헤딩부터 다음 `# ` 헤딩 직전까지를 잘라낸다."""
    lines = body.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"# {name}":
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("# "):
            end = j
            break
    return "\n".join(lines[start:end])


def _sections(raw) -> list:
    out = []
    for entry in raw or []:
        if not isinstance(entry, dict) or "name" not in entry:
            raise ValueError(f"섹션 항목에 name 이 없습니다: {entry!r}")
        out.append(Section(
            name=entry["name"],
            repeat=entry.get("repeat"),
            generate=entry.get("generate", True),
        ))
    return out


def load_report_format(root, preset=None) -> ReportFormat:
    text = (Path(root) / REPORT_FORMAT).read_text(encoding="utf-8")
    front, body = md.split_frontmatter(text)
    preset = preset or front.get("preset")
    if not preset:
        raise ValueError("보고서양식.md 프론트매터에 preset 이 없습니다")

    block = _section_body(body, preset)
    if block is None:
        raise ValueError(
            f"보고서양식.md 에 '# {preset}' 프리셋이 없습니다. "
            "사용 가능: 교집합, 배포양식형, 항목반복형"
        )

    # 프리셋 본문에서 `예비보고서:` / `결과보고서:` 블록만 뽑는다.
    keep, capture = [], False
    for line in block.split("\n"):
        if line.startswith(("예비보고서:", "결과보고서:")):
            capture = True
        elif line.strip() and not line.startswith((" ", "\t")):
            capture = False
        if capture:
            keep.append(line)

    data = md.parse_block("\n".join(keep)) if keep else {}
    return ReportFormat(
        preset=preset,
        pre=_sections(data.get("예비보고서")),
        result=_sections(data.get("결과보고서")),
    )
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_config -v
```

기대: `OK` (10 tests)

- [ ] **Step 7: 브레드보드 템플릿을 복사한다**

**원본은 그대로 둔다.**

```bash
mkdir -p .claude/assets
cp "from_the_past/정리/강의노트/Breadboard.jpg" .claude/assets/Breadboard.jpg
```

- [ ] **Step 8: ⑦ `init-lab-week` 스킬을 만든다**

`.claude/skills/init-lab-week/SKILL.md`:

````markdown
---
name: init-lab-week
description: 논리회로실험 주차 폴더를 표준 7개 하위 폴더로 초기화한다. 사용자가 "5주차 폴더 만들어줘", "이번 주차 초기화", "주차 폴더 세팅" 등을 요청하거나 /init-lab-week 를 호출할 때 사용한다. 이미 있는 폴더는 건너뛰고 보고만 한다.
---

# init-lab-week

`<N>주차/` 아래에 하네스가 전제하는 7개 하위 폴더를 만든다.
다른 스킬은 전부 이 구조가 이미 있다고 가정하고, 없으면 거절한 뒤 이 스킬을 안내한다.

## 실행 절차

1. **주차 번호 추출.** 사용자 메시지에서 `N주차` 를 뽑는다. 못 찾으면 한 줄로 되묻고 중단.

2. **프로젝트 루트 확인.** `.claude/` 를 가진 가장 가까운 상위 디렉토리를 찾는다.
   못 찾으면 거절한다 — 이 스킬은 논회실 프로젝트 안에서만 동작한다.

3. **폴더 생성.** 이미 있으면 건드리지 않는다.

   ```bash
   mkdir -p "<루트>/<N>주차"/{강의노트,체크리스트,결선도,실험사진,퀴즈,STT,output}
   ```

4. **주차 ↔ 실험 매핑 안내.** 매핑이 1:1 이 아니다(3개가 회전한다).
   해당 주차의 실험 번호를 알려준다.

   | 주 | 실험 | 주 | 실험 |
   |---|---|---|---|
   | 2 | 실험1 | 9 | 실험7 |
   | 3 | 실험2 | 10 | 실험8 |
   | 4 | 실험3 | 11 | 실험9 |
   | **5** | **실험5** | 12 | 실험10 |
   | **6** | **실험6** | 13~15 | FPGA |
   | **7** | **실험4** | | |

   5·6·7주차가 실험 5·6·4 로 어긋나는 것이 이 표의 요점이다. 8주차는 mid-term.

5. **교안 복사 제안.** `from_the_past/정리/강의노트/실험N.pdf` 가 있으면
   `<N>주차/강의노트/` 로 복사할지 한 줄로 묻는다. 2026-2 교안이 배포되면
   그것으로 교체해야 한다는 점을 함께 알린다.

6. **결과 보고.** 만든 폴더와 건너뛴 폴더를 한 줄로 정리한다.

## 비-목표

- 명세.md 를 생성하지 않는다 (교안 판독이 필요한 사람의 일이다).
- 기존 파일을 덮어쓰지 않는다.
````

- [ ] **Step 9: `from_the_past/정리/README.md` 의 오류를 정정한다 (R9)**

89편 판독으로 두 가지가 사실이 아님이 확인됐다. 이 README 를 근거로 다른 세션이 다시 오판하는 것을 막는다.

L18 을 아래로 바꾼다:

```markdown
6. **`전학기_모범_실습보고서_camui20/`**: ⚠️ **다른 과목의 풀이 워크북이다.** 실험 12개·7400 계열이고 표지·목적·이론·고찰·참고문헌이 전무하다. 논회실 보고서의 구조·서술을 여기서 참조하지 말 것. 회로도와 진리표 정답을 대조하는 용도로만 쓴다 (총 22개 파일)
```

L28 을 아래로 바꾼다:

```markdown
9. **`가이드라인_및_기준/`**: `예비보고서 양식.pdf` 가 **유일하게 실증된 조교 배포 양식**이고(1쪽 IEEE 윤리 + 2~6쪽 빈 섹션, 2017~2019 제출본이 따름), `실험보고서 평가기준.txt` 는 2016년 조교 공지(예보 20점/결보 23점+가산 2점)다. ⚠️ 하위 `가이드라인/` 4종은 **조교 배포 문서가 아니라 한 학생의 개인 템플릿**이다 — 각 파일 1쪽에 그 학생의 학번·성명이 찍혀 있고, 코퍼스에서 그 표현을 쓰는 사람은 그 한 명뿐이다. 공식 문서로 취급하지 말 것. DE0-Nano 핀맵 포함
```

- [ ] **Step 10: 전체 테스트를 돌린다**

```bash
python3 -m unittest discover -s tests -t .
```

기대: `OK`

- [ ] **Step 11: 커밋**

```bash
git add .claude scripts/lab/config.py tests/test_lab_config.py from_the_past/정리/README.md
git commit -m "feat: 과목정보·보고서양식 설정과 로더, init-lab-week 스킬 추가"
```

---

### Task 4: `spec_parser.py` — 명세를 객체로

**Files:**
- Create: `scripts/lab/spec_parser.py`
- Test: `tests/test_lab_spec_parser.py`

**Interfaces:**
- Consumes: `scripts.lab.md.split_frontmatter`, `scripts.lab.md.parse_tables`
- Produces:
  - `SpecError(ValueError)`
  - `SpecTable` — `.id`, `.title`, `.kind`, `.encoding`, `.source`, `.expected`, `.role`, `.header`, `.rows`, `.line`
  - 상수 `ROLES = ("record", "reference")` — `reference` 는 교안에서 옮긴 참조표라 확인 칸을 만들지 않는다
  - `SpecItem` — `.id`, `.title`, `.device`, `.ics`, `.tables`
  - `LabSpec` — `.week`, `.experiment`, `.title`, `.source_manual`, `.power`, `.items`, `.tables`, `.path`, `.table(table_id) -> SpecTable | None`
  - `parse_spec(path) -> LabSpec`
  - `derived_parts(table) -> list[tuple[str, str]]` — 출력별 `(이름, 식)` 목록. 다중 출력(`derived (X = … ; Y = …)`)을 지원하고, `derived` 가 아니면 빈 리스트
  - `split_columns(table) -> tuple[list[str], list[str]]` — (입력 컬럼, 출력 컬럼). Task 6 의 행 수 검사와 Task 8 의 확인 칸 배치가 **둘 다 이것을 쓴다**
  - 상수 `KINDS = ("truth-table", "stepped", "capture")`, `ENCODINGS = ("0/1", "H/L")`

**역할 분담이 중요하다.** 파서는 **표현할 수 없는 것에만** 예외를 던진다(알 수 없는 kind, 표 누락, 없는 표를 가리키는 항목). `source` 누락·`encoding` 누락 같은 **의미** 결함은 Task 6 의 `validate.py` 가 findings 로 보고한다 — 반쯤 망가진 명세도 ⑤ 검증 스킬이 읽고 지적할 수 있어야 하기 때문이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_spec_parser.py`:

```python
import tempfile
import unittest
from pathlib import Path

from scripts.lab.spec_parser import (SpecError, derived_parts, parse_spec,
                                     split_columns)

ROOT = Path(__file__).resolve().parents[1]
WEEK2 = ROOT / "2주차/체크리스트/명세.md"
WEEK6 = ROOT / "6주차/체크리스트/명세.md"
WEEK12 = ROOT / "12주차/체크리스트/명세.md"


class TestWeek2(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(WEEK2)

    def test_frontmatter(self):
        self.assertEqual(self.spec.week, 2)
        self.assertEqual(self.spec.experiment, 1)
        self.assertEqual(self.spec.power["VCC"], "+5V")

    def test_three_items(self):
        self.assertEqual([i.id for i in self.spec.items],
                         ["E1.P1-1", "E1.P1-2", "E1.P2"])

    def test_ic_list_matches_manual_parts_page(self):
        """교안 p10 준비물이 근거다. 74HC08 은 quad AND 라 3-input 에 1개면 된다."""
        self.assertEqual(self.spec.items[0].ics, ["74HC08", "74HC32"])

    def test_three_input_truth_tables_are_eight_rows(self):
        for tid in ("T1", "T2", "T3", "T4"):
            with self.subTest(table=tid):
                self.assertEqual(len(self.spec.table(tid).rows), 8)
                self.assertEqual(self.spec.table(tid).kind, "truth-table")

    def test_composite_table_is_two_input(self):
        """교안 p13 은 3입력이 아니라 2입력이다 (Task 1 vision 판독으로 확정)."""
        self.assertEqual(len(self.spec.table("T5").rows), 4)

    def test_every_table_declares_source(self):
        for t in self.spec.tables:
            self.assertTrue(t.source, f"{t.id} 에 source 가 없다")

    def test_split_columns_finds_inputs_and_outputs(self):
        inputs, outputs = split_columns(self.spec.table("T1"))
        self.assertEqual(inputs, ["A", "B", "C"])
        self.assertEqual(outputs, ["Y"])

    def test_derived_parts_extracts_expression(self):
        self.assertEqual(derived_parts(self.spec.table("T1")), [("Y", "A·B·C")])

    def test_derived_parts_handles_multiple_outputs(self):
        """실험1 p13 복합회로는 입력 2개에 출력이 3개다."""
        pairs = derived_parts(self.spec.table("T5"))
        self.assertEqual([name for name, _ in pairs], ["X", "Y", "Z"])

    def test_theory_tables_are_reference_not_record(self):
        """T6~T9 는 교안 2입력 이론표다. 학생이 배선하지도 채우지도 않는다."""
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertEqual(self.spec.table(tid).role, "reference")
                self.assertEqual(self.spec.table(tid).encoding, "H/L")

    def test_procedure_tables_default_to_record(self):
        for tid in ("T1", "T2", "T3", "T4", "T5"):
            with self.subTest(table=tid):
                self.assertEqual(self.spec.table(tid).role, "record")

    def test_both_encodings_appear_in_the_real_fixture(self):
        """`H/L` ↔ `0/1` 변환 금지 규칙을 실물로 시험할 수 있어야 한다."""
        encodings = {t.encoding for t in self.spec.tables}
        self.assertEqual(encodings, {"0/1", "H/L"})

    def test_split_columns_on_a_multi_output_table(self):
        inputs, outputs = split_columns(self.spec.table("T5"))
        self.assertEqual(inputs, ["A", "B"])
        self.assertEqual(outputs, ["X", "Y", "Z"])


class TestWeek12CaptureAndStepped(unittest.TestCase):
    """kind 는 실험 단위가 아니라 표 단위 속성이다 (실험10 이 근거)."""

    def setUp(self):
        self.spec = parse_spec(WEEK12)

    def test_dac_is_capture_with_prose_expectation(self):
        t = self.spec.table("T1")
        self.assertEqual(t.kind, "capture")
        self.assertEqual(t.rows, [])
        self.assertIn("계단", t.expected)

    def test_adc_is_stepped_with_a_table(self):
        t = self.spec.table("T2")
        self.assertEqual(t.kind, "stepped")
        self.assertEqual(t.encoding, "0/1")
        self.assertGreater(len(t.rows), 0)


class TestWeek6SymbolicTokens(unittest.TestCase):
    """열린 토큰 모델(R3)이 심볼릭 값을 담는지."""

    def setUp(self):
        self.spec = parse_spec(WEEK6)

    def test_encoding_is_binary_not_hl(self):
        """실험6 교안은 0/1, 실험1 교안은 H/L. 섞지 않는다."""
        for t in self.spec.tables:
            self.assertEqual(t.encoding, "0/1")

    def test_composite_tokens_survive(self):
        cells = {c for t in self.spec.tables for row in t.rows for c in row}
        self.assertIn("Q(t-1)", cells)
        self.assertTrue(any(":" in c for c in cells),
                        "`0 : Reset` 같은 복합 토큰이 살아 있어야 한다")


class TestErrors(unittest.TestCase):
    """실물 명세를 한 군데씩 망가뜨려 파서가 거절하는지 본다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _broken(self, old, new):
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(
            WEEK12.read_text(encoding="utf-8").replace(old, new), encoding="utf-8"
        )
        return target

    def test_unknown_kind_raises(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken("kind: stepped", "kind: numeric"))
        self.assertIn("numeric", str(ctx.exception))

    def test_dangling_table_reference_raises(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(self._broken("tables: [T2]", "tables: [T7]"))
        self.assertIn("T7", str(ctx.exception))

    def test_wrong_schema_raises(self):
        with self.assertRaises(SpecError):
            parse_spec(self._broken("lab-spec/v1", "lab-spec/v0"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_spec_parser -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.spec_parser'`

- [ ] **Step 3: `scripts/lab/spec_parser.py` 를 만든다**

**아래 코드는 실험10 명세(capture + stepped 혼재)로 검증된 것이다:**

```python
"""`명세.md` → `LabSpec`. 필드 계약은 `docs/schema/lab-spec-v1.md` 가 정본이다.

이 파서는 **표현할 수 없는 것에만** 예외를 던진다 (알 수 없는 kind, 표 누락,
없는 표를 가리키는 항목). `source` 누락·`encoding` 누락 같은 의미 결함은
`validate.py` 가 findings 로 보고한다 — 반쯤 망가진 명세도 검토는 되어야 한다.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import md

KINDS = ("truth-table", "stepped", "capture")
ENCODINGS = ("0/1", "H/L")
ROLES = ("record", "reference")

_T_HEAD = re.compile(r"^##\s+(T\d+)\s*·\s*(.+?)\s*$", re.M)
_DERIVED = re.compile(r"^derived\s*\((.+)\)\s*$", re.S)
_ASSIGN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$", re.S)
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_ATTR = re.compile(r"^-\s+([a-z_]+)\s*:\s*(.*)$")


class SpecError(ValueError):
    """명세를 구조적으로 읽을 수 없을 때."""


@dataclass
class SpecTable:
    id: str
    title: str
    kind: str
    encoding: Optional[str]
    source: Optional[str]
    expected: Optional[str]
    role: str            # "record" | "reference"
    header: list
    rows: list
    line: int


@dataclass
class SpecItem:
    id: str
    title: str
    device: list
    ics: list
    tables: list


@dataclass
class LabSpec:
    week: int
    experiment: int
    title: str
    source_manual: str
    power: dict
    items: list
    tables: list
    path: Path

    def table(self, table_id):
        for t in self.tables:
            if t.id == table_id:
                return t
        return None


def _attrs(block: str) -> dict:
    """`- key: value` 속성 목록을 읽는다. 들여쓴 줄은 앞 값에 이어 붙인다."""
    out, key = {}, None
    for line in block.split("\n"):
        if line.lstrip().startswith("|"):
            break
        m = _ATTR.match(line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif key and line.startswith("  ") and line.strip():
            out[key] = (out[key] + " " + line.strip()).strip()
        elif not line.strip():
            key = None
    return out


def _parse_table(table_id, title, block, path) -> SpecTable:
    attrs = _attrs(block)
    kind = attrs.get("kind")
    if kind not in KINDS:
        raise SpecError(
            f"{path}: {table_id} 의 kind 가 {kind!r} 입니다. 허용: {', '.join(KINDS)}"
        )
    found = md.parse_tables(block)
    if kind == "capture":
        header, rows, line = [], [], 0
    else:
        if not found:
            raise SpecError(f"{path}: {table_id}({kind}) 에 마크다운 표가 없습니다")
        header, rows, line = found[0].header, found[0].rows, found[0].line
    return SpecTable(
        id=table_id, title=title, kind=kind,
        encoding=attrs.get("encoding"), source=attrs.get("source"),
        expected=attrs.get("expected"), role=attrs.get("role", "record"),
        header=header, rows=rows, line=line,
    )


def parse_spec(path) -> LabSpec:
    path = Path(path)
    front, body = md.split_frontmatter(path.read_text(encoding="utf-8"))
    if front.get("schema") != "lab-spec/v1":
        raise SpecError(
            f"{path}: schema 가 lab-spec/v1 이 아닙니다 ({front.get('schema')!r})"
        )
    for required in ("week", "experiment", "title", "source_manual", "power", "items"):
        if front.get(required) is None:
            raise SpecError(f"{path}: 프론트매터에 {required} 가 없습니다")

    heads = list(_T_HEAD.finditer(body))
    tables = []
    for n, m in enumerate(heads):
        end = heads[n + 1].start() if n + 1 < len(heads) else len(body)
        tables.append(_parse_table(m.group(1), m.group(2), body[m.end():end], path))

    known = {t.id for t in tables}
    items = []
    for raw in front["items"]:
        for required in ("id", "title", "device", "ics", "tables"):
            if raw.get(required) is None:
                raise SpecError(f"{path}: 항목 {raw.get('id')!r} 에 {required} 가 없습니다")
        missing = [t for t in raw["tables"] if t not in known]
        if missing:
            raise SpecError(
                f"{path}: 항목 {raw['id']} 가 없는 표 {missing} 를 가리킵니다. "
                f"정의된 표: {sorted(known)}"
            )
        items.append(SpecItem(id=raw["id"], title=raw["title"],
                              device=raw["device"], ics=raw["ics"], tables=raw["tables"]))

    return LabSpec(week=front["week"], experiment=front["experiment"],
                   title=front["title"], source_manual=front["source_manual"],
                   power=front["power"], items=items, tables=tables, path=path)


def derived_parts(table):
    """`source: derived (...)` 의 출력별 `(이름, 식)` 목록. 아니면 빈 리스트.

        derived (Y = A·B·C)                     -> [("Y", "A·B·C")]
        derived (X = A+B ; Y = A' ; Z = (A·B)') -> 쌍 3개

    한 표가 출력을 여럿 갖는 경우가 실재한다 (실험1 p13 복합회로).
    """
    m = _DERIVED.match((table.source or "").strip())
    if not m:
        return []
    pairs = []
    for chunk in m.group(1).split(";"):
        assign = _ASSIGN.match(chunk)
        if not assign:
            return []          # 형식이 깨졌다 — validate 가 findings 로 잡는다
        pairs.append((assign.group(1), assign.group(2)))
    return pairs


def split_columns(table):
    """표의 (입력 컬럼, 출력 컬럼).

    `derived` 식이 있으면 식이 참조하는 컬럼이 입력, 대입 대상이 출력이다.
    없으면 마지막 열 하나를 출력으로 본다 — 확인 칸을 어디에 둘지 정하는 데 쓴다.
    """
    pairs = derived_parts(table)
    if pairs:
        targets = [name for name, _ in pairs]
        referenced = set()
        for _, expr in pairs:
            referenced |= set(_NAME.findall(expr))
        inputs = [c for c in table.header if c in referenced and c not in targets]
        if inputs:
            outputs = [c for c in table.header if c in targets]
            return inputs, outputs or [c for c in table.header if c not in inputs]
    if len(table.header) < 2:
        return list(table.header), []
    return list(table.header[:-1]), [table.header[-1]]
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_spec_parser -v
```

기대: `OK` (21 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/spec_parser.py tests/test_lab_spec_parser.py
git commit -m "feat: 명세.md 파서 추가 (lab-spec/v1)"
```

---

### Task 5: `notation.py` — R3 정규화 · R5 보수 · R6 active-low

작은 모듈이지만 **적용 범위를 틀리면 진리표가 망가진다.** 오버바 승격은 부울식에만 쓰고 셀 값에는 쓰지 않는다 — 실험6 의 `Q(t-1)'` 은 상태 토큰이지 부울식이 아니다.

**Files:**
- Create: `scripts/lab/notation.py`
- Test: `tests/test_lab_notation.py`

**Interfaces:**
- Consumes: 없음 (stdlib 만)
- Produces:
  - `DONT_CARE = "X"`
  - `normalize_cell(value, dont_care_column=False) -> str`
  - `normalize_row(row, dont_care_columns=()) -> list[str]`
  - `to_overbar_html(expr: str) -> str` — `'` 를 `<span class="ov">…</span>` 로
  - `active_low(name: str, first_use: bool, experiment: int) -> str`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_notation.py`:

```python
import unittest

from scripts.lab import notation as n


class TestNormalizeCell(unittest.TestCase):
    def test_dont_care_variants_collapse_to_X(self):
        for raw in ("x", "X", "-", "–", "—"):
            with self.subTest(raw=raw):
                self.assertEqual(n.normalize_cell(raw), "X")

    def test_blank_becomes_X_only_in_dont_care_column(self):
        self.assertEqual(n.normalize_cell("", dont_care_column=True), "X")
        self.assertEqual(n.normalize_cell(""), "")

    def test_whitespace_is_collapsed(self):
        self.assertEqual(n.normalize_cell("  0  "), "0")
        self.assertEqual(n.normalize_cell("0  :   Reset"), "0 : Reset")

    def test_never_converts_between_encodings(self):
        """R3. encoding 은 표의 속성이다. H/L 을 0/1 로 바꾸면 안 된다."""
        self.assertEqual(n.normalize_cell("H"), "H")
        self.assertEqual(n.normalize_cell("L"), "L")
        self.assertEqual(n.normalize_row(["L", "H", "L"]), ["L", "H", "L"])

    def test_symbolic_tokens_pass_through(self):
        for raw in ("Q(t-1)", "Q(t-1)'", "0 : Reset", "0->1", "Q=D", "Z", "D0"):
            with self.subTest(raw=raw):
                self.assertEqual(n.normalize_cell(raw), raw)


class TestOverbar(unittest.TestCase):
    def test_parenthesised_scope_promotes_whole_group(self):
        self.assertEqual(n.to_overbar_html("(A·B·C)'"),
                         '<span class="ov">A·B·C</span>')

    def test_bare_variable_promotes_only_itself(self):
        self.assertEqual(n.to_overbar_html("A·B'+C"),
                         'A·<span class="ov">B</span>+C')

    def test_expression_without_prime_is_untouched(self):
        self.assertEqual(n.to_overbar_html("A⊕B"), "A⊕B")

    def test_state_token_would_be_promoted_so_never_call_it_on_cells(self):
        """`Q(t-1)'` 은 문법적으로 승격 대상이다. 그래서 셀에는 부르지 않는다.

        이 테스트는 규칙을 문서화하려고 존재한다 — 함수가 아니라 호출부가
        범위를 지켜야 한다.
        """
        self.assertEqual(n.to_overbar_html("Q(t-1)'"),
                         '<span class="ov">Q(t-1)</span>')
        self.assertEqual(n.normalize_cell("Q(t-1)'"), "Q(t-1)'")


class TestActiveLow(unittest.TestCase):
    def test_marks_only_first_use(self):
        self.assertEqual(n.active_low("RESET", True, 1), "RESET (Active Low)")
        self.assertEqual(n.active_low("RESET", False, 1), "RESET")

    def test_experiment_9_follows_the_manual(self):
        self.assertEqual(n.active_low("GWN", True, 9), "GWN")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_notation -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.notation'`

- [ ] **Step 3: `scripts/lab/notation.py` 를 만든다**

```python
"""표기 규칙 (R3 정규화 · R5 보수 · R6 active-low).

**적용 범위가 이 모듈의 핵심이다.** `to_overbar_html` 은 부울식에만 쓴다.
표 헤더·신호명·**셀 값**에는 쓰지 않는다 — 실험6 의 `Q(t-1)'` 은 상태 토큰이지
부울식이 아니라서, 오버바로 승격하면 진리표가 망가진다.
"""

import re

DONT_CARE = "X"
_DC_TOKENS = ("x", "X", "-", "–", "—")

# `(A·B)'` 또는 `A'` 또는 `Q(t-1)'` — 괄호로 스코프가 명시된 것만 잡는다 (R5).
_PRIMED = re.compile(r"(\([^()]*\)|[A-Za-z][A-Za-z0-9_]*(?:\([^()]*\))?)'")


def normalize_cell(value, dont_care_column=False) -> str:
    """R3 정규화. don't-care 변형과 공백만 손댄다.

    **`H/L` ↔ `0/1` 변환은 절대 하지 않는다.** encoding 은 표의 속성이다.
    """
    s = " ".join(str(value).split())
    if s in _DC_TOKENS:
        return DONT_CARE
    if s == "" and dont_care_column:
        return DONT_CARE
    return s


def normalize_row(row, dont_care_columns=()) -> list:
    return [normalize_cell(v, i in dont_care_columns) for i, v in enumerate(row)]


def to_overbar_html(expr: str) -> str:
    """부울식의 `'` 를 오버바로 승격한다 (R5). **부울식에만 쓸 것.**"""
    def repl(m):
        inner = m.group(1)
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1]
        return f'<span class="ov">{inner}</span>'
    return _PRIMED.sub(repl, expr)


def active_low(name: str, first_use: bool, experiment: int) -> str:
    """R6. 맨 이름 + 첫 등장에만 `(Active Low)`. 실험9 만 교안 표기를 따른다."""
    if experiment == 9:
        return name
    return f"{name} (Active Low)" if first_use else name
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_notation -v
```

기대: `OK` (11 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/notation.py tests/test_lab_notation.py
git commit -m "feat: 표기 정규화·보수 오버바·active-low 모듈 추가"
```

---

### Task 6: `boolexpr.py` + `validate.py` + ⑤ `review-lab-report`

이 Task 가 하네스에서 가장 값이 큰 부분이다. **부울식 역검산**이 손으로 도출한 8행 진리표의 오류를 실험실에 들어가기 전에 잡아낸다.

**Files:**
- Create: `scripts/lab/boolexpr.py`
- Create: `scripts/lab/validate.py`
- Create: `.claude/skills/review-lab-report/SKILL.md`
- Test: `tests/test_lab_boolexpr.py`
- Test: `tests/test_lab_validate.py`

**Interfaces:**
- Consumes: `scripts.lab.md`, `scripts.lab.notation.normalize_cell`, `scripts.lab.notation.DONT_CARE`, `scripts.lab.spec_parser.{LabSpec, derived_parts, split_columns}`, `scripts.lab.config.Section`
- Produces:
  - `boolexpr.eval_boolean(text: str, env: dict[str, int]) -> int`
  - `Finding` — `.level` (`"error"` \| `"warn"`), `.where`, `.message`, `__str__`
  - `check_table_integrity(spec) -> list[Finding]`
  - `check_metadata(spec) -> list[Finding]`
  - `check_row_count(spec) -> list[Finding]`
  - `check_boolean(spec) -> list[Finding]`
  - `validate_spec(spec) -> list[Finding]` — 위 넷을 합친 것
  - `check_netlist(netlist_path, spec) -> list[Finding]`
  - `check_report_sections(report_path, sections: list[Section]) -> list[Finding]`

**설계 규칙:** 이 모듈은 **절대 예외를 던지지 않는다.** 검토는 반쯤 망가진 문서에도 동작해야 하기 때문이다. 모든 문제는 `Finding` 으로 나온다.

- [ ] **Step 1: `boolexpr` 의 실패하는 테스트를 쓴다**

`eval` 을 쓰지 않는다. 연산자 우선순위를 문자열 치환으로 흉내내면 `A⊕B·C` 에서 조용히 틀린다(Python 의 `^` 는 `and` 보다 우선순위가 높다). 재귀 하강 파서로 간다.

`tests/test_lab_boolexpr.py`:

```python
import itertools
import unittest

from scripts.lab.boolexpr import eval_boolean


def truth_column(expr, names):
    return [eval_boolean(expr, dict(zip(names, bits)))
            for bits in itertools.product([0, 1], repeat=len(names))]


class TestOperators(unittest.TestCase):
    def test_and_or_over_three_inputs(self):
        self.assertEqual(truth_column("A·B·C", "ABC"), [0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(truth_column("A+B+C", "ABC"), [0, 1, 1, 1, 1, 1, 1, 1])

    def test_complement_of_a_group(self):
        self.assertEqual(truth_column("(A·B·C)'", "ABC"), [1, 1, 1, 1, 1, 1, 1, 0])
        self.assertEqual(truth_column("(A+B+C)'", "ABC"), [1, 0, 0, 0, 0, 0, 0, 0])

    def test_xor(self):
        self.assertEqual(truth_column("A⊕B", "AB"), [0, 1, 1, 0])


class TestPrecedence(unittest.TestCase):
    """문자열 치환 + eval 로는 여기서 조용히 틀린다."""

    def test_and_binds_tighter_than_or(self):
        self.assertEqual(truth_column("A+B·C", "ABC"), [0, 0, 0, 1, 1, 1, 1, 1])

    def test_and_binds_tighter_than_xor(self):
        self.assertEqual(truth_column("A⊕B·C", "ABC"), [0, 0, 0, 1, 1, 1, 1, 0])

    def test_de_morgan_identity(self):
        self.assertEqual(truth_column("(A·B)'", "AB"), truth_column("A'+B'", "AB"))
        self.assertEqual(truth_column("(A+B)'", "AB"), truth_column("A'·B'", "AB"))


class TestErrors(unittest.TestCase):
    def test_unknown_variable(self):
        with self.assertRaises(ValueError) as ctx:
            eval_boolean("A·D", {"A": 1, "B": 0})
        self.assertIn("D", str(ctx.exception))

    def test_truncated_expression(self):
        with self.assertRaises(ValueError):
            eval_boolean("A·", {"A": 1})

    def test_unbalanced_parenthesis(self):
        with self.assertRaises(ValueError):
            eval_boolean("A)B", {"A": 1, "B": 1})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_boolexpr -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.boolexpr'`

- [ ] **Step 3: `scripts/lab/boolexpr.py` 를 만든다**

**아래 코드는 드모르간 항등과 `A⊕B·C` 우선순위로 검증된 것이다:**

```python
import re

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]*|[()'+·⊕]")


class _Parser:
    """재귀 하강. 우선순위 낮음 → 높음:

        expr   := xor ( '+' xor )*
        xor    := term ( '⊕' term )*
        term   := factor ( '·' factor )*
        factor := atom "'"*
        atom   := NAME | '(' expr ')'
    """

    def __init__(self, text, env):
        self.toks = _TOKEN.findall(text)
        self.i = 0
        self.env = env

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, expect=None):
        cur = self.peek()
        if expect is not None and cur != expect:
            raise ValueError(f"{expect!r} 를 기대했지만 {cur!r} 를 만났습니다")
        self.i += 1
        return cur

    def expr(self):
        v = self.xor()
        while self.peek() == "+":
            self.eat()
            v |= self.xor()
        return v

    def xor(self):
        v = self.term()
        while self.peek() == "⊕":
            self.eat()
            v ^= self.term()
        return v

    def term(self):
        v = self.factor()
        while self.peek() == "·":
            self.eat()
            v &= self.factor()
        return v

    def factor(self):
        v = self.atom()
        while self.peek() == "'":
            self.eat()
            v = 1 - v
        return v

    def atom(self):
        tok = self.eat()
        if tok == "(":
            v = self.expr()
            self.eat(")")
            return v
        if tok is None or not tok[0].isalpha():
            raise ValueError(f"예상치 못한 토큰: {tok!r}")
        if tok not in self.env:
            raise ValueError(f"입력 변수 {tok!r} 이(가) 표에 없습니다")
        return 1 if self.env[tok] else 0


def eval_boolean(text, env):
    p = _Parser(text, env)
    v = p.expr()
    if p.peek() is not None:
        raise ValueError(f"식 끝에 남은 토큰: {p.peek()!r}")
    return v
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_boolexpr -v
```

기대: `OK` (10 tests)

- [ ] **Step 5: `validate` 의 실패하는 테스트를 쓴다**

핵심은 **일부러 틀린 표를 잡아내는 것**이다. 통과만 시키는 테스트는 검증기의 값을 증명하지 못한다.

`tests/test_lab_validate.py`:

```python
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config, validate
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
WEEK2_SPEC = ROOT / "2주차/체크리스트/명세.md"
WEEK2_NETLIST = ROOT / "2주차/결선도/netlist.md"


def spec_from(text):
    tmp = tempfile.mkdtemp()
    path = Path(tmp) / "명세.md"
    path.write_text(text, encoding="utf-8")
    return parse_spec(path)


HEAD = """---
schema: lab-spec/v1
week: 2
experiment: 1
title: Basic Gates
source_manual: from_the_past/정리/강의노트/실험1.pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E1.P1-1
    title: 3-input AND
    device: [LED]
    ics: ["74HC08"]
    tables: [T1]
---

## T1 · 3-input AND 진리표

"""


class TestRealWeek2SpecIsClean(unittest.TestCase):
    def test_no_errors(self):
        findings = validate.validate_spec(parse_spec(WEEK2_SPEC))
        errors = [f for f in findings if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))


class TestBooleanCrosscheck(unittest.TestCase):
    def test_catches_a_wrong_output_bit(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A·B·C)\n\n"
            "| A | B | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 0 | 0 | 1 | 0 |\n"
            "| 0 | 1 | 0 | 0 |\n| 0 | 1 | 1 | 0 |\n"
            "| 1 | 0 | 0 | 0 |\n| 1 | 0 | 1 | 0 |\n"
            "| 1 | 1 | 0 | 1 |\n| 1 | 1 | 1 | 1 |\n"   # 7행이 틀렸다
        ))
        errors = [f for f in validate.check_boolean(spec) if f.level == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("행7", errors[0].where)

    def test_accepts_a_correct_table(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A+B+C)\n\n"
            "| A | B | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 0 | 0 | 1 | 1 |\n"
            "| 0 | 1 | 0 | 1 |\n| 0 | 1 | 1 | 1 |\n"
            "| 1 | 0 | 0 | 1 |\n| 1 | 0 | 1 | 1 |\n"
            "| 1 | 1 | 0 | 1 |\n| 1 | 1 | 1 | 1 |\n"
        ))
        self.assertEqual(validate.check_boolean(spec), [])

    def test_crosschecks_every_output_of_a_multi_output_table(self):
        """실험1 p13 은 출력이 3개다. 하나만 검산하고 넘어가면 안 된다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (X = A+B ; Y = A·B)\n\n"
            "| A | B | X | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 0 | 1 | 1 | 0 |\n"
            "| 1 | 0 | 1 | 0 |\n| 1 | 1 | 1 | 0 |\n"   # Y 마지막 행이 틀렸다
        ))
        errors = [f for f in validate.check_boolean(spec) if f.level == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("Y", errors[0].message)

    def test_works_on_hl_encoded_tables(self):
        """평가용으로만 비트로 읽는다. 데이터는 H/L 그대로 남는다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: H/L\n"
            "- source: derived (Y = A·B)\n\n"
            "| A | B | Y |\n|---|---|---|\n"
            "| L | L | L |\n| L | H | L |\n"
            "| H | L | L |\n| H | H | H |\n"
        ))
        self.assertEqual(validate.check_boolean(spec), [])
        self.assertEqual(spec.table("T1").rows[0], ["L", "L", "L"])


class TestRowCount(unittest.TestCase):
    def test_warns_when_rows_are_not_two_to_the_n(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = A·B·C)\n\n"
            "| A | B | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 0 | 0 |\n| 1 | 1 | 1 | 1 |\n"
        ))
        warns = validate.check_row_count(spec)
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].level, "warn")

    def test_skips_tables_that_use_dont_care(self):
        """실험6 R-S Latch 는 3입력인데 `x x 0` 축약으로 5행이다. 정상이다."""
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n"
            "- source: derived (Y = S·R·C)\n\n"
            "| S | R | C | Y |\n|---|---|---|---|\n"
            "| 0 | 0 | 1 | 0 |\n| x | x | 0 | 0 |\n"
        ))
        self.assertEqual(validate.check_row_count(spec), [])


class TestMetadata(unittest.TestCase):
    def test_missing_source_is_an_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("source" in f.message
                            for f in validate.check_metadata(spec)))

    def test_missing_encoding_is_an_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- source: manual:p4\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("encoding" in f.message
                            for f in validate.check_metadata(spec)))

    def test_capture_needs_expected_prose_not_encoding(self):
        spec = spec_from(HEAD + "- kind: capture\n- source: manual:p11\n")
        messages = [f.message for f in validate.check_metadata(spec)]
        self.assertTrue(any("expected" in m for m in messages))
        self.assertFalse(any("encoding" in m for m in messages))


class TestTableIntegrity(unittest.TestCase):
    def test_ragged_row_is_an_error(self):
        spec = spec_from(HEAD + (
            "- kind: truth-table\n- encoding: 0/1\n- source: manual:p4\n\n"
            "| A | B | Y |\n|---|---|---|\n| 0 | 0 |\n"
        ))
        self.assertTrue(any("헤더" in f.message
                            for f in validate.check_table_integrity(spec)))


class TestNetlist(unittest.TestCase):
    def test_real_week2_netlist_has_power_and_floating_pins(self):
        spec = parse_spec(WEEK2_SPEC)
        errors = [f for f in validate.check_netlist(WEEK2_NETLIST, spec)
                  if f.level == "error"]
        self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

    def test_missing_file_is_an_error(self):
        spec = parse_spec(WEEK2_SPEC)
        findings = validate.check_netlist(ROOT / "없는파일.md", spec)
        self.assertEqual(findings[0].level, "error")


class TestReportSections(unittest.TestCase):
    def test_missing_section_from_the_format_file(self):
        fmt = config.load_report_format(ROOT)
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 실험 목적\n내용\n# 실험 이론\n내용\n", encoding="utf-8")
        missing = [f.message for f in validate.check_report_sections(tmp, fmt.pre)]
        self.assertTrue(any("실험 부품" in m for m in missing))

    def test_optional_sections_are_not_required(self):
        fmt = config.load_report_format(ROOT)
        tmp = Path(tempfile.mkdtemp()) / "보고서.md"
        tmp.write_text("# 실험 결과\n# 예비 비교\n# 결과 분석\n# 고찰\n",
                       encoding="utf-8")
        findings = validate.check_report_sections(tmp, fmt.result)
        self.assertTrue(all("추가 공부" not in f.message for f in findings))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_validate -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.validate'`

- [ ] **Step 7: `scripts/lab/validate.py` 를 만든다**

**아래 코드는 일부러 틀린 3-input OR 표에 심어둔 결함 3개(encoding 누락·행 수 부족·비트 오류)를 전부 잡아내는 것으로 검증됐다:**

```python
"""명세·결선도·보고서 검증. 예외를 던지지 않고 `Finding` 목록을 돌려준다.

⑤ `review-lab-report` 스킬이 이 모듈을 부른다. 검토는 반쯤 망가진 문서에도
동작해야 하므로, 여기서는 절대 예외로 중단하지 않는다.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import md
from .boolexpr import eval_boolean
from .notation import DONT_CARE, normalize_cell
from .spec_parser import derived_parts, split_columns

_BAD_CELL = {"\\|": "escape 된 파이프", "<br>": "<br> 태그", "\t": "탭 문자"}


@dataclass
class Finding:
    level: str   # "error" | "warn"
    where: str
    message: str

    def __str__(self):
        mark = "✗" if self.level == "error" else "!"
        return f"{mark} {self.where} — {self.message}"


def _bit(cell, encoding):
    """평가용 비트로 읽는다. **데이터를 바꾸지 않는다** — 검산 중에만 쓴다."""
    c = normalize_cell(cell)
    if encoding == "H/L":
        return {"L": 0, "H": 1}.get(c)
    return {"0": 0, "1": 1}.get(c)


def check_table_integrity(spec) -> list:
    out = []
    for t in spec.tables:
        width = len(t.header)
        for i, row in enumerate(t.rows, start=1):
            where = f"{spec.path.name}:{t.id} 행{i}"
            if len(row) != width:
                out.append(Finding("error", where,
                    f"셀이 {len(row)}개인데 헤더는 {width}개다"))
            for cell in row:
                for bad, label in _BAD_CELL.items():
                    if bad in cell:
                        out.append(Finding("error", where, f"셀에 {label}가 있다: {cell!r}"))
    return out


def check_metadata(spec) -> list:
    out = []
    for t in spec.tables:
        where = f"{spec.path.name}:{t.id}"
        if not t.source:
            out.append(Finding("error", where, "source 가 없다 (예상값 출처는 항상 명시한다)"))
        if t.role not in ("record", "reference"):
            out.append(Finding("error", where,
                f"role 이 {t.role!r} 이다. `record` 또는 `reference` 여야 한다"))
        if t.kind == "capture":
            if not t.expected:
                out.append(Finding("error", where,
                    "capture 표에 expected 산문이 없다 (예상값을 적을 곳이 여기다)"))
        elif t.encoding not in ("0/1", "H/L"):
            out.append(Finding("error", where,
                f"encoding 이 {t.encoding!r} 이다. `0/1` 또는 `H/L` 을 선언해야 한다"))
    return out


def check_row_count(spec) -> list:
    """진리표 행 수 ↔ 입력 비트 수. `X` 가 있으면 축약된 표이므로 건너뛴다."""
    out = []
    for t in spec.tables:
        if t.kind != "truth-table" or not t.rows:
            continue
        if any(normalize_cell(c) == DONT_CARE for row in t.rows for c in row):
            continue
        if not derived_parts(t):
            continue
        inputs, _ = split_columns(t)
        expected = 2 ** len(inputs)
        if len(t.rows) != expected:
            out.append(Finding("warn", f"{spec.path.name}:{t.id}",
                f"입력 {len(inputs)}비트({', '.join(inputs)})면 {expected}행이어야 하는데 "
                f"{len(t.rows)}행이다"))
    return out


def check_boolean(spec) -> list:
    """`derived (...)` 로 선언된 표를 식으로 되짚는다. 출력이 여럿이면 전부."""
    out = []
    for t in spec.tables:
        pairs = derived_parts(t)
        if not pairs or not t.rows:
            continue
        where = f"{spec.path.name}:{t.id}"
        for target, expr in pairs:
            if target not in t.header:
                out.append(Finding("error", where,
                    f"source 의 출력 {target!r} 이 표 헤더에 없다: {t.header}"))
                continue
            out_col = t.header.index(target)
            for i, row in enumerate(t.rows, start=1):
                if len(row) != len(t.header):
                    continue
                env = {}
                for col, cell in zip(t.header, row):
                    bit = _bit(cell, t.encoding)
                    if bit is not None:
                        env[col] = bit
                got = _bit(row[out_col], t.encoding)
                if got is None:
                    continue
                try:
                    want = eval_boolean(expr, env)
                except ValueError as exc:
                    out.append(Finding("error", where,
                        f"{target} 의 식 {expr!r} 을 평가할 수 없다: {exc}"))
                    break
                if got != want:
                    inputs, _ = split_columns(t)
                    shown = ", ".join(f"{c}={row[t.header.index(c)]}" for c in inputs)
                    out.append(Finding("error", f"{where} 행{i}",
                        f"{shown} 일 때 {target} = {expr} = {want} 인데 "
                        f"표에는 {row[out_col]!r} 이다"))
    return out


def validate_spec(spec) -> list:
    return (check_table_integrity(spec) + check_metadata(spec)
            + check_row_count(spec) + check_boolean(spec))


def check_netlist(netlist_path, spec) -> list:
    """플로팅 입력은 이 과목의 대표 실패 원인이다. 누락을 error 로 잡는다."""
    path = Path(netlist_path)
    if not path.exists():
        return [Finding("error", str(netlist_path), "결선도 netlist 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    out = []
    for token, label in (("VCC", "VCC 연결"), ("GND", "GND 연결"),
                         ("미사용", "미사용 입력핀 처리")):
        if token not in text:
            out.append(Finding("error", path.name, f"{label} 언급이 통째로 없다"))
    for item in spec.items:
        for ic in item.ics:
            if ic not in text:
                out.append(Finding("warn", path.name,
                    f"항목 {item.id} 의 IC {ic} 가 netlist 에 없다"))
    return out


def check_report_sections(report_path, sections) -> list:
    """`.claude/보고서양식.md` 기준으로 섹션 유무·순서를 본다.

    하드코딩된 목차와 대조하지 않는다 — 양식이 연도마다 다르기 때문이다 (R1).
    """
    path = Path(report_path)
    if not path.exists():
        return [Finding("error", str(report_path), "보고서 파일이 없다")]
    text = path.read_text(encoding="utf-8")
    headings = [re.sub(r"^#+\s*(?:\d+[.)]\s*)?", "", ln).strip()
                for ln in text.split("\n") if ln.startswith("#")]
    out, last = [], -1
    for sec in sections:
        if not sec.generate:
            continue
        pos = next((i for i, h in enumerate(headings) if sec.name in h), None)
        if pos is None:
            out.append(Finding("error", path.name, f"양식이 요구하는 섹션 '{sec.name}' 이 없다"))
            continue
        if pos < last:
            out.append(Finding("warn", path.name,
                f"섹션 '{sec.name}' 의 순서가 양식과 다르다"))
        last = max(last, pos)
    return out
```

- [ ] **Step 8: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_validate -v
```

기대: `OK` (15 tests)

만약 `TestRealWeek2SpecIsClean` 이 실패하면 **검증기가 아니라 Task 1 의 명세가 틀린 것이다.** 명세를 고친다 — 그게 이 검증기의 존재 이유다.

- [ ] **Step 9: ⑤ `review-lab-report` 스킬을 만든다**

`.claude/skills/review-lab-report/SKILL.md`:

````markdown
---
name: review-lab-report
description: 논리회로실험 명세·결선도·예비보고서·결과보고서를 검증하고 라운드별 리뷰 문서를 남긴다. 사용자가 "2주차 예비보고서 검토", "명세 검증해줘", "보고서 리뷰", "결과보고서 확인해줘" 등을 요청하거나 /review-lab-report 를 호출할 때 사용한다. 진리표 부울식 역검산, 행 수 대조, source·encoding 누락, netlist 의 VCC/GND/미사용핀 누락, 그리고 `.claude/보고서양식.md` 기준 섹션 대조를 수행한다.
---

# review-lab-report

`scripts/lab/validate.py` 를 불러 검증하고, 결과를 라운드 문서로 남긴다.
**이 스킬은 판단을 새로 만들지 않는다** — 검사 규칙은 전부 코드에 있고 테스트로 고정돼 있다.

## 인자

`<N주차> [pre|result] [round<N>]`

- 주차 토큰이 없으면 한 줄로 되묻고 중단한다.
- `pre`/`result` 가 없으면 `<N>주차/output/` 을 보고 추론한다. 둘 다 있으면 되묻는다.
- `round<N>` 이 없으면 기존 `*_review_round*.md` 중 최대 번호 + 1 을 쓴다.

## 실행 절차

1. **주차 폴더 확인.** `<N>주차/` 가 없으면 **거절하고** `init-lab-week` 를 안내한다.
   폴더를 만들어 주지 않는다.

2. **명세·결선도 검증.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.spec_parser import parse_spec, SpecError
   from scripts.lab import validate
   try:
       spec = parse_spec('<N>주차/체크리스트/명세.md')
   except SpecError as e:
       print('SPEC-ERROR:', e); raise SystemExit(1)
   for f in validate.validate_spec(spec):
       print(f)
   for f in validate.check_netlist('<N>주차/결선도/netlist.md', spec):
       print(f)
   "
   ```

   `SpecError` 가 나오면 그것을 **첫 번째 finding 으로 보고하고** 나머지 검사는 건너뛴다.

3. **보고서 섹션 대조.** **반드시 `.claude/보고서양식.md` 를 기준으로 한다.**
   목차를 스킬에 하드코딩하지 않는다 — 양식은 연도마다·학생마다 다르고
   이번 학기 것이 미확정이다 (R1).

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, validate
   root = config.find_project_root(Path('.'))
   fmt = config.load_report_format(root)
   sections = fmt.pre if '<pre|result>' == 'pre' else fmt.result
   for f in validate.check_report_sections('<보고서 경로>', sections):
       print(f)
   "
   ```

4. **코드가 못 보는 것을 사람이 본다.** 아래는 판정하지 말고 **질문으로** 남긴다.

   | 항목 | 왜 코드로 못 하나 |
   |---|---|
   | 고찰이 본인 경험인가 | 배운 점은 학생 것이다. 지어내면 안 된다 |
   | 교안 회로도와 netlist 위상이 맞는가 | PDF 벡터 판독이 필요하다 |
   | 예상값 `source` 가 실제로 그 쪽에 있는가 | 쪽 번호 대조는 사람이 |
   | 표기가 R5·R6 을 지키는가 | 오버바 승격 범위는 문맥 판단이다 |

5. **라운드 문서 작성.** `<N>주차/output/<pre|result>_review_round<N>.md` 에 쓴다.

   ```markdown
   # <N>주차 <예비|결과>보고서 검토 — round<N>

   ## 자동 검사 (scripts/lab/validate.py)

   - ✗ error 3건 / ! warn 1건
   - (findings 를 그대로 나열)

   ## 사람이 확인할 것

   - (§4 표의 항목 중 해당하는 것)

   ## 판정

   - [ ] 제출 가능
   - [x] 수정 필요 — error 가 남아 있다
   ```

6. **error 가 0 이 될 때까지 반복한다.** warn 은 남겨도 되지만 **왜 남기는지 한 줄** 적는다.

## 비-목표

- 보고서를 고쳐 쓰지 않는다. 지적만 한다 (수정은 ③·④ 의 일이다).
- 검사 규칙을 이 문서에 새로 적지 않는다. 규칙은 `validate.py` 에 있고
  거기에 테스트가 붙어 있다. 새 규칙이 필요하면 **테스트부터** 쓴다.
````

- [ ] **Step 10: 실물 2주차 명세로 검증한다**

```bash
python3 -c "
from scripts.lab.spec_parser import parse_spec
from scripts.lab import validate
spec = parse_spec('2주차/체크리스트/명세.md')
findings = validate.validate_spec(spec) + validate.check_netlist('2주차/결선도/netlist.md', spec)
print('\n'.join(str(f) for f in findings) or '문제 없음')
"
```

기대: `문제 없음`, 또는 남은 warn 이 T5(복합회로 미확정) 관련일 것.

- [ ] **Step 11: 전체 테스트 + 커밋**

```bash
python3 -m unittest discover -s tests -t .
git add scripts/lab/boolexpr.py scripts/lab/validate.py \
        tests/test_lab_boolexpr.py tests/test_lab_validate.py \
        .claude/skills/review-lab-report
git commit -m "feat: 부울식 역검산기와 명세·보고서 검증기, review-lab-report 스킬 추가"
```

---

### Task 7: `html2pdf.py` + ⑥ `make-lab-report-cover` 이식

지난 학기 하네스에서 **검증된 부분만** 가져오고 Windows 종속을 걷어낸다. 측정값 파이프라인은 가져오지 않는다 — 이 과목엔 실측 수치가 거의 없다(전 코퍼스 2개).

**Files:**
- Create: `scripts/lab/html2pdf.py`
- Create: `.claude/skills/make-lab-report-cover/SKILL.md`
- Create: `.claude/skills/make-lab-report-cover/template.html`
- Test: `tests/test_lab_html2pdf.py`

**Interfaces:**
- Consumes: `scripts.lab.config.load_course_info`
- Produces:
  - `PdfError(RuntimeError)`
  - `DEFAULT_CHROME` 상수
  - `html_to_pdf(html_path, pdf_path, chrome=DEFAULT_CHROME, timeout=120) -> Path`

- [ ] **Step 1: 지난 학기 하네스를 스크래치패드에 받는다**

원본 저장소를 이 프로젝트 안에 두지 않는다.

```bash
git clone --depth 1 https://github.com/jjundev/ajou-basic-circuit-lab \
  "$TMPDIR/lastharness"
ls "$TMPDIR/lastharness/.claude/skills/make-lab-report-cover/"
```

기대: `SKILL.md`, `template.html`

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_lab_html2pdf.py`:

```python
import tempfile
import unittest
from pathlib import Path

from scripts.lab.html2pdf import DEFAULT_CHROME, PdfError, html_to_pdf


@unittest.skipUnless(Path(DEFAULT_CHROME).exists(), "Chrome 이 없는 환경")
class TestChromeConversion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.html = Path(self.tmp.name) / "in.html"
        self.html.write_text(
            "<style>@page{size:A4}</style><h1>표지</h1>", encoding="utf-8"
        )

    def test_produces_a_pdf(self):
        out = html_to_pdf(self.html, Path(self.tmp.name) / "out.pdf")
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 1000)

    def test_succeeds_despite_macos_stderr_noise(self):
        """Chrome 은 정상 동작 중에도 task_policy_set 에러를 stderr 로 뱉는다.

        종료 코드나 stderr 로 판정하면 멀쩡한 변환을 실패로 읽는다.
        """
        out = html_to_pdf(self.html, Path(self.tmp.name) / "noise.pdf")
        self.assertTrue(out.exists())

    def test_overwrites_and_refreshes_mtime(self):
        target = Path(self.tmp.name) / "twice.pdf"
        html_to_pdf(self.html, target)
        first = target.stat().st_mtime
        import time
        time.sleep(1.1)
        html_to_pdf(self.html, target)
        self.assertGreater(target.stat().st_mtime, first)

    def test_creates_missing_output_directory(self):
        out = html_to_pdf(self.html, Path(self.tmp.name) / "새폴더" / "out.pdf")
        self.assertTrue(out.exists())


class TestErrors(unittest.TestCase):
    def test_missing_input_raises(self):
        with self.assertRaises(PdfError) as ctx:
            html_to_pdf("/없는/입력.html", "/tmp/x.pdf")
        self.assertIn("입력 HTML", str(ctx.exception))

    def test_missing_chrome_raises_with_config_hint(self):
        tmp = tempfile.mkdtemp()
        src = Path(tmp) / "in.html"
        src.write_text("<h1>x</h1>", encoding="utf-8")
        with self.assertRaises(PdfError) as ctx:
            html_to_pdf(src, Path(tmp) / "out.pdf", chrome="/없는/크롬")
        self.assertIn("과목정보.md", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_html2pdf -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.html2pdf'`

- [ ] **Step 4: `scripts/lab/html2pdf.py` 를 만든다**

**아래 코드는 이 머신의 Chrome 으로 실제 변환·재변환·오류 경로까지 검증된 것이다:**

```python
"""Chrome 헤드리스 PDF 변환 (macOS).

**성공 판정 규칙이 이 모듈의 존재 이유다.** Chrome 은 macOS 에서 정상 동작 중에도
stderr 로 `task_policy_set TASK_CATEGORY_POLICY: (os/kern) invalid argument` 를
뱉는다. 종료 코드나 stderr 로 판정하면 멀쩡한 변환을 실패로 읽는다.
**PDF 파일이 실제로 생겼는지로만 판정한다.**
"""

import subprocess
from pathlib import Path

DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class PdfError(RuntimeError):
    pass


def html_to_pdf(html_path, pdf_path, chrome=DEFAULT_CHROME, timeout=120) -> Path:
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    if not html_path.exists():
        raise PdfError(f"입력 HTML 이 없습니다: {html_path}")
    if not Path(chrome).exists():
        raise PdfError(
            f"Chrome 을 찾을 수 없습니다: {chrome}\n"
            "`.claude/과목정보.md` 의 chrome 경로를 확인하세요."
        )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    before = pdf_path.stat().st_mtime if pdf_path.exists() else None

    proc = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        capture_output=True, text=True, timeout=timeout,
    )

    if not pdf_path.exists() or (before is not None and pdf_path.stat().st_mtime == before):
        raise PdfError(
            f"PDF 가 생성되지 않았습니다 (종료 코드 {proc.returncode}).\n"
            f"stderr:\n{proc.stderr.strip()}"
        )
    return pdf_path
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_html2pdf -v
```

기대: `OK` (6 tests)

- [ ] **Step 6: 표지 템플릿을 이식한다**

지난 학기 템플릿을 그대로 가져온다. 디자인은 검증된 미니멀 A4 이고 플레이스홀더 8개를 쓴다.

```bash
cp "$TMPDIR/lastharness/.claude/skills/make-lab-report-cover/template.html" \
   .claude/skills/make-lab-report-cover/template.html
```

플레이스홀더: `{{TITLE}}`, `{{COURSE}}`, `{{CLASS_SECTION}}`, `{{DEPARTMENT}}`, `{{SUBMIT_DATE}}`, `{{PROFESSOR}}`, `{{STUDENT_IDS}}`, `{{STUDENT_NAMES}}`

**한 가지를 고친다.** 폰트 스택 첫 항목이 `'Pretendard'` 인데 이 머신에 없을 수 있다. `'Apple SD Gothic Neo'` 를 앞으로 옮긴다:

```css
font-family: 'Apple SD Gothic Neo', 'Pretendard', 'Malgun Gothic',
             -apple-system, sans-serif;
```

- [ ] **Step 7: IEEE 윤리 페이지를 템플릿에 추가한다**

2016-2 이후 표지 관행은 **IEEE 윤리 페이지 + 표지 2장 구성**이다(그 전엔 ABEEK 교육목표 페이지). 권위 1순위인 `예비보고서 양식.pdf` 의 1쪽도 IEEE 윤리다.

`template.html` 의 표지 `<div>` **앞에** 윤리 페이지를 넣고 `page-break-after: always` 를 준다. 본문은 `가이드라인_및_기준/예비보고서 양식.pdf` 1쪽에서 가져오되, **`extract_text()` 결과는 단어 사이 공백이 뭉개져 있으므로 그대로 붙여넣지 말고 `Read` 로 vision 판독해서 옮긴다.**

```html
<section class="ethics">
  <h2>IEEE Code of Ethics</h2>
  <p class="src">출처: http://www.ieee.org</p>
  <!-- 양식 PDF 1쪽 본문 -->
</section>
<section class="cover"> ... 기존 표지 ... </section>
```

```css
.ethics { page-break-after: always; }
```

- [ ] **Step 8: `make-lab-report-cover` SKILL.md 를 이식한다**

원본 `$TMPDIR/lastharness/.claude/skills/make-lab-report-cover/SKILL.md` 를 베이스로 하되 **네 곳을 반드시 고친다:**

| 원본 | 바꿀 것 |
|---|---|
| 기본값 표에 학부·과목·교수·분반·학번·성명을 **하드코딩** | `.claude/과목정보.md` 를 읽는다. 스킬에 값을 적지 않는다 |
| `Get-Date -Format 'yyyy.MM.dd'` (PowerShell) | `date +%Y.%m.%d` |
| Edge 헤드리스 (`msedge.exe`) | `scripts.lab.html2pdf.html_to_pdf` |
| `C:\Users\Hyunjun\.claude\skills\...\template.html` | 스킬 폴더 기준 상대 경로 |

`.claude/skills/make-lab-report-cover/SKILL.md`:

````markdown
---
name: make-lab-report-cover
description: 논리회로실험 보고서 표지를 IEEE 윤리 페이지와 함께 A4 2장으로 생성한다. 사용자가 "2주차 예비보고서 표지", "결과보고서 표지 만들어줘", "보고서 표지" 등을 요청하거나 /make-lab-report-cover 를 호출할 때 사용한다. 제목만 받으면 학부·과목·교수·분반·학번·성명을 `.claude/과목정보.md` 에서 읽어 HTML 과 PDF 한 쌍을 만든다.
---

# make-lab-report-cover

보고서 첫 장에 들어가는 **IEEE 윤리 페이지 + 표지** 2장을 한 번에 만든다.
2016-2 이후 코퍼스의 지배적 관행이 이 2장 구성이다.

## 값의 출처

**스킬에 학번·성명·교수명을 적지 않는다.** 전부 `.claude/과목정보.md` 에서 읽는다.

```bash
python3 -c "
from pathlib import Path
from scripts.lab import config
root = config.find_project_root(Path('.'))
info = config.load_course_info(root)
print(info)
"
```

`student_ids` / `student_names` / `team` 이 `~` 이면 (1주차 전) **한 줄로 되묻고**,
사용자가 알려주면 이번 실행에만 쓰되 **`과목정보.md` 에 적어둘지 물어본다.**

## 실행 절차

1. **제목 추출.** 사용자 메시지에서 뽑는다 (예: `2주차 예비보고서`). 못 찾으면 되묻고 중단.

2. **출력 폴더 결정.** 제목에 `N주차` 가 있고 `<N>주차/` 가 있으면 그 아래 `output/`.
   폴더가 없으면 **거절하고** `init-lab-week` 를 안내한다.

3. **충돌 확인.** `<폴더>/<제목> 표지.pdf` 가 이미 있으면 덮어쓸지 한 줄로 확인.

4. **제출일.** 사용자가 명시하지 않으면 오늘 날짜.

   ```bash
   date +%Y.%m.%d
   ```

5. **템플릿 치환.** 스킬 폴더의 `template.html` 을 읽고 플레이스홀더 8개를 모두 바꾼다:
   `{{TITLE}}`, `{{COURSE}}`, `{{CLASS_SECTION}}`, `{{DEPARTMENT}}`,
   `{{SUBMIT_DATE}}`, `{{PROFESSOR}}`, `{{STUDENT_IDS}}`, `{{STUDENT_NAMES}}`

6. **HTML 저장 → PDF 변환.**

   ```bash
   python3 -c "
   from scripts.lab.html2pdf import html_to_pdf
   html_to_pdf('<폴더>/<제목> 표지.html', '<폴더>/<제목> 표지.pdf')
   "
   ```

   실패하면 에러를 그대로 보여주고 **HTML 은 남긴다.**

7. **AI 활용 로그.** `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 그 경로에
   한 줄 추가한다. `~` 면 아무것도 하지 않는다.

8. **결과 안내.** HTML·PDF 두 파일의 마크다운 링크를 한 줄로 출력.

## 자연어 오버라이드

"교수님 김철수로", "분반 D012-1", "제출일 2026.09.20" 처럼 같이 말하면
해당 필드만 바꾼다. 별도 옵션 문법은 없다. 명시되지 않은 필드는 `과목정보.md` 값을 쓴다.

## 비-목표

- 예비/결과 표지를 다른 템플릿으로 나누지 않는다 (제목 문자열만 다르다).
- 과목 정보를 스킬 안에 영속 저장하지 않는다 (`과목정보.md` 가 단일 소스다).
````

- [ ] **Step 9: 2주차 표지를 실제로 만들어 A4 를 실측한다**

```bash
python3 -c "
from pypdf import PdfReader
r = PdfReader('2주차/output/2주차 예비보고서 표지.pdf')
print('pages:', len(r.pages))
for p in r.pages:
    print(round(float(p.mediabox.width)/72*25.4, 1), 'x',
          round(float(p.mediabox.height)/72*25.4, 1), 'mm')
"
```

기대: `pages: 2`, 각 쪽이 `210.0 x 297.0 mm` (오차 ±1mm). 다르면 `@page { size: A4; margin: 0 }` 과 `body { width: 210mm; height: 297mm }` 를 확인한다.

- [ ] **Step 10: 전체 테스트 + 커밋**

```bash
python3 -m unittest discover -s tests -t .
git add scripts/lab/html2pdf.py tests/test_lab_html2pdf.py \
        .claude/skills/make-lab-report-cover
git commit -m "feat: Chrome 헤드리스 PDF 변환기와 표지 스킬 이식 (macOS)"
```

---

### Task 8: `record.py` + `render.py` + ② `prep-lab-checklist` + 2주차 인쇄본

실험실에 들고 갈 물건이 여기서 나온다. **인쇄용 PDF 와 md 템플릿을 항상 쌍으로** 만든다 — 태블릿 필기(PDF)와 전사(md) 둘 다 필요하기 때문이다.

**Files:**
- Create: `scripts/lab/record.py`
- Create: `scripts/lab/render.py`
- Create: `.claude/skills/prep-lab-checklist/SKILL.md`
- Create: `.claude/skills/prep-lab-checklist/template.html`
- Create: `2주차/체크리스트/기록.md`
- Create: `2주차/체크리스트/체크리스트.html`, `2주차/체크리스트/체크리스트.pdf`
- Test: `tests/test_lab_record.py`, `tests/test_lab_render.py`

**Interfaces:**
- Consumes: `scripts.lab.spec_parser.{LabSpec, split_columns}`, `scripts.lab.notation.normalize_cell`, `scripts.lab.html2pdf.html_to_pdf`
- Produces:
  - `record.PROMPTS` — 종료 메모 4문항 튜플
  - `record.derive_record(spec) -> str`
  - `render.render_checklist(spec, netlist_text, template) -> str`
  - `render.crop_rows(netlist_text) -> int` — netlist 가 요구하는 브레드보드 행 수

- [ ] **Step 1: `record` 의 실패하는 테스트를 쓴다**

`tests/test_lab_record.py`:

```python
import unittest
from pathlib import Path

from scripts.lab.record import PROMPTS, derive_record
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]


class TestWeek2Record(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        self.text = derive_record(self.spec)

    def test_frontmatter_marks_it_unfilled(self):
        self.assertIn("schema: lab-record/v1", self.text)
        self.assertIn("filled_by: ~", self.text)

    def test_expected_column_is_labelled_and_check_column_is_blank(self):
        self.assertIn("Y예상", self.text)
        self.assertIn("확인", self.text)

    def test_every_table_gets_a_memo_line(self):
        """개수를 박지 말고 명세에서 센다 — T5 를 채우면 숫자가 바뀐다."""
        used = sum(len(item.tables) for item in self.spec.items)
        self.assertEqual(self.text.count("- 메모:"), used)

    def test_closing_prompts_are_present(self):
        for prompt in PROMPTS:
            self.assertIn(f"- {prompt}:", self.text)

    def test_row_count_survives_derivation(self):
        """8행 진리표는 기록에서도 8행이어야 한다."""
        block = self.text[self.text.index("### T1"):self.text.index("### T2")]
        data_rows = [ln for ln in block.split("\n")
                     if ln.startswith("|") and not set(ln) <= set("|- ")]
        self.assertEqual(len(data_rows), 9)   # 헤더 1 + 데이터 8


class TestKindSpecificShapes(unittest.TestCase):
    def test_capture_gets_a_sketch_grid_not_a_table(self):
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        block = text[text.index("### T1"):text.index("### T2")]
        self.assertIn("스케치", block)
        self.assertIn("- 캡션:", block)
        self.assertNotIn("예상 |", block)

    def test_reference_tables_are_excluded(self):
        """T6~T9 는 교안 2입력 이론표다. 기록 칸을 만들면 안 된다."""
        spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        text = derive_record(spec)
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertNotIn(f"### {tid} ·", text)
        for tid in ("T1", "T5"):
            with self.subTest(table=tid):
                self.assertIn(f"### {tid} ·", text)

    def test_capture_carries_the_prose_expectation(self):
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        self.assertIn("> 예상:", text)

    def test_stepped_keeps_its_columns_without_an_expected_suffix(self):
        """스텝 표는 비어 있는 열 자체가 채울 칸이다. `예상` 을 붙이면 안 된다."""
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        block = text[text.index("### T2"):]
        self.assertIn("| 스텝", block)
        self.assertNotIn("예상", block.split("- 메모:")[0])


class TestAlignment(unittest.TestCase):
    def test_korean_headers_align(self):
        """손으로 채울 표라 정렬이 실제로 중요하다 (한글은 2칸)."""
        text = derive_record(parse_spec(ROOT / "12주차/체크리스트/명세.md"))
        block = [ln for ln in text.split("\n") if ln.startswith("| 스텝")][0]
        rule = text.split("\n")[text.split("\n").index(block) + 1]
        self.assertEqual(len(rule), len(rule.rstrip()))
        self.assertEqual(block.count("|"), rule.count("|"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_record -v
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.record'`

- [ ] **Step 3: `scripts/lab/record.py` 를 만든다**

**아래 코드는 실험1(truth-table)과 실험10(capture + stepped)로 검증됐다:**

```python
"""`LabSpec` → `기록.md`. 사람이 채워도 되고 vision 이 채워도 된다.

확인 칸 규약:
    ✓        예상값과 일치
    <값>     불일치 — 실제로 관찰한 값을 적는다
    (공란)   아직 확인하지 않음
표 전체를 진행하지 않았으면 표 아래에 `- 실험을 진행하지 않았음.` 을 적는다.

kind 마다 칸의 뜻이 다르다:
    truth-table  입력은 주어지고, 출력에 `예상` 을 병기한 뒤 확인 칸을 붙인다
    stepped      스텝·조작은 주어지고, 명세에서 **비어 있는 열**이 채울 칸이다
    capture      셀 표가 아니라 스케치 격자 + 캡션 줄

`role: reference` 인 표는 건너뛴다. 교안에서 그대로 옮긴 참조표라 학생이
배선하지도 채우지도 않는다 (실험1 의 2입력 이론표 T6~T9). 확인 칸을 만들면
"2입력 AND 이론표를 실험실에서 채우시오" 라는 무의미한 빈 칸이 나온다.
"""

import unicodedata

from .spec_parser import split_columns

PROMPTS = ("막혔던 것", "예상과 달랐던 것", "뭘 바꿔서 해결했나", "새로 안 것")


def _width(text: str) -> int:
    """한글·한자는 2칸을 차지한다. 손으로 채울 표라 정렬이 실제로 중요하다."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, target: int) -> str:
    return text + " " * max(0, target - _width(text))


def _grid(header, rows) -> str:
    widths = [max([_width(header[i])] + [_width(r[i]) for r in rows])
              for i in range(len(header))]
    lines = ["| " + " | ".join(_pad(h, widths[i]) for i, h in enumerate(header)) + " |",
             "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
    lines += ["| " + " | ".join(_pad(c, widths[i]) for i, c in enumerate(r)) + " |"
              for r in rows]
    return "\n".join(lines)


def _truth_table(table) -> str:
    inputs, outputs = split_columns(table)
    at = {c: i for i, c in enumerate(table.header)}
    header = list(inputs) + [f"{c}예상" for c in outputs] + ["확인"]
    rows = [[row[at[c]] for c in inputs] + [row[at[c]] for c in outputs] + [""]
            for row in table.rows]
    return _grid(header, rows)


def _stepped(table) -> str:
    """명세에서 비어 있는 열이 실험실에서 채울 칸이다. `예상` 을 붙이지 않는다."""
    return _grid(list(table.header) + ["확인"], [list(row) + [""] for row in table.rows])


def _capture(table) -> str:
    return (f"> 예상: {table.expected or '(명세에 expected 가 없다)'}\n\n"
            "```\n  스케치 — 파형을 여기에 그린다\n\n\n\n\n```\n\n"
            "- 캡션:\n- 사진 파일:")


_RENDER = {"truth-table": _truth_table, "stepped": _stepped, "capture": _capture}


def derive_record(spec) -> str:
    out = [
        "---", "schema: lab-record/v1", f"week: {spec.week}",
        f"experiment: {spec.experiment}", "spec: 명세.md",
        "filled_by: ~          # hand | vision | 미기입", "---", "",
        f"# {spec.week}주차 · 실험{spec.experiment} {spec.title} 기록", "",
        "확인 칸: `✓` 일치 / 값 = 불일치 시 실제 관찰값 / 공란 = 미확인.",
        "표를 통째로 진행하지 않았으면 그 표 아래에 `- 실험을 진행하지 않았음.` 을 적는다.", "",
    ]
    for item in spec.items:
        out += [f"## {item.id} · {item.title}",
                f"IC: {', '.join(item.ics)} · 판독: {', '.join(item.device)}", ""]
        for table_id in item.tables:
            table = spec.table(table_id)
            if table.role == "reference":
                continue          # 교안 참조표다. 실험실에서 채우지 않는다
            out += [f"### {table.id} · {table.title}", "",
                    _RENDER[table.kind](table), "", "- 메모:", ""]
    out += ["# 실험 종료 메모", ""] + [f"- {p}:" for p in PROMPTS] + [""]
    return "\n".join(out)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_record -v
```

기대: `OK` (10 tests)

- [ ] **Step 5: `2주차/체크리스트/기록.md` 를 만든다**

```bash
python3 -c "
from pathlib import Path
from scripts.lab.record import derive_record
from scripts.lab.spec_parser import parse_spec
text = derive_record(parse_spec('2주차/체크리스트/명세.md'))
Path('2주차/체크리스트/기록.md').write_text(text, encoding='utf-8')
print(text[:400])
"
```

- [ ] **Step 6: 인쇄 템플릿을 만든다**

`.claude/skills/prep-lab-checklist/template.html`. 플레이스홀더 4개: `{{TITLE}}`, `{{PROCEDURE}}`, `{{TABLES}}`, `{{BREADBOARD}}`.

**설계 제약이 실험실 조건에서 나온다 (스펙 §조합에서 파생되는 제약):**

| 제약 | 이유 |
|---|---|
| 확인 칸은 **세로 정렬** | 세로줄 하나로 관통해 "전항 일치"를 표기할 수 있어야 한다 |
| 칸은 최소 8mm 사각 | 태블릿 펜 끝으로 찍어 채운다 |
| 칸과 숫자 사이 여백 확보 | vision 전사가 체크와 숫자를 구분해야 한다 |
| 핀 번호는 12pt 이상 | 실험실 조명이 어둡다 |
| 결선 절차가 표보다 **먼저** | 배선을 끝내야 표를 채운다 |

```html
<style>
  @page { size: A4; margin: 12mm 10mm; }
  body { font-family: 'Apple SD Gothic Neo', sans-serif; font-size: 10pt; }
  .procedure { page-break-after: always; }
  .procedure .power { font-weight: 700; border: 2px solid #000;
                      padding: 3mm; margin-bottom: 4mm; }
  .procedure li { font-size: 12pt; line-height: 1.7; }
  table { border-collapse: collapse; margin-bottom: 6mm; }
  th, td { border: 1px solid #333; padding: 2mm 3mm; text-align: center; }
  td.check { width: 10mm; height: 8mm; background: #fafafa; }
  .ov { border-top: 1px solid currentColor; }      /* R5 오버바 */
  .sketch { border: 1px solid #333; height: 45mm; }
  .pair { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }
</style>

<h1>{{TITLE}}</h1>
<section class="procedure">{{PROCEDURE}}</section>
<section class="tables">{{TABLES}}</section>
<section class="breadboard">{{BREADBOARD}}</section>
```

- [ ] **Step 7: `render` 의 실패하는 테스트를 쓴다**

`tests/test_lab_render.py`:

```python
import unittest
from pathlib import Path

from scripts.lab.render import crop_rows, render_checklist
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(
    encoding="utf-8")


class TestChecklistHtml(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / "2주차/체크리스트/명세.md")
        self.netlist = (ROOT / "2주차/결선도/netlist.md").read_text(encoding="utf-8")
        self.html = render_checklist(self.spec, self.netlist, TEMPLATE)

    def test_no_placeholder_survives(self):
        self.assertNotIn("{{", self.html)

    def test_power_and_floating_pins_come_first(self):
        """플로팅 입력이 이 과목의 대표 실패 원인이다. 절차 맨 위에 온다."""
        power = self.html.index("VCC")
        first_table = self.html.index("<table")
        self.assertLess(power, first_table)
        self.assertIn("미사용", self.html)

    def test_check_cells_exist_for_every_truth_table_row(self):
        """개수를 박지 말고 명세에서 센다. 참조표(role=reference)는 빠진다."""
        expected = sum(len(self.spec.table(t).rows)
                       for item in self.spec.items for t in item.tables
                       if self.spec.table(t).kind != "capture"
                       and self.spec.table(t).role != "reference")
        self.assertEqual(self.html.count('class="check"'), expected)
        self.assertGreaterEqual(expected, 32)   # T1~T4 가 8행씩

    def test_expected_value_sits_next_to_the_check_cell(self):
        self.assertIn("Y예상", self.html)

    def test_source_is_surfaced_for_every_table(self):
        for table in self.spec.tables:
            with self.subTest(table=table.id):
                self.assertIn(table.source, self.html)

    def test_reference_tables_do_not_get_check_cells(self):
        """참조표는 인쇄본에 없다 — ③ 예비보고서 이론 절의 재료다."""
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertNotIn(f"{tid} ·", self.html)

    def test_wiring_photo_pair_is_present(self):
        """결선도 | 회로 2열 대조는 코퍼스에서 가장 강한 관행이다."""
        self.assertIn("결선도", self.html)
        self.assertIn("회로", self.html)


class TestCapturePage(unittest.TestCase):
    def test_capture_renders_a_sketch_box_not_a_grid(self):
        spec = parse_spec(ROOT / "12주차/체크리스트/명세.md")
        html = render_checklist(spec, "VCC GND 미사용", TEMPLATE)
        self.assertIn('class="sketch"', html)


class TestCrop(unittest.TestCase):
    def test_row_count_comes_from_the_netlist(self):
        """쓰는 행만 남겨 작도 면적을 줄이는 것이 실제 관행이다 (2020 예보2)."""
        netlist = "- U1 = 74HC08\n  - pin 1 ← 입력 A\n  - pin 14 → VCC(+5V)\n"
        self.assertGreater(crop_rows(netlist), 0)
        self.assertLessEqual(crop_rows(netlist), 30)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 8: `scripts/lab/render.py` 를 만든다**

```python
"""kind 별 인쇄 레이아웃. 실험실 조건이 설계 제약이다.

확인 칸은 세로로 정렬되어야 한다 — 세로줄 하나로 관통해 "전항 일치"를 표기하는
방식이 태블릿 필기에서 가장 빠르기 때문이다. 칸과 숫자 사이에는 vision 전사가
체크와 숫자를 구분할 여백이 있어야 한다.

`role: reference` 표는 인쇄본에서 제외한다. 실험실에서 채우는 물건이 아니라
예비보고서 이론 절의 재료다.
"""

import html
import re

from .notation import normalize_cell
from .spec_parser import split_columns

MAX_BREADBOARD_ROWS = 30
_PIN_ROW = re.compile(r"pin\s+(\d+)")


def crop_rows(netlist_text: str) -> int:
    """netlist 가 실제로 쓰는 행 수. 브레드보드 템플릿을 여기에 맞춰 자른다.

    소스가 하나이므로 크롭이 자동 계산된다 (R7).
    """
    ic_count = netlist_text.count(" = 74")
    rows = max(6, ic_count * 8)
    return min(rows, MAX_BREADBOARD_ROWS)


def _esc(text) -> str:
    return html.escape(str(text), quote=False)


def _procedure(spec, netlist_text) -> str:
    """결선 절차. VCC/GND/미사용핀을 최상단 박스에 둔다."""
    power = " · ".join(f"{k} = {v}" for k, v in spec.power.items())
    out = [f'<div class="power">전원: {_esc(power)} · '
           "미사용 입력핀은 전부 GND (플로팅 금지)</div>", "<ol>"]
    for line in netlist_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("-") and ("pin" in stripped or "미사용" in stripped):
            out.append(f"<li>{_esc(stripped.lstrip('- '))}</li>")
    out.append("</ol>")
    return "\n".join(out)


def _truth_or_stepped_html(table) -> str:
    if table.kind == "truth-table":
        inputs, outputs = split_columns(table)
        at = {c: i for i, c in enumerate(table.header)}
        head = list(inputs) + [f"{c}예상" for c in outputs]
        body = [[normalize_cell(row[at[c]]) for c in inputs]
                + [normalize_cell(row[at[c]]) for c in outputs]
                for row in table.rows]
    else:
        head = list(table.header)
        body = [[normalize_cell(c) for c in row] for row in table.rows]

    out = ["<table>", "<tr>"]
    out += [f"<th>{_esc(h)}</th>" for h in head]
    out.append('<th>확인</th></tr>')
    for row in body:
        out.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row)
                   + '<td class="check"></td></tr>')
    out.append("</table>")
    return "\n".join(out)


def _capture_html(table) -> str:
    return (f"<p>예상: {_esc(table.expected or '')}</p>"
            '<div class="sketch"></div><p>캡션: ________________</p>')


def _tables(spec) -> str:
    out = []
    for item in spec.items:
        out.append(f"<h2>{_esc(item.id)} · {_esc(item.title)}</h2>")
        out.append(f"<p>IC: {_esc(', '.join(item.ics))} · "
                   f"판독: {_esc(', '.join(item.device))}</p>")
        for table_id in item.tables:
            table = spec.table(table_id)
            if table.role == "reference":
                continue          # 참조표는 인쇄본에 넣지 않는다 (③ 이론 절의 재료다)
            out.append(f"<h3>{_esc(table.id)} · {_esc(table.title)}</h3>")
            out.append(f"<p class='src'>출처: {_esc(table.source)}</p>")
            out.append(_capture_html(table) if table.kind == "capture"
                       else _truth_or_stepped_html(table))
        out.append('<div class="pair">'
                   "<div><b>결선도</b><br>(사진 부착)</div>"
                   "<div><b>구성한 회로</b><br>(사진 부착)</div></div>")
    return "\n".join(out)


def _breadboard(spec, netlist_text) -> str:
    rows = crop_rows(netlist_text)
    labels = " · ".join(f"{k}={v}" for k, v in spec.power.items())
    return (f"<h2>브레드보드 작도 ({rows}행)</h2>"
            f"<p>단자: {_esc(labels)}</p>"
            f'<img src="../../.claude/assets/Breadboard.jpg" '
            f'style="width:100%;max-height:{rows * 6}mm;object-fit:cover;'
            'object-position:top">')


def render_checklist(spec, netlist_text, template) -> str:
    title = f"{spec.week}주차 · 실험{spec.experiment} {spec.title} 체크리스트"
    return (template
            .replace("{{TITLE}}", _esc(title))
            .replace("{{PROCEDURE}}", _procedure(spec, netlist_text))
            .replace("{{TABLES}}", _tables(spec))
            .replace("{{BREADBOARD}}", _breadboard(spec, netlist_text)))
```

- [ ] **Step 9: 테스트가 통과하는지 확인한다**

```bash
python3 -m unittest tests.test_lab_render -v
```

기대: `OK` (9 tests)

- [ ] **Step 10: ② `prep-lab-checklist` 스킬을 만든다**

`.claude/skills/prep-lab-checklist/SKILL.md`:

````markdown
---
name: prep-lab-checklist
description: 논리회로실험 주차 명세에서 실험실에 들고 갈 체크리스트를 만든다. 인쇄용 A4 PDF 와 전사용 기록.md 를 항상 쌍으로 낸다. 사용자가 "2주차 체크리스트", "실험실 들고 갈 거 만들어줘", "뭐 측정해야 해", "체크리스트 뽑아줘" 등을 요청하거나 /prep-lab-checklist 를 호출할 때 사용한다. 결선 절차·진리표 확인 칸·브레드보드 작도면·사진 대조란을 포함한다.
---

# prep-lab-checklist

`<N>주차/체크리스트/명세.md` 하나에서 실험실용 산출물 전부를 파생한다.

**PDF 와 md 를 항상 쌍으로 만든다.** 태블릿에 PDF 를 띄워 펜으로 채우고,
끝나면 `기록.md` 로 전사한다(④가 vision 으로 돕는다).

## 실행 절차

1. **주차 폴더·명세 확인.** `<N>주차/체크리스트/명세.md` 가 없으면 **거절한다.**
   폴더가 없으면 `init-lab-week` 를, 명세가 없으면 교안 판독이 먼저임을 안내한다.
   **명세를 지어내지 않는다.**

2. **먼저 검증한다.** 틀린 진리표를 인쇄해서 실험실에 들고 가는 것이 최악이다.

   ```bash
   python3 -c "
   from scripts.lab.spec_parser import parse_spec
   from scripts.lab import validate
   spec = parse_spec('<N>주차/체크리스트/명세.md')
   findings = (validate.validate_spec(spec)
               + validate.check_netlist('<N>주차/결선도/netlist.md', spec))
   print('\n'.join(str(f) for f in findings) or '문제 없음')
   "
   ```

   **error 가 하나라도 있으면 인쇄하지 말고 보고한다.** warn 은 알리고 진행한다.

3. **기록 템플릿 파생.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.record import derive_record
   from scripts.lab.spec_parser import parse_spec
   spec = parse_spec('<N>주차/체크리스트/명세.md')
   Path('<N>주차/체크리스트/기록.md').write_text(derive_record(spec), encoding='utf-8')
   "
   ```

4. **인쇄본 렌더 + PDF.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.render import render_checklist
   from scripts.lab.spec_parser import parse_spec
   from scripts.lab.html2pdf import html_to_pdf
   spec = parse_spec('<N>주차/체크리스트/명세.md')
   netlist = Path('<N>주차/결선도/netlist.md').read_text(encoding='utf-8')
   tmpl = Path('.claude/skills/prep-lab-checklist/template.html').read_text(encoding='utf-8')
   out = Path('<N>주차/체크리스트/체크리스트.html')
   out.write_text(render_checklist(spec, netlist, tmpl), encoding='utf-8')
   html_to_pdf(out, out.with_suffix('.pdf'))
   "
   ```

5. **A4 실측.** 아래를 돌려 210×297mm 인지 확인한다. 아니면 CSS 를 고치고 다시 낸다.

   ```bash
   python3 -c "
   from pypdf import PdfReader
   for p in PdfReader('<N>주차/체크리스트/체크리스트.pdf').pages:
       print(round(float(p.mediabox.width)/72*25.4,1),
             round(float(p.mediabox.height)/72*25.4,1))
   "
   ```

6. **결과 안내.** `기록.md` · `체크리스트.pdf` 링크와 표 개수·행 수를 한 줄로.

## 인쇄물 구성 (이 순서를 지킨다)

1. **결선 절차** — VCC/GND/미사용핀 박스가 맨 위. 배선을 끝내야 표를 채운다
2. **표** — kind 별 레이아웃, 각 표에 `출처` 노출
3. **결선도 | 회로 2열 대조** — 항목마다
4. **브레드보드 작도면** — netlist 가 요구하는 행 수만큼 크롭

## kind 별 칸

| kind | 기록 칸 | 사진 |
|---|---|---|
| `truth-table` | 행마다 세로 정렬 확인 칸, 예상값 좌측 병기 | 항목당 완성 회로 1장 + **불일치 행 필수** |
| `stepped` | 스텝이 행. 명세에서 빈 열이 채울 칸 | **스텝마다** (진행이 요점이다) |
| `capture` | 스케치 격자 + 캡션 줄 | 사진 자체가 결과물 |

사진 파일명은 `T<n> row<m>.jpg` 로 찍는다 — ④가 T번호로 표에 자동 배치한다.

## 비-목표

- 명세를 만들지 않는다 (교안 판독은 사람의 일이다).
- 자동 배선도를 그리지 않는다 (netlist + 빈 브레드보드만 준다).
- 캐시 신선도 로직(mtime 비교·SOURCES 블록)을 만들지 않는다.
  소스가 고정이므로 그냥 다시 만드는 게 싸고 안전하다.
````

- [ ] **Step 11: 2주차 인쇄본을 실제로 만든다**

위 §실행 절차 3~5 를 2주차에 대해 그대로 돌린다. 산출물 3개를 확인한다:
`2주차/체크리스트/기록.md`, `체크리스트.html`, `체크리스트.pdf`

- [ ] **Step 12: 전체 테스트 + 커밋**

```bash
python3 -m unittest discover -s tests -t .
git add scripts/lab/record.py scripts/lab/render.py \
        tests/test_lab_record.py tests/test_lab_render.py \
        .claude/skills/prep-lab-checklist 2주차/체크리스트
git commit -m "feat: 기록 템플릿·인쇄 렌더러와 prep-lab-checklist 스킬 추가"
```

---

### Task 9: ① `explain-lab-preview` 이식

지난 학기 스킬에서 **학습 프로파일 P1~P7 은 그대로** 가져온다 — 도메인 무관하게 유효하다. 바꾸는 건 소스 디스커버리와 grounding 대상뿐이다.

이 Task 는 다른 Task 에 의존하지 않는다. 순서를 앞당겨도 된다.

**Files:**
- Create: `.claude/skills/explain-lab-preview/SKILL.md`
- Create: `.claude/skills/explain-lab-preview/template.html`

**Interfaces:**
- Consumes: `scripts.lab.html2pdf.html_to_pdf` (Task 7), `scripts.lab.config.load_course_info`
- Produces: 없음 (대화가 산출물이다)

- [ ] **Step 1: 원본을 읽는다**

```bash
cat "$TMPDIR/lastharness/.claude/skills/explain-lab-preview/SKILL.md"
```

213줄이다. §0 학습 프로파일, §1 입력 해석, §2 소스 디스커버리, §3 설명 흐름, §5 메뉴, §6 저장, §8 PDF 구조를 확인한다.

- [ ] **Step 2: 그대로 가져오는 것과 바꾸는 것을 가른다**

| 부분 | 조치 |
|---|---|
| §0 학습 프로파일 P1~P7 | **그대로.** 비유 먼저 → 동기 빌드업 → 정밀 디테일 확인 → 통제 실험 프레임 → 표 비교 → 대화형 페이싱 → 난이도 하강 |
| §3 설명 흐름 ([1] 오프닝만 자동, 나머지는 메뉴 진입) | **그대로.** 페이싱 규칙이 P6 의 구현이다 |
| §1 인자 (`쉽게`/`저장`/`pdf`) | **그대로**, 경로 구분자만 `\` → `/` |
| §2 소스 디스커버리 | **전면 교체** (아래 Step 3) |
| 비유 시드 표 (공진·RC·커패시터…) | **전면 교체** — 아날로그 회로 비유다. 논리회로용으로 다시 쓴다 |
| grounding 대상 "실제 수치·Table 구조" | **교체** — 이 과목엔 수치가 없다. 그 주의 **실제 IC·진리표·핀아웃**으로 |
| `C:\Users\Hyunjun\...` 하드코딩 | 제거 |
| 학생 이름 하드코딩 | `.claude/과목정보.md` 참조 |

- [ ] **Step 3: 소스 디스커버리를 논회실용으로 다시 쓴다**

지난 학기는 "예비보고서를 1순위로 인용"했다. **이 과목에선 그러면 안 된다** — 과거 예비보고서는 권위 5순위 코퍼스이고 알려진 오염이 있다.

| 우선순위 | 패턴 | 용도 |
|---|---|---|
| 1 | `docs/강의노트_이론_실험_매핑_정리.md` | 주차 ↔ 실험 ↔ 이론 챕터 매핑 |
| 2 | `<WEEK_DIR>/강의노트/실험N.pdf` 또는 `from_the_past/정리/강의노트/실험N.pdf` | **주 grounding.** 목적·IC·회로도·절차 |
| 3 | `from_the_past/정리/논회 강의노트/Ch*.pdf` | 이론 배경 |
| 4 | `docs/study/*.md` | 이미 정리된 학습 모듈 |
| 5 | `<WEEK_DIR>/STT/` | 강의 녹취 (있으면) |

**주차 → 실험 회전 매핑을 반드시 적용한다.** 5·6·7주차가 실험 5·6·4 다.

**과거 제출본을 인용하지 않는다.** 필요하면 다수결로만, 연도를 명시하고.

- [ ] **Step 4: 비유 시드를 논리회로용으로 다시 쓴다**

```markdown
| 도메인 | 비유 |
|---|---|
| 논리 게이트 | 수문 — AND 는 직렬 수문 둘, OR 은 병렬 수문 둘 |
| 드모르간 | "둘 다 열림의 반대 = 하나라도 닫힘" |
| 진리표 | 가능한 모든 스위치 조합을 빠짐없이 적은 목록 |
| 플립플롭 | 딸깍 스위치 — 손을 떼도 상태가 남는다 |
| 래치 vs F/F | 문이 열려 있는 동안 통과 vs 종 칠 때만 통과 |
| 디코더 | 우편번호 → 정확히 한 집의 초인종 |
| 멀티플렉서 | 여러 수도관 중 하나만 고르는 밸브 |
| 시프트 레지스터 | 컨베이어 벨트 — 클럭마다 한 칸씩 |
| 카운터 | 주행거리계 자릿수 올림 |
| DAC/ADC | 계단 vs 자 — 이산 단계를 연속량에 맞춘다 |
| 플로팅 입력 | 아무 데도 안 연결된 스위치 — 값이 정해지지 않는다 |
```

마지막 항목이 중요하다. 플로팅 입력이 이 과목의 대표 실패 원인이므로 **오프닝에서 한 번 짚는다.**

- [ ] **Step 5: grounding 대상을 그 주의 실물로 바꾼다**

설명이 추상 이론에 머물지 않도록, 아래를 **반드시 그 주의 실제 값으로** 채운다.

- 그 주 쓰는 **IC 번호와 게이트 종류** (실험1 = 74HC00/02/04/08/32/86)
- 그 주 **진리표의 실제 행**
- **핀 배치** — VCC 14 / GND 7, 미사용 입력핀 처리
- 교안의 **encoding** — 실험1 이론표는 `H/L`, 실험6 은 `0/1`. **바꿔 말하지 않는다**

`<N>주차/체크리스트/명세.md` 가 이미 있으면 그것을 grounding 소스로 쓴다(가장 정확하다).

- [ ] **Step 6: read-only 를 명시한다**

원본과 같다. **명세·기록·보고서를 수정하지 않는다.** 산출은 `저장`/`pdf` 인자로만.

- [ ] **Step 7: `template.html` 을 가져온다**

```bash
cp "$TMPDIR/lastharness/.claude/skills/explain-lab-preview/template.html" \
   .claude/skills/explain-lab-preview/template.html
```

**MathJax 는 가져오지 않는다.** 원본은 `mathjax/` 폴더를 번들했지만 이 과목의 수식은 부울식뿐이고, `.ov` CSS 오버바(Task 8 template 과 동일)로 충분하다. `template.html` 에서 MathJax 스크립트 태그를 지우고 `.ov` 규칙을 넣는다.

```css
.ov { border-top: 1px solid currentColor; }
```

PDF 변환은 `scripts.lab.html2pdf.html_to_pdf` 를 쓴다 (Edge 아님).

- [ ] **Step 8: 2주차로 실행 검증한다**

`/explain-lab-preview 2주차` 를 돌려 확인한다:

- [1] 오프닝만 나오고 멈추는가 (P6 페이싱)
- 74HC08·74HC32 같은 **실제 IC 번호**가 나오는가
- 교안 이론표의 `H/L` 을 `0/1` 로 바꿔 말하지 않는가
- 플로팅 입력을 짚는가
- 메뉴가 나오고 사용자 선택을 기다리는가

- [ ] **Step 9: 커밋**

```bash
git add .claude/skills/explain-lab-preview
git commit -m "feat: explain-lab-preview 스킬 이식 (논리회로 grounding 으로 교체)"
```

---

### Task 10: ③ `write-pre-report` + 2주차 예비보고서

**Files:**
- Create: `.claude/skills/write-pre-report/SKILL.md`
- Create: `.claude/skills/write-pre-report/template.html`
- Create: `2주차/output/2주차_예비보고서.md`, `2주차/output/2주차_예비보고서.pdf`
- Create: `2주차/output/pre_review_round1.md`

**Interfaces:**
- Consumes: `scripts.lab.config.load_report_format`, `scripts.lab.spec_parser.parse_spec`, `scripts.lab.notation.to_overbar_html`, `scripts.lab.html2pdf.html_to_pdf`, `scripts.lab.validate.check_report_sections`
- Produces: 2주차 예비보고서 md/pdf 쌍

- [ ] **Step 1: 양식 파일 구동을 스킬의 첫 규칙으로 박는다**

**섹션 목록을 스킬에 적지 않는다.** 이것이 R1 의 핵심이고, 어기면 조교 안내가 왔을 때 스킬을 다시 짜야 한다.

```bash
python3 -c "
from pathlib import Path
from scripts.lab import config
root = config.find_project_root(Path('.'))
fmt = config.load_report_format(root)
print('프리셋:', fmt.preset)
for s in fmt.pre:
    flag = ' (항목마다 반복)' if s.repeat == 'per-item' else ''
    skip = '' if s.generate else '  [생성 안 함]'
    print(f'  - {s.name}{flag}{skip}')
"
```

`repeat: per-item` 인 섹션은 **항목(`items`)마다 반복해서 쓴다.**

- [ ] **Step 2: "실험 부품" 섹션의 재료를 정한다**

코퍼스 60편 중 47편이 이 섹션을 갖고, 명칭이 부품/장비/소자로 갈린다. **명칭은 양식 파일이 정한다.**

내용은 명세의 `ics` 를 기준으로:

- IC 번호와 기능 — `from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/ic칩.txt`
- 핀 다이어그램 — 같은 폴더의 이미지. **74HC08·74HC32 는 그 폴더에 없다.**
  없는 것을 있는 척 인용하지 말고, 표준 DIP-14 배치임을 밝히고 **실물 대조를 권고**한다
- 게이트 구성도 — 교안 p4~p9 의 기호

**LED 330Ω 직렬과 미사용 입력핀 처리를 부품 설명에 함께 적는다.**

- [ ] **Step 3: 결선도 섹션을 쓴다**

평가기준(권위 2순위)이 예보 필수로 요구하는 항목이다. 배포 양식(권위 1순위)에는 없지만 **평가에는 들어간다** — 그래서 교집합 프리셋에 있다.

- `2주차/결선도/netlist.md` 를 표로 싣는다
- Task 8 이 크롭·라벨한 브레드보드 템플릿을 삽입한다
- **자동 배선도를 그리지 않는다.** 실제 관행은 손으로 그리는 것이고,
  코퍼스의 결선도엔 핀 번호가 아니라 신호명·전원명·저항값(`330Ω`)이 주석으로 붙는다

- [ ] **Step 4: "실험 과정 및 예상 결과" 를 쓴다**

명세의 표를 그대로 싣되 **`source` 를 각주로 노출한다.** 예상값의 출처를 항상 밝히는 것이 이 하네스의 규칙이다.

```markdown
| A | B | C | Y |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
...

> T1 출처: 부울대수로 도출 (Y = A·B·C). 교안 p4 의 2입력 AND 이론표를 3입력으로 확장.
```

`capture` 표는 셀 표 대신 `expected` 산문을 싣는다.

- [ ] **Step 5: 보수 표기를 렌더한다 (R5)**

저작은 `'`, PDF 는 오버바. **부울식에만 승격하고 표 헤더·신호명·셀 값에는 하지 않는다.**

```bash
python3 -c "
from scripts.lab.notation import to_overbar_html
for e in [\"(A·B·C)'\", \"A'\", \"(A+B+C)'\"]:
    print(e, '->', to_overbar_html(e))
"
```

기대:

```
(A·B·C)' -> <span class="ov">A·B·C</span>
A' -> <span class="ov">A</span>
(A+B+C)' -> <span class="ov">A+B+C</span>
```

`template.html` 에 `.ov { border-top: 1px solid currentColor; }` 를 넣는다.

**실험6 의 `Q(t-1)'` 같은 셀 값에는 이 함수를 부르지 않는다** — 상태 토큰이지 부울식이 아니다.

- [ ] **Step 6: 표지 결합 + PDF 변환**

⑥ `make-lab-report-cover` 로 표지 2장(IEEE 윤리 + 표지)을 먼저 만들고, 본문 HTML 을 이어 붙여 한 PDF 로 낸다.

```bash
python3 -c "
from scripts.lab.html2pdf import html_to_pdf
html_to_pdf('2주차/output/2주차_예비보고서.html',
            '2주차/output/2주차_예비보고서.pdf')
"
```

- [ ] **Step 7: ①의 저장본 참조 규칙**

`<N>주차/output/*실험프리뷰*.md` 가 있으면 참조하되 **톤을 바꿔 다시 쓴다.** 프리뷰는 대화체 설명이고 보고서는 서면 문서다. 문장을 그대로 옮기지 않는다.

- [ ] **Step 8: `.claude/skills/write-pre-report/SKILL.md` 를 쓴다**

````markdown
---
name: write-pre-report
description: 논리회로실험 예비보고서를 `.claude/보고서양식.md` 의 섹션 목록대로 작성하고 표지와 묶어 PDF 로 낸다. 사용자가 "2주차 예비보고서 써줘", "예보 작성", "예비보고서 만들어줘" 등을 요청하거나 /write-pre-report 를 호출할 때 사용한다. 실험 목적·이론·부품·과정 및 예상 결과·결선도·참고문헌을 명세와 교안에 근거해 채운다.
---

# write-pre-report

## 절대 규칙

1. **섹션 목록을 이 문서에 적지 않는다.** `.claude/보고서양식.md` 에서 읽는다.
   양식은 연도마다·학생마다 다르고 이번 학기 것이 미확정이다 (R1).
2. **예상값의 출처를 항상 밝힌다.** 명세의 `source` 를 각주로 노출한다.
3. **자동 배선도를 그리지 않는다.** netlist 표 + 크롭된 브레드보드 템플릿까지다.
4. **과거 제출본을 베끼지 않는다.** 권위 5순위 코퍼스이고 알려진 오염이 있다.
   참고하려면 다수결로, 연도를 밝히고.
5. **없는 근거를 지어내지 않는다.** 74HC08·74HC32 핀아웃 데이터시트는 저장소에 없다.
   표준 DIP-14 배치임을 밝히고 실물 대조를 권고한다.

## 실행 절차

1. **주차·명세 확인.** 없으면 거절하고 `init-lab-week` 또는 명세 작성을 안내한다.
2. **양식 로드** (§절대 규칙 1). `repeat: per-item` 이면 항목마다 반복한다.
3. **명세 로드 및 검증.** error 가 있으면 보고하고 사용자 판단을 기다린다.
4. **섹션별 작성** — 아래 재료 표를 따른다.
5. **md 저장** → **표지 생성**(⑥) → **HTML 결합** → **PDF 변환**.
6. **⑤ `review-lab-report` 로 검증**하고 error 0 까지 라운드를 반복한다.
7. `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 로그 한 줄을 남긴다.

## 섹션별 재료

| 섹션 | 재료 |
|---|---|
| 실험 목적 | 교안 p2 "목적" 슬라이드 |
| 실험 이론 | 교안 이론 슬라이드 + `논회 강의노트/Ch*.pdf` + `docs/study/` + 명세의 **`role: reference` 표**(실험1 T6~T9 = 2입력 이론표, `encoding: H/L`). **`H/L` 을 `0/1` 로 바꾸지 말 것** |
| 실험 부품 | 명세 `ics` + `ic칩.txt` + 핀아웃 이미지. LED 330Ω·미사용핀 처리 포함 |
| 실험 과정 및 예상 결과 | 명세의 표 전부 + `source` 각주 |
| 회로 결선도 | `<N>주차/결선도/netlist.md` 표 + 크롭된 브레드보드 |
| 출처 및 참고문헌 | 교안 쪽 번호, 데이터시트, 이론 교재. **실제로 본 것만** |

## 비-목표

- 결과를 예측해 실험 결과 섹션을 채우지 않는다 (④의 영역이다).
- 고찰을 쓰지 않는다 (예보엔 없고, 결보에서도 본인 경험이 재료다).
````

- [ ] **Step 9: 2주차 예비보고서를 실제로 만든다**

⑤로 검증한다.

```bash
python3 -c "
from pathlib import Path
from scripts.lab import config, validate
root = config.find_project_root(Path('.'))
fmt = config.load_report_format(root)
for f in validate.check_report_sections('2주차/output/2주차_예비보고서.md', fmt.pre):
    print(f)
" | tee 2주차/output/pre_review_round1.md
```

기대: 출력 없음(모든 섹션 존재). 누락이 나오면 보고서를 고치고 다시 돌린다.

- [ ] **Step 10: 커밋**

```bash
git add .claude/skills/write-pre-report 2주차/output
git commit -m "feat: write-pre-report 스킬과 2주차 예비보고서 추가"
```

---

### Task 11: ④ `write-result-report`

실험이 끝난 뒤 쓰는 스킬이다. **2주차 실험 전에는 끝까지 검증할 수 없다** — 필기 PDF 가 없기 때문이다. 스킬을 완성해 두고, 실험 후 실데이터로 확인한다.

**Files:**
- Create: `.claude/skills/write-result-report/SKILL.md`
- Create: `.claude/skills/write-result-report/template.html`

**Interfaces:**
- Consumes: `scripts.lab.config.load_report_format`, `scripts.lab.spec_parser.parse_spec`, `scripts.lab.md.parse_tables`, `scripts.lab.html2pdf.html_to_pdf`, `scripts.lab.validate.check_report_sections`
- Produces: 없음 (스킬 자체가 산출물)

- [ ] **Step 1: vision 전사 규칙을 정한다**

필기 PDF → `기록.md` 의 확인 칸.

- 불확실한 칸은 **목록으로 제시하고 사용자가 확정한다. 자동 확정 금지.**
- 확정 후 `기록.md` 의 `filled_by:` 를 `vision` 으로 바꾼다
- 체크 표시와 숫자를 혼동하기 쉽다 — Task 8 의 여백 규칙이 이걸 위한 것이다

```markdown
아래 3칸은 판독이 불확실합니다. 확인해 주세요.

| 표 | 행 | 읽은 값 | 대안 |
|---|---|---|---|
| T1 | 5 | `✓` | `1` |
| T3 | 2 | `0` | `✓` |
```

- [ ] **Step 2: 양식 파일 구동** (Task 10 Step 1 과 동일한 규칙)

```bash
python3 -c "
from pathlib import Path
from scripts.lab import config
root = config.find_project_root(Path('.'))
fmt = config.load_report_format(root)
print('프리셋:', fmt.preset)
for s in fmt.result:
    flag = ' (항목마다 반복)' if s.repeat == 'per-item' else ''
    skip = '' if s.generate else '  [생성 안 함]'
    print(f'  - {s.name}{flag}{skip}')
"
```

`항목반복형` 프리셋이면 **고찰이 항목마다 반복되고** 마지막에 `전체적인 고찰`이 한 번 더 온다.

- [ ] **Step 3: 결과 표를 구성한다**

`기록.md` 의 확인 칸을 읽어 결과 표를 만든다.

| 확인 칸 | 결과 표 | 본문 서술 |
|---|---|---|
| `✓` | 예상값을 그대로 | "예상과 일치" (행을 일일이 나열하지 않는다) |
| 값 | **그 실제 관찰값**으로 | **행을 지목해 원인을 논한다** |
| 공란 | 공란 유지 | "미확인" 으로 명시 |
| 표 전체 미진행 | 표 생략 | "실험을 진행하지 않았음" 을 명시 |

**일치와 불일치를 본문에서 구분해 서술한다.** 전부 일치한 척하지 않는다.

사진은 파일명의 `T<n> row<m>` 으로 표에 배치한다.

- [ ] **Step 4: kind 별 서술 골격**

| kind | 골격 |
|---|---|
| `truth-table` | "모든 입력 조합에서 일치" 또는 **불일치 행을 지목**하고 원인 후보(플로팅 입력·배선 오류·IC 불량)를 논한다 |
| `stepped` | "N번째 클럭/펄스에서 천이" — 스텝 진행 자체가 결과다 |
| `capture` | 사진 + 관찰 서술. 명세의 `expected` 산문과 대조한다 |

- [ ] **Step 5: 고찰**

`기록.md` 끝의 종료 메모 4문항(막혔던 것 / 예상과 달랐던 것 / 뭘 바꿔서 해결했나 / 새로 안 것)이 재료다.

**비어 있으면 생성하지 말고 사용자에게 묻는다.** 배운 점은 본인 경험이고, 지어낸 고찰은 평가기준의 "실험으로부터 배운점, 목적 달성 여부"를 만족시키지 못한다.

- [ ] **Step 6: 퀴즈 해설 섹션**

양식이 요구할 때만 생성한다(교집합 프리셋에선 `generate: false`). AI 활용은 승인됐으므로 정책 제약은 없다.

- 입력: `<N>주차/퀴즈/` 의 **그 주 실제 문제**
- 근거: `from_the_past/정리/퀴즈/실험N/` 기출·정답 + 교안
- **문제 원본이 없으면 생성하지 말고 요청한다.** 기억으로 지어낸 문제에 답을 다는 건 무의미하다
- 퀴즈는 **학기마다·분반마다 다르다**(월요반과 금요반 문제지가 다르다). 기출을 "그대로 나올 것"으로 다루지 않는다

- [ ] **Step 7: `.claude/skills/write-result-report/SKILL.md` 를 쓴다**

````markdown
---
name: write-result-report
description: 논리회로실험 결과보고서를 `기록.md` 의 확인 칸과 실험사진에서 작성하고 PDF 로 낸다. 사용자가 "2주차 결과보고서 써줘", "결보 작성", "실험 결과 정리해줘" 등을 요청하거나 /write-result-report 를 호출할 때 사용한다. 필기 PDF 를 vision 으로 전사하고, 일치·불일치를 구분해 서술하며, 섹션 구성은 `.claude/보고서양식.md` 를 따른다.
---

# write-result-report

## 절대 규칙

1. **섹션 목록을 이 문서에 적지 않는다.** `.claude/보고서양식.md` 에서 읽는다 (R1).
2. **불확실한 전사를 자동 확정하지 않는다.** 목록으로 제시하고 사용자가 정한다.
3. **고찰을 지어내지 않는다.** 종료 메모가 비었으면 묻는다.
4. **일치한 척하지 않는다.** 불일치 행은 지목하고 원인을 논한다.
5. **없는 퀴즈 문제를 지어내지 않는다.** 원본을 요청한다.

## 실행 절차

1. 주차 폴더·`기록.md` 확인. 없으면 거절하고 ②를 안내한다.
2. 필기 PDF 가 있으면 vision 전사 → 불확실 칸 확인 → `filled_by: vision`.
3. 양식 로드 (§절대 규칙 1). `repeat: per-item` 처리.
4. 섹션별 작성 (§서술 골격).
5. 표지(⑥) 결합 → PDF 변환.
6. ⑤ `review-lab-report` 로 검증, error 0 까지 반복.
7. `ai_usage_log` 가 `~` 가 아니면 로그 한 줄.

## 서술 골격

| kind | 골격 |
|---|---|
| `truth-table` | 전부 일치면 한 문장. 불일치는 **행을 지목**하고 원인 후보(플로팅 입력·배선 오류·IC 불량)를 논한다 |
| `stepped` | "N번째 클럭에서 천이" — 진행 자체가 결과다 |
| `capture` | 사진 + 관찰. 명세의 `expected` 와 대조한다 |

## 확인 칸 → 결과 표

| 확인 칸 | 결과 표 | 본문 |
|---|---|---|
| `✓` | 예상값 | "예상과 일치" |
| 값 | 그 관찰값 | 행 지목 + 원인 |
| 공란 | 공란 | "미확인" 명시 |
| 표 전체 미진행 | 생략 | "진행하지 않았음" 명시 |

사진은 파일명 `T<n> row<m>.jpg` 로 표에 배치한다.

## 비-목표

- 기록에 없는 값을 채우지 않는다.
- 예상값을 결과로 옮겨 적어 "성공한 실험"을 만들지 않는다.
````

- [ ] **Step 8: 명세만으로 도달 가능한 데까지 검증한다**

실험 전이라 `기록.md` 는 비어 있다. **그 상태에서 스킬이 올바르게 멈추는지**를 본다.

```bash
python3 -c "
from pathlib import Path
from scripts.lab import config, md
root = config.find_project_root(Path('.'))
fmt = config.load_report_format(root)
print('결보 섹션:', [(s.name, s.repeat, s.generate) for s in fmt.result])
text = Path('2주차/체크리스트/기록.md').read_text(encoding='utf-8')
front, body = md.split_frontmatter(text)
print('filled_by:', front['filled_by'])
checks = [r[-1] for t in md.parse_tables(body) for r in t.rows]
print('확인 칸 총', len(checks), '개 / 채워진 것', sum(1 for c in checks if c.strip()))
"
```

기대: `filled_by: None`, 채워진 칸 `0`. 이 상태에서 ④를 부르면 **결과 표를 만들지 말고 "기록이 비어 있다"고 보고해야 한다.**

- [ ] **Step 9: 커밋**

```bash
git add .claude/skills/write-result-report
git commit -m "feat: write-result-report 스킬 추가"
```

---

## 완료 판정

Task 11 까지 끝나면 아래가 전부 참이어야 한다.

```bash
python3 -m unittest discover -s tests -t .
```

기대: `OK` — 기존 55개 + 신규 약 90개

```bash
python3 -c "
from scripts.lab.spec_parser import parse_spec
from scripts.lab import validate
for week, exp in ((2, 1), (6, 6), (12, 10)):
    spec = parse_spec(f'{week}주차/체크리스트/명세.md')
    errors = [f for f in validate.validate_spec(spec) if f.level == 'error']
    print(f'{week}주차(실험{exp}):', errors or '깨끗함')
"
```

기대: 세 줄 모두 `깨끗함`

| 산출물 | 확인 |
|---|---|
| `2주차/체크리스트/체크리스트.pdf` | A4 210×297mm, 확인 칸이 세로 정렬 |
| `2주차/체크리스트/기록.md` | 확인 칸 32개(8행 × 4표) 공란, 종료 메모 4문항 |
| `2주차/output/2주차_예비보고서.pdf` | 표지 2장 + 양식의 6개 섹션 전부 |
| `2주차/output/pre_review_round1.md` | error 0 |
| 스킬 7종 | `.claude/skills/*/SKILL.md` 의 `description` 이 트리거 문구를 담고 있다 |

---

## 이 계획서가 다루지 않는 것

| 항목 | 어디로 |
|---|---|
| 실험7·8·9 확산 검증 (스펙 Task 7) | 후속 계획서. `stepped` 의 제어 펄스(`CLR: 1→0→1`), 실험8 의 LED+7-segment 혼재, 실험9 의 세 알파벳 혼재가 남아 있다 |
| ⑧ 퀴즈 대비 (평가 10%) | 후속 계획서. 기출 84편 + 채점본 스캔이 이미 있다. **유형 대비로만** 써야 한다 |
| ⑨ FPGA 텀프로젝트 (평가 30%) | **별개 파이프라인.** 산출물이 HDL·시뮬레이션 파형·합성 결과·핀 할당이라 `lab-spec/v1` 을 억지로 늘리지 않는다. 13주차까지 시간이 있다 |
| 캐시 신선도 로직 | **만들지 않는다.** 지난 학기 v3/v4/v5 드리프트의 원인이었고, 소스(교안)가 고정이므로 재생성이 싸고 안전하다 |

---

## 미확정 사항 — 확인되면 무엇이 바뀌나

| 항목 | 영향 | 조치 | 확인 시점 |
|---|---|---|---|
| **이번 학기 보고서 양식** | `.claude/보고서양식.md` | `preset:` 한 줄 교체. **스킬은 안 건드린다** | 1~2주차 조교 안내 |
| **2026-2 교안이 2020-2와 같은가** | 명세 3종 전부 | 배포되면 Task 1 을 다시 돌린다. 이 과목은 개정될수록 아날로그가 준다(2016 실험1 = 오실로스코프 → 2020 = LED) | 2주차 |
| 74HC08·74HC32 실물 핀아웃 | `netlist.md` | 표준 DIP-14 로 썼다. **1주차에 실물 각인과 대조** | 1주차 |
| 실험1 p13 복합회로 배선 위상 | `명세.md` T5 | vision 재판독으로 확정. 못 하면 T5 를 비워두지 말고 미확정으로 표시 | Task 1 |
| AI 활용 내역 표기 의무 | 전 스킬 | `ai_usage_log` 자리를 비워뒀다. 값만 채우면 켜진다 | 교수님/조교 |
| 조 편성·조원 | `.claude/과목정보.md` | `team`/`student_ids`/`student_names` 채우기 | 1주차 |
| 예비보고서 분할 제출 여부 | `보고서양식.md` | 프리셋 추가 | 1~2주차 |
| 제출 파일명 규칙 | Task 10·11 출력 | 스킬의 출력 경로 한 줄 | 1~2주차 |

---

## 참조

- 설계 근거 문서: [2026-08-28-logic-lab-harness-design.md](docs/plans/2026-08-28-logic-lab-harness-design.md) — R1~R10 결정, 89편 판독 결과, 자료 권위 서열
- 지난 학기 하네스: `https://github.com/jjundev/ajou-basic-circuit-lab` (Task 7·9 에서 이식)
- 이론↔실험 매핑: [강의노트_이론_실험_매핑_정리.md](docs/강의노트_이론_실험_매핑_정리.md)
- 학습 모듈: [docs/study/](docs/study/) — ①의 보조 소스
- 과거 자료 인벤토리: [from_the_past/정리/README.md](from_the_past/정리/README.md) — **Task 3 Step 9 에서 오류 정정**
