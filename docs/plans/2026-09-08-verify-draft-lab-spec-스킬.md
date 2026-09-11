# verify-draft-lab-spec 스킬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `draft-lab-spec` 을 답안 없는 격리 트리에서 다시 실행시키고 승인본과 자동 대조해 판정 초안과 런북 기록 행을 내는 스킬 `verify-draft-lab-spec` 을 만든다.

**Architecture:** 코드 두 모듈과 스킬 문서 하나다. `scripts/lab/isolate.py` 가 격리 트리를 만들고(archive → 답안지 제거 → `git init` 단일 커밋 → 누출 grep), `scripts/lab/regen_compare.py` 가 재생성물을 승인본과 대조한다(핀 **간선 집합** 대조·문장 교집합·`compare_specs` 차이 분류·판정 마크다운). 스킬 문서는 그 둘을 어느 순서로 부르고 에이전트에게 무엇을 주는지만 정한다. 판정은 자동 분류까지이고 합격 판정은 사람이 한다.

**Tech Stack:** Python 3.14 표준 라이브러리만(`subprocess`·`re`·`pathlib`·`tempfile`) · `unittest` 스타일 테스트를 `.venv/bin/python -m pytest` 로 실행 · 기존 모듈 `scripts/lab/{specdiff,spec_parser,netlist_parser,validate,render,config}`

**Spec:** `docs/plans/2026-09-08-verify-draft-lab-spec-설계.md`

## Global Constraints

- **브랜치.** 현재 브랜치 `feat/실험01-격리재생성`(HEAD `5ee11db`) 위에서 `feat/verify-draft-lab-spec` 을 만들어 작업한다. `main` 에 직접 커밋하지 않는다.
- **인덱스에 남의 스테이징이 있다.** 실험02·03·05·06·10 산출물 44건이 삭제(`D`)로 스테이징돼 있고 이것은 이 작업 것이 아니다. **`git add -A`·`git commit -a` 를 쓰지 않는다.** 항상 파일 경로를 지정해 `git add <경로>` / `git commit -- <경로>` 한다.
- **테스트 러너.** `.venv/bin/python -m pytest <파일> -q`. 시스템 `python3` 에는 pytest 가 없다. `PYTHONPATH` 는 필요 없다(저장소 루트에서 실행).
- **전체 스위트는 작업 트리에서 돌리지 않는다.** 위 스테이징 삭제 때문에 실험02~10 산출물을 읽는 테스트 70여 건이 무관하게 실패한다. 전체를 돌릴 때는 HEAD 임시 worktree 에 변경 파일을 복사해 돌린다 (Task 6 의 명령). 그리고 **`tests/test_lab_specdiff.py` 의 2건은 HEAD 에서 이미 실패한다** (`test_derived_경로에서_밀림_속_진짜_오류가_묻히지_않는다`·`test_머리말에_표가_없는_명세는_그_이유로는_안_짚는다` — 실험01 명세에 머리말 표가 생긴 뒤 낡은 단언). 이 계획은 그것을 고치지 않는다.
- **스킬 문서 불변식** (`tests/test_skill_docs.py`, Task 4 에서 `DOCS` 에 편입한다): `## 절대 규칙` 항목은 0열에서 `1. ` 부터 연속, `## 실행 절차` 는 `0. ` 부터 연속. `§절대 규칙 N`·`§실행 절차 N`·`N단계` 는 실재해야 한다. `§3` 처럼 `§` 뒤에 바로 숫자 금지. `§규칙 N` 표기 금지. 헤딩 깊이 제한은 `REPORT_DOCS` 에만 걸리므로 이 문서에는 안 걸린다.
- **답안지 목록의 정본은 스킬 문서다.** 코드(`isolate.py`)는 목록을 인자로 받기만 한다. 목록 첫 줄은 `.claude/skills/verify-draft-lab-spec/` 자기 자신이다.
- **줄 폭.** 저장소 마크다운은 76열 안팎으로 접는다. 산문은 그 관례를 따른다(표 행은 예외).
- **커밋 메시지.** 한국어, `feat:`/`fix:`/`docs:`/`test:` 접두, 본문에 왜를 적는다. 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- **한국어로 쓴다.** 코드 식별자·경로만 원문.

---

## File Structure

| 파일 | 책임 | 이번 변경 |
|---|---|---|
| `scripts/lab/regen_compare.py` | 재생성물 대 승인본 대조 — 핀 간선 집합, 문장 교집합, `compare_specs` 차이 분류, 판정 마크다운 | **신설** (Task 1·2) |
| `scripts/lab/isolate.py` | 격리 트리 만들기와 누출 grep | **신설** (Task 3) |
| `tests/test_lab_regen_compare.py` | 위 대조 모듈의 계약 | **신설** (Task 1·2) |
| `tests/test_lab_isolate.py` | 격리 트리 모듈의 계약 (임시 git 저장소로) | **신설** (Task 3) |
| `.claude/skills/verify-draft-lab-spec/SKILL.md` | 절차·답안지 목록·프롬프트 원문·판정 항목·기록 | **신설** (Task 4) |
| `tests/test_skill_docs.py` | 스킬 문서 불변식 그물 | `VERIFY` 상수, `DOCS["검증"]`, 답안지 자기참조 테스트 추가 (Task 4) |
| `docs/verify/draft-lab-spec.md` | 시나리오 런북 + 기록 | `### V1` 절(113~237행)을 스킬 참조 한 문단으로 교체 (Task 5) |
| `tmp/verify-artifacts/실험01-격리-<날짜>/` | 실전 실행 산출물 (gitignore) | Task 6 이 만든다 |

`regen_compare.py` 는 `render._circuit_body`·`render._plain` 을 재사용한다. 밑줄 이름이지만 `validate.py` 가 이미 같은 방식으로 import 하고 있어 선례가 있다(`scripts/lab/validate.py:16`).

---

### Task 1: 핀 간선 집합 대조 — `regen_compare.pin_nets` · `compare_netlist_pins`

**Files:**
- Create: `scripts/lab/regen_compare.py`
- Test: `tests/test_lab_regen_compare.py`

**Interfaces:**
- Consumes: `scripts.lab.netlist_parser.parse_netlist(path) -> LabNetlist` (`.circuits` 는 프로퍼티, 각 원소는 `NetlistSection` 이고 `.item`·`.body` 를 갖는다); `scripts.lab.render._circuit_body(section) -> (nodes, before, after)` — `nodes` 의 칩 노드는 `{"type": "chip", "head": "U1 = 74HC08 (quad …)", "wires": [str], "unused": [str], "blocks": [("table", MdTable) | ("note", str)]}`; `MdTable.rows` 는 셀 문자열 리스트의 리스트; `scripts.lab.render._plain(str) -> str`.
- Produces: `pin_nets(netlist_path) -> dict[str, set[frozenset]]` — 항목 id → 간선 집합. 간선은 두 끝점의 `frozenset`. 끝점은 튜플 `("PIN", 칩키, 핀번호)` · `("IN", "A")` · `("LED", "L1")` · `("VCC",)` · `("GND",)` · `("OPEN",)` · `("TEXT", 정규화 문자열)`. 칩키는 칩 종류 문자열(`"74HC08"`)이고 한 회로에 같은 종류가 둘이면 둘째부터 `"74HC08#2"`. `compare_netlist_pins(original, regenerated) -> list[str]` — 차이 한 건에 한 줄, 없으면 빈 리스트.

- [ ] **Step 1: 브랜치를 만든다**

```bash
git checkout -b feat/verify-draft-lab-spec
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_lab_regen_compare.py`:

