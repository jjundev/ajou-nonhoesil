# 실험03 예비보고서 검토 — round3

- 대상: `보고서/실험03/output/실험03_예비보고서.md`
- 명세: `보고서/실험03/체크리스트/명세.md` (항목 4개)
- 조건: round2 와 같다 — 예상 결과 진리표는 강의노트 회로도·Truth Table 의 신호 이름을 그대로 쓴다
- round2 결정 (사용자, 2026-09-14): 선택지 ① "교안 그대로 `A B D B`"

## round2 이후 바뀐 것

| 층 | 무엇을 | 어디 |
|---|---|---|
| 하네스 | 같은 글자가 진리표에서 입력 하나·출력 하나로 갈리면 파서가 받는다. 뒤의 것이 출력이다 | `scripts/lab/spec_parser.py` `_parse_table`·`split_indices` |
| 하네스 | 셀을 이름이 아니라 열 번호로 읽는다 | `validate.check_boolean`·`check_report_tables`(`_col_map`·`_leftover`), `record._truth_table`, `render._truth_table_html` |
| 하네스 | 규칙·계약 문서 | `draft-lab-spec` §5, `docs/schema/lab-spec-v2.md` 「입력과 출력이 같은 글자」 절과 두 표 |
| 테스트 | 새 픽스처 `tests/fixtures/spec_shared_letter.md` 와 테스트 12건. 전체 1128건 중 실패 6건은 작업 전 기준선(1116건)과 같은 6건이다 | `test_lab_spec_parser`·`test_lab_validate`·`test_lab_record`·`test_lab_render` |
| 명세 | T5·T6 머리 `A B D Bo` → `A B D B`, T5 식 `B = A'·B`, T6 `outputs: [D, B]`, 토큰 표·항목 산문 | `체크리스트/명세.md` |
| netlist | 공통 규칙, C3 산문, U2 pin 3 주석, M7·M8 | `결선도/netlist.md` |
| 결선도 | 2-1 LED2 배지 `Bo` → `B`, 머리글·결선 순서 문구. 공통 LED 노트 문구가 바뀌어 12장을 모두 다시 렌더했다 | `render_breadboard.py` E3 빌더 |
| 보고서 | 이론 설명·식, 과정 문단, 표 불릿·머리 `A B D B`, 공통 규칙, 결선 표 `LED2 (B)` | `실험03_예비보고서.md` |

## 자동 검사 (scripts/lab/validate.py)

- ✗ error 0건 / ! warn 0건 / ℹ info 3건

| 단계 | 검사 | 결과 |
|---|---|---|
| 2 | `parse_spec` | 통과. T5 머리 `['A', 'B', 'D', 'B']`, 분할 `(['A', 'B'], ['D', 'B'])` |
| 2 | `check_folder_convention` | finding 없음 |
| 2 | `validate_spec` | ℹ 1건 (새로 나옴, 아래) |
| 2 | `check_netlist` | ℹ 1건 (round1 부터 있던 M8 서술문) |
| 3 | 판본 대조·인용 쪽 범위 | round2 와 같다 (일치, p4~p7) |
| 4 | `check_report_sections` · `check_report_references` · `check_body_style` | finding 없음 |
| 4 | `check_notion_markdown` | ℹ 1건 (노션에 직접 넣을 결선도 PNG 4장) |
| 4 | `check_report_tables` | finding 없음 — 이제 둘째 `B` 를 명세 넷째 열과 맞대서 본다 |
| 4b | `check_rendered_html` / `check_embedded_images` | 대상 HTML 없음 |

새 info:

- ℹ 명세.md:B — 열 `B` 이 표마다 뜻이 다르다 (입력 T1·T2·T3·T4·T5·T6·T7·T8 / 출력 T5·T6)

`check_column_roles` 가 `B` 를 입력이자 출력으로 센 것이다. 교안 표기가 그렇고 명세 머리말
토큰 표에 두 열의 뜻을 밝혔으므로 그대로 둔다. 이 검사가 표를 고치지 말라고 하는 경우가 바로 이것이다.

## 추가 조건 대조 — 강의노트 표기 그대로인가

| 항목 | 강의노트 표 머리 | 보고서 표 머리 | 판정 |
|---|---|---|---|
| 1-1 반가산기 (p4) | 입력 `A B` / 출력 `S C` | `A B S C` | ✓ |
| 1-2 전가산기 (p5) | 입력 `A B Ci` / 출력 `S Co` | `A B Ci S Co` | ✓ |
| 2-1 반감산기 (p6) | 입력 `A B` / 출력 `D B` | `A B D B` | ✓ (round2 ✗ → 고침) |
| 2-2 전감산기 (p7) | 입력 `A B Bi` / 출력 `D Bo` | `A B Bi D Bo` | ✓ |

- 보고서에 남은 `Bo` 는 전부 전감산기(교안 p7 표기)와 LED2 자리 목록 `C·Co·B·Bo` 다.
- 반감산기 표 앞 과정 문단에 "앞의 두 열 A·B가 입력, 뒤의 두 열 D·B가 출력이다" 를
  넣었다. 교안 2단 머리가 하던 구분을 한 줄 머리 표에서 대신한다.
- 결선도 2-1 PNG 를 눈으로 확인했다. LED2 배지 `B`, 머리글 "내림 수 B = A'·B (입력 B 와 같은 글자)".

## 알고 남기는 구멍

- **손그림 H15 는 이름 집합만 본다.** 반감산기 참조 이름이 `{A, B, D}` 로 뭉쳐서, 학생이
  LED2 옆 출력 `B` 를 빠뜨려도 입력 `B` 가 있으면 통과한다. 이름 위치는 판정하지 않는다는
  설계(넷 비교 원칙)의 결과다. 손그림 검토 때 LED2 옆 `B` 는 사람이 본다.

## 사람이 확인할 것

- [ ] **노션 페이지가 옛 판이다.** v1(2026-09-14 11:08 업로드)은 반감산기 표가 `Bo` 다. md 를 다시
  올리거나 노션에서 같은 곳을 고친다. 결선도 2-1 그림도 새 PNG 로 바꾼다.
- [ ] **교안 회로도와 netlist 위상** — round1 부터 넘어온 항목. 이번에 넷은 바꾸지 않았다(이름만 바뀜).

## 판정

- [x] 제출 가능 — 자동 검사 error 0, warn 0. 조건(강의노트 신호 이름 그대로)에 네 표 모두 맞다.
  노션 반영과 위상 최종 서명은 위에 남겼다
- [ ] 수정 필요
