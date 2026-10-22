# 실험07 조립 순서 분리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 실험07 단계1의 기반 배선을 준비6묶음으로 나누고 기존 기능12단계와 검증·기록을 보존한다.

**Architecture:** v3 netlist에 선택적 조립 표를 추가하고 파서가 기능 단계와 별도로 읽는다. 배치 모듈의 준비 registry를 일괄 그림 사슬에 삽입하며, 체크리스트는 부모 기능 단계 직전에 독립 준비 페이지를 인쇄한다. 기존 입력은 빈 준비 목록으로 기존 동작을 유지한다.

**Tech Stack:** 기존 Python·pytest·Pillow·브레드보드 렌더러, HTML/CSS, Chrome 기반 fit_pages/html_to_pdf. 새 외부 의존성 없음.

**Spec:** `docs/superpowers/specs/2026-10-21-e07-assembly-steps-design.md` (실행자는 이 설계와 계획을 모두 읽는다.)

## Global Constraints

- 준비6 + 기능12 = 18 작업 묶음, 기존 걷기11 포함 총29블록. 준비 PDF6페이지 추가.
- `## 단계` 네 열·숫자/걷기 문법·V1~V12·T1~T3는 유지한다.
- 준비는 전원·발생기 출력이 꺼진 추가 조립만 허용한다. sig/mid 신호선과 출력 급전을 준비로 옮기지 않는다.
- 기존 홀·레일 예약·넷·완성본은 유지한다. 배치 탐색 재실행 및 새로운 위치 선택은 범위 밖이다.
- 기록.md와 사용자 기존 변경은 보존한다. 작성된 기록을 빈 템플릿으로 재파생하지 않는다.
- 인쇄 고정 문구는 해요체이며 `~하세요`를 쓰지 않는다.
- 준비 묶음은 한 페이지이며 기존 페이지 크기 측정 코드를 개편하지 않는다.
- 표 없는 기존 v2/v3는 기존 출력 정책을 유지한다. v2에서 조립 표 사용은 명시적 오류다.
- 구현 시 격리 작업공간은 using-git-worktrees 절차로 준비한다. 현재 작업트리의 데이터시트 문서 변경과 실험07/output/은 가져와 수정하지 않는다.
- 아래 커밋은 실행 시의 논리적 경계다. 계획 작성 턴에는 구현하지 않았고, 후속 Native 구현 요청에 따라 실행했다. 자동 푸시는 하지 않는다.

## Review Focus

1. 표가 없는 기존 실험: 빈 기본값으로 출력과 BOARDS/FINALS 사슬이 바뀌지 않아야 함 — Task1/2/3 회귀 테스트.
2. 부모 단계/순서가 잘못된 표와 registry: 순서 정렬이나 dict 덮어쓰기로 숨기지 않고 오류여야 함 — Task1/2.
3. 최초 생성에서 그림이 아직 없는 경우: 구조 검사는 가능하되 파일 검사를 통과하기 전 정식 PDF를 만들면 안 됨 — Task1/3.
4. 부분 준비의 F/F 입력: 통전 구동 검사를 건너뛰어도 좌표·레일 충돌과 의도치 않은 제거는 잡혀야 함 — Task2/4.
5. 준비 표의 중복 인쇄·잘못된 체크 의미: 준비 페이지에 관측표가 없고 기록 빈칸·기존 절차가 유지되어야 함 — Task3/5.

---

## 파일 구조와 책임

