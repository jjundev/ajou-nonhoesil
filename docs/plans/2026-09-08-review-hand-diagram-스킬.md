# 손그림 결선도 검토 스킬 (`review-hand-diagram`) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학생이 배포본 판형 위에 그린 손그림 결선도 PDF 를 승인된 참조 결선도와 넷 수준으로 대조해 쪽별 판정 문서와 증거 크롭을 내는 스킬을 만든다.

**Architecture:** 렌더러(`render_breadboard.py`)가 자기 그림의 배선·부품·칩을 **기호 좌표**로 내놓는 `wiring()` 을 새로 갖는다. `scripts/lab/` 에 세 모듈을 더한다 — 판형 좌표를 맞추고 격자를 덮는 `hand_grid`, 전사 JSON 을 읽는 `hand_transcript`, 넷을 만들어 13개 규칙으로 대조하는 `hand_compare`. 끝점 읽기만 Claude vision 이 하고 판단은 전부 코드가 한다.

**Tech Stack:** Python 3.14 표준 라이브러리 + `pymupdf`(fitz) + `pillow`. 새 의존성 없음 — 둘 다 `requirements-dev.txt` 에 이미 있다. 테스트는 `unittest` (저장소 전체 관례).

**Spec:** `docs/plans/2026-09-08-review-hand-diagram-설계.md`

## Global Constraints

- **답변·문서·주석은 한국어.** 코드 식별자와 경로만 원문. 저장소 전체 관례다.
- **`scripts/lab/` 은 표준 라이브러리만 쓴다** — `requirements-dev.txt` 에 적힌 정책. 예외는 이 계획이 쓰는 `fitz`·`PIL` 뿐이고, 둘 다 "테스트와 검증 스크립트 전용"으로 이미 선언돼 있다. 새 의존성을 추가하지 않는다.
- **판형 좌표를 사람이 뜨지 않는다.** 렌더러 `cols`·`r_y()` 가 유일한 권위이고, 검출값을 거기 맞춘다. 잔차 한계 **3px**.
- **홀 허용치는 렌더러와 같은 5px** (`hole_at()` 이 쓰는 값). 두 곳에 다른 값을 두지 않는다.
- **레일 빈 행은 `RAIL_GAP_ROWS` 를 import 해서 쓴다.** 재선언 금지.
- **칩 대응은 종류(label)로, 같은 종류가 둘이면 `#2`** — `regen_compare.py` 와 같은 관례.
- **테스트 이름은 한국어 문장** (`def test_레일_빈_행에_꽂은_끝점은_막힌다`). 기존 `tests/test_breadboard_physical.py` 관례.
- 렌더러 변경은 **전부 가산적**이다. 기존 함수의 동작·시그니처를 바꾸지 않는다.
- 실험 폴더 경로는 `scripts.lab.config.experiment_dir()` 로만 만든다. `실험1` 을 손으로 적지 않는다.

## 파일 구조

| 파일 | 책임 |
|---|---|
| `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` (수정) | 그리면서 **구조화 기록**을 남기고 `wiring()` 으로 내놓는다. 빌더가 `bb` 를 반환한다 |
| `scripts/lab/hand_grid.py` (신규) | PDF 에서 판형 래스터를 꺼내고, 홀 격자를 검출해 렌더러 좌표표에 맞추고, 격자 오버레이·크롭을 만든다 |
| `scripts/lab/hand_transcript.py` (신규) | 주소 문법 파싱, 전사 JSON → `Diagram`, 칩 핀 배치 공식 |
| `scripts/lab/hand_compare.py` (신규) | 넷 모델, 참조 `Diagram` 추출, 규칙 H1~H13, 판정 마크다운 |
| `.claude/skills/review-hand-diagram/SKILL.md` (신규) | 절차서 |
| `tests/test_breadboard_wiring.py` (신규) | `wiring()` 계약 |
| `tests/test_hand_grid.py` (신규) | 판형 검출·맞춤 |
| `tests/test_hand_transcript.py` (신규) | 주소·전사 파싱 |
| `tests/test_hand_compare.py` (신규) | 넷 모델과 규칙 13개 |
| `tests/test_skill_docs.py` (수정) | 새 SKILL.md 를 교차참조 검사에 등록 |

---

### Task 1: 렌더러가 구조화 기록을 남긴다

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py`
- Test: `tests/test_breadboard_wiring.py`

**Interfaces:**
- Consumes: 없음 (첫 과제)
- Produces:
  - `BreadboardRenderer.sym(x, row) -> (block, col, row) | None` — 픽셀 x 를 열 이름으로. `block` 은 `'left'|'right'`, `col` 은 `cols` 의 키(`'a'`~`'j'`, `'gnd'`, `'vcc'`, `'mid_gnd'`, `'mid_vcc'`).
  - `BreadboardRenderer.wiring() -> dict` — 키는 `chips`, `wires`, `leds`, `resistors`, `chains`, `unused_inputs`, `unused_outputs`, `bridges`, `overlaps`.
  - `build_e1_and/or/nand/nor/comb/comb_s1/comb_s2/comb_s3(output_path, template_path=None) -> BreadboardRenderer`
  - 기록 리스트 `bb.chips`, `bb.leds`, `bb.resistors`, `bb.led_chains`, `bb.unused_inputs`, `bb.unused_outputs`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_breadboard_wiring.py` 를 만든다.

```python
"""렌더러가 **자기가 그린 것**을 기호 좌표로 내놓는지 검사한다.

손그림 검토(`review-hand-diagram`)는 이 출력을 정답으로 삼는다. 픽셀이 아니라
(블록, 열, 행) 으로 내는 이유는 손그림 전사가 '좌 b10' 같은 주소로 적히기
때문이다 — 양쪽을 같은 말로 맞춰야 비교가 된다.

문자열을 파싱해서 알아내지 않는다. `_leads` 에는 '74HC08 pin 3' 같은 뜻풀이가
들어 있지만 그건 사람이 읽는 말이지 계약이 아니다. 그리는 쪽이 사실을 그대로
적어 두게 한다.
"""
import importlib.util
import os
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Wiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.tmp = tempfile.mkdtemp()
        cls.and_bb = cls.mod.build_e1_and(os.path.join(cls.tmp, 'and.png'))
        cls.nand_bb = cls.mod.build_e1_nand(os.path.join(cls.tmp, 'nand.png'))

    def test_빌더가_렌더러를_돌려준다(self):
        self.assertIsInstance(self.and_bb, self.mod.BreadboardRenderer)

    def test_sym_은_픽셀_x_를_열_이름으로_바꾼다(self):
        bb = self.and_bb
        c = bb.cols['left']
        self.assertEqual(bb.sym(c['b'], 10), ('left', 'b', 10))
        self.assertEqual(bb.sym(c['mid_vcc'], 3), ('left', 'mid_vcc', 3))
        self.assertIsNone(bb.sym(95, 10))

    def test_칩은_라벨과_pin1_행과_핀_배치를_남긴다(self):
        chips = self.and_bb.wiring()['chips']
        self.assertEqual([c['label'] for c in chips], ['74HC08'])
        chip = chips[0]
        self.assertEqual(chip['pin1_row'], 10)
        self.assertEqual(chip['block'], 'left')
        # pin 1~7 은 e 열, pin 8~14 는 f 열. draw_chip 이 그렇게 꽂는다
        self.assertEqual(chip['pins'][1], ('left', 'e', 10))
        self.assertEqual(chip['pins'][7], ('left', 'e', 16))
        self.assertEqual(chip['pins'][14], ('left', 'f', 10))
        self.assertEqual(chip['pins'][8], ('left', 'f', 16))

    def test_배선은_양_끝을_기호_좌표로_남긴다(self):
        wires = self.and_bb.wiring()['wires']
        ends = {(w['frm'], w['to']) for w in wires}
        # pin 14 -> 중앙 VCC 레일 (connect_power)
        self.assertIn((('hole', ('left', 'g', 10)),
                       ('hole', ('left', 'mid_vcc', 10))), ends)

    def test_전원잭_끝점은_홀이_아니라_잭으로_남는다(self):
        wires = self.and_bb.wiring()['wires']
        jacks = {w['frm'] for w in wires if w['frm'][0] == 'jack'}
        self.assertEqual(jacks, {('jack', 'red'), ('jack', 'gray')})

    def test_LED_사슬은_네_홀을_한_묶음으로_남긴다(self):
        chains = {ch['tag']: ch for ch in self.and_bb.wiring()['chains']}
        self.assertEqual(set(chains), {'L1', 'L2'})
        l2 = chains['L2']
        # led_chain(c['c'], 19, "L2", ...) — 도착 c19, LED 는 옆 열, 저항은 그 다음
        self.assertEqual(l2['anode'][2], 19)
        self.assertEqual(l2['cathode'][2], 20)
        self.assertEqual(l2['res_top'][2], 20)
        self.assertEqual(l2['res_bottom'][2], 22)
        self.assertEqual(l2['anode'][1], l2['cathode'][1])
        self.assertNotEqual(l2['anode'][1], l2['res_top'][1])

    def test_미사용_입력과_출력이_따로_남는다(self):
        w = self.and_bb.wiring()
        self.assertEqual({(u['chip'], u['pin']) for u in w['unused_inputs']},
                         {('74HC08', 9), ('74HC08', 10), ('74HC08', 12), ('74HC08', 13)})
        self.assertEqual({(u['chip'], u['pin']) for u in w['unused_outputs']},
                         {('74HC08', 8), ('74HC08', 11)})

    def test_레일_브리지가_열_이름_쌍으로_남는다(self):
        bridges = self.and_bb.wiring()['bridges']
        pairs = {(k, a[1], b[1]) for k, a, b in bridges}
        self.assertIn(('gnd', 'gnd', 'mid_gnd'), pairs)
        self.assertIn(('vcc', 'vcc', 'mid_vcc'), pairs)

    def test_칩이_둘인_회로는_둘_다_남는다(self):
        chips = self.nand_bb.wiring()['chips']
        self.assertEqual([c['label'] for c in chips], ['74HC08', '74HC00'])
        self.assertEqual([c['pin1_row'] for c in chips], [7, 18])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_breadboard_wiring.py -q`
Expected: FAIL — `AttributeError: 'BreadboardRenderer' object has no attribute 'sym'` 그리고 빌더가 `None` 을 돌려준다.

- [ ] **Step 3: 기록 리스트와 `sym()` 을 더한다**

`__init__` 의 `self._addr_map = self._build_addr_map()` 바로 앞에 기록 리스트를 더한다.

```python
        # 그린 것을 **사실 그대로** 적어 둔다. 손그림 검토가 이걸 정답으로
        # 읽는다. `_leads` 의 뜻풀이 문자열을 파싱하게 두면 말이 바뀔 때마다
        # 검사기가 조용히 깨진다 — 검사기는 코드를 읽어야지 산문을 읽으면 안 된다
        self.chips = []
        self.leds = []
        self.resistors = []
        self.led_chains = []
        self.unused_inputs = []
        self.unused_outputs = []
```

`_build_addr_map()` 바로 아래에 `_build_sym_map()` 과 `sym()` 을 더한다.

```python
    def _build_sym_map(self):
        """x 좌표 -> (블록, 열 이름). `_addr_map` 의 기계용 짝이다."""
        out = {}
        for block in ('left', 'right'):
            for key, x in self.cols[block].items():
                if key.startswith('chip'):
                    continue
                out[x] = (block, key)
        return out

    def sym(self, x, row):
        """(x, 행) -> (블록, 열 이름, 행). 홀이 아니면 None.

        `addr()` 이 사람이 읽는 '좌 b10' 을 만든다면 이쪽은 기계가 비교하는
        ('left', 'b', 10) 을 만든다. 허용치는 `hole_at()` 과 같은 5px 다 —
        열 피치가 16px 라 그보다 넓으면 인접 열 사이에 거부 구간이 없다.
        """
        best = min(self._sym_map, key=lambda k: abs(k - x))
        if abs(best - x) > 5:
            return None
        block, col = self._sym_map[best]
        return (block, col, row)
```

`__init__` 끝의 `self._addr_map = self._build_addr_map()` 다음 줄에 `self._sym_map = self._build_sym_map()` 을 더한다.

- [ ] **Step 4: 그리는 자리마다 기록을 남긴다**

`draw_chip()` 의 핀 루프 **뒤에** 기록을 더한다 (`for i in range(7):` 루프가 끝난 다음).

```python
        pins = {}
        for i in range(7):
            pins[i + 1] = self.sym(c['e'], start_row + i)
            pins[14 - i] = self.sym(c['f'], start_row + i)
        self.chips.append({'label': name, 'block': block,
                           'pin1_row': start_row, 'pins': pins})
```

`draw_resistor()` 의 첫 두 `self.lead(...)` 뒤에 더한다.

```python
        self.resistors.append({'label': label,
                               'top': self.sym(x, self._row_of(y1)),
                               'bottom': self.sym(x, self._row_of(y2))})
```

`draw_led()` 의 첫 두 `self.lead(...)` 뒤에 더한다.

```python
        self.leds.append({'tag': label,
                          'anode': self.sym(x, self._row_of(y_anode)),
                          'cathode': self.sym(x, self._row_of(y_cathode))})
```

`led_chain()` 의 `self.draw_resistor(x_res, y_k, y_r, label="330Ω")` 뒤에 더한다.

```python
        self.led_chains.append({'tag': tag,
                                'signal': self.sym(x, top_row),
                                'anode': self.sym(x_led, top_row),
                                'cathode': self.sym(x_led, top_row + 1),
                                'res_top': self.sym(x_res, top_row + 1),
                                'res_bottom': self.sym(x_res, top_row + 3)})
```

`connect_unused_inputs()` 의 `for p in pins:` 루프 안, `self.touch_rail(rail, x_rail)` 뒤에 더한다.

```python
            self.unused_inputs.append({'chip': chip, 'pin': p, 'rail': rail})
```

`mark_unused_outputs()` 의 `pin_str = ...` 앞에 더한다.

```python
        for p in pins:
            self.unused_outputs.append({'chip': chip, 'pin': p})
```

- [ ] **Step 5: `wiring()` 을 더한다**

`verify()` 바로 앞에 넣는다.

