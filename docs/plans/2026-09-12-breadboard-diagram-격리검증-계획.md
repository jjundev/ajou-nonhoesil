# breadboard-diagram 격리 재생성 검증 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** breadboard-diagram SKILL.md 의 규칙만 읽은 격리 에이전트가 실험01 결선도 13장을 승인본과 같은 넷으로 다시 그리는지 재고, 갈린 자리마다 "규칙이 없었나 / 있는데 안 읽혔나" 를 가른 판정.md 를 낸다.

**Architecture:** `verify-draft-lab-spec` 의 틀(답안 제거 → 격리 실행 → 자동 대조 → 사람이 판정)을 빌린다. 답안이 파일 하나(`render_breadboard.py`)의 **일부**라 `isolate.build_isolated_tree` 에 커밋 전 편집 훅(`edit`)을 더하고, 실험01 구간을 걷어내는 `breadboard_isolate.py` 와 재생성 빌더를 승인본 빌더와 넷·자리·전환 수치·파일명으로 대조하는 `breadboard_compare.py` 를 새로 쓴다. 절차·답안지 목록·에이전트 프롬프트의 정본은 런북 `docs/verify/breadboard-diagram.md` 다(코드는 목록을 받기만 한다 — 이 저장소의 관례).

**Tech Stack:** Python 3.11 (`python`, `python -m unittest`), Pillow, Git Bash/PowerShell on Windows 11. 기존 모듈 `scripts/lab/isolate.py`·`hand_compare.py`·`netlist_parser.py`·`md.py` 재사용.

**Spec:** `docs/plans/2026-09-12-breadboard-diagram-격리검증-핸드오프.md` (핸드오프 원문). 설계 배경은 `docs/plans/2026-09-12-결선도-단계화-슬롯고정-설계.md`.

## Global Constraints

- 이 워크트리(`claude/quizzical-fermi-56e8c5`, `main` 과 같은 `c887280`)에는 결선도 작업이 **없다.** 16커밋은 `claude/determined-jepsen-20bb0e`(HEAD `93fd763`) 에만 있다. Task 0 이 그 브랜치를 이 브랜치에 합친다. `git merge-tree --write-tree main claude/determined-jepsen-20bb0e` 는 충돌 없이 트리 해시만 냈다(양쪽이 함께 고친 파일: `.claude/skills/write-pre-report/SKILL.md`, `scripts/lab/validate.py`, `tests/test_lab_validate.py`).
- `python` 을 쓴다. `python3` 은 이 머신에서 Microsoft Store 스텁이다. 파이썬 실행 파일: `E:\Python\python.exe`. Poppler: `C:\Users\Hyunjun\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin`.
- 테스트는 `python -m unittest tests.<모듈>` 표적 실행. 전체 실행의 기존 실패(핸드오프 §배경 목록 + `main` 쪽 추가분)는 이 계획이 건드리지 않는다.
- 커밋 트레일러: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` 를 글자 그대로.
- **승인본·breadboard-diagram SKILL.md·netlist.md 를 고치지 않는다.** 갈린 자리는 판정.md 에 적고 사용자에게 묻는 데서 끝난다(verify-draft-lab-spec §절대 규칙 6). 런북 기록 행은 적되 커밋은 사용자 결정.
- 한글을 찍는 `python -c` 가 `UnicodeEncodeError` 로 죽으면 `PYTHONUTF8=1 python -c …` 로 돌린다(Windows 콘솔 cp949).
- Git Bash 에서 `.claude/...` 로 시작하는 인자는 MSYS 경로 변환에 망가진다. `git show "$B:.claude/..."` 같은 명령 앞에 `export MSYS_NO_PATHCONV=1` 을 둔다. PowerShell 에서는 무관하다.
- 스크래치: `C:\Users\Hyunjun\AppData\Local\Temp\claude\C--Users-Hyunjun-Desktop------26-2------claude-worktrees-quizzical-fermi-56e8c5\406c1e33-d854-46c9-83a2-23c6605ad781\scratchpad` (아래 `<스크래치>`). 격리 트리는 `tempfile.gettempdir()` 아래 `iso-실험01-bb` (verify-write-result-report 와 같은 방식).
- 근거물은 저장소 안 `tmp/verify-artifacts/실험01-breadboard-격리-2026-09-12/` (`.gitignore` 의 `tmp/`).

## 핸드오프와 다른 결정

| # | 핸드오프 | 이 계획 | 근거 |
|---|---|---|---|
| 1 | 격리 트리를 스크래치패드에 | `tempfile.gettempdir()/iso-실험01-bb` | `verify-write-result-report` 가 이미 그렇게 하고, 스크래치 경로가 200자를 넘어 Windows 경로 한계에 가깝다 |
| 2 | `output/손그림검토/` 만 뺀다 | `output/` 내용물 전부 비운다 (`clear_subdirs=('output',)`) | 예비보고서 md 가 결선도 파일명 13개를 그대로 싣는다 — 파일명 규칙의 답이다. 손그림 최종통합본 PDF·표지도 같은 폴더다 |
| 3 | 실험사진·손그림 폴더 언급 없음 | `보고서/실험01/실험사진/`·`보고서/실험01/결선도/손그림/` 도 뺀다 | 실물 보드 사진과 손그림 스캔은 배선의 **그림 답안**이다. grep 은 못 보지만 에이전트는 이미지를 연다 |
| 4 | `export-hand-diagram` 스킬 언급 없음 | 뺀다 | 손그림 파일명 규칙에 실험01 예시가 있고 결선도 파일명 규칙과 같은 틀이다 |
| 5 | 전환 수치의 승인본 값은 설계 문서 표에서 | 같은 함수로 승인본 빌더를 직접 잰다 | 표를 베끼면 표가 낡았을 때 도구가 그것을 못 본다. 설계 표는 사람이 읽는 참고값으로만 남긴다 |
| 6 | `hand_grid.py` 언급 없음 | 남긴다 | 실험01 값이 없다. 렌더러 경로 상수뿐이다 |
| 7 | 절차를 세션 안에서 손으로 | 런북 `docs/verify/breadboard-diagram.md` 에 절차·답안지 목록·프롬프트를 적는다 | 실험03 저작 뒤 같은 검증을 다시 돈다. 이 저장소는 검증마다 런북이 있다 |

## 파일 구조

| 파일 | 책임 |
|---|---|
| `scripts/lab/isolate.py` (수정) | `build_isolated_tree(..., edit=None)` — 답안 삭제 뒤·`git init` 전에 트리를 편집하는 훅 |
| `scripts/lab/breadboard_isolate.py` (신규) | 렌더러 소스에서 한 주차 구간과 CLI 항목을 걷어낸다. `strip_section`·`strip_cli`·`strip_e1`·`strip_e1_file` |
| `scripts/lab/breadboard_compare.py` (신규) | 두 렌더러 모듈을 따로 로드해 보드 사슬을 그리고 넷(H1~H10·H14)·칩 자리·전환 수치·파일명을 대조, `judge()` 가 판정 초안 markdown |
| `tests/test_lab_breadboard_isolate.py` (신규) | 구간 제거 계약 |
| `tests/test_lab_breadboard_compare.py` (신규) | 승인본 자기대조 0건·자리표 일치·OR 전환 수치·파일명 규칙·짝 맺기·빌더 오류 격리 |
| `tests/test_lab_isolate.py` (수정) | `edit` 훅 테스트 한 개 |
| `docs/verify/breadboard-diagram.md` (신규) | 런북 — 질문·절대 규칙·절차·답안지 목록·누출 토큰·에이전트 프롬프트·기록 표 |
| `tmp/verify-artifacts/실험01-breadboard-격리-2026-09-12/` (실행 산출물, 미추적) | 재생성 PNG·`render_breadboard.py`·`격리보고.md`·`누출.txt`·`판정.md` |

---

### Task 0: 결선도 브랜치를 이 브랜치에 합친다

**Files:**
- Modify: (머지 커밋) — 새 파일 없음

**Interfaces:**
- Produces: HEAD 에 `E1_SLOTS`·`E1_BOARDS`·`snapshot()` 이 있는 `render_breadboard.py`, `kind: layout` 을 읽는 `netlist_parser.py`, 실험01 netlist·PNG 13장. 이후 모든 Task 가 이것을 전제한다.

- [ ] **Step 1: 합칠 수 있는지 확인한다**

```bash
git status --porcelain
git merge-tree --write-tree main claude/determined-jepsen-20bb0e
```

Expected: 첫 명령은 계획 문서 두 개(`docs/plans/2026-09-12-breadboard-diagram-격리검증-*.md`)만 untracked 로 보이거나 비어 있다. 둘째 명령은 트리 해시 한 줄만 낸다(충돌이면 `CONFLICT` 줄이 따라온다 — 그러면 멈추고 사용자에게 알린다).

- [ ] **Step 2: 계획 문서를 먼저 커밋한다**

```bash
git add docs/plans/2026-09-12-breadboard-diagram-격리검증-핸드오프.md docs/plans/2026-09-12-breadboard-diagram-격리검증-계획.md
git commit -m "docs(plans): breadboard-diagram 격리 재생성 검증 — 핸드오프와 구현 계획

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

- [ ] **Step 3: 합친다**

```bash
git merge --no-ff claude/determined-jepsen-20bb0e -m "merge: 결선도 단계화·슬롯 고정 (claude/determined-jepsen-20bb0e) 를 검증 브랜치에 합친다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

Expected: `Merge made by the 'ort' strategy.` 충돌 없음.

- [ ] **Step 4: 합친 결과가 살아 있는지 표적 테스트로 본다**

```bash
python -m unittest tests.test_breadboard_wiring tests.test_breadboard_baseline tests.test_lab_isolate tests.test_hand_compare tests.test_lab_netlist_parser 2>&1 | tail -5
python -m unittest tests.test_lab_validate 2>&1 | tail -5
```

Expected: 첫 묶음 `OK`. 둘째는 `test_optional_sections_are_not_required` 하나만 실패(작업 전부터 있던 것). 다른 실패가 나오면 양쪽이 함께 고친 `validate.py` 의 의미 충돌이다 — 멈추고 사용자에게 알린다.

- [ ] **Step 5: 승인본 값을 확인해 둔다** (이후 테스트 기대값의 근거)

```bash
python -c "
import os, tempfile
from scripts.lab.hand_grid import load_renderer
m = load_renderer()
d = tempfile.mkdtemp()
base = None
for name, fn, stage in m.E1_BOARDS:
    bb = fn(os.path.join(d, name), stage=stage, baseline=base)
    print(f'{name:60s} steps={len(bb.steps):2d} kept={len(bb.kept):2d} removed={len(bb.removed()):2d} partial={bb.partial}')
    base = bb.snapshot()
