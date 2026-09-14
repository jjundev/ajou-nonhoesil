# 실험03 예비보고서 검토 — round4

- 대상: `보고서/실험03/output/실험03_예비보고서.md`
- 명세: `보고서/실험03/체크리스트/명세.md` (항목 4개 — E3.P1-2 T3·T4, E3.P2-2 T7·T8)
- 조건: round3 이후 조교 공지 `_350547_1`(2026-09-14) — 실험3 은 1-2 전가산기·2-2
  전감산기만 하고 1-1 반가산기·2-1 반감산기는 실험에서 뺀다. Task 3 이 명세·netlist·PNG 를
  이미 이 범위로 줄였고, 이번 round4 는 그 아래에서 손으로 줄인 예비보고서를 검증한다.

## round3 이후 바뀐 것

| 층 | 무엇을 | 어디 |
|---|---|---|
| 명세 | E3.P1-1·E3.P2-1 삭제, 남은 항목 재번호 | `체크리스트/명세.md` (Task 3, 이전 커밋) |
| netlist | C2(전가산기, 2단계) → C4(전감산기, 1단계) 사슬로 재작성, 옛 반가산기·반감산기 PNG 삭제 | `결선도/netlist.md`, PNG (Task 3, 이전 커밋) |
| 스킬 | out-of-scope 하위실험은 과정·예상 결과·결선도에 안 쓴다. 이론에서 구성요소로만(식만, 진리표·과정 없음) 설명 | `write-pre-report/SKILL.md` §절대 규칙 16 (Task 5, 이전 커밋) |
| 보고서 | 목적 둘째 문단, 이론 반가산기·반감산기 마지막 문단, 부품 표 3행·문단, 과정 1-1·2-1 소절 삭제·1-2·2-2 문단, 결선 공통 규칙 3불릿·1-1·2-1 결선 소절 삭제·확인사항 3항목 | `실험03_예비보고서.md` (이번 round) |

## 자동 검사 (scripts/lab/validate.py)

- ✗ error 0건 / ! warn 0건 / ℹ info 2건

| 단계 | 검사 | 결과 |
|---|---|---|
| 2 | `parse_spec` | 통과 |
| 2 | `check_folder_convention` | finding 없음 |
| 2 | `check_item_scope` | finding 없음 |
| 2 | `validate_spec` | finding 없음 |
| 2 | `check_netlist` | finding 없음 |
| 2 | `check_netlist_circuits` | ℹ 1건 (netlist.md:262, M8 — round1 부터 있던 서술문. netlist.md 는 이번 태스크에서 건드리지 않는다) |
| 3 | 판본 대조 | 일치 (`강의노트/실험3. 가산기 & 감산기 (25.03.25 수정).pdf`) |
| 3 | 인용 쪽 범위 | 교안 9쪽 / 인용 [5, 7] — 범위 안 |
| 3 | `check_manual_names` | finding 없음 |
| 4 | `check_report_sections` | finding 없음 (item_count=4) |
| 4 | `check_report_references` | finding 없음 |
| 4 | `check_body_style` | finding 없음 |
| 4 | `check_notion_markdown` | ℹ 1건 (노션에 직접 넣을 결선도 PNG 2장: `실험03_1-2_결선도_전가산기.png`, `실험03_2-2_결선도_전감산기.png`) |
| 4 | `check_report_tables` | finding 없음 (cells=True) |
| 4b | `check_rendered_html` / `check_embedded_images` | 대상 HTML 없음 |

## 기계 검사 (브리프 Step 7 grep)

```
grep -nE "실험 1-1|실험 2-1|네 회로|반가산기 결선|반감산기 결선|전원만 물려|C·Co·B·Bo" 실험03_예비보고서.md
```

아무것도 걸리지 않았다(exit 1). 이론의 `## 반가산기`·`## 반감산기` 헤딩은 이 패턴에 걸리지
않는다 — 예상대로다.

## 사람이 확인할 것

- [ ] **교안 회로도와 netlist 위상** — round1 부터 넘어온 항목. netlist 는 Task 3 이 이미
  C4 사슬로 다시 그렸고 이번 태스크에서는 건드리지 않았다.
- [ ] **노션 페이지 반영** — 이 라운드는 Notion 을 읽기만 했다(v2 되읽기, diff 0). 트리밍한
  본문을 노션에 올리는 것은 Task 9 의 몫이다.
- [x] 이론 `## 반가산기`·`## 반감산기` 는 구성요소 설명(식만)으로 남았고 진리표·과정
  절은 없다 — §절대 규칙 16 조건에 맞는다.
- [x] "이번에는 하지 않는다"류 문장, 삭제된 PNG 참조, "네 회로" 잔존 카운트 없음(자체
  top-to-bottom 재독).

## 판정

- [x] 제출 가능 — 자동 검사 error 0, warn 0. 기계 검사 grep 도 깨끗하다.
- [ ] 수정 필요