```python
    def wiring(self):
        """이 그림이 무엇을 어디에 꽂았는지 **기호 좌표**로 낸다.

        손그림 검토(`review-hand-diagram`)가 정답으로 쓴다. 픽셀이 아니라
        (블록, 열, 행) 으로 내는 이유는 손그림 전사가 '좌 b10' 같은 주소로
        적히기 때문이다 — 양쪽을 같은 말로 맞춰야 비교가 된다.

        `overlaps` 는 `verify()` 가 채운다. `export()` 를 거친 렌더러면 차 있고,
        아니면 비어 있다. 참조 그림에서 **잘 안 보이는 선**을 판정문에 주석으로
        달기 위한 것이다 — 복합회로의 A 갈래가 초록 Z 선 아래 깔려 있어서
        따라 그린 사람이 통째로 빠뜨렸다.
        """
        def endpoint(p):
            x, y = p
            if y < 240 and any(abs(x - jx) < 30 for jx in JACKS.values()):
                color = min(JACKS, key=lambda k: abs(JACKS[k] - x))
                return ('jack', color)
            return ('hole', self.sym(x, self._row_of(y)))

        wires = [{'kind': kind, 'desc': desc,
                  'frm': endpoint(pts[0]), 'to': endpoint(pts[-1])}
                 for kind, pts, desc in self._segments]
        bridges = [(kind, self.sym(a, 1), self.sym(b, 1))
                   for kind, a, b in sorted(self._bridged)]
        return {
            'chips': list(self.chips),
            'wires': wires,
            'leds': list(self.leds),
            'resistors': list(self.resistors),
            'chains': list(self.led_chains),
            'unused_inputs': list(self.unused_inputs),
            'unused_outputs': list(self.unused_outputs),
            'bridges': bridges,
            'overlaps': list(self.overlap_warnings),
        }
```

- [ ] **Step 6: 빌더가 렌더러를 돌려주게 한다**

`build_e1_and`, `build_e1_or`, `build_e1_nand`, `build_e1_nor`, `build_e1_comb` 의 마지막 줄 `bb.export(...)` 다음에 `return bb` 를 더한다. `build_e1_comb_s1/s2/s3` 는 `build_e1_comb(...)` 호출 앞에 `return` 을 붙인다.

```python
    bb.export(output_path, max_row=31)
    return bb
```

```python
def build_e1_comb_s1(output_path, template_path=None):
    return build_e1_comb(output_path, template_path, stage=1)
```

- [ ] **Step 7: 통과를 확인한다**

Run: `python3 -m pytest tests/test_breadboard_wiring.py -q`
Expected: PASS (9 tests)

- [ ] **Step 8: 기존 테스트가 안 깨졌는지 본다**

Run: `python3 -m pytest tests/test_breadboard_physical.py tests/test_breadboard_readability.py tests/test_breadboard_coords.py tests/test_breadboard_diagram_cli.py -q`
Expected: PASS — 변경이 전부 가산적이라 하나도 안 깨져야 한다.

- [ ] **Step 9: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py tests/test_breadboard_wiring.py
git commit -m "feat: 렌더러가 그린 것을 기호 좌표로 내놓는다 — wiring()"
```

---

### Task 2: 판형 래스터를 꺼내 렌더러 좌표표에 맞춘다

**Files:**
- Create: `scripts/lab/hand_grid.py`
- Test: `tests/test_hand_grid.py`

**Interfaces:**
- Consumes: Task 1 의 `BreadboardRenderer.cols`, `r_y()`, `_sym_map`
- Produces:
  - `load_renderer() -> module` — 렌더러 모듈을 경로로 불러온다
  - `BoardImage(md5, width, height, rect, data)` — dataclass
  - `board_image(pdf_path, page_index=0) -> BoardImage`
  - `detect_grid(data) -> (col_xs, row_ys)` — 검출된 홀 중심 좌표 리스트
  - `Calibration(ax, bx, ay, by, res_x, res_y, rect, dpi)` — dataclass, `to_px(x, y) -> (px, py)`
  - `calibrate(board, dpi=300) -> Calibration`
  - `GridError(ValueError)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_grid.py` 를 만든다. 살아 있는 배포본 판형을 쓴다.

```python
"""손그림 PDF 에서 판형을 꺼내 렌더러 좌표표에 맞추는 부분을 검사한다.

판형 좌표를 **사람이 뜨지 않는다.** 배포본은 정본 `Breadboard.jpg` 와 같은
그림인데 가로가 5% 넓다 (`breadboard-diagram/SKILL.md` §2). 눈대중으로 새로
뜨면 배선 끝점이 홀 안에 안 들어가고, 그림은 멀쩡해 보여서 눈으로는 안 잡힌다.
그래서 검출한 격자를 렌더러의 권위 있는 좌표표에 1차식으로 맞추고, 잔차가
크면 소리를 내며 멈춘다.
"""
import unittest
from pathlib import Path

from scripts.lab import hand_grid

ROOT = Path(__file__).resolve().parents[1]
HANDOUT = ROOT / "강의노트/공지사항/Breadboard.pdf"


class BoardExtraction(unittest.TestCase):
    def test_배포본에서_판형_래스터를_꺼낸다(self):
        board = hand_grid.board_image(HANDOUT)
        self.assertGreater(board.width, 400)
        self.assertGreater(board.height, 400)
        self.assertEqual(len(board.md5), 32)

    def test_없는_쪽을_부르면_거절한다(self):
        with self.assertRaises(hand_grid.GridError):
            hand_grid.board_image(HANDOUT, page_index=99)


class GridDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = hand_grid.board_image(HANDOUT)

    def test_열_28개와_행_63개를_찾는다(self):
        cols, rows = hand_grid.detect_grid(self.board.data)
        self.assertEqual(len(cols), 28)
        self.assertEqual(len(rows), 63)

    def test_검출된_열은_왼쪽에서_오른쪽_순이다(self):
        cols, _ = hand_grid.detect_grid(self.board.data)
        self.assertEqual(cols, sorted(cols))


class Fit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cal = hand_grid.calibrate(hand_grid.board_image(HANDOUT))

    def test_잔차가_3px_아래다(self):
        self.assertLess(self.cal.res_x, 3.0)
        self.assertLess(self.cal.res_y, 3.0)

    def test_렌더러_홀이_페이지_픽셀로_옮겨진다(self):
        mod = hand_grid.load_renderer()
        px, py = self.cal.to_px(239, mod.ROW0)   # 좌 a열 1행
        self.assertGreater(px, 0)
        self.assertGreater(py, 0)

    def test_좌표표를_렌더러에서_읽는다(self):
        """숫자를 베껴 적으면 한쪽만 고쳤을 때 갈린다."""
        cols = hand_grid._reference_cols(hand_grid.load_renderer())
        self.assertEqual(len(cols), 28)
        self.assertEqual(len(set(cols)), 28)

    def test_행_간격이_단조_증가한다(self):
        ys = [self.cal.to_px(0, hand_grid.load_renderer().ROW0 + i * 16.345)[1]
              for i in range(10)]
        self.assertEqual(ys, sorted(ys))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_grid.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.lab.hand_grid'`

- [ ] **Step 3: 렌더러가 템플릿 없이도 좌표표를 내주게 한다**

좌표를 베껴 적으면 한쪽만 고쳤을 때 갈린다. 렌더러에서 직접 읽어야 하는데
`__init__` 이 템플릿 이미지를 먼저 여는 탓에 좌표만 쓰려는 쪽이 쓸 수 없다.
`self.cols = {...}` 블록 전체를 `self._init_cols()` 한 줄로 바꾸고 메서드로 뽑는다.

```python
    def _init_cols(self):
        """열 좌표표. 템플릿 없이 좌표만 쓰려는 쪽(손그림 검토)이 있어
        `__init__` 에서 뽑아 놓는다. 이 표가 열 좌표의 **유일한 권위**다."""
        self.cols = {
            'left': {
                'gnd': 174, 'vcc': 190,
                'a': 239, 'b': 256, 'c': 272, 'd': 288, 'e': 305,
                'chip_x1': 310, 'chip_x2': 349,
                'f': 354, 'g': 370, 'h': 386, 'i': 403, 'j': 419,
                'mid_gnd': 468, 'mid_vcc': 484,
            },
            'right': {
                'mid_gnd': 542, 'mid_vcc': 558,
                'a': 607, 'b': 623, 'c': 640, 'd': 656, 'e': 672,
                'chip_x1': 677, 'chip_x2': 716,
                'f': 721, 'g': 738, 'h': 754, 'i': 770, 'j': 786,
                'gnd': 836, 'vcc': 852,
            },
        }
```

Run: `python3 -m pytest tests/test_breadboard_coords.py tests/test_breadboard_wiring.py -q`
Expected: PASS — 값이 그대로라 아무것도 안 깨져야 한다.

- [ ] **Step 4: 모듈을 쓴다**

`scripts/lab/hand_grid.py` 를 만든다.

```python
"""손그림 PDF 의 판형 좌표를 렌더러 좌표표에 맞춘다.

**사람이 좌표를 뜨지 않는다.** 배포본 판형은 정본 `Breadboard.jpg` 와 같은
그림인데 가로가 중앙 기준 5% 넓다 — `breadboard-diagram/SKILL.md` §2 가
"갈아끼우면 결선이 옆 홀에 그려지는데, 그림 자체는 멀쩡해 보여서 눈으로는 안
잡힌다"고 적어 둔 그 차이다. 눈대중 상수를 새로 만들면 같은 사고가 반복된다.

대신 이렇게 한다.

1. 손그림 PDF 의 각 쪽에는 판형 래스터가 **이미지로** 박혀 있고, 놓인 자리도
   PDF 안에 있다. 잉크가 없는 깨끗한 판형을 그대로 꺼낸다.
2. 그 래스터에서 홀 열·행을 검출한다.
3. 검출된 열 28개·행 63개를 렌더러의 `cols`·`r_y()` 에 순서대로 짝지어 축마다
   1차식을 맞춘다. 균일 가로 확대는 1차식이 정확히 흡수한다.
4. 잔차가 3px 를 넘으면 중단한다. 판형이 바뀐 것이다.

쪽 크기로 막지 않는 이유: 학생 PDF 는 필기 앱 내보내기라 1210x834pt 이고
배포본은 A4 594x841pt 다. 쪽 크기를 보면 정상 제출물을 거절한다. 기하를 본다.
"""

import hashlib
import importlib.util
import io
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERER = (REPO_ROOT / ".claude/skills/breadboard-diagram/scripts"
            / "render_breadboard.py")

# 판형 한 장에 있는 홀 열과 행. 렌더러 좌표표가 정하는 값이라 여기서 세지
# 않고 맞춰만 본다 — 검출이 이 수와 다르면 판형이 다른 것이다
EXPECTED_COLS = 28
EXPECTED_ROWS = 63

# 잔차 한계. 렌더러 `hole_at()` 의 홀 허용치가 5px 이므로 그보다 넉넉히 안쪽
MAX_RESIDUAL = 3.0

_renderer = None


class GridError(ValueError):
    """판형을 못 읽었거나 좌표가 안 맞는다."""


def load_renderer():
    """렌더러 모듈. 스킬 폴더 안에 있어 import 경로에 없다."""
    global _renderer
    if _renderer is None:
        spec = importlib.util.spec_from_file_location(
            "render_breadboard", str(RENDERER))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _renderer = mod
    return _renderer


@dataclass
class BoardImage:
    md5: str
    width: int
    height: int
    rect: tuple      # 쪽 안에서 놓인 자리 (x0, y0, x1, y1) — 포인트 단위
    data: bytes      # 원본 래스터 바이트


@dataclass
class Calibration:
    ax: float
    bx: float
    ay: float
    by: float
    res_x: float
    res_y: float
    rect: tuple
    board_size: tuple
    dpi: int

    def to_px(self, x, y):
        """렌더러 좌표 -> 그 쪽을 dpi 로 그렸을 때의 픽셀.

        렌더러 좌표 -> 판형 래스터 픽셀 -> 쪽 포인트 -> 렌더 픽셀 순으로 간다.
        """
        w, h = self.board_size
        x0, y0, x1, y1 = self.rect
        ix = self.ax * x + self.bx
        iy = self.ay * y + self.by
        pt_x = x0 + ix / w * (x1 - x0)
        pt_y = y0 + iy / h * (y1 - y0)
        s = self.dpi / 72.0
        return (pt_x * s, pt_y * s)


def board_image(pdf_path, page_index=0):
    """그 쪽에 깔린 판형 래스터와 놓인 자리.

    가장 넓게 깔린 이미지를 판형으로 본다. 학생이 사진을 덧붙였더라도 판형이
    쪽 대부분을 차지하기 때문이다.
    """
    import fitz

    doc = fitz.open(str(pdf_path))
    try:
        if not 0 <= page_index < len(doc):
            raise GridError(
                f"{Path(pdf_path).name} 에 {page_index + 1}쪽이 없다 "
                f"(전체 {len(doc)}쪽)")
        page = doc[page_index]
        best = None
        for img in page.get_images(full=True):
            xref = img[0]
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            r = max(rects, key=lambda rr: rr.width * rr.height)
            area = r.width * r.height
            if best is None or area > best[0]:
                best = (area, xref, r)
        if best is None:
            raise GridError(
                f"{Path(pdf_path).name} {page_index + 1}쪽에 판형 이미지가 없다. "
                "배포본 판형 위에 그린 PDF 만 검토한다")
        _, xref, rect = best
        info = doc.extract_image(xref)
        return BoardImage(
            md5=hashlib.md5(info["image"]).hexdigest(),
            width=info["width"], height=info["height"],
            rect=(rect.x0, rect.y0, rect.x1, rect.y1),
            data=info["image"])
    finally:
        doc.close()


def _runs(profile, threshold):
    """문턱을 넘는 구간들의 (시작, 끝) 목록."""
    out, i, n = [], 0, len(profile)
    while i < n:
        if profile[i] >= threshold:
            j = i
            while j < n and profile[j] >= threshold:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _merge_to_count(runs, expected):
    """이웃한 구간을 붙여 개수가 `expected` 가 되는 중심 목록.

    홀은 **작은 사각 테두리**로 그려져 있어 구간이 홀마다 둘씩(왼쪽 변,
    오른쪽 변) 나온다. 붙이는 간격을 0 부터 키우면서 개수가 맞는 지점을
    찾는다 — 결과가 결정적이고, 못 맞추면 소리를 낸다.
    """
    if not runs:
        raise GridError("홀을 하나도 못 찾았다")
    span = runs[-1][1] - runs[0][0]
    for gap in range(0, max(2, int(span / expected)) + 2):
        merged, cur = [], list(runs[0])
        for a, b in runs[1:]:
            if a - cur[1] <= gap:
                cur[1] = b
            else:
                merged.append(tuple(cur))
                cur = [a, b]
        merged.append(tuple(cur))
        if len(merged) == expected:
            return [(a + b) / 2.0 for a, b in merged]
    raise GridError(
        f"홀 {expected}개로 정리되지 않는다 (구간 {len(runs)}개). "
        "판형이 바뀌었거나 해상도가 모자란다")


def detect_grid(data):
    """판형 래스터에서 홀 열 중심 x 들과 행 중심 y 들.

    잉크가 없는 원본 래스터를 본다 — 학생 필기는 PDF 의 다른 층에 있다.
    """
    from PIL import Image

    im = Image.open(io.BytesIO(data)).convert("L")
    w, h = im.size
    px = im.load()
    # 위쪽 전원 잭 영역과 아래 여백을 뺀 몸통만 본다
    y0, y1 = int(h * 0.15), int(h * 0.97)
    x0, x1 = int(w * 0.02), int(w * 0.98)

    col_prof = [sum(1 for y in range(y0, y1) if px[x, y] < 140)
                for x in range(w)]
    row_prof = [sum(1 for x in range(x0, x1) if px[x, y] < 140)
                for y in range(h)]

    cols = _merge_to_count(_runs(col_prof, max(col_prof) * 0.35), EXPECTED_COLS)
    rows = _merge_to_count(_runs(row_prof[y0:y1], max(row_prof[y0:y1]) * 0.35),
                           EXPECTED_ROWS)
    return cols, [y + y0 for y in rows]


def _fit(src, dst):
    """dst = a*src + b 최소제곱. (a, b, 최대 잔차) 를 준다."""
    n = len(src)
    ms, md = sum(src) / n, sum(dst) / n
    num = sum((s - ms) * (d - md) for s, d in zip(src, dst))
    den = sum((s - ms) ** 2 for s in src)
    if den == 0:
        raise GridError("맞출 좌표가 한 점뿐이다")
    a = num / den
    b = md - a * ms
    res = max(abs(a * s + b - d) for s, d in zip(src, dst))
    return a, b, res


def calibrate(board, dpi=300):
    """검출한 격자를 렌더러 좌표표에 맞춘다."""
    mod = load_renderer()
    cols, rows = detect_grid(board.data)

    ref_cols = sorted(_reference_cols(mod))
    ref_rows = [mod.ROW0 + (r - 1) * mod.ROW_PITCH for r in range(1, mod.ROW_MAX + 1)]

    ax, bx, res_x = _fit(ref_cols, cols)
    ay, by, res_y = _fit(ref_rows, rows)
    if res_x > MAX_RESIDUAL or res_y > MAX_RESIDUAL:
        raise GridError(
            f"판형이 렌더러 좌표표와 맞지 않는다 "
            f"(가로 잔차 {res_x:.1f}px, 세로 {res_y:.1f}px, 한계 {MAX_RESIDUAL}). "
            "다른 판형 위에 그렸거나 판형이 바뀌었다")
    return Calibration(ax, bx, ay, by, res_x, res_y,
                       board.rect, (board.width, board.height), dpi)


def _reference_cols(mod):
    """렌더러가 아는 열 x 들. 칩 몸통 경계(`chip_x1`·`chip_x2`)는 홀이 아니다.

    숫자를 베껴 적지 않는다 — 렌더러 `cols` 가 유일한 권위다. 템플릿 이미지를
    열지 않으려고 `__new__` 로 껍데기만 만들고 좌표표만 채운다.
    """
    bb = mod.BreadboardRenderer.__new__(mod.BreadboardRenderer)
    mod.BreadboardRenderer._init_cols(bb)
    out = []
    for block in bb.cols.values():
        out.extend(x for key, x in block.items() if not key.startswith('chip'))
    return out
```