| 파일 | 책임 |
|---|---|
| `scripts/lab/netlist_parser.py` | AssemblyStep 데이터와 선택 표 파싱, 본문에서 표 제거 |
| `scripts/lab/assembly.py` (신규) | 조립 의미·자산/registry 대응 검사. 그림 생성이나 HTML 출력은 하지 않음 |
| `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` | 준비 registry 삽입 순회와 기존 그림 검사 연결 |
| `scripts/lab/render.py` | 준비 블록 HTML, 부모 단계 앞 출력 |
| `.claude/skills/prep-lab-checklist/template.html` | 필요한 준비 전용 스타일만 추가 |
| `보고서/실험07/결선도/배치.py` | 같은 좌표의 기반 작업을6묶음으로 분리 |
| `보고서/실험07/결선도/netlist.md` | 조립 표와 단계1 작업 문장 |
| `docs/schema/lab-netlist-v3.md` 및 v2의 기반 규칙 | 새 선택 계약과 기존 규칙의 적용 범위 |
| `.claude/skills/{draft-lab-spec,breadboard-diagram,prep-lab-checklist}/SKILL.md` | 저작·그림·출력 책임별 지침 |
| `tests/test_lab_assembly_{parser,validation,boards,render}.py` (신규) | 새 경계별 테스트 |
| `tests/test_lab_e07_wiring.py`, `tests/test_breadboard_boards.py` | 실험07 및 기존 registry/저장 그림 집합 회귀 |

현재 `.agents/skills`와 `.claude/skills`의 위 세 SKILL.md는 각각 같은 inode다. 실행 환경에서도 확인하고 실제 정본을 한 번만 수정한다. 복사본이 되었으면 내용을 동기화하되 정본 관계를 임의로 바꾸지 않는다.

## 실행 전 기준선

- [x] 실행용 격리 트리에서 spec·계획과 기존 스킬을 읽고 `git status --short`를 기록한다. 사용자 변경을 reset/stash하지 않는다.
- [x] 변경 전 실험07 그림을 임시 디렉터리에 렌더한다. 기록.md SHA256, 모든 단계와 완성본의 snapshot·넷·좌표·도장 및 PNG를 외부 임시 경로에 보관한다. 반환 자료의 set은 정렬해 비교한다. 이후 같은 환경에서 비교한다.
- [x] `.venv/bin/python -m pytest tests/test_lab_e07_wiring.py tests/test_lab_netlist_parser.py tests/test_lab_observation_validation.py -q`를 실행한다. 실패가 있으면 기존 실패와 작업으로 생긴 실패를 구분해 남긴다.

### Task 1: 조립 표 데이터와 의미·파일 검증

**Files:**
- Modify: `scripts/lab/netlist_parser.py:120` 및 `_parse_section` (`:361`)
- Create: `scripts/lab/assembly.py`
- Modify: `scripts/lab/validate.py`의 `check_netlist_circuits` (`:844`)
- Create/Test: `tests/test_lab_assembly_parser.py`, `tests/test_lab_assembly_validation.py`, `tests/fixtures/netlist_assembly_v3.md`
- Modify: `docs/schema/lab-netlist-v3.md`

**Interfaces:**
- Produces: `AssemblyStep(stage_no: int, order: int, title: str, diagram: str, todo: str, check: str, line: int)` dataclass, `NetlistSection.assembly_steps: list[AssemblyStep] = []`(default_factory).
- Produces: `assembly.steps_for_stage(section: NetlistSection, stage_no: int) -> list[AssemblyStep]` (정렬하지 않고 원문 순서).
- Produces: `assembly.check_structure(netlist: LabNetlist) -> list[Finding]`, `assembly.check_assets(netlist: LabNetlist) -> list[Finding]`.
- Consumes: 기존 `parse_netlist(path)`, `Finding`. 순환 import 방지를 위해 assembly에서 Finding은 함수 내부 import, 타입 주석은 TYPE_CHECKING으로 처리한다.

