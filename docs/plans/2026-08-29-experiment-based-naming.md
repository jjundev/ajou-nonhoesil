# 실험 기준 명명 통일 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**설계 근거 문서:** [2026-08-28-logic-lab-harness-design.md](docs/plans/2026-08-28-logic-lab-harness-design.md) — 단, 그 문서의 결정 #4 "폴더 기준 = 주차"를 **이 계획서가 뒤집는다.** 나머지 결정(R1~R10)은 그대로 유효하다.

**Goal:** 저장소의 폴더·산출물 명명을 주차 기준(`2주차/`)에서 실험 기준(`실험01/`)으로 통일하고, 그 규약이 다시 어긋나지 않도록 코드로 강제한다.

**Architecture:** 명명 규칙을 문자열로 흩뿌리지 않고 `config.experiment_dir()` 함수 하나로 모은다. 규약 준수는 `validate.check_folder_convention()` 이 검사하고 ⑤ `review-lab-report` 가 매 검토마다 호출한다. 폴더 이름과 명세의 `experiment` 필드가 어긋나면 error 가 난다 — 이 저장소의 반복 결함이 "규약을 세 곳에 적용하고 네 번째를 잊는 것"이었으므로, 규약은 사람이 지키는 게 아니라 검사가 지키게 한다.

**Tech Stack:** Python 3.14 (**표준 라이브러리만**), unittest, Markdown + 자체 프론트매터 서브셋, Claude Code 프로젝트 스킬

## Global Constraints

- **원본 자료는 읽기 전용.** `from_the_past/`, `강의계획서/` 아래를 이 작업이 수정하지 않는다.
- **`docs/plans/` 의 과거 계획서는 고쳐 쓰지 않는다.** 날짜가 박힌 역사 기록이다. 결정이 뒤집힌 사실은 설계문서에 **한 줄 정정 주석**으로만 남긴다 (Task 5).
- **표준 라이브러리만.** PyYAML·pytest 없음. 테스트는 `python3 -m unittest discover -s tests -t .` 로 돈다.
- **macOS NFD 주의.** 한글 폴더로 `cd` 하면 정규화 차이로 실패한다. 항상 저장소 루트에서 절대경로·글롭으로 접근한다.
- **폴더 이름은 두 자리 0 채움.** `실험01` ~ `실험10`. 0 을 안 채우면 `실험10` 이 `실험2` 앞에 정렬된다.
- **`week` 필드는 유지한다.** 체크리스트·기록 제목이 `{week}주차 · 실험{experiment} {title}` 형식을 계속 쓴다. 5·6·7주차 회전 때문에 시간 순서를 아는 유일한 근거이기도 하다.
- **실험 번호는 1~10 뿐이다.** FPGA(13~15주차)는 실험 번호가 없으므로 `프로젝트/` 로 간다. 8주차 중간고사는 산출물이 없으므로 폴더를 만들지 않는다.

## 확정된 결정 (2026-08-29 사용자)

| # | 항목 | 결정 |
|---|---|---|
| 1 | 비-실험 주차 | FPGA → `프로젝트/` 하나로. 중간고사 폴더 없음 |
| 2 | 폴더 이름 | `실험01/` ~ `실험10/` (두 자리 0 채움) |
| 3 | 명세 `week` 필드 | 유지 (제목·시간순서 근거) |

## 실험 ↔ 주차 매핑 (**1:1 아님 — 3개 회전**)

| 실험 | 주 | 주제 | 폴더 |
|---|---|---|---|
| 1 | 2 | Basic Gates | `실험01/` |
| 2 | 3 | CMOS 전기적 특성 | `실험02/` |
| 3 | 4 | Adder & Subtracter | `실험03/` |
| **4** | **7** | **MUX & DEMUX** | `실험04/` |
| **5** | **5** | **Decoder & Encoder** | `실험05/` |
| **6** | **6** | **Latch & Flip-flop** | `실험06/` |
| 7 | 9 | Shift register | `실험07/` |
| 8 | 10 | Counter | `실험08/` |
| 9 | 11 | RAM | `실험09/` |
| 10 | 12 | D/A & A/D Converter | `실험10/` |
| — | 13~15 | FPGA (DE0-Nano, Quartus) | `프로젝트/` |
| — | 8 | 중간고사 | 폴더 없음 |

**실험4가 7주차다.** 이 표를 외우지 말고 스킬이 띄우는 것을 볼 것.

---

## File Structure

### 수정 — Python 코어

| 파일 | 책임 | 변경 |
|---|---|---|
| `scripts/lab/config.py` | 설정 로딩 | `EXPERIMENT_COUNT`, `experiment_dir()` 추가 |
| `scripts/lab/validate.py` | 검증 | `check_folder_convention()` 추가 |

`record.py`·`render.py`·`spec_parser.py`·`md.py`·`notation.py`·`boolexpr.py`·`html2pdf.py` 는 **건드리지 않는다.** 코어는 폴더 경로를 모르고, 제목 형식(`{week}주차 · 실험{experiment}`)은 유지 결정이라 그대로다.

### 수정 — 테스트

| 파일 | 변경 |
|---|---|
| `tests/test_lab_config.py` | 픽스처 경로 1곳 + `experiment_dir` 테스트 추가 |
| `tests/test_lab_validate.py` | 픽스처 경로 4곳 + `check_folder_convention` 테스트 추가 |
| `tests/test_lab_md.py` | 픽스처 경로 4곳 |
| `tests/test_lab_record.py` | 픽스처 경로 6곳 |
| `tests/test_lab_render.py` | 픽스처 경로 9곳 |
| `tests/test_lab_spec_parser.py` | 픽스처 경로 3곳 |

### 리네임 — 주차 산출물