- [ ] **Step 5: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_grid.py -q`
Expected: PASS (8 tests)

검출이 28/63 으로 안 모이면 `_merge_to_count` 가 개수를 그대로 알려 준다. 문턱(`0.35`)을 0.25~0.5 사이에서 조정하되, **테스트가 요구하는 개수를 맞추려고 `EXPECTED_*` 를 바꾸지 않는다** — 판형의 홀 수는 사실이다.

- [ ] **Step 6: 렌더러 테스트가 안 깨졌는지 본다**

Run: `python3 -m pytest tests/test_breadboard_coords.py tests/test_breadboard_wiring.py -q`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add scripts/lab/hand_grid.py tests/test_hand_grid.py .claude/skills/breadboard-diagram/scripts/render_breadboard.py
git commit -m "feat: 손그림 판형을 렌더러 좌표표에 1차식으로 맞춘다"
```

---

### Task 3: 격자 오버레이와 크롭

**Files:**
- Modify: `scripts/lab/hand_grid.py`
- Test: `tests/test_hand_grid.py`

**Interfaces:**
- Consumes: Task 2 의 `Calibration`, `board_image`, `load_renderer`
- Produces:
  - `render_page(pdf_path, page_index, dpi=300) -> PIL.Image.Image`
  - `overlay_grid(page_im, cal, out_path) -> str`
  - `crop_rows(page_im, cal, row_from, row_to, out_path, scale=3) -> str`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_grid.py` 에 클래스를 더한다.

```python
class Overlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = hand_grid.board_image(HANDOUT)
        cls.cal = hand_grid.calibrate(cls.board)
        cls.page = hand_grid.render_page(HANDOUT, 0)

    def test_쪽을_300dpi_로_그린다(self):
        # A4 세로 594.75x841.5pt -> 300dpi 면 약 2478x3506
        self.assertGreater(self.page.width, 2000)
        self.assertGreater(self.page.height, 3000)

    def test_격자를_덮은_그림이_원본과_크기가_같다(self):
        import tempfile
        from PIL import Image
        out = os.path.join(tempfile.mkdtemp(), 'grid.png')
        hand_grid.overlay_grid(self.page, self.cal, out)
        self.assertEqual(Image.open(out).size, self.page.size)

    def test_크롭은_요청한_행_범위만큼_잘라_확대한다(self):
        import tempfile
        from PIL import Image
        out = os.path.join(tempfile.mkdtemp(), 'crop.png')
        hand_grid.crop_rows(self.page, self.cal, 10, 20, out, scale=2)
        im = Image.open(out)
        self.assertGreater(im.width, 0)
        self.assertGreater(im.height, 0)

    def test_거꾸로_된_행_범위는_거절한다(self):
        import tempfile
        out = os.path.join(tempfile.mkdtemp(), 'x.png')
        with self.assertRaises(hand_grid.GridError):
            hand_grid.crop_rows(self.page, self.cal, 20, 10, out)
```

`tests/test_hand_grid.py` 맨 위에 `import os` 를 더한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_grid.py::Overlay -q`
Expected: FAIL — `AttributeError: module 'scripts.lab.hand_grid' has no attribute 'render_page'`

- [ ] **Step 3: 세 함수를 더한다**

`hand_grid.py` 끝에 붙인다.

```python
# 오버레이 색. 격자선은 **읽는 보조선**이지 판정 근거가 아니다 — 손그림 잉크
# (빨강·파랑·검정·초록)와 겹치지 않는 자홍/하늘로 골라 눈이 헷갈리지 않게 한다
GRID_ROW = (255, 0, 255, 70)
GRID_COL = (0, 160, 255, 60)
GRID_TEXT_ROW = (200, 0, 200, 255)
GRID_TEXT_COL = (0, 90, 200, 255)


def render_page(pdf_path, page_index=0, dpi=300):
    """그 쪽을 dpi 로 그린 이미지."""
    import fitz
    from PIL import Image

    doc = fitz.open(str(pdf_path))
    try:
        if not 0 <= page_index < len(doc):
            raise GridError(
                f"{Path(pdf_path).name} 에 {page_index + 1}쪽이 없다 "
                f"(전체 {len(doc)}쪽)")
        pix = doc[page_index].get_pixmap(dpi=dpi)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


def _col_names(mod):
    """(블록, 열) -> 렌더러 x. 오버레이 라벨과 크롭이 함께 쓴다."""
    bb = mod.BreadboardRenderer.__new__(mod.BreadboardRenderer)
    mod.BreadboardRenderer._init_cols(bb)
    out = {}
    for block, cols in bb.cols.items():
        for key, x in cols.items():
            if not key.startswith('chip'):
                out[(block, key)] = x
    return out


_SHORT = {'gnd': 'G-', 'vcc': 'V+', 'mid_gnd': 'g-', 'mid_vcc': 'v+'}


def overlay_grid(page_im, cal, out_path, max_row=35):
    """행 번호·열 이름·레일 빈 행을 반투명으로 덮은 그림.

    Claude 가 끝점을 읽는 **보조선**이다. 사람이 눈금을 세지 않게 하려고
    있는 것이지, 이 그림으로 판정하지 않는다 — 판정은 전사 파일로 한다.
    """
    from PIL import Image, ImageDraw, ImageFont

    mod = load_renderer()
    im = page_im.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 20)
    except OSError:
        font = ImageFont.load_default()

    names = _col_names(mod)
    xs = [cal.to_px(x, mod.ROW0)[0] for x in names.values()]
    x_lo, x_hi = min(xs), max(xs)

    for r in range(1, min(max_row, mod.ROW_MAX) + 1):
        y = cal.to_px(0, mod.ROW0 + (r - 1) * mod.ROW_PITCH)[1]
        d.line([(x_lo - 60, y), (x_hi + 20, y)], fill=GRID_ROW, width=1)
        label = f'{r} gap' if r in mod.RAIL_GAP_ROWS else str(r)
        d.text((x_lo - 58, y - 10), label, fill=GRID_TEXT_ROW, font=font)

    y_top = cal.to_px(0, mod.ROW0)[1]
    y_bot = cal.to_px(0, mod.ROW0 + (min(max_row, mod.ROW_MAX) - 1)
                      * mod.ROW_PITCH)[1]
    for (block, key), x in names.items():
        px = cal.to_px(x, mod.ROW0)[0]
        d.line([(px, y_top - 30), (px, y_bot)], fill=GRID_COL, width=1)
        tag = _SHORT.get(key, key)
        prefix = '좌' if block == 'left' else '우'
        d.text((px - 9, y_top - 52), f'{prefix}{tag}',
               fill=GRID_TEXT_COL, font=font)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    Image.alpha_composite(im, ov).convert("RGB").save(out_path)
    return out_path


def crop_rows(page_im, cal, row_from, row_to, out_path, scale=3, block=None):
    """행 범위를 잘라 확대한다. 치명 결함의 증거로 쓴다."""
    from PIL import Image

    if row_to <= row_from:
        raise GridError(f"행 범위가 거꾸로다: {row_from} -> {row_to}")
    mod = load_renderer()
    names = _col_names(mod)
    if block:
        names = {k: v for k, v in names.items() if k[0] == block}
    xs = [cal.to_px(x, mod.ROW0)[0] for x in names.values()]
    y0 = cal.to_px(0, mod.ROW0 + (row_from - 1) * mod.ROW_PITCH)[1]
    y1 = cal.to_px(0, mod.ROW0 + (row_to - 1) * mod.ROW_PITCH)[1]
    box = (max(0, int(min(xs) - 80)), max(0, int(y0 - 20)),
           min(page_im.width, int(max(xs) + 40)),
           min(page_im.height, int(y1 + 20)))
    c = page_im.crop(box)
    c = c.resize((c.width * scale, c.height * scale), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    c.save(out_path)
    return out_path
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_grid.py -q`
Expected: PASS (12 tests)

- [ ] **Step 5: 눈으로 한 번 본다**

```bash
python3 -c "
from scripts.lab import hand_grid
b = hand_grid.board_image('강의노트/공지사항/Breadboard.pdf')
cal = hand_grid.calibrate(b)
page = hand_grid.render_page('강의노트/공지사항/Breadboard.pdf')
print(hand_grid.overlay_grid(page, cal, '/tmp/격자확인.png'))
print('잔차', round(cal.res_x,2), round(cal.res_y,2))
"
```
`/tmp/격자확인.png` 를 열어 **자홍 가로선이 홀 한가운데를 지나는지** 본다. 어긋나면 잔차 수치가 작아도 짝짓기가 밀린 것이니 `detect_grid` 의 몸통 범위(`0.15`/`0.97`)를 손본다.

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/hand_grid.py tests/test_hand_grid.py
git commit -m "feat: 손그림 쪽에 홀 격자를 덮고 행 범위를 크롭한다"
```

---

### Task 4: 전사 문법과 `Diagram`

**Files:**
- Create: `scripts/lab/hand_transcript.py`
- Test: `tests/test_hand_transcript.py`

**Interfaces:**
- Consumes: Task 2 의 `hand_grid.load_renderer`
- Produces:
  - `Diagram` dataclass — 필드 `chips, wires, leds, resistors, chains, unused_inputs, unused_outputs, bridges, overlaps, uncertain, title, circuit, signed, page`
  - `chip_pins(block, pin1_row) -> dict[int, (block, col, row)]`
  - `parse_address(text) -> ('hole', (block, col, row)) | ('jack', color)`
  - `parse_transcript(path) -> Diagram`
  - `TranscriptError(ValueError)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_transcript.py` 를 만든다.

```python
"""전사 파일의 문법과 그것이 만드는 `Diagram` 을 검사한다.

주소는 렌더러 `addr()` 이 내는 말과 **똑같이** 쓴다 ('좌 b10',
'좌 GND레일10행'). 양쪽이 다른 말을 쓰면 비교 자체가 성립하지 않는다.
"""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.lab import hand_transcript as ht


def _write(obj):
    p = Path(tempfile.mkdtemp()) / "p3.json"
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return p


MINIMAL = {
    "page": 3, "circuit": "e1_nand", "title": "2-1 NAND Gate", "signed": False,
    "chips": [{"label": "74HC08", "block": "left", "pin1_row": 7}],
    "wires": [{"color": "빨강", "from": "좌 g7", "to": "좌 중앙VCC레일7행"}],
    "leds": [{"tag": "L1", "anode": "좌 c14", "cathode": "좌 c15"}],
    "resistors": [{"tag": "L1", "top": "좌 d15", "bottom": "좌 d17"}],
    "uncertain": [],
}


class Address(unittest.TestCase):
    def test_단자대_주소를_읽는다(self):
        self.assertEqual(ht.parse_address("좌 b10"), ('hole', ('left', 'b', 10)))
        self.assertEqual(ht.parse_address("우 j15"), ('hole', ('right', 'j', 15)))

    def test_레일_주소를_읽는다(self):
        self.assertEqual(ht.parse_address("좌 GND레일10행"),
                         ('hole', ('left', 'gnd', 10)))
        self.assertEqual(ht.parse_address("좌 중앙VCC레일7행"),
                         ('hole', ('left', 'mid_vcc', 7)))
        self.assertEqual(ht.parse_address("우 중앙GND레일29행"),
                         ('hole', ('right', 'mid_gnd', 29)))

    def test_전원잭을_읽는다(self):
        self.assertEqual(ht.parse_address("전원잭(빨강)"), ('jack', 'red'))
        self.assertEqual(ht.parse_address("전원잭(회색)"), ('jack', 'gray'))

    def test_렌더러가_내는_주소를_그대로_읽는다(self):
        """`addr()` 출력과 문법이 갈리면 비교가 성립하지 않는다."""
        from scripts.lab.hand_grid import load_renderer
        mod = load_renderer()
        bb = mod.BreadboardRenderer()
        c = bb.cols['left']
        for x, row in [(c['b'], 10), (c['gnd'], 10), (c['mid_vcc'], 7)]:
            got = ht.parse_address(bb.addr(x, bb.r_y(row)))
            self.assertEqual(got, ('hole', bb.sym(x, row)))

    def test_모르는_주소는_거절한다(self):
        for bad in ["보드밖(입력)", "분기점", "좌 k10", "가운데 b10", "좌 b0"]:
            with self.assertRaises(ht.TranscriptError, msg=bad):
                ht.parse_address(bad)


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


