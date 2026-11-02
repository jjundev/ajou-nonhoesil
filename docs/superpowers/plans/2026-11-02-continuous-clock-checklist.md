# 반복 클록 체크리스트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 클록 실험의 체크리스트가 실제 신호발생기 조작과 입력 변경 및 관측을 충실히 나타내게 한다.

**Architecture:** 명세·결선도 저작 규칙에 반복 클록의 선택 기준과 설정 조건을 추가한다. v3 확인 절차에는 명시적인 반복 클록 토큰을 도입해 수동 에지와 구분하고, 검증·출력·기록 파생 경로에서 유지한다.

**Tech Stack:** Python, Markdown, pytest, 기존 HTML/PDF 체크리스트 생성기.

**Spec:** 2026-11-02 대화의 `/grill-yourself` 설계 및 실험 7 실제 과정. 별도 설계 파일 없음. 아래 두 기본값은 제안이며 사용자 확정 전 구현하지 않는다: LED 관찰용 1 Hz 후보, 교안의 단일 펄스 지시 우선.

## Global Constraints

- 교안과 회로의 전압·타이밍·기구 조건이 우선이다. 1 Hz 및 0~5 V는 실험 7 관찰이며 모든 실험의 확정값이 아니다.
- 명세에 없는 실험 내용, 실제 기록, 특정 장비 설정을 지어내지 않는다.
- 기존 에지 검증과 기록 보존, 체크리스트 PDF와 기록 파일 쌍 생성 규칙을 유지한다.
- 실험 7 기존 결과보고서와 채워진 기록은 변경하지 않는다.
- 신호발생기 출력의 범위와 주파수·단위를 명시하고 진폭의 Vpp/피크 모호성을 남기지 않는다.

## Review Focus

- 반복 중 수동 데이터 입력 변경: Task 1의 반복 행 검증 및 Task 2 렌더 검사.
- 반복 클록을 다른 입력에 사용: Task 1의 비클록 입력 거부 검사.
- 단일 펄스와 연속 펄스 혼합: Task 1의 정지 후 초기 레벨 및 기존 에지 검사.
- 불명확한 전압·주파수: Task 3의 저작 점검에서 출처·단위를 확인.
- 기입된 기록의 유실: Task 3의 기존 기록 보호 검사.

---

### Task 1: 반복 클록의 명시적 표현과 검증

**Files:**
- Modify: `scripts/lab/observations.py` (`procedure_issues`)
- Modify: `docs/schema/lab-netlist-v3.md`
- Test: `tests/test_lab_observations.py`

**Interfaces:** 기존 `procedure_issues(section, procedure) -> list[tuple[int, str]]` 유지. `clocks`로 선언된 입력 셀에서만 `RUN`을 반복 클록으로 허용한다.

- [ ] 다음 테스트를 기존 fixture의 `replace`를 이용해 작성한다. 클록 입력 `0 → RUN → RUN`과 데이터 입력 변경은 통과한다. 비클록 열의 `RUN`, 첫 행의 `RUN`, `RUN` 뒤 에지 토큰은 오류다. `RUN` 뒤 레벨 `0` 또는 `1`은 정지 후 명시한 레벨로 허용하고, 그 다음에만 시작 레벨이 일치하는 에지를 허용한다. 기존 숨은 레벨 변경 오류는 유지한다.
- [ ] `python -m pytest tests/test_lab_observations.py -q`를 실행해 새 테스트가 실패하는지 확인한다.
- [ ] `procedure_issues`에 위 상태 전이를 구현한다. `RUN`은 주기적인 상태만 나타내며 에지 수·위상·회로 출력은 추론하지 않는다. 반복 중 입력 변경 직후 출력은 저작자가 명시한 조건에서만 예상한다.
- [ ] `lab-netlist-v3.md`에 `RUN`의 의미, 최초 정지 레벨 요구, 정지 후 레벨 명시, 수동 에지와 혼합 예를 기술한다. 주파수·출력 전압 범위·설정 근거는 `setup`에 둔다.
- [ ] 같은 pytest 명령과 `python -m pytest tests/test_lab_observation_validation.py tests/test_lab_observation_parser.py -q`를 실행해 모두 통과한다.