| 현재 | 이후 |
|---|---|
| `2주차/` | `실험01/` |
| `6주차/` | `실험06/` |
| `12주차/` | `실험10/` |
| `2주차/output/2주차_예비보고서.{md,html,pdf}` | `실험01/output/실험01_예비보고서.{md,html,pdf}` |

### 수정 — 스킬

| 스킬 | 변경 |
|---|---|
| `init-lab-week/` → `init-lab-experiment/` | 폴더·이름·description 교체, 매핑 표 역전, `프로젝트/` 분기 |
| `prep-lab-checklist/SKILL.md` | 경로 표기 11곳 |
| `review-lab-report/SKILL.md` | 경로 표기 12곳 + 새 검사 배선 |
| `write-pre-report/SKILL.md` | 경로 표기 21곳 |
| `write-result-report/SKILL.md` | 경로 표기 28곳 |
| `explain-lab-preview/SKILL.md` | 경로 표기 34곳 |
| `make-lab-report-cover/SKILL.md` | 경로 표기 4곳 |

### 수정 — 문서

| 파일 | 변경 |
|---|---|
| `docs/schema/lab-spec-v1.md` | 픽스처 경로 표기 (살아 있는 참조 문서) |
| `docs/plans/2026-08-28-logic-lab-harness-design.md` | 결정 #4 행에 정정 주석 한 줄만 |

---

## Task 의존 그래프

```
Task 1 (명명 규약을 코드로)
   ↓
Task 2 (폴더·파일 리네임 + 픽스처·문서)
   ↓
Task 3 (init-lab-experiment)     Task 4 (나머지 6개 스킬)
   ↓                                    ↓
   └────────────→ Task 5 (재생성 + end-to-end 검증) ←┘
```

Task 3 과 Task 4 는 서로 독립이다.

---

### Task 1: 명명 규약을 코드로 고정

명명 규칙이 스킬 문서 118곳에 문자열로만 살아 있으면 반드시 어긋난다. 함수 하나로 모으고, 어긋남을 검사가 잡게 한다.

**Files:**
- Modify: `scripts/lab/config.py`
- Modify: `scripts/lab/validate.py`
- Test: `tests/test_lab_config.py`, `tests/test_lab_validate.py`

**Interfaces:**
- Produces: `config.EXPERIMENT_COUNT: int` (= 10), `config.experiment_dir(experiment: int) -> str`, `validate.check_folder_convention(spec_path, spec) -> list[Finding]`
- Consumes: 기존 `validate.Finding`, `config` 의 기존 임포트 그래프 (`config` 는 `md` 만 임포트하므로 `validate → config` 는 순환이 아니다)

- [ ] **Step 1: `experiment_dir` 의 실패 테스트를 쓴다**

`tests/test_lab_config.py` 끝에 추가:

```python
class ExperimentDirTest(unittest.TestCase):
    """폴더 이름 규칙은 한 곳에서만 만든다 — 문자열로 흩뿌리면 반드시 어긋난다."""

    def test_두_자리로_0을_채운다(self):
        self.assertEqual(config.experiment_dir(1), "실험01")
        self.assertEqual(config.experiment_dir(9), "실험09")

    def test_열_번째는_그대로_두_자리다(self):
        self.assertEqual(config.experiment_dir(10), "실험10")

    def test_0을_채워야_사전순_정렬이_시간순과_맞는다(self):
        names = sorted(config.experiment_dir(n) for n in range(1, 11))
        self.assertEqual(names[0], "실험01")
        self.assertEqual(names[1], "실험02")
        self.assertEqual(names[-1], "실험10")

    def test_범위_밖_번호는_거절한다(self):
        # FPGA 는 실험 번호가 없다. 11 을 허용하면 저장소가 없는 번호를 발명한다.
        for bad in (0, 11, -1):
            with self.subTest(experiment=bad):
                with self.assertRaises(ValueError):
                    config.experiment_dir(bad)

    def test_bool은_정수가_아니다(self):
        # True 는 int 의 하위형이라 조용히 `실험01` 이 된다.
        with self.assertRaises(TypeError):
            config.experiment_dir(True)
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_config -v 2>&1 | tail -20
```

Expected: FAIL — `AttributeError: module 'scripts.lab.config' has no attribute 'experiment_dir'`

- [ ] **Step 3: `experiment_dir` 을 구현한다**

`scripts/lab/config.py` 의 `IDENTITY_FIELDS` 선언 바로 아래에 추가:

```python
# 실험은 1~10 뿐이다. FPGA(13~15주차)는 실험 번호가 없어 `프로젝트/` 로 간다.
EXPERIMENT_COUNT = 10


def experiment_dir(experiment: int) -> str:
    """실험 번호 → 폴더 이름. 두 자리로 0 을 채운다.

    0 을 안 채우면 사전순 정렬이 `실험1, 실험10, 실험2, ...` 가 되어 시간
    순서와 어긋난다. 규칙을 여기 한 곳에만 두는 이유는, 이 저장소의 반복
    결함이 "같은 규약을 세 곳에 적용하고 네 번째를 잊는 것"이기 때문이다.
    """
    if isinstance(experiment, bool) or not isinstance(experiment, int):
        raise TypeError(f"실험 번호는 정수여야 합니다: {experiment!r}")
    if not 1 <= experiment <= EXPERIMENT_COUNT:
        raise ValueError(
            f"실험 번호는 1~{EXPERIMENT_COUNT} 입니다: {experiment}. "
            "FPGA 프로젝트는 실험 번호가 없으므로 `프로젝트/` 를 씁니다."
        )
    return f"실험{experiment:02d}"
```

- [ ] **Step 4: 통과를 확인한다**

