# 칩 자리 변경 미추종 검사 (H14) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 손그림 전사가 칩 방향(pin 1 열)을 기록하고, 칩이 참조와 다른 자리(행·방향)에 있을 때 그 이동을 안 따라간 요소가 칩 핀 행에 앉으면 검사기가 H14 치명 한 줄로 칩 이름과 요소를 함께 내게 한다.

**Architecture:** 전사 스키마에 선택 키 `pin1_col` 을 더하고 `chip_pins` 가 거울상 배치를 만든다. `check_placement` 는 열 차이도 H10 표기로 적는다. 새 규칙 `check_chip_follow` 는 "참조 좌표 그대로인 요소"를 모아 그 노드에 앉은 칩 핀이 참조와 다른지 본다 — 거리 기준 없이 충돌만 본다. 증상 줄(H3·H6·H7)은 그대로 두고 H14 가 원인 줄로 더해진다.

**Tech Stack:** Python 3.14 표준 라이브러리 + `pillow` + `pymupdf`. 새 의존성 없음. 테스트는 `unittest` 를 pytest 로 돌린다.

**Spec:** `docs/plans/2026-09-10-review-hand-diagram-칩자리-설계.md`. 결정 #1~#10 이 거기 있다.

## Global Constraints

- **주석·문서·테스트 이름은 한국어.** 코드 식별자와 경로만 원문. 저장소 전체 관례다.
- **테스트 이름은 한국어 문장** (`def test_pin1_col_f_면_핀이_거울상이다`). `tests/test_hand_compare.py` 관례.
- **파이썬은 `.venv/bin/python` 으로 돈다.** 시스템 `python3` 에는 pytest 가 없다.
- **기준 스위트:**

  ```bash
  .venv/bin/python -m pytest tests/test_hand_grid.py tests/test_hand_transcript.py tests/test_hand_compare.py tests/test_breadboard_wiring.py tests/test_breadboard_physical.py tests/test_breadboard_readability.py tests/test_breadboard_coords.py tests/test_breadboard_diagram_cli.py tests/test_skill_docs.py -q
  ```

  시작 시점 **193건 통과, 1건 실패**. 실패 1건은 `test_skill_docs.py::SkillDocInvariants::test_worked_subsection_example_matches_the_approved_report` (예비보고서 "회로 결선도" 절 개수 7≠8) 로 이 작업과 무관하다. **고치지 않는다.** 아래에서 "기준 스위트 통과" 는 이 1건을 제외한 전부를 뜻한다.
