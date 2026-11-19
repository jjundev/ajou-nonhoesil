# 실험06~10 실험설명 개선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실험06~10의 독자가 본문과 그림으로 다음 상태나 조작을 재현할 수 있게 수정하고, 같은 검수를 이후 저작 과정에 넣는다.

**Architecture:** 사용 중인 발행본을 기준으로 추적된 저작 원고를 동기화하고, 기존 렌더 함수로 변경할 토픽을 임시 복사본에 조립한다. 발행본에는 검증된 실험설명 파일과 관련 자산을 반영한다. 재현 검사는 제작 스킬의 기존 설명 충분성 검수에서 수행한다.

**Tech Stack:** 저장소 `.venv`의 Python, 기존 학습팩 렌더·Markdown 변환기·검사기, HTML, SVG, JSON, Playwright 또는 기존 Chromium 검수 환경.

**Spec:** 이 문서의 [확정 설계](#확정-설계). 같은 채팅의 2026-11-19 `grill-yourself` 설계를 옮겼다.

## Global Constraints

- 작업 범위는 `복습노트/실험06`~`실험10`의 선정 토픽, 대응 저작 원고, 관련 실험설명 SVG·동반 MD·표 배치·요약·검증 기록, 제작 스킬 문서다.
- 기존 결론 먼저 읽기 방식, 토픽 ID와 순서, 앵커, 읽음 저장 키, 한국어 `~해요`체를 유지한다. 새 표·그림은 기존 작성 방식과 파일 배치 계약을 따른다.
- HTML·MD·요약에서 초기값, 비트 순서, 활성 극성, 엣지, 모델의 성립 조건을 맞춘다. 교안 근거, 설명을 위한 모형, 미확정 실험 조건의 출처를 유지한다.
- 원본, 기출문제·기출풀이, 문제설명 HTML·MD·원고, 문제은행·증거와 기존 UI 자산은 파일별 바이트 동일을 검증한다. 공통 렌더러와 스키마는 기존 인터페이스로 사용한다.
- 검증 단계는 변경한 내용을 수동으로 재현하고 기존 자동 검사와 발행 전 파일 비교를 실행한다. 독립 검토 이력은 실제로 수행한 경우에만 기록한다.

## Review Focus

1. 최근 발행본에만 있는 실험10의 자리값 설명이 재생성 후 빠질 수 있다. `0001`, `0010`의 QA·QB 매핑과 1·2·4·8 설명을 재생성본과 발행본에서 확인한다(Task 1, 2, 5).
2. 실험09의 연속 쓰기 행이 주소 전환 중 쓰기를 허용할 수 있다. 모든 주소 변경 사이의 `WE=1`과 마지막 읽기 전 WE 해제를 확인한다(Task 2).
3. 실험10의 선형 출력 요구값을 실제 출력 예측으로 읽을 수 있다. 0V 모형, 기준을 올린 선형 가정, 공급 한계를 같은 코드에서 대조한다(Task 2).
4. 표 머리글을 바꾸거나 열을 추가하면 표 메타데이터가 어긋날 수 있다. 수정 토픽의 모든 표 키·열 수·머리글을 렌더 함수로 검증하고 375px에서 마지막 열에 접근한다(Task 2, 4, 5).
5. 전체 팩 검사에서 기존 문제설명 불일치가 새 오류를 가릴 수 있다. 실패 메시지 전체를 팩별로 비교하고 반영 대상 밖의 파일 해시도 비교한다(Task 1, 5).

---

## 확정 설계

독자에게 맡기는 추론은 새 규칙을 배운 뒤 다른 입력에 적용하는 한 단계다. 처음 보는 결선·극성·엣지·조작에서는 `시작 상태와 조건 → 중간 신호 또는 조작 → 결과`를 한 번 보여 준다. 다음 행을 읽기 전에 필요한 조건은 앞에서 찾을 수 있어야 한다. 설명을 위한 모형에서 실제 회로로 넘어가는 경우, 결론을 적용하는 자리에서 조건부터 밝힌다.

대표 사례는 실험06 JK의 첫 갱신, 실험09 74670의 주소 전환, 실험10 DAC의 기준 전압 변경이다. 이 세 사례에서 적용한 검수 기준을 스킬에 적고, 앞 감사에서 찾은 나머지 지점에 같은 방법을 적용한다.

### 파일과 데이터 흐름

| 경로 | 책임 |
|---|---|
| `docs/learning-pack-source/실험06/sections.py` | 토픽별 본문 `S`와 제목·출처에 대응하는 원고 |
| `docs/learning-pack-source/실험07/content.py`, `실험08/content.py`, `실험09/content.py`, `실험10/content.py` | 각 실험의 `TOPICS` 본문과 오른쪽 요약 |
| `docs/learning-pack-source/실험08/figures.py` | `ripple_block()`의 실험설명용 SVG 원고 |
| `복습노트/실험NN/실험NN_실험설명.html`, `.pack/실험NN_실험설명.md` | `NN=06,07,08,09,10`의 학생용 본문과 동반 MD |
| 각 팩의 `.pack/sections/table-layout.json` | 변경된 토픽에서 실제로 나온 머리글·열 개수·표 키 동기화 |
| `복습노트/실험06/.pack/sections/note-summaries.json` | 실험06 우측 요약 정본 |
| `복습노트/실험08/.pack/figures/ripple-block.svg` | 실험설명에서 참조하는 비동기 블록도 |
| 각 팩의 `.pack/검증결과.md` | 재현한 행, 근거, 결과와 화면 검수 기록 |
| `.claude/skills/logic-lab-review-pack/references/authoring.md`, `verification.md` | 저작·검수 기준. `.agents/skills/logic-lab-review-pack`은 같은 스킬을 가리킨다. |

### 변경 토픽 조립 방식

- `복습노트/실험NN`을 별도 stage의 같은 이름으로 복사한다. stage의 형제 `.vendor`는 기존 공용 자원 경로를 가리키게 한다. 임시 코드는 `tmp/review-pack/` 안에서만 사용한다.
- 실험06은 `sections.S[topic_id]`를 사용하고, 실험07~10은 `content.TOPICS`에서 `(topic_id, title, pages, body, summary)`를 읽어 `body + h.sumparts(**summary)`로 원고를 만든다. `h`·`content` 모듈 이름이 공유되므로 각 실험은 별도 Python 프로세스로 읽는다. 실험06의 요약은 stage에서 `load_note_summaries()`와 `replace_summary()`로 적용한다.
- 각 원고에 해당 실험의 `h.pull_layouts(fragment, lambda ordinal: f'{topic_id}/{ordinal}')`를 적용한다. stage의 `table-layout.json`에서 해당 토픽의 항목만 교체한다. 임시 `sections/<id>.html`을 만들고 `render.read_fragment(run, relative, names, manifest)`로 링크를 변환한다. `reading_structure_errors(topic_id, fragment)`가 빈 목록이면 `layout_note_tables()`와 `separate_tables(separate_equations(fragment))`를 적용한다. 호출 순서는 `scripts/lab/review_pack/render.py:62`의 기존 흐름에 맞춘다.
- 발행 HTML에서 해당 ID의 `<article class="topic">`를 정확히 한 번 찾아 `<h3>` 뒤의 본문을 교체한다. 토픽 제목과 ID, 다른 article의 바이트를 비교한다. `convert_pack(note_path, manifest=manifest)`로 stage의 실험설명 MD를 내보낸다. 실험08 SVG는 `figures.ripple_block().svg()`에서 얻는다.

## Task 1 · 수정 전 기준선 확보

**입력** 기존 다섯 팩과 추적 원고. **산출물** 임시 팩 복사본, 파일별 SHA-256과 전체 검사 메시지, 수정 토픽의 원고와 발행본 비교 결과.

- [x] 저장소 루트에서 `git status --short`를 확인하고 새 `tmp/review-pack/` 하위에 작업별 stage와 원본 스냅샷을 준비한다. 팩별 전체 상대경로와 SHA-256을 기록한다. HTML의 토픽 ID 순서와 읽음 저장 키는 별도로 기록한다.
- [x] 아래 명령으로 현재 팩의 검사 메시지를 보관한다. 계획 작성 시 다섯 팩 모두 `explanation_html: explanation differs from authored content` 한 건이었다. 실행 시 기준선이 달라지면 해당 오류와 변경 경로를 먼저 확인한다.

  ```bash
  .venv/bin/python -B - <<'PY'
  from pathlib import Path
  from scripts.lab.review_pack.checks import check_pack

  for number in range(6, 11):
      folder = Path('복습노트') / f'실험{number:02d}'
      print(folder.name, sorted(check_pack(folder)))
  PY
  ```

- [x] Task 5에 적힌 pytest 명령도 같은 상태에서 실행해 실패한 테스트 ID와 메시지를 기준선에 붙인다.
- [x] 변경 대상 article을 현행 원고에서 한 번 조립해 stage의 원본과 비교한다. 내용 차이는 정리해 원고에 합칠 변경으로 기록한다. 특히 커밋 `3fe9ae0a`의 실험10 `t-dac`에서 가중합의 정의, QA부터 `1·2·4·8`, `0001·0010`의 해석과 표 이유 열을 확인한다.

## Task 2 · JK, 74670, DAC 대표 사례 수정

**파일** 실험06 `sections.py`·요약 JSON의 `t-jk-latch`, 실험09 `content.py`의 `t-74670`, 실험10 `content.py`의 `t-oc`·`t-dac`. **산출물** stage에 조립한 대표 토픽과 각 토픽의 결과 가림 검산 기록.

- [x] `t-jk-latch`의 `결과 Q`와 JK 규칙표 머리글을 **한 번 갱신 직후의 값**으로 명시한다. `E=J=K=1`에서 `직전 Q=0 → A,B=01 → Q=1 → A,B=10 → Q=0`을 표 바로 뒤에 연결한다. E가 계속 열려 있을 때 두 번째 전이가 일어나는 까닭과 하강 엣지 JK의 단일 갱신을 같은 사례로 이어 준다.
- [x] JK 두 번째 전이의 결과를 가리고 `Q=1, Q′=0`을 되먹였을 때 `A=1, B=0, Q=0`이 도출되는지 확인한다. 짧은 E 펄스의 종료 조건과 엣지형의 갱신 조건을 요약에도 반영한다.
- [x] `t-74670` 쓰기 표를 [체크리스트 T4](/Users/hyunjun_macbook_pro/Documents/Univ/논회실/보고서/실험09/체크리스트/명세.md:169)와 맞춘다. `00/0001 → 01/0010 → 10/0100 → 11/1000`의 각 전환에 `WE=1`로 해제하는 중간 행을 넣고, 마지막 쓰기 뒤 WE를 1로 한 다음 RE를 0으로 내려 읽는 행을 둔다. `RE=1`인 출력은 고임피던스와 LED 꺼짐으로 설명한다.
- [x] 74670의 주소 변경 세 번과 마지막 읽기 전환을 표만 보고 재현한다. 모든 주소·데이터 변경 직전에 `WE=1`, 모든 쓰기 행에서 `WE=0`, 읽기에서 `WE=1, RE=0`이다. 첫 두 주소를 읽어 `0001`, `0010`이 되는지 표 값으로 검산한다.
- [x] `t-dac` 원고에 Task 1에서 확인한 자리값 설명을 먼저 합친다. `t-oc`의 저항비는 0V 노드에서 구한 근사로 표시하고, 등간격 식과 계단 표는 `1·2·4·8` 이상 모델로 표시한다. 실제 결선 설명은 `I₀=(0−V노드)/R가지`, `I₁=(5−V노드)/(R가지+R풀업)`, `ΔI=I₁−I₀` 순서로 한 비트의 전류 차이를 설명한다. 식과 수치 계산은 보충에 둔다.
- [x] `V노드=7.5V`, `R풀업=1.5kΩ`, `R가지=22.6·10.5·4.5·1.5kΩ`, `Rf=4.5kΩ`인 이상 스위치 사례를 검산한다. 계산상 `0000→0001→0010`의 선형 출력 요구값은 약 `42.21→41.18→39.93V`다. 수치의 성격을 **선형 가정에서 필요한 출력**으로 표시하고, +15V 양전원을 가정하면 선형 동작 범위를 벗어난다는 판정을 적는다. 교안의 계단 개형과 실제 측정에 관한 불확실성은 기존 명세에 맞춘다.
- [x] 세 토픽을 stage에 조립한다. 세 검산의 처음 조건·중간 상태·결과가 본문과 요약에서 일치하고 변경된 표의 메타데이터가 유효한지 확인한다.

## Task 3 · 제작 스킬 규칙 개정

**파일** `.claude/skills/logic-lab-review-pack/references/authoring.md`, `verification.md`. **입력** Task 2의 재현 결과. **산출물** 이후 새 팩과 부분 갱신에 적용할 저작 문구와 수동 판정 절차.

- [x] `authoring.md`의 원리·추적표 규칙에 처음 적용하는 연결의 `조건 → 중간 신호/조작 → 결과`, 조작표의 필수 전환, 모델 전제가 보이는 시점을 한 문단으로 추가한다. JK·RAM·DAC의 예를 각각 한 줄 이내로 붙인다.
- [x] `verification.md`의 설명 충분성에 **대표 행의 결과·이유를 가리고 앞 본문과 그림으로 재현**하는 절차를 넣는다. 기록 항목은 `토픽/행`, `앞 근거`, `재현한 중간 단계 및 결과`, `판정`이다. 기존 「한눈에 보기」 필수 항목과 오래된 앵커를 현행 결론 먼저 규정에 맞춘다.
- [x] 두 문서를 왕복해서 읽는다. 저작 지침에 제시된 증거를 검수자가 앞 본문에서 찾을 수 있는지 Task 2 세 사례로 대조한다. 검수 절차의 링크와 해당 절 제목을 확인한다.

## Task 4 · 나머지 지적 반영

**파일** 실험06 `sections.py`·요약 JSON, 실험07~10 `content.py`, 실험08 `figures.py`. **산출물** 아래 항목을 검산한 stage HTML·MD·자산.

- [x] **06 `t-basics`, `t-sr-basic`, `t-sr-enable`, `t-d-latch`.** D·JK·T 특성식에 갱신 조건을 달거나 해당 원리가 소개되는 지점으로 옮긴다. 기본 SR의 Reset 경로에 `R=0 → Q′=1 → Q=0`을 보여 준다. Enable SR과 D에서 `A,B=01`은 Set, `10`은 Reset이라는 쌍을 사용하고 Enable SR의 `00` 금지와 맞춘다.
- [x] **07 `t-shift`, `t-jk`, `t-convert`, `t-7496`.** 상승 엣지 D 모형의 그림 설명과 실제 6비트 하강 엣지 JK의 용도를 밝힌다. `S=0`, 직전 `Q₀=1`이면 처음 두 JK 입력이 `01·10`이고 하강 뒤 `Q₀Q₁=01`임을 추적한다. PISO는 `적재·이동 직후 상태`에서 읽도록 머리글과 문장을 통일한다. `1011`을 적재하면 처음부터 `1,1,0,1`을 읽는다. 7496의 미확정 극성·엣지를 조작표 앞에서 설명한다.
- [x] **08 `t-async`의 `ripple-block.svg`, `t-toggle`, `t-7490`, `t-fnd`.** 그림에 두 하강 엣지 CLK와 `T=1`을 구분하고 외부 CLK→FFA, A→FFB를 확인한다. 2단 2진과 mod의 상태 수 표기를 구분한다. `2×(QD QC QB)+QA`로 `7→8`의 상위 묶음 `011→100`을 추적한다. 7447의 `H`인 세그먼트는 싱크가 해제되어 GND로 흐르는 경로가 끊긴다고 설명한다. `AB=11 → 01 → 00`과 a 소등 이유를 그림에서 검산한다.
- [x] **09 `t-1bit`, `t-2bit`, `t-rules`.** `쓰기 허용·데이터 1 → S,R=10 ↔ S′,R′=01 → Q=1`을 한 번 보여 준다. 2bit 표에서 저장 상태 `W1: (1, 미정)`, `W2: (1,0)`, `R2: OUT=(1,0)`, `R4: OUT=(0,1)`을 추적한다. `OUT0=WR1`은 `OE0=IN0=1`이고 WR 입력 쌍이 유효할 때 적용한다. WR `00` 유지와 `11` 금지 행도 같은 조건과 대조한다.
- [x] **10 `t-network`, `t-comparator`, `t-adc`.** 2R 두 갈래가 병렬로 R이 되고 직렬 R을 더하면 같은 단계가 생기는 모습을 하나의 계산으로 보여 준다. 2비트의 `1/2·1/4`와 3비트의 `1/8`을 확인한다. 실험 비교기의 `0100`은 예시의 9V와 8V 사이를 알려 주는 기록 코드로 표시한다. 오름 Counter 예시의 첫 초과 코드는 `7`, SAR 예시의 6.3V 구간 코드는 `6`이다. 각 예시가 어떤 기준으로 결과를 기록하는지 밝힌다.
- [x] 나머지 토픽을 stage에 조립하고 실험별로 위에 지정된 행의 결과를 가려 검산한다. 수정한 토픽의 요약·동반 MD와 일치하는지 읽고 재현 근거를 각 `.pack/검증결과.md`에 남긴다.

## Task 5 · 최종 비교와 부분 반영

**입력** Task 1 기준선과 검증된 stage. **산출물** 원고와 일치하는 발행본, 팩 검사 결과, 파일 보존 비교 및 화면 근거.

- [x] stage에서 각 팩의 `check_pack`, 실험설명 `check_md`, 변경 fragment의 `reading_structure_errors`, 요약·표 배치 검사를 실행한다. 전체 검사 메시지에는 Task 1의 기준선 외에 추가 오류가 없어야 한다. 생성된 SVG가 실험08 발행 대상과 일치하고 `ripple-block.svg` 이외의 자산 해시가 같은지 확인한다.
- [x] 브라우저에서 바뀐 토픽을 해시로 직접 연다. 375px/1280px와 밝은/어두운 테마에서 표 마지막 열, 수식과 SVG, 우측 요약을 읽을 수 있어야 한다. 그림 요청·KaTeX 오류를 확인하고 토픽 이동 및 읽음 체크를 한 번 시험한다.
- [x] 기존 자동 검사를 실행한다. 계획 작성 당시 아래 묶음은 **93 통과, 1 실패**였다. 기존 실패의 테스트 ID는 `test_check_pack_flags_summary_drift`이며 실험01 문제설명 비교 오류에서 멈췄다. 실행 시 Task 1에서 읽은 기준선과 대조한다.

  ```bash
  .venv/bin/python -B -m pytest -p no:cacheprovider -q \
    tests/test_review_pack_note_reading.py \
    tests/test_review_pack_note_metadata.py \
    tests/test_review_pack_note_summary.py \
    tests/test_review_pack_table_layout.py
  ```

- [x] 팩별 SHA-256을 대조해 변경 목록을 확정한다. 허용 대상은 `.html`, 동반 `.md`, 변경된 표 배치·요약, 실험08 설명 SVG와 해당 검증 기록이다. 문제설명·기출/PDF·증거·UI 자산의 바이트, 토픽 ID·읽음 저장 키, 수정 토픽 밖의 article 바이트가 기존과 같은지 확인한다.
- [x] 실제 반영 직전 팩별 `pack_write_lock(folder)` 안에서 Task 1의 원본 해시를 다시 확인한다. 검증된 변경 파일 묶음만 `replace_workbook_files({destination: staged_path, ...}, folder)`로 반영한다. 이 함수는 대상 경로를 받는 기존 교체·복구 함수다. 대상 원본이 도중에 달라졌으면 해당 팩을 다시 대조하고 stage를 갱신한다.
- [x] 실제 반영 경로에서 전체 팩 검사와 파일별 해시 비교를 다시 실행하고 `git diff --check`를 확인한다. 반영 뒤 새 검사 오류가 생기면 해당 팩의 교체 파일을 Task 1 스냅샷에서 복원하고 원인을 확인한 뒤 stage부터 다시 검증한다. 최종 보고에는 수정된 팩과 스킬 경로, 재현한 대표 사례, 기준선 오류를 적는다.