```bash
python3 -m unittest tests.test_lab_config -v 2>&1 | tail -5
```

Expected: PASS (OK)

- [ ] **Step 5: `check_folder_convention` 의 실패 테스트를 쓴다**

`tests/test_lab_validate.py` 끝에 추가:

```python
class FolderConventionTest(unittest.TestCase):
    """폴더 이름과 명세의 `experiment` 가 어긋나면 잡는다.

    리네임을 한 번 하고 끝내면 다음 주차에 다시 어긋난다. 규약은 사람이
    아니라 검사가 지킨다.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _spec_at(self, folder, experiment):
        """`<folder>/체크리스트/명세.md` 를 만들고 (경로, spec) 을 돌려준다.

        `parse_spec` 은 항목마다 `title`·`device`·`ics`·`tables` 를 요구한다
        (`spec_parser.py`). 하나라도 빠지면 `SpecError` 가 나서 픽스처가
        만들어지지 않는다.
        """
        d = self.dir / folder / "체크리스트"
        d.mkdir(parents=True)
        path = d / "명세.md"
        path.write_text(
            "---\n"
            "schema: lab-spec/v1\n"
            f"week: 2\n"
            f"experiment: {experiment}\n"
            "title: Basic Gates\n"
            "source_manual: x.pdf\n"
            'power: {VCC: "+5V", GND: "GND"}\n'
            "items:\n"
            "  - id: E1.P1\n"
            "    title: 첫 항목\n"
            "    device: [LED]\n"
            "    ics: ['74HC08']\n"
            "    tables: [T1]\n"
            "---\n\n"
            "# E1.P1 · 첫 항목\n\n"
            "## T1 · 표\n\n"
            "- kind: truth-table\n"
            "- source: 교안 p1\n"
            "- encoding: 0/1\n\n"
            "| A | Y |\n|---|---|\n| 0 | 0 |\n| 1 | 1 |\n",
            encoding="utf-8",
        )
        return path, parse_spec(path)

    def test_맞으면_finding_이_없다(self):
        path, spec = self._spec_at("실험01", 1)
        self.assertEqual(validate.check_folder_convention(path, spec), [])

    def test_주차_이름이_남아_있으면_잡는다(self):
        path, spec = self._spec_at("2주차", 1)
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(any("실험01" in f.message for f in findings))

    def test_0을_안_채운_이름을_잡는다(self):
        path, spec = self._spec_at("실험1", 1)
        self.assertTrue(validate.check_folder_convention(path, spec))

    def test_번호가_어긋나면_잡는다(self):
        # 12주차는 실험10 이다. 실험12 폴더는 존재하면 안 된다.
        path, spec = self._spec_at("실험09", 10)
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(any("실험10" in f.message for f in findings))

    def test_범위_밖_번호에도_예외를_던지지_않는다(self):
        """⑤ 는 반쯤 망가진 문서에도 돌아야 한다 — 여기서 죽으면 안 된다."""
        path, spec = self._spec_at("실험11", 11)
        findings = validate.check_folder_convention(path, spec)
        self.assertTrue(findings)
        self.assertEqual(findings[0].level, "error")
```

- [ ] **Step 6: 실패를 확인한다**

```bash
python3 -m unittest tests.test_lab_validate -v 2>&1 | tail -20
```

Expected: FAIL — `AttributeError: module 'scripts.lab.validate' has no attribute 'check_folder_convention'`

- [ ] **Step 7: `check_folder_convention` 을 구현한다**

`scripts/lab/validate.py` 의 임포트 블록에 `config` 를 더한다 (`config` 는 `md` 만 임포트하므로 순환이 아니다):

```python
from . import config, md
```

그리고 `check_netlist` 정의 **앞에** 추가:

```python
def check_folder_convention(spec_path, spec) -> list:
    """명세가 놓인 폴더 이름이 `experiment` 필드와 맞는지 본다.

    폴더는 `<실험NN>/체크리스트/명세.md` 구조다. 리네임을 한 번 하고 끝내면
    다음 주차에 다시 어긋나므로, ⑤ 가 매 검토마다 이것을 부른다.
    """
    path = Path(spec_path).resolve()
    parents = path.parents
    if len(parents) < 2:
        return [Finding("error", str(spec_path),
                        "명세 경로가 `<실험NN>/체크리스트/명세.md` 형태가 아니다")]
    actual = parents[1].name
    try:
        expected = config.experiment_dir(spec.experiment)
    except (TypeError, ValueError) as e:
        # ⑤ 는 반쯤 망가진 문서에도 돌아야 한다. 여기서 죽으면 검토가 멈춘다.
        return [Finding("error", actual,
                        f"명세의 experiment 값을 폴더 이름으로 바꿀 수 없다: {e}")]
    if actual != expected:
        return [Finding("error", actual,
            f"폴더 이름이 `{actual}` 인데 명세의 `experiment: {spec.experiment}` 는 "
            f"`{expected}` 를 요구한다 — 둘 중 하나가 틀렸다")]
    return []
```

- [ ] **Step 8: 통과를 확인한다**

```bash
python3 -m unittest tests.test_lab_validate tests.test_lab_config 2>&1 | tail -4
```

Expected: OK

- [ ] **Step 9: 테스트에 실효가 있는지 뮤테이션으로 확인한다**

`check_folder_convention` 의 마지막 비교를 `if False:` 로 잠시 바꾸고 돌린다.

```bash
python3 -m unittest tests.test_lab_validate 2>&1 | tail -3
```

Expected: FAILED (failures=3) — `주차_이름`, `0을_안_채운`, `번호가_어긋나면` 세 개가 죽는다. 확인 후 되돌린다.

- [ ] **Step 10: 커밋**

