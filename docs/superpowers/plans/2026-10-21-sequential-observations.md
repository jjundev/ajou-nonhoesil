# Sequential Observations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공통 결선도 도구에서 순차회로의 관측점과 순서 있는 확인 절차를 검증하고, 배선 단계 안에 핀·조작·저작한 기대값·LED 안내를 인쇄한다.

**Architecture:** 관측점 등록과 부울식 계산을 분리한다. 기존 v2 계산 경로를 보존하고, v3에서 expression/observed 노드와 명시적인 확인 절차를 추가한다. 순차 기대값은 교안 근거로 저작한 데이터이며, 회로 시뮬레이션으로 계산한 값으로 취급하지 않는다.

**Tech Stack:** 기존 Python 3, dataclasses, 표준 라이브러리 Markdown 부분집합 파서, pytest, 기존 checklist HTML·Chrome PDF 파이프라인. 새 런타임 의존성 없음.

**Spec:** 이 문서의 [확정 설계](#확정-설계). 2026-10-21 grill-yourself 설계와 사용자의 `B로 하자` 결정을 실행에 필요한 계약으로 구체화했다. 별도 설계 파일 없이 이 문서에 함께 보존한다.

## Global Constraints

- 선택 B: 저작한 순차 확인 절차를 검증·인쇄한다. 범용 순차회로 시뮬레이터와 기대값 자동 추론은 포함하지 않는다.
- 새 기능은 `lab-netlist/v3`; 기존 `lab-netlist/v2`를 계속 읽는다. `lab-spec/v2`와 기존 기록표 계약은 변경하지 않는다.
- 기존 조합회로의 부울식 계산, v2 렌더링 결과, 기록표의 행·셀·확인 칸·사진 파일명 계약을 보존한다.
- 기존 실험01·02의 레거시 예외와 실험03 이후 단계 검증을 유지한다. 새 기능 때문에 걷기 문법·주소 대조·신호선 예산을 완화하지 않는다.
- 관측점 이름·핀은 한 번 정의한다. 단계와 LED는 그 정의를 조회하며 핀을 중복 저작하지 않는다.
- 확인 절차와 실측 기록표는 별개다. 절차의 기대값을 `명세.md`나 `기록.md`의 측정 빈칸에 채우지 않는다.
- 각 확인 절차는 자체 준비·초기화 설명을 포함한다. 앞 배선 단계에서 우연히 남은 상태를 암묵적으로 이어받지 않는다.
- 파일·핀·출처를 구조적으로 검증했다고 논리 기대값이나 물리 배선이 증명됐다고 보고하지 않는다.
- 실험07 실물 배치·PNG 제작·실험06 승인본 교체·보고서 재생성은 이번 구현 범위 밖이다. 실험06·07 사례는 격리된 fixture로 검증한다.
- 기존 산출물·작성 중 기록·사용자 변경은 덮어쓰지 않는다. 계획 작성 시 실험07 보고서 및 learning-pack-source 폴더가 untracked이므로 구현 시작 때 상태를 다시 확인한다.
- `.agents/skills`와 `.claude/skills`의 대상 SKILL.md는 현재 같은 파일이다(`samefile=True`). 실행 때 재확인하고 동일 실체는 한 번만 수정한다.
- 사용자 요청 없이 커밋·푸시하지 않는다. 각 Task는 독립 검토 및 선택적 커밋 경계다. 구현 시작 시 using-git-worktrees로 격리 여부를 결정한다.

## Review Focus

1. 같은 입력이 반복되지만 상태가 다른 절차: 행의 순서·중복을 보존한다(Task 1/2).
2. 빈 기대값·미정·관측 안 함: 서로 구분하고 출력 0 또는 소등으로 표시하지 않는다(Task 2/4).
3. 유지·반전과 비트값이 서로 다른 LED에 함께 있는 행: LED별 상태를 잃지 않고 극성을 정확히 적용한다(Task 4).
4. 마지막 배선 단계·프로브 관측·앞 회로에서 이어받은 LED: 명시적으로 참조한 절차는 빠뜨리지 않고, 절차에 없는 기대값을 만들어 넣지 않는다(Task 3/4).
5. v2 승인본 및 채워진 기록과 공존: 새 계약의 도입만으로 기존 파일이나 기록표 결과를 바꾸지 않는다(Task 1/5/6).

---

## 확정 설계

### 1. 버전과 노드

새 파서는 v2/v3를 모두 받는다. `LabNetlist.schema: str = 'lab-netlist/v2'`를 dataclass 끝의 기본 필드로 추가해 기존 positional 호출을 보존한다. 알 수 없는 버전은 지금처럼 `NetlistError`다. v3 문서를 v2라고 표기하거나 v2에 새 문법을 넣으면 명확히 거절한다.

v2 `## 노드`의 세 열과 기존 node dict 모양은 그대로 둔다. v3는 다음 네 열을 사용한다.

```markdown
## 노드

| 노드 | 유형 | 식 | 핀 |
|---|---|---|---|
| SERIAL DATA 보수 | expression | SERIAL_DATA' | U1 pin 11 |
| BIT1 | observed | - | U2 pin 15 |
```

v3 정규형은 `{name: str, kind: 'expression'|'observed', expr: str|None, pin: str}`다. `expression`은 비어 있지 않은 식, `observed`는 원문 `-`만 허용하고 내부에서 None으로 만든다. v2의 kind 생략은 expression으로 해석하되 기존 dict에 필드를 억지로 추가하지 않는다. 관측점 조회는 양쪽 노드를 모두 보고 부울식 계산은 expression만 본다. v3에서 같은 이름·같은 물리 핀을 중복 등록하는 것은 오류다.

계산 가능한 식이라는 이유만으로 observed 절차를 우회하지 않는다. 단계가 절차를 명시하면 절차가 우선이다. 절차 없는 observed 관측 단계는 오류이고, expression 관측 단계는 기존 계산 경로를 쓸 수 있다. 이때 실제로 expression을 계산해야 할 때만 truth-table 기록표 존재를 요구한다.

### 2. 확인 절차 문법

각 회로 내부 `## 확인 절차 V<n> · <제목>` 아래 속성과 표를 둔다. ID는 회로 안에서 유일한 `V[1-9][0-9]*`이며 다른 회로의 절차를 참조하지 않는다. 새 절을 파서가 본문에서 제거해 칩 배선·참조표로 중복 인쇄하지 않는다.

```markdown
## 확인 절차 V1 · BIT1 초기화 및 입력 확인

- source: manual:p9
- provenance: derived
- rationale: p8~10의 초기화·직렬 입력 동작을 부분 배선 확인 순서로 구체화했다.
- setup: CLK을 0에 정지하고 PR1을 1에 둔 뒤 첫 행의 CLR 초기화부터 수행한다.
- encoding: 0/1
- inputs: [SERIAL_DATA, CLK, CLR, PR1]
- clocks: [CLK]
- observe: [BIT1]

| 순서 | 조작 | SERIAL_DATA | CLK | CLR | PR1 | BIT1 |
|---|---|---|---|---|---|---|
| 1 | 초기화 | 0 | 0 | 0 | 1 | 0 |
| 2 | CLR 해제 | 0 | 0 | 1 | 1 | 0 |
| 3 | 데이터 설정 | 1 | 0 | 1 | 1 | 0 |
| 4 | 클럭 상승 | 1 | 0->1 | 1 | 1 | 0 |
| 5 | 클럭 하강 | 1 | 1->0 | 1 | 1 | 1 |
```

이 예시는 **계약 설명용**이다. 실제 부분 배선의 입력·노드·조작은 교안과 배선 상태를 근거로 별도 저작한다.

- 필수 속성은 source/provenance/setup/encoding/inputs/observe다. provenance는 manual 또는 derived. derived이면 rationale도 필수다. clocks는 생략 시 빈 목록이다.
- source는 v1 범위에서 `manual:p<양의 정수>` 한 곳을 대표 근거로 명시하며 나머지 쪽과 유도 이유는 rationale에 적는다. 인용 쪽이 실제 `spec.source_manual`의 범위 안인지 확인한다. 출처 확인은 내용 전사의 증명이 아니다.
- encoding은 0/1 또는 H/L. 입력·기대 비트는 그 표기를 보존한다. 에지 토큰은 기존 규약처럼 `0->1`, `1->0`이며 clocks로 선언한 입력에만 허용한다.
- 표 머리는 정확히 `순서`, `조작`, inputs 순서, observe 순서다. 이름은 중복 없이 두 목록이 서로 겹치지 않는다. 순서는 1부터 연속 정수, 조작은 비어 있지 않아야 한다.
- 모든 입력 셀은 명시한다. 빈칸·X·앞 행 값 자동 이월은 허용하지 않는다. 각 clock의 첫 행은 레벨이고 이후 에지는 직전 레벨과 시작값이 일치해야 한다. bare level의 변경으로 숨은 에지를 만들지 않는다. 이 검사는 clock 궤적만 보며 칩 상태를 시뮬레이션하지 않는다.
- 기대 셀은 해당 encoding의 비트, `유지`, `반전`, `미정`, `관측 안 함` 중 하나다. 빈칸은 오류다. `미정`은 예측을 못 한다는 뜻, `관측 안 함`은 그 행에서 확인하지 않는다는 뜻이다.
- `유지`·`반전`은 같은 절차에서 그 노드를 앞서 관측한 행이 있어야 한다. 둘 다 논리값에 대한 관계이며 알려진 비트로 자동 환산하지 않는다. 첫 행부터 이전 상태를 가정할 수 없도록 한다.
- 단계의 주 관측 노드는 해당 절차 observe에 있고, 적어도 한 행에서 0/1(H/L) 또는 유지/반전으로 확인 가능해야 한다. 전 행 미정/관측 안 함인 절차는 단계 확인으로 쓸 수 없다.
- inputs는 조작 이름이며 실제 입력 위치는 기존 보드 sidecar로 조회한다. 존재하지 않는 입력 위치·아직 연결되지 않은 관측 LED는 기존 정책에 따라 식별 가능한 경고다. 준비·초기화의 물리적 충분성은 저작/시각 검토 항목으로 남는다.

### 3. 단계 참조와 인쇄

기존 단계표 네 열을 유지한다. v3의 확인 셀 문법은 `노드 \`BIT1\` · 절차 \`V1\` — <관측 설명>`이다. 파서는 여기에 `procedure: str|None`을 추가하며 v2 단계 dict는 기존 키/값을 유지한다. 걷기 행에 절차 참조를 붙이면 오류다. `절차`를 썼지만 ID가 깨진 경우 일반 산문으로 조용히 처리하지 않는다.

새 절차는 단계 안에 다음 순서로 인쇄한다: 확인 노드·핀 → 준비 설명 → 출처 및 전사/유도 구분 → 조작·입력·예상·확인 표. derived 절차에는 **`교안 원문이 아니다 — 교안에서 유도한 확인 절차`**를 그 자리에 표시한다. 마지막 단계도 명시적 절차를 생략하지 않는다.

논리 기대값과 LED 점등은 별개로 취급한다. 알려진 비트만 `leds.lit(bit, active_low)`로 점등을 계산한다. 유지/반전은 각 LED에 `직전 그대로`/`직전과 반대`, 미정은 `미정`, 관측 안 함 또는 해당 절차에 없는 누적 LED는 `이번 절차 관측 안 함`으로 표시한다. 소등 열에 미정 LED를 섞지 않는다. 서로 다른 LED의 상태를 하나의 유지 문구로 합치지 않는다. 프로브로 보는 노드도 LED 존재와 무관하게 절차를 인쇄한다.

v2의 HTML은 그대로 보존한다. v3의 절차 표는 `td.box`를 쓰고 기록표의 `td.check`·빈 기록 셀 수를 늘리지 않는다. 입력이 많은 순차 절차는 조작+입력 영역과 관측 결과 영역을 동일 행 순서를 유지해 배치한다. 입력 이름·비트열을 잘라 내거나 글씨를 축소해 숨기지 않는다. 현재 체크리스트 폭 210mm와 `fit_pages`의 페이지 높이 조정을 사용하며 A4라고 가정하지 않는다.

### 4. 공통 인터페이스

`scripts/lab/netlist_parser.py`에 다음 구조를 추가한다. 기존 모든 필드 뒤 기본값으로 추가한다.

- `ObservationStep(order: int, action: str, inputs: list[str], expected: list[str], line: int)`.
- `ObservationProcedure(id: str, title: str, source: str, provenance: str, rationale: str, setup: str, encoding: str, inputs: list[str], clocks: list[str], observe: list[str], steps: list[ObservationStep], line: int)`.
- `NetlistSection.procedures: list[ObservationProcedure] = field(default_factory=list)`.

새 `scripts/lab/observations.py`는 parser 객체를 소비하는 의미 검증·기대값 어댑터다. parser가 이 모듈을 역으로 import하지 않는다.

- `ObservationError(ValueError)`.
- `point_kind(node: dict) -> str`: v2의 kind 생략을 expression으로 해석.
- `points(section) -> dict[str, dict]`: 전체 관측점의 이름/핀 조회. 중복은 오류.
- `procedure_for_stage(section, stage: dict) -> ObservationProcedure | None`: 해당 회로의 절차 참조 조회.
- `procedure_issues(section, procedure: ObservationProcedure) -> list[tuple[int, str]]`: 줄번호와 메시지. 시퀀스·셀·참조 의미 오류를 모아서 반환.
- `ObservationRow(order: int|None, action: str, inputs: list[str], expected: list[str])`.
- `ObservationTable(inputs: list[str], points: list[tuple[str, str]], rows: list[ObservationRow], encoding: str, provenance: str, source: str, setup: str, rationale: str)`.
- `stage_observations(section, spec, stage: dict, node_names: list[str]) -> ObservationTable`: 절차가 있으면 저작 행을 그대로 반환하고, 없으면 기존 `nodes.stage_nodes_table` 결과를 변환한다. 요청한 노드에 절차의 예상 열이 없으면 `관측 안 함`을 반환한다. 기존 계산 경로의 provenance는 computed다. 계산을 요청한 observed 노드는 오류다.

기존 `nodes.py`의 공개 함수 시그니처는 바꾸지 않는다. 계산할 때 observed를 걸러내고 expression의 원래 검산을 유지한다. renderer의 v2 경로도 유지한다. 공통 관측점 조회와 새 v3 절차 경로가 observations를 사용하며 기존 계산기를 새 상태 엔진으로 바꾸지 않는다.

## 파일 구성

| 파일 | 책임 |
|---|---|
| `scripts/lab/netlist_parser.py` | v2/v3 구조 파싱, 절차 모델, 단계 참조 |
| 새 `scripts/lab/observations.py` | 관측점 조회, 절차 의미 검사, 기대값 어댑터 |
| `scripts/lab/nodes.py` | expression 계산 및 기존 진리표 검산 유지 |
| `scripts/lab/validate.py` | 기존 Finding 형식으로 유형·절차·출처·보드 위치 검사 연결 |
| `scripts/lab/leds.py` | 두 유형의 관측점 조회, 기존 LED 급전/극성 유지 |
| `scripts/lab/render.py` | v3 절차 블록과 LED별 상태 표현, 기존 v2 렌더 보존 |
| `.claude/skills/prep-lab-checklist/template.html` | 새 절차 표의 인쇄 스타일만 추가 |
| 새 `docs/schema/lab-netlist-v3.md` | 새 문법/검증 계약 |
| 기존 v2 스키마·draft/prep 스킬 | 지원 버전 안내와 유형별 저작/인쇄 규칙 |
| 새 observation 테스트·fixture | v3 파싱, 순차 절차, 렌더, 호환성 증거 |

## 실행 전 기준선

- [ ] 구현을 요청받은 뒤 작업트리/브랜치와 현재 변경을 확인한다. 이번 계획 파일과 사용자 작업을 구현 diff와 구분한다.
- [ ] 첫 runtime 수정 전에 기존 테스트 fixture를 같은 경로·환경에서 렌더한 v2 HTML 기준선과 기존 record 결과를 고유 tmp 폴더에 저장한다. Task 4/5에서 같은 fixture의 결과와 비교한다. 기준선 생성 명령·대상 fixture·해시를 검증 기록에 남긴다.
- [ ] 기존 관련 테스트를 실행해 현재 실패가 있으면 기록한다. 구현 후의 실패를 사전 문제라고 추정하지 않는다. 기존 저장 PNG와 다른 환경의 재렌더 바이트 차이를 곧바로 회귀로 판정하지 않는다.

## Task 1: v3 구조를 읽고 v2를 보존하는 파서

**Files:** Modify `scripts/lab/netlist_parser.py:87-116,195-224,272-325`; create `tests/test_lab_observation_parser.py`, `tests/fixtures/netlist_observation_v3.md`, `tests/fixtures/spec_observation_stepped.md`, `docs/schema/lab-netlist-v3.md`; extend `tests/test_lab_netlist_parser.py`.

**Interfaces:** Consumes 기존 Markdown 표/속성 파서. Produces 위 ObservationStep/ObservationProcedure/NetlistSection.procedures/LabNetlist.schema와 v3 node dict 및 단계 procedure 참조. 파서가 구조 오류를 NetlistError로 내며 의미 오류는 Task 2/3이 처리한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_v3_parses_observed_and_expression_nodes`는 observed.expr is None, expression.expr == "SERIAL_DATA'"를 검사한다. `test_procedure_keeps_duplicate_input_rows_in_order`는 입력이 같고 출력이 다른 행이 두 개 모두 원래 순서로 남음을 검사한다. `test_v3_stage_resolves_procedure_syntax`는 BIT1/V1을 각각 추출한다.

  핵심 assertion은 `assert observed['expr'] is None`, `assert expression['expr'] == "SERIAL_DATA'"`, `assert stage['node'] == 'BIT1'`, `assert stage['procedure'] == 'V1'`이다. 여기서 각 객체는 위 새 fixture를 parse_netlist로 읽어 찾는다.
- [ ] **Step 2: 거절/보존 테스트 작성.** `test_v2_parse_shape_is_unchanged`는 기존 node/stage dict와 동일, schema만 기본 v2임을 검사한다. `test_rejects_new_syntax_under_v2`, `test_rejects_duplicate_procedure_ids`, `test_rejects_wrong_node_or_procedure_headers`, `test_rejects_ragged_procedure_rows`, `test_rejects_malformed_procedure_reference`, `test_procedure_is_removed_from_circuit_body`를 추가한다. 기존 `2걷기`·`03걷기` 파싱도 그대로다.
- [ ] **Step 3: RED 확인.** `.venv/bin/python -m pytest -n0 tests/test_lab_observation_parser.py tests/test_lab_netlist_parser.py -q`. 새 v3 미지원 때문에 실패하는지 확인한다.
- [ ] **Step 4: 최소 파서 및 문법 문서 구현.** 위 확정 설계의 정확한 열·속성·ID·정규형을 구현한다. nodes/절차/단계는 같은 회로 범위에서 처리하고 본문 중복 인쇄를 방지한다. v2 노드 dict 변경 금지.
- [ ] **Step 5: GREEN 및 변경 범위 검토.** Step 3 명령이 통과해야 한다. runtime 코드·스키마·fixture·테스트만 해당 Task의 diff에 있는지 확인한다. 커밋은 요청된 경우에만 이 경계로 한다.

## Task 2: 시뮬레이션 없는 절차 의미 검사와 기대값 어댑터

**Files:** Create `scripts/lab/observations.py`, `tests/test_lab_observations.py`; modify `scripts/lab/nodes.py:50-109`; extend `tests/test_lab_nodes.py`.

**Interfaces:** Consumes Task 1 모델과 기존 `nodes.stage_nodes_table`. Produces 확정 설계의 observations 공개 인터페이스. 이 Task는 Finding이나 HTML을 생성하지 않는다.

- [ ] **Step 1: 실패 테스트 작성.** `test_authored_procedure_does_not_require_truth_table`는 stepped 명세만으로 행을 그대로 반환함을 검사한다. `test_same_inputs_can_have_different_authored_states`는 같은 입력 행의 기대값 0/1이 각각 보존됨을 검사한다. `test_computed_adapter_matches_existing_nodes`는 기존 계산기와 입력·노드·비트·행 순서가 같음을 검사한다.

  같은 입력 두 행의 핵심 assertion은 `assert table.rows[0].inputs == table.rows[1].inputs`, `assert table.rows[0].expected == ['0']`, `assert table.rows[1].expected == ['1']`, `assert len(table.rows) == 2`다. 이 fixture는 파서/인쇄의 행 보존 검사이며 칩 동작을 증명하는 물리 시나리오로 쓰지 않는다.
- [ ] **Step 2: 경계 테스트 작성.** `test_empty_unknown_and_unobserved_are_distinct`는 빈 셀만 오류이고 미정/관측 안 함은 별개 토큰임을 검사한다. `test_rejects_missing_or_duplicate_columns`, `test_rejects_unknown_nodes_and_bad_provenance`, `test_derived_requires_rationale_and_setup`, `test_rejects_bad_order_and_undeclared_clock_edges`를 추가한다. `test_clock_trace_rejects_mismatched_edge_and_hidden_transition`는 초기 레벨 누락, 0 뒤 1->0, 0 뒤 bare 1을 거절한다. `test_relative_expectation_requires_prior_observation`는 첫 행 유지/반전을 거절하되 앞 행 관측 이후를 허용한다.
- [ ] **Step 3: RED 확인.** `.venv/bin/python -m pytest -n0 tests/test_lab_observations.py tests/test_lab_nodes.py -q`. 모듈/동작 부재 실패를 확인한다.
- [ ] **Step 4: 어댑터 구현.** procedure_issues는 위 의미 규칙을 한 곳에서 검사한다. stage_observations는 행을 합치거나 클럭에 따른 새 기대값을 계산하지 않는다. nodes.py는 observed를 계산하지 않고 기존 expression-only 데이터 결과를 보존한다.
- [ ] **Step 5: GREEN 확인.** Step 3 명령 통과 및 tests/fixtures/spec_edge.md 같은 기존 상태 토큰 진리표가 여전히 파싱·계산 가능한 범위에서 동작함을 확인한다. 스냅샷 expected를 구현 결과에 맞춰 바꾸지 않는다.

## Task 3: 검증기에 유형·절차·LED·입력 위치 연결

**Files:** Modify `scripts/lab/validate.py:698-770,825-899,1002-1077`, `scripts/lab/leds.py:43-98`; create `tests/test_lab_observation_validation.py`; extend `tests/test_lab_leds.py`.

**Interfaces:** Consumes Task 2 points/procedure_for_stage/procedure_issues/stage_observations. Produces 기존 `check_netlist_circuits`, `check_stage_leds`, `check_io_locations` 시그니처의 Finding 목록. 내부 `check_observation_procedures(netlist, spec) -> list[Finding]`를 추가하고 check_netlist_circuits에서 한 번 호출한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_observed_stage_with_procedure_has_no_truth_table_error`는 현재의 stepped+노드 오류가 없어짐을 검사한다. `test_observed_stage_without_procedure_is_error`, `test_expression_stage_without_record_table_is_still_error`, `test_duplicate_point_name_or_pin_is_error_v3`를 추가한다. v2의 검사 강도는 보존한다.
- [ ] **Step 2: 참조·출처·물리 조회 테스트 작성.** `test_walk_cannot_reference_procedure`, `test_primary_node_requires_checkable_expectation`, `test_procedure_reference_cannot_cross_circuits`, `test_manual_source_page_out_of_range_is_error`를 추가한다. `test_observed_pin_resolves_led_feed`는 같은 핀이 같은 관측점으로 풀림을 검사한다. `test_scenario_inputs_are_checked_against_stage_sidecar`는 누락 입력 위치가 식별 가능한 warn임을 검사한다. `test_probe_observation_does_not_require_led`와 `test_walk_contract_is_not_relaxed`도 추가한다.
- [ ] **Step 3: RED 확인.** `.venv/bin/python -m pytest -n0 tests/test_lab_observation_validation.py tests/test_lab_leds.py -q`.
- [ ] **Step 4: 검증 경로 구현.** 공통 핀 형식·칩 선언 검사는 모든 노드에 적용한다. 부울식 검산은 expression에만 적용한다. 새 절차의 셀/참조 오류는 error, 아직 생성되지 않은 보드 자산/입력 위치는 기존 정책처럼 warn이다. observed+절차 경로를 위한 면제를 모든 노드 검사 무력화로 구현하지 않는다. 입력 위치는 procedure.inputs에서 조회한다.
- [ ] **Step 5: GREEN 확인.** Step 3 및 `.venv/bin/python -m pytest -n0 tests/test_lab_netlist_parser.py tests/test_lab_nodes.py tests/test_breadboard_physical.py -q` 통과. 단계 번호·걷기 주소·R8에 대한 기존 테스트를 삭제/완화하지 않는다.

## Task 4: 단계 안의 순차 확인 표와 LED별 기대 동작 인쇄

**Files:** Modify `scripts/lab/render.py:880-1032,1067 이하`, `.claude/skills/prep-lab-checklist/template.html`; create `tests/test_lab_observation_render.py`; extend `tests/test_lab_render.py`.

**Interfaces:** Consumes Task 2 ObservationTable, Task 3 관측점/급전 조회, 기존 `lit`와 sidecar LED 순서. Produces 새 `_observation_procedure_html(table, leds=(), feed=None, png=None) -> str` 및 기존 `_stage_html`의 v3 분기. v2 공개/테스트 호출 형태를 유지한다.

- [ ] **Step 1: 실패 테스트 작성.** `test_last_stage_prints_explicit_procedure`는 마지막 단계에도 절차 제목·5개 원래 행·BIT1 핀이 있는지 검사한다. `test_probe_stage_prints_procedure_without_led`는 LED가 없어도 같은 조작/기대값이 있는지 검사한다. `test_derived_procedure_is_labeled_at_point_of_use`는 정확한 `교안 원문이 아니다 — 교안에서 유도한 확인 절차` 문구와 출처·준비 설명을 검사한다. manual 절차에는 유도 표시를 붙이지 않는다.
- [ ] **Step 2: LED·기록 불변식 테스트 작성.** `test_active_low_and_active_high_known_bits`는 극성별 점등을 검사한다. `test_mixed_hold_toggle_unknown_and_bits_are_per_led`는 서로 다른 LED의 비트·유지·반전·미정·관측 안 함이 모두 남고 미정을 소등으로 분류하지 않음을 검사한다. `test_inherited_led_missing_in_procedure_is_unobserved`는 기대값 추론이 없음을 검사한다. `test_scenario_checkboxes_do_not_add_record_cells`는 td.box만 늘고 td.check/기록 빈칸 수가 불변임을 검사한다. `test_v2_render_html_is_unchanged`는 대표 v2 출력과 바이트 비교한다.
- [ ] **Step 3: RED 확인.** `.venv/bin/python -m pytest -n0 tests/test_lab_observation_render.py tests/test_lab_render.py -q`.
- [ ] **Step 4: 렌더 구현.** 명시적 procedure 분기를 기존 last/LED 계산 분기보다 먼저 처리한다. point_kind가 observed인 노드를 `_unstaged_nodes_html`에서 조합식으로 계산하지 않는다. 단계에서 참조하지 않은 절차는 임의의 순서로 실행하라고 인쇄하지 않고 검증 경고로 식별한다. 새 CSS는 observation-procedure 범위에만 적용한다. 기존 record_row_leds의 행 전체 HOLD 반환을 새 다중 LED 절차에 그대로 재사용하지 않는다.
- [ ] **Step 5: GREEN 확인.** Step 3 명령이 통과하고 HTML escape된 신호명/조작/출처가 안전하게 출력되는지 검사한다. 새 표가 본문 참조표로 중복 인쇄되지 않아야 한다.

## Task 5: 실험06·07 사례로 종단 검증 및 인쇄 QA

**Files:** Create `tests/test_lab_observation_integration.py`, `tests/fixtures/netlist_observation_jk_v3.md`, `tests/fixtures/spec_observation_jk.md`, `docs/verification/2026-10-21-sequential-observations.md`. 필요시 앞 Task의 v3 fixture만 확장한다. 실제 `보고서/실험06`·`보고서/실험07` 산출물은 수정하지 않는다.

**Interfaces:** Consumes parser→check_netlist_circuits→render_checklist와 기존 derive_record/write_record/fit_pages/html_to_pdf. Produces 재현 가능한 fixture 기반 HTML/PDF 검증 증거. 테스트 임시 자산은 tmp_path, 수동 QA는 고유 tmp 폴더를 쓴다.

- [ ] **Step 1: 실패하는 종단 테스트 작성.** `test_jk_hold_toggle_sequence_end_to_end`는 reset→hold→toggle과 Q/Q' 관측을 검사한다. `test_six_bit_sequence_preserves_serial_timeline`는 고정된 검증 입력의 저작 결과 000000→100000→010000을 해당 에지 행에서 그대로 인쇄하고, 에지 사이 준비 행도 남는지 검사한다. fixture 기대값은 원래 교안 배선과 독립 손계산으로 검토하고 도구가 계산했다고 주장하지 않는다.
- [ ] **Step 2: 기록 보호 테스트 작성.** `test_scenario_does_not_change_derived_record`는 같은 lab-spec/v2에서 절차 유무와 무관하게 derive_record가 동일함을 검사한다. `test_filled_record_is_not_overwritten`는 기존 write_record 가드를 호출해 내용/해시가 그대로임을 검사한다. 실험07 실제 T1~T3 출력을 fixture expected로 채우지 않는다.
- [ ] **Step 3: 종단 테스트 실행.** `.venv/bin/python -m pytest -n0 tests/test_lab_observation_integration.py -q` 실행 후 연결 누락으로 실패하면 그 실패를 고정하고 필요한 결함만 고쳐 통과시킨다. 앞 Task에서 이미 완성돼 첫 실행부터 통과하면 그대로 기록하고 불필요한 runtime 변경을 하지 않는다. 앞 Task의 단위 테스트도 함께 통과해야 한다.
- [ ] **Step 4: 격리된 HTML/PDF QA.** fixture에 완성 보드가 없다는 경고와 단계 그림 부재를 숨기지 않는다. LED/입력 위치 테스트는 소형 임시 sidecar를 사용하며 실험07 물리 배치를 검증했다고 보고하지 않는다. 기존 render_checklist→fit_pages→html_to_pdf로 한 개 LED 및 여섯 출력 절차를 고유 tmp 폴더에 렌더한다. Chrome 화면과 PDF 렌더에서 조작·핀·출처·긴 입력 이름·LED 번호·행 순서·체크박스·페이지 잘림을 직접 확인한다. 행이 긴 표의 반복 헤더/분할 후 순서도 확인한다. 실행하지 못한 화면/PDF 검사는 미완료로 기록한다.
- [ ] **Step 5: 관련 회귀 실행.** `.venv/bin/python -m pytest -n0 tests/test_lab_observation_parser.py tests/test_lab_observations.py tests/test_lab_observation_validation.py tests/test_lab_observation_render.py tests/test_lab_observation_integration.py tests/test_lab_netlist_parser.py tests/test_lab_nodes.py tests/test_lab_leds.py tests/test_lab_render.py tests/test_breadboard_physical.py tests/test_breadboard_boards.py tests/test_breadboard_wiring.py -q`. 실패가 없고 확인 기록이 작성돼야 이 Task가 완료다.

## Task 6: 저작 스킬·계약 동기화와 최종 회귀

**Files:** Modify `.claude/skills/draft-lab-spec/SKILL.md`, `.claude/skills/prep-lab-checklist/SKILL.md`, `docs/schema/lab-netlist-v2.md`, `docs/schema/lab-netlist-v3.md`, `docs/schema/lab-spec-v2.md`의 netlist 부속 안내만; create `tests/test_lab_observation_contract_docs.py`; update 검증 기록.

**Interfaces:** Consumes Task 1~5의 완료된 계약과 검증 명령. Produces 스킬에서 복사 실행 가능한 v2/v3 유형별 저작/검증 절차. 실험별 하드코딩과 공통 도구의 범위 혼동을 제거한다.

- [ ] **Step 1: 문서 계약 실패 테스트 작성.** `test_v3_docs_cover_types_procedures_and_authored_expectations`는 정확한 열·토큰·유도 표시를 검사한다. `test_skills_route_sequential_observations_to_procedures`는 모든 노드가 반드시 부울식이라는 기존 단정을 제거하고 관측 유형별 규칙 및 기존 승인본 보호가 남아 있음을 검사한다. 예제는 임시 파일로 파싱·검증해 문법 불일치를 잡는다.
- [ ] **Step 2: RED 확인.** `.venv/bin/python -m pytest -n0 tests/test_lab_observation_contract_docs.py tests/test_schema_doc_sync.py -q`.
- [ ] **Step 3: 문서·스킬 갱신.** draft의 절대 규칙과 단계 7/검증/fresh 검토 과제에 새 절차를 반영한다. prep의 예외 설명에서 모든 NetlistError가 메타 누락이라는 단정을 고치고 실제 버전/문법 오류를 그대로 전달한다. v2 스키마 내용은 바꾸지 않고 v3 링크만 추가한다. breadboard 규칙 R7~R10·예산 예외는 수정하지 않는다. samefile을 재확인해 중복 편집하지 않는다.
- [ ] **Step 4: GREEN 및 전체 회귀.** Step 2 통과 후 `.venv/bin/python -m pytest -q`를 한 번 실행한다. 전체 실패는 변경 전 상태/관련성에 근거해 구분하되 실패를 숨기거나 성공으로 보고하지 않는다. 검증 후 새 변경이 없으면 반복 실행하지 않는다.
- [ ] **Step 5: 최종 검토/인계.** git diff --check, 허용 경로 diff, 기존 실험 산출물·채워진 기록의 보존, Task 5의 시각 QA를 확인한다. 검증 기록에 구조 검증/논리 손검산/화면/PDF/물리 배치의 각 수행 여부를 분리해 적는다. 완료 보고는 공통 도구 구현 범위만 주장하고 실험07 배치와 실제 v3 문서 적용은 후속 작업으로 남긴다.

## 완료 조건 및 후속 경계

- [ ] v2 파싱/계산/인쇄의 회귀가 없고 v3 순차 확인 절차가 기록 진리표 없이도 단계 안에 인쇄된다.
- [ ] 같은 입력의 반복 행, 클럭 에지, 여러 노드의 유지/반전/미정/관측 안 함이 손실 없이 표현된다.
- [ ] 잘못된 참조·빈 기대값·정의 누락은 오류이며 물리 자산 부재는 구체적인 경고다.
- [ ] 기존 기록표·측정 빈칸·작성된 기록은 변경되지 않는다.
- [ ] 구조/회귀 테스트와 화면/PDF QA의 실제 수행 증거를 남긴다. 물리 배치를 검증했다고 보고하지 않는다.
- [ ] 이후 별도 작업은 실험07 v3 초안 작성 → 실제 배치기/R7~R10 검증 → 결선도 → prep-lab-checklist 순서다. 기존 실험07 초안을 제자리에서 임의 교체하지 않는다.

## 계획 자체 검토

- 설계 범위: 관측점 분리(Task 1/2), 절차/오류(Task 2/3), 인쇄/LED(Task 4), 기록 보호·실험06/07 사례·시각 검증(Task 5), 스킬/계약(Task 6)으로 모두 대응했다.
- 인터페이스: 모델은 parser가 소유하고 observations는 이를 소비한다. validate/render/leds가 같은 관측점 정의를 참조하며 parser→observations 역참조는 만들지 않는다.
- Review Focus 다섯 항목에 해당하는 테스트를 각 소유 Task에 배치했다. 행/시간 의미 보존과 실제 논리 정확성 검증의 차이를 명시했다.
- 이번 단계에서는 이 계획 파일만 작성했다. 구현·회로 산출물 교체·테스트 실행·커밋·푸시는 수행하지 않았다.

## 실행 방식

2026-10-21 구현 요청에 따라 Native로 실행했다. Task 1~6 기능·문서 구현 및 fresh 리뷰 수정 완료.
최종 3546 passed / 기존 원본에서도 재현한 11 failed / 9 skipped다. 기능/문서 집중 검사는 74 passed,
관련 기존 동작 포함 검사는 407 passed다. 세부 수행·범위 조정·기존 실패는
[검증 기록](../../verification/2026-10-21-sequential-observations.md)에 남겼다.
아래는 계획 당시의 실행 선택 설명이다.

 **Native(직접 구현)**를 권장한다. 여섯 Task가 같은 parser 모델·검증·renderer 계약에 순차적으로 의존하므로 한 구현자가 전체 맥락을 유지하는 편이 효율적이다. Native를 선택하면 마지막에 fresh 에이전트가 전체 변경을 읽기 전용으로 검토하고, 지적 처리 후 필요한 검증을 다시 실행한다. 필요하면 Subagent-driven으로 Task마다 구현/검토를 나눌 수 있다. 사용자가 실행 방식을 정하고 구현을 요청한 뒤 시작한다.

### 후속 실험07 적용 완료 (2026-10-21)

사용자의 추가 구현 요청에 따라 실험07에 v3·실제 배치·부분 배선 임시 고정·걷기·체크리스트를 적용했다.
[실험07 배치 검증 기록](../../verification/2026-10-21-e07-v3-placement.md)에 핀 재배정, R7 예외,
24개 그림, 28쪽 PDF, 3564 passed/기존 실패 11개 및 시각 검증 근거를 남겼다.