class Parse(unittest.TestCase):
    def test_최소_전사를_읽는다(self):
        d = ht.parse_transcript(_write(MINIMAL))
        self.assertEqual(d.circuit, "e1_nand")
        self.assertEqual(d.page, 3)
        self.assertFalse(d.signed)
        self.assertEqual(len(d.wires), 1)
        self.assertEqual(d.chips[0]['pins'][1], ('left', 'e', 7))

    def test_LED_와_저항을_꼬리표로_묶어_사슬을_만든다(self):
        d = ht.parse_transcript(_write(MINIMAL))
        self.assertEqual(len(d.chains), 1)
        ch = d.chains[0]
        self.assertEqual(ch['tag'], 'L1')
        self.assertEqual(ch['cathode'], ('left', 'c', 15))
        self.assertEqual(ch['res_top'], ('left', 'd', 15))
        self.assertEqual(ch['res_bottom'], ('left', 'd', 17))

    def test_짝_없는_저항은_거절한다(self):
        obj = json.loads(json.dumps(MINIMAL))
        obj['resistors'][0]['tag'] = 'L9'
        with self.assertRaisesRegex(ht.TranscriptError, 'L9'):
            ht.parse_transcript(_write(obj))

    def test_uncertain_은_주소로_보관된다(self):
        obj = json.loads(json.dumps(MINIMAL))
        obj['uncertain'] = ["좌 d17"]
        d = ht.parse_transcript(_write(obj))
        self.assertEqual(d.uncertain, {('left', 'd', 17)})

    def test_필수_열쇠가_없으면_거절한다(self):
        obj = json.loads(json.dumps(MINIMAL))
        del obj['circuit']
        with self.assertRaisesRegex(ht.TranscriptError, 'circuit'):
            ht.parse_transcript(_write(obj))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_transcript.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.lab.hand_transcript'`

- [ ] **Step 3: 모듈을 쓴다**

`scripts/lab/hand_transcript.py` 를 만든다.

