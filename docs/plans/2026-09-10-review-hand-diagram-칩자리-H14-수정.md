# H14 리뷰 지적 수정 구현 계획 (회전 배치 · 노드 대조 · 문장)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pin1_col="f"` 가 실제로 꽂을 수 있는 180° 회전 배치가 되게 하고, H14 의 요소 대조를 홀에서 노드로 접고, 칩이 떠난 갈래의 문장 모순을 없앤다. 리뷰(2026-09-10, 범위 ac694d4..cdf0a29)의 Critical 1 · Important 2 · Minor 4·5·6 을 닫는다.

**Architecture:** `pin1_row`·`pin1_col` 은 **pin 1 표시가 있는 홀 그대로**다 — 노치가 아래를 보면 pin 1 은 f 열 아랫행이므로 `pin1_row` 가 아랫행이 된다. `chip_pins` 가 `'f'` 일 때 행을 내려가며 놓는다. 칩의 행 이동량은 `pin1_row` 가 아니라 핀 집합의 최소 행(`chip_top_row`)으로 잰다. `_unshifted_elements` 는 `node_of` 로 접어 대조한다. 테스트 헬퍼 `_flip_chip` (거울상)은 `_rotate_chip` (회전)으로 바꾸고 레일 홀은 건드리지 않는다.

**Tech Stack:** Python 3.14 표준 라이브러리 + `pillow` + `pymupdf`. 새 의존성 없음. 테스트는 `unittest` 를 pytest 로 돌린다.