"
```

Expected: 9줄. `실험01_1-2_결선도_3입력_OR_1단계_칩교체.png` 행이 `steps= 1 kept=… removed= 0`. 출력을 이 계획 실행 노트에 남긴다(Task 3 런북 「승인본 기준 수치」 절에 붙인다).

---

### Task 1: 격리 편집 훅과 실험01 구간 제거기

**Files:**
- Modify: `scripts/lab/isolate.py:90-115` (`build_isolated_tree`)
- Create: `scripts/lab/breadboard_isolate.py`
- Test: `tests/test_lab_isolate.py` (한 개 추가), `tests/test_lab_breadboard_isolate.py` (신규)

**Interfaces:**
- Consumes: `isolate._git`, `isolate._restore`, 렌더러 소스의 구간 경계 규약 — 주차 구간 앞뒤에 `# ---------------------------------------------------------------------------` 줄이 있고 실험01 구간 머리는 `# 실험 1 · 기본 게이트 — 슬롯 고정 배치` 다(`render_breadboard.py:1505-1506`, 실험02 구간 머리는 `:1860-1861`).
- Produces:
  - `build_isolated_tree(root, dest, experiment, answer_keys, clear_subdirs=_CLEARED, keep=(), edit=None) -> Path` — `edit(dest: Path) -> None` 은 `keep` 복원 뒤·`git init` 전에 한 번 불린다.
  - `breadboard_isolate.strip_section(src: str, marker: str) -> str`
  - `breadboard_isolate.strip_cli(src: str, prefix: str) -> str`
  - `breadboard_isolate.strip_e1(src: str) -> str`
  - `breadboard_isolate.strip_e1_file(path) -> None`
  - `breadboard_isolate.RENDERER = ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"`

- [ ] **Step 1: `edit` 훅의 실패 테스트를 쓴다**

`tests/test_lab_isolate.py` 의 `class ResultReportMode` 끝에 추가:

```python
    def test_edit_훅은_커밋_전에_트리를_고친다(self):
        # 답안이 파일 일부일 때(결선도 빌더 구간) 파일을 지우는 대신 고쳐야 한다.
        # git init 전에 불려야 `git status` 도 이력도 원문을 말하지 않는다.
        dest = Path(tempfile.mkdtemp()) / "iso"

        def edit(tree):
            (tree / "keep.md").write_text("고쳐진 본문\n", encoding="utf-8")

        build_isolated_tree(self.root, dest, 1, [], edit=edit)
        self.assertEqual((dest / "keep.md").read_text(encoding="utf-8"), "고쳐진 본문\n")
        self.assertEqual(_git(dest, "status", "--porcelain"), "")
        self.assertEqual(_git(dest, "rev-list", "--count", "HEAD").strip(), "1")
        self.assertIn("고쳐진 본문", _git(dest, "show", "HEAD:keep.md"))
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python -m unittest tests.test_lab_isolate.ResultReportMode.test_edit_훅은_커밋_전에_트리를_고친다 2>&1 | tail -3
```

Expected: `TypeError: build_isolated_tree() got an unexpected keyword argument 'edit'`.

- [ ] **Step 3: 훅을 넣는다**

`scripts/lab/isolate.py` 의 `build_isolated_tree` 시그니처와 `keep` 복원 뒤:

```python
def build_isolated_tree(root, dest, experiment: int, answer_keys,
                        clear_subdirs=_CLEARED, keep=(), edit=None) -> Path:
    """…(기존 docstring 유지)…

    `edit(dest)` 는 답안 삭제·`keep` 복원 뒤, `git init` **전**에 한 번 불린다.
    답안이 파일 하나의 일부일 때(결선도 빌더 구간) 파일을 지우지 않고 고치는
    자리다 — 커밋 뒤에 고치면 `git show HEAD:…` 로 원문이 되살아난다.
    """
    …
    for rel in keep:
        _restore(archive, dest, rel)
    if edit is not None:
        edit(dest)

    _git(dest, "init", "-q")
```

- [ ] **Step 4: 통과를 확인한다**

```bash
python -m unittest tests.test_lab_isolate 2>&1 | tail -3
```

Expected: `OK`.

- [ ] **Step 5: 구간 제거기의 실패 테스트를 쓴다**

`tests/test_lab_breadboard_isolate.py`:

```python
"""렌더러에서 실험01 빌더 구간을 걷어내는 계약.

파일을 통째로 지우면 시험할 도구(렌더러 본체·verify()·기준선)가 없고, 통째로
두면 답안(E1_SLOTS·빌더)이 있다. 구간만 걷어낸 사본이 `ast.parse` 되고, 실험02
빌더는 남고, 실험01 토큰은 하나도 없어야 한다.
"""

import ast
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from scripts.lab.breadboard_isolate import (E1_MARKER, RENDERER, strip_cli, strip_e1,
                                            strip_e1_file, strip_section)

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / RENDERER).read_text(encoding="utf-8")

FAKE = (
    "import os\n"
    "\n"
    "# ---------------------------------------------------------------------------\n"
    "# 실험 1 · 가짜\n"
    "E1_X = 1\n"
    "def build_e1_a(p): return 1\n"
    "\n"
    "# ---------------------------------------------------------------------------\n"
    "# 실험 2 · 가짜\n"
    "def build_e2_a(p): return 2\n"
    "\n"
    "def main():\n"
    "    parser.add_argument('--circuit', choices=[\n"
    '        "e1_a", "e1_all",\n'
    '        "e2_a", "e2_all"\n'
    "    ])\n"
    "    dispatch = {\n"
    '        "e1_a": build_e1_a,\n'
    '        "e1_all": build_e1_all,\n'
    '        "e2_a": build_e2_a,\n'
    "    }\n"
)


class StripSection(unittest.TestCase):
    def test_머리_앞_경계부터_다음_경계_직전까지_걷어낸다(self):
        out = strip_section(FAKE, "# 실험 1 ·")
        self.assertNotIn("E1_X", out)
        self.assertNotIn("build_e1_a(p)", out)
        self.assertIn("# 실험 2 · 가짜", out)
        self.assertIn("def build_e2_a", out)
        self.assertIn("import os", out)

    def test_머리가_없으면_예외다(self):
        with self.assertRaises(ValueError):
            strip_section(FAKE, "# 실험 9 ·")

    def test_머리_앞줄이_경계가_아니면_예외다(self):
        # 첫 경계 줄(실험 1 바로 앞)만 무너뜨린다
        src = FAKE.replace("# ----", "# xxxx", 1)
        with self.assertRaises(ValueError):
            strip_section(src, "# 실험 1 ·")


class StripCli(unittest.TestCase):
    def test_choices_와_dispatch_에서_접두사_항목을_뺀다(self):
        out = strip_cli(FAKE, "e1_")
        self.assertNotIn('"e1_', out)
        self.assertIn('"e2_a", "e2_all"', out)
        self.assertIn('"e2_a": build_e2_a,', out)
        # 토큰을 뺀 뒤 공백만 남은 줄이 없다
        self.assertNotIn("\n        \n", out)


class RealRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = strip_e1(SRC)

    def test_원본에는_실험01_구간이_있다(self):
        self.assertIn(E1_MARKER, SRC)
        self.assertIn("E1_SLOTS", SRC)

    def test_실험01_토큰이_하나도_없다(self):
        for tok in ("E1_SLOTS", "E1_BOARDS", "E1_FINALS", "_e1_", "build_e1", '"e1_', "_E1_"):
            self.assertNotIn(tok, self.out, tok)

    def test_렌더러_본체와_실험02는_남는다(self):
        for tok in ("class BreadboardRenderer", "def snapshot", "def removed", "def verify",
                    "def mark_unused_inputs", "def build_e2_inv", "def build_e2_all",
                    '"e2_all": build_e2_all', "def main"):
            self.assertIn(tok, self.out, tok)

    def test_파싱된다(self):
        ast.parse(self.out)

    def test_걷어낸_사본이_import_되고_실험02_빌더가_돈다(self):
        d = Path(tempfile.mkdtemp())
        p = d / "render_breadboard.py"
        p.write_text(self.out, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("render_breadboard_stripped", str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertFalse(hasattr(mod, "build_e1_and"))
        bb = mod.build_e2_inv(str(d / "inv.png"),
                              template_path=str(ROOT / ".claude/assets/Breadboard.jpg"))
        self.assertTrue((d / "inv.png").exists())

    def test_strip_e1_file_은_제자리에서_고친다(self):
        d = Path(tempfile.mkdtemp())
        p = d / "render_breadboard.py"
        p.write_text(SRC, encoding="utf-8")
        strip_e1_file(p)
        self.assertNotIn("E1_SLOTS", p.read_text(encoding="utf-8"))
```

- [ ] **Step 6: 실패를 확인한다**

```bash
python -m unittest tests.test_lab_breadboard_isolate 2>&1 | tail -3
```

Expected: `ModuleNotFoundError: No module named 'scripts.lab.breadboard_isolate'`.

- [ ] **Step 7: 모듈을 쓴다**

`scripts/lab/breadboard_isolate.py`:

```python
"""격리 재생성용 — 렌더러에서 한 주차의 빌더 구간을 걷어낸다.

`isolate.build_isolated_tree` 는 파일 단위로 지운다. 결선도 검증은 파일 하나
(`render_breadboard.py`)의 **일부**가 답안이다 — 실험01 빌더 구간(`E1_SLOTS`·
`_e1_*`·`build_e1_*`·`E1_BOARDS`·`E1_FINALS`)은 지우고 렌더러 본체·`verify()`·
기준선 기능·실험02 빌더는 남겨야 한다. 파일을 통째로 지우면 시험할 도구가
없고, 통째로 두면 답안이 있다.

구간 경계는 렌더러 자신의 규약을 쓴다 — 주차 구간 앞뒤에
`# ----…` 줄이 있고 구간 머리가 `# 실험 N · …` 주석이다.

