# 핸드오프 — breadboard-diagram 격리 재생성 검증

> 이 문서는 2026-09-12 세션이 낸 핸드오프를 그대로 옮긴 것이다. 짝이 되는 계획은
> `docs/plans/2026-09-12-breadboard-diagram-격리검증-계획.md` 이고, 계획은 이 문서를
> 스펙으로 삼는다. 계획이 핸드오프와 다르게 정한 자리는 계획 쪽 「핸드오프와 다른 결정」
> 절에 근거와 함께 적혀 있다.

## 배경

브랜치 `claude/determined-jepsen-20bb0e` (워크트리 `.claude/worktrees/youthful-mahavira-a9bbf4`,
`main` 에서 분기, 커밋 16개, 작업 트리 깨끗함). 실험01 실험실 기록의 세 교훈을 반영해
결선도·체크리스트 파이프라인을 바꿨다.

* 설계: `docs/plans/2026-09-12-결선도-단계화-슬롯고정-설계.md`
* 구현 계획: `docs/plans/2026-09-12-결선도-단계화-슬롯고정-구현계획.md`
* 핵심 변경: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` (슬롯 고정
  `E1_SLOTS`, 기준선 `baseline`/`snapshot()`/`removed()`, `mark_unused_inputs`, 실험01 빌더
  재작성, `E1_BOARDS` 9장 + `E1_FINALS` 4장), `scripts/lab/{netlist_parser,validate,render}.py`
  (`kind: layout`, `## 단계` 표), 실험01 netlist·PNG 13장·체크리스트, 스킬 문서 5종.
* 결선도 파일명 규칙: `실험NN_<소단원>_결선도_<회로명>[_<k>단계_<이름>].png`
  (breadboard-diagram SKILL 「파일명 규칙」 문단이 정본).
* 테스트: `python -m unittest` → 973 tests, 실패 5·오류 16. 전부 작업 전부터 있던 것
  (`test_lab_config` 13E+2F, `test_lab_html2pdf` 2E, `test_merge_report` 1E,
  `test_skill_docs.test_no_dangling_cross_references [결과]`,
  `test_lab_validate.test_optional_sections_are_not_required`,
  `test_lab_md.test_real_record_file_marks_unfilled_as_none`).

## 이 세션에서 하려던 것

질문: breadboard-diagram SKILL.md 의 규칙(슬롯·기준선·단계·파일명)만 읽은 에이전트가 실험01
결선도 13장을 승인본과 같은 넷으로 다시 그릴 수 있는가. 갈리는 자리 = SKILL.md 에 더 적어야
할 규칙. 실험03 저작 전에 알아야 한다.

breadboard-diagram 에는 격리 검증 스킬이 없다. `verify-draft-lab-spec` 의 틀(답안 제거 →
격리 실행 → 자동 대조 → 사람이 판정)을 그대로 빌린다. 참고:
`.claude/skills/verify-draft-lab-spec/SKILL.md`, `scripts/lab/isolate.py`
(`build_isolated_tree`, `leak_scan`).

## 절차 제안

1. 격리 트리. `git archive HEAD` 사본을 스크래치패드에 푼다(`isolate.build_isolated_tree`
   재사용 가능, KEYS 는 아래로 바꾼다). 뺄 것:
   * `render_breadboard.py` 의 실험01 구간: 주석 `# 실험 1 · 기본 게이트 — 슬롯 고정 배치`
     부터 `build_e1_all` 끝까지 (`E1_SLOTS`·`_S1/_S2/_S3`·`_E1_INPUT_NOTE`·`_e1_frame`·
     `_e1_front`·`_e1_single`·`_e1_two_chip`·`build_e1_*`·`E1_BOARDS`·`E1_FINALS`·
     `_e1_baseline`·`_e1_board`·래퍼 8개). `main()` 의 `choices`/`dispatch` 에서 `e1_*`
     항목도 뺀다. 렌더러 본체·`verify()`·기준선 기능·실험02 빌더는 남긴다.
   * `보고서/실험01/결선도/*.png` 13장, `보고서/실험01/output/손그림검토/`,
     `보고서/실험01/체크리스트/체크리스트.{html,pdf}`,
     `보고서/실험01/실험1_Basic_Gates_예비보고서.pdf`, `보고서/실험01/실험중있었던일.md`.
   * `tests/`(실험01 값을 픽스처로 읽는다), `docs/plans/`, `docs/verify/`,
     `scripts/lab/hand_compare.py`·`hand_transcript.py`·`export_hand_diagrams.py`·
     `contact_sheet.py`(실험01 배치를 안다), `.claude/skills/verify-draft-lab-spec/`,
     `review-hand-diagram/`, `write-pre-report/`, `prep-lab-checklist/`(배치 예시가 있다).
   * 남길 것: breadboard-diagram SKILL.md·`render_breadboard.py`(위 구간 제거본)·
     `.claude/assets/Breadboard.jpg`, `보고서/실험01/결선도/netlist.md`(자리표·단계 표 포함 —
     이것이 입력), `체크리스트/명세.md`, `docs/schema/`, `강의노트/`, `.claude/데이터시트_출처.md`.
   * 누출 grep: `E1_SLOTS`, `_e1_`, `1-1_결선도`, `좌 7행`, `c7→c9`, `a25` 로 트리를 훑는다.
     SKILL.md 의 「슬롯·기준선·단계」 절과 「파일명 규칙」 문단은 계약서라 못 뺀다 — 구조적
     누출로 적고 그 자리의 일치는 합격 근거로 세지 않는다. 주의: SKILL.md §3 회로 ID 목록과
     §4a 에 실험01 슬롯 행 번호(7·18·우 10)와 임시 점퍼 `c7→c9` 가 예시로 적혀 있다. 이것도
     구조적 누출이다.