- **`보고서/실험02`~`실험10` 이 작업 트리에서 삭제돼 있다.** 이 작업과 무관하다. 되살리지 않는다.
- **`보고서/실험01/output/손그림검토/` 는 git 이 추적하지 않는다.** 그 안의 파일은 커밋하지 않는다. 회귀 픽스처는 `tests/fixtures/` 에 복사한다.
- **검사기는 산문이 아니라 코드를 읽는다.** 배선 설명 문자열로 분기하지 않는다.
- **렌더러(`render_breadboard.py`)는 건드리지 않는다.** 참조 칩은 항상 pin 1 이 e 열이고, 검사기는 `ch.get('pin1_col', 'e')` 로 그 부재를 흡수한다.
- **H10 은 표기로 남는다** (결정 #9). 기존 테스트 `test_H10_칩이_밀리면_표기로만_알린다` 가 이를 고정한다.
- **한 파일을 여러 Task 가 고칠 때는 그 시점의 최종 함수 전체를 준다.** "끝에 추가" 로 쓰지 않는다.
- **커밋 메시지는 한국어 요약 + 대시 설명** (`feat: 전사가 pin 1 열을 적는다 — 뒤집힌 칩을 표현한다`). 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` 을 붙인다.

## 파일 구조

새 파일은 픽스처 하나다. 나머지는 고치는 자리만 적는다.

| 파일 | 이번에 바뀌는 책임 |
|---|---|
| `scripts/lab/hand_transcript.py` | `chip_pins` 가 `pin1_col` 을 받아 거울상 배치를 만든다. `parse_transcript` 가 `pin1_col` 을 읽고 검증한다 |
| `tests/test_hand_transcript.py` | 거울상 배치·기본값·거절 시험 |
| `scripts/lab/hand_compare.py` | `check_placement` 가 열 차이를 H10 으로 낸다. 새 `check_chip_follow` 와 보조 `_unshifted_elements` 가 H14 를 낸다. `_RULES` 등록 |
| `tests/test_hand_compare.py` | H10 방향 시험 · `_flip_chip` 헬퍼 · H14 시험 넷 · 규칙 코드 범위 H14 |
| `tests/fixtures/hand_e1_nand_chip_up_one.json` | 2026-09-09 round2 전사 복사본. 실물 회귀 사례 |
| `.claude/skills/review-hand-diagram/SKILL.md` | 전사 예시·전사 규칙·검사 목록·판정 원칙에 H14 반영 |
| `tests/test_skill_docs.py` | 규칙 개수 검사를 H14 까지로 |

---

### Task 1: 전사가 pin 1 열을 적는다

**Files:**
- Modify: `scripts/lab/hand_transcript.py:59-70` (`chip_pins`), `:111-127` (`parse_transcript` 칩 블록)
- Test: `tests/test_hand_transcript.py`

**Interfaces:**
- Consumes: 없음.
- Produces: `chip_pins(block: str, pin1_row: int, pin1_col: str = 'e') -> dict[int, tuple[str, str, int]]`. `pin1_col` 이 `'e'`·`'f'` 밖이면 `ValueError`. `parse_transcript` 가 만드는 칩 dict 에 `'pin1_col'` 키(`'e'` 또는 `'f'`)가 들어간다. Task 2·3 이 `ch.get('pin1_col', 'e')` 로 읽는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_transcript.py` 의 `class ChipPins` 를 아래 최종 형태로 바꾸고, `class Parse` 안 `test_최소_전사를_읽는다` 바로 뒤에 세 테스트를 넣는다.

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

    def test_pin1_col_f_면_핀이_거울상이다(self):
        """노치가 아래를 보게 그린 칩. pin 1~7 이 f 열, 8~14 가 e 열이다."""
        pins = ht.chip_pins('left', 17, 'f')
        self.assertEqual(pins[1], ('left', 'f', 17))
        self.assertEqual(pins[7], ('left', 'f', 23))
        self.assertEqual(pins[8], ('left', 'e', 23))
        self.assertEqual(pins[14], ('left', 'e', 17))

    def test_pin1_col_은_e_나_f_만_받는다(self):
        """DIP-14 는 채널을 걸친다. 다른 열은 핀 모델이 없다."""
        with self.assertRaises(ValueError):
            ht.chip_pins('left', 17, 'd')
```

```python
    def test_pin1_col_이_없으면_e_다(self):
        """기존 전사 파일은 pin1_col 이 없다. 그대로 읽혀야 한다."""
        d = ht.parse_transcript(_write(MINIMAL))
        self.assertEqual(d.chips[0]['pin1_col'], 'e')
        self.assertEqual(d.chips[0]['pins'][1], ('left', 'e', 7))

    def test_pin1_col_f_를_읽는다(self):
        obj = dict(MINIMAL)
        obj['chips'] = [{"label": "74HC08", "block": "left",
                         "pin1_row": 7, "pin1_col": "f"}]
        d = ht.parse_transcript(_write(obj))
        self.assertEqual(d.chips[0]['pin1_col'], 'f')
        self.assertEqual(d.chips[0]['pins'][1], ('left', 'f', 7))
        self.assertEqual(d.chips[0]['pins'][14], ('left', 'e', 7))

    def test_pin1_col_이_e_f_밖이면_TranscriptError(self):
        """채널을 안 걸친 칩은 전사가 못 담는다. uncertain 으로 보내라고 말한다."""
        obj = dict(MINIMAL)
        obj['chips'] = [{"label": "74HC08", "block": "left",
                         "pin1_row": 7, "pin1_col": "d"}]
        with self.assertRaises(ht.TranscriptError) as cm:
            ht.parse_transcript(_write(obj))
        self.assertIn('uncertain', str(cm.exception))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_transcript.py -q -k "pin1_col"`
Expected: 5 failed — `chip_pins() takes 2 positional arguments` 와 `KeyError: 'pin1_col'`.

- [ ] **Step 3: 구현한다**

`scripts/lab/hand_transcript.py` 의 `chip_pins` 를 통째로 바꾼다.

```python
def chip_pins(block, pin1_row, pin1_col='e'):
    """DIP-14 가 꽂히는 홀. pin 1~7 은 pin 1 열, pin 8~14 는 건너편 열.

    `pin1_col='e'` 가 렌더러 `draw_chip()` 이 꽂는 자리와 같아야 한다 —
    `test_핀_배치가_렌더러와_같다` 가 그것을 묶어 둔다. `'f'` 는 노치가 아래를
    보게 그린 칩이다. 채널을 걸치지 않는 열은 핀 모델이 없어 거절한다.
    """
    across = {'e': 'f', 'f': 'e'}
    if pin1_col not in across:
        raise ValueError(
            f"pin 1 열은 e 또는 f 다 — DIP-14 는 채널을 걸친다: {pin1_col!r}")
    pins = {}
    for i in range(7):
        pins[i + 1] = (block, pin1_col, pin1_row + i)
        pins[14 - i] = (block, across[pin1_col], pin1_row + i)
    return pins
```

`parse_transcript` 의 칩 블록(`chips = []` 부터 `chips.append(...)` 까지)을 아래로 바꾼다.

```python
    chips = []
    for ch in obj['chips']:
        try:
            label = ch['label']
            pin1_row = ch['pin1_row']
        except KeyError as e:
            raise TranscriptError(f"칩 항목에 필수 키 {e} 가 없다: {ch}") from e
        block = BLOCKS.get(ch.get('block'), ch.get('block'))
        if block not in ('left', 'right'):
            raise TranscriptError(f"블록이 좌/우가 아니다: {ch.get('block')!r}")
        try:
            row = int(pin1_row)
        except (ValueError, TypeError) as e:
            raise TranscriptError(f"pin1_row 가 정수가 아니다: {pin1_row!r}") from e
        _check_row(row, f"{label} pin1_row={row}")
        # pin 1 열. 없으면 e — 기존 전사가 전부 그렇다. 뒤집어 그린 칩은 f 다.
        # 채널을 안 걸친 칩(a~d·g~j)은 핀 모델이 없어 전사가 못 담는다 —
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

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_transcript.py -q`
Expected: 전부 PASS (기존 17건 + 새 5건).

- [ ] **Step 5: 커밋한다**

```bash
git add scripts/lab/hand_transcript.py tests/test_hand_transcript.py
git commit -m "feat: 전사가 pin 1 열을 적는다 — 뒤집힌 칩을 표현한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: H10 이 칩 방향 차이도 표기로 낸다

**Files:**
- Modify: `scripts/lab/hand_compare.py:489-519` (`check_placement`)
- Test: `tests/test_hand_compare.py` (`class Paperwork`, `test_H10_칩이_밀리면_표기로만_알린다` 바로 뒤)

**Interfaces:**
- Consumes: Task 1 의 칩 dict `'pin1_col'` 키와 `chip_pins(block, row, 'f')`.
- Produces: `check_placement` 가 열 차이에 `HandFinding('H10', '표기', <칩 키>, ...)` 를 하나 더 낸다. 메시지에 `'f 열'` 이 들어간다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_compare.py` 상단 import 를 아래로 바꾼다 (`chip_pins` 를 더한다).

```python
import unittest

from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import Diagram, chip_pins
```

`class Paperwork` 의 `test_H10_칩이_밀리면_표기로만_알린다` 바로 뒤에 넣는다.

```python
    def test_H10_칩이_뒤집히면_표기로_알린다(self):
        """노치가 아래를 보게 그린 칩. 배선이 함께 뒤집혀 있으면 회로는 맞다."""
        ref, hand = self._pair()
        ch = hand.chips[1]
        ch['pin1_col'] = 'f'
        ch['pins'] = chip_pins(ch['block'], ch['pin1_row'], 'f')
        found = [f for f in hc.check_placement(ref, hand) if f.rule == 'H10']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].grade, '표기')
        self.assertEqual(found[0].where, '74HC00')
        self.assertIn('f 열', found[0].message)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py -q -k "뒤집히면_표기"`
Expected: FAIL — `AssertionError: 0 != 1`.

- [ ] **Step 3: 구현한다**

`scripts/lab/hand_compare.py` 의 `check_placement` 를 통째로 아래로 바꾼다.

```python
def check_placement(ref, hand):
    """H9 브리지 행 차이 · H10 칩 자리 차이(행·방향). 둘 다 표기다.

    칩이 밀리거나 뒤집혀도 배선이 함께 옮겨져 있으면 그림은 유효하다. 그래도
    알리는 이유는 체크리스트의 좌표 표기와 어긋나기 때문이다 — 같이 제출한다면
    맞춰 두는 편이 낫다. 옮겨진 자리를 배선이 **안** 따라간 것은 H14 가 본다.
    """
    out = []
    rmap, hmap = {}, {}
    for key, ch in zip(chip_keys(ref), ref.chips):
        rmap[key] = (ch['pin1_row'], ch.get('pin1_col', 'e'))
    for key, ch in zip(chip_keys(hand), hand.chips):
        hmap[key] = (ch['pin1_row'], ch.get('pin1_col', 'e'))
    for key, (rrow, rcol) in rmap.items():
        got = hmap.get(key)
        if got is None:
            continue
        hrow, hcol = got
        if hrow != rrow:
            out.append(HandFinding(
                'H10', '표기', key,
                f'참조는 pin 1 이 {rrow}행인데 손그림은 {hrow}행이다 '
                f'({hrow - rrow:+d}행). 배선이 함께 옮겨져 있으면 회로는 맞다'))
        if hcol != rcol:
            out.append(HandFinding(
                'H10', '표기', key,
                f'참조는 pin 1 이 {rcol} 열인데 손그림은 {hcol} 열이다 — '
                '칩이 뒤집혀 있다. 배선이 함께 뒤집혀 있으면 회로는 맞다'))

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

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py -q`
Expected: 전부 PASS. 특히 `test_H10_칩이_밀리면_표기로만_알린다` 가 그대로 통과한다 (행 차이 줄 하나만 난다).

- [ ] **Step 5: 커밋한다**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: H10 이 칩 방향 차이도 표기로 낸다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: H14 — 칩 자리 변경을 안 따라간 요소

**Files:**
- Create: `tests/fixtures/hand_e1_nand_chip_up_one.json`
- Modify: `scripts/lab/hand_compare.py` (`check_placement` 앞에 `_unshifted_elements`·`check_chip_follow` 추가, `_RULES`)
- Test: `tests/test_hand_compare.py` (헬퍼 `_flip_chip`, 새 `class ChipFollow`, `class RuleRegistry`)

**Interfaces:**
- Consumes: Task 1 의 `chip_pins(block, row, pin1_col)` 과 칩 dict `'pin1_col'`. 기존 `node_of`, `chip_keys`, `_describe`, `_addr`, `HandFinding`.
- Produces: `check_chip_follow(ref, hand) -> list[HandFinding]` (규칙 `'H14'`, 등급 `'치명'`, `where` = 칩 키). `_unshifted_elements(ref, hand, delta) -> list[tuple[str, tuple]]` — `(설명, 홀)` 목록. Task 4 문서와 Task 5 재판정이 H14 를 전제한다.

- [ ] **Step 1: 실물 회귀 픽스처를 만든다**

2026-09-09 round2 전사를 복사한다. 원본이 없으면 아래 내용으로 그대로 쓴다.

```bash
cp 보고서/실험01/output/손그림검토/round2/전사/p1.json tests/fixtures/hand_e1_nand_chip_up_one.json
```

내용 (원본과 같아야 한다):

```json
{
  "page": 1,
  "circuit": "e1_nand",
  "title": "2-1 NAND Gate",
  "signed": false,
  "chips": [
    {"label": "74HC08", "block": "좌", "pin1_row": 7},
    {"label": "74HC00", "block": "좌", "pin1_row": 17}
  ],
  "wires": [
    {"color": "빨강", "from": "전원잭(빨강)", "to": "좌 VCC레일3행"},
    {"color": "파랑", "from": "전원잭(회색)", "to": "좌 GND레일3행"},
    {"color": "검정", "from": "좌 GND레일7행", "to": "좌 b7"},
    {"color": "빨강", "from": "좌 g7", "to": "좌 중앙VCC레일7행"},
    {"color": "파랑", "from": "좌 g8", "to": "좌 중앙GND레일7행"},
    {"color": "검정", "from": "좌 GND레일9행", "to": "좌 b8"},
    {"color": "파랑", "from": "좌 g9", "to": "좌 중앙GND레일9행"},
    {"color": "초록", "from": "좌 b9", "to": "좌 b14"},
    {"color": "초록", "from": "좌 a9", "to": "좌 a17"},
    {"color": "파랑", "from": "좌 GND레일10행", "to": "좌 d10"},
    {"color": "파랑", "from": "좌 GND레일11행", "to": "좌 d11"},
    {"color": "파랑", "from": "좌 g11", "to": "좌 중앙GND레일11행"},
    {"color": "파랑", "from": "좌 g12", "to": "좌 중앙GND레일12행"},
    {"color": "파랑", "from": "좌 GND레일13행", "to": "좌 d13"},
    {"color": "파랑", "from": "좌 GND레일16행", "to": "좌 b16"},
    {"color": "빨강", "from": "좌 g17", "to": "좌 중앙VCC레일17행"},
    {"color": "파랑", "from": "좌 g18", "to": "좌 중앙GND레일17행"},
    {"color": "검정", "from": "좌 GND레일18행", "to": "좌 d18"},
    {"color": "파랑", "from": "좌 g19", "to": "좌 중앙GND레일18행"},
    {"color": "검정", "from": "좌 c19", "to": "좌 c24"},
    {"color": "파랑", "from": "좌 GND레일19행", "to": "좌 c20"},
    {"color": "파랑", "from": "좌 GND레일21행", "to": "좌 c21"},
    {"color": "파랑", "from": "좌 g21", "to": "좌 중앙GND레일21행"},
    {"color": "파랑", "from": "좌 g22", "to": "좌 중앙GND레일22행"},
    {"color": "파랑", "from": "좌 GND레일23행", "to": "좌 c23"},
    {"color": "파랑", "from": "좌 GND레일27행", "to": "좌 c27"}
  ],
  "leds": [
    {"tag": "L1", "anode": "좌 c14", "cathode": "좌 c15"},
    {"tag": "L2", "anode": "좌 d24", "cathode": "좌 d25"}
  ],
  "resistors": [
    {"tag": "L1", "top": "좌 d15", "bottom": "좌 d17"},
    {"tag": "L2", "top": "좌 e25", "bottom": "좌 e27"}
  ],
  "bridges": [
    {"kind": "gnd", "from": "좌 GND레일28행", "to": "좌 중앙GND레일28행"},
    {"kind": "vcc", "from": "좌 VCC레일29행", "to": "좌 중앙VCC레일29행"}
  ],
  "uncertain": []
}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_hand_compare.py` 상단, `_shift_rows` 정의 바로 뒤(`class Nodes` 앞)에 헬퍼를 넣는다.

```python
_MIRROR = {'a': 'j', 'b': 'i', 'c': 'h', 'd': 'g', 'e': 'f',
           'f': 'e', 'g': 'd', 'h': 'c', 'i': 'b', 'j': 'a',
           'gnd': 'mid_gnd', 'vcc': 'mid_vcc',
           'mid_gnd': 'gnd', 'mid_vcc': 'vcc'}


