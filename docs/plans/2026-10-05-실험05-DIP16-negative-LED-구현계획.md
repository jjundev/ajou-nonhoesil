# 실험05 DIP-16 · Negative Logic LED Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 결선도 엔진(그리기·배선기·배치기)이 DIP-16 칩(74HC42)과 출력 0 에서 켜지는 LED 사슬을 다루게 하고, 실험05 1-2 시험판이 `place_search` → `verify()` 와 진리표 시뮬레이션을 통과하게 한다.

**Architecture:** 칩 모델 표 `DIP_PINS`(이름 → 핀 수) 하나에서 핀 수를 얻는다. 핀 기하 `_dip_pin_row/_dip_side` 는 `n=14` 기본 인자로 넓혀 DIP-14 결과를 바이트 단위로 지킨다. 그린 칩의 핀 수는 칩 레코드의 `len(pins)` 로 읽는다 — 레코드에 키를 더하면 `wiring()` 을 거쳐 v1 도장이 깨진다. Negative 사슬은 `led_chain(…, active_low=True)` 갈래로, 레일 점퍼 행(윗행+3)이 보통 사슬과 같아 배치기 LED 행 계산은 바꾸지 않는다.

**Tech Stack:** Python 표준 라이브러리 + Pillow(엔진 기존), unittest/pytest(xdist `-n auto --dist loadgroup`, 단위만 볼 때 `-n0`).

**Spec:** `docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md`

## Global Constraints