```python
"""재생성 결선도·명세를 승인본과 대조하는 도구의 계약.

격리 재생성의 판정을 사람 눈에 맡기면 매번 기준이 흔들린다. 2026-09-08 회차의
스크래치 스크립트는 `pin 3 → U1.pin4` 와 `pin 4 ← pin 3` 을 다른 것으로 봤다 —
같은 선을 어느 쪽 핀에 적었는가의 차이일 뿐인데 불일치로 찍었다. 그래서 여기는
**간선 집합**으로 비교한다. 살아 있는 실험01 결선도를 한 군데씩 변형해 검사기가
그 자리를 짚는지 본다. 합성 픽스처는 헤딩형 하나(`netlist_heading_chips.md`)만
쓴다 — 실험01 은 전부 불릿형이라 헤딩형 경로를 살아 있는 실물로는 못 밟는다.
"""

import re
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.regen_compare import compare_netlist_pins, pin_nets

ROOT = Path(__file__).resolve().parents[1]
E01 = ROOT / config.experiment_dir(1)
NETLIST = E01 / "결선도/netlist.md"
HEADING = ROOT / "tests/fixtures/netlist_heading_chips.md"


def _variant(replacements):
    """실험01 결선도를 한 군데 바꾼 임시 사본. `replacements` 는 (old, new) 쌍이고
    old 는 원문에 정확히 한 번 있어야 한다 — 두 번 있으면 무엇을 바꿨는지 모른다."""
    text = NETLIST.read_text(encoding="utf-8")
    for old, new in replacements:
        assert text.count(old) == 1, (old, text.count(old))
        text = text.replace(old, new)
    d = Path(tempfile.mkdtemp()) / "결선도"
    d.mkdir()
    p = d / "netlist.md"
    p.write_text(text, encoding="utf-8")
    return p


class PinNets(unittest.TestCase):
    def test_원본_자기대조는_차이_0건(self):
        self.assertEqual(compare_netlist_pins(NETLIST, NETLIST), [])

    def test_불릿형_C1_의_간선이_읽힌다(self):
        nets = pin_nets(NETLIST)
        c1 = nets["E1.P1-1"]
        self.assertIn(frozenset({("PIN", "74HC08", 1), ("IN", "A")}), c1)
        self.assertIn(frozenset({("PIN", "74HC08", 14), ("VCC",)}), c1)
        self.assertIn(frozenset({("PIN", "74HC08", 9), ("GND",)}), c1)      # 미사용 입력
        self.assertIn(frozenset({("PIN", "74HC08", 8), ("OPEN",)}), c1)     # 미사용 출력
        self.assertIn(frozenset({("PIN", "74HC08", 3), ("LED", "L1")}), c1)
        self.assertIn(frozenset({("PIN", "74HC08", 3), ("PIN", "74HC08", 4)}), c1)

    def test_다칩_회로는_U번호가_아니라_칩_종류로_맺는다(self):
        c3 = pin_nets(NETLIST)["E1.P2-1"]
        # 원문은 `U3.pin3 → U4.pin1` 이다. U 번호는 문서마다 달라도 되므로 키는 종류다.
        self.assertIn(frozenset({("PIN", "74HC08", 3), ("PIN", "74HC00", 1)}), c3)

    def test_팬아웃을_반대쪽_핀에만_적어도_같다(self):
        # C3 의 U3.pin3 → U4.pin1 선을 U3 쪽에서 지운다. U4 쪽 `pin 1 ← U3.pin3` 이
        # 같은 간선을 이미 말하므로 차이가 없어야 한다.
        v = _variant([("  - pin 3  → U4.pin1          (게이트1 출력 A·B)\n", "")])
        self.assertEqual(compare_netlist_pins(NETLIST, v), [])

    def test_핀_하나를_옮기면_양방향으로_짚는다(self):
        # C1 의 입력 C 를 pin 5 에서 pin 9 로 옮긴다. 원본에만 있는 간선(5←C)과
        # 재생성에만 있는 간선(9←C)이 **둘 다** 나와야 한다 — 충돌만 찾으면 누락은
        # 안 보인다(런북 §V1).
        v = _variant([("  - pin 5  ← 입력 C\n  - pin 6  → L2 애노드 (330Ω 직렬) → GND    ※ 최종 출력 L2 = A·B·C, T1 의 검증 대상",
                       "  - pin 9  ← 입력 C\n  - pin 6  → L2 애노드 (330Ω 직렬) → GND    ※ 최종 출력 L2 = A·B·C, T1 의 검증 대상")])
        out = compare_netlist_pins(NETLIST, v)
        self.assertTrue(any("E1.P1-1" in s and "원본에만" in s and "pin 5" in s for s in out), out)
        self.assertTrue(any("E1.P1-1" in s and "재생성에만" in s and "pin 9" in s for s in out), out)

    def test_헤딩형_표에서_핀을_읽는다(self):
        nets = pin_nets(HEADING)
        c1 = nets["E10.P1"]
        self.assertIn(frozenset({("PIN", "7490", 5), ("VCC",)}), c1)
        self.assertIn(frozenset({("PIN", "7490", 4), ("OPEN",)}), c1)      # `| 4, 13 | 개방 |`
        self.assertIn(frozenset({("PIN", "7404", 1), ("PIN", "7490", 12)}), c1)   # `| 1 ← | U1 pin 12 (QA) |`
        self.assertIn(frozenset({("PIN", "7404", 11), ("GND",)}), c1)     # `| 미사용 입력핀 11, 13 | GND |`

    def test_항목이_한쪽에만_있으면_그것도_차이다(self):
        v = _variant([("- item: E1.P3\n", "- item: E1.P9\n")])
        out = compare_netlist_pins(NETLIST, v)
        self.assertTrue(any("E1.P3" in s and "원본에만" in s for s in out), out)
        self.assertTrue(any("E1.P9" in s and "재생성에만" in s for s in out), out)
```

- [ ] **Step 3: 실패를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_lab_regen_compare.py -q
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.regen_compare'` 로 수집 단계 실패.

- [ ] **Step 4: 최소 구현을 쓴다**

`scripts/lab/regen_compare.py`:

```python
"""격리 재생성물을 승인본과 대조한다.

`specdiff.compare_specs` 가 명세의 계약 필드를 보는 것과 짝을 이룬다 — 여기는
**결선도**와 **산문 재사용**을 본다. 결선도는 핀 번호를 줄 단위로 비교하지 않고
**간선 집합**으로 비교한다: `pin 3 → U1.pin4` 와 `pin 4 ← pin 3` 은 같은 선이고,
어느 칩 상자에 적었는가는 저작자 선택이다. 미사용 핀의 GND·개방 지정도 간선이라
누락이 그대로 드러난다.

칩은 U 번호가 아니라 **종류**(`74HC08`)로 맺는다. 원본이 `U3`, 재생성이 `U1` 로
불러도 같은 칩이다. 한 회로에 같은 종류가 둘이면 둘째부터 `#2` 를 붙인다.
"""

import re
from collections import Counter
from pathlib import Path

from .netlist_parser import parse_netlist
from .render import _circuit_body, _plain

_CHIP_HEAD = re.compile(r"U(\d+)\s*=\s*([A-Za-z0-9]+)")
_WIRE = re.compile(r"^pin\s*(\d+)\s*(←|→|<-|->)\s*(.+)$")
_UNUSED_HEAD = re.compile(r"미사용\s*(입력|출력)핀")
_OTHER_PIN = re.compile(r"U(\d+)[ .]*pin\s*(\d+)")
_SELF_PIN = re.compile(r"^pin\s*(\d+)$")
_INPUT = re.compile(r"입력\s*([A-Z]\w*)")
_LED = re.compile(r"LED_?([A-Z]\w*)|\bL(\d)\b")


def _clean(text: str) -> str:
    t = re.split(r"※", text)[0]
    t = re.sub(r"\(.*?\)", "", t)
    return re.sub(r"\s+", " ", t).strip(" ,·*`")


def _endpoint(text: str, umap: dict, self_key: str):
    t = _clean(text)
    m = _OTHER_PIN.search(t)
    if m:
        return ("PIN", umap.get(f"U{m.group(1)}", f"U{m.group(1)}"), int(m.group(2)))
    m = _SELF_PIN.match(t)
    if m:
        return ("PIN", self_key, int(m.group(1)))
    m = _INPUT.search(t)
    if m:
        return ("IN", m.group(1))
    m = _LED.search(t)
    if m:
        return ("LED", m.group(1) or f"L{m.group(2)}")
    if "VCC" in t or "+5V" in t:
        return ("VCC",)
    if "GND" in t:
        return ("GND",)
    if "개방" in t:
        return ("OPEN",)
    return ("TEXT", t)


def _chip_keys(nodes) -> dict:
    """`U<n>` → 칩키. 같은 종류가 둘이면 둘째부터 `#2`."""
    seen, umap = Counter(), {}
    for n in nodes:
        if n["type"] != "chip":
            continue
        m = _CHIP_HEAD.search(n["head"])
        if not m:
            continue
        kind = m.group(2)
        seen[kind] += 1
        umap[f"U{m.group(1)}"] = kind if seen[kind] == 1 else f"{kind}#{seen[kind]}"
    return umap


def _edges_of_chip(chip, umap) -> set:
    m = _CHIP_HEAD.search(chip["head"])
    if not m:
        return set()
    me = umap[f"U{m.group(1)}"]
    edges = set()

    def add(pin, target_text):
        edges.add(frozenset({("PIN", me, int(pin)), _endpoint(target_text, umap, me)}))

    for w in chip["wires"]:
        mw = _WIRE.match(_clean(w)) or _WIRE.match(w.strip())
        if mw:
            add(mw.group(1), mw.group(3))
    for u in chip["unused"]:
        # 불릿형은 `미사용 입력핀: pin 9, 10 → GND`, 헤딩형은 `_absorb_wiring` 이
        # 셀을 ` · ` 로 이은 `미사용 입력핀 11, 13 · GND · 플로팅 금지` 다. 핀은
        # 화살표나 `·` 앞 조각의 숫자 전부, 대상은 그 뒤에서 GND/VCC/개방을 찾는다.
        mu = _UNUSED_HEAD.search(u)
        if not mu:
            continue
        rest = u[mu.end():].replace("->", "→")
        head = re.split(r"→|·", rest, maxsplit=1)[0]
        tail = rest[len(head):]
        target = "GND" if "GND" in tail else "VCC" if "VCC" in tail else "개방" if "개방" in tail else tail
        for p in re.findall(r"\d+", head):
            add(p, target)
    for kind, table in chip["blocks"]:
        if kind != "table":
            continue
        for row in table.rows:
            cells = [_plain(c).strip() for c in row]
            if len(cells) < 2 or not cells[0]:
                continue
            pins = re.findall(r"\d+", re.sub(r"\(.*?\)", "", cells[0]))
            if not pins:
                continue
            for p in pins:
                add(p, cells[1])
    return edges


def pin_nets(netlist_path) -> dict:
    """항목 id → 간선 집합."""
    out = {}
    for sec in parse_netlist(Path(netlist_path)).circuits:
        nodes, _, _ = _circuit_body(sec)
        umap = _chip_keys(nodes)
        edges = out.setdefault(sec.item, set())
        for chip in (n for n in nodes if n["type"] == "chip"):
            edges |= _edges_of_chip(chip, umap)
    return out


def _fmt(edge) -> str:
    def one(e):
        if e[0] == "PIN":
            return f"{e[1]} pin {e[2]}"
        return e[0] if len(e) == 1 else f"{e[0]}:{e[1]}"
    a, b = sorted(edge, key=lambda e: (e[0] != "PIN", str(e)))
    return f"{one(a)} ↔ {one(b)}"


def compare_netlist_pins(original, regenerated) -> list:
    """차이 한 건에 한 줄. 같으면 빈 리스트."""
    a, b = pin_nets(original), pin_nets(regenerated)
    out = []
    for item in sorted(set(a) | set(b), key=str):
        if item not in b:
            out.append(f"{item}: 원본에만 있는 항목이다 (간선 {len(a[item])}개)")
            continue
        if item not in a:
            out.append(f"{item}: 재생성에만 있는 항목이다 (간선 {len(b[item])}개)")
            continue
        for e in sorted(a[item] - b[item], key=_fmt):
            out.append(f"{item}: 원본에만 — {_fmt(e)}")
        for e in sorted(b[item] - a[item], key=_fmt):
            out.append(f"{item}: 재생성에만 — {_fmt(e)}")
    return out
```

- [ ] **Step 5: 통과를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_lab_regen_compare.py -q
```

기대: 7 passed. `test_헤딩형_표에서_핀을_읽는다` 가 실패하면 `_UNUSED` 가 헤딩형 셀(`미사용 입력핀 11, 13` — 콜론도 `pin` 도 없다)을 못 읽는 것이다. 정규식은 위처럼 `:?`·`(?:pin\s*)?` 를 선택으로 둔다.

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/regen_compare.py tests/test_lab_regen_compare.py
git commit -m "$(cat <<'EOF'
feat: 결선도를 간선 집합으로 대조한다 — 어느 칩에 적었든 같은 선은 같다

격리 재생성의 핀 판정은 줄 단위 비교로는 못 한다. 2026-09-08 회차의
스크래치 도구는 `pin 3 → U1.pin4` 와 `pin 4 ← pin 3` 을 불일치로 찍었다.
양 끝점을 정규화한 간선 집합으로 비교하고, 칩은 U 번호가 아니라 종류로
맺는다. 미사용 핀의 GND·개방 지정도 간선이라 누락이 그대로 보인다.
불릿형·헤딩형 둘 다 `render._circuit_body` 로 읽는다.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)" -- scripts/lab/regen_compare.py tests/test_lab_regen_compare.py
```

---

### Task 2: 문장 교집합·차이 분류·판정 마크다운

**Files:**
- Modify: `scripts/lab/regen_compare.py` (Task 1 의 파일 끝에 추가)
- Modify: `tests/test_lab_regen_compare.py` (테스트 클래스 추가)

**Interfaces:**
- Consumes: `scripts.lab.specdiff.compare_specs(original, regenerated) -> list[str]`, `scripts.lab.specdiff.uncovered_tables(spec_path) -> list[str]`, `scripts.lab.spec_parser.parse_spec(path)`, `scripts.lab.validate.check_netlist(netlist_path, spec) -> list[Finding]` (`Finding.level` 은 `"error"|"warn"|"info"`), Task 1 의 `compare_netlist_pins`.
- Produces: `shared_sentences(regen_paths, corpus_paths, min_len=25) -> list[str]` (긴 것부터); `classify_spec_diffs(diffs) -> dict[str, list[str]]` (키는 `"id_shift"`·`"encoding"`·`"title"`·`"cell"`·`"other"` 다섯 전부 항상 있음); `judgment_markdown(experiment, regen_dir, corpus_dirs=()) -> str`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_regen_compare.py` 끝에 추가:

```python
from scripts.lab.regen_compare import (classify_spec_diffs, judgment_markdown,
                                       shared_sentences)

SPEC = E01 / "체크리스트/명세.md"


def _spec_variant(replacements):
    """실험01 명세를 바꾼 임시 사본. **첫 출현만** 바꾼다 — `| 1 | 1 | 1 | 1  | 1  |`
    같은 행은 T1·T2 에 둘 다 있어서 전부 바꾸면 차이가 둘이 된다."""
    text = SPEC.read_text(encoding="utf-8")
    for old, new in replacements:
        assert text.count(old) >= 1, old
        text = text.replace(old, new, 1)
    d = Path(tempfile.mkdtemp()) / config.experiment_folder_name(1) / "체크리스트"
    d.mkdir(parents=True)
    p = d / "명세.md"
    p.write_text(text, encoding="utf-8")
    return p


class SharedSentences(unittest.TestCase):
    def test_자기_자신과는_전부_겹친다(self):
        out = shared_sentences([SPEC], [SPEC])
        self.assertTrue(out)
        self.assertTrue(all(len(s) >= 25 for s in out))

    def test_다른_글과는_안_겹친다(self):
        p = Path(tempfile.mkdtemp()) / "x.md"
        p.write_text("이 문장은 스물다섯 자를 넘기려고 일부러 길게 쓴 문장이다.\n", encoding="utf-8")
        self.assertEqual(shared_sentences([p], [SPEC]), [])


class ClassifySpecDiffs(unittest.TestCase):
    def test_다섯_키가_항상_있다(self):
        out = classify_spec_diffs([])
        self.assertEqual(set(out), {"id_shift", "encoding", "title", "cell", "other"})

    def test_인코딩만_바꾼_사본은_전부_encoding_으로_간다(self):
        # T1 을 0/1 → H/L 로 뒤집는다. 뜻은 같으니 cell 로 세면 안 된다.
        # `\b0\b`·`\b1\b` 는 헤더의 `L1`·`L2` 안 숫자를 건드리지 않는다 —
        # `L` 과 `1` 사이는 단어 경계가 아니다.
        text = SPEC.read_text(encoding="utf-8")
        start = text.index("## T1 ·")
        end = text.index("\n# ", start)
        block = text[start:end].replace("encoding: 0/1", "encoding: H/L")
        block = "\n".join(
            re.sub(r"\b1\b", "H", re.sub(r"\b0\b", "L", l)) if l.startswith("|") else l
            for l in block.splitlines())
        v = _spec_variant([(text[start:end], block)])
        from scripts.lab.specdiff import compare_specs
        got = classify_spec_diffs(compare_specs(SPEC, v))
        self.assertTrue(got["encoding"], got)
        self.assertEqual(got["cell"], [], got)
        self.assertEqual(got["title"], [], got)

    def test_셀_하나를_뒤집으면_cell_이다(self):
        v = _spec_variant([("| 1 | 1 | 1 | 1  | 1  |", "| 1 | 1 | 1 | 1  | 0  |")])
        from scripts.lab.specdiff import compare_specs
        got = classify_spec_diffs(compare_specs(SPEC, v))
        self.assertEqual(len(got["cell"]), 1, got)
        self.assertEqual(got["encoding"], [])

    def test_제목만_바꾸면_title_이다(self):
        v = _spec_variant([("## T1 · 3-input AND 진리표", "## T1 · 3-input AND gate 진리표")])
        from scripts.lab.specdiff import compare_specs
        got = classify_spec_diffs(compare_specs(SPEC, v))
        self.assertEqual(len(got["title"]), 1, got)
        self.assertEqual(got["cell"], [])


class Judgment(unittest.TestCase):
    def test_원본을_원본과_대조한_판정문(self):
        md = judgment_markdown(1, E01, corpus_dirs=[E01 / "output"])
        self.assertIn("compare_specs 차이 0건", md)
        self.assertIn("핀 간선 차이 0건", md)
        self.assertIn("check_netlist error 0건", md)
        self.assertIn("세션 메모리 주입 아래서 돌았다", md)
        self.assertIn("구조 검증이 통과했다는 것은 파서가 읽을 수 있다는 뜻이고", md)
```

- [ ] **Step 2: 실패를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_lab_regen_compare.py -q
```

기대: `ImportError: cannot import name 'classify_spec_diffs'`.

- [ ] **Step 3: 구현을 붙인다**

`scripts/lab/regen_compare.py` 끝에 추가:

```python
from . import config, validate                      # noqa: E402
from .spec_parser import parse_spec                 # noqa: E402
from .specdiff import compare_specs, uncovered_tables   # noqa: E402

_SENT_SPLIT = re.compile(r"(?<=[.。다\)])\s|\|")


def _sentences(path, min_len):
    t = re.sub(r"\s+", " ", Path(path).read_text(encoding="utf-8"))
    return {p.strip() for p in _SENT_SPLIT.split(t) if len(p.strip()) >= min_len}


def shared_sentences(regen_paths, corpus_paths, min_len=25) -> list:
    """재생성물과 코퍼스가 공유하는 문장. 격리의 실증이다 — 답을 못 봤으면
    칩 이름·프론트매터 조각 말고는 겹칠 수 없다."""
    r, c = set(), set()
    for p in regen_paths:
        r |= _sentences(p, min_len)
    for p in corpus_paths:
        c |= _sentences(p, min_len)
    return sorted(r & c, key=len, reverse=True)


_CELL = re.compile(r"행\d+ \S+: 원본 '([^']*)' / 재생성 '([^']*)'")
_ENC_PAIRS = {("0", "L"), ("1", "H"), ("L", "0"), ("H", "1")}


def classify_spec_diffs(diffs) -> dict:
    """`compare_specs` 의 줄을 다섯 갈래로 나눈다. 갈래마다 뜻이 다르다 —
    `id_shift` 는 표가 하나 늘거나 줄어 번호가 밀린 것, `encoding` 은 `0/1`↔`H/L`
    치환으로 설명되는 셀, `cell` 은 진짜 값 차이, `title` 은 이름만 다른 것."""
    out = {"id_shift": [], "encoding": [], "title": [], "cell": [], "other": []}
    for d in diffs:
        if d.startswith("[표 ID"):
            out["id_shift"].append(d)
        elif " encoding: " in d:
            out["encoding"].append(d)
        elif " title: " in d:
            out["title"].append(d)
        else:
            m = _CELL.search(d)
            if m and (m.group(1), m.group(2)) in _ENC_PAIRS:
                out["encoding"].append(d)
            elif m:
                out["cell"].append(d)
            else:
                out["other"].append(d)
    return out


def judgment_markdown(experiment: int, regen_dir, corpus_dirs=()) -> str:
    """판정 초안. 자동으로 셀 수 있는 것만 센다 — 제목 갈림의 옳고 그름과
    산문은 사람이 본다."""
    root = Path(config.experiment_dir(experiment))
    regen_dir = Path(regen_dir)
    o_spec, r_spec = root / "체크리스트/명세.md", regen_dir / "체크리스트/명세.md"
    o_net, r_net = root / "결선도/netlist.md", regen_dir / "결선도/netlist.md"

    diffs = classify_spec_diffs(compare_specs(o_spec, r_spec))
    total = sum(len(v) for v in diffs.values())
    unc = uncovered_tables(r_spec)
    findings = validate.check_netlist(r_net, parse_spec(r_spec))
    by_level = {lvl: [f for f in findings if f.level == lvl] for lvl in ("error", "warn", "info")}
    pins = compare_netlist_pins(o_net, r_net)
    corpus = [o_spec, o_net]
    for d in corpus_dirs:
        corpus += sorted(Path(d).glob("*.md"))
    shared = shared_sentences([r_spec, r_net], corpus)

    L = [f"# 실험{experiment} 격리 재생성 판정 초안", "",
         "이 회차는 세션 메모리 주입 아래서 돌았다.", "",
         f"## 1. compare_specs 차이 {total}건"]
    for k, label in (("id_shift", "ID 밀림"), ("encoding", "인코딩 치환"), ("title", "제목"),
                     ("cell", "**셀 실차이**"), ("other", "기타")):
        L.append(f"- {label}: {len(diffs[k])}건")
        L += [f"    - {x}" for x in diffs[k][:20]]
    L += ["", f"대조 밖 표 {len(unc)}건"] + [f"- {x}" for x in unc]
    L += ["", f"## 2. check_netlist error {len(by_level['error'])}건 · warn {len(by_level['warn'])}건 · info {len(by_level['info'])}건"]
    L += [f"- {f}" for lvl in ("error", "warn", "info") for f in by_level[lvl]]
    L += ["", f"## 3. 핀 간선 차이 {len(pins)}건"] + [f"- {x}" for x in pins]
    L += ["", f"## 4. 문장 교집합 {len(shared)}건 (25자 이상)"] + [f"- {s[:120]}" for s in shared[:15]]
    L += ["", "## 5. 사람이 볼 것",
          "- 제목 차이는 가리키는 대상이 바뀌었는지부터 본다 (런북 §V1 의 title 기준).",
          "- 머리말 표(토큰 규약)와 산문은 도구가 안 본다. 원본과 나란히 읽는다.",
          "- 에이전트 보고 3항(첫 실행 error/warn/info)으로 **규칙이 막았나 / 검사가 잡았나**를 가른다.",
          "",
          "> 구조 검증이 통과했다는 것은 파서가 읽을 수 있다는 뜻이고, 내용이 맞다는 뜻이 아니다.", ""]
    return "\n".join(L)
```

- [ ] **Step 4: 통과를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_lab_regen_compare.py -q
```

기대: 14 passed. `test_인코딩만_바꾼_사본은…` 이 `cell` 을 남기면 변형 함수가 헤더 행(`| A | B | C | L1 | L2 |`)까지 바꾼 것이다 — 조건 `"A |" not in l` 이 헤더를 건너뛰는지 본다.

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/regen_compare.py tests/test_lab_regen_compare.py
git commit -m "$(cat <<'EOF'
feat: 격리 재생성 판정 초안을 도구가 낸다 — 차이 분류·문장 교집합·판정문

compare_specs 의 204건은 2026-09-08 회차에서 전부 ID 밀림·인코딩 치환·
제목 셋으로 환원됐다. 그 분류를 사람이 매번 손으로 하지 않도록 도구가
가른다. 셀 실차이만 굵게 낸다. 문장 교집합은 격리의 실증이고, 판정문은
"세션 메모리 주입 아래서 돌았다" 와 구조 검증의 한계 한 줄을 항상 싣는다.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)" -- scripts/lab/regen_compare.py tests/test_lab_regen_compare.py
```

---

### Task 3: 격리 트리 — `isolate.build_isolated_tree` · `leak_tokens` · `leak_scan`

**Files:**
- Create: `scripts/lab/isolate.py`
- Test: `tests/test_lab_isolate.py`

**Interfaces:**
- Consumes: `scripts.lab.config.experiment_dir(n) -> str` (`"보고서/실험01"`), `scripts.lab.spec_parser.parse_spec(path)` (`.items[].id`·`.items[].title`, `.tables[].source`).
- Produces: `build_isolated_tree(root, dest, experiment, answer_keys) -> Path` — `dest` 에 HEAD 를 풀고 `answer_keys`(루트 기준 상대경로 문자열)를 지우고 `보고서/실험NN/{체크리스트,결선도,output}` 내용물을 비운 뒤 `git init` + 커밋 1개. 끝나면 `dest/.git` 이 독립 저장소이고 `git status --porcelain` 이 빈 문자열이다. `leak_tokens(spec_path) -> list[str]` — 항목 id, 항목 제목, `derived (...)` 괄호 안 식. `leak_scan(dest, tokens, exts=(".md", ".py", ".html", ".txt", ".json")) -> list[str]` — `"경로:줄번호: 토큰"` 형식, `.git` 제외.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_isolate.py`:

```python
"""격리 트리 계약. 답안지를 지운 뒤 `git init` 단일 커밋 위에 두어야
`git status` 로 삭제 목록이 새지 않는다(런북 2026-09-01 누출 (1)).

