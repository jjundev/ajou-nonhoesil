# 테스트 정리와 변경 기반 테스트 라우터 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 지킬 대상이 없어진 테스트를 지우고 63초짜리 `TrialMarkers` 를 1초 미만 합성 보드로 바꾼 뒤, 바뀐 파일을 실제로 읽는 테스트 파일만 고르는 `pytest --affected` 를 더한다.

**Architecture:** 감사 훅(`sys.addaudithook`)이 테스트 파일마다 독립 프로세스에서 읽은 파일·훑은 디렉터리·띄운 자식 프로세스를 기록해 맵을 만든다(`python -m tests._affected rebuild`). `--affected` 는 기준 커밋 이후 변경 경로를 맵과 맞대 테스트 파일을 고르고, 모르는 코드가 바뀌었거나 맵이 없으면 전체를 돈다. 고르기는 xdist 컨트롤러가 한 번 하고 `workerinput` 으로 워커에 넘긴다.

**Tech Stack:** Python 3.14 표준 라이브러리만, pytest 9 + pytest-xdist 3.8(`-n auto --dist loadgroup`), git.

**Spec:** 2026-10-14 세션의 grill-yourself 설계(채팅). 아래 '설계 요약' 이 그 사본이다 — 결정 #0~#13, #11·#13 은 추천값 확정, #12 = 합성 함정 보드.

## 설계 요약

- 실측(이 Mac, main 8553b66): 벽시계 125초, CPU 합 1038초, 10코어. 병렬은 거의 포화 — 시간을 줄이는 길은 덜 돌리는 것.
- #11 지운다: `tests/test_global_hwp_to_pdf_skill.py`(저장소 밖 `~/.gemini` 스킬 검사), `tests/test_review_pack_motivation_refresh.py` + `docs/learning-pack-source/refresh_motivation.py`(계획 19/19 완료된 1회성), `test_review_pack_layout.py` 의 `test_migration_*` 2개 + `scripts/lab/migrate_pack_layout.py` + `logic-lab-review-pack` SKILL 116행의 안내(2026-10-13 적용 끝난 1회성 이전).
- #12 `TrialMarkers`(`test_breadboard_place.py:588`, 63초)를 합성 함정 보드로: 단계에만 있는 LED 사슬이 입력선 번호 원의 기본 자리를 막게 하고, 힌트를 끄면 번호 원이 실제로 움직이는지 같이 단언한다. 스크래치 시제품: 힌트 켬 → 움직임 0, 끔 → 1개(`left mid_gnd 30 → left j 30` 입력선), 0.33초.
- #13 `pytest` 는 계속 전체. `--affected` 는 선택. 병합·push 전에는 전체.
- #0 방식 B(실행 추적 맵). #1 단위 = 테스트 파일. #2 맵은 파일마다 독립 프로세스(`-n0`)로 — 프로세스 안 캐시(`tests/_renders.py:26` `_CACHE`, `engine()`, `engine/base.py:429` `lru_cache`)가 의존을 다른 파일에 붙이기 때문. #3 맵 위치 `<git common dir>/pytest-affected/map.json`(커밋 안 함, worktree 공유). #4 기준 = `merge-base(HEAD, origin/main)` → `merge-base(HEAD, main)` → `HEAD`, 여기에 작업 트리·untracked, `--no-renames`. #5 새·지운 파일은 테스트가 훑은 디렉터리(조상 포함, 저장소 루트 제외)에 걸면 선택. #6 어느 테스트도 안 읽는 변경: 코드면 전체, 아니면 보고만. #7 비파이썬 자식(Chrome·playwright·node·git)은 `EXTRA_DEPS` 표 + 정적 가드. #8 파이썬 자식은 `sitecustomize` 로 추적. #9 컨트롤러 계산 → `workerinput` → 워커 deselect. #10 맵 갱신은 수동, 맵이 기준보다 오래면 경고만.

## Global Constraints

- 작업 위치: `git worktree add .claude/worktrees/test-router -b claude/test-router main`. worktree 루트에 `ln -s ../../../.venv .venv`, 공용 `.git/info/exclude` 에 `.venv` 가 없으면 한 줄 넣는다. 병합은 사용자가 정한다.
- 의존성 추가 없음 — 표준 라이브러리만. `requirements-dev.txt` 의 패키지 목록은 그대로다.
- `pytest`(인자 없음)의 동작은 바꾸지 않는다. `--affected` 를 줄 때만 고른다.
- 엔진(`.claude/skills/breadboard-diagram/scripts/**`)·`보고서/**`·`tests/fixtures/board_v2_e4/**` 는 고치지 않는다.
- 기준 실패(main 8553b66, 이 Mac): `test_review_pack_work_table::test_published_payloads_obey_the_rule_and_match_the_source`, `test_lab_schematic::TestMainWithSpec::test_box_가_수가_아니면_사용법_오류`, `test_breadboard_diagram_cli::BreadboardCli::test_완성본끼리_빌더를_공유하지_않는다`[실험06]. 이 밖의 새 실패 0.
- 경로는 저장소 상대 posix, 유니코드 NFC(`unicodedata.normalize('NFC', …)`). Windows(역슬래시)에서도 같은 문자열이 나와야 한다.
- 맵 형식 `version` = `1`. 파일당 rebuild 시간 제한 900초.
- 한국어 주석·docstring·테스트 이름·커밋 메시지. 커밋 끝 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- 테스트 명령은 worktree 루트에서 `.venv/bin/python -m pytest …`. 전체 스위트(약 2분)는 배경으로 돌린다.

## Review Focus