어느 **파일**을 지우는가(답안지 목록)는 여기 없다. 정본은
`docs/verify/breadboard-diagram.md` 다.
"""

import re
from pathlib import Path

RENDERER = ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
RULE = "# ----"            # 구간 경계 줄의 머리
E1_MARKER = "# 실험 1 ·"   # 실험01 구간 머리 주석의 머리


def strip_section(src: str, marker: str) -> str:
    """`marker` 로 시작하는 주석이 이끄는 구간을 걷어낸다.

    구간 = 그 주석 바로 앞의 경계 줄부터 다음 경계 줄 직전까지. 머리가 없거나
    둘 이상이거나 앞줄이 경계가 아니면 ValueError — 조용히 원본을 돌려주면
    답안이 든 트리로 시험을 돈다.
    """
    lines = src.splitlines(keepends=True)
    heads = [i for i, line in enumerate(lines) if line.startswith(marker)]
    if len(heads) != 1:
        raise ValueError(f"구간 머리 {marker!r} 가 {len(heads)}번 나온다 (1번이어야 한다)")
    i = heads[0]
    if i == 0 or not lines[i - 1].startswith(RULE):
        raise ValueError(f"{marker!r} 앞줄이 구간 경계({RULE}…)가 아니다")
    start = i - 1
    end = next((n for n in range(i + 1, len(lines)) if lines[n].startswith(RULE)),
               len(lines))
    return "".join(lines[:start] + lines[end:])


def strip_cli(src: str, prefix: str) -> str:
    """`main()` 의 `choices=[…]` 와 `dispatch = {…}` 에서 `prefix` 로 시작하는
    회로 ID 항목을 뺀다. 토큰을 뺀 뒤 공백만 남은 줄은 지운다."""
    p = re.escape(prefix)
    out = re.sub(rf'^[ \t]*"{p}\w*": \w+,[ \t]*\n', "", src, flags=re.M)
    out = re.sub(rf'"{p}\w*",[ \t]*', "", out)
    return "\n".join(line for line in out.split("\n") if line == "" or line.strip() != "")


def strip_e1(src: str) -> str:
    """실험01 답안 구간 + CLI 항목을 뺀 렌더러 소스."""
    return strip_cli(strip_section(src, E1_MARKER), "e1_")


def strip_e1_file(path) -> None:
    p = Path(path)
    p.write_text(strip_e1(p.read_text(encoding="utf-8")), encoding="utf-8")
```

- [ ] **Step 8: 통과를 확인한다**

```bash
python -m unittest tests.test_lab_breadboard_isolate 2>&1 | tail -3
```

Expected: `OK` (실험02 렌더 한 장 때문에 몇 초 걸린다). `test_파싱된다` 가 죽으면 `strip_cli` 의 줄 삭제가 `choices=[` 리스트 안 쉼표를 깨뜨린 것이다 — `"e1_all",` 뒤에 개행이 남아 `"e2_inv"` 가 다음 줄에 있어야 하므로, 원본 `render_breadboard.py:2145-2149` 를 열어 실제 줄바꿈 위치를 확인하고 정규식을 맞춘다.

- [ ] **Step 9: 커밋**

```bash
git add scripts/lab/isolate.py scripts/lab/breadboard_isolate.py tests/test_lab_isolate.py tests/test_lab_breadboard_isolate.py
git commit -m "feat(lab): breadboard_isolate — 렌더러의 실험01 빌더 구간만 걷어내는 격리 편집기와 isolate.build_isolated_tree edit 훅

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 대조기 `breadboard_compare.py`

**Files:**
- Create: `scripts/lab/breadboard_compare.py`
- Test: `tests/test_lab_breadboard_compare.py`

**Interfaces:**
- Consumes:
  - `scripts.lab.hand_compare._from_wiring(w, circuit_id) -> Diagram`, `compare(ref, hand) -> list[HandFinding]` (필드 `rule`·`grade`·`where`·`message`), `BLOCKING = ('치명', '기능')`
  - `scripts.lab.netlist_parser.parse_netlist(path)` → `.of_kind('layout')[0].body`, `.of_kind('circuit')` 의 `.item` (`E1.P1-1`)
  - `scripts.lab.md.parse_tables(body)[0].rows` (행마다 셀 리스트; 자리표 `| S1 | 좌 7행 | … |`)
  - 렌더러 인스턴스: `.wiring()`(`chips[i]` 는 `label`·`block`·`pin1_row`·`pins`), `.snapshot()`, `.steps`, `.kept`, `.removed()`, `.swaps`, `.partial`; 빌더 `build_e1_x(output_path, template_path=None, stage=None, baseline=None) -> bb`; `E1_BOARDS = [(파일명, 빌더, stage)]`, `E1_FINALS = [(파일명, 빌더)]`
- Produces (Task 3·6 이 부른다):
  - `load_renderer_at(path, name) -> module`
  - `@dataclass Board: name, cid, stage, bb, error`
  - `render_chain(boards, out_dir, template_path=None) -> list[Board]` — 앞 보드 `snapshot()` 을 기준선으로 이어 그린다
  - `render_finals(finals, out_dir, template_path=None) -> list[Board]`
  - `pair_boards(ref, new) -> list[tuple[Board, Board | None]]` + 짝 없는 재생성 보드는 `(None, Board)` 로 뒤에 붙는다
  - `net_findings(ref, new) -> list[HandFinding]` — H11·H12·H13(손그림 서류 규칙) 제외
  - `layout_slots(netlist_path) -> dict[str, tuple[str, int]]`
  - `seats(boards) -> dict[tuple[str, int], set[str]]`
  - `transition(board) -> dict` (`name`·`steps`·`kept`·`removed`·`swaps`·`partial`·`error`)
  - `sub_items(netlist_path) -> set[str]`, `check_filename(name, subs) -> str` (빈 문자열이면 합격)
  - `judge(experiment, approved_renderer, regen_renderer, netlist_path, regen_png_dir, template_path, leak_hits=(), agent_report="") -> str`

- [ ] **Step 1: 실패 테스트를 쓴다**

`tests/test_lab_breadboard_compare.py`:

```python
"""결선도 격리 재생성물 대조기의 계약.

승인본을 승인본과 대조하면 치명·기능 0건이어야 한다 — 검사기가 틀린 것을 먼저
가려낸다. 나머지는 자리표·전환 수치·파일명·짝 맺기·빌더 오류 격리.
"""

import os
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab import breadboard_compare as bc
from scripts.lab.breadboard_isolate import RENDERER

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = str(ROOT / ".claude/assets/Breadboard.jpg")
NETLIST = ROOT / config.experiment_dir(1) / "결선도/netlist.md"
PNG_DIR = ROOT / config.experiment_dir(1) / "결선도"


class Rendered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = bc.load_renderer_at(ROOT / RENDERER, "rb_test_approved")
        cls.tmp = tempfile.mkdtemp()
        cls.boards = bc.render_chain(cls.mod.E1_BOARDS, os.path.join(cls.tmp, "a"), TEMPLATE)
        cls.finals = bc.render_finals(cls.mod.E1_FINALS, os.path.join(cls.tmp, "f"), TEMPLATE)

    def test_보드_아홉_완성본_넷이_오류_없이_그려진다(self):
        self.assertEqual([b.error for b in self.boards], [""] * 9)
        self.assertEqual([b.error for b in self.finals], [""] * 4)
        self.assertEqual(self.boards[0].cid, "e1_and")
        self.assertEqual(self.boards[1].stage, None)
        self.assertEqual(self.boards[2].stage, 1)

    def test_자기대조는_치명_기능_0건(self):
        other = bc.load_renderer_at(ROOT / RENDERER, "rb_test_again")
        b2 = bc.render_chain(other.E1_BOARDS, os.path.join(self.tmp, "b"), TEMPLATE)
        for ref, new in zip(self.boards, b2):
            with self.subTest(ref.name):
                bad = [f for f in bc.net_findings(ref, new) if f.grade in bc.BLOCKING]
                self.assertEqual(bad, [], [str(x) for x in bad])

    def test_자기대조는_서류_규칙을_안_낸다(self):
        rules = {f.rule for f in bc.net_findings(self.boards[3], self.boards[3])}
        self.assertFalse(rules & {"H11", "H12", "H13"}, rules)

    def test_자리표는_빌더가_앉힌_자리와_같다(self):
        slots = bc.layout_slots(NETLIST)
        self.assertEqual(slots, self.mod.E1_SLOTS)
        used = set(bc.seats(self.boards + self.finals))
        self.assertEqual(used, set(slots.values()))

    def test_OR_전환은_칩_교체_한_줄_걷는_것_0(self):
        t = bc.transition(self.boards[1])
        self.assertEqual((t["steps"], t["removed"], t["swaps"]), (1, 0, 1))
        self.assertFalse(t["partial"])

    def test_복합_1단계는_partial_이고_걷는_것이_있다(self):
        t = bc.transition(self.boards[6])
        self.assertTrue(t["partial"])
        self.assertGreater(t["removed"], 0)


class Pairing(unittest.TestCase):
    def _b(self, name, cid="e1_x"):
        return bc.Board(name, cid, None, None, "")

    def test_이름이_같으면_이름으로_짝짓는다(self):
        ref = [self._b("a.png"), self._b("b.png")]
        new = [self._b("b.png"), self._b("a.png")]
        pairs = bc.pair_boards(ref, new)
        self.assertEqual([(r.name, n.name) for r, n in pairs],
                         [("a.png", "a.png"), ("b.png", "b.png")])

    def test_이름이_다르면_남은_것끼리_순서로_짝짓는다(self):
        ref = [self._b("a.png"), self._b("b.png"), self._b("c.png")]
        new = [self._b("x.png"), self._b("b.png"), self._b("y.png")]
        pairs = bc.pair_boards(ref, new)
        self.assertEqual([(r.name, n.name) for r, n in pairs],
                         [("a.png", "x.png"), ("b.png", "b.png"), ("c.png", "y.png")])

    def test_재생성이_모자라거나_남으면_None_으로_보인다(self):
        ref = [self._b("a.png"), self._b("b.png")]
        new = [self._b("a.png"), self._b("b.png"), self._b("z.png")]
        pairs = bc.pair_boards(ref, new)
        self.assertEqual(pairs[-1][0], None)
        self.assertEqual(pairs[-1][1].name, "z.png")
        pairs = bc.pair_boards(ref, new[:1])
        self.assertEqual(pairs[1][1], None)


class Filenames(unittest.TestCase):
    SUBS = {"1-1", "1-2", "2-1", "2-2", "3"}

    def test_netlist_에서_소단원_토큰을_뽑는다(self):
        self.assertEqual(bc.sub_items(NETLIST), self.SUBS)

    def test_승인본_13장은_전부_합격이다(self):
        for p in sorted(PNG_DIR.glob("*.png")):
            self.assertEqual(bc.check_filename(p.name, self.SUBS), "", p.name)

    def test_어긋난_이름은_이유를_낸다(self):
        for bad in ("실험1-1_결선도_AND.png", "실험01_1-1_AND.png", "실험01_9_결선도_AND.png",
                    "실험01_2-1_결선도_NAND_단계1.png", "e1_and.png"):
            self.assertNotEqual(bc.check_filename(bad, self.SUBS), "", bad)


class BrokenBuilder(unittest.TestCase):
    def test_빌더가_죽어도_사슬은_계속되고_오류가_남는다(self):
        def boom(path, template_path=None, stage=None, baseline=None):
            raise AssertionError("R2 한 홀에 리드 둘")

        def none_builder(path, template_path=None, stage=None, baseline=None):
            return None

        mod = bc.load_renderer_at(ROOT / RENDERER, "rb_test_broken")
        boards = bc.render_chain([("x.png", boom, None), ("y.png", none_builder, 1),
                                  mod.E1_BOARDS[0]], tempfile.mkdtemp(), TEMPLATE)
        self.assertIn("R2", boards[0].error)
        self.assertIn("돌려주지 않는다", boards[1].error)
        self.assertEqual(boards[2].error, "")
        t = bc.transition(boards[0])
        self.assertEqual(t["steps"], None)


class Judgment(unittest.TestCase):
    def test_승인본을_승인본과_대조한_판정문(self):
        md = bc.judge(1, ROOT / RENDERER, ROOT / RENDERER, NETLIST, PNG_DIR, TEMPLATE,
                      leak_hits=["a.md:1: E1_SLOTS"], agent_report="3. 첫 렌더 통과")
        for head in ("## 1. 구조적 누출 1건", "## 2. 보드 사슬", "## 3. 절차 그림 넷 대조",
                     "## 4. 완성본 넷 대조", "## 5. 칩 자리", "## 6. 전환 수치",
                     "## 7. 파일명 13", "## 8. 에이전트 보고", "## 9. 사람이 볼 것"):
            self.assertIn(head, md, head)
        self.assertIn("세션 메모리 주입", md)
        self.assertIn("치명 0 · 기능 0", md)
        self.assertIn("첫 렌더 통과", md)
```

- [ ] **Step 2: 실패를 확인한다**

```bash
python -m unittest tests.test_lab_breadboard_compare 2>&1 | tail -3
```

Expected: `ModuleNotFoundError: No module named 'scripts.lab.breadboard_compare'`.

- [ ] **Step 3: 모듈을 쓴다**

`scripts/lab/breadboard_compare.py`:

```python
"""결선도 격리 재생성물을 승인본과 대조한다.