def _flip_chip(d, index, wiring=True):
    """index 번째 칩을 뒤집는다(pin 1 이 f 열). `wiring=True` 면 그 칩 행에
    끝점이 있는 요소도 좌우 거울상으로 옮긴다 — 배선이 함께 뒤집힌 그림이다.
    `False` 면 칩만 뒤집고 배선은 참조 자리에 둔다."""
    ch = d.chips[index]
    rows = range(ch['pin1_row'], ch['pin1_row'] + 7)
    ch['pin1_col'] = 'f'
    ch['pins'] = chip_pins(ch['block'], ch['pin1_row'], 'f')
    if not wiring:
        return d

    def m(hole):
        if hole is None or hole[2] not in rows:
            return hole
        return (hole[0], _MIRROR[hole[1]], hole[2])

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

`class Paperwork` 바로 앞에 새 클래스를 넣는다.

```python
class ChipFollow(unittest.TestCase):
    """2026-09-09 시험 PDF: 74HC00 을 한 행 위(17행)에 그리고 아래 배선은 전부
    따라갔는데 L1 저항만 참조 자리(d15→d17)에 남았다. H7 이 증상을, H10 이
    행 차이를 각각 냈지만 둘을 잇는 줄은 사람이 요약할 때 만들었다. 그 줄이
    H14 다 — 칩 이름·이동량·남은 요소를 한 줄에 낸다."""

    FIXTURE = Path(__file__).parent / 'fixtures' / 'hand_e1_nand_chip_up_one.json'

    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.signed = True
        hand.title = '2-1 NAND Gate'
        return ref, hand

    def test_H14_실물_전사에서_칩이_올라가고_L1_저항이_남으면_잡는다(self):
        hand = parse_transcript(self.FIXTURE)
        ref = hc.reference_diagram(hand.circuit)
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual(len(found), 1)
        f = found[0]
        self.assertEqual(f.grade, '치명')
        self.assertEqual(f.where, '74HC00')
        self.assertIn('-1행', f.message)
        self.assertIn('L1 저항 아랫다리 좌 d17', f.message)
        self.assertIn('pin 1 행', f.message)
        # 74HC08 은 참조 자리 그대로다 — 줄이 없다
        self.assertNotIn('74HC08', f.message)

    def test_H14_는_증상_줄을_지우지_않는다(self):
        """H7 은 여전히 저항 아랫다리를 짚는다. H14 는 원인 줄이다."""
        hand = parse_transcript(self.FIXTURE)
        ref = hc.reference_diagram(hand.circuit)
        rules = {f.rule for f in hc.compare(ref, hand)}
        self.assertIn('H7', rules)
        self.assertIn('H10', rules)
        self.assertIn('H14', rules)

    def test_전체가_함께_밀린_그림에는_H14_가_없다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        hand.signed = True
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual([str(x) for x in found], [])

    def test_권장_수정을_적용하면_H14_와_H7_이_사라진다(self):
        """실물 전사에서 저항 아랫다리만 d17 → d16 으로 올린다. L1 LED(c14·c15)와
        저항 윗다리(d15)는 여전히 참조 자리 그대로지만 74HC00 은 17~23행이라
        충돌이 없다 — 참조 좌표에 남았다는 것만으로는 H14 를 내지 않는다.
        2026-09-09 요약이 권한 수정이 정확히 이것이다."""
        hand = parse_transcript(self.FIXTURE)
        ref = hc.reference_diagram(hand.circuit)
        fixed = ('left', 'd', 16)
        for r in hand.resistors:
            if r['tag'] == 'L1':
                r['bottom'] = fixed
        for c in hand.chains:
            if c['tag'] == 'L1':
                c['res_bottom'] = fixed
        found = hc.compare(ref, hand)
        self.assertEqual([str(f) for f in found if f.rule in ('H14', 'H7')], [])
        self.assertEqual([str(f) for f in found if f.grade in hc.BLOCKING], [])
        self.assertEqual(hc.verdict(found), '제출 가능')

    def test_칩만_뒤집고_배선을_두면_H14_가_난다(self):
        ref, hand = self._pair()
        _flip_chip(hand, 1, wiring=False)
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H14']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].where, '74HC00')
        self.assertIn('f 열', found[0].message)
        self.assertIn('배선 끝점', found[0].message)

    def test_배선까지_함께_뒤집으면_H14_없이_H10_표기만_난다(self):
        """넷이 같으면 유효한 그림이다 — 행 밀림과 같은 원리."""
        ref, hand = self._pair()
        _flip_chip(hand, 1, wiring=True)
        found = hc.compare(ref, hand)
        self.assertEqual([str(f) for f in found if f.rule == 'H14'], [])
        self.assertEqual([str(f) for f in found if f.grade == '치명'], [])
        h10 = [f for f in found if f.rule == 'H10']
        self.assertEqual(len(h10), 1)
        self.assertIn('f 열', h10[0].message)
```