1. **NFD 한글 경로** — macOS 도구가 NFD 로 준 `보고서/실험05/…` 도 맵의 NFC 경로와 같은 파일로 본다. Task 4 `test_NFD_경로도_같은_파일로_본다`.
2. **테스트가 `os.chdir` 한 뒤 상대경로로 읽는다** — 그 시점 cwd 기준으로 저장소 경로를 기록한다. Task 3 `test_chdir_뒤_상대경로도_저장소_경로로_적는다`.
3. **이름 바꾸기(`git mv`)** — 옛 경로·새 경로 둘 다 판정에 들어간다. Task 4 `test_이름_바꾸면_두_경로가_다_나온다`.
4. **선택이 0개일 때 xdist 종료 코드 5** — "돌릴 것 없음" 은 종료 코드 0. Task 6 Step 5.
5. **파이썬 자식을 `env=` 로 추적 변수 없이 띄운다** — 자식이 추적되지 않으니 그 테스트 파일을 opaque 로 표시한다. Task 3 `test_추적_변수_없이_띄운_파이썬_자식은_opaque`.

---

## 파일

- Delete: `tests/test_global_hwp_to_pdf_skill.py`, `tests/test_review_pack_motivation_refresh.py`, `docs/learning-pack-source/refresh_motivation.py`, `scripts/lab/migrate_pack_layout.py` (Task 1)
- Modify: `tests/test_review_pack_layout.py`, `.claude/skills/logic-lab-review-pack/SKILL.md:116` (Task 1)
- Create: `tests/fixtures/board_v2_marker_trap/배치.py` (Task 2)
- Modify: `tests/test_breadboard_place.py:1-4,588-605`, `tests/test_shared_engine.py:43` (Task 2)
- Create: `tests/_trace.py`, `tests/_trace_site/sitecustomize.py`, `tests/test_affected_trace.py` (Task 3)
- Create: `tests/_affected.py`, `tests/test_affected.py` (Task 4·5)
- Modify: `tests/conftest.py`, `pytest.ini`, `requirements-dev.txt` 주석 (Task 6)
- 작업 기록(커밋 안 함): `tmp/test-router/` (Task 7)

---

### Task 1: 지킬 대상 없는 테스트와 1회성 도구 지우기

**Files:**
- Delete: `tests/test_global_hwp_to_pdf_skill.py`, `tests/test_review_pack_motivation_refresh.py`, `docs/learning-pack-source/refresh_motivation.py`, `scripts/lab/migrate_pack_layout.py`
- Modify: `tests/test_review_pack_layout.py`, `.claude/skills/logic-lab-review-pack/SKILL.md:116`

**Interfaces:**
- Produces: 없음(삭제만).

- [ ] **Step 1: worktree 만들기** — Global Constraints 의 명령. `git -C .claude/worktrees/test-router log -1 --oneline` 이 `8553b66` 이상의 main 이면 통과.

- [ ] **Step 2: 네 파일 지우기** — `git rm` 으로 위 네 파일.

- [ ] **Step 3: `tests/test_review_pack_layout.py` 정리** — `from scripts.lab import migrate_pack_layout as mig` 줄, `_old_layout()` 함수, `test_migration_restores_published_pack_byte_for_byte`, `test_migration_is_noop_on_migrated_packs` 를 지운다. 그 뒤 쓰이지 않게 된 import(`json`·`re` 등 — 남은 코드에서 안 쓰는 것만)를 지운다. 나머지 테스트는 그대로.

- [ ] **Step 4: SKILL 116행 고치기** — 다음 한 줄로 바꾼다.

```
옛 구조(`자료/` 와 루트 MD 를 쓰던 팩, 2026-10-13 이전)는 읽지 않는다. 옮기는 1회성 도구 `migrate_pack_layout` 는 적용을 마치고 지웠다(필요하면 git `8553b66` 에서 꺼낸다).
```

- [ ] **Step 5: 남은 참조가 없는지 확인**

Run: `git grep -n -E "migrate_pack_layout|refresh_motivation|test_global_hwp_to_pdf_skill|motivation_refresh" -- ':!docs/plans' ':!docs/superpowers'`
Expected: 116행의 새 문장 한 줄만.

- [ ] **Step 6: 관련 테스트 돌리기**

Run: `.venv/bin/python -m pytest tests/test_review_pack_layout.py tests/test_skill_docs.py -q`
Expected: 모두 PASS.

- [ ] **Step 7: Commit**

```bash
git add -A tests scripts/lab docs/learning-pack-source .claude/skills/logic-lab-review-pack/SKILL.md
git commit -m "chore(tests): 지킬 대상 없는 테스트와 1회성 도구 삭제

전역 hwp 스킬 검사(저장소 밖), 도입부 갱신 도구(계획 완료), 팩 배치 이전 도구(2026-10-13 적용)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `TrialMarkers` → 합성 함정 보드

**Files:**
- Create: `tests/fixtures/board_v2_marker_trap/배치.py`
- Modify: `tests/test_breadboard_place.py:1-4`(docstring), `:588-605`(`TrialMarkers` 교체)
- Modify: `tests/test_shared_engine.py:43`

**Interfaces:**
- Produces: 픽스처 모듈의 `TRAP: PlaceCircuit`, `LAYOUT: dict`, `STAGES = (1, 2, None)`, `_draw(bb, stage, hints=True) -> None`.

- [ ] **Step 1: 픽스처 쓰기** — 스크래치에서 함정이 서는 것을 확인한 형태다(행·열 값이 함정 자체라 그대로 옮긴다).

```python
# 번호 원 고정 시험용 합성 보드 — 실험 보드가 아니다. 배치기(`place_search`)로 고른 자리가 아니라
# 함정이 서도록 손으로 정한 자리다(`PlaceEnforced` 대상 아님).
#
# 함정: 단계 1 에만 있는 LED 사슬 셋(우 a 22·28·38행)이 입력 E(U4 pin 13, 좌 30행) 점퍼 번호 원의
# 기본 자리를 막는다. 힌트(`place_marker_hints`) 없이 그리면 그 원이 단계 그림과 완성본에서 다른
# 자리에 앉는다 — 2026-10-05 실험04 v2 시험판 MUX 입력 E·D3 와 같은 꼴(`test_breadboard_place.MarkerTrap`).
from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit, place_chips,
                               place_marker_hints, place_paths, draw_routed,
                               _dip_pin_row as _pin_row, _dip_side as _side)

