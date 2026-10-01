# Logic Lab Config Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows에서 교안 후보 테스트가 경로 구분자와 배포본 존재 여부 때문에 실패하지 않게 한다.

**Architecture:** `manual_candidates()`의 반환값과 우선순위는 유지한다. 테스트의 후보 식별에는 `Path.parents`를 쓰고, 파일명 규칙 검사는 배포본 없는 임시 루트에서 실행한다. 수정 파일은 기존 테스트 파일 하나다.

**Tech Stack:** Python, `pathlib.Path`, `tempfile.TemporaryDirectory`, `unittest`, pytest 및 pytest-subtests.

**Spec:** `docs/superpowers/specs/2026-09-29-lab-config-tests-design.md`

## Global Constraints

- `scripts/lab/config.py`, 원본 자료, `codex/logic-lab-review-pack` 브랜치 및 해당 워크트리는 변경하지 않는다.
- 기존 후보 우선순위는 배포본 → 보고서 폴더 사본 → 과거 교안이다.
- 기존 변경을 보존한다. 시작 직전 `git status --short --branch`와 대상 파일의 diff를 확인한다.
- Windows에서 두 명령으로 검증한다. macOS에서 직접 실행하지 않았다면 macOS 검증 완료라고 주장하지 않는다.
- 구현은 현재 깨끗한 `C:\Users\Hyunjun\.codex\worktrees\c7b4\논회실` 체크아웃에서 진행할 수 있다. 실행 전 해당 체크아웃이 여전히 깨끗하고 지정된 저장소와 같은 커밋인지 확인한다. 이 계획과 설계는 지정된 저장소의 `docs/superpowers/`에 있으며 기존 미추적 문서는 건드리지 않는다.

## Review Focus

| 조건 | 기대 동작 | 확인 테스트 |
|---|---|---|
| Windows의 `\` 경로 표현 | 아카이브 후보를 찾는다 | `test_아카이브_후보가_열_개_다_실재한다` |
| Windows의 보고서 사본 경로 | `EXPERIMENT_BASE` 아래 후보를 찾는다 | `test_기반이_두_입구_전부에_적용된다` |
| 아카이브와 이름이 비슷한 이웃 폴더 | 이웃 폴더를 아카이브로 오인하지 않는다 | 새 `test_아카이브_후보_폴더_경계로_고른다` |
| 실험 4 배포본이 없는 루트 | `실험04/실험4.pdf` 형식과 사본 → 아카이브 순서를 검사한다 | `test_파일_이름은_0_을_채우지_않는다` |
| 이번 학기 배포본이 있는 루트 | 배포본 → 사본 → 아카이브 순서를 유지한다 | 기존 `test_배포본이_주차_폴더_사본보다_먼저다`와 `test_주차_폴더_사본이_아카이브보다_먼저다` |

---

## File map

- Modify: `tests/test_lab_config.py` — 교안 후보 식별 헬퍼와 두 테스트의 입력·경로 비교. 새 경계 테스트도 이 파일의 `TestManualCandidates`에 둔다.
- Read only: `scripts/lab/config.py` — `manual_candidates(experiment, root=None) -> list[Path]`, `MANUAL_ARCHIVE`, `EXPERIMENT_BASE`의 계약을 확인한다.
- Read only: `tests/test_lab_validate.py`, `tests/test_skill_docs.py` — 회귀 검사 대상이다.

### Task 1: 경로 독립적인 후보 선택과 결정적인 파일명 검사

**Files:**
- Modify: `tests/test_lab_config.py:12-32` — 아카이브 헬퍼, 파일명 테스트, 경계 테스트.
- Modify: `tests/test_lab_config.py:378-387` — 보고서 사본 선택.
- Test: `tests/test_lab_config.py`, `tests/test_lab_validate.py`, `tests/test_skill_docs.py`.

**Interfaces:**
- Consumes: `config.manual_candidates(experiment, root=None) -> list[Path]`, `config.MANUAL_ARCHIVE: str`, `config.EXPERIMENT_BASE: str`.
- Produces: 기존 `archive_candidate(candidates: list) -> Path`의 같은 시그니처와 반환값. 제품 코드의 인터페이스는 바꾸지 않는다.

- [ ] **Step 1: 작업 상태와 기존 실패를 확인한다**

PowerShell에서 실행할 체크아웃을 작업 디렉터리로 삼는다.

```powershell
git status --short --branch
git diff -- tests/test_lab_config.py scripts/lab/config.py
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m pytest -p no:cacheprovider -n0 tests/test_lab_config.py -q
```

기준 기대값은 Windows에서 14 failed, 99 passed다. 다른 결과가 나오면 실패 이름과 변경 파일을 먼저 조사한다. `git status`에 기존 변경이 있으면 덮어쓰지 않는다.

현재의 깨끗한 `c7b4` 분리 체크아웃에서 실행한다면 기준 재현 후 전용 브랜치를 만든다. `main`이나 학습팩 브랜치에서 이 명령을 실행하지 않는다.

```powershell
git switch -c codex/lab-config-test-fix
```

- [ ] **Step 2: 아카이브 폴더 경계의 실패 테스트를 추가한다**

`TestManualCandidates`에 다음 메서드를 추가한다.

```python
def test_아카이브_후보_폴더_경계로_고른다(self):
    candidates = [
        Path('from_the_past/정리/강의노트-복사/실험1.pdf'),
        Path('from_the_past/정리/강의노트/실험1.pdf'),
    ]
    self.assertEqual(archive_candidate(candidates), candidates[1])