파일 상단 import 를 최종 형태로 맞춘다.

```python
import unittest
from pathlib import Path

from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import Diagram, chip_pins, parse_transcript
```

`class RuleRegistry` 의 규칙 코드 테스트를 바꾼다.

```python
    def test_규칙_코드가_H1부터_H14까지_빠짐없다(self):
        import inspect
        src = inspect.getsource(hc)
        for n in range(1, 15):
            self.assertIn(f"'H{n}'", src, f'H{n} 규칙이 없다')
```

- [ ] **Step 3: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py -q -k "ChipFollow or 규칙_코드"`
Expected: 7건 중 `test_전체가_함께_밀린_그림에는_H14_가_없다` 와 `test_권장_수정을_적용하면_H14_와_H7_이_사라진다` 만 PASS(H14 가 아직 없으니 비어 있고, 고친 사슬은 H7 도 없다), 나머지 5건 FAIL.

- [ ] **Step 4: 구현한다**

`scripts/lab/hand_compare.py` 에서 `check_placement` 정의 **바로 앞**에 두 함수를 넣는다.

```python
def _unshifted_elements(ref, hand, delta):
    """참조 좌표에 그대로 남은 손그림 요소 — (설명, 홀) 목록.

    LED·저항 다리는 꼬리표로 짝을 맞춘다. 배선은 꼬리표가 없어 끝점 홀 쌍으로
    맞추는데, 전체가 delta 만큼 밀린 그림에서는 레일 선이 우연히 참조의 다른
    선과 같은 자리에 올 수 있다(GND10→d10 이 밀려 GND11→d11 이 된다). 그래서
    **delta 만큼 되돌린 쌍이 참조에 있으면 '따라온 것'으로 보고 뺀다.** 잭
    끝점 배선은 칩 행에 앉을 수 없어 건너뛴다.
    """
    out = []
    ref_led = {(l['tag'], side): l[key] for l in ref.leds
               for side, key in (('A', 'anode'), ('K', 'cathode'))}
    for l in hand.leds:
        for side, key in (('A', 'anode'), ('K', 'cathode')):
            if ref_led.get((l['tag'], side)) == l[key]:
                out.append((_describe(('LED', l['tag'], side)), l[key]))

    ref_res = {(r.get('tag', ''), side): r[key] for r in ref.resistors
               for side, key in (('T', 'top'), ('B', 'bottom'))}
    for r in hand.resistors:
        for side, key in (('T', 'top'), ('B', 'bottom')):
            if ref_res.get((r.get('tag', ''), side)) == r[key]:
                out.append((_describe(('RES', r.get('tag', ''), side)), r[key]))

    ref_wires = {frozenset((w['frm'][1], w['to'][1])) for w in ref.wires
                 if w['frm'][0] == 'hole' and w['to'][0] == 'hole'}

    def back(hole):
        return (hole[0], hole[1], hole[2] - delta)

    for w in hand.wires:
        if w['frm'][0] != 'hole' or w['to'][0] != 'hole':
            continue
        a, b = w['frm'][1], w['to'][1]
        if frozenset((a, b)) not in ref_wires:
            continue
        if delta and frozenset((back(a), back(b))) in ref_wires:
            continue
        desc = f"{w.get('kind', '')} 배선 끝점".strip()
        out.append((desc, a))
        out.append((desc, b))
    return out