**Spec:** `docs/plans/2026-09-10-review-hand-diagram-칩자리-설계.md` (결정 #1 은 이 계획 Task 3 에서 정정한다). 리뷰 원문은 이 계획 앞 대화의 검토 보고다. 요지:

- **Critical 1.** `chip_pins('left', 18, 'f')` 가 pin 1 f18 … pin 7 f24 를 주는데 이는 좌우 거울상이라 실물 DIP 가 취할 수 없다. 노치를 아래로 돌린 칩은 pin 1 이 f24, pin 7 이 f18, pin 8 이 e18, pin 14 가 e24 다.
- **Important 2.** `_unshifted_elements` 가 홀 좌표를 정확 비교해서, 같은 노드 옆 홀(d17 대신 c17)에 남은 요소를 놓친다.
- **Important 3.** `h_pin is None` 갈래 문장 "참조에서는 pin 7 행, 지금은 칩 밖" 이 머리말 "그 핀 행에 앉았다" 와 모순된다.
- **Minor 4.** `_flip_chip.m()` 이 블록을 안 본다. **Minor 5.** `_MIRROR` 레일 항등에 주석이 없다. **Minor 6.** `'H1' ~ 'H13'`, `규칙 13개` 낡은 주석.
- Minor 7(블록 차이 무검사)은 이번 범위 이전부터 있던 구멍이라 **하지 않는다.**

## Global Constraints

- **주석·문서·테스트 이름은 한국어.** 코드 식별자와 경로만 원문.
- **테스트 이름은 한국어 문장.** 기존 관례.
- **파이썬은 `.venv/bin/python` 으로 돈다.**
- **기준 스위트:**

  ```bash
  .venv/bin/python -m pytest tests/test_hand_grid.py tests/test_hand_transcript.py tests/test_hand_compare.py tests/test_breadboard_wiring.py tests/test_breadboard_physical.py tests/test_breadboard_readability.py tests/test_breadboard_coords.py tests/test_breadboard_diagram_cli.py tests/test_skill_docs.py -q
  ```

  시작 시점(HEAD cdf0a29, 작업 트리 상태) **208건 통과, 실패 0.** 작업 트리에 `tests/test_skill_docs.py`·`보고서/실험01/output/실험01_예비보고서.md` 등 이 작업과 무관한 미커밋 변경이 있다. **건드리지 않고, 이 계획의 커밋에 섞지 않는다** (`git add` 는 파일을 지정한다).
- **`보고서/실험01/output/손그림검토/` 는 git 이 추적하지 않는다.** 커밋하지 않는다.
- **렌더러(`render_breadboard.py`)는 건드리지 않는다.** 참조 칩은 항상 노치 위이고 `pin1_col` 키가 없다.
- **H10 은 표기로 남는다.** `test_H10_칩이_밀리면_표기로만_알린다` 가 고정한다.
- **H14 의 정의는 바뀌지 않는다.** "참조 좌표(노드)에 남은 요소가 앉은 노드에서 그 칩의 핀이 참조와 달라졌는가". 거리 기준을 넣지 않는다.
- **레일 홀은 회전에서 움직이지 않는다.** 레일은 한 도체라 행이 뜻이 없고, 행을 돌리면 빈 행(RAIL_GAP_ROWS)에 걸린다.
- **한 파일을 여러 Task 가 고칠 때는 그 시점의 최종 함수 전체를 준다.** "끝에 추가" 로 쓰지 않는다.
- **커밋 메시지는 한국어 요약 + 대시 설명**, 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## 파일 구조

새 파일은 없다.

| 파일 | 이번에 바뀌는 책임 |
|---|---|
| `scripts/lab/hand_transcript.py` | `chip_pins` 가 `'f'` 를 회전으로 놓는다. 새 `chip_top_row(chip)` |
| `scripts/lab/hand_compare.py` | δ 를 `chip_top_row` 로 잰다(`check_chip_follow`·`check_placement`). `_unshifted_elements` 노드 접기. H14 문장. H10 문장. 낡은 주석 |
| `tests/test_hand_transcript.py` | 회전 배치 기대값 |
| `tests/test_hand_compare.py` | `_flip_chip` → `_rotate_chip`, 회전 테스트, c17 회귀, 문장 테스트, 모듈 독스트링 |
| `.claude/skills/review-hand-diagram/SKILL.md` | 전사 규칙을 회전으로 고쳐 쓴다 |
| `docs/plans/2026-09-10-review-hand-diagram-칩자리-설계.md` | 결정 #1 정정 기록 |

---

### Task 1: `pin1_col="f"` 를 180° 회전 배치로 고친다

**Files:**
- Modify: `scripts/lab/hand_transcript.py:59-75` (`chip_pins`), `:131-141` (parse 주석·`chips.append`)
- Modify: `scripts/lab/hand_compare.py:33` (import), `:556-603` (`check_chip_follow` 의 δ), `:606-628` (`check_placement` 의 δ·문장)
- Test: `tests/test_hand_transcript.py:75-81`, `:104-111`; `tests/test_hand_compare.py:46-82` (헬퍼), `:627-646` (회전 테스트 둘), `:674-683` (H10 방향 테스트)

**Interfaces:**
- Consumes: 없음.
- Produces:
  - `chip_pins(block, pin1_row, pin1_col='e') -> dict[int, tuple]`. `'e'`: pin i+1 = (block,'e',pin1_row+i), pin 14−i = (block,'f',pin1_row+i). `'f'`: pin i+1 = (block,'f',pin1_row−i), pin 14−i = (block,'e',pin1_row−i). 그 외 `ValueError`.
  - `chip_top_row(chip: dict) -> int` — `min(row for (_b, _c, row) in chip['pins'].values())`. 참조 칩(키 없음)과 손그림 칩 모두에 쓴다. Task 2 가 `check_chip_follow` 안에서 그대로 쓴다.
  - 테스트 헬퍼 `_rotate_chip(d, index, wiring=True) -> Diagram`. Task 2 테스트가 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다 — 전사**

`tests/test_hand_transcript.py` 의 `class ChipPins` 를 아래 최종 형태로 바꾼다.

```python
class ChipPins(unittest.TestCase):
    def test_핀_배치가_렌더러와_같다(self):
        """`draw_chip` 이 꽂는 자리와 한 글자도 갈리면 안 된다."""
        from scripts.lab.hand_grid import load_renderer
        import os
        import tempfile as tf
        mod = load_renderer()
        bb = mod.build_e1_nand(os.path.join(tf.mkdtemp(), 'x.png'))
        for chip in bb.wiring()['chips']:
            self.assertEqual(ht.chip_pins(chip['block'], chip['pin1_row']),
                             chip['pins'])

    def test_pin1_col_f_면_180도_돌린_배치다(self):
        """노치가 아래를 보게 돌린 칩. pin 1 이 f 열 **아랫행**이고 위로
        올라가며 2, 3 … 7 이다. 좌우 거울상(pin 1 이 f 열 윗행)은 실물 DIP 가
        취할 수 없는 도형이라 만들지 않는다 — 2026-09-10 리뷰 Critical 1."""
        pins = ht.chip_pins('left', 24, 'f')
        self.assertEqual(pins[1], ('left', 'f', 24))
        self.assertEqual(pins[7], ('left', 'f', 18))
        self.assertEqual(pins[8], ('left', 'e', 18))
        self.assertEqual(pins[14], ('left', 'e', 24))

    def test_돌린_칩은_노치_위_칩과_같은_행을_차지한다(self):
        """18~24행 칩을 돌리면 여전히 18~24행이다 — 홀 집합이 같다."""
        up = set(ht.chip_pins('left', 18, 'e').values())
        down = set(ht.chip_pins('left', 24, 'f').values())
        self.assertEqual(up, down)

    def test_chip_top_row_는_핀_집합의_최소_행이다(self):
        up = {'pins': ht.chip_pins('left', 18, 'e')}
        down = {'pins': ht.chip_pins('left', 24, 'f')}
        self.assertEqual(ht.chip_top_row(up), 18)
        self.assertEqual(ht.chip_top_row(down), 18)

    def test_pin1_col_은_e_나_f_만_받는다(self):
        """DIP-14 는 채널을 걸친다. 다른 열은 핀 모델이 없다."""
        with self.assertRaises(ValueError):
            ht.chip_pins('left', 17, 'd')
```

`class Parse` 의 `test_pin1_col_f_를_읽는다` 를 아래로 바꾼다.

```python
    def test_pin1_col_f_를_읽는다(self):
        """pin1_row 는 pin 1 표시가 있는 홀의 행 그대로다 — 돌린 칩이면 아랫행."""
        obj = dict(MINIMAL)
        obj['chips'] = [{"label": "74HC08", "block": "left",
                         "pin1_row": 13, "pin1_col": "f"}]
        d = ht.parse_transcript(_write(obj))
        self.assertEqual(d.chips[0]['pin1_col'], 'f')
        self.assertEqual(d.chips[0]['pins'][1], ('left', 'f', 13))
        self.assertEqual(d.chips[0]['pins'][7], ('left', 'f', 7))
        self.assertEqual(d.chips[0]['pins'][14], ('left', 'e', 13))
```

- [ ] **Step 2: 실패하는 테스트를 쓴다 — 검사기**

`tests/test_hand_compare.py` 에서 `_MIRROR` 와 `_flip_chip` 을 지우고 그 자리에 아래를 넣는다 (`_shift_rows` 뒤, `class Nodes` 앞).

```python
# 단자대 열의 180° 회전 짝. 레일 열은 일부러 없다 — 레일은 한 도체라 행이
# 뜻이 없고, 행을 돌리면 빈 행(RAIL_GAP_ROWS)에 걸린다. `_rotate_chip.m()` 이
# 이 표에 없는 열은 그대로 돌려준다
_ROTATE_COL = {'a': 'j', 'b': 'i', 'c': 'h', 'd': 'g', 'e': 'f',
               'f': 'e', 'g': 'd', 'h': 'c', 'i': 'b', 'j': 'a'}


def _rotate_chip(d, index, wiring=True):
    """index 번째 칩을 180° 돌린다 — 노치가 아래를 보고 pin 1 이 f 열 아랫행.

    `wiring=True` 면 **같은 블록**의, 그 칩 행 범위에 있는 단자대 홀도 함께
    돌린다(열 a↔j … e↔f, 행 top+bottom−r). 배선이 함께 돌아간 그림이다.
    `False` 면 칩만 돌리고 배선은 참조 자리에 둔다. 다른 블록은 건드리지
    않는다 — e1_comb 은 좌 74HC04 와 우 74HC32 가 행을 공유한다."""
    ch = d.chips[index]
    top = min(h[2] for h in ch['pins'].values())
    bottom = top + 6
    ch['pin1_row'], ch['pin1_col'] = bottom, 'f'
    ch['pins'] = chip_pins(ch['block'], bottom, 'f')
    if not wiring:
        return d

    def m(hole):
        if (hole is None or hole[0] != ch['block']
                or hole[1] not in _ROTATE_COL
                or not top <= hole[2] <= bottom):
            return hole
        return (hole[0], _ROTATE_COL[hole[1]], top + bottom - hole[2])

    for w in d.wires:
        for side in ('frm', 'to'):
            kind, val = w[side]
            w[side] = (kind, m(val)) if kind == 'hole' else (kind, val)
    for l in d.leds:
        l['anode'], l['cathode'] = m(l['anode']), m(l['cathode'])
    for r in d.resistors:
        r['top'], r['bottom'] = m(r['top']), m(r['bottom'])
    for c in d.chains:
        for k in ('signal', 'anode', 'cathode', 'res_top', 'res_bottom'):
            if k in c:
                c[k] = m(c[k])
    d.bridges = [(k, m(a), m(b)) for k, a, b in d.bridges]
    return d
```

`class ChipFollow` 의 마지막 두 테스트(`test_칩만_뒤집고_배선을_두면_H14_가_난다`, `test_배선까지_함께_뒤집으면_H14_없이_H10_표기만_난다`)를 아래 둘로 바꾼다.

```python
    def test_칩만_돌리고_배선을_두면_H14_가_난다(self):
        """칩은 돌아갔는데 배선은 참조 자리다. 같은 노드의 핀 번호가 바뀐다."""
        ref, hand = self._pair()
        _rotate_chip(hand, 1, wiring=False)
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].where, '74HC00')
        self.assertIn('f 열', found[0].message)
        self.assertIn('배선 끝점', found[0].message)

    def test_배선까지_함께_돌리면_H14_없이_H10_표기만_난다(self):
        """넷이 같으면 유효한 그림이다 — 행 밀림과 같은 원리. H6 이 모든 핀
        서명을 대조하므로 치명 0건이 곧 넷 동치의 증거다."""
        ref, hand = self._pair()
        _rotate_chip(hand, 1, wiring=True)
        found = hc.compare(ref, hand)
        self.assertEqual([str(f) for f in found if f.rule == 'H14'], [])
        self.assertEqual([str(f) for f in found if f.grade == '치명'], [])
        h10 = [f for f in found if f.rule == 'H10']
        self.assertEqual(len(h10), 1)
        self.assertIn('f 열', h10[0].message)

    def test_다른_블록_칩과_행을_나눠_써도_회전은_그_블록만_돌린다(self):
        """e1_comb 의 좌 74HC04(7~13행)를 돌려도 우 74HC32(10~16행)는 그대로다.
        치명 0건이어야 한다 — 리뷰 Minor 4."""
        ref = hc.reference_diagram('e1_comb')
        hand = hc.reference_diagram('e1_comb')
        hand.signed = True
        _rotate_chip(hand, 0, wiring=True)
        found = hc.compare(ref, hand)
        self.assertEqual([str(f) for f in found if f.grade == '치명'], [])
```

`class Paperwork` 의 `test_H10_칩이_뒤집히면_표기로_알린다` 를 아래로 바꾼다.

```python
    def test_H10_칩이_돌아_있으면_표기로_알린다(self):
        """노치가 아래를 보게 돌린 칩. 같은 행을 차지하므로 행 줄은 없고
        방향 줄 하나만 난다. 배선이 함께 돌아 있으면 회로는 맞다."""
        ref, hand = self._pair()
        _rotate_chip(hand, 1, wiring=True)
        found = [f for f in hc.check_placement(ref, hand) if f.rule == 'H10']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].grade, '표기')
        self.assertEqual(found[0].where, '74HC00')
        self.assertIn('f 열', found[0].message)
        self.assertNotIn('행이다', found[0].message)
```

- [ ] **Step 3: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_transcript.py tests/test_hand_compare.py -q -k "180도 or 같은_행을_차지 or chip_top_row or pin1_col_f_를 or 돌리 or 돌아"`
Expected: 전부 FAIL — `chip_top_row` 없음, `pins[7]` 기대값 불일치, `_rotate_chip` 후 치명 다수.

- [ ] **Step 4: 구현한다 — `hand_transcript.py`**

`chip_pins` 를 통째로 바꾸고 바로 뒤에 `chip_top_row` 를 둔다.

```python
def chip_pins(block, pin1_row, pin1_col='e'):
    """DIP-14 가 꽂히는 홀. `pin1_row`·`pin1_col` 은 **pin 1 표시가 있는 홀
    그대로**다.

    `'e'`: 노치가 위. pin 1~7 이 e 열을 내려가고 8~14 가 f 열을 올라온다 —
    렌더러 `draw_chip()` 과 같아야 하며 `test_핀_배치가_렌더러와_같다` 가 묶는다.
    `'f'`: 노치가 아래(180° 회전). pin 1 이 f 열 **아랫행**이고 위로 올라가며
    2 … 7, pin 8 이 e 열 윗행에서 내려오며 … 14 가 e 열 아랫행이다. 좌우
    거울상(pin 1 이 f 열 윗행)은 실물 DIP 가 취할 수 없는 도형이라 만들지
    않는다 — 2026-09-10 리뷰가 그 배치로 잡힌 허위 치명을 짚었다.
    채널을 걸치지 않는 열은 핀 모델이 없어 거절한다.
    """
    if pin1_col == 'e':
        step, across = +1, 'f'
    elif pin1_col == 'f':
        step, across = -1, 'e'
    else:
        raise ValueError(
            f"pin 1 열은 e 또는 f 다 — DIP-14 는 채널을 걸친다: {pin1_col!r}")
    pins = {}
    for i in range(7):
        row = pin1_row + step * i
        pins[i + 1] = (block, pin1_col, row)
        pins[14 - i] = (block, across, row)
    return pins


def chip_top_row(chip):
    """칩이 차지하는 첫 행. 행 이동량(H10·H14)은 이것으로 잰다 — `pin1_row` 는
    돌린 칩에서 아랫행이라 참조(항상 노치 위)와 바로 비교할 수 없다."""
    return min(row for _block, _col, row in chip['pins'].values())
```

`parse_transcript` 칩 블록의 주석을 바꾼다 (코드는 그대로).

```python
        # pin 1 열. 없으면 e — 기존 전사가 전부 그렇다. 180° 돌려 노치가
        # 아래를 보는 칩은 f 이고, 그때 pin1_row 는 pin 1 표시가 있는 **아랫행**
        # 이다. 채널을 안 걸친 칩(a~d·g~j)은 핀 모델이 없어 전사가 못 담는다 —
        # 그 칩의 pin 1 홀을 `uncertain` 에 올리면 H13 보류로 사람에게 간다
        pin1_col = ch.get('pin1_col', 'e')
        if pin1_col not in ('e', 'f'):
            raise TranscriptError(
                f"{label} pin1_col={pin1_col!r} — pin 1 열은 e 또는 f 다. "
                "채널을 안 걸친 칩은 pin 1 홀을 uncertain 에 올린다")
        chips.append({'label': label, 'block': block,
                      'pin1_row': row, 'pin1_col': pin1_col,
                      'pins': chip_pins(block, row, pin1_col)})
```

- [ ] **Step 5: 구현한다 — `hand_compare.py`**

import 줄을 바꾼다.

```python
from .hand_grid import load_renderer
from .hand_transcript import Diagram, chip_top_row
```

`check_chip_follow` 를 통째로 아래로 바꾼다 (δ 와 문장. `_unshifted_elements` 는 Task 2 에서 고친다).

```python
def check_chip_follow(ref, hand):
    """H14 칩 자리 변경을 안 따라간 요소.

    2026-09-09 시험 PDF 에서 74HC00 이 한 행 위(17행)에 있고 아래 배선은 전부
    따라갔는데 L1 저항만 참조 자리(d15→d17)에 남아 저항 아랫다리가 pin 1 행에
    앉았다. H7 이 증상("GND 에 안 닿는다")을, H10 이 행 차이를 냈지만 둘을 잇는
    줄이 없어 판정문만 읽으면 저항 한 줄 고치라는 뜻으로 읽혔다.

    거리 기준을 쓰지 않는다. **참조 좌표 그대로인 요소가 앉은 노드에서 이 칩의
    핀이 참조와 달라졌는가** 만 본다. 행 이동이면 참조에서 핀이 없던 노드에
    핀이 생기거나(∅ → pin n) 칩이 떠나 핀이 사라지고(pin n → ∅), 180° 회전이면
    같은 노드의 핀 번호가 바뀐다(1 ↔ 14). 충돌이 없으면 회로는 멀쩡하고 H10
    표기만 남는다. 증상 줄(H3·H6·H7)은 그대로 두고 이 줄을 더한다 — 같은
    층위의 메아리가 아니라 원인 줄이다.

    행 이동량은 `chip_top_row` 로 잰다. 돌린 칩은 `pin1_row` 가 아랫행이라
    참조(항상 노치 위)의 `pin1_row` 와 빼면 +6 이 헛난다.
    """
    out = []
    rchips = dict(zip(chip_keys(ref), ref.chips))
    hchips = dict(zip(chip_keys(hand), hand.chips))
    for key, rch in rchips.items():
        hch = hchips.get(key)
        if hch is None:
            continue
        delta = chip_top_row(hch) - chip_top_row(rch)
        hcol, rcol = hch.get('pin1_col', 'e'), rch.get('pin1_col', 'e')
        if delta == 0 and hcol == rcol:
            continue
        rpins = {node_of(h): p for p, h in rch['pins'].items()}
        hpins = {node_of(h): p for p, h in hch['pins'].items()}
        stuck = []
        for desc, hole in _unshifted_elements(ref, hand, delta):
            node = node_of(hole)
            r_pin, h_pin = rpins.get(node), hpins.get(node)
            if r_pin == h_pin:
                continue
            # 두 갈래는 다른 사실이다. 핀이 생긴 자리는 "그 핀 행에 앉았다",
            # 핀이 사라진 자리는 "칩이 떠나 허공에 남았다". 머리말은 둘을 다
            # 덮는 말("칩과 어긋난다")로 쓴다 — 2026-09-10 리뷰 Important 3
            where = (f'지금 pin {h_pin} 행' if h_pin is not None
                     else f'참조에서는 pin {r_pin} 행이었는데 칩이 떠났다')
            stuck.append(f'{desc} {_addr(hole)} ({where})')
        if not stuck:
            continue
        how = []
        if delta:
            how.append(f'참조보다 {delta:+d}행 옮겨졌')
        if hcol != rcol:
            how.append(f'180° 돌아 pin 1 이 {hcol} 열로 갔')
        out.append(HandFinding(
            'H14', '치명', key,
            '고 '.join(how) + '는데 다음 요소가 참조 좌표에 남아 칩과 어긋난다: '
            + ', '.join(stuck)))
    return out
```

`check_placement` 를 통째로 아래로 바꾼다.

```python
def check_placement(ref, hand):
    """H9 브리지 행 차이 · H10 칩 자리 차이(행·방향). 둘 다 표기다.

    칩이 밀리거나 180° 돌아 있어도 배선이 함께 옮겨져 있으면 그림은 유효하다.
    그래도 알리는 이유는 체크리스트의 좌표 표기와 어긋나기 때문이다 — 같이
    제출한다면 맞춰 두는 편이 낫다. 옮겨진 자리를 배선이 **안** 따라간 것은
    H14 가 본다. 행은 `chip_top_row` 로 잰다 — 돌린 칩은 `pin1_row` 가 아랫행이다.
    """
    out = []
    rmap, hmap = {}, {}
    for key, ch in zip(chip_keys(ref), ref.chips):
        rmap[key] = (chip_top_row(ch), ch.get('pin1_col', 'e'))
    for key, ch in zip(chip_keys(hand), hand.chips):
        hmap[key] = (chip_top_row(ch), ch.get('pin1_col', 'e'))
    for key, (rrow, rcol) in rmap.items():
        got = hmap.get(key)
        if got is None:
            continue
        hrow, hcol = got
        if hrow != rrow:
            out.append(HandFinding(
                'H10', '표기', key,
                f'참조는 칩 윗행이 {rrow}행인데 손그림은 {hrow}행이다 '
                f'({hrow - rrow:+d}행). 배선이 함께 옮겨져 있으면 회로는 맞다'))
        if hcol != rcol:
            out.append(HandFinding(
                'H10', '표기', key,
                f'참조는 pin 1 이 {rcol} 열(노치 위)인데 손그림은 {hcol} 열'
                f'(노치 아래)이다 — 칩이 180° 돌아 있다. '
                '배선이 함께 돌아 있으면 회로는 맞다'))

    # 메시지가 행만 말하므로 **행만 비교한다.** 종류까지 넣어 비교하면 전사가
    # `kind` 를 빠뜨렸을 때 '[29,30]인데 [29,30]이다' 라는 자기모순이 나온다
    rb = sorted({a[2] for _k, a, _b in ref.bridges})
    hb = sorted({a[2] for _k, a, _b in hand.bridges})
    if rb and hb and rb != hb:
        # 경고는 방향을 본다. round2 는 28·29행(참조보다 위)인데 '30행 아래'
        # 경고를 받았다 — 맞지 않는 조언이다
        below = max(hb) > max(rb)
        tail = ('레일이 가운데서 끊긴 실물 보드라면 참조보다 아래 놓인 브리지는 '
                '전원을 못 올린다' if below
                else '도면상 같은 노드라 회로에는 영향이 없다')
        out.append(HandFinding(
            'H9', '표기', '레일 브리지',
            f'참조는 {rb}행인데 손그림은 {hb}행이다. {tail}'))
    return out
```

- [ ] **Step 6: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_transcript.py tests/test_hand_compare.py -q`
Expected: 전부 PASS. `test_H14_실물_전사에서_칩이_올라가고_L1_저항이_남으면_잡는다` 가 문장 변경 후에도 통과한다 — 단언은 `'-1행'`·`'L1 저항 아랫다리 좌 d17'`·`'pin 1 행'` 이고 새 문장 `... (지금 pin 1 행)` 이 셋을 다 담는다.

`test_배선까지_함께_돌리면_...` 이 치명으로 깨지면 `_rotate_chip.m()` 이 돌린 홀이 원래 홀과 겹친 것이다(H2 줄이 홀을 가리킨다). 회전은 칩 행 안에서 전단사라 겹칠 수 없으니, 그 경우 `top`/`bottom` 계산이나 `_ROTATE_COL` 을 본다. 검사기를 테스트에 맞춰 느슨하게 만들지 않는다.

- [ ] **Step 7: 커밋한다**

```bash
git add scripts/lab/hand_transcript.py scripts/lab/hand_compare.py tests/test_hand_transcript.py tests/test_hand_compare.py
git commit -m "fix: pin1_col=f 를 180° 회전으로 놓는다 — 거울상은 꽂을 수 없다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: H14 의 요소 대조를 홀에서 노드로 접는다

**Files:**
- Modify: `scripts/lab/hand_compare.py:512-553` (`_unshifted_elements`)
- Test: `tests/test_hand_compare.py` (`class ChipFollow`)

**Interfaces:**
- Consumes: Task 1 의 `check_chip_follow` 가 `_unshifted_elements(ref, hand, delta)` 를 `(설명, 홀)` 목록으로 받는다는 계약. 그 계약은 유지한다.
- Produces: 없음 (내부 변경).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`class ChipFollow` 의 `test_권장_수정을_적용하면_H14_와_H7_이_사라진다` 바로 뒤에 넣는다.

```python
    def test_같은_노드_옆_홀에_남아도_H14_가_난다(self):
        """저항 아랫다리를 d17 이 아니라 c17 에 꽂아도 같은 노드다. 검사기의
        대원칙은 홀이 아니라 넷이다 — 이 함수만 홀을 비교하면 안 된다.
        2026-09-10 리뷰 Important 2."""
        hand = parse_transcript(self.FIXTURE)
        ref = hc.reference_diagram(hand.circuit)
        beside = ('left', 'c', 17)
        for r in hand.resistors:
            if r['tag'] == 'L1':
                r['bottom'] = beside
        for c in hand.chains:
            if c['tag'] == 'L1':
                c['res_bottom'] = beside
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual(len(found), 1)
        self.assertIn('L1 저항 아랫다리 좌 c17', found[0].message)
        self.assertIn('지금 pin 1 행', found[0].message)

    def test_칩이_떠난_자리의_문장은_머리말과_맞는다(self):
        """전체를 +1 밀면 74HC00 은 19~25행이고 18행이 빈다. pin 14 의 VCC
        선만 참조 자리(g18)에 두면 그 선은 칩이 떠난 허공에 남는다 — 19~25행
        어디에 남기면 다른 핀 행에 앉는 것이라 이 갈래가 아니다. "그 핀 행에
        앉았다" 로 읽히면 안 된다. 2026-09-10 리뷰 Important 3.
        (+1 이동은 레일 빈 행에 걸려 H1 이 나지만 H14 만 본다.)"""
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        hand.signed = True
        moved = ('hole', ('left', 'g', 19)), ('hole', ('left', 'mid_vcc', 19))
        for w in hand.wires:
            if (w['frm'], w['to']) == moved:
                w['frm'] = ('hole', ('left', 'g', 18))
                w['to'] = ('hole', ('left', 'mid_vcc', 18))
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].where, '74HC00')
        self.assertIn('칩과 어긋난다', found[0].message)
        self.assertIn('참조에서는 pin 14 행이었는데 칩이 떠났다', found[0].message)
        self.assertNotIn('앉았다', found[0].message)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py -q -k "옆_홀 or 떠난_자리"`
Expected: `test_같은_노드_옆_홀에_남아도_H14_가_난다` FAIL (`0 != 1`). `test_칩이_떠난_자리의_문장은_머리말과_맞는다` 는 Task 1 의 문장 변경으로 이미 PASS 일 수 있다 — 그래도 남긴다. 이 테스트가 H14 1건을 기대하는 근거: +1 밀린 74HC00 은 19~25행이고 남긴 선의 끝점 g18 은 노드 (T,left,18,R) 로 참조에서 pin 14 자리였다가 손그림에서는 핀이 없다. 되돌림 필터는 (g17, mid_vcc17) 이 참조에 없으므로 이 선을 거르지 않는다. 다른 끝점 mid_vcc18 은 레일 노드라 핀이 없어 조용하다. 74HC08 도 +1 밀렸지만 그 행에 남은 요소가 없어 줄이 없다 — 그래서 정확히 1건이다.

- [ ] **Step 3: 구현한다**

`_unshifted_elements` 를 통째로 아래로 바꾼다.

```python
def _unshifted_elements(ref, hand, delta):
    """참조 자리에 그대로 남은 손그림 요소 — (설명, 홀) 목록.

    **홀이 아니라 노드로 대조한다.** 같은 행 a~e 는 한 노드라 d17 에 남기든
    c17 에 남기든 같은 사실이다 — 2026-09-10 리뷰가 c17 사례를 놓치는 것을
    짚었다. 돌려주는 홀은 손그림 쪽 홀이다(판정문 주소용).

    LED·저항 다리는 꼬리표로 짝을 맞춘다. 배선은 꼬리표가 없어 끝점 노드 쌍으로
    맞추는데, 전체가 delta 만큼 밀린 그림에서는 레일 선이 우연히 참조의 다른
    선과 같은 자리에 올 수 있다(GND10→d10 이 밀려 GND11→d11 이 된다). 그래서
    **delta 만큼 되돌린 쌍이 참조에 있으면 '따라온 것'으로 보고 뺀다.** 잭
    끝점 배선은 칩 행에 앉을 수 없어 건너뛴다.
    """
    out = []
    ref_led = {(l['tag'], side): node_of(l[key]) for l in ref.leds
               for side, key in (('A', 'anode'), ('K', 'cathode'))}
    for l in hand.leds:
        for side, key in (('A', 'anode'), ('K', 'cathode')):
            if ref_led.get((l['tag'], side)) == node_of(l[key]):
                out.append((_describe(('LED', l['tag'], side)), l[key]))

    ref_res = {(r.get('tag', ''), side): node_of(r[key]) for r in ref.resistors
               for side, key in (('T', 'top'), ('B', 'bottom'))}
    for r in hand.resistors:
        for side, key in (('T', 'top'), ('B', 'bottom')):
            if ref_res.get((r.get('tag', ''), side)) == node_of(r[key]):
                out.append((_describe(('RES', r.get('tag', ''), side)), r[key]))

    ref_wires = {frozenset((node_of(w['frm'][1]), node_of(w['to'][1])))
                 for w in ref.wires
                 if w['frm'][0] == 'hole' and w['to'][0] == 'hole'}

    def back(hole):
        return node_of((hole[0], hole[1], hole[2] - delta))

    for w in hand.wires:
        if w['frm'][0] != 'hole' or w['to'][0] != 'hole':
            continue
        a, b = w['frm'][1], w['to'][1]
        if frozenset((node_of(a), node_of(b))) not in ref_wires:
            continue
        if delta and frozenset((back(a), back(b))) in ref_wires:
            continue
        desc = f"{w.get('kind', '')} 배선 끝점".strip()
        out.append((desc, a))
        out.append((desc, b))
    return out