**넷으로 본다, 홀로 보지 않는다** — `hand_compare` 와 같은 이유. 재생성 빌더가
칩을 한 행 위에 놓아도 넷이 같으면 그림은 유효하고, 그 좌표 차이는 H9·H10
(표기) 로만 나온다. 치명·기능이 나오면 넷이 다른 것이다.

네 축을 잰다.

1. 넷 — 보드마다 `hand_compare.compare(ref, hand)` (H1~H10·H14; 손그림 서류
   규칙 H11~H13 은 뺀다)
2. 자리 — 빌더가 실제로 앉힌 칩 자리 vs netlist `kind: layout` 표
3. 전환 — 보드 사슬을 기준선으로 이어 그렸을 때 `steps`·`kept`·`removed()`·
   `swaps` 수
4. 파일명 — `실험NN_<소단원>_결선도_<회로명>[_<k>단계_<이름>].png`

승인본 쪽 값도 **같은 함수로** 잰다 — 설계 문서의 표를 베끼면 표가 낡았을 때
도구가 그것을 못 본다. 두 렌더러 모듈은 이름을 달리해 따로 로드한다
(`hand_grid.load_renderer` 의 캐시 이름 `render_breadboard` 와 겹치지 않게).

판정은 사람이 한다. `judge()` 는 셀 수 있는 것만 세고 「사람이 볼 것」 으로 끝난다.
"""

import importlib.util
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import md
from .hand_compare import BLOCKING, _from_wiring, compare
from .netlist_parser import parse_netlist

PAPERWORK = ("H11", "H12", "H13")   # 제목·서명·전사 불확실 — 손그림에만 있는 것
_SEAT = re.compile(r"(좌|우)\s*(\d+)행")
_BLOCK = {"좌": "left", "우": "right"}
STAGE_RE = re.compile(r"^실험(\d{2})_(\d+(?:-\d+)?)_결선도_(.+)_(\d+)단계_([^_]+)\.png$")
FINAL_RE = re.compile(r"^실험(\d{2})_(\d+(?:-\d+)?)_결선도_(.+)\.png$")


def load_renderer_at(path, name):
    """렌더러 모듈을 경로에서 로드한다. `name` 은 모듈마다 달라야 한다."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@dataclass
class Board:
    name: str        # PNG 파일명
    cid: str         # 빌더 이름에서 `build_` 를 뗀 것 — hand_compare 의 회로 ID 자리
    stage: object    # None 이면 완성 상태
    bb: object       # 렌더러 (export 까지 마쳐 overlaps 가 차 있다). 죽었으면 None
    error: str       # 빌더가 죽었으면 그 메시지

    def __str__(self):
        return f"{self.name} ({self.cid}, stage={self.stage}){' ✗ ' + self.error if self.error else ''}"


def _cid(fn):
    return getattr(fn, "__name__", "?").removeprefix("build_")


def _call(fn, path, template_path, stage, baseline):
    """빌더를 규약 시그니처로 부른다. 시그니처가 다르면 위치 인자 둘로 한 번 더 —
    그것도 죽으면 오류 문자열. 어느 쪽이었는지는 오류 문자열에 남긴다."""
    try:
        return fn(path, template_path, stage=stage, baseline=baseline), ""
    except TypeError as e:
        try:
            return fn(path, template_path), f"stage/baseline 인자를 안 받는다 ({e})"
        except Exception as e2:  # noqa: BLE001 — 판정 재료다
            return None, f"{type(e2).__name__}: {e2}"
    except Exception as e:  # noqa: BLE001 — verify() 의 AssertionError 가 여기로 온다
        return None, f"{type(e).__name__}: {e}"


def render_chain(boards, out_dir, template_path=None):
    """`EN_BOARDS` 모양의 [(파일명, 빌더, stage)] 를 앞 보드를 기준선으로 이어 그린다.

    빌더가 죽으면 그 보드는 `error` 를 갖고 다음 보드는 기준선 없이 간다 —
    한 장이 죽었다고 사슬 전체를 못 보는 것보다 낫다.
    """
    os.makedirs(out_dir, exist_ok=True)
    out, base = [], None
    for name, fn, stage in boards:
        bb, err = _call(fn, os.path.join(out_dir, name), template_path, stage, base)
        if bb is None and not err:
            err = "빌더가 렌더러를 돌려주지 않는다 — 끝에 `return bb` 가 없다"
        out.append(Board(name, _cid(fn), stage, bb, err))
        base = bb.snapshot() if bb is not None else None
    return out


def render_finals(finals, out_dir, template_path=None):
    """완성본 — 기준선 없이."""
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for name, fn in finals:
        bb, err = _call(fn, os.path.join(out_dir, name), template_path, None, None)
        if bb is None and not err:
            err = "빌더가 렌더러를 돌려주지 않는다 — 끝에 `return bb` 가 없다"
        out.append(Board(name, _cid(fn), None, bb, err))
    return out


def pair_boards(ref, new):
    """이름이 같은 것끼리 먼저, 남은 것끼리는 순서로. 남는 쪽은 None 짝."""
    by_name = {b.name: b for b in new}
    pairs, used = [], set()
    for r in ref:
        if r.name in by_name:
            pairs.append([r, by_name[r.name]])
            used.add(r.name)
        else:
            pairs.append([r, None])
    rest = [b for b in new if b.name not in used]
    for p in pairs:
        if p[1] is None and rest:
            p[1] = rest.pop(0)
    pairs = [tuple(p) for p in pairs]
    pairs += [(None, b) for b in rest]
    return pairs


def _compare_diagrams(ref_d, new_d):
    new_d.signed = True
    new_d.title = ref_d.circuit
    return [f for f in compare(ref_d, new_d) if f.rule not in PAPERWORK]


def net_findings(ref, new):
    """승인본 보드 vs 재생성 보드. 어느 쪽이든 못 그렸으면 빈 목록 — 그 사실은
    `error` 가 따로 말한다."""
    if ref is None or new is None or ref.bb is None or new.bb is None:
        return []
    return _compare_diagrams(_from_wiring(ref.bb.wiring(), ref.cid),
                             _from_wiring(new.bb.wiring(), ref.cid))


def layout_slots(netlist_path):
    """netlist `kind: layout` 표 → {'S1': ('left', 7), …}. 절이 없으면 빈 dict."""
    layouts = parse_netlist(Path(netlist_path)).of_kind("layout")
    if not layouts:
        return {}
    slots = {}
    for row in md.parse_tables(layouts[0].body)[0].rows:
        m = _SEAT.search(row[1])
        if m:
            slots[row[0].strip()] = (_BLOCK[m.group(1)], int(m.group(2)))
    return slots


def seats(boards):
    """보드들이 실제로 앉힌 (block, pin1_row) → 그 자리에 앉았던 칩 라벨 집합."""
    out = {}
    for b in boards:
        if b.bb is None:
            continue
        for ch in b.bb.wiring()["chips"]:
            out.setdefault((ch["block"], ch["pin1_row"]), set()).add(ch["label"])
    return out


def transition(board):
    if board is None or board.bb is None:
        return {"name": board.name if board else "—", "steps": None, "kept": None,
                "removed": None, "swaps": None, "partial": None,
                "error": board.error if board else "짝 없음"}
    bb = board.bb
    return {"name": board.name, "steps": len(bb.steps), "kept": len(bb.kept),
            "removed": len(bb.removed()), "swaps": len(bb.swaps),
            "partial": bool(bb.partial), "error": board.error}


def sub_items(netlist_path):
    """회로 절의 `item`(`E1.P1-1`) 에서 `P` 뒤 토큰 — 파일명의 <소단원> 후보."""
    out = set()
    for sec in parse_netlist(Path(netlist_path)).of_kind("circuit"):
        if sec.item and ".P" in sec.item:
            out.add(sec.item.split(".P", 1)[1])
    return out