실제 저장소를 쓰지 않고 임시 git 저장소를 하나 만들어 돌린다 — 이 테스트가
본 저장소의 HEAD 에 의존하면 승인본이 바뀔 때마다 흔들린다.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.isolate import build_isolated_tree, leak_scan, leak_tokens

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def _fake_repo():
    root = Path(tempfile.mkdtemp())
    (root / "docs/verify").mkdir(parents=True)
    (root / "docs/verify/answer.md").write_text("합격 조건\n", encoding="utf-8")
    exp = root / config.experiment_dir(1)
    (exp / "체크리스트").mkdir(parents=True)
    (exp / "결선도").mkdir()
    (exp / "체크리스트/명세.md").write_text("정답\n", encoding="utf-8")
    (exp / "결선도/netlist.md").write_text("정답\n", encoding="utf-8")
    (root / "keep.md").write_text("남는 파일 E1.P1-1 언급\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")
    return root


class BuildIsolatedTree(unittest.TestCase):
    def setUp(self):
        self.root = _fake_repo()
        self.dest = Path(tempfile.mkdtemp()) / "iso"
        build_isolated_tree(self.root, self.dest, 1, ["docs/verify"])

    def test_답안지는_없고_나머지는_있다(self):
        self.assertFalse((self.dest / "docs/verify").exists())
        self.assertTrue((self.dest / "keep.md").exists())

    def test_실험_폴더는_비어_있되_남아_있다(self):
        exp = self.dest / config.experiment_dir(1)
        self.assertTrue((exp / "체크리스트").is_dir())
        self.assertTrue((exp / "결선도").is_dir())
        self.assertTrue((exp / "output").is_dir())
        self.assertFalse((exp / "체크리스트/명세.md").exists())
        self.assertFalse((exp / "결선도/netlist.md").exists())

    def test_독립_저장소이고_커밋은_하나이며_status_는_비어_있다(self):
        self.assertTrue((self.dest / ".git").is_dir())
        self.assertEqual(_git(self.dest, "rev-list", "--count", "HEAD").strip(), "1")
        self.assertEqual(_git(self.dest, "status", "--porcelain"), "")

    def test_원본_저장소는_건드리지_않는다(self):
        self.assertTrue((self.root / "docs/verify/answer.md").exists())
        self.assertEqual(_git(self.root, "status", "--porcelain"), "")