```python
"""손그림 전사 파일을 읽어 `Diagram` 으로 만든다.

전사는 **사람(vision)이 적는다.** 선 끝점 추출을 자동화하지 않는 이유는 검정이
신호선·칩 글자·저항 지그재그를 전부 겸해서 색 분할이 되지 않기 때문이다.
대신 읽은 결과를 파일로 남긴다 — 재검토 때 무엇을 잘못 읽었는지 짚을 수 있다.

주소 문법은 렌더러 `addr()` 출력과 **같은 말**이다 ('좌 b10',
'좌 GND레일10행'). 양쪽을 같은 말로 맞춰야 비교가 된다. 렌더러가 '보드밖(입력)'
이나 '분기점' 을 낼 수도 있는데 그건 홀이 아니므로 전사에서는 거절한다.

JSON 을 쓴다. `requirements-dev.txt` 에 PyYAML 이 없고 `scripts/lab/` 은 표준
라이브러리만 쓴다는 정책이 그 파일에 적혀 있다.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TERMINAL_COLS = tuple('abcdefghij')
RAIL_NAMES = {
    'GND레일': 'gnd', 'VCC레일': 'vcc',
    '중앙GND레일': 'mid_gnd', '중앙VCC레일': 'mid_vcc',
}
BLOCKS = {'좌': 'left', '우': 'right'}
JACK_COLORS = {'빨강': 'red', '노랑': 'yellow', '회색': 'gray'}
ROW_MIN, ROW_MAX = 1, 63

_TERMINAL = re.compile(r'^(좌|우)\s+([a-j])(\d{1,2})$')
_RAIL = re.compile(r'^(좌|우)\s+(중앙GND레일|중앙VCC레일|GND레일|VCC레일)(\d{1,2})행$')
_JACK = re.compile(r'^전원잭\((빨강|노랑|회색)\)$')

REQUIRED_KEYS = ('page', 'circuit', 'chips', 'wires')


class TranscriptError(ValueError):
    """전사 파일을 읽을 수 없다."""


@dataclass
class Diagram:
    """한 쪽의 결선. 손그림과 참조가 **같은 모양**으로 담긴다."""
    chips: list = field(default_factory=list)
    wires: list = field(default_factory=list)
    leds: list = field(default_factory=list)
    resistors: list = field(default_factory=list)
    chains: list = field(default_factory=list)
    unused_inputs: list = field(default_factory=list)
    unused_outputs: list = field(default_factory=list)
    bridges: list = field(default_factory=list)
    overlaps: list = field(default_factory=list)
    uncertain: set = field(default_factory=set)
    title: str = ""
    circuit: str = ""
    signed: bool = False
    page: int = 0


def chip_pins(block, pin1_row):
    """DIP-14 가 꽂히는 홀. pin 1~7 은 e 열, pin 8~14 는 f 열.

    `draw_chip()` 이 실제로 꽂는 자리와 같아야 한다 —
    `test_핀_배치가_렌더러와_같다` 가 그것을 묶어 둔다.
    """
    pins = {}
    for i in range(7):
        pins[i + 1] = (block, 'e', pin1_row + i)
        pins[14 - i] = (block, 'f', pin1_row + i)
    return pins


def parse_address(text):
    """'좌 b10' -> ('hole', ('left', 'b', 10)). 홀이 아니면 거절한다."""
    s = (text or "").strip()
    m = _JACK.match(s)
    if m:
        return ('jack', JACK_COLORS[m.group(1)])
    m = _TERMINAL.match(s)
    if m:
        row = int(m.group(3))
        _check_row(row, s)
        return ('hole', (BLOCKS[m.group(1)], m.group(2), row))
    m = _RAIL.match(s)
    if m:
        row = int(m.group(3))
        _check_row(row, s)
        return ('hole', (BLOCKS[m.group(1)], RAIL_NAMES[m.group(2)], row))
    raise TranscriptError(
        f"홀 주소로 읽을 수 없다: {s!r} — "
        "'좌 b10' · '좌 GND레일10행' · '전원잭(빨강)' 꼴로 적는다")


def _check_row(row, s):
    if not ROW_MIN <= row <= ROW_MAX:
        raise TranscriptError(f"{ROW_MIN}~{ROW_MAX}행 밖이다: {s!r}")


def parse_transcript(path):
    """전사 JSON -> `Diagram`."""
    path = Path(path)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise TranscriptError(f"{path.name} 을 읽을 수 없다: {e}") from e

    missing = [k for k in REQUIRED_KEYS if k not in obj]
    if missing:
        raise TranscriptError(
            f"{path.name} 에 {', '.join(missing)} 이(가) 없다")

    chips = []
    for ch in obj['chips']:
        block = BLOCKS.get(ch.get('block'), ch.get('block'))
        if block not in ('left', 'right'):
            raise TranscriptError(f"블록이 좌/우가 아니다: {ch.get('block')!r}")
        row = int(ch['pin1_row'])
        _check_row(row, f"{ch.get('label')} pin1_row={row}")
        chips.append({'label': ch['label'], 'block': block,
                      'pin1_row': row, 'pins': chip_pins(block, row)})

    wires = [{'kind': w.get('color', ''), 'desc': w.get('desc', ''),
              'frm': parse_address(w['from']), 'to': parse_address(w['to'])}
             for w in obj['wires']]

    leds = [{'tag': l['tag'],
             'anode': parse_address(l['anode'])[1],
             'cathode': parse_address(l['cathode'])[1]}
            for l in obj.get('leds', [])]
    resistors = [{'tag': r.get('tag', ''), 'label': r.get('label', '330Ω'),
                  'top': parse_address(r['top'])[1],
                  'bottom': parse_address(r['bottom'])[1]}
                 for r in obj.get('resistors', [])]

    by_tag = {l['tag']: l for l in leds}
    chains = []
    for r in resistors:
        led = by_tag.get(r['tag'])
        if led is None:
            raise TranscriptError(
                f"저항 꼬리표 {r['tag']!r} 에 맞는 LED 가 없다. "
                "LED 와 저항은 같은 꼬리표로 묶는다")
        chains.append({'tag': r['tag'], 'anode': led['anode'],
                       'cathode': led['cathode'],
                       'res_top': r['top'], 'res_bottom': r['bottom']})

    bridges = []
    for b in obj.get('bridges', []):
        a = parse_address(b['from'])[1]
        z = parse_address(b['to'])[1]
        bridges.append((b.get('kind', ''), a, z))

    uncertain = {parse_address(u)[1] for u in obj.get('uncertain', [])}

    return Diagram(chips=chips, wires=wires, leds=leds, resistors=resistors,
                   chains=chains, bridges=bridges, uncertain=uncertain,
                   title=obj.get('title', ''), circuit=obj['circuit'],
                   signed=bool(obj.get('signed', False)),
                   page=int(obj['page']))
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_transcript.py -q`
Expected: PASS (12 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/hand_transcript.py tests/test_hand_transcript.py
git commit -m "feat: 손그림 전사 문법을 렌더러 주소와 같은 말로 맞춘다"
```

---

### Task 5: 넷 모델과 핀 서명

**Files:**
- Create: `scripts/lab/hand_compare.py`
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: Task 4 의 `Diagram`, `hand_transcript.parse_address`
- Produces:
  - `node_of(hole) -> tuple`
  - `build_nets(diagram) -> dict[node, node]` (대표 노드로의 사상)
  - `attachments(diagram) -> dict[node, set]`
  - `chip_key(diagram, index) -> str` — 종류로 맺고 중복은 `#2`
  - `signatures(diagram) -> dict[(chip_key, pin), frozenset]`
  - `RAIL_COLS`, `VCC_COLS`, `GND_COLS`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_compare.py` 를 만든다.

```python
"""넷 모델과 규칙 13개를 검사한다.

**홀 좌표가 아니라 넷으로 비교한다.** 칩이 참조보다 한 행 위에 있어도 주변
배선이 같이 옮겨져 있으면 그림은 유효하다 — 2026-09-08 손그림 세 쪽이 전부
그랬다. `regen_compare` 가 결선도를 간선 집합으로 보는 것과 같은 이유다.

살아 있는 실험01 참조 결선도를 한 군데씩 망가뜨려 검사기가 그 자리를 짚는지
본다. 합성 픽스처로는 실물에서만 나오는 배치를 못 밟는다.
"""
import unittest

from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import Diagram


def _wire(a, b, kind='sig'):
    return {'kind': kind, 'desc': '', 'frm': ('hole', a), 'to': ('hole', b)}


class Nodes(unittest.TestCase):
    def test_같은_행_a부터e_는_한_노드다(self):
        self.assertEqual(hc.node_of(('left', 'a', 10)),
                         hc.node_of(('left', 'e', 10)))

    def test_같은_행이라도_f부터j_는_다른_노드다(self):
        self.assertNotEqual(hc.node_of(('left', 'a', 10)),
                            hc.node_of(('left', 'f', 10)))

    def test_레일은_행을_무시한다(self):
        self.assertEqual(hc.node_of(('left', 'gnd', 3)),
                         hc.node_of(('left', 'gnd', 40)))

    def test_좌우_중앙레일은_서로_다른_도체다(self):
        self.assertNotEqual(hc.node_of(('left', 'mid_gnd', 10)),
                            hc.node_of(('right', 'mid_gnd', 10)))


class Nets(unittest.TestCase):
    def test_점퍼가_두_스트립을_잇는다(self):
        d = Diagram(wires=[_wire(('left', 'a', 10), ('left', 'a', 20))])
        nets = hc.build_nets(d)
        self.assertEqual(nets[hc.node_of(('left', 'c', 10))],
                         nets[hc.node_of(('left', 'e', 20))])

    def test_LED_는_스트립을_잇지_않는다(self):
        d = Diagram(leds=[{'tag': 'L1', 'anode': ('left', 'c', 14),
                           'cathode': ('left', 'c', 15)}])
        nets = hc.build_nets(d)
        self.assertNotEqual(nets[hc.node_of(('left', 'c', 14))],
                            nets[hc.node_of(('left', 'c', 15))])


class Signatures(unittest.TestCase):
    def _chip(self, row=10, label='74HC08'):
        from scripts.lab.hand_transcript import chip_pins
        return {'label': label, 'block': 'left', 'pin1_row': row,
                'pins': chip_pins('left', row)}

    def test_pin14_가_VCC_레일에_닿으면_서명에_VCC_가_있다(self):
        d = Diagram(chips=[self._chip()],
                    wires=[_wire(('left', 'g', 10), ('left', 'mid_vcc', 10), 'vcc')])
        sig = hc.signatures(d)
        self.assertIn(('RAIL', 'VCC'), sig[('74HC08', 14)])
        self.assertNotIn(('RAIL', 'GND'), sig[('74HC08', 14)])

    def test_레일_이름이_아니라_극성만_서명에_들어간다(self):
        """좌 GND 로 내렸든 중앙 GND 로 내렸든 같은 뜻이다 — 브리지 유무는
        H8 이 따로 본다. 한 결함을 두 번 보고하지 않는다."""
        a = Diagram(chips=[self._chip()],
                    wires=[_wire(('left', 'd', 16), ('left', 'gnd', 16), 'gnd')])
        b = Diagram(chips=[self._chip()],
                    wires=[_wire(('left', 'd', 16), ('left', 'mid_gnd', 16), 'gnd')])
        self.assertEqual(hc.signatures(a)[('74HC08', 7)],
                         hc.signatures(b)[('74HC08', 7)])

    def test_행이_통째로_밀려도_서명은_같다(self):
        """칩과 배선이 함께 옮겨지면 유효한 그림이다."""
        a = Diagram(chips=[self._chip(10)],
                    wires=[_wire(('left', 'g', 10), ('left', 'mid_vcc', 10), 'vcc')])
        b = Diagram(chips=[self._chip(9)],
                    wires=[_wire(('left', 'g', 9), ('left', 'mid_vcc', 9), 'vcc')])
        self.assertEqual(hc.signatures(a)[('74HC08', 14)],
                         hc.signatures(b)[('74HC08', 14)])

    def test_같은_종류_칩_둘이면_둘째에_샵2_가_붙는다(self):
        d = Diagram(chips=[self._chip(7, '74HC04'), self._chip(18, '74HC04')])
        keys = {k for k, _ in hc.signatures(d)}
        self.assertEqual(keys, {'74HC04', '74HC04#2'})

    def test_LED_애노드가_핀_서명에_들어간다(self):
        d = Diagram(chips=[self._chip()],
                    leds=[{'tag': 'L2', 'anode': ('left', 'c', 15),
                           'cathode': ('left', 'c', 16)}],
                    wires=[_wire(('left', 'd', 15), ('left', 'c', 15))])
        self.assertIn(('LED', 'L2', 'A'), hc.signatures(d)[('74HC08', 6)])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.lab.hand_compare'`

- [ ] **Step 3: 넷 모델을 쓴다**

`scripts/lab/hand_compare.py` 를 만든다.

```python
"""손그림 결선도를 참조와 대조한다.

**홀 좌표가 아니라 넷으로 본다.** 칩이 참조보다 한 행 위에 놓여도 주변 배선이
같이 옮겨져 있으면 그림은 유효하다 — 2026-09-08 손그림 세 쪽이 전부 그랬다.
좌표를 직접 비교하면 멀쩡한 그림을 오답으로 찍는다. `regen_compare` 가 결선도
명세를 간선 집합으로 보는 것과 같은 이유다.

모델:

- **노드** — 단자대 스트립 `('T', 블록, 행, 반쪽)` 과 전원 레일
  `('R', 블록, 열)`. 레일은 행을 무시한다(한 도체다). 잭은 `('J', 색)`.
- **간선** — 배선(점퍼)만. LED·저항·칩 핀은 노드를 잇지 **않는다**. 부품이지
  단락이 아니다. 이걸 섞으면 LED 양끝이 한 넷이 되어 사슬 검사가 통째로 무의미해진다.
- **부착물** — 그 노드에 붙은 것. 핀·LED 다리·저항 다리·잭, 그리고 레일 극성.
- **핀 서명** — 그 핀이 속한 넷의 부착물 집합. 비교 단위다.

레일은 **극성으로만** 서명에 넣는다. 좌 GND 로 내렸든 중앙 GND 로 내렸든 같은
뜻이고, 브리지가 있으면 한 넷이다. 브리지 유무는 H8 이 따로 본다 — 한 결함을
두 번 보고하지 않기 위해서다.
"""

from dataclasses import dataclass

RAIL_COLS = frozenset({'gnd', 'vcc', 'mid_gnd', 'mid_vcc'})
VCC_COLS = frozenset({'vcc', 'mid_vcc'})
GND_COLS = frozenset({'gnd', 'mid_gnd'})
LEFT_HALF = frozenset('abcde')

GRADES = ('치명', '기능', '표기', '보류')


@dataclass
class HandFinding:
    rule: str      # 'H1' ~ 'H13'
    grade: str     # 치명 | 기능 | 표기 | 보류
    where: str
    message: str

    def __str__(self):
        return f"[{self.grade}] {self.rule} {self.where} — {self.message}"


def node_of(hole):
    """홀 -> 노드. 같은 행 a~e 는 한 노드, f~j 는 다른 한 노드."""
    block, col, row = hole
    if col in RAIL_COLS:
        return ('R', block, col)
    return ('T', block, row, 'L' if col in LEFT_HALF else 'R')


def _endpoint_node(ep):
    kind, val = ep
    return ('J', val) if kind == 'jack' else node_of(val)


class _UF(dict):
    def find(self, k):
        self.setdefault(k, k)
        while self[k] != k:
            self[k] = self[self[k]]
            k = self[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self[rb] = ra


def build_nets(diagram):
    """노드 -> 대표 노드. 배선만 잇는다."""
    uf = _UF()
    for hole in _all_holes(diagram):
        uf.find(node_of(hole))
    for w in diagram.wires:
        uf.union(_endpoint_node(w['frm']), _endpoint_node(w['to']))
    for _kind, a, b in diagram.bridges:
        uf.union(node_of(a), node_of(b))
    return {k: uf.find(k) for k in list(uf)}


def _all_holes(diagram):
    for ch in diagram.chips:
        yield from ch['pins'].values()
    for w in diagram.wires:
        for ep in (w['frm'], w['to']):
            if ep[0] == 'hole' and ep[1] is not None:
                yield ep[1]
    for l in diagram.leds:
        yield l['anode']
        yield l['cathode']
    for r in diagram.resistors:
        yield r['top']
        yield r['bottom']
    for _k, a, b in diagram.bridges:
        yield a
        yield b


def chip_keys(diagram):
    """칩 순서 -> 이름. 종류로 맺고 같은 종류가 둘이면 둘째부터 '#2'."""
    seen, out = {}, []
    for ch in diagram.chips:
        label = ch['label']
        seen[label] = seen.get(label, 0) + 1
        out.append(label if seen[label] == 1 else f"{label}#{seen[label]}")
    return out


def attachments(diagram, nets=None):
    """대표 노드 -> 그 넷에 붙은 것들."""
    nets = nets if nets is not None else build_nets(diagram)
    out = {}

    def add(node, item):
        out.setdefault(nets.get(node, node), set()).add(item)

    for key, ch in zip(chip_keys(diagram), diagram.chips):
        for pin, hole in ch['pins'].items():
            add(node_of(hole), ('PIN', key, pin))
    for l in diagram.leds:
        add(node_of(l['anode']), ('LED', l['tag'], 'A'))
        add(node_of(l['cathode']), ('LED', l['tag'], 'K'))
    for r in diagram.resistors:
        add(node_of(r['top']), ('RES', r.get('tag', ''), 'T'))
        add(node_of(r['bottom']), ('RES', r.get('tag', ''), 'B'))
    for w in diagram.wires:
        for ep in (w['frm'], w['to']):
            if ep[0] == 'jack':
                add(('J', ep[1]), ('JACK', ep[1]))
    # 레일 극성. 레일 이름이 아니라 극성만 — 좌·중앙 어느 쪽인지는 저작자
    # 선택이고 브리지가 있으면 같은 넷이다
    for node in list(nets):
        if node[0] == 'R':
            pol = 'VCC' if node[2] in VCC_COLS else 'GND'
            add(node, ('RAIL', pol))
    return out


def signatures(diagram):
    """(칩 이름, 핀 번호) -> 그 핀 넷의 부착물. 자기 자신은 뺀다."""
    nets = build_nets(diagram)
    att = attachments(diagram, nets)
    out = {}
    for key, ch in zip(chip_keys(diagram), diagram.chips):
        for pin, hole in ch['pins'].items():
            rep = nets[node_of(hole)]
            out[(key, pin)] = frozenset(att.get(rep, set()) - {('PIN', key, pin)})
    return out
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (11 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: 결선을 넷으로 본다 — 행이 밀려도 서명이 같다"
```

---

### Task 6: 참조 결선도를 같은 모양으로 꺼낸다

**Files:**
- Modify: `scripts/lab/hand_compare.py`
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: Task 1 의 `wiring()`, Task 5 의 넷 모델
- Produces:
  - `CIRCUITS` — 회로 ID -> 빌더 이름 사상
  - `reference_diagram(circuit_id) -> Diagram`
  - `CompareError(ValueError)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_compare.py` 에 더한다.

```python
class Reference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nand = hc.reference_diagram('e1_nand')

    def test_참조가_Diagram_으로_나온다(self):
        self.assertEqual([c['label'] for c in self.nand.chips],
                         ['74HC08', '74HC00'])
        self.assertEqual([c['pin1_row'] for c in self.nand.chips], [7, 18])

    def test_참조_pin14_는_VCC_이고_pin7_은_GND_다(self):
        sig = hc.signatures(self.nand)
        for chip in ('74HC08', '74HC00'):
            self.assertIn(('RAIL', 'VCC'), sig[(chip, 14)])
            self.assertNotIn(('RAIL', 'GND'), sig[(chip, 14)])
            self.assertIn(('RAIL', 'GND'), sig[(chip, 7)])

    def test_참조_미사용_출력은_아무_데도_안_닿는다(self):
        sig = hc.signatures(self.nand)
        for chip, pin in [('74HC08', 6), ('74HC08', 8), ('74HC00', 11)]:
            self.assertEqual(sig[(chip, pin)], frozenset())

    def test_참조_LED_사슬은_캐소드와_저항_윗다리가_한_넷이다(self):
        nets = hc.build_nets(self.nand)
        for ch in self.nand.chains:
            self.assertEqual(nets[hc.node_of(ch['cathode'])],
                             nets[hc.node_of(ch['res_top'])])

    def test_참조_칩_사이_연결이_서명에_보인다(self):
        sig = hc.signatures(self.nand)
        self.assertIn(('PIN', '74HC00', 1), sig[('74HC08', 3)])

    def test_모르는_회로_ID_는_거절한다(self):
        with self.assertRaises(hc.CompareError):
            hc.reference_diagram('e9_없음')

    def test_다섯_회로가_모두_열린다(self):
        for cid in ('e1_and', 'e1_or', 'e1_nand', 'e1_nor', 'e1_comb'):
            d = hc.reference_diagram(cid)
            self.assertTrue(d.chips, cid)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py::Reference -q`
Expected: FAIL — `AttributeError: module 'scripts.lab.hand_compare' has no attribute 'reference_diagram'`

- [ ] **Step 3: 참조 추출을 더한다**

`hand_compare.py` 맨 위 import 에 더한다.

```python
import os
import tempfile

from .hand_grid import load_renderer
from .hand_transcript import Diagram
```

그리고 모듈 끝에 붙인다.

```python
# 손그림 검토가 정답으로 삼는 회로들. `main()` 의 dispatch 와 같은 이름을 쓴다
CIRCUITS = ('e1_and', 'e1_or', 'e1_nand', 'e1_nor', 'e1_comb',
            'e1_comb_s1', 'e1_comb_s2', 'e1_comb_s3')


class CompareError(ValueError):
    """참조를 꺼내거나 대조할 수 없다."""


def reference_diagram(circuit_id):
    """렌더러 빌더를 돌려 그 그림의 결선을 `Diagram` 으로 꺼낸다.

    빌더가 PNG 를 쓰긴 하지만 우리가 필요한 건 `wiring()` 이다. 임시 폴더에
    쓰고 버린다 — `export()` 가 `verify()` 를 부르므로 `overlaps` 도 이때 찬다.
    """
    if circuit_id not in CIRCUITS:
        raise CompareError(
            f"모르는 회로 ID: {circuit_id!r}. "
            f"쓸 수 있는 것: {', '.join(CIRCUITS)}")
    mod = load_renderer()
    builder = getattr(mod, f"build_{circuit_id}", None)
    if builder is None:
        raise CompareError(f"빌더가 없다: build_{circuit_id}")
    with tempfile.TemporaryDirectory() as tmp:
        bb = builder(os.path.join(tmp, f"{circuit_id}.png"))
    if bb is None:
        raise CompareError(
            f"build_{circuit_id} 가 렌더러를 돌려주지 않는다 — "
            "빌더 끝에 `return bb` 가 있어야 한다")
    return _from_wiring(bb.wiring(), circuit_id)


def _from_wiring(w, circuit_id):
    """`wiring()` 출력 -> `Diagram`. 손그림 쪽과 같은 모양으로 맞춘다."""
    bridges = [(kind, a, b) for kind, a, b in w['bridges']
               if a is not None and b is not None]
    return Diagram(
        chips=[dict(c) for c in w['chips']],
        wires=[dict(x) for x in w['wires']],
        leds=[dict(l) for l in w['leds']],
        resistors=[dict(r) for r in w['resistors']],
        chains=[dict(c) for c in w['chains']],
        unused_inputs=[dict(u) for u in w['unused_inputs']],
        unused_outputs=[dict(u) for u in w['unused_outputs']],
        bridges=bridges,
        overlaps=list(w['overlaps']),
        circuit=circuit_id)
```

참조 저항에는 꼬리표가 없어(`draw_resistor` 는 `label` 만 안다) 사슬 대조가 `chains` 를 쓴다. `_from_wiring` 은 `resistors` 의 `tag` 를 `chains` 에서 채운다 — 아래를 `_from_wiring` 의 `return` 앞에 넣는다.

```python
    by_hole = {c['res_top']: c['tag'] for c in w['chains']}
    for r in w['resistors']:
        r['tag'] = by_hole.get(r['top'], r.get('label', ''))
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (18 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: 참조 결선도를 손그림과 같은 모양으로 꺼낸다"
```

---

### Task 7: 자기대조는 0건 — 그리고 물리 규칙 H1·H2

**Files:**
- Modify: `scripts/lab/hand_compare.py`
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: Task 6 의 `reference_diagram`
- Produces:
  - `compare(ref, hand) -> list[HandFinding]` — 이 과제에서는 H1·H2 만 채운다
  - `check_holes(hand) -> list[HandFinding]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class SelfCompare(unittest.TestCase):
    def test_참조를_그대로_손그림으로_넣으면_결함_0건(self):
        """정답을 정답과 견주어 결함이 나오면 검사기가 틀린 것이다."""
        for cid in ('e1_and', 'e1_or', 'e1_nand', 'e1_nor'):
            ref = hc.reference_diagram(cid)
            hand = hc.reference_diagram(cid)
            hand.signed = True
            hand.title = cid
            bad = [f for f in hc.compare(ref, hand) if f.grade != '표기']
            self.assertEqual(bad, [], f"{cid}: {[str(x) for x in bad]}")


class Physical(unittest.TestCase):
    def _hand(self, cid='e1_nand'):
        d = hc.reference_diagram(cid)
        d.signed = True
        return d

    def test_H1_레일_빈_행에_꽂은_끝점을_잡는다(self):
        hand = self._hand()
        hand.wires.append({'kind': 'gnd', 'desc': '',
                           'frm': ('hole', ('left', 'gnd', 14)),
                           'to': ('hole', ('left', 'b', 14))})
        rules = {f.rule for f in hc.compare(hc.reference_diagram('e1_nand'), hand)}
        self.assertIn('H1', rules)

    def test_H1_63행_밖은_잡는다(self):
        hand = self._hand()
        hand.wires.append({'kind': 'sig', 'desc': '',
                           'frm': ('hole', ('left', 'a', 70)),
                           'to': ('hole', ('left', 'b', 70))})
        rules = {f.rule for f in hc.compare(hc.reference_diagram('e1_nand'), hand)}
        self.assertIn('H1', rules)

    def test_H2_한_홀에_리드_둘을_잡는다(self):
        hand = self._hand()
        chip = hand.chips[0]
        hand.wires.append({'kind': 'sig', 'desc': '',
                           'frm': ('hole', chip['pins'][1]),
                           'to': ('hole', ('left', 'a', 30))})
        found = [f for f in hc.compare(hc.reference_diagram('e1_nand'), hand)
                 if f.rule == 'H2']
        self.assertTrue(found)
        self.assertIn('e7', found[0].where)

    def test_H2_는_참조에서는_안_난다(self):
        ref = hc.reference_diagram('e1_nand')
        self.assertEqual([f for f in hc.check_holes(ref, ref) if f.rule == 'H2'], [])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py::SelfCompare tests/test_hand_compare.py::Physical -q`
Expected: FAIL — `AttributeError: ... has no attribute 'compare'`

- [ ] **Step 3: H1·H2 와 `compare()` 뼈대를 더한다**

`hand_compare.py` 끝에 붙인다.

```python
def _addr(hole):
    """홀 -> 사람이 읽는 주소. 판정문에 그대로 들어간다."""
    block, col, row = hole
    prefix = '좌' if block == 'left' else '우'
    names = {'gnd': 'GND레일', 'vcc': 'VCC레일',
             'mid_gnd': '중앙GND레일', 'mid_vcc': '중앙VCC레일'}
    if col in RAIL_COLS:
        return f'{prefix} {names[col]}{row}행'
    return f'{prefix} {col}{row}'


def check_holes(ref, hand):
    """H1 끝점이 실제 홀인가 · H2 한 홀에 리드 하나인가. (`ref` 는 쓰지 않는다)

    렌더러 `verify()` 의 R1·R2 를 손그림 쪽으로 옮긴 것이다. 그림대로 꽂을 수
    없는 결선은 무엇을 뜻하든 틀린 것이라 서명 비교보다 먼저 본다.

    규칙 함수는 전부 `(ref, hand)` 를 받는다 — `_RULES` 가 한 줄로 도는
    대신 규칙마다 분기를 두면 규칙이 늘 때마다 그 분기가 커진다.
    """
    mod = load_renderer()
    out, leads = [], {}

    def put(hole, what):
        block, col, row = hole
        if not 1 <= row <= mod.ROW_MAX:
            out.append(HandFinding(
                'H1', '치명', _addr(hole),
                f'{row}행은 판에 없다 (1~{mod.ROW_MAX}행)'))
            return
        if col in RAIL_COLS and row in mod.RAIL_GAP_ROWS:
            out.append(HandFinding(
                'H1', '치명', _addr(hole),
                f'레일 {row}행에는 홀이 없다 — 5홀씩 묶여 빈 행이다. '
                f'{what} 를 이웃 행으로 옮긴다'))
            return
        key = (block, col, row)
        if key in leads:
            out.append(HandFinding(
                'H2', '치명', _addr(hole),
                f'한 홀에 둘: {leads[key]} + {what}. '
                '같은 행 a~e 는 한 노드라 옆 홀로 옮기면 된다'))
        else:
            leads[key] = what

    for key, ch in zip(chip_keys(hand), hand.chips):
        for pin, hole in ch['pins'].items():
            put(hole, f'{key} pin {pin}')
    for w in hand.wires:
        for ep in (w['frm'], w['to']):
            if ep[0] == 'hole' and ep[1] is not None:
                put(ep[1], f"{w.get('kind', '')} 배선".strip())
    for l in hand.leds:
        put(l['anode'], f"{l['tag']} LED 애노드")
        put(l['cathode'], f"{l['tag']} LED 캐소드")
    for r in hand.resistors:
        put(r['top'], f"{r.get('tag', '')} 저항 윗다리".strip())
        put(r['bottom'], f"{r.get('tag', '')} 저항 아랫다리".strip())
    for kind, a, b in hand.bridges:
        put(a, f'{kind} 레일 브리지')
        put(b, f'{kind} 레일 브리지')
    return out


# 규칙을 여기 순서대로 돈다. 새 규칙은 이 목록에 올린다 — 함수만 만들고
# 목록에 안 올리면 검사가 조용히 빠진다. 2026-09-08 회차에서 LED 사슬 검사를
# 통째로 건너뛴 것이 바로 그 실패였다
_RULES = [check_holes]


def compare(ref, hand):
    """참조와 손그림을 견준다. 심한 것부터 정렬해서 준다."""
    out = []
    for rule in _RULES:
        out.extend(rule(ref, hand))
    order = {g: i for i, g in enumerate(GRADES)}
    return sorted(out, key=lambda f: (order.get(f.grade, 9), f.rule))
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (23 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: 손그림에 렌더러 R1·R2 를 옮긴다 — H1·H2"
```

---

### Task 8: 전원 4종 H3·H4·H5

**Files:**
- Modify: `scripts/lab/hand_compare.py`
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: Task 7 의 `_RULES`, `HandFinding`, `signatures`
- Produces: `check_power(ref, hand) -> list[HandFinding]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class Power(unittest.TestCase):
    """2026-09-08 손그림 3쪽은 뒷단 74HC00 오른쪽이 통째로 비어 있었다 —
    pin 14 전원과 pin 9·10·12·13 접지 다섯 가닥이 없었다. 위 칩과 나란히
    놓고 봐야 보이는 결함이라 사람 눈으로는 놓치기 쉽다."""

    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.signed = True
        return ref, hand

    def _drop_wires_touching(self, d, hole):
        node = hc.node_of(hole)
        d.wires = [w for w in d.wires
                   if hc._endpoint_node(w['frm']) != node
                   and hc._endpoint_node(w['to']) != node]

    def test_H3_pin14_전원이_없으면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[1]['pins'][14])
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H3']
        self.assertTrue(found)
        self.assertIn('74HC00', found[0].where)
        self.assertEqual(found[0].grade, '치명')

    def test_H3_pin7_접지가_없으면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[1]['pins'][7])
        rules = {f.rule for f in hc.compare(ref, hand)}
        self.assertIn('H3', rules)

    def test_H3_pin14_를_GND_에_물리면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[1]['pins'][14])
        hand.wires.append({'kind': 'gnd', 'desc': '',
                           'frm': ('hole', ('left', 'g', 18)),
                           'to': ('hole', ('left', 'mid_gnd', 18))})
        msgs = ' '.join(f.message for f in hc.compare(ref, hand) if f.rule == 'H3')
        self.assertIn('GND', msgs)

    def test_H4_미사용_입력_접지가_빠지면_잡는다(self):
        ref, hand = self._pair()
        self._drop_wires_touching(hand, hand.chips[0]['pins'][9])
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H4']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '기능')

    def test_H5_미사용_출력을_접지하면_잡는다(self):
        ref, hand = self._pair()
        hand.wires.append({'kind': 'gnd', 'desc': '',
                           'frm': ('hole', ('left', 'g', 9)),
                           'to': ('hole', ('left', 'mid_gnd', 9))})
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H5']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')
        self.assertIn('개방', found[0].message)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py::Power -q`
Expected: FAIL — H3·H4·H5 가 하나도 안 난다

- [ ] **Step 3: `check_power()` 를 더한다**

```python
def _pin_of(hand_keys, ref_key):
    """참조 칩 이름이 손그림에도 있는가. 없으면 None."""
    return ref_key if ref_key in hand_keys else None


def check_power(ref, hand):
    """H3 전원·접지 · H4 미사용 입력 접지 · H5 미사용 출력 개방.

    칩마다 이 넷을 세는 것이 손그림 검토의 뼈대다 — 회로가 무엇이든 항상
    같고, 빠지면 회로가 아예 안 돈다. 2026-09-08 손그림 3쪽에서 뒷단 칩
    오른쪽 다섯 가닥이 통째로 없었던 것을 잡는 자리다.
    """
    out = []
    hsig = signatures(hand)
    hkeys = set(chip_keys(hand))

    for key in chip_keys(ref):
        if key not in hkeys:
            out.append(HandFinding(
                'H3', '치명', key, '참조에 있는 칩이 손그림에 없다'))
            continue
        for pin, want, avoid in ((14, 'VCC', 'GND'), (7, 'GND', 'VCC')):
            sig = hsig.get((key, pin), frozenset())
            if ('RAIL', want) not in sig:
                out.append(HandFinding(
                    'H3', '치명', f'{key} pin {pin}',
                    f'{want} 레일에 닿지 않는다. '
                    f'{"전원이 안 들어가 칩이 동작하지 않는다" if pin == 14 else "접지가 없어 칩이 동작하지 않는다"}'))
            if ('RAIL', avoid) in sig:
                out.append(HandFinding(
                    'H3', '치명', f'{key} pin {pin}',
                    f'{avoid} 레일에도 닿아 있다 — 전원 단락이다'))

    for u in ref.unused_inputs:
        key, pin = u['chip'], u['pin']
        if key not in hkeys:
            continue
        want = 'VCC' if u.get('rail') == 'vcc' else 'GND'
        if ('RAIL', want) not in hsig.get((key, pin), frozenset()):
            out.append(HandFinding(
                'H4', '기능', f'{key} pin {pin}',
                f'미사용 입력인데 {want} 에 묶이지 않았다. '
                'CMOS 입력은 뜨면 안 된다'))

    for u in ref.unused_outputs:
        key, pin = u['chip'], u['pin']
        if key not in hkeys:
            continue
        sig = hsig.get((key, pin), frozenset())
        if sig:
            what = ', '.join(sorted(str(s) for s in sig))
            out.append(HandFinding(
                'H5', '치명', f'{key} pin {pin}',
                f'미사용 출력은 개방(NC)이어야 하는데 {what} 에 닿아 있다. '
                'GND 로 내리거나 출력끼리 묶으면 칩이 상한다'))
    return out
```

`_RULES` 를 고친다.

```python
_RULES = [check_holes, check_power]
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (28 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: 칩마다 전원 4종을 센다 — H3·H4·H5"
```

---

### Task 9: 신호 서명 H6

**Files:**
- Modify: `scripts/lab/hand_compare.py`
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: Task 8 의 `_RULES`
- Produces: `check_signals(ref, hand) -> list[HandFinding]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class Signals(unittest.TestCase):
    """4쪽은 74HC02 pin 3 으로 가는 입력 C 가 없었고, 5쪽은 74HC32 pin 1 로
    가는 A 갈래가 없었다. 둘 다 '있어야 할 것이 없다' 라 원도만 보고는
    안 보인다 — 5쪽 갈래는 참조 그림에서 초록 선 아래 깔려 있기까지 했다."""

    def _pair(self, cid='e1_nor'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.signed = True
        return ref, hand

    def test_H6_입력이_빠지면_잡는다(self):
        ref, hand = self._pair()
        node = hc.node_of(hand.chips[1]['pins'][3])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H6']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')

    def test_H6_칩_사이_연결이_빠지면_잡는다(self):
        ref, hand = self._pair('e1_nand')
        node = hc.node_of(hand.chips[1]['pins'][1])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        msgs = ' '.join(f.message for f in hc.compare(ref, hand) if f.rule == 'H6')
        self.assertIn('74HC08', msgs)

    def test_H6_출력_둘이_한_넷이면_잡는다(self):
        """5쪽에서 Z 선과 A·B 선이 한 홀에서 만났다 — 출력끼리 맞물린다."""
        ref, hand = self._pair('e1_comb')
        a = hand.chips[0]['pins'][4]      # 74HC04 출력
        b = hand.chips[1]['pins'][3]      # 74HC08 출력
        hand.wires.append({'kind': 'mid', 'desc': '',
                           'frm': ('hole', (a[0], 'd', a[2])),
                           'to': ('hole', (b[0], 'd', b[2]))})
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H6']
        self.assertTrue(found)

    def test_H6_행이_통째로_밀린_그림은_통과한다(self):
        """칩과 배선이 함께 한 행 내려간 그림은 유효하다."""
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        hand.signed = True
        found = [f for f in hc.compare(ref, hand)
                 if f.rule == 'H6' or f.grade == '치명']
        self.assertEqual([str(x) for x in found], [])
```

같은 파일 위쪽(클래스들 앞)에 도우미를 더한다.

```python
def _shift_rows(d, delta):
    """그림 전체를 delta 행만큼 옮긴다. 레일 빈 행은 피하지 않으므로
    빈 행에 걸리지 않는 delta 만 쓴다."""
    def s(hole):
        return None if hole is None else (hole[0], hole[1], hole[2] + delta)

    for ch in d.chips:
        ch['pin1_row'] += delta
        ch['pins'] = {p: s(h) for p, h in ch['pins'].items()}
    for w in d.wires:
        for side in ('frm', 'to'):
            kind, val = w[side]
            w[side] = (kind, s(val)) if kind == 'hole' else (kind, val)
    for l in d.leds:
        l['anode'], l['cathode'] = s(l['anode']), s(l['cathode'])
    for r in d.resistors:
        r['top'], r['bottom'] = s(r['top']), s(r['bottom'])
    for c in d.chains:
        for k in ('signal', 'anode', 'cathode', 'res_top', 'res_bottom'):
            if k in c:
                c[k] = s(c[k])
    d.bridges = [(k, s(a), s(b)) for k, a, b in d.bridges]
    return d
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py::Signals -q`
Expected: FAIL — H6 이 안 난다

- [ ] **Step 3: `check_signals()` 를 더한다**

```python
def _describe(item):
    """부착물 하나를 사람 말로."""
    if item[0] == 'PIN':
        return f'{item[1]} pin {item[2]}'
    if item[0] == 'LED':
        return f"{item[1]} LED {'애노드' if item[2] == 'A' else '캐소드'}"
    if item[0] == 'RES':
        return f"{item[1]} 저항 {'윗' if item[2] == 'T' else '아랫'}다리"
    if item[0] == 'RAIL':
        return f'{item[1]} 레일'
    if item[0] == 'JACK':
        return f'{item[1]} 전원잭'
    return str(item)


def check_signals(ref, hand):
    """H6 핀 서명 차이.

    전원(H3)·미사용(H4·H5)이 이미 본 것은 뺀다 — 한 결함을 두 번 보고하지
    않는다. 남는 것이 신호선이다: 입력, 단 간 연결, LED 도달.
    """
    out = []
    rsig, hsig = signatures(ref), signatures(hand)
    hkeys = set(chip_keys(hand))
    skip = {(u['chip'], u['pin']) for u in ref.unused_inputs}
    skip |= {(u['chip'], u['pin']) for u in ref.unused_outputs}

    for (key, pin), want in sorted(rsig.items()):
        if key not in hkeys or pin in (7, 14) or (key, pin) in skip:
            continue
        got = hsig.get((key, pin), frozenset())
        missing = want - got
        extra = got - want
        if not missing and not extra:
            continue
        parts = []
        if missing:
            parts.append('없다: ' + ', '.join(sorted(_describe(m) for m in missing)))
        if extra:
            parts.append('더 있다: ' + ', '.join(sorted(_describe(e) for e in extra)))
        note = _reference_hidden(ref, key, pin)
        out.append(HandFinding(
            'H6', '치명', f'{key} pin {pin}',
            ' · '.join(parts) + note))
    return out


def _reference_hidden(ref, key, pin):
    """참조 그림에서 그 핀으로 가는 선이 다른 선에 깔려 있으면 알린다.

    2026-09-08 5쪽에서 빠진 `A -> 74HC32 pin 1` 이 그런 선이었다. 원도가
    숨겨 놓은 것을 따라 그린 사람 탓으로 돌리면 다음에도 같은 자리가 빠진다.
    """
    needle = f'pin {pin}'
    for w in ref.overlaps:
        if needle in w:
            return ' (참조 그림에서 다른 선에 깔려 잘 안 보이는 자리다)'
    return ''
```

`_RULES` 에 올린다.

```python
_RULES = [check_holes, check_power, check_signals]
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (32 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: 신호 핀 서명을 대조한다 — H6"
```

---

### Task 10: LED 사슬 H7 과 레일 연속성 H8

**Files:**
- Modify: `scripts/lab/hand_compare.py`
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: Task 9 의 `_RULES`
- Produces: `check_led_chains(ref, hand)`, `check_rails(ref, hand)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class LedChain(unittest.TestCase):
    """**1차 검토가 통째로 건너뛴 검사다.** 3·4쪽 L1 저항이 LED 캐소드 행이
    아니라 애노드 행에서 시작해 LED 가 아예 안 켜지는데, 칩 배선만 보면
    멀쩡해 보인다. 그래서 코드로 강제한다."""

    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.signed = True
        return ref, hand

    def _chain(self, d, tag):
        return next(c for c in d.chains if c['tag'] == tag)

    def test_H7_저항이_한_행_위면_잡는다(self):
        ref, hand = self._pair()
        ch = self._chain(hand, 'L1')
        top = ch['res_top']
        ch['res_top'] = (top[0], top[1], top[2] - 1)
        for r in hand.resistors:
            if r['tag'] == 'L1':
                r['top'] = ch['res_top']
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H7']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')
        self.assertIn('캐소드', found[0].message)

    def test_H7_저항_아랫다리가_GND_에_안_닿으면_잡는다(self):
        ref, hand = self._pair()
        ch = self._chain(hand, 'L1')
        node = hc.node_of(ch['res_bottom'])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H7']
        self.assertTrue(found)
        self.assertIn('GND', found[0].message)

    def test_H7_사슬이_통째로_없으면_잡는다(self):
        ref, hand = self._pair()
        hand.chains = [c for c in hand.chains if c['tag'] != 'L2']
        hand.leds = [l for l in hand.leds if l['tag'] != 'L2']
        hand.resistors = [r for r in hand.resistors if r.get('tag') != 'L2']
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H7']
        self.assertTrue(found)
        self.assertIn('L2', found[0].where)


class Rails(unittest.TestCase):
    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.signed = True
        return ref, hand

    def test_H8_브리지가_없으면_잡는다(self):
        ref, hand = self._pair()
        hand.wires = [w for w in hand.wires if w.get('desc') != '레일 브리지']
        hand.bridges = []
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H8']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')

    def test_H8_브리지가_있으면_안_난다(self):
        ref, hand = self._pair()
        self.assertEqual([f for f in hc.compare(ref, hand) if f.rule == 'H8'], [])
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py::LedChain tests/test_hand_compare.py::Rails -q`
Expected: FAIL — H7·H8 이 안 난다

- [ ] **Step 3: 두 규칙을 더한다**

```python
def check_led_chains(ref, hand):
    """H7 LED 사슬이 이어져 있는가.

    신호 -> LED 애노드 -> 캐소드 -> 저항 윗다리 -> 아랫다리 -> GND 로 다섯
    자리가 사슬로 이어져야 한다. 어느 한 마디만 어긋나도 LED 는 안 켜지는데
    **칩 배선만 보면 멀쩡해 보인다.** 2026-09-08 1차 검토가 이 검사를 건너뛰어
    3·4쪽의 죽은 L1 을 통과시켰다.

    신호가 애노드에 도달하는지는 H6 이 이미 본다(핀 서명에 LED 애노드가
    들어간다). 여기는 캐소드부터 GND 까지를 본다.
    """
    out = []
    nets = build_nets(hand)
    att = attachments(hand, nets)
    by_tag = {c['tag']: c for c in hand.chains}

    for rc in ref.chains:
        tag = rc['tag']
        hcn = by_tag.get(tag)
        if hcn is None:
            out.append(HandFinding(
                'H7', '치명', tag,
                '참조에 있는 LED 사슬이 손그림에 없다 '
                '(LED 와 330Ω 을 같은 꼬리표로 적었는지 본다)'))
            continue
        k_net = nets.get(node_of(hcn['cathode']))
        t_net = nets.get(node_of(hcn['res_top']))
        if k_net != t_net:
            out.append(HandFinding(
                'H7', '치명', f"{tag} ({_addr(hcn['cathode'])})",
                f"LED 캐소드({_addr(hcn['cathode'])})와 "
                f"저항 윗다리({_addr(hcn['res_top'])})가 다른 줄이다. "
                'LED 가 안 켜지고 전류는 저항으로만 빠진다'))
        b_net = nets.get(node_of(hcn['res_bottom']))
        if ('RAIL', 'GND') not in att.get(b_net, set()):
            touched = ', '.join(sorted(_describe(a) for a in att.get(b_net, set())))
            out.append(HandFinding(
                'H7', '치명', f"{tag} ({_addr(hcn['res_bottom'])})",
                f"저항 아랫다리가 GND 레일에 닿지 않는다"
                + (f' — 대신 {touched} 에 닿아 있다' if touched else '')))
    return out


def check_rails(ref, hand):
    """H8 레일 연속성.

    레일쌍 넷은 서로 **별개 스트립**이다. +5V 를 한 레일에 넣고 칩 14번 핀을
    다른 레일에 물리면 그림은 완벽해 보이는데 전원이 안 간다. 렌더러도 같은
    이유로 `verify()` 에 연결성 검사를 넣었다 — 눈으로는 절대 안 잡힌다.
    """
    out = []
    nets = build_nets(hand)
    att = attachments(hand, nets)

    for pol, colset in (('VCC', VCC_COLS), ('GND', GND_COLS)):
        used = {}
        for node in nets:
            if node[0] == 'R' and node[2] in colset:
                rep = nets[node]
                if any(a[0] in ('PIN', 'JACK', 'RES', 'LED')
                       for a in att.get(rep, set())):
                    used.setdefault(rep, []).append(node)
        if len(used) > 1:
            groups = ' / '.join(
                '+'.join(sorted(f'{n[1]} {n[2]}' for n in g))
                for g in used.values())
            out.append(HandFinding(
                'H8', '치명', f'{pol} 레일',
                f'{pol} 레일이 끊겨 있다 — 브리지가 없다: {groups}. '
                '레일쌍은 별개 스트립이라 이어주지 않으면 전원이 안 간다'))
    return out
```

`_RULES` 에 올린다.

```python
_RULES = [check_holes, check_power, check_signals, check_led_chains, check_rails]
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (37 tests)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: LED 사슬과 레일 연속성을 센다 — H7·H8"
```

---

### Task 11: 표기·보류 H9~H13 과 판정문

**Files:**
- Modify: `scripts/lab/hand_compare.py`
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: Task 10 의 `_RULES`
- Produces:
  - `check_placement(ref, hand)` — H9·H10
  - `check_paperwork(ref, hand)` — H11·H12·H13
  - `verdict(findings) -> str` — `'제출 가능'` | `'수정 필요'`
  - `judgment_markdown(pages, round_no) -> str` — `pages` 는 `[(page_no, circuit, findings, hand)]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
class Paperwork(unittest.TestCase):
    def _pair(self, cid='e1_nand'):
        ref = hc.reference_diagram(cid)
        hand = hc.reference_diagram(cid)
        hand.signed = True
        hand.title = '2-1 NAND Gate'
        return ref, hand

    def test_H10_칩이_밀리면_표기로만_알린다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = _shift_rows(hc.reference_diagram('e1_nand'), +1)
        hand.signed = True
        hand.title = '2-1 NAND Gate'
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H10']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '표기')

    def test_H12_학번_미기재를_잡는다(self):
        ref, hand = self._pair()
        hand.signed = False
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H12']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '표기')

    def test_H11_제목이_회로와_다르면_잡는다(self):
        ref, hand = self._pair()
        hand.title = '2-2 NAND Gate'
        hand.circuit = 'e1_nor'
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H11']
        self.assertTrue(found)

    def test_H13_uncertain_은_보류로_나온다(self):
        ref, hand = self._pair()
        hand.uncertain = {('left', 'd', 17)}
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H13']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '보류')


class Verdict(unittest.TestCase):
    def test_치명이_있으면_수정_필요(self):
        f = [hc.HandFinding('H3', '치명', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '수정 필요')

    def test_기능이_있으면_수정_필요(self):
        f = [hc.HandFinding('H4', '기능', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '수정 필요')

    def test_표기만_있으면_제출_가능(self):
        """학번 미기재는 막지 않는다 — 별도 줄로만 알린다."""
        f = [hc.HandFinding('H12', '표기', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '제출 가능')

    def test_보류만_있으면_제출_가능(self):
        f = [hc.HandFinding('H13', '보류', 'x', 'y')]
        self.assertEqual(hc.verdict(f), '제출 가능')


class Judgment(unittest.TestCase):
    def test_판정문에_쪽별_결함과_총평이_들어간다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        hand.signed = False
        hand.title = '2-1 NAND Gate'
        hand.page = 3
        md = hc.judgment_markdown([(3, 'e1_nand', hc.compare(ref, hand), hand)],
                                  round_no=1)
        self.assertIn('round1', md)
        self.assertIn('3쪽', md)
        self.assertIn('제출 가능', md)
        self.assertIn('H12', md)

    def test_치명이_있으면_총평이_수정_필요다(self):
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        hand.signed = True
        node = hc.node_of(hand.chips[1]['pins'][14])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        md = hc.judgment_markdown([(3, 'e1_nand', hc.compare(ref, hand), hand)], 1)
        self.assertIn('수정 필요', md)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py::Paperwork tests/test_hand_compare.py::Verdict tests/test_hand_compare.py::Judgment -q`
Expected: FAIL — H9~H13 과 `verdict`·`judgment_markdown` 이 없다

- [ ] **Step 3: 나머지 규칙과 판정문을 더한다**

```python
# 회로 ID -> 제목에 들어가야 할 말. 제목만 보고 다른 회로를 그렸다고
# 판정하지 않는다 — 제목이 틀렸는지 그림이 틀렸는지는 서명이 가른다
CIRCUIT_WORDS = {
    'e1_and': ('AND',), 'e1_or': ('OR',),
    'e1_nand': ('NAND',), 'e1_nor': ('NOR',),
    'e1_comb': ('복합', 'COMB'),
    'e1_comb_s1': ('복합', 'COMB'), 'e1_comb_s2': ('복합', 'COMB'),
    'e1_comb_s3': ('복합', 'COMB'),
}


def check_placement(ref, hand):
    """H9 브리지·잭 행 차이 · H10 칩 행 차이. 둘 다 표기다.

    칩이 밀려도 배선이 함께 옮겨져 있으면 그림은 유효하다. 그래도 알리는
    이유는 체크리스트의 좌표 표기와 어긋나기 때문이다 — 같이 제출한다면
    맞춰 두는 편이 낫다.
    """
    out = []
    rmap, hmap = {}, {}
    for key, ch in zip(chip_keys(ref), ref.chips):
        rmap[key] = ch['pin1_row']
    for key, ch in zip(chip_keys(hand), hand.chips):
        hmap[key] = ch['pin1_row']
    for key, rrow in rmap.items():
        hrow = hmap.get(key)
        if hrow is not None and hrow != rrow:
            out.append(HandFinding(
                'H10', '표기', key,
                f'참조는 pin 1 이 {rrow}행인데 손그림은 {hrow}행이다 '
                f'({hrow - rrow:+d}행). 배선이 함께 옮겨져 있으면 회로는 맞다'))

    rb = {(k, a[2]) for k, a, _b in ref.bridges}
    hb = {(k, a[2]) for k, a, _b in hand.bridges}
    if rb and hb and rb != hb:
        out.append(HandFinding(
            'H9', '표기', '레일 브리지',
            f'참조는 {sorted(r for _k, r in rb)}행인데 손그림은 '
            f'{sorted(r for _k, r in hb)}행이다. 도면상 같은 노드지만, '
            '레일이 가운데서 끊긴 실물 보드라면 30행 아래 브리지는 전원을 못 올린다'))
    return out


def check_paperwork(ref, hand):
    """H11 제목 · H12 자필 기재 · H13 전사 보류."""
    out = []
    words = CIRCUIT_WORDS.get(hand.circuit or ref.circuit, ())
    title = (hand.title or '').upper()
    if words and title and not any(w.upper() in title for w in words):
        out.append(HandFinding(
            'H11', '표기', '제목',
            f'제목 {hand.title!r} 에 {" 또는 ".join(words)} 가 없다. '
            '회로와 제목 중 어느 쪽이 틀렸는지 함께 본다'))
    if not hand.signed:
        out.append(HandFinding(
            'H12', '표기', '자필 기재',
            '학번·이름·날짜가 없다. 참조 도면이 제출 조건으로 요구한다'))
    for hole in sorted(hand.uncertain):
        out.append(HandFinding(
            'H13', '보류', _addr(hole),
            '전사가 확신하지 못한 끝점이다. 그 자리를 확대해 다시 읽는다'))
    return out


_RULES = [check_holes, check_power, check_signals, check_led_chains,
          check_rails, check_placement, check_paperwork]

BLOCKING = ('치명', '기능')


def verdict(findings):
    """치명·기능이 없으면 제출 가능. 표기는 막지 않고 별도 줄로 알린다."""
    return '수정 필요' if any(f.grade in BLOCKING for f in findings) else '제출 가능'


def judgment_markdown(pages, round_no):
    """쪽별 판정 문서. `pages` 는 (쪽 번호, 회로 ID, 결함들, 손그림) 목록."""
    every = [f for _p, _c, fs, _h in pages for f in fs]
    lines = [f'# 손그림 결선도 검토 round{round_no}', '',
             f'**총평: {verdict(every)}**', '']

    counts = {g: sum(1 for f in every if f.grade == g) for g in GRADES}
    lines += ['| 등급 | 건수 |', '|---|---|']
    lines += [f'| {g} | {counts[g]} |' for g in GRADES]
    lines.append('')

    for page, circuit, findings, hand in pages:
        lines.append(f'## {page}쪽 · {circuit} · {hand.title or "제목 없음"}')
        lines.append('')
        lines.append(f'판정: **{verdict(findings)}**')
        lines.append('')
        if not findings:
            lines += ['참조와 다른 곳이 없다.', '']
            continue
        lines += ['| 등급 | 규칙 | 자리 | 내용 |', '|---|---|---|---|']
        for f in findings:
            msg = f.message.replace('|', r'\|')
            lines.append(f'| {f.grade} | {f.rule} | {f.where} | {msg} |')
        lines.append('')
    return '\n'.join(lines)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (48 tests)

- [ ] **Step 5: 규칙이 전부 목록에 올라 있는지 묶는다**

`tests/test_hand_compare.py` 에 더한다. 이 테스트가 **이번 계획의 존재 이유**다 — 검사 함수를 만들고 목록에 안 올리면 조용히 빠진다.

```python
class RuleRegistry(unittest.TestCase):
    def test_check_로_시작하는_함수는_전부_규칙_목록에_있다(self):
        """함수만 만들고 `_RULES` 에 안 올리면 검사가 조용히 빠진다.
        2026-09-08 1차 검토가 LED 사슬을 건너뛴 것이 바로 그 실패였다."""
        defined = {v for k, v in vars(hc).items()
                   if k.startswith('check_') and callable(v)}
        self.assertEqual(defined, set(hc._RULES))

    def test_규칙_코드가_H1부터_H13까지_빠짐없다(self):
        import inspect
        src = inspect.getsource(hc)
        for n in range(1, 14):
            self.assertIn(f"'H{n}'", src, f'H{n} 규칙이 없다')
```

Run: `python3 -m pytest tests/test_hand_compare.py -q`
Expected: PASS (50 tests)

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "feat: 표기·보류 규칙과 판정문을 낸다 — H9~H13"
```

---

### Task 12: 스킬 절차서

**Files:**
- Create: `.claude/skills/review-hand-diagram/SKILL.md`
- Modify: `tests/test_skill_docs.py`

**Interfaces:**
- Consumes: Task 1~11 전부
- Produces: `/review-hand-diagram` 로 부를 수 있는 절차서

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 의 경로 상수 근처(21~26줄)에 더한다.

```python
HAND = ROOT / ".claude/skills/review-hand-diagram/SKILL.md"
```

그리고 파일 끝에 클래스를 더한다.

```python
class HandDiagramSkill(unittest.TestCase):
    def test_문서가_있다(self):
        self.assertTrue(HAND.exists())

    def test_출력_경로가_박혀_있다(self):
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("output/손그림검토/round", text)

    def test_폴더_가드가_거절보다_앞에_온다(self):
        """실험 폴더가 없으면 만들지 않고 init-lab-experiment 로 보낸다."""
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("init-lab-experiment", text)
        self.assertLess(text.index("experiment_dir"),
                        text.index("init-lab-experiment"))

    def test_규칙_열세개가_전부_적혀_있다(self):
        text = HAND.read_text(encoding="utf-8")
        for n in range(1, 14):
            self.assertIn(f"H{n}", text)

    def test_전사를_사람이_한다고_적혀_있다(self):
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("전사", text)
        self.assertIn("uncertain", text)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `python3 -m pytest tests/test_skill_docs.py::HandDiagramSkill -q`
Expected: FAIL — 파일이 없다

- [ ] **Step 3: SKILL.md 를 쓴다**

`.claude/skills/review-hand-diagram/SKILL.md` 를 만든다.

````markdown
---
name: review-hand-diagram
description: 학생이 배포본 브레드보드 판형 위에 손으로 따라 그린 결선도 PDF 를 승인된 참조 결선도와 대조해 쪽별 판정과 증거 크롭을 낸다. 사용자가 "손그림 검토해줘", "따라 그린 거 확인", "브래드보드 작도 확인", "이거 이대로 제출해도 돼?" 등을 요청하거나 /review-hand-diagram 을 호출할 때 사용한다. 홀 좌표가 아니라 넷으로 비교하므로 칩이 몇 행 밀려도 배선이 함께 옮겨져 있으면 통과시킨다.
---

# review-hand-diagram

손그림 결선도를 참조와 대조한다. **판단은 전부 코드가 한다** — 이 문서는
전사(轉寫)를 어떻게 적을지와 결과를 어떻게 낼지만 정한다.

## 왜 코드가 판단하는가

2026-09-08 회차에서 사람이 눈으로 대조하다 **LED 사슬 검사를 통째로 건너뛰었다.**
칩별 전원·미사용핀·신호선만 보고 통과시켰는데, 재검토에서 저항이 한 행 위에
꽂혀 LED 가 아예 안 켜지는 것이 나왔다. 절차서를 더 써서 막을 수 있는 종류가
아니다 — 절차는 이미 알고 있었고 그중 하나를 건너뛴 것이다.

그래서 검사를 `scripts/lab/hand_compare.py` 의 `_RULES` 목록에 넣었고,
`tests/test_hand_compare.py` 가 **`check_` 로 시작하는 함수가 전부 목록에
올라 있는지** 검사한다.

## 인자

`<N주차|실험N> <PDF 경로> [round<N>]`

- 번호 토큰이 없으면 한 줄로 되묻고 중단한다.
- `round<N>` 이 없으면 기존 `round*` 폴더 중 최대 번호 + 1 을 쓴다.

## 실행 절차

### 1. 실험 번호를 폴더 이름으로 옮긴다

사용자는 "실험1", "2주차", "다음 실험" 으로 부르고 경로는 `<실험NN>/` 이다.
손으로 `실험1` 이라고 적지 않는다 — 0 을 안 채우면 `실험10` 이 `실험2` 앞에 선다.

```bash
python3 -c "
from scripts.lab import config
print(config.experiment_dir(<실험번호>))
"
```

주차로 불렸으면 `config.experiments_in_week(<N>)`, 날짜로 불렸으면
`config.next_experiments()` 를 쓴다. 리스트가 둘 이상이면 되묻고 중단한다.

폴더가 없으면 **거절하고** `init-lab-experiment` 를 안내한다. 만들어 주지 않는다.

### 2. 쪽마다 판형을 꺼내고 격자를 덮는다

```bash
python3 -c "
from scripts.lab import hand_grid
import sys
pdf = sys.argv[1]
out = sys.argv[2]
import fitz
n = len(fitz.open(pdf))
for i in range(n):
    b = hand_grid.board_image(pdf, i)
    cal = hand_grid.calibrate(b)
    page = hand_grid.render_page(pdf, i)
    hand_grid.overlay_grid(page, cal, f'{out}/격자/p{i+1}.png')
    print(i+1, b.md5[:8], round(cal.res_x,2), round(cal.res_y,2))
" <PDF> <출력폴더>
```

`GridError` 가 나면 그대로 알리고 중단한다. 판형이 다른 그림 위에 그렸거나
판형이 바뀐 것이다 — 추측으로 넘어가지 않는다.

### 3. 격자 그림을 보고 전사한다

`격자/p<N>.png` 를 읽고 `전사/p<N>.json` 을 쓴다. **이 단계만 사람(vision)이
한다.**

```json
{
  "page": 3,
  "circuit": "e1_nand",
  "title": "2-1 NAND Gate",
  "signed": false,
  "chips": [
    {"label": "74HC08", "block": "좌", "pin1_row": 7},
    {"label": "74HC00", "block": "좌", "pin1_row": 17}
  ],
  "wires": [
    {"color": "빨강", "from": "좌 g7", "to": "좌 중앙VCC레일7행"},
    {"color": "검정", "from": "좌 GND레일7행", "to": "좌 b7"}
  ],
  "leds": [{"tag": "L1", "anode": "좌 c14", "cathode": "좌 c15"}],
  "resistors": [{"tag": "L1", "top": "좌 d15", "bottom": "좌 d16"}],
  "bridges": [{"kind": "gnd", "from": "좌 GND레일29행", "to": "좌 중앙GND레일29행"}],
  "uncertain": []
}
```

전사 규칙:

- **끝점과 점만 홀로 읽는다.** 선이 지나가는 홀은 적지 않는다. 끝점이 아닌
  자리에 점이 찍혀 있으면 그 자리도 꽂힌 것으로 읽는다 — 출력끼리 맞물린
  결함이 그렇게 나타난다.
- 두 행 사이로 보이면 **3배로 확대해** 다시 본다.
  `hand_grid.crop_rows(page, cal, 시작행, 끝행, 경로, scale=3)`.
- 그래도 못 정하면 그 주소를 `uncertain` 에 올린다. 추측으로 채우지 않는다.
- 색은 보이는 대로 적되 **판정에 쓰지 않는다.** 색이 틀려도 끝점이 맞으면
  통과, 색이 맞아도 끝점이 틀리면 오류다.
- 회로 ID(`circuit`)는 제목과 칩 라벨로 고른다. `e1_and` · `e1_or` ·
  `e1_nand` · `e1_nor` · `e1_comb` 중 하나다.

### 4. 대조하고 판정문을 낸다

```bash
python3 -c "
from pathlib import Path
from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import parse_transcript
import sys
out = Path(sys.argv[1]); rnd = int(sys.argv[2])
pages = []
for p in sorted((out/'전사').glob('p*.json')):
    hand = parse_transcript(p)
    ref = hc.reference_diagram(hand.circuit)
    pages.append((hand.page, hand.circuit, hc.compare(ref, hand), hand))
(out/'판정.md').write_text(hc.judgment_markdown(pages, rnd), encoding='utf-8')
for page, _c, fs, _h in pages:
    for f in fs:
        print(page, f)
" <출력폴더> <라운드번호>
```

### 5. 치명 결함마다 증거 크롭을 만들어 보낸다

결함의 `where` 에 행이 들어 있으면 그 행 앞뒤 5행을 잘라 `증거/` 에 넣고
`SendUserFile` 로 보낸다. 사용자가 직접 눈으로 확인할 수 있어야 한다.

### 6. 요약한다

판정문 총평(`제출 가능` / `수정 필요`)을 먼저 말하고, 쪽별로 고칠 선을
**손그림 좌표로** 적는다. 참조 좌표를 그대로 옮기지 않는다 — 칩이 밀려 있으면
참조 좌표가 다른 자리를 가리킨다.

## 검사 목록

| 코드 | 검사 | 등급 |
|---|---|---|
| H1 | 끝점이 실제 홀인가 (레일 빈 행, 63행 밖) | 치명 |
| H2 | 한 홀에 리드 둘 | 치명 |
| H3 | pin 14 는 VCC 에만, pin 7 은 GND 에만 닿는가 | 치명 |
| H4 | 참조가 접지한 미사용 입력이 손그림에서도 묶였는가 | 기능 |
| H5 | 참조가 개방한 미사용 출력에 무언가 물렸는가 | 치명 |
| H6 | 핀 서명 차이 (입력·단 간 연결·LED 도달) | 치명 |
| H7 | LED 사슬: 캐소드~저항 윗다리가 한 줄 · 아랫다리가 GND | 치명 |
| H8 | 레일 연속성: 브리지가 있는가 | 치명 |
| H9 | 브리지 행이 참조와 다름 | 표기 |
| H10 | 칩 pin 1 행이 참조와 다름 | 표기 |
| H11 | 제목이 회로와 불일치 | 표기 |
| H12 | 학번·이름·날짜 미기재 | 표기 |
| H13 | 전사 `uncertain` | 보류 |

**치명·기능이 0건이면 제출 가능이다.** 표기는 막지 않고 별도 줄로 알린다 —
학번 미기재로 제출을 막을지는 채점 관행이지 회로 문제가 아니다.

## 판정할 때 지키는 것

- **행이 밀린 것은 오류가 아니다.** 칩과 배선이 함께 옮겨져 있으면 그림은
  유효하다. H10 이 표기로만 알린다. 참조 좌표와 다르다는 이유로 치명을 매기지
  않는다.
- **참조 그림도 의심한다.** 참조가 `overlap_warnings` 에 올린 배선은 다른 선에
  깔려 잘 안 보이는 자리다. H6 메시지에 그 사실이 붙는다 — 놓친 쪽을 탓하기
  전에 원도를 본다. 2026-09-08 5쪽에서 빠진 `A → 74HC32 pin 1` 이 그런 선이었다.
- **한 결함을 두 번 보고하지 않는다.** 브리지 누락은 H8 만 낸다. 미사용핀은
  H4·H5 가 보고 H6 에서는 뺀다.

## 비-목표

- 결선도를 그리지 않는다. 참조는 `breadboard-diagram` 이 만든다.
- 손그림 선을 자동 벡터화하지 않는다. 검정이 신호선·칩 글자·저항을 겸해서
  색으로 갈리지 않는다.
- 다이오드 극성을 판정하지 않는다. 손그림이 점 하나라 판정 불가다.
- 명세·보고서를 검증하지 않는다. `review-lab-report` 가 한다.
````

- [ ] **Step 4: 통과를 확인한다**

Run: `python3 -m pytest tests/test_skill_docs.py -q`
Expected: PASS

- [ ] **Step 5: 스위트 전체를 돌린다**

Run: `python3 -m pytest tests/ -q`
Expected: PASS — 기존 테스트가 하나도 안 깨져야 한다.

- [ ] **Step 6: 실물로 한 번 돌려 본다**

`/Users/hyunjun_macbook_pro/Downloads/논회실보드 최종본.pdf` 로 3쪽을 검토해
**74HC00 오른쪽 다섯 가닥 누락(H3)** 과 **L1 저항 한 행 위(H7)** 가 나오는지
확인한다. 이 둘은 2026-09-08 회차에서 실제로 있었던 결함이고, 그중 H7 은 1차
검토가 놓쳤던 것이다. 안 나오면 검사기가 틀린 것이다.

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/review-hand-diagram/SKILL.md tests/test_skill_docs.py
git commit -m "feat: 손그림 결선도 검토를 스킬로 만든다 — review-hand-diagram"
```

---

## 자기 점검

**설계 항목 대응**

| 설계 | 과제 |
|---|---|
| 넷 비교 모델 | Task 5 |
| 판형 좌표 맞춤 · 3px 가드 | Task 2 |
| 격자 오버레이 · 크롭 | Task 3 |
| 전사 JSON · 주소 문법 | Task 4 |
| 참조 정답 출처 (`wiring()`) | Task 1, 6 |
| H1~H13 열세 규칙 | Task 7(H1·H2), 8(H3~H5), 9(H6), 10(H7·H8), 11(H9~H13) |
| 판정 등급 · 제출 가능 기준 | Task 11 |
| 회차 관리 (`round<N>`, md5) | Task 12 절차서 2·4단계 |
| 출력 위치 | Task 12 (`test_출력_경로가_박혀_있다` 가 묶는다) |
| 참조 자체 결함 주석 | Task 9 `_reference_hidden` |

**남는 위험 두 가지**

1. **Task 2 의 홀 검출이 28/63 으로 안 모일 수 있다.** 배포본 판형은 998px
   폭이라 여유가 있지만 학생 PDF 에 박힌 래스터는 607px 라 홀이 6px 남짓이다.
   `_merge_to_count` 가 개수를 그대로 알려 주므로 문턱(`0.35`)을 0.25~0.5 에서
   조정한다. **`EXPECTED_COLS`·`EXPECTED_ROWS` 를 바꿔서 맞추지 않는다** —
   판형의 홀 수는 사실이지 조정 손잡이가 아니다.
2. **Task 6 의 `e1_comb` 는 `overlap_policy='warn'` 이다.** 포개짐 2건이 남아
   있어 `verify()` 가 던지지 않고 경고만 낸다. `reference_diagram('e1_comb')`
   는 그래서 열리지만, 그 경고가 `overlaps` 에 담겨 H6 메시지에 주석으로
   붙는다 — 의도한 동작이다.