def check_chip_follow(ref, hand):
    """H14 칩 자리 변경을 안 따라간 요소.

    2026-09-09 시험 PDF 에서 74HC00 이 한 행 위(17행)에 있고 아래 배선은 전부
    따라갔는데 L1 저항만 참조 자리(d15→d17)에 남아 저항 아랫다리가 pin 1 행에
    앉았다. H7 이 증상("GND 에 안 닿는다")을, H10 이 행 차이를 냈지만 둘을 잇는
    줄이 없어 판정문만 읽으면 저항 한 줄 고치라는 뜻으로 읽혔다.

    거리 기준을 쓰지 않는다. **참조 좌표 그대로인 요소가 앉은 노드에서 이 칩의
    핀이 참조와 달라졌는가** 만 본다. 행 이동이면 참조에서 핀이 없던 노드에
    핀이 생기고(∅ → pin n), 뒤집힘이면 같은 노드의 핀 번호가 바뀐다(1 ↔ 14).
    충돌이 없으면 회로는 멀쩡하고 H10 표기만 남는다. 증상 줄(H3·H6·H7)은
    그대로 두고 이 줄을 더한다 — 같은 층위의 메아리가 아니라 원인 줄이다.
    """
    out = []
    rchips = dict(zip(chip_keys(ref), ref.chips))
    hchips = dict(zip(chip_keys(hand), hand.chips))
    for key, rch in rchips.items():
        hch = hchips.get(key)
        if hch is None:
            continue
        delta = hch['pin1_row'] - rch['pin1_row']
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
            where = (f'pin {h_pin} 행' if h_pin is not None
                     else f'참조에서는 pin {r_pin} 행, 지금은 칩 밖')
            stuck.append(f'{desc} {_addr(hole)} ({where})')
        if not stuck:
            continue
        how = []
        if delta:
            how.append(f'참조보다 {delta:+d}행 옮겨졌')
        if hcol != rcol:
            how.append(f'pin 1 이 {hcol} 열로 뒤집혔')
        out.append(HandFinding(
            'H14', '치명', key,
            '고 '.join(how) + '는데 다음 요소가 참조 좌표에 남아 그 핀 행에 '
            '앉았다: ' + ', '.join(stuck)))
    return out