```

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py -q`
Expected: 전부 PASS. 특히 `test_전체가_함께_밀린_그림에는_H14_가_없다` 가 여전히 비어 있다 — 노드로 접어도 되돌림 필터가 같은 논리로 선다.

추가 확인 (오탐 회귀): 여덟 회로 전부에 ±1 전체 이동을 걸어 H14 가 비는지 본다.

```bash
.venv/bin/python -c "
from scripts.lab import hand_compare as hc
from tests.test_hand_compare import _shift_rows
bad = []
for cid in hc.CIRCUITS:
    for d in (+1, -1):
        ref = hc.reference_diagram(cid); hand = _shift_rows(hc.reference_diagram(cid), d); hand.signed = True
        h14 = [str(f) for f in hc.compare(ref, hand) if f.rule == 'H14']
        if h14: bad.append((cid, d, h14))
print('H14 오탐:', bad)
" 2>&1 | grep -v SUCCESS
```

Expected: `H14 오탐: []`. (−1 이동은 일부 회로에서 H1 레일 빈 행이 날 수 있지만 그것은 H14 가 아니다.)

- [ ] **Step 5: 커밋한다**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "fix: H14 요소 대조를 홀에서 노드로 접는다 — 옆 홀에 남아도 잡는다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 문서·주석을 회전으로 고치고 설계 결정 #1 을 정정한다

