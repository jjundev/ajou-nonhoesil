# 실험02 예비보고서 검토 — round5

- 대상: `보고서/실험02/output/실험02_예비보고서.md` (조교 공지 `_350547_1` 로 소실험 범위를 실험 1-1·1-2 로 줄인 손수정본)
- 명세: `보고서/실험02/체크리스트/명세.md` (Task 2 에서 E2.P2 를 뺐다 — 항목 2개, T1·T2)
- 조건: round4 이후 실험 2(CMOS AC 특성 — tpd·1MHz 사각파·인버터 체인)를 실험 목적·이론·부품·과정·결선도에서 전부 뺐다

## round4 이후 바뀐 것

| 절 | 무엇을 |
|---|---|
| 실험 목적 | 목표 네 가지(논리 레벨·슈미트 트리거·DC 특성·DC·AC·스위칭 특성) → 세 가지(논리 레벨·슈미트 트리거·DC 특성). "마지막으로 …tpd…" 문장 삭제 |
| 실험 이론 | `## CMOS 인버터의 구조` 둘째 문단에서 부하 커패시턴스·전달 지연 언급을 출력 전압 강하 설명으로 교체. `## 전달 지연` 소절 전체 삭제 |
| 실험 부품 | 오실로스코프·함수발생기·74HC04 세 행의 비고에서 실험 2 관련 문구 제거. 74HC04 수량은 강의노트 준비물 그대로 2 유지 |
| 실험 과정 및 예상 결과 | `## 실험 2) CMOS의 AC 특성 확인` 소절(측정 절차·T3 측정표·데이터시트 tpd 표) 전체 삭제. 1-1·1-2 두 소절만 남는다 |
| 회로 결선도 | 공통 결선 규칙의 "세 회로" → "두 회로"로, 실험 2 관련 배선 절차 삭제. `## 실험 2) CMOS의 AC 특성 확인 결선` 소절(그림·결선표) 전체 삭제. 실험 전 확인할 사항에서 실험 2 전용 불릿 3개(사각파 offset, 단 수 세기, 체인 방향) 삭제 — 남은 불릿 3개(Vpp 확인, 칩 각인, X-Y 모드 경로) |

## 자동 검사 (scripts/lab/validate.py)

- ✗ error 0건 / ! warn 0건 / ℹ info 1건

| 단계 | 검사 | 결과 |
|---|---|---|
| 2 | `check_folder_convention` · `check_item_scope` · `validate_spec` · `check_netlist` · `check_netlist_circuits` | finding 없음 |
| 3 | 판본 대조(`명세.md` source_manual == 지금 열리는 교안) | 일치. 인용 쪽 10·11 / 교안 12쪽 — 범위 안. `check_manual_names` finding 없음 |
| 4 | `check_report_sections` (item_count=2) | finding 없음 |
| 4 | `check_report_references` | finding 없음 — 74HC04·74HC14 데이터시트만 남았고 둘 다 회로가 실제로 쓴다 |
| 4 | `check_body_style` | finding 없음 |
| 4 | `check_notion_markdown` | ℹ 1건 — 노션에서 직접 넣어야 할 그림 2장(1-1·1-2 결선도). 실험 2 결선도 PNG 는 더 이상 참조되지 않는다 |
| 4 | `check_report_tables` (cells=True) | finding 없음 — 남은 T1·T2 는 명세 표 머리와 그대로 대조된다 |
| 4b | HTML(`체크리스트/`·`output/`) | 대상 파일 없음 |

## 사람이 확인할 것

- 고찰이 본인 경험인가 — 예비보고서라 해당 없음(고찰 절 없음)
- 교안 회로도와 netlist 위상 일치 — 이번 라운드에서 새로 안 봤다(Task 2 에서 이미 확인된 범위이고, 이번 트림은 netlist.md 를 건드리지 않았다)
- 인용 쪽(p10·p11) 내용이 명세가 적은 표인가 — vision 재대조는 하지 않았다. Task 2·round3·4 에서 이미 확인된 인용이고 이번 트림이 T1·T2 자체를 바꾸지 않았다
- 표기 R5·R6(보수 `'`, 오버바 승격 범위) — `check_body_style`·`check_notion_markdown` 이 관련 항목을 finding 없음으로 통과, 본문에 보수 표기 자체가 없다
- 섹션 제목이 `.claude/보고서양식.md` 와 글자 그대로 같은가 — `check_report_sections` 가 정확 일치로 통과

## 알고 남기는 구멍

- round4 와 같다 — `check_report_tables` 는 `kind: truth-table` 만 본다. 이번 트림으로 표 자체가 줄었으므로(T3·데이터시트 tpd 표 삭제) 해당 구멍의 영향 범위도 같이 줄었다.
- 실험02 는 여전히 손그림 검토 회로 목록(`hand_compare.CIRCUITS`)에 없다. 이번 작업 범위 밖이다.

## 판정

- [x] 제출 가능 — 자동 검사 error 0, warn 0. 손 트림 뒤에도 섹션·표·참고문헌·문체 검사가 전부 통과한다
- [ ] 수정 필요