BOARD = 'v2'
SLOTS = ('K1',)
LAYOUT = {'slots': {'K1': 29}, 'leds': {'trap': {'L1': 22, 'L2': 28, 'L3': 38}}, 'bridge': [48, 49]}
STAGES = (1, 2, None)

_WIRES = (
    (1, 1, 'sig', ('U4', 12), ('LED', 'L1'), '임시 급전: U4 pin 12 -> LED1'),
    (1, 1, 'sig', ('U4', 8), ('LED', 'L3'), '임시 급전: U4 pin 8 -> LED3'),
    (1, 1, 'sig', ('U4', 6), ('LED', 'L2'), '임시 급전: U4 pin 6 -> LED2'),
    (2, None, 'sig', ('U4', 12), ('LED', 'L1'), 'Y = U4 pin 12 -> LED1'),
)
_INPUTS = ((1, 'E', 'U4', 13), (1, 'S1', 'U4', 9), (1, 'S0', 'U4', 5))


def _frame(bb, layout):
    L = bb.cols['left']
    gnd_row, vcc_row = layout['bridge']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], gnd_row, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], vcc_row, kind='vcc')


def _fixed(bb, stage, superset=False, layout=None):
    lay = layout or LAYOUT
    R, L, k, leds = bb.cols['right'], bb.cols['left'], place_chips(TRAP, lay), lay['leds']['trap']
    bb.draw_chip('74HC04', k['U4'])
    _frame(bb, lay)
    bb.connect_power(k['U4'], gnd_col='a')
    if superset or (stage is not None and stage < 2):
        for tag in ('L1', 'L2', 'L3'):
            bb.led_chain(R['a'], leds[tag], tag, '임시 관측', block='right')
    else:
        bb.led_chain(R['a'], leds['L1'], 'Y', 'Y', block='right')
    for s, name, chip, pin in _INPUTS:
        if superset or stage is None or s <= stage:
            side = _side(pin)
            _input_jumper(bb, L, _pin_row(k[chip], pin), name, f'{chip} pin {pin}',
                          side=side, col='a' if side == 'a' else 'j')


TRAP = PlaceCircuit('trap', {'U4': 'K1'}, {'U4': '74HC04'}, ('L1', 'L2', 'L3'), _WIRES, _fixed,
                    tuple((c, p) for _s, _n, c, p in _INPUTS))


def _draw(bb, stage, hints=True):
    """실험 빌더의 그리기 함수와 같은 순서. `hints=False` 는 함정이 살아 있는지 재는 시험 전용."""
    bb.partial = stage is not None and stage < 2
    bb.marker_hints = place_marker_hints(TRAP, LAYOUT) if hints else {}
    _fixed(bb, stage)
    draw_routed(bb, TRAP.wires, place_paths(TRAP, LAYOUT), stage)