```

- [ ] **Step 3: 새 테스트가 기존 헬퍼에서 실패하는지 확인한다**

```powershell
python -m pytest -p no:cacheprovider -n0 tests/test_lab_config.py -q
```

기대값: 기존 14건에 새 경계 테스트가 추가되어 실패한다. Windows에서는 `StopIteration`, POSIX에서는 첫 번째 이웃 폴더를 잘못 고르는 단언 실패가 예상된다.

- [ ] **Step 4: 두 후보 선택을 `Path` 경계 비교로 고친다**

`archive_candidate()`의 반환문을 다음처럼 바꾼다.

```python
return next(c for c in candidates
            if Path(config.MANUAL_ARCHIVE) in c.parents)
```

`test_기반이_두_입구_전부에_적용된다`의 `사본` 선택문을 다음처럼 바꾼다. `experiment_dir()`가 반환하는 문자열의 슬래시 검사는 그대로 둔다.

```python
사본 = next(c for c in config.manual_candidates(3)
           if Path(base) in c.parents)
```

- [ ] **Step 5: 경로 수정의 결과를 확인한다**

```powershell
python -m pytest -p no:cacheprovider -n0 tests/test_lab_config.py -q
```

기대값: 아카이브 10개 서브테스트, 경계 테스트, 사본 선택 테스트가 통과한다. 실험 4 후보 인덱스 테스트 한 건만 남아야 한다. 추가 실패가 있으면 다음 단계 전에 원인을 분류한다.

- [ ] **Step 6: 파일명 테스트의 입력을 통제한다**

`test_파일_이름은_0_을_채우지_않는다` 본문에서 `got` 생성과 두 단언을 다음처럼 감싼다.

```python
with tempfile.TemporaryDirectory() as root:
    got = config.manual_candidates(4, root=root)
self.assertEqual(got[0], Path('보고서/실험04/강의노트/실험4.pdf'))
self.assertEqual(got[1], Path('from_the_past/정리/강의노트/실험4.pdf'))
```

기존 `import tempfile`을 그대로 쓴다. 후보는 상대 경로이므로 임시 디렉터리가 닫힌 뒤에도 두 단언을 실행할 수 있다.

- [ ] **Step 7: 단일 파일과 관련 회귀 검사를 실행한다**

```powershell
python -m pytest -p no:cacheprovider -n0 tests/test_lab_config.py -q
python -m pytest -p no:cacheprovider -n0 tests/test_lab_config.py tests/test_lab_validate.py tests/test_skill_docs.py -q
git diff --check
git status --short --branch
```

기대값: 두 pytest 명령의 종료 코드가 0이다. 실패가 남으면 테스트 이름과 원인을 기록한다. `git diff --check`가 통과하고 수정된 제품 코드나 원본 자료가 없어야 한다.

- [ ] **Step 8: 검증된 테스트 변경만 커밋한다**

실행 방법을 정한 뒤, 별도 작업 브랜치에서 진행할 때만 아래를 실행한다. 지정된 `main`의 기존 미추적 문서와 학습팩 브랜치 파일은 스테이징하지 않는다.

```powershell
git add tests/test_lab_config.py
git diff --cached --check
git commit -m "test: make lab config manual tests platform independent"
```

## Self-review

- 설계의 세 원인을 Task 1의 Steps 4·6이 각각 해결한다.
- `config.py`의 우선순위는 수정하지 않고 기존 배포본 테스트와 전체 회귀 검사로 확인한다.
- 새 경계 테스트는 문자열 접두사만 바꾸는 수정이 놓칠 수 있는 이웃 폴더를 검사한다.
- 코드 조각의 `Path`, `tempfile`, `archive_candidate`, `manual_candidates`는 모두 기존 파일의 이름과 시그니처를 따른다.