```

`_RULES` 를 아래로 바꾼다.

```python
# 규칙을 여기 순서대로 돈다. 새 규칙은 이 목록에 올린다 — 함수만 만들고
# 목록에 안 올리면 검사가 조용히 빠진다. 2026-09-08 회차에서 LED 사슬 검사를
# 통째로 건너뛴 것이 바로 그 실패였다
_RULES = [check_holes, check_power, check_signals, check_led_chains,
          check_rails, check_chip_follow, check_placement, check_paperwork]
```

- [ ] **Step 5: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py tests/test_hand_transcript.py -q`
Expected: 전부 PASS. `test_check_로_시작하는_함수는_전부_규칙_목록에_있다` 가 `check_chip_follow` 등록을 확인한다.

`test_배선까지_함께_뒤집으면_H14_없이_H10_표기만_난다` 가 치명 0건에서 깨지면 `_flip_chip` 이 거울상으로 옮긴 홀 중 참조에 없는 자리가 생긴 것이다 — 그 경우 실패 메시지의 H1·H2 줄이 가리키는 홀을 `_MIRROR` 표와 맞춰 본다. 검사기 코드를 그 테스트에 맞춰 느슨하게 만들지 않는다.

- [ ] **Step 6: 기준 스위트를 돌린다**

Run: 기준 스위트 (Global Constraints 의 명령).
Expected: 기존 실패 1건(`test_worked_subsection_example_matches_the_approved_report`)만 남고 나머지 전부 PASS. 통과 건수는 193 + Task 1 의 5 + Task 2 의 1 + Task 3 의 6 = 205.