class LeakScan(unittest.TestCase):
    def test_승인본에서_토큰을_뽑는다(self):
        toks = leak_tokens(SPEC)
        self.assertIn("E1.P1-1", toks)
        self.assertIn("실험 1-1) 3-input AND gate", toks)
        self.assertTrue(any(t.startswith("X = A + (A'·B)'") for t in toks), toks)

    def test_트리에서_토큰을_찾고_git_은_건너뛴다(self):
        root = _fake_repo()
        hits = leak_scan(root, ["E1.P1-1"])
        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0].startswith("keep.md:1:"), hits[0])
```

- [ ] **Step 2: 실패를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_lab_isolate.py -q
```

기대: `ModuleNotFoundError: No module named 'scripts.lab.isolate'`.

- [ ] **Step 3: 구현을 쓴다**

`scripts/lab/isolate.py`:

```python
"""격리 재생성용 작업 트리.

`git worktree` 를 쓰지 않는다 — worktree 는 이력을 통째로 들고 가서 답안지를
지워도 `git status` 에 삭제 목록이 뜨고 `git show HEAD:...` 로 되살릴 수 있다.
`git archive HEAD` 로 풀고 답안지를 지운 뒤 **새 저장소로 `git init` 해 커밋
하나**를 만든다. 그러면 `git status` 도 `git log` 도 아무것도 말하지 않는다.

답안지 **목록은 여기 없다.** 정본은 스킬 문서(`verify-draft-lab-spec/SKILL.md`)
이고 이 모듈은 받은 목록을 지울 뿐이다 — 목록을 코드에 두면 스킬 문서와
둘이 되어 표류한다.
"""

import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from . import config
from .spec_parser import parse_spec

_CLEARED = ("체크리스트", "결선도", "output")


def _git(cwd, *args) -> str:
    return subprocess.run(["git", "-c", "user.name=ws", "-c", "user.email=ws@local", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def build_isolated_tree(root, dest, experiment: int, answer_keys) -> Path:
    root, dest = Path(root), Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=root,
                             check=True, capture_output=True).stdout
    tar_path = dest.parent / (dest.name + ".tar")
    tar_path.write_bytes(archive)
    with tarfile.open(tar_path) as tf:
        tf.extractall(dest, filter="data")
    tar_path.unlink()

    for key in answer_keys:
        p = dest / key
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    exp = dest / config.experiment_dir(experiment)
    for sub in _CLEARED:
        d = exp / sub
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    _git(dest, "init", "-q")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-qm", "workspace")
    return dest


_DERIVED = re.compile(r"derived\s*\((.*)\)\s*$")


def leak_tokens(spec_path) -> list:
    """승인본 명세에서 트리에 남아 있으면 안 되는 문자열을 뽑는다."""
    spec = parse_spec(Path(spec_path))
    toks = []
    for it in spec.items:
        toks += [it.id, it.title]
    for t in spec.tables:
        m = _DERIVED.search(t.source or "")
        if m:
            toks += [part.strip() for part in m.group(1).split(";") if part.strip()]
    return toks


def leak_scan(dest, tokens, exts=(".md", ".py", ".html", ".txt", ".json")) -> list:
    dest = Path(dest)
    hits = []
    for p in sorted(dest.rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix not in exts:
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(lines, 1):
            for tok in tokens:
                if tok in line:
                    hits.append(f"{p.relative_to(dest)}:{n}: {tok}")
    return hits
```

- [ ] **Step 4: 통과를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_lab_isolate.py -q
```

기대: 6 passed. 필드명은 확인된 것이다 — `SpecItem.id`·`SpecItem.title`·`SpecTable.source` (`scripts/lab/spec_parser.py:32-51`).

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/isolate.py tests/test_lab_isolate.py
git commit -m "$(cat <<'EOF'
feat: 격리 트리를 archive → 답안지 제거 → git init 단일 커밋으로 만든다

worktree 는 이력을 들고 가서 답안지를 지워도 git status 에 삭제 목록이
뜬다(런북 2026-09-01 누출). 새 저장소의 커밋 하나 위에 두면 아무것도
새지 않는다. 답안지 목록은 스킬 문서가 정본이고 이 모듈은 받기만 한다.
누출 grep 은 승인본 명세의 항목 id·제목·파생식으로 트리를 훑는다 —
목록이 낡아도 남은 자리가 보고서에 남는다.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)" -- scripts/lab/isolate.py tests/test_lab_isolate.py
```

---

### Task 4: 스킬 문서와 그물 편입

**Files:**
- Create: `.claude/skills/verify-draft-lab-spec/SKILL.md`
- Modify: `tests/test_skill_docs.py:19-45` (상수·`DOCS`) 와 파일 끝(테스트 추가)

**Interfaces:**
- Consumes: Task 1~3 의 `pin_nets`·`compare_netlist_pins`·`judgment_markdown`·`build_isolated_tree`·`leak_tokens`·`leak_scan`, 그리고 `scripts.lab.config.experiment_dir`.
- Produces: 스킬 문서. 절 이름은 `## 인자`·`## 절대 규칙`·`## 실행 절차`·`## 답안지 목록`·`## 에이전트 프롬프트`·`## 비-목표`. `tests/test_skill_docs.py` 의 `DOCS["검증"] = (VERIFY, ("절대 규칙", "실행 절차"))`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 에서 `DRAFT = ...` 줄 아래에:

```python
VERIFY = ROOT / ".claude/skills/verify-draft-lab-spec/SKILL.md"
```

`DOCS` 에 한 줄:

```python
    "검증": (VERIFY, ("절대 규칙", "실행 절차")),
```

파일 끝 `SkillDocInvariants` 클래스 안에:

```python
    def test_the_verifier_lists_itself_as_an_answer_key(self):
        # 스킬 문서 자체가 합격 조건을 담는다. 격리 트리에서 빼지 않으면
        # 에이전트가 저장소를 뒤지다 자기 채점표를 읽는다 — 2026-08-31 에
        # docs/verify/ 로 실제로 일어난 일이다.
        text = self.docs["검증"]
        sec = sections(text)["답안지 목록"]
        self.assertIn("`.claude/skills/verify-draft-lab-spec/`", sec)
        self.assertIn("`docs/verify/`", sec)
        self.assertIn("`tests/`", sec)
        self.assertIn("`scripts/lab/regen_compare.py`", sec)
        self.assertIn("`scripts/lab/isolate.py`", sec)

    def test_the_verifier_prompt_gives_no_reasons_and_forbids_git_history(self):
        # 금지 사유는 첫 줄부터 "채점되는 시험" 임을 알려준다(런북 2026-09-01
        # 누출 (3)). 이력은 답안지 이름을 흘린다.
        sec = sections(self.docs["검증"])["에이전트 프롬프트"]
        self.assertNotIn("합격", sec)
        self.assertNotIn("채점", sec)
        self.assertIn("`git log`", sec)
        self.assertIn("한 번에 통과했으면 그렇다고 명시", sec)

    def test_the_verifier_does_not_fix_anything(self):
        sec = sections(self.docs["검증"])["비-목표"]
        self.assertIn("`draft-lab-spec` 을 고치지 않는다", sec)
        self.assertIn("커밋하지 않는다", sec)
```

`self.docs` 는 `setUp`(`tests/test_skill_docs.py:233`)이 `DOCS` 를 순회해 채우므로 `"검증"` 을 `DOCS` 에 넣는 것으로 읽힌다.