2. 에이전트 프롬프트 (verify-draft-lab-spec §에이전트 프롬프트 형식을 따르되 요청만 바꾼다):
   ".claude/skills/breadboard-diagram/SKILL.md 를 읽고 그 문서의 규칙대로
   보고서/실험01/결선도/netlist.md 가 기술한 실험1 회로 다섯 개의 빌더와 보드 사슬을
   `render_breadboard.py` 에 작성하고, `--circuit e1_all` 로 `보고서/실험01/결선도/` 에
   렌더하라." 금지 항목(디렉토리 밖 접근·git 이력·전체 테스트)과 보고 형식 7항은 그대로.
   환경 문장은 Windows 기준(`python`, Poppler PATH). 사유·합격 조건은 쓰지 않는다.
3. 대조. 저장소(승인본) 쪽에서:
   * 넷 대조: `scripts/lab/hand_compare.py` 의 `_from_wiring(bb.wiring(), cid)` 로 승인본
     빌더와 재생성 빌더의 `Diagram` 을 만들고 `compare(ref, hand)` 를 회로 5개 + 단계 8개에
     돌린다. 재생성 모듈은 `importlib` 로 격리 트리의 `render_breadboard.py` 를 따로 로드한다.
     H1~H14 규칙 의미는 review-hand-diagram/SKILL.md 표 참조. 홀 좌표가 달라도 넷이 같으면 통과.
   * 자리표: 재생성 `E1_SLOTS`(이름이 달라도 됨 — 빌더의 `wiring()['chips']` 자리)가 netlist
     `kind: layout` 표와 같은가.
   * 전환 수치: 보드 사슬을 돌며 `len(bb.steps)`·`len(bb.kept)`·`len(bb.removed())` 를
     승인본과 나란히 표로. 승인본 값은 설계 문서 §슬롯과 단계 표(C1 16 · C2 0+칩교체 ·
     C3-1 3 · C3-2 4 · C4-1 1 · C4-2 4 · C5-1 8/8 · C5-2 4/1 · C5-3 11/0).
   * 파일명 13개가 규칙과 맞는가.
   * `verify()` 첫 실행 통과 여부와 되돌린 횟수(에이전트 보고 3항).
4. 판정. 갈린 자리마다 "규칙이 없었는가, 있는데 안 읽혔는가" 를 가른다. 결과를
   `tmp/verify-artifacts/실험01-breadboard-격리-<날짜>/판정.md` 로. SKILL.md 를 고치는 것은
   판정 뒤 사용자 결정.

## 함정

* 폰트: 렌더러는 이제 Windows 폰트 폴백이 있다(`FONT_CANDIDATES`). macOS 경로 하드코딩은
  사라졌다.
* `python3` 는 이 머신에서 Microsoft Store 스텁이다. `python` 을 쓴다.
* `verify()` R1~R6 는 엄격하다. 에이전트가 좌표를 옮기며 검사를 통과시키는 과정 자체가 관찰
  대상이다(SKILL §5 "최소 패치는 증상을 건드리고 원인을 남긴다").
* 기준선이 회색이 되려면 공통 배선을 같은 헬퍼·같은 순서로 그려야 한다(`free_rail_row` 가
  점유 순서로 레일 행을 고른다). 에이전트가 이 규칙을 놓치면 전환 그림에 새 배선이 잔뜩
  생긴다 — 그것도 판정 대상.
* `tests/test_breadboard_wiring.py::test_빌더_칩_자리가_netlist_자리표와_같다` 와
  `test_breadboard_diagram_cli.py` 가 승인본 빌더 구조를 단언한다. 재생성본에는 돌리지 말고
  대조 스크립트로만 본다.

## 미결·기타

* 이 세션의 verify-draft-lab-spec 격리 에이전트가 백그라운드에서 돌고 있었다(draft-lab-spec
  의 netlist 규칙 넷을 잰다). 결과는 이 세션에서 받는다. 그 검증과 이 검증은 별개다.
* 브랜치 처리(`main` 머지 · PR · 유지)는 아직 미정.
* 미룬 사소한 항목 22건 중 눈에 띄는 것: 손그림 픽스처
  `tests/fixtures/hand_e1_nand_chip_up_one.json` 재생성 스크립트가 커밋되지 않음,
  `render_breadboard.py` 가 2,160줄이라 실험03 전에 주차별 빌더 모듈 분리 검토,
  `docs/verify/draft-lab-spec.md` 런북에 이번 회차 행 미기록.