- [ ] **Step 7: 커밋한다**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py tests/fixtures/hand_e1_nand_chip_up_one.json
git commit -m "feat: H14 — 칩 자리 변경을 안 따라간 요소를 원인 줄로 낸다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 스킬 문서에 pin1_col 과 H14 를 적는다

**Files:**
- Modify: `.claude/skills/review-hand-diagram/SKILL.md:82-85` (전사 예시), `:96-108` (전사 규칙), `:142-158` (검사 목록), `:165-167` (판정 원칙)
- Test: `tests/test_skill_docs.py:651-654`

**Interfaces:**
- Consumes: Task 1 의 `pin1_col` 키 이름, Task 3 의 규칙 코드 `H14`.
- Produces: 없음 (문서).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 의 `test_규칙_열세개가_전부_적혀_있다` 를 아래로 바꾼다.

```python
    def test_규칙_열네개가_전부_적혀_있다(self):
        text = HAND.read_text(encoding="utf-8")
        for n in range(1, 15):
            self.assertIn(f"H{n}", text)

    def test_전사가_pin_1_열을_적는다고_돼_있다(self):
        """뒤집어 그린 칩은 pin1_col 없이는 전사가 못 담는다."""
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("pin1_col", text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_skill_docs.py -q -k "열네개 or pin_1_열"`
Expected: 2 failed — `'H14' not found`, `'pin1_col' not found`.

- [ ] **Step 3: 문서를 고친다**

`.claude/skills/review-hand-diagram/SKILL.md` 의 전사 예시 `chips` 를 아래로 바꾼다.

```json
  "chips": [
    {"label": "74HC08", "block": "좌", "pin1_row": 7, "pin1_col": "e"},
    {"label": "74HC00", "block": "좌", "pin1_row": 17, "pin1_col": "e"}
  ],
```

전사 규칙 목록에서 `- 회로 ID(\`circuit\`)는 ...` 항목 **앞**에 한 항목을 넣는다.

```markdown
- **칩은 pin 1 표시가 어느 열인지 적는다.** 노치가 위를 보면 `"pin1_col": "e"`,
  아래를 보면 `"f"` 다. 없으면 e 로 읽는다. 채널을 걸치지 않은 칩(pin 1 이
  a~d·g~j 열)은 전사가 못 담으니 그 pin 1 홀을 `uncertain` 에 올린다 — H13
  보류로 사람에게 간다.
```

검사 목록 표의 `| H10 | 칩 pin 1 행이 참조와 다름 | 표기 |` 를 아래로 바꾸고, `| H13 | ... |` 뒤에 H14 줄을 넣는다.

```markdown
| H10 | 칩 pin 1 행·열이 참조와 다름 | 표기 |
```

```markdown
| H14 | 칩 자리 변경(행·방향)을 안 따라간 요소가 칩 핀 행에 앉음 | 치명 |
```

"판정할 때 지키는 것" 의 첫 항목을 아래로 바꾼다.