- [ ] **Step 2: 실패를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -q -k "verifier or contiguous or dangling"
```

기대: `FileNotFoundError` 또는 `KeyError: '검증'` 으로 실패.

- [ ] **Step 3: 스킬 문서를 쓴다**

`.claude/skills/verify-draft-lab-spec/SKILL.md`:

````markdown
---
name: verify-draft-lab-spec
description: draft-lab-spec 스킬을 답안 없는 격리 트리에서 다시 실행시키고 승인본과 자동 대조해 판정 초안과 런북 기록 행을 낸다. 사용자가 "격리 재생성 돌려", "실험1 로 스킬 검증", "draft-lab-spec 고쳤으니 검증해" 등을 요청하거나 /verify-draft-lab-spec 을 호출할 때 쓴다. 승인된 명세·결선도가 있는 실험(통제군)만 잰다. 아무것도 고치지 않는다 — 갈린 자리는 근거를 모아 사용자에게 묻는 데서 끝난다.
---

# verify-draft-lab-spec

`draft-lab-spec` 문서는 컴파일도 실행도 되지 않는다. 결함은 문서를 읽어서는
안 나오고, 규칙만 주고 격리 에이전트에게 실행시켜야 나온다 — 이 저장소가
2026-08-30 이후 매 회차 확인한 사실이다. 이 스킬은 그 실행을 `/` 한 번으로
만든다. 시나리오 V1(무인자 재생성)만 맡는다. V2~V7 은
`docs/verify/draft-lab-spec.md` 가 그대로 맡는다.

## 인자

`<실험N>`

- 번호 토큰이 없으면 한 줄로 되묻고 중단한다.
- 그 실험의 `체크리스트/명세.md` 와 `결선도/netlist.md` 가 둘 다 있어야
  한다 — 그것이 통제군이다. 하나라도 없으면 "통제군이 없다" 로 거절한다.
  2026-09-08 기준 자격이 있는 것은 실험01 뿐이다(나머지는 아카이브 교안으로
  저작돼 배포본이 오면 다시 저작해야 한다).

## 절대 규칙

1. **답안지를 전부 뺀 트리에서만 돈다.** 목록은 §답안지 목록이고 첫 줄이
   이 스킬 자신이다. 목록을 줄이지 않는다 — 2026-08-31 회차에서 에이전트
   둘이 `docs/verify/` 를 읽고 자기 합격 조건을 따랐다. 그 합격은 아무것도
   증명하지 않는다.
2. **못 빼는 누출은 적는다.** `draft-lab-spec/SKILL.md` 와
   `docs/schema/lab-spec-v2.md` 는 실험01 을 예시로 든다(항목 제목·T5
   파생식·`74HC02` 출력핀). 계약서라 못 뺀다. 누출 grep 결과를 판정.md
   에 "구조적 누출" 로 적고, **그 자리의 일치는 합격 근거로 세지 않는다.**
3. **프롬프트에 사유와 합격 조건을 쓰지 않는다.** "읽지 마라 — 합격 조건이
   거기 있다" 는 첫 줄부터 채점되는 시험임을 알린다. 이력 명령
   (`git log`·`show`·`diff`)도 금지한다. §에이전트 프롬프트를 글자 그대로
   쓴다.
4. **규칙이 막았는지 검사가 잡았는지를 가른다.** 에이전트 보고 3항(첫 실행의
   error/warn/info 원문)이 그 근거다. 검사가 잡은 항목은 전부 스킬 문서의
   빈 자리로 취급한다. 첫 실행 error 0 인데 승인본과 갈렸으면 **규칙도
   검사도 없는 자리**다 — 통제군 대조만이 그것을 본다.
5. **자동 합격은 없다.** 도구는 차이를 분류하고 세기만 한다. 제목 갈림의
   옳고 그름(런북 §V1 의 title 기준), 머리말 표, 산문은 사람이 원본과
   나란히 읽는다.
6. **아무것도 고치지 않는다.** `draft-lab-spec` 도, 승인본도, 규칙도. 갈린
   자리는 근거를 모아 사용자에게 묻고 멈춘다. 커밋하지 않는다.
7. **세션 메모리 주입을 명시한다.** 하네스가 컨트롤러의 세션 메모리를
   서브에이전트에 주입한다(런북 2026-09-01 누출 (2)). 막을 수 없으니
   판정.md 첫 줄에 적는다 — `judgment_markdown` 이 자동으로 넣는다.

## 실행 절차

0. **실험 번호를 폴더로 옮기고 통제군을 확인한다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   d = Path(config.experiment_dir(<실험번호>))
   for f in ('체크리스트/명세.md', '결선도/netlist.md'):
       print('O' if (d / f).exists() else 'X', d / f)
   "
   ```

   `X` 가 하나라도 있으면 거절한다.

1. **격리 트리를 만든다.** 스크래치패드 아래에 둔다. 답안지 목록은
   §답안지 목록을 **그대로** 옮긴다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import build_isolated_tree
   KEYS = [
       '.claude/skills/verify-draft-lab-spec',
       'docs/verify', 'docs/plans', 'docs/study', 'docs/rule-friction',
       'docs/notion-feedback', 'docs/강의노트_이론_실험_매핑_정리.md',
       'scripts/lab/specdiff.py', 'scripts/lab/regen_compare.py',
       'scripts/lab/isolate.py', 'tests',
       '.claude/skills/breadboard-diagram',
       '.claude/skills/explain-lab-preview', '.claude/skills/init-lab-experiment',
       '.claude/skills/make-lab-report-cover', '.claude/skills/prep-lab-checklist',
       '.claude/skills/review-lab-report', '.claude/skills/sync-report-to-notion',
       '.claude/skills/write-pre-report', '.claude/skills/write-result-report',
   ]
   dest = build_isolated_tree(Path('.'), Path('<스크래치>/iso-<실험NN>'), <실험번호>, KEYS)
   print(dest)
   "
   ```

   `보고서/<실험NN>/{체크리스트,결선도,output}/` 내용물은 함수가 비운다.
   폴더는 남는다 — `draft-lab-spec` 1단계가 폴더를 요구한다.

2. **누출을 훑는다.** 승인본 명세의 항목 id·제목·파생식으로 트리를 grep 한다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import leak_scan, leak_tokens
   toks = leak_tokens(Path(config.experiment_dir(<실험번호>)) / '체크리스트/명세.md')
   for h in leak_scan('<스크래치>/iso-<실험NN>', toks): print(h)
   "
   ```

   남는 자리가 `draft-lab-spec/SKILL.md`·`docs/schema/` 뿐이면 정상이다
   (§절대 규칙 2). 다른 파일이 나오면 §답안지 목록에 더하고 1단계부터
   다시 한다 — 목록이 낡은 것이다.

3. **대조 도구를 자기대조로 점검한다.** 승인본을 승인본과 대조해 0건이
   나와야 다음 단계의 숫자를 믿을 수 있다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.regen_compare import compare_netlist_pins
   from scripts.lab.specdiff import compare_specs
   d = Path(config.experiment_dir(<실험번호>))
   print('spec', len(compare_specs(d/'체크리스트/명세.md', d/'체크리스트/명세.md')))
   print('pins', len(compare_netlist_pins(d/'결선도/netlist.md', d/'결선도/netlist.md')))
   "
   ```

   둘 다 `0` 이어야 한다.

4. **에이전트를 띄운다.** Agent 도구, 기본 모델, 백그라운드. §에이전트
   프롬프트를 글자 그대로 쓰고 `<작업 디렉토리>`·`<실험번호>` 만 채운다.
   2026-09-08 실측은 305k 토큰·21분이다. 기다리는 동안 다른 일을 해도 되지만
   **격리 트리와 승인본은 건드리지 않는다.**

5. **산출물을 보존한다.** 끝나면 스크래치의 `보고서/<실험NN>/` 과
   `tmp/격리보고.md`·`tmp/판독노트*.md` 를 저장소 `tmp/verify-artifacts/
   <실험NN>-격리-<YYYY-MM-DD>/` 로 복사한다(`tmp/` 는 gitignore). 격리
   트리를 지우기 전에 한다 — 이 산출물이 근거물이다.

6. **판정 초안을 낸다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.regen_compare import judgment_markdown
   out = Path('tmp/verify-artifacts/<실험NN>-격리-<YYYY-MM-DD>/판정.md')
   out.write_text(judgment_markdown(<실험번호>, '<스크래치>/iso-<실험NN>/' + config.experiment_dir(<실험번호>),
                                    corpus_dirs=[Path(config.experiment_dir(<실험번호>)) / 'output']), encoding='utf-8')
   print(out.read_text(encoding='utf-8'))
   "
   ```

   2단계의 누출 grep 결과를 판정.md 의 "구조적 누출" 절로 덧붙인다.

7. **사람이 본다.** 판정.md 의 §5 항목을 하나씩 짚는다 — 제목 차이는
   가리키는 대상이 바뀌었는지(런북 §V1), 머리말 표와 산문은 원본과 나란히,
   에이전트 보고 3항으로 §절대 규칙 4 의 갈림. 결과를 판정.md 끝에
   "## 6. 판정" 으로 적는다: 셀·핀·IC 의 일치 여부, 갈린 자리와 그 자리에
   규칙·검사가 있었는지, 원본 쪽 결함.