```bash
git add scripts/lab/config.py scripts/lab/validate.py tests/test_lab_config.py tests/test_lab_validate.py && git commit -m "feat: 실험 폴더 명명 규약을 experiment_dir() 과 검사로 고정"
```

---

### Task 2: 폴더·산출물 리네임 + 픽스처·문서 갱신

리네임과 픽스처 갱신은 **한 커밋이어야 한다.** 폴더를 옮기는 순간 테스트 26곳이 깨지므로 쪼개면 중간 상태가 빨간불이다.

**Files:**
- Rename: `2주차/` → `실험01/`, `6주차/` → `실험06/`, `12주차/` → `실험10/`
- Rename: `실험01/output/2주차_예비보고서.{md,html,pdf}` → `실험01/output/실험01_예비보고서.{md,html,pdf}`
- Modify: `실험01/output/실험01_예비보고서.md` (내부 상호참조 8곳)
- Modify: `tests/test_lab_{md,record,render,spec_parser,validate,config}.py`
- Modify: `docs/schema/lab-spec-v1.md`

**Interfaces:**
- Consumes: `config.experiment_dir()` (Task 1)
- Produces: 이후 모든 태스크가 쓰는 실물 픽스처 경로 `실험01/체크리스트/명세.md`, `실험06/체크리스트/명세.md`, `실험10/체크리스트/명세.md`

- [ ] **Step 1: 리네임 전 상태를 기록한다**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | grep -E '^(Ran|OK|FAILED)'
```

Expected: `Ran 255 tests` / `OK` (Task 1 에서 245 + 10)

- [ ] **Step 2: 폴더를 옮긴다**

`12주차 → 실험10` 이다 (12 가 아니다). 매핑 표를 다시 볼 것.

```bash
git mv 2주차 실험01 && git mv 6주차 실험06 && git mv 12주차 실험10 && git status --short
```

Expected: `R` 로 시작하는 리네임 항목들. 내용 변경(`M`)은 없다.

- [ ] **Step 3: 산출물 파일명을 바꾼다**

```bash
for ext in md html pdf; do git mv "실험01/output/2주차_예비보고서.$ext" "실험01/output/실험01_예비보고서.$ext"; done && ls -1 실험01/output/
```

Expected: `pre_review_round1.md`, `실험01_예비보고서.html`, `실험01_예비보고서.md`, `실험01_예비보고서.pdf`

- [ ] **Step 4: 예비보고서 안의 상호참조 8곳을 고친다**

본문 제목의 `# 2주차 예비보고서` 와 부제의 `· 2주차 ·` 는 **그대로 둔다** — `week` 유지 결정이므로 사람이 읽는 표기에는 주차가 남는다. 바꾸는 것은 **경로**뿐이다.

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('실험01/output/실험01_예비보고서.md')
t = p.read_text(encoding='utf-8')
before = t.count('2주차/')
t = t.replace('2주차/체크리스트/', '실험01/체크리스트/').replace('2주차/결선도/', '실험01/결선도/')
assert '2주차/' not in t, '남은 경로: ' + t[t.index('2주차/')-40:t.index('2주차/')+40]
p.write_text(t, encoding='utf-8')
print(f'경로 참조 {before}곳 교체')
PY
```

Expected: `경로 참조 8곳 교체`

- [ ] **Step 5: 테스트 픽스처 경로를 고친다**

`"2주차" / "체크리스트"` 처럼 **따옴표가 나뉜 형태 2곳**은 단순 치환으로 안 잡힌다 (`tests/test_lab_config.py:102`, `tests/test_lab_validate.py:226`). 아래 스크립트가 둘 다 처리한다.

```bash
python3 - <<'PY'
from pathlib import Path
pairs = [('12주차', '실험10'), ('6주차', '실험06'), ('2주차', '실험01')]  # 12 를 먼저
total = 0
for f in sorted(Path('tests').glob('test_lab_*.py')):
    t = orig = f.read_text(encoding='utf-8')
    for old, new in pairs:
        t = t.replace(f'{old}/', f'{new}/').replace(f'"{old}"', f'"{new}"')
    if t != orig:
        f.write_text(t, encoding='utf-8')
        total += 1
        print('  갱신:', f.name)
print(f'{total}개 파일')
PY
```

**`12주차` 를 `2주차` 보다 먼저 치환해야 한다** — 순서를 바꾸면 `12주차` 가 `1실험01` 이 된다.

**치환 뒤 반드시 되돌려야 하는 곳이 하나 있다.** Task 1 이 만든
`test_주차_이름이_남아_있으면_잡는다` 는 `_spec_at("2주차", 1)` 로 **일부러 옛
이름**을 쓴다 — 그게 그 테스트의 전부다. 스크립트가 이것까지 `실험01` 로
바꾸면 폴더와 `experiment` 가 우연히 일치해 테스트가 공허하게 통과한다.

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('tests/test_lab_validate.py')
t = p.read_text(encoding='utf-8')
old = 'path, spec = self._spec_at("실험01", 1)\n        findings = validate.check_folder_convention(path, spec)'
new = 'path, spec = self._spec_at("2주차", 1)\n        findings = validate.check_folder_convention(path, spec)'
assert old in t, '이미 되돌려져 있거나 형태가 다르다 — 손으로 확인할 것'
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('옛 이름 픽스처 복원')
PY
```

Expected: `옛 이름 픽스처 복원`

Expected: 6개 파일 갱신 (`test_lab_config`, `test_lab_md`, `test_lab_record`, `test_lab_render`, `test_lab_spec_parser`, `test_lab_validate`)

- [ ] **Step 6: 오해를 부르는 루프 변수 이름을 고친다**