- [x] **Step 1: 실패 테스트 작성.** `test_parse_six_assembly_rows`는 fixture의 `(stage_no, order)`가 `[(1, i) for i in range(1, 7)]`, 회로 본문에 조립 표가 없고 기존 단계가 유지됨을 단언한다. `test_no_assembly_is_empty_and_v2_rejects_new_table`, `test_bad_headers_empty_cells_duplicate_table_and_nonpositive_numbers`를 추가한다. `test_invalid_parent_order_and_duplicate_keys`는 없는/중복 부모, 중복·역순·빠진 순서를 error로 잡는다. `test_structure_before_assets`는 구조 검사 성공/없는 PNG 또는 JSON의 자산 검사 error를 구분한다.
- [x] **Step 2: 실패 확인.** `.venv/bin/python -m pytest tests/test_lab_assembly_parser.py tests/test_lab_assembly_validation.py -q` 실행. 새 필드/모듈 미구현으로 실패해야 한다.
- [x] **Step 3: 구현.** `_split_assembly_steps(body: str, path: Path, line: int, schema: str) -> tuple[list[AssemblyStep], str]`와 위 인터페이스를 구현한다. 파싱 형식 오류는 NetlistError, 참조·연속성·파일 문제는 Finding(error). `check_netlist_circuits`에는 구조 검사만 연결해 최초 그림 생성 전에 파일 누락으로 막히지 않게 한다. `check_assets`는 실제 PNG·JSON을 읽을 수 있어야 통과한다. 스키마에 생성 후 파일 검사 게이트를 명시한다.
- [x] **Step 4: 통과 확인.** 새 두 파일과 `tests/test_lab_netlist_parser.py tests/test_lab_observation_parser.py tests/test_lab_observation_validation.py`를 pytest로 실행해 모두 통과시킨다.
- [x] **Step 5: 커밋.** 이 task의 명시 파일만 git add하고 staged diff 확인 후 `feat: parse and validate assembly steps`로 커밋한다.