```markdown
- **행이 밀린 것은 오류가 아니다.** 칩과 배선이 함께 옮겨져(또는 뒤집혀)
  있으면 그림은 유효하다. H10 이 표기로만 알린다. 참조 좌표와 다르다는 이유로
  치명을 매기지 않는다. 다만 **따라오지 않은 요소가 옮겨진 칩의 핀 행에 앉으면
  H14 가 원인을 낸다** — 2026-09-09 시험 PDF 에서 74HC00 이 한 행 올라갔는데
  L1 저항만 참조 자리에 남아 아랫다리가 pin 1 행에 앉은 것이 그 사례다. H7 이
  증상을, H14 가 원인을 말한다. 요약할 때 H14 를 첫 줄에 둔다.
```

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_skill_docs.py -q -k "HandDiagram or 열네개 or pin_1_열 or 손그림"`
Expected: PASS. 이어서 기준 스위트를 돌려 기존 실패 1건 외 전부 PASS 인지 본다.

- [ ] **Step 5: 커밋한다**

```bash
git add .claude/skills/review-hand-diagram/SKILL.md tests/test_skill_docs.py
git commit -m "docs: 전사에 pin1_col, 검사 목록에 H14 를 적는다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 시험 PDF 를 다시 판정한다 (round2 제자리 갱신)

**Files:**
- Modify (미추적 산출물, 커밋 안 함): `보고서/실험01/output/손그림검토/round2/판정.md`
- Create (미추적): `보고서/실험01/output/손그림검토/round2/hand.pdf`

**Interfaces:**
- Consumes: Task 3 의 `check_chip_follow` 가 `_RULES` 에 있어야 한다.
- Produces: 없음. 사용자 확인용 산출물이다.

- [ ] **Step 1: PDF 를 round1 관례대로 보관한다**

```bash
cp "/Users/hyunjun_macbook_pro/Downloads/논실 2-1 수정.pdf" "보고서/실험01/output/손그림검토/round2/hand.pdf"
```

원본 PDF 가 Downloads 에 없으면 이 단계를 건너뛰고 요약에 그렇게 적는다.

- [ ] **Step 2: 같은 전사로 판정을 다시 낸다**

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

Expected: 첫 줄이 `1 [치명] H14 74HC00 — 참조보다 -1행 옮겨졌는데 다음 요소가 참조 좌표에 남아 그 핀 행에 앉았다: L1 저항 아랫다리 좌 d17 (pin 1 행)`. 이어 H7 (L1 좌 d17), H10 (74HC00 -1행), H12, H9 가 그대로 난다. 총평은 `수정 필요`.

- [ ] **Step 3: 판정문을 확인한다**

```bash
sed -n 1,25p 보고서/실험01/output/손그림검토/round2/판정.md
```

Expected: 표의 첫 행이 H14 다 (치명 정렬 안에서 규칙 코드 순이라 H14 는 H6·H7 뒤에 올 수 있다 — `compare` 는 `(등급, 규칙)` 으로 정렬한다. H14 가 표에 있으면 된다).

- [ ] **Step 4: 커밋하지 않는다**

`보고서/실험01/output/손그림검토/` 는 미추적이다. `git status --short | grep 손그림검토` 가 아무것도 내지 않아야 한다.

---

## Self-Review

**Spec coverage.** 설계 §구현 명세의 항목을 하나씩 짚는다.
- `chip_pins(block, pin1_row, pin1_col='e')` + `ValueError` → Task 1.
- `parse_transcript` 의 `pin1_col` 읽기·거절·메시지 → Task 1.
- 참조 쪽 `ch.get('pin1_col', 'e')` → Task 2·3 코드가 그렇게 읽는다.
- `check_placement` 열 비교 H10 → Task 2.
- `check_chip_follow` 네 단계(칩 순회·그대로인 요소·핀 변화·한 줄) → Task 3.
- `_RULES` 등록 → Task 3.
- 테스트 다섯 종(실물 픽스처·전체 이동·충돌 없음·뒤집힘 둘)과 규칙 코드 범위 → Task 3.
- 전사 테스트 셋 → Task 1.
- SKILL.md 네 자리 → Task 4.
- round2 재판정과 hand.pdf → Task 5.
- 결정 #9(표기 유지)는 기존 H10 테스트가 지킨다. 결정 #10(round2 갱신)은 Task 5.

**Placeholder scan.** "적절히", "필요 시", "Task N 과 같이" 없음. 모든 코드 단계에 코드 블록이 있다.

**Type consistency.** `chip_pins(block, row, 'f')` 호출이 Task 1 시그니처와 맞는다. `_unshifted_elements(ref, hand, delta)` 가 `(desc, hole)` 튜플을 내고 `check_chip_follow` 가 그렇게 푼다. `HandFinding(rule, grade, where, message)` 순서가 기존 정의와 같다. 테스트 파일 import 의 최종 형태(`Path`, `chip_pins`, `parse_transcript`)를 Task 3 에서 한 번에 준다 — Task 2 는 `chip_pins` 만 더한 중간 형태를 주는데, Task 3 이 그것을 덮는 최종 형태를 명시하므로 파일 중간에 import 가 끼지 않는다.