`tests/test_lab_validate.py` 의 `for week in (...)` 는 5단계 치환으로 값만 바뀌어
`for week in ("실험01", "실험06", "실험10")` 이 된다. 이름이 거짓말을 한다.

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('tests/test_lab_validate.py')
t = p.read_text(encoding='utf-8')
old = '''        for week in ("실험01", "실험06", "실험10"):
            with self.subTest(week=week):
                spec = parse_spec(ROOT / week / "체크리스트" / "명세.md")'''
new = '''        for folder in ("실험01", "실험06", "실험10"):
            with self.subTest(folder=folder):
                spec = parse_spec(ROOT / folder / "체크리스트" / "명세.md")'''
assert old in t, '5단계 치환 결과와 다르다 — 손으로 확인할 것'
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('루프 변수 week -> folder')
PY
```

Expected: `루프 변수 week -> folder`

- [ ] **Step 7: 잔재가 없는지 확인한다**

```bash
grep -rn '[0-9]주차[/_]' tests/*.py scripts/lab/*.py
```

**`[/_]` 의 밑줄이 중요하다.** `2주차_예비보고서.html` 처럼 슬래시가 아니라
밑줄로 이어지는 참조가 있고, `[0-9]주차/` 만 보면 그것을 놓친다. 실제로
`tests/test_lab_validate.py` 의 예비보고서 HTML 경로가 이 형태였다.

Expected: 출력 없음. 산문 주석(`notation.py` 의 `2주차 명세 T5`, `render.py` 의
`IC 가 적은 주차는`)과 일부러 옛 이름을 쓰는 픽스처는 경로가 아니므로 이
패턴에 걸리지 않는다.

- [ ] **Step 8: 테스트를 돌린다**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | grep -E '^(Ran|OK|FAILED)'
```

Expected: `Ran 255 tests` / `OK`

- [ ] **Step 9: 새 검사가 실물에서 통과하는지 본다**

```bash
python3 -c "
from pathlib import Path
from scripts.lab.spec_parser import parse_spec
from scripts.lab import validate
for d in ('실험01', '실험06', '실험10'):
    p = Path(d) / '체크리스트/명세.md'
    print(d, validate.check_folder_convention(p, parse_spec(p)) or '규약 일치')
"
```

Expected: 세 줄 모두 `규약 일치`

- [ ] **Step 10: 스키마 문서의 픽스처 경로를 고친다**

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('docs/schema/lab-spec-v1.md')
t = p.read_text(encoding='utf-8')
for old, new in [('12주차/', '실험10/'), ('6주차/', '실험06/'), ('2주차/', '실험01/')]:
    t = t.replace(old, new)
p.write_text(t, encoding='utf-8')
print('남은 주차 경로:', t.count('주차/'))
PY
```

Expected: `남은 주차 경로: 0`

- [ ] **Step 11: 커밋**

```bash
git add -A && git commit -m "refactor: 주차 폴더를 실험 폴더로 리네임 (2→실험01, 6→실험06, 12→실험10)"
```

---

### Task 3: `init-lab-week` → `init-lab-experiment`

폴더를 만드는 스킬이 옛 규약을 가르치고 있으면 다음 주에 `13주차/` 가 다시 생긴다.

**Files:**
- Rename: `.claude/skills/init-lab-week/` → `.claude/skills/init-lab-experiment/`
- Modify: `.claude/skills/init-lab-experiment/SKILL.md` (전면)

**Interfaces:**
- Consumes: `config.experiment_dir()` (Task 1)
- Produces: 다른 스킬이 "폴더가 없으면 안내"할 대상 이름 `init-lab-experiment`

- [ ] **Step 1: 스킬 폴더를 옮긴다**

```bash
git mv .claude/skills/init-lab-week .claude/skills/init-lab-experiment && ls .claude/skills/
```

Expected: `init-lab-experiment` 가 목록에 있고 `init-lab-week` 는 없다

- [ ] **Step 2: SKILL.md 를 새로 쓴다**

`.claude/skills/init-lab-experiment/SKILL.md` 전체를 아래로 바꾼다:

````markdown
---
name: init-lab-experiment
description: 논리회로실험 실험 폴더를 표준 7개 하위 폴더로 초기화한다. 사용자가 "실험5 폴더 만들어줘", "5주차 초기화", "다음 실험 폴더 세팅" 등을 요청하거나 /init-lab-experiment 를 호출할 때 사용한다. 주차로 말해도 실험 번호로 옮겨 만든다. 이미 있는 폴더는 건너뛰고 보고만 한다.
---

# init-lab-experiment

`실험NN/` 아래에 하네스가 전제하는 7개 하위 폴더를 만든다.
다른 스킬은 전부 이 구조가 이미 있다고 가정하고, 없으면 거절한 뒤 이 스킬을 안내한다.

## 실험 ↔ 주차 매핑 (**1:1 아님 — 3개 회전**)

| 실험 | 주 | 주제 | 실험 | 주 | 주제 |
|---|---|---|---|---|---|
| 1 | 2 | Basic Gates | 7 | 9 | Shift register |
| 2 | 3 | CMOS 전기적 특성 | 8 | 10 | Counter |
| 3 | 4 | Adder & Subtracter | 9 | 11 | RAM |
| **4** | **7** | **MUX & DEMUX** | 10 | 12 | D/A & A/D Converter |
| **5** | **5** | **Decoder & Encoder** | — | 13~15 | FPGA → `프로젝트/` |
| **6** | **6** | **Latch & Flip-flop** | — | 8 | 중간고사 → 폴더 없음 |

**실험4가 7주차다.** 5·6·7주차가 실험 5·6·4 로 어긋나는 것이 이 표의 요점이다.

## 실행 절차

1. **번호 추출 — 주차로 말해도 받는다.** 사용자 메시지에서 `실험N` 또는 `N주차` 를
   뽑는다. 주차로 왔으면 위 표로 실험 번호를 찾는다. 못 찾으면 한 줄로 되묻고 중단.

   - **8주차(중간고사)면 폴더를 만들지 않는다.** 실험 산출물이 없다고 한 줄로 알린다.
   - **13~15주차(FPGA)면** `실험NN/` 이 아니라 `프로젝트/` 를 쓴다. 3주치가 한
     프로젝트이므로 주차마다 폴더를 만들지 않는다. 4단계로 간다.

2. **프로젝트 루트 확인.** `.claude/` 를 가진 가장 가까운 상위 디렉토리를 찾는다.
   못 찾으면 거절한다 — 이 스킬은 논회실 프로젝트 안에서만 동작한다.

3. **폴더 이름을 코드로 만든다.** 손으로 `실험5` 라고 적지 않는다 — 0 을 안 채우면
   `실험10` 이 `실험2` 앞에 정렬된다.

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.experiment_dir(<N>))
   "
   ```

4. **폴더 생성.** 이미 있으면 건드리지 않는다.

   ```bash
   mkdir -p "<루트>/<폴더이름>"/{강의노트,체크리스트,결선도,실험사진,퀴즈,STT,output}
   ```

   `<폴더이름>` 은 3단계 출력(`실험05` 등) 또는 FPGA 면 `프로젝트`.

5. **매핑 안내.** 만든 실험이 몇 주차인지 위 표에서 알려준다. 5·6·7주차 구간이면
   어긋난다는 점을 함께 알린다 — 엉뚱한 교안을 여는 실수가 여기서 가장 잦다.

6. **교안 복사 제안.** `from_the_past/정리/강의노트/실험N.pdf` 가 있으면
   `<폴더이름>/강의노트/` 로 복사할지 한 줄로 묻는다. 2026-2 교안이 배포되면
   그것으로 교체해야 한다는 점을 함께 알린다.

7. **결과 보고.** 만든 폴더와 건너뛴 폴더를 한 줄로 정리한다.

## 비-목표

- 명세.md 를 생성하지 않는다 (교안 판독이 필요한 사람의 일이다).
- 기존 파일을 덮어쓰지 않는다.
- 주차 이름 폴더(`5주차/`)를 만들지 않는다. 규약은 실험 기준이고,
  `validate.check_folder_convention` 이 어긋남을 잡는다.
````

- [ ] **Step 3: 다른 스킬이 옛 이름을 안내하지 않는지 본다**

```bash
grep -rn 'init-lab-week' .claude/ docs/schema/ 2>/dev/null
```

Expected: 출력 없음이면 통과. 남아 있으면 Task 4 에서 함께 고친다 (같은 파일들이다).

- [ ] **Step 4: 폴더 이름 생성이 실제로 도는지 확인한다**

```bash
python3 -c "
from scripts.lab import config
print([config.experiment_dir(n) for n in (1, 5, 10)])
"
```

Expected: `['실험01', '실험05', '실험10']`

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: init-lab-week 를 init-lab-experiment 로 — 역매핑 표와 프로젝트/ 분기"
```

---

### Task 4: 나머지 6개 스킬의 경로 규약 갱신

**Files:**
- Modify: `.claude/skills/prep-lab-checklist/SKILL.md`
- Modify: `.claude/skills/review-lab-report/SKILL.md`
- Modify: `.claude/skills/write-pre-report/SKILL.md`
- Modify: `.claude/skills/write-result-report/SKILL.md`
- Modify: `.claude/skills/explain-lab-preview/SKILL.md`
- Modify: `.claude/skills/make-lab-report-cover/SKILL.md`

**Interfaces:**
- Consumes: `validate.check_folder_convention` (Task 1), `init-lab-experiment` 이름 (Task 3)
- Produces: 없음 (문서 변경)

- [ ] **Step 1: 경로 플레이스홀더를 일괄 치환한다**

`<N>주차` → `<실험NN>` 으로 바꾼다. 산문의 "주차"(예: "IC 가 적은 주차는")는 경로가 아니므로 건드리지 않는다 — 아래는 **경로 형태만** 잡는다.

```bash
python3 - <<'PY'
from pathlib import Path
import re
total = 0
for f in sorted(Path('.claude/skills').glob('*/SKILL.md')):
    if f.parent.name == 'init-lab-experiment':
        continue
    t = orig = f.read_text(encoding='utf-8')
    t = t.replace('<N>주차/', '<실험NN>/')          # 경로
    t = t.replace('<N>주차_', '<실험NN>_')          # 산출물 파일명
    t = t.replace('`<N>주차`', '`<실험NN>`')        # 폴더 자체를 가리키는 표기
    t = t.replace("Path('<N>주차')", "Path('<실험NN>')")
    t = t.replace('init-lab-week', 'init-lab-experiment')
    if t != orig:
        f.write_text(t, encoding='utf-8')
        n = len(re.findall(r'<실험NN>', t))
        print(f'  {f.parent.name}: <실험NN> {n}곳')
        total += 1