8. **런북 기록 표에 행을 붙인다.** `docs/verify/draft-lab-spec.md` 의
   `## 기록` 표 마지막 행 뒤에 한 줄:

   `| <YYYY-MM-DD> | \`<git rev-parse --short HEAD>\` | V1 — 실험NN 무인자 재생성 | <한 줄 요약>. 판정: tmp/verify-artifacts/<실험NN>-격리-<날짜>/판정.md |`

   상세 절은 사람이 판정.md 를 다듬어 옮긴다. 이 스킬은 행만 붙인다.

9. **보고한다.** 세 가지를 낸다 — 일치한 것, 갈린 자리와 §절대 규칙 4 의
   판정, 원본 쪽 결함. 갈린 자리마다 근거(교안·과거 제출본·코드)를 모아
   사용자에게 **묻는다**. 규칙 신설과 승인본 수정은 이 스킬 밖이다.
   격리 트리를 지운다.

## 답안지 목록

격리 트리에서 지우는 것. 정본은 이 절이고 코드는 받기만 한다. 첫 줄이
이 스킬 자신이다.

- `.claude/skills/verify-draft-lab-spec/` — 이 문서. 합격 조건과 프롬프트가
  있다
- `docs/verify/` — 런북. 시나리오와 회차 기록
- `docs/plans/` — 합격 조건이 표와 문장으로 들어 있다
- `docs/study/`·`docs/rule-friction/`·`docs/notion-feedback/`·
  `docs/강의노트_이론_실험_매핑_정리.md` — 실험 내용의 파생 서술
- `scripts/lab/specdiff.py`·`scripts/lab/regen_compare.py`·
  `scripts/lab/isolate.py` — docstring 이 채점 기준을 적는다
- `tests/` — 실험01 값을 픽스처로 읽는 테스트가 열 개 넘는다
- `.claude/skills/breadboard-diagram/` — 실험01 배선이 코드로 있다
- `draft-lab-spec` 을 뺀 스킬 여덟 — `write-pre-report` 가 실험01 제목표를
  싣는 등 값이 샌다
- `보고서/<실험NN>/{체크리스트,결선도,output}/` **내용물** — 폴더는 둔다

남기는 것: `docs/schema/`·`docs/corpus-audit/`·`scripts/lab/` 나머지·
`.claude/데이터시트_출처.md`·`.claude/과목정보.md`·`강의노트/`·
`from_the_past/`·다른 실험 폴더. `draft-lab-spec` 이 참조하거나 그 절차가
실물로 드는 것들이다.

## 에이전트 프롬프트

```
작업 디렉토리: <작업 디렉토리>

이 저장소에 `draft-lab-spec` 스킬이 있다.
`.claude/skills/draft-lab-spec/SKILL.md` 를 읽고 **그 문서의 절차 그대로** 다음 요청을 수행하라:

> 실험<실험번호> 명세와 결선도를 만들어라

너에게 주어진 것은 그 스킬 문서와 이 저장소뿐이다. 다른 맥락은 없다. 한국어로 작업하고 보고한다.

금지:
- 위 작업 디렉토리 밖으로 나가지 마라. 밖의 파일을 읽지도 쓰지도 마라.
- `python3 -m unittest discover` 를 돌리지 마라. 스킬 절차가 지정하는 표적 검증 명령만 쓴다.
- `git commit` / `git add` / `git log` / `git show` / `git diff` / `git stash` / `git checkout` / 브랜치 조작을 하지 마라. 이 작업과 무관하다. 트리 상태 확인이 필요하면 `git status --porcelain` 만 쓴다.
- 스킬 문서와 이 저장소 밖의 지식으로 셀 값·핀 번호를 채우지 마라. 근거가 저장소 안 파일이면 그 경로를 적는다.

환경: `pytest` 없다. 파이썬은 작업 디렉토리에서 `python3 ...` 로 돌린다. `pdftotext`·`pdftoppm`·`pdfinfo` 는 `/opt/homebrew/bin/` 에 있다. 판독 노트·렌더 PNG 같은 스크래치는 작업 디렉토리 안 `tmp/` 아래에 둔다. 스킬 절차 중 다른 에이전트에게 검토를 맡기는 단계가 있으면 Agent 도구로 실제로 맡긴다 — 그 에이전트에게도 위 작업 디렉토리 밖 금지를 그대로 전한다.

끝나면 아래 형식으로 보고하라. 같은 내용을 작업 디렉토리 안 `tmp/격리보고.md` 에도 저장하라.

1. 만든 파일 경로 전부 (없으면 "없음"). 어느 교안 판본(경로·쪽수)을 열었는지.
2. 스킬 문서의 마지막 절차 단계가 요구하는 목록 전부, 그리고 그 단계가 반드시 붙이라는 한 줄.
3. 검증 단계마다: **첫 실행**에서 error / warn / info 가 각각 무엇이 나왔는지 원문 그대로, 그것을 어떻게 처리했는지, 몇 번 반복했는지. **첫 실행에서 error 0 으로 한 번에 통과했으면 그렇다고 명시하라.**
4. 검토 단계를 실제로 돌렸는지, 돌렸으면 지적 각각과 처리.
5. 막혔거나 규칙이 안 맞아 스스로 판단으로 메운 자리 (없으면 "없음"). 어느 규칙·단계였는지 번호로.
6. 스킬 문서에서 모호하거나 서로 어긋난다고 느낀 문장 (없으면 "없음"). 원문 인용과 함께.
7. 이번 작업에서 읽은 저장소 파일 전부. 다른 실험 폴더의 파일을 참고했으면 무엇을 어디에 썼는지.
```

## 비-목표

- **`draft-lab-spec` 을 고치지 않는다.** 갈린 자리는 묻고 멈춘다.
- **승인본을 고치지 않는다. 커밋하지 않는다.**
- **V2~V7 을 돌리지 않는다.** 런북이 맡는다.
- **다른 스킬을 재지 않는다.** `write-pre-report` 의 격리 검증은 별개다.
````

- [ ] **Step 4: 통과를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -q
```

기대: 전부 통과. `test_rule_and_step_numbering_is_contiguous` 가 `검증/실행 절차` 에서 깨지면 어느 단계 번호가 0열에서 시작하지 않은 것이다. `test_no_dangling_cross_references` 가 깨지면 `§절대 규칙 N`·`N단계` 중 없는 번호를 가리킨 것이다 — 이 문서는 규칙 7개·단계 0~9 다.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/verify-draft-lab-spec/SKILL.md tests/test_skill_docs.py
git commit -m "$(cat <<'EOF'
feat: 격리 재생성 검증을 스킬로 만든다 — verify-draft-lab-spec

런북은 있었지만 아무도 안 돌렸다(기록 표의 2026-09-07 행이 미실행이다).
2026-09-08 회차가 만든 절차 — 넓어진 답안지 목록, git init 단일 커밋,
간선 대조, 규칙/검사 판정 — 를 `/` 한 번에 돌게 옮긴다. 스킬 자신이
답안지라 목록 첫 줄이 자기 자신이고, 그물이 그것을 고정한다. 자동 합격은
없고 아무것도 고치지 않는다.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)" -- .claude/skills/verify-draft-lab-spec/SKILL.md tests/test_skill_docs.py
```

---

### Task 5: 런북 V1 절을 스킬 참조로 바꾼다

**Files:**
- Modify: `docs/verify/draft-lab-spec.md:113-237` (`### V1 — 재생성 (무인자)` 부터 `### V2 — \`명세만\`` 직전까지)

**Interfaces:**
- Consumes: Task 4 의 스킬 이름.
- Produces: V1 절 한 문단. 뒤 시나리오(V2~V7)와 기록은 그대로.

- [ ] **Step 1: 절 경계를 확인한다**

```bash
grep -n "^### V1\|^### V2" docs/verify/draft-lab-spec.md
```

기대: `113:### V1 — 재생성 (무인자)` 와 `238:### V2 — \`명세만\``. 번호가 다르면 아래 파이썬의 절 경계는 헤딩 문자열로 찾으므로 그대로 된다.

- [ ] **Step 2: 절을 교체한다**

```bash
python3 - <<'EOF'
from pathlib import Path
p = Path("docs/verify/draft-lab-spec.md")
t = p.read_text(encoding="utf-8")
a = t.index("### V1 — 재생성 (무인자)")
b = t.index("### V2 — `명세만`")
new = """### V1 — 재생성 (무인자)

**스킬 `verify-draft-lab-spec` 을 돌린다** (`/verify-draft-lab-spec <실험N>`).
격리 트리 만들기·답안지 목록·에이전트 프롬프트·판정 초안·기록 행까지 그
스킬 문서가 정본이다. 여기서는 되풀이하지 않는다 — 둘을 두면 표류한다.

스킬이 안 하는 것만 여기 적는다. **`title` 차이의 판정 기준**은 아래
그대로다: 표나 항목이 가리키는 대상이 바뀌었으면 불합격이다 — 반가산기
표에 전가산기 이름이 붙은 종류다. `특성표`/`진리표` 처럼 종류 이름만
갈렸으면 §절대 규칙 4 의 기준(이전 상태가 출력에 들어가는 표는 `특성표`)
으로 어느 쪽이 옳은지 가른다. 가른 결과 재생성이 그 기준을 어겼으면
불합격, 원본이 어겼으면 재생성 쪽의 그 차이는 셈에서 뺀다. 괄호 곁말이
빠졌거나 더해졌으면 교안을 떠서 그 곁말이 교안의 것인지 본다 — 교안에
있는 쪽이 맞다. **핀 대조는 간선 집합이라 방향이 둘이다** — 충돌과
누락(미사용 핀의 GND·VCC·개방 지정)을 함께 본다.

통제군은 승인된 명세·결선도가 있는 실험뿐이다. 2026-09-08 기준 실험01.
실험06 을 쓰던 이전 판(교안 p9·p11 의 `C` 열 지뢰)은 그 승인본이
아카이브 교안 기준이라 배포본이 오면 다시 저작한 뒤에야 통제군이 된다.

"""
p.write_text(t[:a] + new + t[b:], encoding="utf-8")
print("ok", len(t), "->", len(t[:a] + new + t[b:]))
EOF
```