def check_filename(name, subs):
    """규칙에 맞으면 ''. 아니면 이유 한 줄."""
    m = STAGE_RE.match(name) or FINAL_RE.match(name)
    if not m:
        return "틀이 `실험NN_<소단원>_결선도_<회로명>[_<k>단계_<이름>].png` 가 아니다"
    if m.group(2) not in subs:
        return f"<소단원> `{m.group(2)}` 이 명세 항목에 없다 (후보: {', '.join(sorted(subs))})"
    if not STAGE_RE.match(name) and re.search(r"_단계\d+|단계_\d+|_\d+단계$", m.group(3)):
        return "단계 표기가 `_<k>단계_<이름>` 순서가 아니다"
    return ""


def _grade_counts(findings):
    c = {"치명": 0, "기능": 0, "표기": 0, "보류": 0}
    for f in findings:
        c[f.grade] = c.get(f.grade, 0) + 1
    return c


def _pair_table(pairs, title):
    L = [f"### {title}", "", "| 승인본 | 재생성 | 치명 | 기능 | 표기 | 빌더 오류 |", "|---|---|---|---|---|---|"]
    detail, every = [], []
    for ref, new in pairs:
        fs = net_findings(ref, new)
        every += fs
        c = _grade_counts(fs)
        err = (ref.error if ref else "") or (new.error if new else "")
        L.append(f"| {ref.name if ref else '—'} | {new.name if new else '—'} | "
                 f"{c['치명']} | {c['기능']} | {c['표기']} | {err} |")
        for f in fs:
            detail.append(f"- {ref.name if ref else new.name} · {f.rule} {f.grade} · {f.where}: {f.message}")
    total = _grade_counts(every)
    L += ["", f"합계 치명 {total['치명']} · 기능 {total['기능']} · 표기 {total['표기']}", ""]
    L += detail + [""]
    return L


def judge(experiment, approved_renderer, regen_renderer, netlist_path, regen_png_dir,
          template_path, leak_hits=(), agent_report=""):
    """판정 초안. 셀 수 있는 것만 센다 — 갈린 자리에 규칙이 있었는지는 사람이
    SKILL.md 와 에이전트 보고를 놓고 가른다."""
    ref_mod = load_renderer_at(approved_renderer, f"rb_approved_e{experiment}")
    new_mod = load_renderer_at(regen_renderer, f"rb_regen_e{experiment}")
    boards_attr, finals_attr = f"E{experiment}_BOARDS", f"E{experiment}_FINALS"
    slots = layout_slots(netlist_path)
    subs = sub_items(netlist_path)
    regen_pngs = sorted(p.name for p in Path(regen_png_dir).glob("*.png"))

    with tempfile.TemporaryDirectory() as d:
        ref_b = render_chain(getattr(ref_mod, boards_attr), os.path.join(d, "ra"), template_path)
        ref_f = render_finals(getattr(ref_mod, finals_attr), os.path.join(d, "rf"), template_path)
        new_boards = getattr(new_mod, boards_attr, None)
        new_finals = getattr(new_mod, finals_attr, None)
        new_b = render_chain(new_boards, os.path.join(d, "na"), template_path) if new_boards else []
        new_f = render_finals(new_finals, os.path.join(d, "nf"), template_path) if new_finals else []

        L = [f"# 실험{experiment} breadboard-diagram 격리 재생성 판정 초안", "",
             "이 회차는 세션 메모리 주입 아래서 돌았다(verify-draft-lab-spec §절대 규칙 7).", "",
             f"## 1. 구조적 누출 {len(leak_hits)}건", ""]
        L += [f"- {h}" for h in leak_hits] + [""]

        nb = f"{len(new_b)}장" if new_boards else f"`{boards_attr}` 없음"
        nf = f"{len(new_f)}장" if new_finals else f"`{finals_attr}` 없음"
        L += [f"## 2. 보드 사슬 — 승인본 {len(ref_b)}장+완성본 {len(ref_f)}장 / 재생성 {nb}+완성본 {nf}", ""]
        L += [f"- 재생성 {b}" for b in new_b + new_f] + [""]

        bp = pair_boards(ref_b, new_b)
        fp = pair_boards(ref_f, new_f)
        L += ["## 3. 절차 그림 넷 대조 (H1~H10·H14 — 홀이 달라도 넷이 같으면 표기만 난다)", ""]
        L += _pair_table(bp, "절차 그림")
        L += ["## 4. 완성본 넷 대조", ""]
        L += _pair_table(fp, "완성본")

        used = seats(new_b + new_f)
        L += ["## 5. 칩 자리 — netlist `kind: layout` vs 재생성 보드가 앉힌 자리", "",
              "| 슬롯 | 자리표 | 재생성이 그 자리에 앉힌 칩 |", "|---|---|---|"]
        for s, seat in slots.items():
            L.append(f"| {s} | {seat[0]} {seat[1]} | {', '.join(sorted(used.get(seat, set()))) or '—'} |")
        extra = {k: v for k, v in used.items() if k not in set(slots.values())}
        L += [""] + [f"- 자리표 밖 자리: {k[0]} {k[1]} ← {', '.join(sorted(v))}" for k, v in extra.items()] + [""]

        L += ["## 6. 전환 수치 (steps = 번호 받은 줄 · kept = 회색 · removed = 걷는다 표 · swaps = 칩 교체/삽입)", "",
              "| 승인본 | steps | kept | removed | swaps | partial | 재생성 | steps | kept | removed | swaps | partial |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for ref, new in bp:
            a, b = transition(ref), transition(new)
            L.append(f"| {a['name']} | {a['steps']} | {a['kept']} | {a['removed']} | {a['swaps']} | {a['partial']} "
                     f"| {b['name']} | {b['steps']} | {b['kept']} | {b['removed']} | {b['swaps']} | {b['partial']} |")
        L.append("")

        bad = [(n, check_filename(n, subs)) for n in regen_pngs]
        bad = [(n, why) for n, why in bad if why]
        L += [f"## 7. 파일명 {len(regen_pngs)}장 중 규칙 위반 {len(bad)}건", ""]
        L += [f"- {n}: {why}" for n, why in bad]
        L += [f"- (전체) {n}" for n in regen_pngs] + [""]

        L += ["## 8. 에이전트 보고 (원문)", "", agent_report or "(없음)", ""]
        L += ["## 9. 사람이 볼 것",
              "- 3·4절의 치명·기능마다: SKILL.md 에 그 넷을 정하는 문장이 **있었는가**(있는데 안 읽힘) / **없었는가**(규칙 없음). 8절 3항의 첫 렌더 결과로 verify() 가 잡았는지도 가른다.",
              "- 5절: 자리가 다르면 「슬롯」 문단이 자리 **선택**을 지시하는지 본다 — 자리표는 netlist 가 주므로 여기서 갈리면 netlist 를 안 읽은 것이다.",
              "- 6절: 재생성 kept 가 승인본보다 작으면 공통 배선을 같은 헬퍼·같은 순서로 안 그린 것(「기준선」 문단). removed 가 다르면 단계 분해가 다른 것.",
              "- 7절: 파일명 갈림은 「파일명 규칙」 문단이 <소단원>·<이름> 을 어디서 가져오라 했는지 본다.",
              "- 1절의 누출 자리와 일치하는 것은 합격 근거로 세지 않는다.",
              "", "> 치명 0 은 넷이 같다는 뜻이고, 그림이 따라 그리기 좋다는 뜻이 아니다. PNG 는 눈으로 한 번 본다.", ""]
    return "\n".join(L)
```

- [ ] **Step 4: 통과를 확인한다**

```bash
python -m unittest tests.test_lab_breadboard_compare 2>&1 | tail -5
```

Expected: `OK` (보드 렌더 50장 남짓, 1~2분). 실패 가능성이 있는 자리와 대응:
- `test_자기대조는_치명_기능_0건` 에서 `e1_comb` 계열이 H5·H6 을 낸다면 `_from_wiring` 의 브리지 걸러내기나 미사용 출력 판정이 단계 그림의 `partial` 상태와 맞물린 것이다 — `tests/test_hand_compare.py::SelfCompare` 가 `e1_comb` 를 뺀 이유가 그것일 수 있다. 그 경우 테스트를 낮추지 말고, 실제 finding 을 읽어 `net_findings` 에서 **원인에 맞게** 거른다(예: 양쪽 다 `partial` 인 보드끼리는 H5 를 뺀다). 거른 규칙과 이유는 모듈 docstring 에 적는다.
- 콘솔이 `UnicodeEncodeError` 를 내면 `PYTHONUTF8=1` 을 앞에 붙인다(Global Constraints).

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/breadboard_compare.py tests/test_lab_breadboard_compare.py
git commit -m "feat(lab): breadboard_compare — 결선도 재생성물을 승인본과 넷·칩 자리·전환 수치·파일명으로 대조하고 판정 초안을 낸다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 런북 `docs/verify/breadboard-diagram.md`

**Files:**
- Create: `docs/verify/breadboard-diagram.md`

**Interfaces:**
- Consumes: Task 1·2 의 함수 이름, Task 0 Step 5 의 승인본 수치 출력.
- Produces: Task 4~6 이 **그대로 복사해 실행하는** 명령과 프롬프트. 답안지 목록의 정본.

- [ ] **Step 1: 런북을 쓴다**

`docs/verify/breadboard-diagram.md` (아래 전문. `<poppler 경로>` 는 Global Constraints 의 값으로 채워 넣는다):

````markdown
# `breadboard-diagram` 격리 재생성 런북

**질문.** `breadboard-diagram/SKILL.md` 의 규칙(슬롯·기준선·단계·파일명)만 읽은
에이전트가 실험01 결선도 13장을 승인본과 같은 넷으로 다시 그리는가. 갈리는
자리 = SKILL.md 에 더 적어야 할 규칙. 새 주차(실험03)를 저작하기 전에 안다.

`verify-draft-lab-spec` 의 틀(답안 제거 → 격리 실행 → 자동 대조 → 사람이 판정)을
빌린다. 그 스킬의 §절대 규칙 1~7 이 그대로 적용된다. 다른 점은 답안이 파일
하나의 **일부**라는 것 — `render_breadboard.py` 에서 실험01 구간만 걷어낸다
(`scripts/lab/breadboard_isolate.py`). 대조는 `scripts/lab/breadboard_compare.py`.

## 절대 규칙 (verify-draft-lab-spec 과 같다 — 여기 다시 적는 이유는 그 스킬 폴더가
격리 트리에서 지워지기 때문이다)

1. 답안지를 전부 뺀 트리에서만 돈다. 목록은 §답안지 목록.
2. 못 빼는 누출은 적는다. SKILL.md §3 회로 ID 목록·§4a 「슬롯·기준선·단계」·
   「파일명 규칙」 문단, `docs/schema/lab-netlist-v2.md` 의 `E1_SLOTS` 언급,
   그리고 **netlist.md 의 `## 단계` 표 자체**(`c7→c9`·`b19`·`a8→a18` 같은 홀
   주소를 적는다 — 그것이 입력이다)는 계약서라 못 뺀다. 판정.md 1절에 적고
   그 자리의 일치는 합격 근거로 세지 않는다.