**Files:**
- Modify: `.claude/skills/review-hand-diagram/SKILL.md:107-110` (전사 규칙), `:159` (H10 표), `:170-175` (판정 원칙)
- Modify: `docs/plans/2026-09-10-review-hand-diagram-칩자리-설계.md` (결정 #1 행, 정정 절)
- Modify: `scripts/lab/hand_compare.py:46` (주석), `tests/test_hand_compare.py:1` (모듈 독스트링)
- Test: `tests/test_skill_docs.py` — **커밋본** 검사만 쓴다. 작업 트리의 미커밋 변경은 건드리지 않는다.

**Interfaces:**
- Consumes: Task 1 의 `pin1_row` 의미(pin 1 표시 홀의 행).
- Produces: 없음.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 의 `class HandDiagramSkill` 에서 `test_전사가_pin_1_열을_적는다고_돼_있다` 를 아래로 바꾼다. 이 파일은 작업 트리에 미커밋 변경이 있으므로 **이 함수만** 고치고, 커밋할 때 `git add -p` 로 이 덩어리만 올린다.

```python
    def test_전사가_pin_1_열을_적는다고_돼_있다(self):
        """돌려 그린 칩은 pin1_col 없이는 전사가 못 담는다. 거울상이 아니라
        180° 회전이고, 그때 pin1_row 는 아랫행이라고 적혀 있어야 한다."""
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("pin1_col", text)
        self.assertIn("아랫행", text)
        self.assertNotIn("거울", text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_skill_docs.py -q -k "pin_1_열"`
Expected: FAIL — `'아랫행' not found`.

- [ ] **Step 3: SKILL.md 를 고친다**

전사 규칙의 `- **칩은 pin 1 표시가 어느 열인지 적는다.** ...` 항목을 아래로 바꾼다.

```markdown
- **칩은 pin 1 표시가 있는 홀의 행·열을 그대로 적는다.** 노치가 위를 보면
  pin 1 이 e 열 윗행이라 `"pin1_row"` 에 윗행, `"pin1_col": "e"` 다. 180° 돌려
  노치가 아래를 보면 pin 1 이 f 열 **아랫행**이라 `"pin1_row"` 에 아랫행,
  `"pin1_col": "f"` 다. 좌우로 뒤집힌 배치(pin 1 이 f 열 윗행)는 실물 DIP 가
  취할 수 없다 — 그렇게 보이면 번호를 잘못 읽은 것이니 확대해 다시 본다.
  없으면 e 로 읽는다. 채널을 걸치지 않은 칩(pin 1 이 a~d·g~j 열)은 전사가 못
  담으니 그 pin 1 홀을 `uncertain` 에 올린다 — H13 보류로 사람에게 간다.
```

검사 목록 표의 H10 줄을 바꾼다.

```markdown
| H10 | 칩 윗행·방향이 참조와 다름 | 표기 |
```

"판정할 때 지키는 것" 첫 항목을 아래로 바꾼다.

```markdown
- **행이 밀린 것은 오류가 아니다.** 칩과 배선이 함께 옮겨져(또는 180° 돌아)
  있으면 그림은 유효하다. H10 이 표기로만 알린다. 참조 좌표와 다르다는 이유로
  치명을 매기지 않는다. 다만 **따라오지 않은 요소가 옮겨진 칩의 핀 행에 앉거나
  칩이 떠난 자리에 남으면 H14 가 원인을 낸다** — 2026-09-09 시험 PDF 에서
  74HC00 이 한 행 올라갔는데 L1 저항만 참조 자리에 남아 아랫다리가 pin 1 행에
  앉은 것이 그 사례다. H7 이 증상을, H14 가 원인을 말한다. 요약할 때 H14 를
  첫 줄에 둔다. H14 는 홀이 아니라 노드로 대조한다 — d17 대신 c17 에 남겨도
  같은 결함이다.
```

- [ ] **Step 4: 설계서를 정정한다**

`docs/plans/2026-09-10-review-hand-diagram-칩자리-설계.md` 의 결정 표에서 `| 1 | 방향 표현 방식 | ...` 행을 아래로 바꾼다.

```markdown
| 1 | 방향 표현 방식 | `pin1_col` 선택 키, 기본 `e`, 값 `e`/`f` 만. **`pin1_row`·`pin1_col` 은 pin 1 표시가 있는 홀 그대로 — `f` 면 `pin1_row` 는 아랫행이다** (2026-09-10 정정) | `chip_pins` 가 e/f 를 못 박고 있다 (`hand_transcript.py:59`). 렌더러도 항상 e 다 (`render_breadboard.py:693`). 행 이동량은 `chip_top_row` 로 잰다 |
```

파일 끝에 절을 더한다.

```markdown
## 정정 (2026-09-10 리뷰)

- **결정 #1 의 배치가 틀렸었다.** 처음 명세 "'f' 면 pin 1~7 이 f 열, 8~14 가
  e 열" 은 행 방향을 안 적었고, 구현은 pin 1 을 f 열 **윗행**에 놓아 좌우
  거울상을 만들었다. 실물 DIP 는 그 도형을 취할 수 없다 — 노치를 아래로 돌리면
  pin 1 은 f 열 **아랫행**이다. 이 상태로 SKILL.md 지시대로 전사하면 돌린 칩마다
  H3·H5·H6 허위 치명이 난다. 수정: `chip_pins` 가 `'f'` 일 때 행을 내려가며
  놓고, `pin1_row` 는 pin 1 표시 홀의 행 그대로(아랫행), 행 이동량은
  `chip_top_row` 로 잰다. 계획 `2026-09-10-review-hand-diagram-칩자리-H14-수정.md`.
- **결정 #4·#5 의 "참조 좌표" 는 홀이 아니라 노드다.** 같은 행 a~e 는 한 노드라
  d17 에 남기든 c17 에 남기든 같은 사실이다. `_unshifted_elements` 가 `node_of`
  로 접어 대조한다.
- **"칩 밖" 갈래 문장.** 머리말을 "칩과 어긋난다" 로 바꾸고, 핀이 생긴 자리는
  "지금 pin n 행", 칩이 떠난 자리는 "참조에서는 pin n 행이었는데 칩이 떠났다" 로
  나눠 적는다.
```

- [ ] **Step 5: 낡은 주석을 고친다**

`scripts/lab/hand_compare.py` 의 `HandFinding.rule` 주석:

```python
    rule: str      # 'H1' ~ 'H14'
```

`tests/test_hand_compare.py` 모듈 독스트링 첫 줄:

```python
"""넷 모델과 규칙 14개를 검사한다.
```

- [ ] **Step 6: 통과를 확인한다**

Run: 기준 스위트.
Expected: 실패 0. 통과 건수는 시작 208 + Task 1 의 +3 (전사 2, 검사 1) + Task 2 의 +2 = 213 근처. 정확한 수보다 실패 0 이 기준이다.

- [ ] **Step 7: 시험 PDF 판정을 다시 내 문장을 확인한다 (커밋 없음)**

```bash
.venv/bin/python -c "
from pathlib import Path
from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import parse_transcript
out = Path('보고서/실험01/output/손그림검토/round2'); rnd = 2
pages = []
for p in sorted((out/'전사').glob('p*.json')):
    hand = parse_transcript(p)
    ref = hc.reference_diagram(hand.circuit)
    pages.append((hand.page, hand.circuit, hc.compare(ref, hand), hand))
(out/'판정.md').write_text(hc.judgment_markdown(pages, rnd), encoding='utf-8')
for page, _c, fs, _h in pages:
    for f in fs:
        print(page, f)
" 2>&1 | grep -v SUCCESS
```

Expected: H14 줄이 `1 [치명] H14 74HC00 — 참조보다 -1행 옮겨졌는데 다음 요소가 참조 좌표에 남아 칩과 어긋난다: L1 저항 아랫다리 좌 d17 (지금 pin 1 행)`. H10 줄이 `참조는 칩 윗행이 18행인데 손그림은 17행이다 (-1행)`. 나머지(H7·H9·H12)는 그대로.

- [ ] **Step 8: 커밋한다**

`tests/test_skill_docs.py` 는 미커밋 변경과 섞이지 않게 덩어리만 올린다.

```bash
git add .claude/skills/review-hand-diagram/SKILL.md docs/plans/2026-09-10-review-hand-diagram-칩자리-설계.md scripts/lab/hand_compare.py tests/test_hand_compare.py
git add -p tests/test_skill_docs.py
git commit -m "docs: 전사 규칙을 180° 회전으로 고쳐 쓰고 설계 결정 #1 을 정정한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

`git add -p` 에서 `test_전사가_pin_1_열을_적는다고_돼_있다` 덩어리만 `y`, 나머지는 `n`. 커밋 뒤 `git diff --stat tests/test_skill_docs.py` 로 미커밋 변경이 여전히 작업 트리에 남아 있는지 본다.

---

## Self-Review

**Spec coverage.** 리뷰 항목마다 Task 를 짚는다.
- Critical 1 (거울상 → 회전): Task 1. `chip_pins` 회전, `chip_top_row`, δ 측정 변경, `_rotate_chip`, 테스트 네 개(전사 3, 검사 3, H10 1).
- Important 2 (홀 → 노드): Task 2. `_unshifted_elements` 노드 접기, c17 회귀 테스트.
- Important 3 (문장 모순): Task 1 에서 문장 변경, Task 2 에서 테스트로 묶음.
- Minor 4 (블록 미확인): Task 1 `_rotate_chip.m()` 이 블록을 보고, e1_comb 테스트.
- Minor 5 (`_MIRROR` 레일 주석): Task 1 에서 `_ROTATE_COL` 로 바꾸며 레일을 빼고 이유를 주석에.
- Minor 6 (낡은 주석): Task 3.
- Minor 7 (블록 차이 무검사): 범위 밖으로 명시.
- 설계 결정 #1 정정: Task 3.
- SKILL.md 지시 정정: Task 3.
- 시험 PDF 재판정: Task 3 Step 7.

**Placeholder scan.** "적절히", "필요 시", "Task N 과 같이" 없음. 모든 코드 단계에 코드 블록이 있다.

**Type consistency.** `chip_pins(block, pin1_row, pin1_col)` 시그니처는 그대로고 `'f'` 의 의미만 바뀐다. `chip_top_row(chip)` 는 `chip['pins']` 만 읽으므로 참조 칩·손그림 칩·테스트의 `{'pins': ...}` 모두에 쓰인다. `_rotate_chip` 이 `chip_pins` 를 쓰므로 `tests/test_hand_compare.py` 의 기존 import (`Diagram, chip_pins, parse_transcript`) 로 충분하다. `_unshifted_elements` 의 반환 계약 `(설명, 손그림 홀)` 은 Task 1 의 `check_chip_follow` 가 `_addr(hole)` 로 쓰는 것과 맞는다. H14 문장의 부분 문자열 `'-1행'`·`'L1 저항 아랫다리 좌 d17'`·`'pin 1 행'`·`'f 열'`·`'배선 끝점'` 은 기존 테스트 단언을 전부 만족한다.