- [ ] **Step 3: 나머지 시나리오가 V1 을 참조하는 자리를 고친다**

```bash
grep -n "§V1\|V1 의" docs/verify/draft-lab-spec.md
```

V7 절에 "명령은 §V1 의 마지막 블록에서 경로만 `/tmp/v7` 로 바꿔 쓴다" 가 있다. 그 문장을 다음으로 바꾼다:

```bash
python3 - <<'EOF'
from pathlib import Path
p = Path("docs/verify/draft-lab-spec.md")
t = p.read_text(encoding="utf-8")
old = "명령은\n  §V1 의 마지막 블록에서 경로만 `/tmp/v7` 로 바꿔 쓴다. **그 `error 0`\n  은 자기정합 검사다**(§V1 의 같은 단락 참고)."
assert t.count(old) == 1, t.count(old)
new = ("명령은\n  `scripts.lab.validate.check_netlist(<netlist>, parse_spec(<spec>))` 의\n"
       "  `level == \"error\"` 만 센다. **그 `error 0` 은 자기정합 검사다** — 원본\n"
       "  결선도와는 대조하지 않는다. 대조는 `regen_compare.compare_netlist_pins` 다.")
p.write_text(t.replace(old, new), encoding="utf-8"); print("ok")
EOF
```

`assert` 가 깨지면 원문이 다른 것이다 — `grep -n "경로만" docs/verify/draft-lab-spec.md` 로 실제 문장을 보고 `old` 를 그 원문으로 맞춘다.

- [ ] **Step 4: 문서 테스트를 돌린다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py tests/test_schema_doc_sync.py -q
```

기대: 통과. 런북은 `DOCS` 에 없으므로 상호참조 검사는 안 걸린다.

- [ ] **Step 5: 커밋**

```bash
git add docs/verify/draft-lab-spec.md
git commit -m "$(cat <<'EOF'
docs: 런북 V1 절을 verify-draft-lab-spec 참조로 바꾼다

절차가 스킬과 런북 둘에 있으면 표류한다. V1 은 스킬이 정본이고 런북에는
스킬이 안 하는 것 — title 판정 기준과 통제군 조건 — 만 남긴다. V2~V7 은
그대로다.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)" -- docs/verify/draft-lab-spec.md
```

---

### Task 6: 전체 스위트 확인과 실전 1회 (실험01)

**Files:**
- Create: `tmp/verify-artifacts/실험01-격리-<YYYY-MM-DD>/` (gitignore, 커밋 안 함)
- Modify: `docs/verify/draft-lab-spec.md` (`## 기록` 표에 행 하나)

**Interfaces:**
- Consumes: Task 4 의 스킬 문서 전체. 비교 기준은 `tmp/verify-artifacts/e01-격리-2026-09-08/` 의 2026-09-08 회차 산출물.
- Produces: 판정.md 와 기록 행. 이 회차의 합격 조건은 **판정.md 가 2026-09-08 회차와 같은 결론을 내는가** 다.

- [ ] **Step 1: 전체 스위트를 HEAD 임시 트리에서 돌린다**

작업 트리에는 남의 스테이징 삭제가 있어 전체 스위트가 무관하게 깨진다. 변경 파일을 HEAD 임시 worktree 에 얹어 돌린다:

```bash
W=$(mktemp -d)/wt && git worktree add --detach -q "$W" HEAD && \
for f in scripts/lab/regen_compare.py scripts/lab/isolate.py tests/test_lab_regen_compare.py tests/test_lab_isolate.py .claude/skills/verify-draft-lab-spec/SKILL.md tests/test_skill_docs.py docs/verify/draft-lab-spec.md; do mkdir -p "$W/$(dirname "$f")"; cp "$f" "$W/$f"; done && \
(cd "$W" && "$OLDPWD/.venv/bin/python" -m pytest tests/ -q 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" | tail -8); git worktree remove --force "$W"
```

기대: 실패는 `tests/test_lab_specdiff.py` 의 기존 2건뿐이다(Global Constraints). 새 실패가 있으면 그 Task 로 돌아간다.

- [ ] **Step 2: 스킬을 실제로 돌린다**

이 세션에서 `/verify-draft-lab-spec 실험1` 을 부른다. 0~9단계를 문서 그대로 밟는다. 4단계 에이전트는 백그라운드이고 20분 안팎이다.

- [ ] **Step 3: 2026-09-08 회차와 결론을 맞춘다**

판정.md 가 다음을 내야 한다. 다르면 스킬 문서의 결함이거나 `draft-lab-spec` 이 그 사이 바뀐 것이다 — 어느 쪽인지 적는다.

| 항목 | 2026-09-08 회차 | 이번 판정.md |
|---|---|---|
| `compare_specs` 셀 실차이 | 0건 | `cell: 0건` |
| 핀 간선 차이 | 0건(스크래치 도구로는 서식 차이만) | `핀 간선 차이 0건` |
| `check_netlist` error | 0 | `error 0건` |
| 문장 교집합 | 6건, 전부 칩 이름·프론트매터 조각 | 10건 이하, 실질 문장 없음 |
| 갈린 자리 | 파생표 인코딩·`title`·이름 없는 항목·표 순서 | **이번엔 닫혔어야 한다** — 2026-09-08 에 규칙을 넣었다. 남아 있으면 규칙이 안 먹은 것이고 그것이 이번 회차의 발견이다 |

- [ ] **Step 4: 기록 행을 붙인다** (스킬 8단계). 행 요약에 "스킬 첫 실전 실행" 을 넣는다.

- [ ] **Step 5: 커밋**

```bash
git add docs/verify/draft-lab-spec.md
git commit -m "$(cat <<'EOF'
docs: verify-draft-lab-spec 첫 실전 실행을 기록한다 — 실험01

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
EOF
)" -- docs/verify/draft-lab-spec.md
```

본문에는 판정.md 의 §6 요약 세 줄(일치한 것·갈린 자리·원본 결함)을 넣는다.

---

## Self-Review

**Spec coverage.** 설계 문서의 결정 표를 위에서부터 짚는다.

| 결정 | Task |
|---|---|
| 대상·이름·인자·거절 | 4 (`## 인자`, 0단계) |
| archive → 제거 → git init | 3 |
| 답안지 목록·자기 자신 첫 줄·그물 | 4 (`## 답안지 목록`, 테스트) |
| 누출 grep | 3 (`leak_scan`), 4 (2단계) |
| 프롬프트 (사유 없음·git 이력 금지·보고 7항) | 4 (`## 에이전트 프롬프트`, 테스트) |
| 기본 모델·백그라운드·비용 | 4 (4단계) |
| 세션 메모리 명시 | 2 (`judgment_markdown`), 4 (규칙 7) |
| 핀 간선 대조·불릿형/헤딩형 | 1 |
| 자동 분류 + 사람 판정 | 2, 4 (6·7단계, 규칙 5) |
| 갈린 자리는 묻고 멈춤 | 4 (9단계, 비-목표) |
| 기록 행 자동 | 4 (8단계) |
| 런북 V1 → 한 문단 | 5 |
| 실전 1회 | 6 |

빠진 것: 없음.

**Placeholder scan.** `TBD`·`TODO`·"적절히"·"필요에 따라" 없음. Task 3 Step 4 의 "필드명이 다르면 확인한다" 는 확인 명령을 같이 준다.

**Type consistency.** `pin_nets` 는 Task 1 정의 그대로 Task 2 의 `judgment_markdown` 이 `compare_netlist_pins` 로 쓴다. `build_isolated_tree(root, dest, experiment, answer_keys)` 인자 순서가 Task 3 테스트·Task 4 1단계에서 같다. `leak_scan(dest, tokens)` 도 같다. `judgment_markdown(experiment, regen_dir, corpus_dirs=())` 의 `regen_dir` 은 **실험 폴더**(`.../보고서/실험01`)이지 격리 트리 루트가 아니다 — Task 4 6단계가 `config.experiment_dir` 를 이어 붙이는 이유다.