print(f'{total}개 스킬 갱신')
PY
```

Expected: 6개 스킬 갱신

- [ ] **Step 2: 남은 `<N>주차` 가 없는지 확인한다**

```bash
grep -rn '<N>주차' .claude/skills/
```

Expected: 출력 없음

- [ ] **Step 3: 산문에 남은 주차 표기를 눈으로 검토한다**

```bash
grep -rn '주차' .claude/skills/*/SKILL.md | grep -v 'init-lab-experiment' | grep -v '실험NN'
```

Expected: 남는 것은 매핑 설명·`{week}주차` 제목 형식 같은 **산문**뿐이어야 한다. 경로처럼 보이는 것이 있으면 손으로 고친다.

- [ ] **Step 4: ⑤ 에 새 검사를 배선한다**

`.claude/skills/review-lab-report/SKILL.md` 의 2단계 코드블록에서 `check_netlist` 호출 **앞에** 폴더 규약 검사를 넣는다. 아래 블록으로 통째로 바꾼다:

````markdown
2. **폴더 규약·명세·결선도 검증.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.spec_parser import parse_spec, SpecError
   from scripts.lab import validate
   spec_path = Path('<실험NN>/체크리스트/명세.md')
   try:
       spec = parse_spec(spec_path)
   except SpecError as e:
       print('SPEC-ERROR:', e); raise SystemExit(1)
   for f in validate.check_folder_convention(spec_path, spec):
       print(f)
   for f in validate.validate_spec(spec):
       print(f)
   for f in validate.check_netlist('<실험NN>/결선도/netlist.md', spec):
       print(f)
   "
   ```

   `SpecError` 가 나오면 그것을 **첫 번째 finding 으로 보고하고** 나머지 검사는 건너뛴다.

   폴더 규약 finding 은 "폴더 이름과 명세의 `experiment` 중 하나가 틀렸다"는 뜻이다.
   어느 쪽이 맞는지는 교안으로 확인한다 — 실험4는 7주차이므로 주차로 추측하면 틀린다.
````

- [ ] **Step 5: ⑤ 를 실물에 돌려 통과하는지 본다**

```bash
python3 -c "
from pathlib import Path
from scripts.lab.spec_parser import parse_spec
from scripts.lab import validate
sp = Path('실험01/체크리스트/명세.md')
spec = parse_spec(sp)
fs = (validate.check_folder_convention(sp, spec) + validate.validate_spec(spec)
      + validate.check_netlist('실험01/결선도/netlist.md', spec))
print('\n'.join(str(f) for f in fs) or '문제 없음')
"
```

Expected: `문제 없음`

- [ ] **Step 6: 커밋**

```bash
git add -A && git commit -m "refactor: 스킬 6종의 경로 규약을 <실험NN> 으로, ⑤ 에 폴더 규약 검사 배선"
```

---

### Task 5: 산출물 재생성 + end-to-end 재검증 + 설계문서 정정

리네임 뒤 산출물이 실제로 다시 나오는지 확인하지 않으면, 깨진 채로 커밋된다. 이 저장소에서 실제로 두 번 일어난 사고다.

**Files:**
- Regenerate: `실험01/체크리스트/기록.md`, `실험01/체크리스트/체크리스트.{html,pdf}`
- Modify: `docs/plans/2026-08-28-logic-lab-harness-design.md` (정정 주석 한 줄)

**Interfaces:**
- Consumes: Task 1~4 전부

- [ ] **Step 1: ② 를 새 경로로 끝까지 돌린다**

```bash
python3 -c "
from pathlib import Path
from scripts.lab import config
from scripts.lab.record import derive_record
from scripts.lab.render import render_checklist
from scripts.lab.spec_parser import parse_spec
from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf
root = config.find_project_root(Path('.'))
info = config.load_course_info(root)
spec = parse_spec('실험01/체크리스트/명세.md')
Path('실험01/체크리스트/기록.md').write_text(derive_record(spec), encoding='utf-8')
netlist = Path('실험01/결선도/netlist.md').read_text(encoding='utf-8')
tmpl = Path('.claude/skills/prep-lab-checklist/template.html').read_text(encoding='utf-8')
out = Path('실험01/체크리스트/체크리스트.html')
out.write_text(render_checklist(spec, netlist, tmpl), encoding='utf-8')
html_to_pdf(out, out.with_suffix('.pdf'), chrome=info.get('chrome') or DEFAULT_CHROME)
print('ok')
"
```

Expected: `ok`

- [ ] **Step 2: 제목에 주차가 유지됐는지 확인한다**

`week` 유지 결정이므로 인쇄물 제목은 `2주차 · 실험1 Basic Gates 체크리스트` 그대로여야 한다.

```bash
python3 -c "
from pypdf import PdfReader
r = PdfReader('실험01/체크리스트/체크리스트.pdf')
print('쪽수:', r.get_num_pages())
print('제목줄:', r.pages[0].extract_text().splitlines()[0])
for p in r.pages:
    w, h = float(p.mediabox.width)/72*25.4, float(p.mediabox.height)/72*25.4
    assert abs(w-210) < 1 and abs(h-297) < 1, f'A4 아님: {w}x{h}'
print('전 쪽 A4 확인')
"
```

Expected: `쪽수: 8`, 제목줄에 `2주차 · 실험1 Basic Gates 체크리스트`, `전 쪽 A4 확인`

- [ ] **Step 3: 재생성 결과가 리네임 전과 같은지 확인한다**

```bash
git status --short 실험01/체크리스트/
```

Expected: `체크리스트.pdf` 만 `M`. PDF 는 내장 타임스탬프 때문에 바이트가 달라진다 — `기록.md`·`체크리스트.html` 이 변경 목록에 없어야 한다. 있으면 리네임이 내용을 바꾼 것이므로 멈추고 원인을 찾는다.

- [ ] **Step 4: 예비보고서 HTML 의 경로 잔재를 고치고 PDF 를 다시 낸다**

Task 2 는 `.md` 의 경로만 고쳤다. 그 `.md` 로 만들어졌던 `.html`·`.pdf` 에는
`2주차/결선도/netlist.md` 같은 **옛 경로가 8곳 그대로 굳어 있다** — 제출물의
출처 표기가 존재하지 않는 경로를 가리키는 셈이다.

```bash
python3 - <<'PY'
from pathlib import Path
from scripts.lab import config
from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf
h = Path('실험01/output/실험01_예비보고서.html')
t = h.read_text(encoding='utf-8')
before = t.count('2주차/')
t = t.replace('2주차/체크리스트/', '실험01/체크리스트/').replace('2주차/결선도/', '실험01/결선도/')
assert '2주차/' not in t, '남은 경로가 있다'
h.write_text(t, encoding='utf-8')
info = config.load_course_info(config.find_project_root(Path('.')))
html_to_pdf(h, h.with_suffix('.pdf'), chrome=info.get('chrome') or DEFAULT_CHROME)
print(f'경로 {before}곳 교체 후 PDF 재생성')
PY
```

Expected: `경로 8곳 교체 후 PDF 재생성`

제목 `# 2주차 예비보고서` 와 부제 `· 2주차 ·` 는 여기서도 **그대로 둔다** —
`week` 유지 결정이다. 바꾸는 것은 경로뿐이다.

```bash
python3 -c "
from pypdf import PdfReader
r = PdfReader('실험01/output/실험01_예비보고서.pdf')
print('쪽수:', r.get_num_pages())
for p in r.pages:
    w, h = float(p.mediabox.width)/72*25.4, float(p.mediabox.height)/72*25.4
    assert abs(w-210) < 1 and abs(h-297) < 1, f'A4 아님: {w}x{h}'
print('전 쪽 A4 확인')
"
```

Expected: `쪽수: 16`, `전 쪽 A4 확인`

- [ ] **Step 5: 모든 HTML 산출물을 ⑤ 3b 로 검사한다**

```bash
python3 -c "
from pathlib import Path
from scripts.lab import validate
n = 0
for html in sorted(list(Path('실험01/output').glob('*.html'))
                   + list(Path('실험01/체크리스트').glob('*.html'))):
    fs = validate.check_rendered_html(html) + validate.check_embedded_images(html)
    print(f'  {html}: {len(fs)}건')
    n += len(fs)
print('합계', n, '건')
"
```

Expected: 두 파일 모두 `0건`, `합계 0 건`. 예비보고서의 브레드보드 그림 경로(`../../.claude/assets/`)가 리네임 뒤에도 풀리는지를 여기서 잡는다.

- [ ] **Step 6: 전체 테스트를 돌린다**

```bash
python3 -m unittest discover -s tests -t . 2>&1 | grep -E '^(Ran|OK|FAILED)'
```

Expected: `Ran 255 tests` / `OK`

- [ ] **Step 7: 설계문서에 정정 주석을 남긴다**

과거 계획서는 고쳐 쓰지 않지만, 설계문서는 **권위 문서**라 결정이 뒤집힌 사실을 모르면 다음 사람이 오해한다. 결정 표의 #4 행 한 줄만 바꾼다.

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('docs/plans/2026-08-28-logic-lab-harness-design.md')
t = p.read_text(encoding='utf-8')
old = '| 4 | 폴더 기준 | **주차** (`5주차/`) | 매핑은 폴더 내 메타에 기록 |'
new = ('| 4 | 폴더 기준 | ~~**주차** (`5주차/`)~~ → **실험** (`실험05/`) | '
       '2026-08-29 뒤집힘 — [실험 기준 명명 통일](2026-08-29-experiment-based-naming.md) 참조. '
       '매핑은 명세 프론트매터의 `week`·`experiment` 에 그대로 있다 |')
assert old in t, '결정 #4 행을 찾지 못했다'
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('설계문서 결정 #4 정정')
PY
```

Expected: `설계문서 결정 #4 정정`

- [ ] **Step 8: 저장소 전체에 경로 잔재가 없는지 최종 확인한다**

```bash
grep -rn '[0-9]주차[/_]' --include='*.py' --include='*.md' --include='*.html' . \
  | grep -v '^./docs/plans/2026-08-2[789]' | grep -v '^./from_the_past/' \
  | grep -v '^./.superpowers/' | grep -v '^./.agents/'
```

Expected: 출력 없음. 제외한 둘은 각각 **역사 기록**(과거 계획서)과 **읽기 전용 원본**이다.

- [ ] **Step 9: 커밋**

```bash
git add -A && git commit -m "chore: 실험 폴더로 산출물 재생성, 설계문서 결정 #4 정정"
```

---

## 완료 기준

- [ ] `실험01/`, `실험06/`, `실험10/` 이 존재하고 `2주차/`, `6주차/`, `12주차/` 는 없다
- [ ] `python3 -m unittest discover -s tests -t .` → 255 tests OK
- [ ] 세 명세 모두 `check_folder_convention` 이 finding 0
- [ ] `실험01/체크리스트/체크리스트.pdf` 8쪽 전 쪽 A4, 제목에 `2주차 · 실험1` 유지
- [ ] `<N>주차` 플레이스홀더가 스킬에 하나도 없다
- [ ] `init-lab-week` 이라는 이름이 저장소 어디에도 없다
- [ ] 설계문서 결정 #4 에 뒤집힘 표시가 있다

## 이 계획서가 하지 않는 것

- **과거 계획서 수정.** `docs/plans/2026-08-2[78]-*.md` 는 날짜가 박힌 역사 기록이다.
- **`프로젝트/` 폴더 생성.** FPGA 는 13주차다. 스킬이 다룰 줄만 알면 되고, 폴더는 그때 만든다.
- **`week` 필드 제거.** 유지 결정이다. 제목·시간순서 근거로 계속 쓴다.
- **실험02~05·07~09 폴더 생성.** 명세가 없는 빈 폴더는 만들지 않는다 — 교안 판독은 사람의 일이다.