3. 프롬프트에 사유와 합격 조건을 쓰지 않는다. 이력 명령도 금지.
4. 규칙이 막았는지 검사(`verify()`)가 잡았는지를 가른다. 에이전트 보고 3항이
   근거다. 첫 렌더 통과인데 승인본과 갈렸으면 규칙도 검사도 없는 자리다.
5. 자동 합격은 없다. 치명 0 은 넷이 같다는 뜻일 뿐이다.
6. 아무것도 고치지 않는다 — SKILL.md 도 승인본도. 갈린 자리는 묻고 멈춘다.
7. 세션 메모리 주입을 판정.md 첫 줄에 적는다(`judge()` 가 넣는다).

## 실행 절차

0. **통제군과 작업 트리를 확인한다.**

   ```bash
   python -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.breadboard_isolate import RENDERER
   d = Path(config.experiment_dir(1))
   for f in ('결선도/netlist.md', '체크리스트/명세.md'):
       print('O' if (d / f).exists() else 'X', d / f)
   print(len(list((d / '결선도').glob('*.png'))), 'png (13 이어야 한다)')
   print('E1_SLOTS' in Path(RENDERER).read_text(encoding='utf-8'), '승인본 빌더 있음')
   "
   git status --porcelain .claude/skills/breadboard-diagram scripts/lab docs/schema 보고서/실험01
   ```

   `X`·13 아님·`False`·비어 있지 않은 status 중 하나라도 있으면 멈춘다 —
   격리 트리는 `git archive HEAD` 다.

1. **격리 트리를 만든다.** 답안지 목록은 §답안지 목록을 **그대로** 옮긴다.

   ```bash
   python -c "
   import tempfile
   from pathlib import Path
   from scripts.lab.isolate import build_isolated_tree
   from scripts.lab.breadboard_isolate import RENDERER, strip_e1_file
   KEYS = [
       '.claude/skills/verify-draft-lab-spec', '.claude/skills/verify-write-result-report',
       '.claude/skills/review-hand-diagram', '.claude/skills/export-hand-diagram',
       '.claude/skills/write-pre-report', '.claude/skills/prep-lab-checklist',
       'docs/verify', 'docs/plans', 'docs/study', 'docs/rule-friction',
       'docs/notion-feedback', 'docs/corpus-audit', 'docs/강의노트_이론_실험_매핑_정리.md',
       'scripts/lab/hand_compare.py', 'scripts/lab/hand_transcript.py',
       'scripts/lab/export_hand_diagrams.py', 'scripts/lab/contact_sheet.py',
       'scripts/lab/breadboard_isolate.py', 'scripts/lab/breadboard_compare.py',
       'scripts/lab/isolate.py', 'scripts/lab/regen_compare.py', 'scripts/lab/specdiff.py',
       'scripts/lab/report_compare.py', 'tests',
       '보고서/실험01/결선도/*.png', '보고서/실험01/결선도/손그림',
       '보고서/실험01/체크리스트/체크리스트.html', '보고서/실험01/체크리스트/체크리스트.pdf',
       '보고서/실험01/실험사진', '보고서/실험01/실험중있었던일.md',
       '보고서/실험01/*예비보고서*.pdf',
   ]
   dest = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
   build_isolated_tree(Path('.'), dest, 1, KEYS, clear_subdirs=('output',),
                       edit=lambda t: strip_e1_file(t / RENDERER))
   print(dest)
   "
   ```

   남는 것: `breadboard-diagram/SKILL.md`·걷어낸 `render_breadboard.py`·
   `.claude/assets/Breadboard.jpg`·`보고서/실험01/결선도/netlist.md`(입력)·
   `체크리스트/{명세,기록}.md`·`docs/schema/`·`강의노트/`·`.claude/데이터시트_출처.md`·
   `draft-lab-spec` 등 나머지 스킬·`scripts/lab/` 나머지·다른 실험 폴더.

2. **누출을 훑는다.**

   ```bash
   python -c "
   import tempfile
   from pathlib import Path
   from scripts.lab.isolate import leak_scan
   dest = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
   TOKS = ['E1_SLOTS', '_e1_', 'build_e1', 'E1_BOARDS', '결선도_3입력', '결선도_복합',
           '1단계_', '좌 7행', '좌 18행', '우 10행', 'c7→c9', 'a25', 'c9→c14', 'b19']
   hits = leak_scan(dest, TOKS)
   Path('tmp/verify-artifacts').mkdir(parents=True, exist_ok=True)
   Path('tmp/verify-artifacts/누출-실험01-bb.txt').write_text('\n'.join(hits), encoding='utf-8')
   for h in hits: print(h)
   print(len(hits), '건')
   "
   ```

   **정상(구조적 누출)**: `.claude/skills/breadboard-diagram/SKILL.md`,
   `docs/schema/lab-netlist-v2.md`, `보고서/실험01/결선도/netlist.md`,
   `.claude/skills/draft-lab-spec/SKILL.md`(파일명 예시), `scripts/lab/render.py`·
   `validate.py`(단계 표 열 이름), `보고서/실험01/체크리스트/{명세,기록}.md`.
   **그 밖의 파일**이 나오면 §답안지 목록에 더하고 1단계부터 다시 한다.

3. **대조 도구를 자기대조로 점검한다.**

   ```bash
   python -m unittest tests.test_lab_breadboard_compare.Rendered.test_자기대조는_치명_기능_0건 tests.test_lab_breadboard_compare.Rendered.test_자리표는_빌더가_앉힌_자리와_같다 2>&1 | tail -3
   ```

   `OK` 여야 한다.

4. **에이전트를 띄운다.** Agent 도구, 기본 모델, 백그라운드. §에이전트 프롬프트를
   글자 그대로 쓰고 `<작업 디렉토리>` 만 1단계가 찍은 경로로 채운다. 기다리는
   동안 격리 트리와 승인본은 건드리지 않는다. 형제 검증의 실측은 305k 토큰·21분.

5. **산출물을 보존한다.** 끝나면 격리 트리에서 저장소 `tmp/verify-artifacts/
   실험01-breadboard-격리-<YYYY-MM-DD>/` 로 복사한다: `보고서/실험01/결선도/`
   (재생성 PNG), `.claude/skills/breadboard-diagram/scripts/render_breadboard.py`
   (재생성 빌더 — `render_breadboard.py` 이름 그대로), `tmp/격리보고.md`, 그리고
   2단계의 `누출-실험01-bb.txt`. 격리 트리를 지우기 전에 한다.

6. **판정 초안을 낸다.** 승인본 템플릿 경로를 명시해 넘긴다 — 복사한 재생성
   렌더러는 `REPO_ROOT` 가 어긋나 템플릿을 스스로 못 찾는다.

   ```bash
   python -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.breadboard_compare import judge
   from scripts.lab.breadboard_isolate import RENDERER
   art = Path('tmp/verify-artifacts/실험01-breadboard-격리-<YYYY-MM-DD>')
   leaks = [l for l in (art / '누출-실험01-bb.txt').read_text(encoding='utf-8').splitlines() if l]
   report = (art / '격리보고.md').read_text(encoding='utf-8') if (art / '격리보고.md').exists() else ''
   out = art / '판정.md'
   out.write_text(judge(1, Path(RENDERER), art / 'render_breadboard.py',
                        Path(config.experiment_dir(1)) / '결선도/netlist.md', art / '결선도',
                        str(Path('.claude/assets/Breadboard.jpg').resolve()),
                        leak_hits=leaks, agent_report=report), encoding='utf-8')
   print(out.read_text(encoding='utf-8'))
   "
   ```

   재생성 모듈에 `E1_BOARDS` 가 없으면 2절이 그렇게 말한다. 그러면 재생성
   `render_breadboard.py` 를 읽어 `[(파일명, 빌더, stage)]` 목록을 손으로 만들어
   `render_chain` 에 넘기는 짧은 스크립트로 3~6절을 다시 낸다 — 그 사실 자체가
   「주차 빌더를 쓸 때」 문단의 판정 재료다.

7. **사람이 본다.** 판정.md 9절을 하나씩 짚고, 재생성 PNG 13장을 승인본과
   나란히 눈으로 본다(회색 기준선이 실제로 회색인지, 번호가 새 배선에만
   붙었는지). 결과를 판정.md 끝에 "## 10. 판정" 으로 적는다: 넷·자리·전환·
   파일명의 일치 여부, 갈린 자리와 그 자리에 규칙·검사가 있었는지, 원본 쪽 결함.

8. **기록 표에 행을 붙인다.** 이 문서 `## 기록` 표 마지막 행 뒤에 한 줄. 커밋은
   사용자 결정.

9. **보고한다.** 세 가지 — 일치한 것, 갈린 자리와 규칙·검사 유무, 원본·도구 쪽
   결함. 갈린 자리마다 SKILL.md 의 어느 절에 무엇을 더 쓰면 닫히는지 **제안**
   하고 사용자에게 묻는다. SKILL.md 수정은 이 런북 밖이다. 격리 트리를 지운다.

## 답안지 목록

격리 트리에서 지우는 것. 정본은 이 절이고 1단계의 `KEYS` 는 이것을 옮긴 것이다.

- `.claude/skills/verify-draft-lab-spec/`·`verify-write-result-report/` — 시험
  형식과 답안지 목록·합격 조건
