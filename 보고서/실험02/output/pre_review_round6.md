# 실험02 예비보고서 검토 — round6

최종 전체 리뷰(Opus) Minor 4 반영 확인 라운드. `## 실험 목적` 문단의 "강의노트가
드는 목표 가운데" 표현을 지우고, 그 주에 실제로 하는 목표만 말하도록 고친 뒤 돈다.

## 자동 검사 (scripts/lab/validate.py)

- ✗ error 0건 / ! warn 0건

2단계 — 폴더 규약·`check_item_scope`·`validate_spec`·`check_netlist`·
`check_netlist_circuits`: 문제 없음.

3단계 — 판본 확인: 명세가 적은 교안과 지금 열리는 교안이 일치
(`강의노트/실험2. CMOS 회로의 전기적 특성.pdf`). 인용 쪽(10·11)이 교안 쪽 수(12)
안에 있다. `check_manual_names`: 문제 없음.

4단계 — `check_report_sections`(양식: `.claude/보고서양식.md` 의 `pre`,
`item_count=len(spec.items)`), `check_report_references`, `check_body_style`,
`check_notion_markdown`, `check_report_tables(cells=True)`: 전부 error/warn 없음.
`check_report_references` 는 참고문헌 절 확인, 이하 동일. 유일한 출력은 info 한 줄
— 결선도 PNG 2장을 노션에서 직접 넣어야 한다는 안내(제출 파이프라인 안내이지
결함이 아니다).

4b단계 — `<실험NN>/체크리스트/*.html`·`<실험NN>/output/*.html` 전부(이번엔
`체크리스트.html` 하나) `check_rendered_html`·`check_embedded_images`: 문제 없음.

## 사람이 확인할 것

- 고찰이 본인 경험인가 — 아직 실험 전(예비보고서)이라 해당 없음.
- 교안 회로도와 netlist 위상이 맞는가 — round5 까지 이미 확인됨, 이번 라운드는
  실험 목적 문단만 바꿨으므로 재확인 대상 아님.
- 인용한 쪽(p10·11)의 내용이 명세가 적은 표인가 — round5 까지 확인됨.
- 섹션 제목이 양식과 글자 그대로 같은가 — `check_report_sections` 가 이미 봄, 이상 없음.

## 판정

- [x] 제출 가능
- [ ] 수정 필요