- v1 승인본(실험01~04) 그림·도장 불변 — `tests/test_breadboard_boards.py` `CommittedPngs` 가 지킨다.
- e4 시험판 λ=0 스냅숏 `tests/fixtures/board_v2_e4/plans_lambda0.json` 불변 — `tests/test_breadboard_route.py` 가 지킨다. e4 `배치탐색.md` 지문(`place_hash`) 불변.
- 칩 레코드(`bb.chips` 원소)에 키를 더하지 않는다. LED 사슬 레코드에는 Negative 일 때만 `'active_low': True` 를 더한다 — 둘 다 `wiring()` 으로 도장에 든다.
- 표준 라이브러리 + Pillow 만. 저장소 언어는 한국어(주석·docstring·오류·시험 이름).
- 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. main 에 직접 커밋하지 않는다 — 워크트리 `.claude/worktrees/e5-dip16`, 브랜치 `e5-dip16`.
- 범위: 74HC42(1-2)만 시뮬레이터에 넣는다. 74HC148·74HC08 은 넣지 않는다(`EXPERIMENT_SCOPE[5] = ("1-2", "2-2")`).
- 1-2 LED 위→아래 순서: `Y0, Y1, Y2, Y3, Y4, Y5, Y9, Y6, Y8, Y7`(사용자 #13).
- Negative LED 표기: 꼬리표는 신호 이름만, 순서표 사슬 줄에 `0 이면 켜짐`, 보드 아래 note `Y0~Y9 LED 는 출력 0 에서 켜진다(Negative Logic).`(사용자 #14).
- DIP-16 칩 이름 글자 상자 높이 ≤ `2·row_pitch − 4`(v2 = 34px). DIP-14 는 `font_chip`(11pt) 그대로.
- 합격 기준: 전체 스위트에서 메모리 `lab-harness-test-env` 의 알려진 실패(`test_lab_config`(서브시험 10) · `test_lab_html2pdf` 2 · `test_merge_report` 2 · `test_lab_figure_export` 1 · 가끔 `test_trace_guide` 실험04) 밖 실패 0. `test_lab_isolate` 는 부하 중 깜빡이니 실패하면 따로 다시 돈다.
- 느린 시험(`test_breadboard_boards`·`test_breadboard_route`·`test_breadboard_v2_e4_trial`·`test_breadboard_place`·새 `test_breadboard_v2_e5_trial`, 전체 스위트 5~6분)은 배경으로 돌린다.

## Review Focus

1. **모르는 칩 이름이 그리기에 들어온다** — v1 빌더 호환으로 14핀으로 그린다(배치기만 `ValueError`). Task 1 `test_칩_모델_표`, Task 2 `test_모르는_이름은_14핀으로_그린다`.
2. **빌더가 `draw_chip` 보다 `connect_power` 를 먼저 부른다** — 핀 수를 모르니 14핀으로 보되 `[WARN]` 을 stderr 에 낸다(16핀 칩이면 pin 7 출력을 GND 에 묶는 그림이 조용히 나간다). Task 2 `test_칩보다_전원을_먼저_부르면_경고`.
3. **한 슬롯에 14핀·16핀 칩이 회로마다 섞인다** — 슬롯 높이는 8, 레일 빈 행 검사는 k+6·k+7 둘 다. Task 3 `test_섞인_슬롯은_두_GND_행을_다_본다`.
4. **Negative 사슬이 기준선에 그대로 있다(단계 그림 다음 장)** — 회색, 번호 없음, `kept` 에 남는다. 열쇠가 극성 따라 어긋나면 매 단계 새로 꽂으라고 나온다. Task 5 `test_기준선의_Negative_사슬은_그대로`.
5. **진리표 순서와 다른 LED 순서** — 배치기가 태그 순서(`PlaceCircuit.leds`)를 그대로 위→아래로 놓는다. Task 4 `test_LED_는_핀_행_순서로_위에서_아래`.

---

## 파일

- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py`
  - 칩 모델 표·핀 기하(`_dip_pin_row` 근처 ~2604)
  - 그리기(`draw_chip` ~1394, `connect_power` ~1486, `connect_unused_inputs` ~1522, `led_chain` ~1314)
  - 칩 기하 조회(`side_leads` ~1698, `chip_side_of` ~1719, `_chip_bodies` ~1768)
  - 배선기(`_end_holes` ~2624, `_coster` ~2694, `_routes` ~2806)
  - 배치기(`DIP14` ~3041 ~ `place_plan` ~3361)
- Modify: `tests/_gate_sim.py` — 출력별 함수, 74HC42, `led_on`.
- Create: `tests/test_breadboard_dip16.py` — DIP-16·Negative 사슬 단위 시험.
- Create: `tests/fixtures/board_v2_e5/배치.py`, `tests/fixtures/board_v2_e5/배치탐색.md`(도구가 쓴다) — 1-2 시험판.
- Create: `tests/test_breadboard_v2_e5_trial.py` — 시험판 규약·읽기 규칙·진리표.
- Modify: `tests/test_breadboard_place.py`(모르는 칩 시험, DIP-16 배치 시험, `PlaceEnforced` 에 e5), `tests/test_gate_sim.py`, `tests/test_skill_docs.py`.
- Modify: `.claude/skills/breadboard-diagram/SKILL.md`(§2b, v2 배치 규약), `.claude/skills/draft-lab-spec/SKILL.md`(v2 자리표 규약 ~541).
- Modify: 설계 문서 끝에 "실행 결과" 절(Task 8).

## 시작 전 (워크트리·원장)

- [ ] **1. 워크트리를 만든다**

```bash
git worktree add .claude/worktrees/e5-dip16 -b e5-dip16 main
```

- [ ] **2. 설계·계획 문서를 워크트리로 옮겨 첫 커밋으로 남긴다** (main 작업 트리에는 커밋하지 않은 채로 있다)

```bash
mv docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md docs/plans/2026-10-05-실험05-DIP16-negative-LED-구현계획.md .claude/worktrees/e5-dip16/docs/plans/
cd .claude/worktrees/e5-dip16
git add docs/plans/2026-10-05-실험05-DIP16-negative-LED-*.md
git commit -m "docs(plans): 실험05 DIP-16·Negative Logic LED 설계·구현계획

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **3. 원장** `.superpowers/sdd/2026-10-05-실험05-dip16/progress.md` 를 만들고 Task 1~8 을 줄로 적는다(지난번 원장 꼴). 이후 모든 명령은 워크트리 루트에서 돈다.

---

### Task 1: 칩 모델 표와 핀 기하

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` (`_dip_pin_row`·`_dip_side` ~2604, `DIP14` ~3041, `place_check` ~3076)
- Create: `tests/test_breadboard_dip16.py`
- Modify: `tests/test_breadboard_place.py` (`Model.test_14핀이_아니면_멈춘다`)

**Interfaces:**
- Produces:
  - `DIP_PINS: dict[str, int]`
  - `dip_pins(model: str, strict: bool = False) -> int` — 모르면 strict 에서 `ValueError`(메시지에 `DIP_PINS`), 아니면 14.
  - `_dip_pin_row(k: int, pin: int, n: int = 14) -> int`
  - `_dip_side(pin: int, n: int = 14) -> 'a' | 'f'`
  - `place_check` 는 `DIP_PINS` 밖 모델에서 `ValueError`(메시지에 `DIP_PINS`).

- [ ] **Step 1: 실패하는 시험을 쓴다** — `tests/test_breadboard_dip16.py` 를 만든다.

```python
"""DIP-16 칩과 Negative Logic LED — 그리기·배선기 단위 시험.

설계: docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md
배치기 시험은 `test_breadboard_place.py` 의 `Dip16Place`, 시험판은 `test_breadboard_v2_e5_trial.py`.
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _board(mod, **kw):
    bb = mod.BreadboardRenderer(None, board='v2', **kw)
    bb.enable_steps()
    return bb


class PinGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_DIP14_는_그대로(self):
        rows = [self.mod._dip_pin_row(10, p) for p in range(1, 15)]
        self.assertEqual(rows, [10, 11, 12, 13, 14, 15, 16, 16, 15, 14, 13, 12, 11, 10])
        self.assertEqual([self.mod._dip_side(p) for p in (7, 8)], ['a', 'f'])

    def test_DIP16_핀_행과_쪽(self):
        rows = [self.mod._dip_pin_row(10, p, 16) for p in range(1, 17)]
        self.assertEqual(rows, [10, 11, 12, 13, 14, 15, 16, 17, 17, 16, 15, 14, 13, 12, 11, 10])
        self.assertEqual([self.mod._dip_side(p, 16) for p in (8, 9)], ['a', 'f'])

    def test_칩_모델_표(self):
        self.assertEqual(self.mod.dip_pins('74HC42'), 16)
        self.assertEqual(self.mod.dip_pins('74HC08'), 14)
        self.assertEqual(self.mod.dip_pins('74HC9999'), 14)       # 그리기는 v1 호환으로 14
        with self.assertRaisesRegex(ValueError, 'DIP_PINS'):
            self.mod.dip_pins('74HC9999', strict=True)


if __name__ == '__main__':
    unittest.main()
```

`tests/test_breadboard_place.py` 의 `Model.test_14핀이_아니면_멈춘다` 를 아래 둘로 바꾼다.

```python
    def test_모르는_칩이면_멈춘다(self):
        c = _toy(self.mod, [], models={'U1': '74HC04', 'U2': '74HC4511'})
        with self.assertRaisesRegex(ValueError, 'DIP_PINS'):
            self.mod.place_check(c)

    def test_16핀_칩은_받는다(self):
        self.mod.place_check(_toy(self.mod, [], models={'U1': '74HC42', 'U2': '74HC08'}))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py "tests/test_breadboard_place.py::Model" -n0 -q`
Expected: `PinGeometry` 3건 FAIL(`_dip_pin_row()` 가 인자 3개를 안 받음, `dip_pins` 없음). `test_모르는_칩이면_멈춘다` FAIL(메시지가 '14핀'). `test_16핀_칩은_받는다` FAIL(ValueError).

- [ ] **Step 3: 구현한다**

`_dip_pin_row`·`_dip_side`(~2604)를 아래로 바꾼다. 표는 그 바로 위에 둔다.

```python
# 칩 모델 표 — 이름 → DIP 핀 수. VCC 는 마지막 핀, GND 는 n/2 핀(74HC DIP 공통)이라 식으로 얻는다.
# 배치기는 여기 없는 칩을 거절한다(`place_check`). 그리기(`draw_chip`)는 v1 빌더 호환으로 14핀으로 본다.
DIP_PINS = {
    '74HC00': 14, '74HC02': 14, '74HC04': 14, '74HC08': 14, '74HC10': 14, '74HC11': 14,
    '74HC20': 14, '74HC21': 14, '74HC27': 14, '74HC32': 14, '74HC74': 14, '74HC86': 14,
    '74HC42': 16, '74HC138': 16, '74HC148': 16,
}


def dip_pins(model, strict=False):
    """칩 이름 → 핀 수. 모르면 `strict` 에서 ValueError, 아니면 14."""
    n = DIP_PINS.get(model)
    if n is None:
        if strict:
            raise ValueError(f'모르는 칩 {model!r} — 칩 모델 표 `DIP_PINS` 에 핀 수를 올린다')
        return 14
    return n


def _dip_pin_row(k, pin, n=14):
    """칩 pin 1 행 `k` 에서 DIP-`n` 핀 `pin` 이 앉는 행."""
    return k + pin - 1 if pin <= n // 2 else k + n - pin


def _dip_side(pin, n=14):
    return 'a' if pin <= n // 2 else 'f'
```

배치기 머리(~3040)의 `DIP14` 주석·정의를 지운다(아래 두 줄 주석 포함).

```python
# 배선기가 아는 칩 — `_dip_pin_row` 가 DIP-14 를 가정한다. 16핀(74HC138 따위)·7-segment 는 배선기부터 넓힌다
DIP14 = frozenset({...})
```

`PlaceCircuit` docstring 의 "`models` 칩 → 모델(`DIP14`)" 을 "`models` 칩 → 모델(`DIP_PINS` 의 이름)" 으로 고친다. `place_check` 의 첫 세 줄을 바꾼다.

```python
    bad = sorted({m for m in circuit.models.values() if m not in DIP_PINS})
    if bad:
        raise ValueError(f'{circuit.name}: 배치기는 칩 모델 표(`DIP_PINS`)에 있는 칩만 놓는다 — {bad}')
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py "tests/test_breadboard_place.py::Model" -n0 -q`
Expected: PASS. 이어서 `grep -n "DIP14" .claude/skills/breadboard-diagram/scripts/render_breadboard.py tests/*.py` 가 아무것도 안 낸다.

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py tests/test_breadboard_dip16.py tests/test_breadboard_place.py
git commit -m "feat(breadboard): 칩 모델 표 DIP_PINS 와 핀 수를 받는 핀 기하

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: DIP-16 그리기 — 몸통·핀 번호·이름 글자·전원·미사용 입력·칩 기하 조회

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` (`draw_chip` ~1394, `connect_power` ~1486, `connect_unused_inputs` ~1522, `side_leads` ~1698, `chip_side_of` ~1719, `_chip_bodies` ~1768)
- Test: `tests/test_breadboard_dip16.py`

**Interfaces:**
- Consumes: `dip_pins(name)` (Task 1).
- Produces:
  - `BreadboardRenderer._pins_at(block: str, start_row: int) -> int` — 그 자리에 그린 칩의 `len(pins)`. 없으면 `[WARN]` 을 stderr 에 내고 14.
  - `BreadboardRenderer._chip_font(name: str, rows: int)` — 칩 이름 글꼴.
  - 칩 레코드 `pins` 가 16개(DIP-16)일 수 있다. 행 수는 늘 `len(ch['pins']) // 2` 로 읽는다.

- [ ] **Step 1: 실패하는 시험을 쓴다** — `tests/test_breadboard_dip16.py` 에 클래스를 더한다(`if __name__` 위).

```python
import contextlib
import io


class DrawDip16(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.bb = _board(cls.mod)
        cls.bb.draw_chip('74HC42', 10)
        cls.bb.connect_power(10, gnd_col='a')
        cls.L = cls.bb.cols['left']

    def half(self, r):
        """행 r 과 r+1 사이 반 행의 y."""
        return (self.bb.r_y(r) + self.bb.r_y(r + 1)) / 2

    def test_핀_16개가_e_f_열_8행에(self):
        ch = self.bb.chips[-1]
        self.assertEqual(sorted(ch['pins']), list(range(1, 17)))
        self.assertEqual(ch['pins'][8], self.bb.sym(self.L['e'], 17))
        self.assertEqual(ch['pins'][9], self.bb.sym(self.L['f'], 17))
        self.assertEqual(ch['pins'][16], self.bb.sym(self.L['f'], 10))
        self.assertEqual(set(ch), {'label', 'block', 'pin1_row', 'pins'})   # wiring() → 도장

    def test_몸통은_pin_1_행부터_pin_8_행까지(self):
        (box, _x, _ch), = self.bb._chip_bodies()
        self.assertEqual(box[1], self.bb.r_y(10) - 10)
        self.assertEqual(box[3], self.bb.r_y(17) + 10)

    def test_이름_상자는_가운데_반_행_하나만_막는다(self):
        """74HC42 는 a쪽 출력 일곱이 다 LED 로 건넌다 — 건널 반 행 9개 중 이름이 하나만 막아야
        핀마다 하나씩 남는다(설계 #5)."""
        (box, _ch), = self.bb.chip_label_boxes
        self.assertLessEqual(box[3] - box[1], 2 * self.bb.spec.row_pitch - 4)
        xa, xb = self.L['d'], self.L['g']
        free = [r for r in range(9, 17)
                if not self.bb._seg_in_box((xa, self.half(r)), (xb, self.half(r)), box)]
        self.assertEqual(free, [9, 10, 11, 12, 14, 15, 16])

    def test_DIP14_이름_글꼴은_그대로(self):
        bb = _board(self.mod)
        bb.draw_chip('74HC20', 10)
        (box, _ch), = bb.chip_label_boxes
        lb = bb.font_chip.getbbox('74HC20')
        self.assertAlmostEqual(box[3] - box[1], lb[2] - lb[0] + 4)

    def test_모르는_이름은_14핀으로_그린다(self):
        bb = _board(self.mod)
        bb.draw_chip('74HCXX', 10)
        self.assertEqual(len(bb.chips[-1]['pins']), 14)

    def test_전원은_pin_16_과_pin_8(self):
        segs = {d: pts for _k, pts, d in self.bb._segments}
        vcc, gnd = segs['pin 16 -> +5V 레일'], segs['pin 8 -> GND 레일']
        self.assertEqual(vcc[0], (self.L['g'], self.bb.r_y(10)))
        self.assertEqual(vcc[-1][0], self.L['mid_vcc'])
        self.assertEqual(gnd[0], (self.L['a'], self.bb.r_y(17)))
        self.assertEqual(gnd[-1][0], self.L['gnd'])

    def test_칩보다_전원을_먼저_부르면_경고(self):
        bb = _board(self.mod)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            bb.connect_power(10)
        self.assertIn('[WARN]', err.getvalue())
        self.assertIn('pin 14 -> +5V 레일', [d for _k, _p, d in bb._segments])

    def test_미사용_입력_행은_16핀_기준(self):
        bb = _board(self.mod)
        bb.draw_chip('74HC42', 10)
        bb.connect_unused_inputs([13], 10, chip='74HC42', bridge_row=30)    # pin 13 = 행 13, f쪽
        (pts,) = [pts for _k, pts, d in bb._segments if 'pin 13' in d]
        self.assertEqual(pts[0], (bb.cols['left']['g'], bb.r_y(13)))

    def test_칩_쪽_판정과_리드_수는_8행까지(self):
        end = ('hole', self.bb.sym(self.L['b'], 17))
        self.assertEqual(self.bb.chip_side_of(end)['side'], 'a')
        a_side = next(s for s in self.bb.side_leads() if s['side'] == 'a')
        self.assertIn(self.bb.addr(self.L['a'], self.bb.r_y(17)), a_side['addrs'])   # pin 8 GND 점퍼
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py::DrawDip16 -n0 -q`
Expected: FAIL. 핀이 14개이고, 몸통이 행 16 까지이며, `pin 14 -> +5V 레일` 이 나오고, 경고가 없다.

- [ ] **Step 3: `draw_chip` 을 고친다**

`draw_chip` 첫 다섯 줄(`c = …` ~ `y_bot = …`)을 바꾼다.

```python
    def draw_chip(self, name, start_row, block='left'):
        c = self.cols[block]
        n = dip_pins(name)
        rows = n // 2
        x1, x2 = c['chip_x1'], c['chip_x2']
        y_top = self.r_y(start_row) - 8
        y_bot = self.r_y(start_row + rows - 1) + 8
```

이름 글자 네 줄(`self._vtext(label_at, name, text_fill, self.font_chip)` ~ `lb = self.font_chip.getbbox(name)`)을 바꾼다.

```python
        font = self._chip_font(name, rows)
        self._vtext(label_at, name, text_fill, font)
        # 세로로 돌린 이름 글자가 차지하는 상자(논리 좌표, `_vtext` 의 여백 2 포함) — R14
        lb = font.getbbox(name)
```

핀 루프 둘을 바꾼다(`range(7)` → `range(rows)`, `14 - i` → `n - i`).

```python
        for i in range(rows):
            y = self.r_y(start_row + i)
            self.draw.line([(c['e'], y), (x1, y)], fill=(170, 170, 170, 255), width=3)
            self.draw.line([(x2, y), (c['f'], y)], fill=(170, 170, 170, 255), width=3)
            self.draw.text((x1 + 3, y - 6), str(i + 1), fill=num_fill, font=self.font_num)
            rt = str(n - i)
            w = self.draw.textbbox((0, 0), rt, font=self.font_num)[2]
            self.draw.text((x2 - 3 - w, y - 6), rt, fill=num_fill, font=self.font_num)
            self.lead(c['e'], y, f'{name} pin {i + 1}')
            self.lead(c['f'], y, f'{name} pin {n - i}')

        pins = {}
        for i in range(rows):
            pins[i + 1] = self.sym(c['e'], start_row + i)
            pins[n - i] = self.sym(c['f'], start_row + i)
```

`_vtext` 바로 아래에 `_chip_font` 를 더한다.

```python
    def _chip_font(self, name, rows):
        """칩 이름 글꼴. DIP-14 는 늘 `font_chip`(11pt). DIP-16 은 세로 글자 상자가 `2·pitch − 4` 이하인
        가장 큰 크기다 — 몸통 가운데 반 행(k+3.5) 하나만 막아 a쪽 pin 1~7 이 그 위·아래 반 행 일곱으로
        건넌다. 74HC42 는 출력 일곱이 a쪽이다. 11pt(44px)면 반 행 셋을 막아 Y3·Y4 가 못 건넌다(2026-10-05 설계 #5)."""
        if rows == 7:
            return self.font_chip
        limit = 2 * self.spec.row_pitch - 4
        for size in range(11, 5, -1):
            f = _font('en', size)
            b = f.getbbox(name)
            if b[2] - b[0] + 4 <= limit:
                return f
        return _font('en', 6)
```

- [ ] **Step 4: 전원·미사용 입력을 고친다**

`nearest_vcc_rail` 아래에 `_pins_at` 을 더한다.

```python
    def _pins_at(self, block, start_row):
        """그 자리에 그린 칩의 핀 수. 칩 레코드에 키를 더하지 않고 `pins` 개수로 읽는다 — 레코드는
        `wiring()` 으로 도장에 든다. 아직 안 그렸으면 14 로 보고 경고한다(v1 빌더는 전부 14핀이다. 16핀 칩을
        그리기 전에 전원을 부르면 pin 7 출력을 GND 에 묶는 그림이 조용히 나간다)."""
        for ch in self.chips:
            if ch['block'] == block and ch['pin1_row'] == start_row:
                return len(ch['pins'])
        print(f'[WARN] {block} {start_row}행에 그린 칩이 없다 — 14핀으로 본다. draw_chip 을 먼저 부른다',
              file=sys.stderr)
        return 14
```

`connect_power` docstring 첫 줄을 `"""pin 14(DIP-16 은 16) -> +5V, pin 7(DIP-16 은 8) -> GND. …` 로 고치고 본문을 바꾼다.

```python
        c = self.cols[block]
        n = self._pins_at(block, start_row)
        g = start_row + n // 2 - 1          # GND 핀 행 — DIP-14 pin 7 은 k+6, DIP-16 pin 8 은 k+7
        x_vcc = c['mid_vcc'] if block == 'left' else c['vcc']
        x_gnd = c['gnd'] if block == 'left' else c['mid_gnd']
        r14 = self.free_rail_row(start_row, x_vcc)
        self.step_wire([(c['g'], self.r_y(start_row)), (x_vcc, self.r_y(r14))],
                       'vcc', f'pin {n} -> +5V 레일',
                       marker_near=((c['g'] + x_vcc) // 2, self.r_y(start_row) - 11))
        r7 = self.free_rail_row(g, x_gnd)
        self.step_wire([(c[gnd_col], self.r_y(g)), (x_gnd, self.r_y(r7))],
                       'gnd', f'pin {n // 2} -> GND 레일', marker_at=gnd_marker_at,
                       marker_near=((c['d'] + x_gnd) // 2, self.r_y(g) - 11))
```

`connect_unused_inputs` 의 핀 → 행 계산과 브리지 조건을 바꾼다.

```python
        c = self.cols[block]
        n = self._pins_at(block, start_row)
        h = n // 2
        placed = []
        for p in pins:
            if 1 <= p <= h:
                placed.append((start_row + (p - 1), c[col], p))
            elif h < p <= n:
                placed.append((start_row + (n - p), c['g'], p))
```

```python
        if rail == 'gnd' and any(h < p <= n for p in pins):
```

- [ ] **Step 5: 칩 기하 조회 셋을 고친다**

`side_leads`:

```python
            rows = range(ch['pin1_row'], ch['pin1_row'] + len(ch['pins']) // 2)
```

`chip_side_of`(docstring 의 `pin1_row~+6` 도 `pin1_row ~ pin1_row+행수−1` 로):

```python
            if ch['block'] == blk and ch['pin1_row'] <= row <= ch['pin1_row'] + len(ch['pins']) // 2 - 1:
```

`_chip_bodies`(docstring "pin 7 행 아래" → "마지막 a쪽 핀 행 아래"):

```python
            box = (c['chip_x1'] - 1, self.r_y(ch['pin1_row']) - 10,
                   c['chip_x2'] + 1, self.r_y(ch['pin1_row'] + len(ch['pins']) // 2 - 1) + 10)
```

- [ ] **Step 6: 통과를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py -n0 -q`
Expected: PASS.

- [ ] **Step 7: v1·v2 회귀를 배경으로 돈다**

Run: `python -m pytest tests/test_breadboard_boards.py tests/test_breadboard_v2.py tests/test_breadboard_readability.py tests/test_breadboard_physical.py tests/test_breadboard_sidecar.py tests/test_breadboard_baseline.py tests/test_breadboard_wiring.py -q`
Expected: PASS(`CommittedPngs` 도장 전부 그대로). 실패하면 DIP-14 경로에서 문자열·좌표·호출 순서가 바뀐 곳을 찾는다 — 도장이 바뀌는 수정은 하지 않는다.

- [ ] **Step 8: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py tests/test_breadboard_dip16.py
git commit -m "feat(breadboard): DIP-16 칩을 그린다 — 8행 몸통·pin 16/8 전원·이름 글자는 반 행 하나만 막는다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 배선기·배치기의 DIP-16

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` (`_end_holes` ~2624, `_coster` ~2694, `_routes` ~2806, `place_wire_cost` ~3118, `mid_rail_rows` ~3144, `bridge_rows` ~3155, `led_rows` ~3166, `place_r10_ok` ~3206, `slot_candidates` ~3224, `place_proxy` ~3243, `place_plan` ~3361)
- Test: `tests/test_breadboard_dip16.py`, `tests/test_breadboard_place.py`

**Interfaces:**
- Consumes: `dip_pins`, `_dip_pin_row(k, pin, n)`, `_dip_side(pin, n)` (Task 1). 칩 레코드 `len(pins)` (Task 2).
- Produces:
  - `_chip_pins(bb) -> dict[int, int]` — 좌 블록 pin 1 행 → 핀 수.
  - `circuit_pins(circuit) -> dict[str, int]` — 칩 → 핀 수(strict).
  - `slot_rows(circuits, slots) -> dict[str, set[int]]` — 슬롯 → 그 슬롯에 앉는 칩들의 행 수 집합. 아무 칩도 없으면 `{7}`.
  - `place_wire_cost(chips, wire, pins=None)`
  - `slot_candidates(slots, gmin=…, gmax=…, starts=…, rows=None)`
  - `bridge_rows(slots, rows=None)`
  - `mid_rail_rows`·`led_rows`·`place_r10_ok`·`place_proxy` 의 서명은 그대로다(안에서 `circuit_pins` 를 쓴다).

- [ ] **Step 1: 배선기 시험을 쓴다** — `tests/test_breadboard_dip16.py` 에 더한다.

```python
class RouterDip16(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_끝_홀은_16핀_기하(self):
        bb = _board(self.mod)
        bb.draw_chip('74HC42', 10)
        L = bb.cols['left']
        self.assertEqual(self.mod._end_holes(bb, {'U1': 10}, ('U1', 9)),
                         [(L[c], bb.r_y(17)) for c in 'ghij'])
        self.assertEqual(self.mod._end_holes(bb, {'U1': 10}, ('U1', 8)),
                         [(L[c], bb.r_y(17)) for c in 'abcd'])

    def test_a쪽_가운데_아래_핀은_아래_반_행으로_건넌다(self):
        """pin 5(행 14)의 위 반 행 13.5 는 이름 상자가 막는다 — 아래 14.5 로 건너야 한다."""
        def fixed(bb, stage, superset=False):
            bb.draw_chip('74HC42', 10)
            bb.led_chain(bb.cols['right']['a'], 21, 'Y4', '시험', block='right')

        (path, _m), = self.mod.route_plan(fixed, {'U1': 10},
                                          [(1, None, 'sig', ('U1', 5), ('LED', 21), 'Y4')])
        bb = _board(self.mod)
        self.assertEqual(path[1][1], (bb.r_y(14) + bb.r_y(15)) / 2)
```

`tests/test_breadboard_place.py` 끝(`if __name__` 위)에 더한다.

```python
class Dip16Place(unittest.TestCase):
    """배치기의 DIP-16 — 슬롯 높이·레일 빈 행·브리지·핀 기하(설계 #6)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _one(self, model, wires=(), leds=(), inputs=()):
        return self.mod.PlaceCircuit('d', {'U1': 'K1'}, {'U1': model}, tuple(leds), tuple(wires),
                                     lambda bb, stage, superset, layout: None, tuple(inputs))

    def test_슬롯_행_수는_그_슬롯의_칩들(self):
        a = _toy(self.mod, [], models={'U1': '74HC42', 'U2': '74HC08'})
        b = self.mod.PlaceCircuit('b', {'U9': 'K1'}, {'U9': '74HC04'}, (), (),
                                  lambda bb, stage, superset, layout: None)
        self.assertEqual(self.mod.slot_rows([a, b], ('K1', 'K2', 'K3')),
                         {'K1': {7, 8}, 'K2': {7}, 'K3': {7}})

    def test_섞인_슬롯은_두_GND_행을_다_본다(self):
        # 3..8 중 k·k+6·k+7 이 레일 빈 행(8·14)이 아닌 것. 7 은 k+7 = 14, 8 은 k = 8
        ks = [c['K1'] for c in self.mod.slot_candidates(('K1',), rows={'K1': {7, 8}})]
        self.assertEqual(ks, [3, 4, 5, 6])
        self.assertIn(7, [c['K1'] for c in self.mod.slot_candidates(('K1',))])   # 14핀이면 7 도 된다

    def test_16핀_간격은_8행_더하기_빈_행(self):
        for c in self.mod.slot_candidates(('K1', 'K2'), rows={'K1': {8}, 'K2': {7}}):
            if c['K1'] < c['K2']:
                self.assertTrue(8 + 3 <= c['K2'] - c['K1'] <= 8 + 6, c)
            else:
                self.assertTrue(7 + 3 <= c['K1'] - c['K2'] <= 7 + 6, c)

    def test_브리지는_16핀_마지막_행_아래(self):
        self.assertEqual(self.mod.bridge_rows({'K1': 36}, {'K1': {8}}), [46, 47])   # 36+7+3
        self.assertEqual(self.mod.bridge_rows({'K1': 36}), [45, 46])                # 36+6+3

    def test_비용은_16핀_기하(self):
        f = self.mod.place_wire_cost({'U1': 10}, _w(('U1', 9), ('LED', 17)), {'U1': 16})   # 행 17, f쪽
        a = self.mod.place_wire_cost({'U1': 10}, _w(('U1', 8), ('LED', 17)), {'U1': 16})   # 행 17, a쪽
        self.assertGreaterEqual(a - f, 400)

    def test_가운데_레일_입력_행은_16핀_기하(self):
        c = self._one('74HC42', inputs=[('U1', 15), ('U1', 12)])    # 행 4, 7
        self.assertEqual(self.mod.mid_rail_rows(c, {'K1': 3}, [15, 16]), {3, 4, 7, 15, 16})

    def test_R10_은_16핀_행으로(self):
        w9, w11 = _w(('U1', 9), ('LED', 'L1')), _w(('U1', 11), ('LED', 'L2'))   # 행 k+7, k+5
        bad = self._one('74HC42', [w9, w11], leds=('L1', 'L2'))
        self.assertFalse(self.mod.place_r10_ok(bad, {'U1': 3}, {'L1': 10, 'L2': 20}))
        good = self._one('74HC42', [w11, w9], leds=('L2', 'L1'))
        self.assertTrue(self.mod.place_r10_ok(good, {'U1': 3}, {'L2': 10, 'L1': 20}))

    def test_근사는_16핀_슬롯의_브리지를_쓴다(self):
        c = self._one('74HC42', [_w(('U1', 9), ('LED', 'L1'))], leds=('L1',))
        _cost, lay = self.mod.place_proxy([c], {'K1': 3})
        self.assertEqual(lay['bridge'], self.mod.bridge_rows({'K1': 3}, {'K1': {8}}))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py::RouterDip16 "tests/test_breadboard_place.py::Dip16Place" -n0 -q`
Expected: FAIL. 끝 홀이 행 16 이고, `slot_rows` 가 없고, `rows=` 와 `pins` 인자를 안 받는다.

- [ ] **Step 3: 배선기를 고친다**

`_end_holes` 위에 `_chip_pins` 를 두고 본문 끝 세 줄을 바꾼다.

```python
def _chip_pins(bb):
    """좌 블록 칩 pin 1 행 → 핀 수. 칩마다 행이 달라 행 하나로 칩이 정해진다. 칩 레코드에 키를 더하지
    않고 `pins` 개수로 읽는다(`wiring()` → 도장)."""
    return {ch['pin1_row']: len(ch['pins']) for ch in bb.chips if ch['block'] == 'left'}
```

```python
    k, pin = chips[end[0]], end[1]
    n = _chip_pins(bb).get(k, 14)
    row = _dip_pin_row(k, pin, n)
    return [(L[c], bb.r_y(row)) for c in _STRIP_COLS[_dip_side(pin, n)]
            if (L[c], row) not in bb._leads and (L[c], row) not in bb._passed]
```

`_coster` 의 `bodies`:

```python
    bodies = [(bb.r_y(ch['pin1_row']) - 10, bb.r_y(ch['pin1_row'] + len(ch['pins']) // 2 - 1) + 10)
              for ch in bb.chips]
```

`_routes` 의 캐시 열쇠(몸통 높이가 비용에 들어가니 핀 수도 열쇠에 넣는다):

```python
    chip_rows = tuple((ch['pin1_row'], len(ch['pins'])) for ch in bb.chips)
```

- [ ] **Step 4: 배치기를 고친다**

`place_check` 아래에 둘을 더한다.

```python
def circuit_pins(circuit):
    """칩 → 핀 수. `place_check` 를 지난 회로만 — 모르는 칩은 ValueError."""
    return {chip: dip_pins(m, strict=True) for chip, m in circuit.models.items()}


def slot_rows(circuits, slots):
    """슬롯 → 그 슬롯에 앉는 칩들의 행 수 집합(14핀 7, 16핀 8). 슬롯 높이는 최댓값이고, 레일 빈 행
    검사는 모든 GND 핀 행(k+행수−1)에 한다 — 회로마다 같은 슬롯에 14핀·16핀이 앉을 수 있다. 칩이
    없는 슬롯은 {7}."""
    out = {s: set() for s in slots}
    for c in circuits:
        for chip, s in c.chips.items():
            out[s].add(dip_pins(c.models[chip], strict=True) // 2)
    return {s: (v or {7}) for s, v in out.items()}
```

`place_wire_cost` 서명과 `holes`:

```python
def place_wire_cost(chips, wire, pins=None):
    """…(기존 docstring)… `pins` 는 칩 → 핀 수(없으면 14)."""
    L, R, pitch = _place_geom()
    _s, _e, _k, frm, to, _d = wire
    pins = pins or {}

    def holes(end):
        if end[0] == 'LED':
            return [(R['a'], end[1])], None
        n = pins.get(end[0], 14)
        row = _dip_pin_row(chips[end[0]], end[1], n)
        side = _dip_side(end[1], n)
        return [(L[c], row) for c in _STRIP_COLS[side]], side
```

`mid_rail_rows`:

```python
    used = {slots[s] for s in circuit.chips.values()}
    rows = used | set(bridge)
    pins = circuit_pins(circuit)
    for chip, pin in circuit.inputs:
        if _dip_side(pin, pins[chip]) == 'f':
            rows.add(_dip_pin_row(slots[circuit.chips[chip]], pin, pins[chip]))
    return rows
```

`bridge_rows`(docstring 끝에 "`rows` 는 `slot_rows` — 없으면 모든 슬롯 7행."):

```python
def bridge_rows(slots, rows=None):
    rows = rows or {}
    r = max(k + max(rows.get(s, {7})) - 1 for s, k in slots.items()) + 3
```

(그 아래 `while` 은 그대로.)

`led_rows` 의 `cost` 안 합계(`chips = …` 다음 줄에 `pins = circuit_pins(circuit)` 를 둔다):

```python
        return sum(place_wire_cost(chips, (s, e, k, sub(f), sub(t), d), pins)
                   for s, e, k, f, t, d in mine[tag])
```

`led_rows` docstring 의 "윗행+3(저항 아랫다리 = GND 점퍼 출발 행)" 은 Task 5 에서 고친다.

`place_r10_ok`(`stages = …` 앞에 `pins = circuit_pins(circuit)` 를 둔다):

```python
                    live.append((leds[led[1]], _dip_pin_row(chips[chip[0]], chip[1], pins[chip[0]])))
```

`slot_candidates`(docstring 에 "`rows` 는 `slot_rows` — 칩 사이 간격은 위 칩 높이 + g, 레일 빈 행 검사는 k 와 그 슬롯의 모든 GND 행." 을 더한다):

```python
def slot_candidates(slots, gmin=PLACE_GMIN, gmax=PLACE_GMAX, starts=PLACE_STARTS, rows=None):
    rows = rows or {}
    out = []
    for order in itertools.permutations(slots):
        for k0 in starts:
            for gaps in itertools.product(range(gmin, gmax + 1), repeat=len(slots) - 1):
                ks = [k0]
                for s, g in zip(order, gaps):
                    ks.append(ks[-1] + max(rows.get(s, {7})) + g)
                if any(k in RAIL_GAP_ROWS or any(k + r - 1 in RAIL_GAP_ROWS for r in rows.get(s, {7}))
                       for s, k in zip(order, ks)):
                    continue
                cand = dict(zip(order, ks))
                if bridge_rows(cand, rows) is not None:
                    out.append(cand)
    return out
```

`place_proxy`:

```python
    for c in circuits:
        pins = circuit_pins(c)
        if any(_dip_pin_row(slots[c.chips[chip]], pin, pins[chip]) in RAIL_GAP_ROWS for chip, pin in c.inputs):
            return None
    bridge = bridge_rows(slots, slot_rows(circuits, slots))
```

```python
        total += sum(place_wire_cost(chips, w, circuit_pins(c)) for w in place_wires(c, layout))
```

`place_plan` 의 `ranked`:

```python
    rows_ = slot_rows(circuits, slots)
    ranked = sorted((r for r in (place_proxy(circuits, s) for s in slot_candidates(slots, gmin, rows=rows_))
                     if r is not None), key=lambda r: (r[0], layout_key(r[1])))
```

- [ ] **Step 5: 통과를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py "tests/test_breadboard_place.py::Dip16Place" "tests/test_breadboard_place.py::Proxy" "tests/test_breadboard_place.py::LedRows" "tests/test_breadboard_place.py::R10AndCandidates" "tests/test_breadboard_place.py::InputRows" -n0 -q`
Expected: PASS.

- [ ] **Step 6: e4 회귀를 배경으로 돈다** (2~3분)

Run: `python -m pytest tests/test_breadboard_route.py tests/test_breadboard_place.py tests/test_breadboard_v2_e4_trial.py -q`
Expected: PASS — λ=0 스냅숏, `PlaceEnforced`(e4 지문), `PlacedTrial` 그대로.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py tests/test_breadboard_dip16.py tests/test_breadboard_place.py
git commit -m "feat(breadboard): 배선기·배치기가 DIP-16 핀 기하와 슬롯 높이를 안다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 실험05 1-2 시험판 — 배선이 나는가 (보통 사슬로 먼저)

설계 #10: 실현성 위험은 배선이다. 경로는 LED 사슬 극성과 무관하므로(LED 끝점은 둘 다 우 a 윗행) 보통 사슬로 먼저 잰다. Negative 는 Task 5 에서 한 줄로 바꾼다.

**Files:**
- Create: `tests/fixtures/board_v2_e5/배치.py`, `tests/fixtures/board_v2_e5/배치탐색.md`(도구가 쓴다)
- Create: `tests/test_breadboard_v2_e5_trial.py`
- Modify: `tests/test_breadboard_place.py` (`PlaceEnforced`)
- (막힐 때만) Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` `_coster` — Step 5

**Interfaces:**
- Consumes: Task 1~3 전부. `_input_jumper`, `PlaceCircuit`, `place_chips`, `place_paths`, `place_marker_hints`, `draw_routed`, `place_proxy`.
- Produces: 시험판 모듈 속성 `BOARD`, `SLOTS`, `LAYOUT`, `PLACE`, `BCD`, `BOARDS`, `RESTART`, `FINALS`, `build_trial_bcd(output_path, template_path=None, stage=None, baseline=None, layer=None)`, `_LEDS`.

- [ ] **Step 1: 시험판을 쓴다** — `tests/fixtures/board_v2_e5/배치.py`

```python
# 실험05 v2 시험판 — 1-2 BCD → 10진 디코더(74HC42) 하나. DIP-16 칩과 Negative Logic LED 를 엔진이
# 그리는지 잰다. 설계: `docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md`.
#
#   K1 : 74HC42 (U1) — 입력 A·B·C·D = pin 15·14·13·12(f쪽, 가운데 GND 레일에서), 출력 Y0~Y9 =
#        pin 1~7·9~11. 칩 핀은 전부 쓴다(미사용 없음).
#   LED 는 칩 핀 행 순서다(R10, 사용자 #13): Y0 Y1 Y2 Y3 Y4 Y5 Y9 Y6 Y8 Y7. Y7·Y8·Y9 가 pin 9·10·11
#   (행 k+7·k+6·k+5)이라 진리표 순서로 두면 건너는 선이 엇갈린다.
#   a쪽 출력 → LED 선은 칩 이름 상자에 가까운 핀부터 적는다(pin 4, 3, 2, 1, 5, 6, 7) — 이름 상자가
#   반 행 k+3.5 를 막으면 a쪽 일곱 가닥이 건널 반 행이 핀마다 하나로 정해지고, 배선기 수리는 막힌 선
#   앞 한 가닥만 바꿔 본다. 위에서부터 깔면 pin 4 가 막힌다.
#   행은 `LAYOUT` — 배치기(`python -m scripts.lab.place_search tests/fixtures/board_v2_e5/배치.py`)가
#   고른 값을 옮겨 적는다(SKILL §4). 손으로 고치지 않는다 — PlaceEnforced 가 `배치탐색.md` 와 맞댄다.
from render_breadboard import (BreadboardRenderer, _input_jumper, PlaceCircuit, place_chips, place_paths,
                               place_marker_hints, draw_routed, _dip_pin_row)

BOARD = 'v2'
SLOTS = ('K1',)
LAYOUT = {'slots': {'K1': 3}, 'leds': {'bcd': {}}, 'bridge': [15, 16]}   # Step 3 에서 바꾼다

_LEDS = ('Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y9', 'Y6', 'Y8', 'Y7')
_OUT = {'Y0': 1, 'Y1': 2, 'Y2': 3, 'Y3': 4, 'Y4': 5, 'Y5': 6, 'Y6': 7, 'Y7': 9, 'Y8': 10, 'Y9': 11}
# (단계) — 한 단계 새 신호선 셋 이하. 순서 = 그리는 순서 = 경로를 정하는 순서(머리 주석)
_ORDER = (('Y3', 1), ('Y2', 1), ('Y1', 1), ('Y0', 2), ('Y4', 2), ('Y5', 2),
          ('Y6', 3), ('Y9', 3), ('Y8', 3), ('Y7', 4))
_WIRES = [(s, None, 'sig', ('U1', _OUT[t]), ('LED', t), f'{t} = U1 pin {_OUT[t]} -> LED {t}')
          for t, s in _ORDER]
# 입력 점퍼 (단계, 이름, 칩, 핀). A 가 LSB(교안 p9 Bit0).
_INPUTS = [(1, 'A', 'U1', 15), (1, 'B', 'U1', 14), (1, 'C', 'U1', 13), (1, 'D', 'U1', 12)]

_INPUT_NOTE = ('입력은 GND(=0) 에 꽂힌 자리로 그렸다. 1 을 줄 때는 그 점퍼의 레일 쪽 끝만 '
               '빨간 +5V 레일로 옮겨 꽂는다.')


def _fixed(bb, stage, superset=False, layout=None):
    """칩·전원·브리지·LED 사슬 열·입력 점퍼 넷 — 전부 1단계 기반이다."""
    lay = layout or LAYOUT
    L, R = bb.cols['left'], bb.cols['right']
    k = place_chips(BCD, lay)['U1']
    bb.draw_chip('74HC42', k)
    gnd_row, vcc_row = lay['bridge']
    bb.connect_jacks()
    bb.bridge_rails(L['gnd'], L['mid_gnd'], gnd_row, kind='gnd')
    bb.bridge_rails(L['vcc'], L['mid_vcc'], vcc_row, kind='vcc')
    bb.connect_power(k, gnd_col='a')
    for tag in _LEDS:
        bb.led_chain(R['a'], lay['leds']['bcd'][tag], tag, f'{tag} — 진리표 {tag} 열', block='right')
    for _s, name, chip, pin in _INPUTS:
        _input_jumper(bb, L, _dip_pin_row(k, pin, 16), name, f'{chip} pin {pin}', side='f', col='j')


def _draw(bb, stage):
    bb.partial = stage is not None and stage < 4
    bb.marker_hints = place_marker_hints(BCD, LAYOUT)
    _fixed(bb, stage)
    draw_routed(bb, BCD.wires, place_paths(BCD, LAYOUT), stage)
    bb.note(_INPUT_NOTE)


def build_trial_bcd(output_path, template_path=None, stage=None, baseline=None, layer=None):
    """1-2 BCD → 10진 디코더 v2 시험판. `stage` 1..4 또는 None(완성)."""
    bb = BreadboardRenderer(template_path, baseline=baseline, layer=layer, board=BOARD)
    bb.enable_steps()
    bb.set_header('실험05 v2 시험판: BCD → 10진 디코더', '74HC42 · 칩 좌 블록, LED 우 블록')
    _draw(bb, stage)
    bb.export(output_path, max_row=63)
    return bb


BCD = PlaceCircuit('bcd', {'U1': 'K1'}, {'U1': '74HC42'}, _LEDS, tuple(_WIRES), _fixed,
                   tuple((c, p) for _s, _n, c, p in _INPUTS))
PLACE = [BCD]

BOARDS = [(f'trial_e5_bcd_{s}.png', build_trial_bcd, s) for s in (1, 2, 3, 4)]
RESTART = set()
FINALS = [('trial_e5_bcd.png', build_trial_bcd)]
```

- [ ] **Step 2: 시험을 쓴다** — `tests/test_breadboard_v2_e5_trial.py`

```python
"""실험05 v2 시험판 — 1-2 BCD → 10진 디코더(74HC42). DIP-16 칩과 Negative Logic LED 를 엔진이 v2 규약
(R7~R14) 안에서 그리는지 잰다. 설계: docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md
"""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e5/배치.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Trial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e5')
        cls.tmp = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class BcdFinal(_Trial):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bb = cls.board.build_trial_bcd(os.path.join(cls.tmp, 'bcd.png'))

    def test_v2_규약을_지킨다(self):
        self.assertEqual({ch['block'] for ch in self.bb.chips}, {'left'})
        self.assertEqual(self.bb.cross_side_wires(), [])
        self.assertEqual(self.bb._block_role_violations(), [])
        self.assertLessEqual(max(s['count'] for s in self.bb.side_leads()), self.mod.SIDE_LEAD_MAX)

    def test_칩은_16핀이다(self):
        (ch,) = self.bb.chips
        self.assertEqual(len(ch['pins']), 16)

    def test_LED_는_핀_행_순서로_위에서_아래(self):
        tops = self.board.LAYOUT['leds']['bcd']
        self.assertEqual(sorted(tops, key=tops.get), list(self.board._LEDS))
        self.assertEqual(self.board._LEDS, ('Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y9', 'Y6', 'Y8', 'Y7'))


class Readability(_Trial):
    """단계 그림 넷과 완성본이 읽기 규칙 R11~R14 를 지킨다(`verify()` 가 이미 집행하지만 판형 스위치가
    꺼지면 조용히 안 돌기 때문에 직접 본다 — e4 시험판과 같다)."""

    def test_완성본과_단계_그림이_R11_R14_를_지킨다(self):
        bad, base = {}, None
        boards = list(self.board.BOARDS) + [(n, f, 'final') for n, f in self.board.FINALS]
        for name, fn, stage in boards:
            if stage == 'final':
                bb = fn(os.path.join(self.tmp, name))
            else:
                bb = fn(os.path.join(self.tmp, name), None, stage=stage, baseline=base)
                base = bb.snapshot()
            got = (bb.marker_problems() + bb.wires_over_holes() + bb.needless_body_crossings()
                   + bb.wires_over_chip_labels())
            if got:
                bad[name] = got
        self.assertEqual(bad, {}, '\n'.join(f'{k}: {len(v)}건 — {v[:3]}' for k, v in bad.items()))


if __name__ == '__main__':
    unittest.main()
```

`tests/test_breadboard_place.py` `PlaceEnforced` 를 고친다(파일 머리 `TRIAL` 아래에 `TRIAL_E5 = ROOT / 'tests/fixtures/board_v2_e5/배치.py'`).

```python
        for f in sorted(ROOT.glob('보고서/실험*/결선도/배치.py')) + [TRIAL, TRIAL_E5]:
```

```python
        self.assertIn(TRIAL, checked)
        self.assertIn(TRIAL_E5, checked)
```

- [ ] **Step 3: 처음 `LAYOUT` 을 근사로 채운다**

`slot_rows` 로 보면 K1 후보는 k = 3 하나다. k = 4·5·6 은 입력 핀 행에 레일 빈 행 8 이 걸리고, 7·8 은 GND 행이나 k 가 레일 빈 행이다.

```bash
python -c "
import sys; sys.path.insert(0, '.claude/skills/breadboard-diagram/scripts')
import render_breadboard as m
b = m.load_board_file('tests/fixtures/board_v2_e5/배치.py', 'e5')
print([s for s in m.slot_candidates(b.SLOTS, rows=m.slot_rows(b.PLACE, b.SLOTS)) if m.place_proxy(b.PLACE, s)])
print(m.place_proxy(b.PLACE, {'K1': 3})[1])
"
```

Expected: 첫 줄 `[{'K1': 3}]`. 둘째 줄은 layout dict 이다. 둘째 줄 dict 를 그대로 `LAYOUT = …` 자리에 옮기고, `# Step 3 에서 바꾼다` 주석을 지운다.

- [ ] **Step 4: 시험판을 돌린다** (배경, 몇 분)

Run: `python -m pytest tests/test_breadboard_v2_e5_trial.py -q`
Expected: `BcdFinal`·`Readability` PASS.

막히면 첫 사유 줄로 가른다.
- `경로 없음: ('U1', p) -> ('LED', …)` 이고 p 가 1~7 이면 → Step 5(대책)로 간다.
- 그 밖(R11 번호 원, R7 리드 수, R13·R14, `경로 없음` 이 f쪽) → **멈추고 사용자에게 사유를 보고한다.** 손좌표·`marker_at` 으로 맞추지 않는다 — SKILL §4 가 금한다.
  - 미리 아는 위험: 입력 넷(pin 15·14·13·12)이 **이웃한 네 행**에서 가운데 GND 로 들어간다. 그래서 가운데 여백의 입력 배지와 번호 원(배지 위 18px)이 이웃 행 배지와 겹칠 수 있다(`_input_jumper` docstring "가운데 여백은 한 번에 입력 한 행만 받는다"). 이 사유로 막히면 보고할 때 이것이라고 짚는다. 대책(입력 배지를 보드 바깥으로 빼는 엔진 변경 등)은 사용자와 정한다.

- [ ] **Step 5: (Step 4 에서 a쪽이 막혔을 때만) 16핀 a쪽 출력의 안쪽 반 행 벌점**

`tests/test_breadboard_dip16.py` `RouterDip16` 에 시험을 먼저 더한다.

```python
    def test_16핀_a쪽은_몸통_가운데_쪽_반_행이_비싸다(self):
        bb = _board(self.mod)
        bb.draw_chip('74HC42', 10)
        cost = self.mod._coster(bb)
        L, y = bb.cols['left'], bb.r_y(12)                     # pin 3, 가운데(13.5) 위
        up = [(L['d'], y), (L['d'], y - 9.5), (560, y - 9.5)]
        down = [(L['d'], y), (L['d'], y + 9.5), (560, y + 9.5)]
        self.assertGreater(cost(down)[1], cost(up)[1])
```

Run: `python -m pytest "tests/test_breadboard_dip16.py::RouterDip16" -n0 -q` → 새 시험 FAIL(두 비용이 같다).

`_coster` 의 `bodies` 아래에 더한다.

```python
    # DIP-16 a쪽 출력은 건널 반 행이 핀마다 하나다(설계 #5) — 이름 상자 쪽(몸통 가운데 쪽)으로 들어가면
    # 이웃 핀의 반 행을 뺏는다. 14핀 칩은 대상이 아니다(e4 λ=0 스냅숏 불변)
    mids16 = [(bb.r_y(ch['pin1_row']) + bb.r_y(ch['pin1_row'] + 7)) / 2
              for ch in bb.chips if len(ch['pins']) == 16]

    def inward(path):
        if len(path) < 2 or abs(path[0][0] - path[1][0]) > .5:
            return 0
        a, y1 = path[0][1], path[1][1]
        return sum(1 for m in mids16 if abs(a - m) < 4 * pitch and abs(y1 - m) < abs(a - m))
```

`cost` 안 `c = 40 * (len(path) - 2) + 400 * body_crossings(path)` 을 아래로 바꾼다.

```python
        c = 40 * (len(path) - 2) + 400 * body_crossings(path) + 60 * inward(path)
```

Run: `python -m pytest tests/test_breadboard_dip16.py -n0 -q` → PASS. 그다음 Step 4 와 Task 3 Step 6(e4 회귀)을 다시 돈다. 그래도 막히면 멈추고 보고한다.

- [ ] **Step 6: 배치기를 돌려 `배치탐색.md` 를 쓰고 `LAYOUT` 을 맞춘다** (배경)

Run: `python -m scripts.lab.place_search tests/fixtures/board_v2_e5/배치.py`
Expected: `tests/fixtures/board_v2_e5/배치탐색.md` 가 생긴다. 후보가 하나라 기준(지금 `LAYOUT`)이 `✔ 고름` 이다. 보고서 첫 JSON 블록의 `layout` 이 `LAYOUT` 과 다르면 그 값으로 옮긴다.

Run: `python -m pytest "tests/test_breadboard_place.py::PlaceEnforced" tests/test_breadboard_v2_e5_trial.py -q`
Expected: PASS.

- [ ] **Step 7: 커밋**

```bash
git add tests/fixtures/board_v2_e5 tests/test_breadboard_v2_e5_trial.py tests/test_breadboard_place.py
# Step 5 를 했으면: git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py tests/test_breadboard_dip16.py
git commit -m "test(breadboard): 실험05 1-2 v2 시험판 — 74HC42 와 LED 열 벌이 배치·배선·verify 를 통과한다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Negative Logic LED 사슬

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` (`led_chain` ~1314, `led_rows`·`mid_rail_rows` docstring)
- Modify: `tests/fixtures/board_v2_e5/배치.py` (`_fixed`·`_draw`)
- Test: `tests/test_breadboard_dip16.py`

**Interfaces:**
- Produces: `BreadboardRenderer.led_chain(x, top_row, tag, desc, block='left', color_rgb=(220, 20, 20), marker_dx=-21, active_low=False)`. Negative 사슬 레코드 `{'tag', 'signal', 'anode', 'cathode', 'res_top', 'res_bottom', 'active_low': True}`. 열은 `x_led`=신호 옆 열(330Ω), `x_res`=그다음 열(LED)이다. 행은 330Ω 이 top→top+2, LED 캐소드가 top+2, 애노드가 top+3 이다. 레일 점퍼는 kind `'vcc'`, desc `f'{tag} LED 애노드 -> +5V'`. 순서표 사슬 줄 desc 에 `0 이면 켜짐` 이 든다.

- [ ] **Step 1: 실패하는 시험을 쓴다** — `tests/test_breadboard_dip16.py` 에 더한다.

```python
class NegativeLed(unittest.TestCase):
    """출력 0 에서 켜지는 LED(교안 실험5 p9) — 신호 → 330Ω → LED(캐소드 → 애노드) → +5V."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.bb = _board(cls.mod)
        cls.R = cls.bb.cols['right']
        cls.bb.led_chain(cls.R['a'], 10, 'Y0', '시험', block='right', active_low=True)
        cls.ch = cls.bb.led_chains[-1]

    def test_저항이_신호_옆_LED_가_그다음(self):
        s, R = self.bb.sym, self.R
        self.assertEqual(self.ch['signal'], s(R['a'], 10))
        self.assertEqual(self.ch['res_top'], s(R['b'], 10))
        self.assertEqual(self.ch['res_bottom'], s(R['b'], 12))
        self.assertEqual(self.ch['cathode'], s(R['c'], 12))
        self.assertEqual(self.ch['anode'], s(R['c'], 13))
        self.assertIs(self.ch['active_low'], True)

    def test_애노드_줄에서_가운데_VCC_로(self):
        (kind, pts), = [(k, p) for k, p, d in self.bb._segments if d == 'Y0 LED 애노드 -> +5V']
        self.assertEqual(kind, 'vcc')
        self.assertEqual(pts[0], (self.R['a'], self.bb.r_y(13)))
        self.assertEqual(pts[-1], (self.R['mid_vcc'], self.bb.r_y(13)))

    def test_넷은_신호_저항_캐소드_애노드_VCC(self):
        nets = self.bb.nets()

        def net_of(label):
            return next(n for n in nets if label in n['labels'])
        self.assertIn('vcc', net_of('LED Y0 애노드')['rails'])
        self.assertIs(net_of('LED Y0 캐소드'), net_of('저항1(330Ω) 아랫다리'))

    def test_순서표_사슬_줄에_0_이면_켜짐(self):
        self.assertTrue(any('0 이면 켜짐' in st['desc'] for st in self.bb.steps))

    def test_보통_사슬은_키가_그대로(self):
        bb = _board(self.mod)
        bb.led_chain(self.R['a'], 10, 'Y0', '시험', block='right')
        self.assertEqual(set(bb.led_chains[-1]),
                         {'tag', 'signal', 'anode', 'cathode', 'res_top', 'res_bottom'})

    def test_기준선의_Negative_사슬은_그대로(self):
        """다음 단계 그림에서 같은 사슬은 회색·번호 없음이다 — 열쇠가 극성 따라 어긋나면 매 단계
        새로 꽂으라고 나온다."""
        snap = self.bb.snapshot()
        bb = _board(self.mod, baseline=snap)
        bb.led_chain(self.R['a'], 10, 'Y0', '시험', block='right', active_low=True)
        self.assertFalse(any('0 이면 켜짐' in st['desc'] for st in bb.steps))
        self.assertTrue(any('0 이면 켜짐' in k for k in bb.kept))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py::NegativeLed -n0 -q`
Expected: FAIL(`led_chain()` 이 `active_low` 를 안 받음). `test_보통_사슬은_키가_그대로` 는 PASS.

- [ ] **Step 3: `led_chain` 을 고친다**

서명에 `active_low=False` 를 더하고, docstring 끝에 한 문단을 더한다.

```python
        `active_low` 면 **Negative Logic** 사슬이다(실험05 1-2, 교안 p9 "Output 을 Negative Logic
        으로 구축") — 출력이 0 일 때 켜진다. 신호 → 330Ω(옆 열, 윗행~윗행+2) → LED(그다음 열, 캐소드
        윗행+2 → 애노드 윗행+3) → +5V. 저항과 LED 의 열 쓰임이 보통 사슬과 뒤집힌다. 레일 점퍼는 보통
        사슬과 같은 윗행+3 에서 나가 배치기 `led_rows` 가 극성을 몰라도 된다. 레코드에는
        `'active_low': True` 를 더한다 — 보통 사슬에는 키를 넣지 않는다(`wiring()` → 도장).
```

`x_led, x_res = …` 다음의 `key = (…)` 를 아래로 바꾼다.

```python
        if active_low:
            x_l, a_row, k_row = x_res, top_row + 3, top_row + 2      # LED: 캐소드 위, 애노드 아래
            x_r, rt_row, rb_row = x_led, top_row, top_row + 2        # 330Ω: 신호 스트립 → 캐소드 스트립
        else:
            x_l, a_row, k_row = x_led, top_row, top_row + 1
            x_r, rt_row, rb_row = x_res, top_row + 1, top_row + 3
        key = (self.sym(x_l, a_row), self.sym(x_l, k_row),
               self.sym(x_r, rt_row), self.sym(x_r, rb_row))
```

`try:` 블록 본문 전체를 아래로 바꾼다(보통 사슬은 글자 하나 안 바뀐다 — 아래 `else` 갈래가 기존 문자열·좌표 그대로다).

```python
        try:
            y_a, y_k = self.r_y(a_row), self.r_y(k_row)
            y_rt, y_rb = self.r_y(rt_row), self.r_y(rb_row)
            y_top, y_end = self.r_y(top_row), self.r_y(top_row + 3)
            self.draw_led(x_l, y_a, y_k, color_rgb, tag)
            self.draw_resistor(x_r, y_rt, y_rb, label="330Ω")
            if self._pull_parts:
                x0, x1 = min(x_l, x_r) - 12, max(x_l, x_r) + 12
                self._dashed([(x0, y_top - 12), (x1, y_top - 12), (x1, y_end + 12), (x0, y_end + 12),
                              (x0, y_top - 12)], REMOVE, width=3, dash=7, gap=5,
                             draw=_ScaledDraw(self.ghost_layer))
                self.ghost_chains_drawn.add(key)
            rec = {'tag': tag,
                   'signal': self.sym(x, top_row),
                   'anode': self.sym(x_l, a_row),
                   'cathode': self.sym(x_l, k_row),
                   'res_top': self.sym(x_r, rt_row),
                   'res_bottom': self.sym(x_r, rb_row)}
            if active_low:
                rec['active_low'] = True
            self.led_chains.append(rec)
            if active_low:
                self.step_note('sig', self.addr(x_r, y_rt), self.addr(x_l, y_a),
                               f'{tag}: 330Ω({self.addr(x_r, y_rt)}→{self.addr(x_r, y_rb)}) + '
                               f'LED(캐소드 {self.addr(x_l, y_k)}→애노드 {self.addr(x_l, y_a)}) 직렬 · '
                               f'0 이면 켜짐 · {desc}',
                               marker_near=(x + marker_dx, self.r_y(top_row + 1)))
                x_rail, kind, what = self.nearest_vcc_rail(x_led, block), 'vcc', f'{tag} LED 애노드 -> +5V'
            else:
                self.step_note('sig', self.addr(x_l, y_a), self.addr(x_r, y_rb),
                               f'{tag}: LED({self.addr(x_l, y_a)}→{self.addr(x_l, y_k)}) + '
                               f'330Ω({self.addr(x_r, y_k)}→{self.addr(x_r, y_rb)}) 직렬 · {desc}',
                               marker_near=(x + marker_dx, y_k))
                x_rail, kind, what = self.nearest_gnd_rail(x_led, block), 'gnd', f'{tag} 저항 아래 -> GND'
            # 레일 점퍼는 윗행+3 에서 레일에 가장 가까운 빈 홀로 — 그 행에서 비어 있는 열은 두 극성 모두
            # 신호 열과 `x_led` 다(보통 사슬은 LED 가 윗행~+1, Negative 는 저항이 윗행~+2)
            free = [x, x_led] + ([group[i + 3 * step]] if 0 <= i + 3 * step < len(group) else [])
            x_from = min(free, key=lambda h: abs(h - x_rail))
            r_rail = self.free_rail_row(top_row + 3, x_rail)
            self.step_wire([(x_from, y_end), (x_rail, self.r_y(r_rail))],
                           kind, what, width=2, marker_near=(x_from - 22, y_end + 2))
        finally:
            self._keep_parts = False
            self._pull_parts = False
```

`led_rows` docstring 의 "윗행+3(저항 아랫다리 = GND 점퍼 출발 행)" 을 "윗행+3(레일 점퍼 출발 행 — 보통 사슬은 저항 아랫다리 → GND, Negative 사슬은 LED 애노드 → +5V)" 로, `mid_rail_rows` docstring 의 "LED GND 점퍼가 여기 착지하면" 을 "LED 레일 점퍼(GND·VCC)가 여기 착지하면" 으로 고친다.

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m pytest tests/test_breadboard_dip16.py -n0 -q`
Expected: PASS.

- [ ] **Step 5: 시험판을 Negative 로 바꾼다**

`tests/fixtures/board_v2_e5/배치.py` 의 `led_chain` 줄을 바꾸고 노트를 더한다.

```python
    for tag in _LEDS:
        bb.led_chain(R['a'], lay['leds']['bcd'][tag], tag, f'{tag} — 진리표 {tag} 열', block='right',
                     active_low=True)
```

```python
_LOW_NOTE = 'Y0~Y9 LED 는 출력 0 에서 켜진다(Negative Logic).'
```

```python
    bb.note(_INPUT_NOTE)
    bb.note(_LOW_NOTE)
```

머리 주석의 `K1 :` 줄 아래에 `#   LED 사슬은 Negative Logic(교안 p9) — 신호 → 330Ω → LED → +5V, 출력 0 에서 켜진다.` 를 더한다.

- [ ] **Step 6: v1·v2 회귀와 시험판을 배경으로 돈다**

Run: `python -m pytest tests/test_breadboard_boards.py tests/test_breadboard_v2.py tests/test_breadboard_v2_e4_trial.py tests/test_breadboard_v2_e5_trial.py tests/test_breadboard_place.py tests/test_hand_compare.py tests/test_trace_guide.py -q`
Expected: PASS. v1 도장과 e4 가 그대로다. e5 시험판은 사슬 부품 자리만 바뀌고 `verify()` 를 통과한다. `PlaceEnforced` 가 통과하는 이유는 지문이 `fixed` 를 안 보기 때문이다. e5 시험판이 막히면 Task 4 Step 6 처럼 `place_search` 를 다시 돌린다. 그래도 막히면 멈추고 보고한다.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py tests/test_breadboard_dip16.py tests/fixtures/board_v2_e5
git commit -m "feat(breadboard): Negative Logic LED 사슬 — led_chain(active_low=True), 출력 0 에서 켜진다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 시뮬레이터 — 74HC42 와 LED 극성

**Files:**
- Modify: `tests/_gate_sim.py`
- Test: `tests/test_gate_sim.py`, `tests/test_breadboard_v2_e5_trial.py`

**Interfaces:**
- Consumes: Negative 사슬 레코드 `active_low`(Task 5). `bb._strip(sym)`, `bb._lead_labels() -> [(라벨, sym)]`.
- Produces:
  - `PINMAP` 항목은 `(입력핀들, 출력핀)` 또는 `(입력핀들, 출력핀, 함수)` 다. 함수가 있으면 `_FUNC` 대신 쓴다.
  - `PINMAP['74HC42']`
  - `led_on(bb, nets, tag, inputs) -> bool`

- [ ] **Step 1: 실패하는 시험을 쓴다** — `tests/test_gate_sim.py`

머리 import 를 `from types import SimpleNamespace` 와 `from tests._gate_sim import SimError, led_on, value_of` 로 바꾸고, `GateSim` 에 더한다.

```python
    def test_74HC42_는_BCD_값의_출력만_0(self):
        nets = [net('입력 A', '74HC42#3 pin 15'), net('입력 B', '74HC42#3 pin 14'),
                net('입력 C', '74HC42#3 pin 13'), net('입력 D', '74HC42#3 pin 12')]
        outs = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 9, 8: 10, 9: 11}
        nets += [net(f'74HC42#3 pin {p}', f'Y{n}') for n, p in outs.items()]
        for v in range(16):                    # 10~15 는 BCD 밖 — 모두 1
            ins = {'A': v & 1, 'B': v >> 1 & 1, 'C': v >> 2 & 1, 'D': v >> 3 & 1}
            for n in range(10):
                self.assertEqual(value_of(nets, f'Y{n}', ins), 0 if v == n else 1, (v, n))

    def test_led_on_은_사슬_극성을_본다(self):
        bb = SimpleNamespace(
            led_chains=[{'tag': 'Y0', 'signal': ('right', 'a', 10), 'active_low': True},
                        {'tag': 'L1', 'signal': ('right', 'a', 20)}],
            _strip=lambda s: (s[0], 'ae', s[2]),
            _lead_labels=lambda: [('저항1(330Ω) 윗다리', ('right', 'b', 10)),
                                  ('LED L1 애노드', ('right', 'b', 20))])
        nets = [net('입력 A', '저항1(330Ω) 윗다리'), net('입력 B', 'LED L1 애노드')]
        self.assertTrue(led_on(bb, nets, 'Y0', {'A': 0, 'B': 0}))
        self.assertFalse(led_on(bb, nets, 'Y0', {'A': 1, 'B': 0}))
        self.assertTrue(led_on(bb, nets, 'L1', {'A': 0, 'B': 1}))
        self.assertFalse(led_on(bb, nets, 'L1', {'A': 0, 'B': 0}))
        with self.assertRaisesRegex(SimError, 'Y9'):
            led_on(bb, nets, 'Y9', {'A': 0, 'B': 0})
```

`tests/test_breadboard_v2_e5_trial.py` 머리에 `from tests._gate_sim import led_on` 을 더하고 `BcdFinal` 에 더한다.

```python
    def test_진리표_BCD_0_15(self):
        """BCD 값 n 이면 Y_n LED 하나만 켜진다. 10~15 면 다 꺼진다(교안 p9 — Negative Logic)."""
        nets = self.bb.nets()
        for v in range(16):
            ins = {'A': v & 1, 'B': v >> 1 & 1, 'C': v >> 2 & 1, 'D': v >> 3 & 1}
            for n in range(10):
                self.assertEqual(led_on(self.bb, nets, f'Y{n}', ins), v == n, (v, n))
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_gate_sim.py -n0 -q`
Expected: FAIL(`led_on` import 실패).

- [ ] **Step 3: 구현한다** — `tests/_gate_sim.py`

모듈 docstring 끝에 "MSI 칩(74HC42)은 출력마다 함수가 달라 `PINMAP` 항목 셋째 원소로 준다." 를 더한다. `PINMAP` 에 더한다.

```python
# 74HC42 BCD → 10진: 입력 A(15)·B(14)·C(13)·D(12), A 가 LSB. 값 n 이면 Y_n 만 0, 10~15 면 전부 1
_HC42_OUT = (1, 2, 3, 4, 5, 6, 7, 9, 10, 11)
PINMAP['74HC42'] = [((15, 14, 13, 12), p,
                     lambda v, n=n: 0 if v[0] + 2 * v[1] + 4 * v[2] + 8 * v[3] == n else 1)
                    for n, p in enumerate(_HC42_OUT)]
```

`_drivers` 의 안쪽 루프를 바꾼다.

```python
            for entry in PINMAP[chip]:
                ins, o = entry[0], entry[1]
                if o == pin:
                    fn = entry[2] if len(entry) > 2 else _FUNC[chip]
                    out.setdefault(i, []).append((chip, row, ins, fn))
```

`_drivers` docstring 을 `"""넷 번호 → [(칩, 행, 입력핀들, 함수)] — 그 넷에 출력핀이 앉은 게이트."""` 로 고친다. `value_of` 의 `ev` 안을 바꾼다.

```python
        if gates:
            chip, row, ins, fn = gates[0]
            vals = []
            for p in ins:
                lab = f'{chip}#{row} pin {p}'
                if lab not in where:
                    raise SimError(f'뜬 입력: {lab}')
                vals.append(ev(where[lab]))
            srcs.append(fn(vals))
```

파일 끝에 더한다.

```python
def led_on(bb, nets, tag, inputs):
    """LED `tag` 가 켜지는가. 보통 사슬은 신호 1 에서, Negative Logic 사슬(`active_low`)은 신호 0 에서
    켜진다. 신호 스트립에 꽂힌 다리 라벨로 값을 읽는다 — 보통 사슬은 LED 애노드, Negative 사슬은 저항
    윗다리다."""
    chain = next((c for c in bb.led_chains if c['tag'] == tag), None)
    if chain is None:
        raise SimError(f'LED 사슬 {tag} 이 없다')
    strip = bb._strip(chain['signal'])
    label = next((lab for lab, sym in bb._lead_labels() if bb._strip(sym) == strip), None)
    if label is None:
        raise SimError(f'LED 사슬 {tag} 의 신호 스트립에 다리가 없다')
    return value_of(nets, label, inputs) == (0 if chain.get('active_low') else 1)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python -m pytest tests/test_gate_sim.py -n0 -q`, 그다음 배경으로 `python -m pytest tests/test_breadboard_v2_e5_trial.py tests/test_breadboard_v2_e4_trial.py -q`
Expected: PASS(e4 의 `value_of` 시험도 그대로).

- [ ] **Step 5: 커밋**

```bash
git add tests/_gate_sim.py tests/test_gate_sim.py tests/test_breadboard_v2_e5_trial.py
git commit -m "test(breadboard): 시뮬레이터에 74HC42 와 LED 극성 — 시험판 BCD 0~15 진리표

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: SKILL·draft-lab-spec 문서

**Files:**
- Modify: `.claude/skills/breadboard-diagram/SKILL.md` (§2b ~70-99, "v2 배치 규약" ~405)
- Modify: `.claude/skills/draft-lab-spec/SKILL.md` (v2 자리표 규약 ~536-546)
- Test: `tests/test_skill_docs.py` (`BreadboardV2Docs`)

- [ ] **Step 1: 실패하는 시험을 쓴다** — `BreadboardV2Docs` 에 더한다.

```python
    def test_렌더러_문서가_DIP16_과_Negative_LED_를_적는다(self):
        """실험05 1-2(74HC42) — 16핀 칩과 출력 0 에서 켜지는 LED(2026-10-05). 문서에 없으면 다음 주차
        빌더가 14핀·GND 사슬 습관으로 돌아가거나, a쪽 출력을 위에서부터 적어 배선기가 막힌다."""
        text = BREADBOARD_SKILL.read_text(encoding="utf-8")
        for s in ("DIP_PINS", "active_low=True", "Negative Logic", "pin 4, 3, 2, 1, 5, 6, 7",
                  "tests/fixtures/board_v2_e5/배치.py", "Y0, Y1, Y2, Y3, Y4, Y5, Y9, Y6, Y8, Y7"):
            self.assertIn(s, text)
        draft = DRAFT.read_text(encoding="utf-8")
        for s in ("Negative Logic", "+5V → LED → 330Ω → 출력", "MSI"):
            self.assertIn(s, draft)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_skill_docs.py::BreadboardV2Docs -n0 -q`
Expected: 새 시험 FAIL.

- [ ] **Step 3: breadboard-diagram SKILL 을 고친다**

§2b 의 `- 본보기: tests/fixtures/board_v2/배치.py …` 항목 아래에 둘을 더한다.

```markdown
- **DIP-16 칩(74HC42 따위).** 칩 핀 수는 엔진의 칩 모델 표 `DIP_PINS`(이름 → 14/16)에서 온다 —
  배치기는 표에 없는 칩을 거절하고, 그리기는 모르는 이름을 14핀으로 본다(v1 빌더 호환). 16핀 칩은
  8행이고 pin 16 → 가운데 VCC(행 k), pin 8 → GND(행 k+7)다. 이름 글자는 몸통 가운데 반 행 하나만
  막게 줄여 그린다 — 74HC42 는 a쪽 pin 1~7 이 전부 출력이라 일곱 가닥이 몸통을 건너는데, 건널 반 행이
  핀마다 하나뿐이다. 그래서 a쪽 출력 → LED 선은 배선표에 **이름 상자에 가까운 핀부터**
  (pin 4, 3, 2, 1, 5, 6, 7) 적는다 — 배선기 수리는 막힌 선 앞 한 가닥만 바꿔 보므로 위에서부터 적으면
  pin 4 가 막힌다. 본보기 `tests/fixtures/board_v2_e5/배치.py`(실험05 1-2 시험판).
- **Negative Logic LED.** 출력이 0 일 때 켜지는 회로(교안 "Output 을 Negative Logic 으로 구축")는
  `bb.led_chain(R['a'], top, 'Y0', desc, block='right', active_low=True)` 로 그린다 — 신호 우 a 윗행 →
  330Ω(b, 윗행~윗행+2) → LED(c, 캐소드 윗행+2 → 애노드 윗행+3) → a 윗행+3 에서 가운데 VCC 레일. 레일
  점퍼 행이 보통 사슬과 같은 윗행+3 이라 배치기는 극성을 모른다. 보드 위 꼬리표는 신호 이름만 두고,
  보드 아래 `bb.note('Y0~Y9 LED 는 출력 0 에서 켜진다(Negative Logic).')` 한 줄을 둔다(순서표 사슬
  줄에는 엔진이 `0 이면 켜짐` 을 넣는다). LED 순서는 R10 대로 **칩 핀 행 순서**다 — 진리표 순서와 다르면
  핀 행 순서가 이긴다(74HC42: Y0, Y1, Y2, Y3, Y4, Y5, Y9, Y6, Y8, Y7 — Y7·Y8·Y9 가 pin 9·10·11).
```

"v2 배치 규약 (R9·R10)" 문단의 "LED 를 구동하는 게이트는 **f~j 쪽(pin 8~14)** 에 배정해 건너는 선이 칩 몸통 위를 지나지 않게 하고," 바로 뒤에 "(핀이 정해진 MSI 칩은 예외 — 위 DIP-16 항목)" 을 끼운다.

- [ ] **Step 4: draft-lab-spec SKILL 을 고친다**

"LED 를 구동하는 게이트는 칩의 **f쪽(pin 8~14)** 에 배정한다. …(실물: 실험04 M9)." 항목 아래에 둘을 더한다(같은 들여쓰기).

```markdown
     - 핀이 정해진 **MSI 칩**(74HC42 따위 DIP-16)은 출력 쪽을 고를 수 없다 — a쪽 출력도 LED 로
       건넌다(엔진이 이름 글자를 줄여 건널 반 행을 남긴다). LED 번호는 그래도 핀 행 순서다(실험05 1-2:
       Y0~Y5, Y9, Y6, Y8, Y7). 진리표 열 순서와 다르면 그 사실을 미확정 표에 적는다.
     - 출력이 0 에서 켜지는 회로(교안 "Output 을 Negative Logic 으로 구축")는 LED 사슬을
       `+5V → LED → 330Ω → 출력` 으로 적는다. 결선도 빌더는 `led_chain(…, active_low=True)` 로 그린다.
```

- [ ] **Step 5: 통과를 확인한다**

Run: `python -m pytest tests/test_skill_docs.py -n0 -q`
Expected: PASS(기존 문서 시험 포함).

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/breadboard-diagram/SKILL.md .claude/skills/draft-lab-spec/SKILL.md tests/test_skill_docs.py
git commit -m "docs(breadboard): DIP-16 칩·Negative Logic LED·a쪽 출력 배선 순서를 SKILL 에 적는다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 전체 스위트·결과 기록·후속 칩

**Files:**
- Modify: `docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md` (끝에 "실행 결과")

- [ ] **Step 1: 전체 스위트를 배경으로 돈다** (5~6분)

Run: `python -m pytest -q`
Expected: 알려진 환경 실패(Global Constraints) 밖 실패 0. `test_lab_isolate` 가 실패하면 그 파일만 다시 돈다.

- [ ] **Step 2: 설계 문서 끝에 "실행 결과" 절을 쓴다** — 아래 다섯 가지를 적는다.
  - Task 4 Step 5(안쪽 반 행 벌점)를 했는가.
  - 시험판 `LAYOUT`(칩 행·LED 윗행·브리지).
  - superset 지표: `python -c` 로 `_place_measure(list(b.PLACE), b.LAYOUT)` 를 찍은 길이·꺾임·밀도.
  - 전체 스위트 결과 줄.
  - 남은 일: 손그림 대조 H6·H7, `보고서/실험05` 명세·netlist·결선도.

- [ ] **Step 3: 커밋**

```bash
git add docs/plans/2026-10-05-실험05-DIP16-negative-LED-설계.md
git commit -m "docs(plans): 실험05 DIP-16·Negative LED 실행 결과

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: 후속 작업 칩을 올린다** (`spawn_task`). 프롬프트에는 아래를 넣는다.
  - 제목: "손그림 대조를 DIP-16·Negative LED 에 맞춘다"
  - `scripts/lab/hand_compare.py:362` H6 이 전원 핀을 `(14, 'VCC', 'GND'), (7, 'GND', 'VCC')` 로 박았다. 칩 레코드 `len(pins)` 로 n / n/2 를 쓴다.
  - `check_led_chains`(H7)가 캐소드↔저항 윗다리, 저항 아랫다리↔GND 를 가정한다. Negative 사슬(`active_low`)은 신호↔저항 윗다리, 저항 아랫다리↔캐소드, 애노드↔+5V 다.
  - 실험05 손그림을 대조하기 전에 필요하다.
  - 브랜치 `e5-dip16` 병합 뒤에 한다.

- [ ] **Step 5: 브랜치 전체 검토** — 가장 강한 모델로 새 검토자 하나를 띄워 `main..e5-dip16` 을 본다(Native 실행의 마지막 관문). 지적을 고치고 다시 돈 뒤 사용자에게 병합을 묻는다.