- `.claude/skills/review-hand-diagram/` — H 규칙 표와 실험01 판정 사례
- `.claude/skills/export-hand-diagram/` — 손그림 파일명 규칙(결선도와 같은 틀)의 실험01 예시
- `.claude/skills/write-pre-report/`·`prep-lab-checklist/` — 실험01 배치·파일명 예시
- `docs/verify/`·`docs/plans/` — 이 런북·설계·계획. 합격 조건과 승인본 수치 표
- `docs/study/`·`docs/rule-friction/`·`docs/notion-feedback/`·`docs/corpus-audit/`·
  `docs/강의노트_이론_실험_매핑_정리.md` — 파생 서술
- `scripts/lab/hand_compare.py`·`hand_transcript.py`·`export_hand_diagrams.py`·
  `contact_sheet.py` — 실험01 회로 ID 와 배치를 안다
- `scripts/lab/breadboard_isolate.py`·`breadboard_compare.py`·`isolate.py`·
  `regen_compare.py`·`specdiff.py`·`report_compare.py` — docstring 이 채점 기준
- `tests/` — 실험01 값을 픽스처로 단언한다
- `render_breadboard.py` 의 실험01 구간 — `strip_e1_file` 이 걷어낸다(파일은 남는다)
- `보고서/실험01/결선도/*.png`·`결선도/손그림/` — 답 그 자체와 손그림 스캔
- `보고서/실험01/체크리스트/체크리스트.{html,pdf}` — 단계 그림이 박혀 있다
- `보고서/실험01/output/` 내용물 전부 — 예비보고서 md 가 파일명 13개를 싣는다.
  손그림검토 라운드에 전사 JSON 과 판정이 있다
- `보고서/실험01/실험사진/`·`실험중있었던일.md`·`*예비보고서*.pdf` — 실물 보드
  사진·실험실 기록·제출본

## 누출 토큰

`E1_SLOTS`·`_e1_`·`build_e1`·`E1_BOARDS`·`결선도_3입력`·`결선도_복합`·`1단계_`·
`좌 7행`·`좌 18행`·`우 10행`·`c7→c9`·`a25`·`c9→c14`·`b19`. 2단계가 이 목록을 쓴다.

## 승인본 기준 수치 (사람이 읽는 참고값 — 판정은 6단계가 같은 함수로 다시 잰다)

(Task 0 Step 5 의 출력 9줄을 여기 표로 붙인다. 열: 보드 · steps · kept · removed · partial.)

설계 문서 `docs/plans/2026-09-12-결선도-단계화-슬롯고정-설계.md` §슬롯과 단계 표의
"새 배선/걷는 배선" 은 배선 가닥 수이고, 위 `steps` 는 칩 교체·삽입 줄과 부품 줄을
포함한 **번호 받은 줄 수**라 값이 다르다. 둘을 섞지 않는다.

## 에이전트 프롬프트

```
작업 디렉토리: <작업 디렉토리>

이 저장소에 `breadboard-diagram` 스킬이 있다.
`.claude/skills/breadboard-diagram/SKILL.md` 를 읽고 **그 문서의 규칙 그대로** 다음 요청을 수행하라:

> `보고서/실험01/결선도/netlist.md` 가 기술한 실험1 회로 다섯 개(C1~C5)의 빌더와 보드 사슬을 `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` 에 작성하고, `--circuit e1_all` 로 `보고서/실험01/결선도/` 에 렌더하라.

너에게 주어진 것은 그 스킬 문서와 이 저장소뿐이다. 다른 맥락은 없다. 한국어로 작업하고 보고한다.

금지:
- 위 작업 디렉토리 밖으로 나가지 마라. 밖의 파일을 읽지도 쓰지도 마라.
- `python -m unittest discover` 나 `pytest` 를 돌리지 마라. 렌더러의 `verify()` 가 유일한 검사다.
- `git commit` / `git add` / `git log` / `git show` / `git diff` / `git stash` / `git checkout` / 브랜치 조작을 하지 마라. 이 작업과 무관하다. 트리 상태 확인이 필요하면 `git status --porcelain` 만 쓴다.
- 스킬 문서와 이 저장소 밖의 지식으로 핀 번호·홀 자리를 채우지 마라. 근거가 저장소 안 파일이면 그 경로를 적는다.
- `netlist.md` 를 고치지 마라. 그것이 입력이다.

환경: 파이썬은 작업 디렉토리에서 `python ...` 로 돌린다 — 스킬 문서의 `python3` 는 `python` 으로 읽는다. Pillow 는 설치돼 있다. `pdftotext`·`pdftoppm`·`pdfinfo` 는 `<poppler 경로>` 에 있다. 판독 노트·시험 렌더 같은 스크래치는 작업 디렉토리 안 `tmp/` 아래에 둔다.

끝나면 아래 형식으로 보고하라. 같은 내용을 작업 디렉토리 안 `tmp/격리보고.md` 에도 저장하라.

1. 만든·고친 파일 경로 전부. 렌더한 PNG 파일명 전부.
2. 빌더·보드 사슬·완성본 목록의 이름과 각 빌더가 맡은 회로·단계.
3. `verify()` 결과: 빌더마다 **첫 렌더**에서 AssertionError 가 났는지 원문 그대로, 그것을 어떻게 고쳤는지, 몇 번 되돌렸는지. **첫 렌더에서 한 번에 통과했으면 그렇다고 명시하라.** 홀 자리를 옮긴 곳마다 옮기기 전 자리와 이유.
4. 단계 그림마다 회색(기준선)이 된 배선 수와 "앞 단계에서 걷는다" 표에 오른 항목.
5. 막혔거나 규칙이 안 맞아 스스로 판단으로 메운 자리 (없으면 "없음"). SKILL.md 의 어느 절이었는지.
6. SKILL.md 에서 모호하거나 서로 어긋난다고 느낀 문장 (없으면 "없음"). 원문 인용과 함께.
7. 이번 작업에서 읽은 저장소 파일 전부. 다른 실험 폴더의 파일을 참고했으면 무엇을 어디에 썼는지.
```

## 기록

| 날짜 | HEAD | 시나리오 | 결과 |
|---|---|---|---|
````

- [ ] **Step 2: 승인본 수치 표를 채운다**

Task 0 Step 5 의 출력 9줄을 「승인본 기준 수치」 절에 markdown 표로 옮긴다(열: 보드 · steps · kept · removed · partial). 값을 지어내지 않는다 — 출력을 다시 돌려 붙인다.

- [ ] **Step 3: 런북의 명령이 실제로 도는지 0단계와 3단계만 돌려 본다**

```bash
python -c "
from pathlib import Path
from scripts.lab import config
from scripts.lab.breadboard_isolate import RENDERER
d = Path(config.experiment_dir(1))
for f in ('결선도/netlist.md', '체크리스트/명세.md'):
    print('O' if (d / f).exists() else 'X', d / f)
print(len(list((d / '결선도').glob('*.png'))), 'png (13 이어야 한다)')
print('E1_SLOTS' in Path(RENDERER).read_text(encoding='utf-8'), '승인본 빌더 있음')
"
```

Expected: `O` 둘, `13 png`, `True`.

- [ ] **Step 4: 문서 테스트가 런북에 걸리지 않는지 본다**

```bash
python -m unittest tests.test_skill_docs 2>&1 | tail -3
```

Expected: 작업 전과 같은 결과(`test_no_dangling_cross_references [결과]` 하나만 실패). `docs/verify/` 는 그 테스트의 대상이 아니다.

- [ ] **Step 5: 커밋**