### Task 2: 준비 그림 registry와 누적 기준선

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py:247`
- Modify: `scripts/lab/assembly.py`
- Create/Test: `tests/test_lab_assembly_boards.py`
- Modify/Test: `tests/test_breadboard_boards.py`, `tests/_boards.py` (기존 파일/빌더 열거를 새 helper로 통일하는 데 필요한 부분만)

**Interfaces:**
- Consumes: Task1의 AssemblyStep·steps_for_stage.
- Produces: 주차 선택 필드 `ASSEMBLY_BOARDS: dict[str, list[tuple[str, Callable]]]`, 키는 BOARDS 내 부모 일반 단계 PNG 파일명.
- Produces: 엔진 `iter_procedure_boards(board) -> Iterator[tuple[str, Callable, int | None, bool]]`; 값은 `(filename, builder, stage, is_assembly)`이며 준비는 stage=None. 준비 builder는 `(output_path, template_path=None, baseline=None) -> BreadboardRenderer`를 받는다.
- Produces: `assembly.check_registry(netlist: LabNetlist, registry: dict[str, list[tuple[str, Callable]]]) -> list[Finding]`; 표·부모·준비 파일명/순서의 정확한 일치를 검사한다.

- [x] **Step 1: 실패 테스트 작성.** `test_insert_preparation_before_parent_and_propagate_snapshot`에서 두 준비→부모→걷기→다음 단계 순서와 기준선 전달을 단언한다. `test_empty_registry_preserves_existing_chain`과 `test_final_has_no_preparation_baseline`을 추가한다. `test_registry_rejects_orphan_walk_parent_duplicate_names_and_order_mismatch`는 orphan/걷기 부모·중복 PNG·표 불일치를 잡는다. `test_preparation_rejects_removal_and_new_signal`은 준비에서 제거와 sig/mid를 거절한다.
- [x] **Step 2: 실패 확인.** `.venv/bin/python -m pytest tests/test_lab_assembly_boards.py -q` 실행. helper/검사 미구현으로 실패해야 한다.
- [x] **Step 3: 구현.** build_all이 helper를 사용해 준비를 부모 직전에 그리고 기존 check_board/check_palette 및 파일명 충돌 검사를 적용한다. 정상 준비는 미완성이어도 물리 검사를 생략하지 않는다. 기존 BOARDS·FINALS 계약은 유지한다. 그림 집합·기준선 검사를 수행하는 테스트도 helper로 순회해 새 준비를 빠뜨리지 않게 한다. 표가 없는 보드의 결과는 그대로다.
- [x] **Step 4: 통과 확인.** `.venv/bin/python -m pytest tests/test_lab_assembly_boards.py tests/test_breadboard_boards.py -q`로 기존 board fixture와 전체 주차 registry 회귀를 확인한다.
- [x] **Step 5: 커밋.** task2 명시 파일만 stage하고 `feat: render assembly boards before observation stages`로 커밋한다.

### Task 3: 준비 페이지와 정식 출력 게이트

**Files:**
- Modify: `scripts/lab/render.py:888`, `circuit_pages` (`:1237`)
- Modify: `.claude/skills/prep-lab-checklist/template.html`
- Create/Test: `tests/test_lab_assembly_render.py`
- Modify/Test: `tests/test_lab_fit_pages.py` (기존 wrapper 지원 확인에 한함)

**Interfaces:**
- Consumes: Task1 `steps_for_stage`, `check_assets`; Task2 registry 검사는 제작 절차에서 실행한다.
- Produces: `_assembly_html(step: AssemblyStep, netlist: LabNetlist) -> str` in render.py.
- Keeps: `render_checklist(spec, netlist, template)`의 인자·반환형. 조립 행이 있는 입력에서만 check_assets error가 있으면 ValueError로 정식 HTML/PDF 생성을 차단한다.

- [x] **Step 1: 실패 테스트 작성.** `test_six_preparation_blocks_before_stage_one`은 준비6개→기능1 순서와 기존 기능/걷기 개수 보존을 단언한다. `test_preparation_has_off_banner_and_wiring_check_not_observation`은 고정 문구 `전원과 신호발생기 출력을 꺼요.`, 완료 확인, 관측표·측정 입력칸 부재를 확인한다. `test_missing_or_unreadable_assets_prevents_render`와 `test_plain_v3_and_v2_render_unchanged`를 추가한다. `test_preparation_fit_wrapper_keeps_image_todo_and_check_together`는 기존 fit 측정에 등록되고 요소가 같은 블록에 있음을 검사한다.
- [x] **Step 2: 실패 확인.** `.venv/bin/python -m pytest tests/test_lab_assembly_render.py -q`로 새 출력 부재에 의한 실패를 확인한다.
- [x] **Step 3: 구현.** 기존 `<div class="stage">` wrapper를 준비에도 쓰고 클래스 문자열이나 fit_pages의 정규식을 불필요하게 바꾸지 않는다. 제목은 `단계 1 준비 ① · <제목>`이다. 그림과 사이드카 작업 목록, todo, check를 넣고 관측 노드·V표는 넣지 않는다. 부모 일반 단계 직전에 준비를 출력하며 걷기 참조와 LED 급전 지도를 조립 행 때문에 재계산하지 않는다.
- [x] **Step 4: 통과 확인.** `.venv/bin/python -m pytest tests/test_lab_assembly_render.py tests/test_lab_render.py tests/test_lab_fit_pages.py tests/test_lab_observation_render.py -q` 실행. 기존 입력의 HTML 회귀와 fit 등록을 확인한다.
- [x] **Step 5: 커밋.** task3 파일만 stage하고 `feat: print assembly checks before functional stages`로 커밋한다.

### Task 4: 실험07의 실제 준비6묶음과 배선 보존

**Files:**
- Modify: `보고서/실험07/결선도/배치.py:54`, `보고서/실험07/결선도/netlist.md:235`
- Modify/Test: `tests/test_lab_e07_wiring.py`
- Create/Test: `tests/test_lab_e07_assembly.py`
- Create: `보고서/실험07/결선도/실험07_1_결선도_6bit시프트레지스터_1준비_{1..6}.png` 및 동일 stem `.json`
- Regenerate: 기존 단계1 PNG/JSON (준비 이후 기준선·sidecar 변경). 나머지는 실제 콘텐츠 변경 여부로만 판단한다.

**Interfaces:**
- Consumes: Task1 표·Task2 ASSEMBLY_BOARDS와 순회 helper·Task3 출력.
- Produces: `_build_assembly(output_path, template_path=None, baseline=None, *, assembly_order: int) -> BreadboardRenderer` in 배치.py. registry에는 functools.partial로 order=1..6을 고정한 callable을 넣는다.
- Keeps: build_e7_shift의 기존 호출 인자, BOARDS·FINALS 식별자, 최종 배치·기존 _temporary_plan의 절대 경로.

- [x] **Step 1: 실패 테스트 작성.** `test_e07_has_exactly_six_preparations_for_stage_one`는 spec의6개 제목·순서·파일명을 대조한다. `test_preparations_only_add_foundation_and_never_move_prior_wires`는 연속 snapshot의 기존 경로/부품 보존을 확인한다. `test_stage_one_absolute_board_matches_reference`와 `test_later_stages_and_final_match_reference`는 실행 전 기준선과 넷·홀·절대 경로를 비교한다. 기준선 비교에서 색/강조/부모 단계 설명 변경만 제외하며 실제 핀/부품을 제외하지 않는다. `test_existing_walks_procedures_and_record_unchanged`는 걷기 주소와 V/T 및 기록 해시를 확인한다.
- [x] **Step 2: 실패 확인.** `.venv/bin/python -m pytest tests/test_lab_e07_assembly.py -q` 실행. 새 registry/표 부재로 실패해야 한다.
- [x] **Step 3: 구현.** 설계 표의6묶음을 그대로 적용한다. 원래 전체 기반의 예약 좌표를 사용하고 부분 그림마다 free_rail_row를 다시 돌려 위치를 바꾸지 않는다. 기존 _fixed의 stage/final/superset 동작과 배치 평가용 경로를 보존한다. 마지막 준비까지 D 점퍼·NAND 묶음을 남기고, 원래 단계1이 이를 추가한다. 기존 통전 입력 구동 테스트는 일반 기능 단계에만 적용하고 준비에는 물리·누적 검사를 적용한다. 새 표와 registry는 check_registry로 대조한다.
- [x] **Step 4: 통과 확인.** `.venv/bin/python -m pytest tests/test_lab_e07_assembly.py tests/test_lab_e07_wiring.py tests/test_lab_assembly_boards.py -q` 실행 후 `.venv/bin/python .claude/skills/breadboard-diagram/scripts/render_breadboard.py --experiment 7`로 생성한다. 준비6/기능12/걷기11, 자산 검사 error0을 확인하고 기준선과 완성본을 비교한다.
- [x] **Step 5: 커밋.** task4 명시 파일과 준비6쌍·실제 변경된 단계1쌍만 stage한다. 완성본 및 무관 산출물이 섞이지 않았는지 확인하고 `feat: split experiment seven foundation into six assembly groups`로 커밋한다.

### Task 5: 스킬 규칙·출판 절차와 최종 산출물 검증

**Files:**
- Modify: `.claude/skills/draft-lab-spec/SKILL.md`, `.claude/skills/breadboard-diagram/SKILL.md`, `.claude/skills/prep-lab-checklist/SKILL.md`
- Modify: `docs/schema/lab-netlist-v2.md` (기반 일괄 설치 문구의 후속 확장 안내만)
- Create/Test: `tests/test_lab_assembly_contract_docs.py`
- Regenerate: `보고서/실험07/체크리스트/실험07_Shift_Register_체크리스트.html`, `체크리스트.pdf`
- Create: `docs/verification/2026-10-21-e07-assembly-steps.md`

**Interfaces:**
- Consumes: Tasks1~4의 파싱·구조/자산/registry 검사, 기존 render_checklist/fit_pages/html_to_pdf.
- Produces: 저작→구조 검사→그림 생성→registry/자산 검사→HTML→fit_pages→PDF→화면 검토의 명시 제작 절차. 기존 기록 재파생은 호출하지 않는다.

- [x] **Step 1: 실패 테스트 작성.** `test_skills_define_foundation_workload_and_six_step_pilot`은 기반을 무조건 첫 단계에 몰라는 모순 문구가 없고 역할별 새 계약이 있음을 확인한다. `test_publication_requires_assets_and_preserves_record`는 제작 절차의 자산 검사와 기록 보존을 확인한다. 문서 테스트는 핵심 계약만 고정하고 전체 문장 스냅샷으로 만들지 않는다.
- [x] **Step 2: 실패 확인.** `.venv/bin/python -m pytest tests/test_lab_assembly_contract_docs.py -q` 실행. 이전 스킬 문구 때문에 실패해야 한다.
- [x] **Step 3: 스킬 갱신.** 명세 저작은 분할 원칙·선택 표, 결선도 스킬은 registry·누적/물리 제약, 체크리스트 스킬은 출력 게이트·페이지·통전 의미를 맡긴다. 스키마v3를 정본으로 참조하고 v2 문구는 v2 역사적 규약 범위로 한정한다. 모든 실험에 준비6개를 강제하지 않는다.
- [x] **Step 4: 기능 검증.** 새 assembly 테스트들과 기존 netlist/관측/렌더/fit/보드/배선 관련 테스트를 실행한다. 이후 `.venv/bin/python -m pytest -q` 전체를 한 번 실행해 공용 렌더러 회귀를 확인한다. 실패·skip·warn은 실제 출력대로 기록하고, 새 변경이 없다면 같은 전체 검사를 반복하지 않는다.
- [x] **Step 5: 산출물 생성.** prep-lab-checklist의4/5/6단계로 HTML·fit_pages·PDF를 생성·검증한다. 그 전에 새 구조·registry·자산 검사의 error0을 확인한다. 기록.md 생성/덮어쓰기와 spec 측정값 채우기는 하지 않는다.
- [x] **Step 6: 화면 확인.** 준비6쪽과 단계1·걷기/단계2 연결부, 마지막 기능 단계·기록표를 렌더해 확인한다. 강조선·핀/홀 주소 가독성, 그림/작업/확인의 동일 페이지, LED 물리 순서·출력 급전 부재, 전원 문구를 점검한다. 페이지수는 기준선+6, 총 준비/기능/걷기29블록으로 확인한다. 기록 해시와 기준선 비교, 테스트 결과, 검토 이미지 경로를 verification 문서에 남긴다. 화면 확인이 불가능하면 그 제한을 그대로 보고한다.
- [x] **Step 7: 커밋과 인계.** task5 파일만 stage하고 `git diff --cached --check`, `git diff --cached --stat`, staged 파일 목록을 확인한다. `docs: deliver experiment seven assembly checklist workflow`로 커밋한다. 최종 보고에는 기능12+준비6과 늘어난6페이지, 테스트/화면 검토 결과 및 보존된 기록을 적는다. 자동 푸시·병합은 하지 않는다.

## 계획 자체 검토

- 설계 커버리지: 분할 규칙 Task5, 선택 표/오류 Task1, 그림 기준선 Task2/4, 페이지와 출력 게이트 Task3/5, 실험07 파일·기록 보존 Task4/5에 연결됨.
- 인터페이스: AssemblyStep와 assembly_steps는 Task1, registry와 순회4튜플은 Task2가 정의하며 이후 동일 이름으로 사용함.
- 기존 기능과 준비 구분: 기존 stages에는 준비를 넣지 않아 관측/걷기 검사와 LED feed 계산을 오염시키지 않음.
- 테스트 경계: Review Focus5개를 각 task의 구체 테스트에 연결함.
- 계획 단계에서는 이 문서와 동반 설계 문서만 저장함. 후속 Native 요청으로 직접 구현했고 마지막 독립 리뷰를 진행함.


## 실행 기록

2026-10-21 Native 실행. 상기의 체크는 구현 및 검증 보고서에 근거한 완료 표시다.
Task5 문서 문자열 테스트는 실제 게이트 실행·렌더 결과 검증과 계약 검토로 대체했다.
템플릿과 fit_pages는 기존 래퍼를 그대로 사용하므로 변경할 필요가 없었다.
스킬 크기 상한 때문에 결선도 조립 상세는 `references/assembly.md`로 분리했다.
독립 리뷰에서 찾은 기존 입력의 배치 파일/Pillow 의존 회귀는 실패 재현 후 복구했다.
기존 E05/E06 테스트 실패는 원래 main 대조 결과와 함께 verification 문서에 남겼다.