```

- [ ] **Step 2: 테스트 쓰기** — `tests/test_breadboard_place.py` 의 `TrialMarkers` 클래스(588~605행)를 지우고 같은 자리에 넣는다. 모듈 상단 상수 옆에 `TRAP = ROOT / 'tests/fixtures/board_v2_marker_trap/배치.py'`.

```python
class MarkerTrap(unittest.TestCase):
    """엔진 고정 부품(전원선·LED 사슬·입력 점퍼) 번호 원은 단계 그림·완성본 어디서나 같은 자리다 —
    `place_marker_hints`(superset 판에서 비킨 자리)를 빌더가 준다(2026-10-05 최종 검토). 예전에는
    실험04 v2 시험판 14장(63초)으로 쟀다. 합성 함정 보드로 옮기면서, 함정이 아직 서는지(힌트를 끄면
    움직이는지)를 같이 본다 — 서지 않으면 아래 시험은 아무것도 재지 않는다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _renders.engine()
        cls.board = cls.mod.load_board_file(TRAP, 'board_v2_marker_trap')

    def _moved(self, hints):
        seen = {}
        for st in self.board.STAGES:
            bb = self.mod.BreadboardRenderer(None, board='v2')
            bb.enable_steps()
            self.board._draw(bb, st, hints=hints)
            for key, at in bb.settled_markers.items():
                seen.setdefault(key, set()).add(tuple(at))
        return {k: v for k, v in seen.items() if len(v) > 1}

    def test_힌트를_끄면_번호_원이_움직인다(self):
        self.assertNotEqual(self._moved(hints=False), {}, '함정이 서지 않는다 — 픽스처 자리를 다시 고른다')

    def test_고정_부품_원은_그림마다_같은_자리(self):
        self.assertEqual(self._moved(hints=True), {})
```

- [ ] **Step 3: docstring·공유 목록 고치기** — `test_breadboard_place.py` 1~4행 docstring 의 "시험판 시험은 `tests/fixtures/board_v2_e4/배치.py` 로 잰다" 뒤에 "번호 원 고정은 `tests/fixtures/board_v2_marker_trap/배치.py` 로" 를 덧붙인다. `tests/test_shared_engine.py:43` 을 `'test_breadboard_place': ('PlacedTrial',),` 로.

- [ ] **Step 4: 돌리기**

Run: `.venv/bin/python -m pytest tests/test_breadboard_place.py tests/test_shared_engine.py -q -n0 --durations=3`
Expected: 모두 PASS, `MarkerTrap` 두 시험 합 2초 미만.

- [ ] **Step 5: 함정 민감도 역검사** — 엔진 사본 하나를 따로 로드해 `place_marker_hints` 를 `lambda *a: {}` 로 바꿔 끼운 상태에서 `test_고정_부품_원은_그림마다_같은_자리` 의 단언이 실패하는지 스크래치 스크립트(`tmp/test-router/trap_check.py`, 커밋 안 함)로 확인한다.
Expected: `moved` 가 비어 있지 않다.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/board_v2_marker_trap tests/test_breadboard_place.py tests/test_shared_engine.py
git commit -m "test(breadboard): 번호 원 고정 시험을 합성 함정 보드로 (63초 → 1초 미만)

힌트를 끄면 움직이는지도 단언해 함정이 사라지면 조용히 무의미해지지 않게 한다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 추적기 `tests/_trace.py`

**Files:**
- Create: `tests/_trace.py`, `tests/_trace_site/sitecustomize.py`, `tests/test_affected_trace.py`

**Interfaces:**
- Produces (`tests/_trace.py`):
  - `ENV_DIR = 'AFFECTED_TRACE_DIR'`, `ENV_ROOT = 'AFFECTED_ROOT'`
  - `SKIP_PREFIXES = ('.git/', '.venv/', '.pytest_cache/', 'tmp/', '.claude/worktrees/')`
  - `rel(path, root: str, cwd: str | None = None) -> str | None` — 저장소 상대 NFC posix. 저장소 밖·`SKIP_PREFIXES`·`__pycache__` 디렉터리 자체면 `None`. `…/__pycache__/m.cpython-314.pyc` → `…/m.py`.
  - `is_read(mode, flags) -> bool` — `mode` 가 문자열이면 `w`·`a`·`x`·`+` 가 없을 때 참, `None` 이면 `flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT) == 0`.
  - `class Recorder` — `__init__(self, root: str)`, `hook(self, event: str, args: tuple) -> None`, `finish(self, out_dir: str) -> None`(`<out_dir>/<pid>.json` 에 `{"files": [...], "dirs": [...], "spawned": [[...]], "opaque": bool}` 를 정렬해 쓴다; 쓰기 전 `sys.modules` 의 `__file__` 을 `rel()` 로 `files` 에 더한다).
  - `install() -> Recorder | None` — `ENV_DIR` 이 없으면 `None`. 있으면 `Recorder(os.environ.get(ENV_ROOT) or <이 파일의 parents[1]>)` 를 만들고 `sys.addaudithook(rec.hook)`, `atexit.register(rec.finish, <ENV_DIR>)`.
  - pytest 훅 `pytest_configure(config) -> None` — `install()` 을 부른다(`-p tests._trace` 로만 실린다).
- Produces (`tests/_trace_site/sitecustomize.py`): `ENV_DIR` 이 있으면 `tests/_trace.py` 를 **파일 경로로**(`importlib.util.spec_from_file_location`) 불러 `install()` — 자식의 `sys.path` 를 바꾸지 않는다.

- [ ] **Step 1: 실패하는 테스트 쓰기** — `tests/test_affected_trace.py`

```python
def test_pyc_는_원본_py_로_적는다():
    assert rel('/r/scripts/lab/__pycache__/md.cpython-314.pyc', '/r') == 'scripts/lab/md.py'

def test_저장소_밖과_건너뛸_곳은_버린다():
    assert rel('/elsewhere/x.md', '/r') is None
    assert rel('/r/.git/HEAD', '/r') is None
    assert rel('/r/tmp/a.md', '/r') is None

def test_NFD_를_NFC_로():
    nfd = unicodedata.normalize('NFD', '/r/보고서/실험05/명세.md')
    assert rel(nfd, '/r') == unicodedata.normalize('NFC', '보고서/실험05/명세.md')

def test_읽기만_센다():
    assert is_read('r', 0) and is_read('rb', 0)
    assert not is_read('w', 0) and not is_read('r+', 0) and not is_read('ab', 0)
    assert is_read(None, os.O_RDONLY) and not is_read(None, os.O_WRONLY | os.O_CREAT)
```

같은 파일의 끝단 시험 셋은 공용 도우미 `_trace_run(tmp_path, body: str) -> dict` 를 쓴다: `tmp_path/proj` 에 `data.txt`·`sub/a.txt`·`child.txt` 와 `body` 를 담은 `test_x.py` 를 만들고, `env = {**os.environ, 'AFFECTED_TRACE_DIR': out, 'AFFECTED_ROOT': proj, 'PYTHONPATH': f'{REPO}/tests/_trace_site{os.pathsep}{REPO}'}` 로 `sys.executable -m pytest -n0 -p tests._trace -p no:cacheprovider -q test_x.py` 를 `cwd=proj` 로 돌린 뒤 `out` 의 JSON 들을 합쳐(files·dirs 합집합, opaque OR) 돌려준다.

```python
def test_읽은_파일_훑은_디렉터리_파이썬_자식을_적는다(tmp_path):
    got = _trace_run(tmp_path, '''
import subprocess, sys
from pathlib import Path
def test_x():
    Path('data.txt').read_text()
    list(Path('sub').glob('*.txt'))
    subprocess.run([sys.executable, '-c', "open('child.txt').read()"], check=True)
''')
    assert {'data.txt', 'child.txt', 'test_x.py'} <= set(got['files'])
    assert 'sub' in got['dirs']
    assert got['opaque'] is False

def test_chdir_뒤_상대경로도_저장소_경로로_적는다(tmp_path):
    got = _trace_run(tmp_path, '''
import os
def test_x():
    os.chdir('sub'); open('a.txt').read()
''')
    assert 'sub/a.txt' in got['files']

def test_추적_변수_없이_띄운_파이썬_자식은_opaque(tmp_path):
    got = _trace_run(tmp_path, '''
import subprocess, sys
def test_x():
    subprocess.run([sys.executable, '-c', 'pass'], env={}, check=True)
''')
    assert got['opaque'] is True

def test_비파이썬_자식은_opaque_이고_인자_경로를_적는다(tmp_path):
    got = _trace_run(tmp_path, '''
import subprocess
def test_x():
    subprocess.run(['cat', 'data.txt'], check=True, capture_output=True)
''')
    assert got['opaque'] is True and 'data.txt' in got['files']
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_affected_trace.py -q -n0`
Expected: FAIL — `ModuleNotFoundError: tests._trace`.

- [ ] **Step 3: `tests/_trace.py`·`sitecustomize.py` 구현** — `hook` 이 보는 이벤트:
  - `open` (`path, mode, flags`): `path` 가 `str`·`bytes`·`os.PathLike` 일 때만, `is_read` 면 `rel(path, root, os.getcwd())` 를 `files` 에.
  - `os.scandir`·`os.listdir` (`path`): `rel` 을 `dirs` 에(`None`·`''` 는 버림. `path` 가 `None` 이면 cwd).
  - `subprocess.Popen` (`executable, args, cwd, env`): `argv = list(args)` 를 `spawned` 에. 실행 파일 이름(`executable or argv[0]`)이 `python` 으로 시작하거나 `sys.executable` 과 같고, `env` 가 `None` 이거나 `ENV_DIR` 을 품으면 opaque 아님. 아니면 `opaque = True`. 인자 중 `rel()` 이 저장소 경로를 주고 그 경로가 있으면 파일이면 `files`, 디렉터리면 `dirs`.
  - `finish` 가 시작되면 기록을 멈춘다(자기 JSON 쓰기를 적지 않게).

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_affected_trace.py -q -n0`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/_trace.py tests/_trace_site tests/test_affected_trace.py
git commit -m "test(router): 테스트가 읽은 파일을 감사 훅으로 적는 추적기

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 고르기 `tests/_affected.py` — 변경 집합과 `select`

**Files:**
- Create: `tests/_affected.py`, `tests/test_affected.py`

**Interfaces:**
- Consumes: 없음(맵 형식만 Task 5 와 공유).
- Produces (`tests/_affected.py`):
  - `ROOT: Path`(= `Path(__file__).resolve().parents[1]`)
  - `FULL_TRIGGERS = ('pytest.ini', 'tests/conftest.py', 'requirements-dev.txt', 'tests/_affected.py', 'tests/_trace.py', 'tests/_trace_site/sitecustomize.py')`
  - `CODE_SUFFIXES = frozenset({'.py', '.js', '.mjs', '.cjs', '.css', '.html', '.json', '.toml'})`
  - `IGNORE = ('docs/**', 'tmp/**', '.claude/worktrees/**', '문제풀이영상/**', '.claude/skills/logic-lab-solution-video/**')`
  - `EXTRA_DEPS: dict[str, tuple[str, ...]]` — 아래 Step 3 값.
  - `norm(p: str) -> str` — NFC, `\` → `/`.
  - `changed_files(base: str, root: Path = ROOT) -> dict[str, str]` — 경로 → `'A'|'D'|'M'`.
  - `default_base(root: Path = ROOT) -> str` — 커밋 sha.
  - `@dataclass(frozen=True) class Selection`: `files: frozenset[str] | None`(None = 전체), `reasons: dict[str, tuple[str, ...]]`(테스트 → 걸린 변경 경로 또는 `'맵에 없음'`), `full_reason: str | None`, `unread: tuple[str, ...]`
  - `select(changed: dict[str, str], depmap: dict | None, test_files: Iterable[str], extra: dict = EXTRA_DEPS) -> Selection`

- [ ] **Step 1: 실패하는 테스트 쓰기** — `tests/test_affected.py`. 가짜 맵 `M = {'version': 1, 'tests': {'tests/test_a.py': {'files': ['tests/test_a.py', 'scripts/lab/md.py', '보고서/실험05/명세.md'], 'dirs': ['보고서'], 'opaque': False}, 'tests/test_b.py': {'files': ['tests/test_b.py', 'scripts/lab/notion.py'], 'dirs': [], 'opaque': False}}}`, `T = ['tests/test_a.py', 'tests/test_b.py']`.

```python
def test_읽은_파일이_바뀌면_그_테스트만():
    s = select({'scripts/lab/md.py': 'M'}, M, T)
    assert s.files == {'tests/test_a.py'} and s.reasons['tests/test_a.py'] == ('scripts/lab/md.py',)

def test_테스트_파일_자신이_바뀌면_고른다():
    assert select({'tests/test_b.py': 'M'}, M, T).files == {'tests/test_b.py'}

def test_훑은_디렉터리_아래_새_파일은_조상까지_본다():
    assert select({'보고서/실험07/결선도/배치.py': 'A'}, M, T).files == {'tests/test_a.py'}

def test_훑은_디렉터리_아래라도_수정은_파일로만_본다():
    s = select({'보고서/실험06/명세.md': 'M'}, M, T)
    assert s.files == frozenset() and s.unread == ('보고서/실험06/명세.md',)

def test_전체_트리거():
    assert select({'tests/conftest.py': 'M'}, M, T).files is None

def test_맵이_없으면_전체():
    s = select({'scripts/lab/md.py': 'M'}, None, T)
    assert s.files is None and 'rebuild' in s.full_reason

def test_아무도_안_읽는_코드는_전체_비코드는_보고만():
    assert select({'scripts/lab/new.py': 'A'}, M, T).files is None
    s = select({'보고서/실험05/output/메모.md': 'M'}, M, T)
    assert s.files == frozenset() and s.unread == ('보고서/실험05/output/메모.md',)

def test_IGNORE_아래_코드는_보고만():
    assert select({'docs/x.py': 'M'}, M, T).files == frozenset()

def test_맵에_없는_테스트는_늘_고른다():
    assert 'tests/test_c.py' in select({'보고서/x.md': 'M'}, M, T + ['tests/test_c.py']).files

def test_지운_테스트_파일은_전체를_부르지_않는다():
    assert select({'tests/test_gone.py': 'D'}, M, T).files == frozenset()

def test_EXTRA_glob_으로_고른다():
    s = select({'복습노트/실험05/a.html': 'M'}, M, T, extra={'tests/test_b.py': ('복습노트/**',)})
    assert s.files == {'tests/test_b.py'}

def test_바뀐_것이_없으면_빈_선택():
    s = select({}, M, T)
    assert s.files == frozenset() and s.full_reason is None

def test_NFD_경로도_같은_파일로_본다():
    nfd = unicodedata.normalize('NFD', '보고서/실험05/명세.md')
    assert select({nfd: 'M'}, M, T).files == {'tests/test_a.py'}

def test_역슬래시_경로():
    assert select({'scripts\\lab\\md.py': 'M'}, M, T).files == {'tests/test_a.py'}
```

임시 git 저장소(`git init`, `user.name`·`user.email` 은 `-c` 로) 시험:

```python
def test_변경_집합은_커밋_작업트리_untracked_를_합친다(tmp_path): ...
    # base 커밋 뒤: a.txt 수정 커밋, b.txt 스테이지 안 한 수정, c.txt untracked, d.txt 삭제
    # → {'a.txt': 'M', 'b.txt': 'M', 'c.txt': 'A', 'd.txt': 'D'}

def test_이름_바꾸면_두_경로가_다_나온다(tmp_path): ...
    # git mv old.txt new.txt 후 → {'old.txt': 'D', 'new.txt': 'A'}

def test_기준은_origin_main_다음_main_다음_HEAD(tmp_path): ...
    # origin 없음·main 없음(브랜치 이름 trunk) → HEAD sha
    # main 만 있음 → merge-base(HEAD, main)
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_affected.py -q -n0`
Expected: FAIL — `ModuleNotFoundError: tests._affected`.

- [ ] **Step 3: 구현** — `select` 판정 순서(앞이 이긴다):
  1. `changed` 를 `norm` 한다. 비면 빈 선택.
  2. `FULL_TRIGGERS` 나 `tests/_trace_site/` 아래가 있으면 전체(`full_reason = '설정·라우터 변경: <경로>'`).
  3. `depmap is None` 또는 `version != 1` 이면 전체(`'맵 없음 — python -m tests._affected rebuild'`).
  4. 테스트 `t` 마다: 맵에 없으면 `'맵에 없음'` 으로 고른다. 있으면 변경 `p` 가 `p == t` 이거나 `p in files` 이거나, 상태가 `A`·`D` 이고 `p` 의 조상(빈 문자열 제외) 하나가 `dirs` 에 있거나, `PurePosixPath(p).full_match(g)` 인 `g in extra.get(t, ())` 가 있으면 고른다.
  5. 어느 `t` 도 고르지 않은 `p`: `tests/test_*.py` 꼴이고 상태 `D` 면 버린다. 확장자가 `CODE_SUFFIXES` 이고 `IGNORE` 에 안 걸리면 전체(`'테스트가 읽지 않는 코드: <p>'`). 나머지는 `unread`(정렬).
  - `changed_files`: `git -c core.quotepath=off diff --name-status -z --no-renames <base>` 와 `git ls-files --others --exclude-standard -z`. 상태 첫 글자 `A`·`D` 는 그대로, 그 밖은 `M`. untracked 는 `A`.
  - `EXTRA_DEPS` 값:

```python
_PACK = ('복습노트/**', '.claude/skills/logic-lab-review-pack/**')
EXTRA_DEPS = {
    # playwright·Chrome·node 가 팩 HTML 과 그것이 부르는 자산을 직접 연다 — 파이썬 쪽 기록에 안 남는다.
    'tests/test_review_pack_explanation_browser.py': _PACK,
    'tests/test_review_pack_navigation_browser.py': _PACK,
    'tests/test_review_pack_workbook_browser.py': _PACK,
    'tests/test_workbook_equations.py': _PACK,
    'tests/test_workbook_clip_gate.py': _PACK,
    'tests/test_review_pack_print.py': _PACK,
    # `git show :<경로>` 로 인덱스 사본을 읽는다.
    'tests/test_review_pack_workbook_render.py': ('.claude/skills/logic-lab-review-pack/assets/workbook/**',),
    # Chrome 은 파이썬이 tmp 에 쓴 HTML 만 연다 — 그 재료는 파이썬 쪽에 기록된다.
    'tests/test_lab_html2pdf.py': (), 'tests/test_lab_fit_pages.py': (),
    'tests/test_lab_figure_export.py': (), 'tests/test_trace_guide.py': (), 'tests/test_lab_config.py': (),
    # git 을 임시 저장소나 인자로 준 경로에만 쓴다.
    'tests/test_lab_isolate.py': (), 'tests/test_lab_schematic.py': (),
}
```

- [ ] **Step 4: 정적 가드 테스트 더하기** — 같은 파일에:

```python
def test_브라우저_Chrome_git_node_를_부르는_테스트는_EXTRA_DEPS_에_있다():
    pat = re.compile(r"sync_playwright|chromium|_chrome\(|html2pdf|\[\s*['\"]git['\"]|\[\s*node\b")
    need = {f'tests/{p.name}' for p in (ROOT / 'tests').glob('test_*.py') if pat.search(p.read_text(encoding='utf-8'))}
    assert need - set(EXTRA_DEPS) == set()

def test_EXTRA_DEPS_의_테스트_파일은_있다():
    assert [t for t in EXTRA_DEPS if not (ROOT / t).is_file()] == []
```

가드가 위 표 밖의 파일을 내놓으면 그 파일이 무엇을 직접 여는지 보고 표에 행을 더한다(빈 튜플이면 이유 주석).

- [ ] **Step 5: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_affected.py -q -n0`
Expected: 모두 PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/_affected.py tests/test_affected.py
git commit -m "test(router): 변경 경로로 테스트 파일을 고르는 select

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 맵 만들기 `rebuild` 와 `explain` CLI

**Files:**
- Modify: `tests/_affected.py`, `tests/test_affected.py`

**Interfaces:**
- Consumes: Task 3 `ENV_DIR`·`ENV_ROOT`·JSON 형식, Task 4 `Selection`·`select`·`changed_files`·`default_base`.
- Produces:
  - `map_path(root: Path = ROOT) -> Path` — `git rev-parse --path-format=absolute --git-common-dir` / `pytest-affected/map.json`
  - `load_map(path: Path) -> dict | None`(없거나 JSON 이 깨졌으면 None), `save_map(path: Path, data: dict) -> None`(부모 폴더 생성, 임시 파일에 쓰고 `os.replace`)
  - `test_files(root: Path = ROOT) -> list[str]` — `tests/test_*.py` 정렬
  - `trace_file(test: str, root: Path = ROOT, timeout: int = 900) -> dict | None` — 맵 항목 `{'files', 'dirs', 'opaque', 'seconds', 'outcome'}`; 시간 초과·JSON 없음이면 None
  - `rebuild(jobs: int | None = None, root: Path = ROOT, timeout: int = 900) -> dict` — 맵을 저장하고 돌려준다
  - `plan(base: str | None = None, root: Path = ROOT) -> tuple[Selection, list[str]]` — 고르기 + 요약 줄
  - `header_lines(sel: Selection, base: str, changed: int, total: int, map_commit: str | None, built: str | None, stale: bool = False) -> list[str]` — 문구는 Step 1 아래 목록
  - `main(argv: list[str] | None = None) -> int` — `rebuild [-j N] [--timeout S]`, `explain [--base REF]`

- [ ] **Step 1: 실패하는 테스트 쓰기**

```python
def test_trace_file_은_한_파일의_기록을_합친다(tmp_path):
    # tmp 프로젝트(Task 3 도우미와 같은 꼴, 파이썬 자식 포함)에서 trace_file('test_x.py', root=proj)
    e = trace_file('test_x.py', root=proj, timeout=120)
    assert 'data.txt' in e['files'] and 'child.txt' in e['files'] and e['outcome'] == 'passed'

def test_시간_초과는_None(tmp_path):
    # body: time.sleep(5) → trace_file(..., timeout=1) is None

def test_실패한_테스트도_기록은_남는다(tmp_path):
    # body: 파일을 읽고 assert False → e['outcome'] == 'failed', 읽은 파일 기록됨

def test_rebuild_는_맵에_빠진_파일을_적지_않는다(tmp_path):
    # test_ok.py 와 test_hang.py(sleep) 를 두고 rebuild(jobs=2, root=proj, timeout=2)
    m = load_map(map_path(proj))
    assert set(m['tests']) == {'tests/test_ok.py'} and m['version'] == 1 and m['commit']

def test_plan_요약_첫_줄():
    sel = Selection(files=frozenset({'tests/test_a.py'}), reasons={}, full_reason=None, unread=())
    lines = header_lines(sel, base='abc1234def', changed=3, total=103, map_commit='8553b66aa', built='2026-10-14T10:00')
    assert lines == ['라우터: 기준 abc1234 · 바뀐 파일 3 · 선택 1/103 · 맵 2026-10-14(8553b66)']
```

`header_lines` 문구는 고정이다:
- 고름: `라우터: 기준 {base[:7]} · 바뀐 파일 {changed} · 선택 {k}/{total} · 맵 {built[:10]}({map_commit[:7]})`
- 전체: `라우터: 전체 실행 — {full_reason}`
- 빈: `라우터: 바뀐 파일 없음 — 돌릴 것 없음` (`changed == 0`), `라우터: 바뀐 파일 {changed} 개를 읽는 테스트 없음 — 돌릴 것 없음`(그 밖)
- `stale` 이면 둘째 줄 `라우터: 맵이 기준보다 오래됐다 — python -m tests._affected rebuild`

- [ ] **Step 2: 실패 확인** — `.venv/bin/python -m pytest tests/test_affected.py -q -n0` → FAIL(`ImportError`).

- [ ] **Step 3: 구현**
  - `trace_file`: 임시 폴더를 `ENV_DIR` 로, `ENV_ROOT = root`, `PYTHONPATH = <ROOT>/tests/_trace_site + os.pathsep + <ROOT> + 기존값` 으로 `sys.executable -m pytest -n0 -p tests._trace -p no:cacheprovider -q <test>` 를 `cwd=root` 로. 종료 코드 0 → `passed`, 1 → `failed`, 그 밖 → `error`. `seconds` 는 벽시계. JSON 들은 files·dirs 합집합(정렬), opaque OR.
  - `rebuild`: `jobs` 기본 `os.cpu_count()`. 직전 맵의 `seconds` 가 긴 것부터(없는 파일은 맨 앞) `ThreadPoolExecutor` 로. `None` 인 파일은 맵에서 뺀다(Task 4 규칙 4 로 늘 골라진다). 저장 형식 `{'version': 1, 'commit': <HEAD sha>, 'built': <ISO 초 단위>, 'python': platform.python_version(), 'platform': sys.platform, 'tests': {...}}`. 끝에 표준 출력으로 보고: 파일 수·실패·시간 초과 목록, `opaque` 이면서 `EXTRA_DEPS` 에 없는 파일, 맵의 어느 항목도 읽지 않은 `git ls-files` 코드 파일(`CODE_SUFFIXES`, `IGNORE` 제외) 수와 앞 20개.
  - `plan`: `base or default_base()`, `changed_files`, `load_map(map_path())`, `select`; `stale` = 맵 커밋이 기준의 조상이면서 기준과 다를 때(`git merge-base --is-ancestor`).
  - `explain`: `header_lines` 다음에 고른 테스트마다 `  tests/test_x.py ← <걸린 경로들>` 와 `unread` 를 `  (읽는 테스트 없음) <경로>` 로 찍는다.

- [ ] **Step 4: 통과 확인** — 같은 명령, 모두 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/_affected.py tests/test_affected.py
git commit -m "test(router): 파일마다 격리해 의존 맵을 만드는 rebuild 와 explain

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: `pytest --affected` 연결과 사용법 주석

**Files:**
- Modify: `tests/conftest.py`, `pytest.ini`, `requirements-dev.txt`

**Interfaces:**
- Consumes: Task 5 `plan`, `header_lines`.
- Produces: `pytest --affected[=BASE]`.

- [ ] **Step 1: `tests/conftest.py` 를 이 형태로** — 기존 `pytest_collection_modifyitems`(그룹 붙이기, `tryfirst`)는 그대로 두고 아래를 더한다. 모듈 docstring 끝에 "`--affected` 는 `tests/_affected.py` 가 고른 테스트 파일만 남긴다" 한 문단.
  - `pytest_addoption(parser)`: `parser.addoption('--affected', nargs='?', const='auto', default=None, metavar='BASE', help='기준 커밋 이후 바뀐 파일을 읽는 테스트 파일만 돈다(tests/_affected.py)')`
  - `pytest_configure(config)`: 워커가 아니고(`not hasattr(config, 'workerinput')`) 옵션이 있으면 `sel, lines = _affected.plan(None if opt == 'auto' else opt)` 를 `config.stash[AFFECTED]` 에 둔다(`AFFECTED = pytest.StashKey[tuple]()`).
  - `pytest_report_header(config) -> list[str]`: 저장된 `lines`.
  - `@pytest.hookimpl(optionalhook=True) pytest_configure_node(node)`: `node.workerinput['affected'] = None if sel.files is None else sorted(sel.files)`.
  - `pytest_collection_modifyitems(config, items)`(그룹 훅과 다른 이름 충돌 없이 — 같은 훅을 두 번 정의할 수 없으니 기존 함수 끝에서 `_deselect(config, items)` 를 부른다): 고를 목록을 워커는 `config.workerinput.get('affected', None)`, 컨트롤러(`-n0`)는 stash 에서 얻는다. 옵션이 없거나 목록이 None 이면 아무것도 안 한다. 아니면 `item.path` 의 `ROOT` 상대 posix 가 목록 밖인 항목을 `config.hook.pytest_deselected(items=...)` 로 알리고 `items[:]` 에서 뺀다.
  - `pytest_sessionfinish(session, exitstatus)`: 옵션이 있고 고른 목록이 비었고 `exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED` 면 `session.exitstatus = pytest.ExitCode.OK`.

- [ ] **Step 2: 주석** — `pytest.ini` 주석 끝에 두 줄: "바뀐 곳만 볼 때는 `pytest --affected`(기준: origin/main 과의 merge-base). 맵은 `python -m tests._affected rebuild`(약 3분)로 만들고, 병합·push 전에는 전체를 돈다." `requirements-dev.txt` 의 설치 안내 블록(`.venv/bin/python -m pytest tests/ -q` 줄 아래)에 같은 두 명령.

- [ ] **Step 3: 맵 만들기**

Run: `.venv/bin/python -m tests._affected rebuild`
Expected: `tests/test_*.py` 전부가 맵에 있고 시간 초과 0. "opaque 인데 EXTRA_DEPS 에 없음" 이 나오면 Task 4 Step 4 처럼 행을 더하고 다시 돈다.

- [ ] **Step 4: 고르기 확인** — 각각 파일을 공백 한 줄로 바꾼 뒤 `git checkout -- <파일>` 로 되돌린다.

| 바꾼 파일 | Run | Expected |
|---|---|---|
| (없음) | `.venv/bin/python -m pytest --affected=HEAD -q` | 첫 줄 `라우터: 바뀐 파일 없음 — 돌릴 것 없음`, 종료 코드 0 |
| `.claude/skills/breadboard-diagram/SKILL.md` | `.venv/bin/python -m tests._affected explain --base HEAD` | `tests/test_skill_docs.py ← …SKILL.md` 를 포함, 전체 실행 아님 |
| `scripts/lab/review_pack/render.py` | 같은 explain | `test_review_pack_*` 가 들고 `test_breadboard_*` 는 없다 |
| `pytest.ini` | 같은 explain | `라우터: 전체 실행 — 설정·라우터 변경: pytest.ini` |

- [ ] **Step 5: 선택 0개 + xdist 종료 코드** — `보고서/실험05/output/` 아래에 untracked 메모 `zz.md` 하나를 만들고 `.venv/bin/python -m pytest --affected=HEAD -q; echo $?` → 요약이 `라우터: 바뀐 파일 1 개를 읽는 테스트 없음 — 돌릴 것 없음`, 마지막 줄 `0`. 메모를 지운다.

- [ ] **Step 6: 전체 스위트** — `.venv/bin/python -m pytest tests/ -q`(배경). Expected: Global Constraints 의 기준 실패 셋 밖 실패 0.

- [ ] **Step 7: Commit**

```bash
git add tests/conftest.py pytest.ini requirements-dev.txt
git commit -m "test(router): pytest --affected — 바뀐 파일을 읽는 테스트만

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 수용 검사 — 변이 다섯 곳과 시간

**Files:**
- 작업 기록(커밋 안 함): `tmp/test-router/acceptance.md`

**Interfaces:**
- Consumes: Task 5·6 전부.

- [ ] **Step 1: 변이 검사** — 아래 다섯 곳에 하나씩, 테스트가 최소 하나 실패할 한 줄 결함(반환값을 바꾸거나 상수를 바꾸는 꼴)을 넣는다. 각각 (a) `.venv/bin/python -m pytest tests/ -q -p no:cacheprovider` 의 실패 테스트 파일 집합 F, (b) `.venv/bin/python -m tests._affected explain --base HEAD` 의 선택 집합 S 를 적고 되돌린다.
  1. `scripts/lab/spec_parser.py`
  2. `scripts/lab/review_pack/render.py`
  3. `.claude/skills/breadboard-diagram/scripts/render_breadboard.py`
  4. `보고서/실험05/결선도/배치.py`
  5. `.claude/skills/logic-lab-review-pack/assets/` 아래 템플릿 HTML 하나
  Expected: 다섯 번 모두 `F ⊆ S`(기준 실패 셋은 F 에서 뺀다). 하나라도 어긋나면 빠진 파일이 무엇을 왜 못 읽었는지 적고 `EXTRA_DEPS` 나 추적기를 고친 뒤 그 변이를 다시 잰다.

- [ ] **Step 2: 시간 표** — Task 6 Step 4 의 SKILL.md·`review_pack/render.py` 와 엔진(`render_breadboard.py` 공백 한 줄) 세 경우를 `/usr/bin/time -p .venv/bin/python -m pytest --affected=HEAD -q` 로 재 `acceptance.md` 에 벽시계·선택 파일 수를 표로 적는다. 비교 기준: 전체 125초(main 8553b66).

- [ ] **Step 3: 보고** — `acceptance.md` 의 두 표를 사용자에게 보이고 병합 여부를 묻는다. 커밋 없음.