```bash
git add docs/verify/breadboard-diagram.md
git commit -m "docs(verify): breadboard-diagram 격리 재생성 런북 — 절차·답안지 목록·누출 토큰·에이전트 프롬프트

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 격리 트리 · 누출 · 자기대조 (런북 0~3단계 실행)

**Files:**
- Create (미추적): `tmp/verify-artifacts/누출-실험01-bb.txt`, `tempfile.gettempdir()/iso-실험01-bb/`

**Interfaces:**
- Consumes: 런북 0~3단계 명령 그대로.
- Produces: 격리 트리 경로 문자열(Task 5 프롬프트의 `<작업 디렉토리>`), 누출 목록 파일.

- [ ] **Step 1: 런북 0단계를 돌린다**

런북 `docs/verify/breadboard-diagram.md` 0단계의 두 명령을 복사해 돌린다.
Expected: `O O 13 True`, status 비어 있음. 아니면 멈춘다.

- [ ] **Step 2: 런북 1단계를 돌린다**

런북 1단계 명령을 복사해 돌린다. Expected: 마지막 줄에 격리 트리 경로(`C:\Users\Hyunjun\AppData\Local\Temp\iso-실험01-bb`). 이어서 걷어냈는지 직접 본다:

```bash
python -c "
import tempfile
from pathlib import Path
p = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
src = (p / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py').read_text(encoding='utf-8')
print('E1_SLOTS' in src, 'build_e1' in src, 'build_e2_inv' in src, 'def snapshot' in src)
print(sorted(x.name for x in (p / '보고서/실험01/결선도').iterdir()))
print(sorted(x.name for x in (p / '보고서/실험01').iterdir()))
print(list((p / '보고서/실험01/output').iterdir()))
"
git -C "$(python -c "import tempfile;print(tempfile.gettempdir())")/iso-실험01-bb" status --porcelain
git -C "$(python -c "import tempfile;print(tempfile.gettempdir())")/iso-실험01-bb" rev-list --count HEAD
```

Expected: `False False True True`; 결선도에 `netlist.md` 만; 실험01 아래 `output`·`결선도`·`체크리스트` 만; output 비어 있음; status 비어 있음; 커밋 수 `1`.

- [ ] **Step 3: 걷어낸 렌더러가 격리 트리 안에서 돈다**

```bash
python -c "
import subprocess, sys, tempfile
from pathlib import Path
p = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
r = subprocess.run([sys.executable, '.claude/skills/breadboard-diagram/scripts/render_breadboard.py', '--circuit', 'e2_inv', '--output', 'tmp/시험.png'], cwd=p, capture_output=True, text=True)
print(r.returncode, r.stdout[-200:], r.stderr[-300:])
r = subprocess.run([sys.executable, '.claude/skills/breadboard-diagram/scripts/render_breadboard.py', '--circuit', 'e1_all', '--output', 'tmp'], cwd=p, capture_output=True, text=True)
print(r.returncode, r.stderr[-200:])
"
```

Expected: 첫 실행 `0`; 둘째는 `2` 에 `invalid choice: 'e1_all'`. 시험 PNG 는 `tmp/` 아래라 트리 status 에 안 잡히는지 다시 `git status --porcelain` 으로 확인하고, 잡히면 지운다(`tmp/` 는 `.gitignore` 에 있어 안 잡혀야 정상).

- [ ] **Step 4: 런북 2단계(누출)를 돌린다**

런북 2단계 명령을 복사해 돌린다. 출력 파일마다 §답안지 목록의 「정상(구조적 누출)」 집합에 드는지 본다. 밖의 파일이 있으면 런북 §답안지 목록과 1단계 `KEYS` 에 더하고(런북 수정은 커밋한다) Step 2 부터 다시 한다.

- [ ] **Step 5: 런북 3단계(자기대조)를 돌린다**

```bash
python -m unittest tests.test_lab_breadboard_compare.Rendered 2>&1 | tail -3
```

Expected: `OK`.

---

### Task 5: 격리 에이전트 실행 (런북 4단계)

**Files:**
- 없음 (격리 트리 안에서만 쓴다)

**Interfaces:**
- Consumes: 런북 §에이전트 프롬프트, Task 4 의 격리 트리 경로.
- Produces: 격리 트리의 `보고서/실험01/결선도/*.png`, 고쳐진 `render_breadboard.py`, `tmp/격리보고.md`, 그리고 에이전트의 최종 보고 텍스트.

- [ ] **Step 1: 프롬프트를 채운다**

런북 §에이전트 프롬프트를 글자 그대로 복사하고 `<작업 디렉토리>` 를 Task 4 Step 2 의 경로로, `<poppler 경로>` 가 아직 자리표시자면 Global Constraints 의 값으로 바꾼다. 사유·합격 조건·"승인본"·"대조" 같은 말을 **한 글자도 더하지 않는다.**

- [ ] **Step 2: Agent 도구로 띄운다**

`subagent_type: general-purpose`, 기본 모델, `run_in_background: true`. 프롬프트는 Step 1 의 것.

- [ ] **Step 3: 기다린다**

완료 알림이 올 때까지 격리 트리와 승인본을 건드리지 않는다. 그동안 할 수 있는 것은 Task 6 의 스크립트를 스크래치에 미리 적어 두는 것뿐이다. 알림이 오면 보고 원문을 그대로 `<스크래치>/에이전트보고.md` 에 저장한다(격리 트리의 `tmp/격리보고.md` 와 같아야 하지만 에이전트가 저장을 빠뜨릴 수 있다).

- [ ] **Step 4: 에이전트가 트리 밖을 건드리지 않았는지 본다**

```bash
git status --porcelain
```

Expected: 비어 있다(저장소 쪽). 격리 트리 쪽은 `git -C <트리> status --porcelain` 이 재생성물(수정된 `render_breadboard.py`, 새 PNG)만 보인다.

---

### Task 6: 보존 · 대조 · 판정 · 기록 (런북 5~8단계)

**Files:**
- Create (미추적): `tmp/verify-artifacts/실험01-breadboard-격리-2026-09-12/{결선도/, render_breadboard.py, 격리보고.md, 누출-실험01-bb.txt, 판정.md}`
- Modify: `docs/verify/breadboard-diagram.md` `## 기록` 표 (미커밋)

**Interfaces:**
- Consumes: `breadboard_compare.judge(...)`, 런북 6단계 명령.
- Produces: `판정.md` (초안 1~9절 + 사람이 쓴 10절), 런북 기록 행.

- [ ] **Step 1: 보존한다 (런북 5단계)**

```bash
python -c "
import shutil, tempfile
from pathlib import Path
src = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
art = Path('tmp/verify-artifacts/실험01-breadboard-격리-2026-09-12')
art.mkdir(parents=True, exist_ok=True)
shutil.copytree(src / '보고서/실험01/결선도', art / '결선도', dirs_exist_ok=True)
shutil.copy(src / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py', art / 'render_breadboard.py')
rep = src / 'tmp/격리보고.md'
if rep.exists(): shutil.copy(rep, art / '격리보고.md')
else: print('격리보고.md 없음 — 스크래치의 에이전트보고.md 를 복사한다')
shutil.copy('tmp/verify-artifacts/누출-실험01-bb.txt', art / '누출-실험01-bb.txt')
print(sorted(p.name for p in art.iterdir()))
print(sorted(p.name for p in (art / '결선도').iterdir()))
"
```

Expected: 다섯 항목, 결선도 아래 `netlist.md` + 재생성 PNG 들. `격리보고.md` 가 없으면 `<스크래치>/에이전트보고.md` 를 그 이름으로 복사한다.

- [ ] **Step 2: 판정 초안을 낸다 (런북 6단계)**

런북 6단계 명령에서 `<YYYY-MM-DD>` 를 `2026-09-12` 로 바꿔 돌린다. Expected: 판정.md 가 찍히고 2절이 재생성 보드 수를 말한다. `E1_BOARDS` 없음이면 런북 6단계 끝의 안내대로 재생성 `render_breadboard.py` 를 읽어 목록을 손으로 만든 스크립트를 `<스크래치>/judge_manual.py` 에 쓰고 다시 낸다 — 그 스크립트도 `art/` 에 복사해 둔다.

- [ ] **Step 3: 재생성 렌더러가 승인본 테스트 하네스와 무관하게 돈다는 것을 확인한다**

판정.md 2절에 빌더 오류가 있으면 그 오류가 우리 로더 탓인지(예: 템플릿 경로) 에이전트 코드 탓인지 가른다:

```bash
python -c "
import tempfile
from pathlib import Path
from scripts.lab.breadboard_compare import load_renderer_at
m = load_renderer_at('tmp/verify-artifacts/실험01-breadboard-격리-2026-09-12/render_breadboard.py', 'rb_probe')
print([a for a in dir(m) if a.startswith(('E1_', 'build_e1'))])
"
```

- [ ] **Step 4: 사람이 본다 (런북 7단계)**

판정.md 9절의 다섯 항목을 순서대로 짚는다. PNG 13장은 승인본 `보고서/실험01/결선도/` 와 나란히 Read 도구로 연다(같은 이름끼리; 이름이 다르면 짝 맺기 표 순서로). 갈린 자리마다 표 한 줄:

```
| 자리 | 승인본 | 재생성 | SKILL.md 에 규칙이 있었나 (절·문장 인용) | verify() 가 잡았나 (보고 3항) | 판정 |
```

판정 값은 셋 중 하나 — `규칙 없음` / `규칙 있음·안 읽힘` / `검사 없음`. 결과를 판정.md 끝에 `## 10. 판정` 으로 적는다: 넷·자리·전환·파일명 각각의 일치 여부 한 줄, 갈린 자리 표, 원본·도구 쪽 결함(대조기가 헛잡은 것 포함).

- [ ] **Step 5: 런북 기록 행을 붙인다 (런북 8단계)**

`docs/verify/breadboard-diagram.md` 의 `## 기록` 표 헤더 밑에:

```
| 2026-09-12 | `<git rev-parse --short HEAD>` | V1 — 실험01 결선도 13장 재생성 | <한 줄 요약: 넷 치명 N·자리 일치/불일치·전환 kept 비교·파일명 위반 N·규칙 없음 N자리>. 판정: tmp/verify-artifacts/실험01-breadboard-격리-2026-09-12/판정.md |
```

커밋하지 않는다(사용자 결정).

- [ ] **Step 6: 격리 트리를 지운다**

```bash
python -c "
import tempfile
from pathlib import Path
from scripts.lab.isolate import _rmtree
p = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
_rmtree(p); print('deleted', not p.exists())
"
```

---

### Task 7: 보고 (런북 9단계)

**Files:** 없음

- [ ] **Step 1: 사용자에게 보고한다**

한 메시지로, 이 순서:

1. **일치한 것** — 넷(치명·기능 0 인 보드 수/13), 자리표, 전환 수치 중 승인본과 같은 것, 파일명.
2. **갈린 자리** — 판정.md 10절의 표를 요약. 자리마다 `규칙 없음 / 규칙 있음·안 읽힘 / 검사 없음` 과 근거(SKILL.md 절 인용, 보고 3항).
3. **원본·도구 쪽 결함** — 대조기가 헛잡은 것, 승인본 빌더의 문제, 런북 명령이 안 돈 자리.
4. **제안** — `규칙 없음` 자리마다 SKILL.md 어느 절에 어떤 문장을 더하면 닫히는지. **묻고 멈춘다.** SKILL.md 를 고치지 않는다.
5. 산출물 경로, 미커밋 항목(런북 기록 행), 브랜치 처리 미결(이 브랜치에 결선도 브랜치가 합쳐졌으니 `main` 머지·PR·유지 중 하나를 결정해야 한다는 것).

---

## 자기 검토

**스펙 대조.** 핸드오프 절차 1(격리 트리·뺄 것·남길 것·누출 grep) → Task 1·3·4. 절차 2(프롬프트) → Task 3 런북 §에이전트 프롬프트·Task 5. 절차 3(넷 대조·자리표·전환 수치·파일명·verify 첫 실행) → Task 2 `judge()` 3~8절. 절차 4(판정.md, 규칙 없음/안 읽힘 가르기) → Task 6 Step 4. 함정 네 개 — 폰트(합친 렌더러에 있음), `python`(Global Constraints), verify 엄격성·좌표 이동 관찰(프롬프트 3항이 "옮긴 곳마다 옮기기 전 자리와 이유" 를 요구), 기준선 회색 조건(`judge()` 6절 kept 비교 + 9절 안내), 승인본 테스트를 재생성본에 돌리지 않음(대조는 `breadboard_compare` 만). 미결 세 개 중 브랜치 처리는 Task 7 에서 다시 묻는다; 나머지 둘은 이 계획 밖.

**자리표시자.** 코드 블록 없이 "…을 구현한다" 로 끝나는 단계 없음. Task 3 Step 2 의 표는 실행 시 실제 출력으로 채우는 것이라 값을 미리 적지 않았다(지어내면 안 되는 값).

**이름 일관성.** `strip_e1_file`·`RENDERER`·`E1_MARKER`(Task 1) ↔ 런북 1단계·테스트 import. `load_renderer_at`·`render_chain`·`render_finals`·`pair_boards`·`net_findings`·`_compare_diagrams`·`layout_slots`·`seats`·`transition`·`sub_items`·`check_filename`·`judge`·`Board`·`BLOCKING`·`_from_wiring`(Task 2) ↔ 테스트·런북 6단계. `build_isolated_tree(..., edit=)` ↔ 런북 1단계. `isolate._rmtree` ↔ Task 6 Step 6.