### Task 2: 체크리스트 출력과 기록의 반복 클록 보존

**Files:**
- Inspect and modify only if needed: `scripts/lab/render.py`, `scripts/lab/record.py`
- Test: `tests/test_lab_observation_render.py`, `tests/test_lab_observation_integration.py`

**Interfaces:** Task 1의 `RUN`을 원본 데이터에서 그대로 사용한다. 사용자 출력은 `반복 클록`으로 표시하되 원본과 입력 순서는 변경하지 않는다.

- [ ] v3 fixture를 활용하여 `RUN` 행 2개와 D 변경, 정지 후 수동 에지를 포함한 렌더 테스트를 작성한다. `반복 클록`, 설정 설명, D 조작, LED 기대값 및 빈 실제 결과 칸이 출력되고, 수동 에지 지시도 보존되어야 한다.
- [ ] `python -m pytest tests/test_lab_observation_render.py tests/test_lab_observation_integration.py -q`를 실행해 새로운 표시 검사가 실패하는지 확인한다.
- [ ] 공통 출력 경로에서 클록 열의 `RUN`만 `반복 클록`으로 표시한다. 명세 stepped 기록표도 반복 클록을 설명할 때 동일한 의미가 보이도록 작성하고, 기록 생성 시 실제 결과를 채우지 않는다.
- [ ] 위 테스트 및 `python -m pytest tests/test_lab_checklist_minimal.py -q`를 실행해 통과한다.

### Task 3: 실험별 저작과 현장 검증 규칙

**Files:**
- Modify: `.agents/skills/draft-lab-spec/SKILL.md`
- Modify: `.agents/skills/prep-lab-checklist/SKILL.md`
- Test: `tests/test_lab_observation_contract_docs.py` 및 해당 실험용 임시 fixture

**Interfaces:** Task 1의 `RUN`, 기존 `setup`, `source`, `provenance`, `rationale`, stepped 표와 기존 PDF/기록 생성 절차를 사용한다.

- [ ] 스킬 지침에 다음 우선순위를 추가한다: 교안의 명시적 단일 펄스·정지 요구 보존; 반복 클록이 적합하고 허용되면 신호발생기 사용; 주파수 미지정 LED 관찰 시 1 Hz를 검토하되 근거·회로 적합성 확인 후 제안; 전압 범위·오프셋·진폭 단위는 장비와 회로에 맞춰 명시. 실험별로 D, CLR, PR 등을 수동 조작하는 순서와 안정화 후 관찰을 작성한다.
- [ ] 실제와 이론을 분리한다. 반복 중 특정 에지 번호의 값은 그 에지 수와 입력 타이밍을 실제로 통제·관찰한 경우에만 실측으로 적는다. 교안 외 절차는 유도 사실을 원본에 남기고 빈 실제 칸을 유지한다.
- [ ] 문서 계약 테스트에 `RUN`, 단일 펄스 예외, 교안 우선, 전압 단위 및 기존 기록 보존 지침이 존재하는지 추가하고 실행한다: `python -m pytest tests/test_lab_observation_contract_docs.py -q`.
- [ ] 임시 fixture에서 반복 입력 변경과 단일 펄스가 공존하는 체크리스트를 생성하고 검증한다. HTML의 조작 순서·설정·실측 빈칸 및 PDF의 가독성·잘림을 확인한다. 채워진 기록은 `write_record`가 덮어쓰기를 거절하는 기존 테스트를 실행하고 보존한다. 실제 실험 7 산출물은 덮지 않는다.
- [ ] `python -m pytest tests/test_lab_observations.py tests/test_lab_observation_validation.py tests/test_lab_observation_parser.py tests/test_lab_observation_render.py tests/test_lab_observation_integration.py tests/test_lab_observation_contract_docs.py tests/test_lab_checklist_minimal.py -q`를 실행해 통과한다.

## 완료 기준

반복 클록 및 단일 펄스가 정확히 구별되고, 출력된 조작과 기록 칸이 실제 수행 순서에 맞으며, 기존 에지 검증·기록 보호 테스트와 PDF 시각 검사가 통과한다. 새 실험의 설정은 해당 교안이 나온 후 결정한다.
