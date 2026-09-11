# 손그림 검토 스킬 수정 5건 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 최종 검토에서 나온 결함 다섯을 고쳐, 판형 필터가 시험으로 묶이고 참조 브리지가 실재 홀을 가리키며 결함 하나가 판정문 한두 줄로만 나오게 한다.

**Architecture:** 넷은 서로 독립이라 커밋 넷으로 나눈다. 판형 필터는 회귀 시험을 붙여 커밋하고, 브리지는 렌더러에 기록 리스트를 더해 산문 대조를 없애고, 핀 서명은 레일 넷을 극성 토큰으로 접어 소음을 지우고, H9 는 비교한 것을 그대로 말하게 한다. 전부 이미 있는 흐름의 수정이고 새 파일은 없다.

**Tech Stack:** Python 3.14 표준 라이브러리 + `pillow` + `pymupdf`. 새 의존성 없음. 테스트는 `unittest`.

**Spec:** 이 계획 바로 앞 대화의 설계(`# 손그림 검토 스킬 수정 5건`). 근거가 되는 최초 설계는 `docs/plans/2026-09-08-review-hand-diagram-설계.md` 다.

## Global Constraints

- **주석·문서·테스트 이름은 한국어.** 코드 식별자와 경로만 원문. 저장소 전체 관례다.
- **테스트 이름은 한국어 문장** (`def test_레일_브리지가_실제로_꽂힌_행을_담는다`). `tests/test_breadboard_physical.py` 관례.
- **파이썬은 `.venv/bin/python` 으로 돈다.** 시스템 `python3` 에는 pytest 가 없다.
- **`보고서/실험02`~`실험10` 이 작업 트리에서 삭제돼 있어 스위트 전체는 107건 빨갛다.** 이 작업과 무관하다. **되살리지 않는다.** 검증은 아래 파일들로만 한다.

  ```bash
  .venv/bin/python -m pytest tests/test_hand_grid.py tests/test_hand_transcript.py tests/test_hand_compare.py tests/test_breadboard_wiring.py tests/test_breadboard_physical.py tests/test_breadboard_readability.py tests/test_breadboard_coords.py tests/test_breadboard_diagram_cli.py tests/test_skill_docs.py -q
  ```

  이 명령을 아래에서 **기준 스위트**라 부른다. 시작 시점 기준 181건 통과다.
- **`보고서/실험01/output/손그림검토/round1` 잔해는 그대로 둔다.** 사용자 산출물이다.
- **렌더러 변경은 전부 가산적이다.** 기존 함수의 동작·시그니처를 바꾸지 않는다.
- **판형 좌표 상수를 새로 뜨지 않는다.** 렌더러 `cols`·`r_y()` 가 유일한 권위다.
- **검사기는 산문이 아니라 코드를 읽는다.** 배선 설명 문자열로 분기하지 않는다.

## 파일 구조

새 파일은 없다. 고치는 자리만 적는다.

| 파일 | 이번에 바뀌는 책임 |
|---|---|
| `scripts/lab/hand_grid.py` | `detect_grid()` 의 테두리 필터에 실측 근거 주석을 단다. 로직은 그대로 |
| `tests/test_hand_grid.py` | 합성 가로줄 회귀 시험 클래스를 더한다 |
| `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` | 브리지가 꽂힌 **실재 행**을 기록한다 |
| `tests/test_breadboard_wiring.py` | 브리지 행이 레일 빈 행이 아님을 묶는다 |
| `scripts/lab/hand_compare.py` | `_from_wiring` 의 산문 대조 제거 · `signatures` 레일 접기 · H5 메시지 · H9 비교와 메시지 |
| `tests/test_hand_compare.py` | 위 넷의 계약을 묶는다 |

---

### Task 1: 판형 테두리 필터를 시험으로 묶고 커밋한다

**Files:**
- Modify: `scripts/lab/hand_grid.py` (`detect_grid()` 안의 주석)
- Test: `tests/test_hand_grid.py` (클래스 추가)

**Interfaces:**
- Consumes: `hand_grid.board_image(pdf_path, page_index=0) -> BoardImage`, `hand_grid.detect_grid(data) -> (col_xs, row_ys)`
- Produces: 없음 (기존 API 그대로)

**배경.** `hand_grid.py` 에 커밋되지 않은 3줄이 있다. 인쇄된 판형 테두리를 행 프로파일에서 빼는 필터다. 그 3줄을 지우고 돌리면 **테스트 13건이 전부 통과한다** — 모든 테스트가 배포본만 쓰는데 배포본에서는 이 필터가 완전한 무동작이기 때문이다(행 프로파일 최대 0.333 < 문턱 0.45). 정작 이 필터가 고친 학생 PDF 는 저장소 밖에 있어 시험대에 없다. 이대로 커밋하면 누가 "쓸모없어 보이는 3줄"이라며 지워도 아무도 모른다.

실측값 (2026-09-09):

| 판형 | 홀 행 최대 비율 | 걸러낸 줄 | 필터 효과 |
|---|---|---|---|
| 배포본 998x1345 | 0.333 | 없음 | 무동작 |
| 학생본 607x832 | 0.285 | 1줄, 0.696 | 이게 없으면 구간 94개로 튀어 63행에 못 모인다 |

- [ ] **Step 1: 실패하는 회귀 시험을 쓴다**

`tests/test_hand_grid.py` 의 `class Overlay` **앞에** 아래 클래스를 넣는다. `Overlay` 는 파일 94번째 줄에서 시작한다.

```python
class BorderLine(unittest.TestCase):
    """인쇄된 판형 테두리가 홀 행으로 잡히면 63행으로 안 모인다.

    학생 PDF 에서 실제로 일어난 고장이다 — 아래 테두리 한 줄 때문에 구간이
    94개로 튀었다. 그 PDF 는 저장소 밖에 있으므로 배포본에 같은 줄을 합성한다.
    합성하지 않으면 이 필터는 배포본에서 무동작이라 시험대에 오르지 않는다.
    """

    @classmethod
    def setUpClass(cls):
        cls.board = hand_grid.board_image(HANDOUT)
        cls.clean_cols, cls.clean_rows = hand_grid.detect_grid(cls.board.data)

    def _with_line(self, ratio=0.98):
        """홀 행 **사이**에 폭 `ratio` 만큼 꽉 찬 검은 줄을 그은 래스터."""
        import io
        from PIL import Image, ImageDraw

        im = Image.open(io.BytesIO(self.board.data)).convert("RGB")
        w, _h = im.size
        # 홀 행 두 개의 한가운데 — 진짜 행을 덮지 않는 자리다
        y = int((self.clean_rows[-3] + self.clean_rows[-2]) / 2)
        ImageDraw.Draw(im).rectangle(
            [int(w * 0.02), y, int(w * ratio), y + 2], fill=(0, 0, 0))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()

    def test_꽉_찬_가로줄이_있어도_63행_28열을_찾는다(self):
        cols, rows = hand_grid.detect_grid(self._with_line())
        self.assertEqual(len(rows), 63)
        self.assertEqual(len(cols), 28)

    def test_가로줄이_행_위치를_밀지_않는다(self):
        """개수만 맞고 자리가 밀리면 맞춤 잔차가 관문을 넘는다."""
        _cols, rows = hand_grid.detect_grid(self._with_line())
        for clean, got in zip(self.clean_rows, rows):
            self.assertLess(abs(clean - got), 1.0)

    def test_홀_행은_거르지_않는다(self):
        """홀 행의 어둠 비율은 0.33 을 넘지 않는다 — 문턱 0.45 아래다."""
        self.assertEqual(len(self.clean_rows), 63)
```

- [ ] **Step 2: 필터를 잠시 빼고 시험이 잡는지 확인한다**

`scripts/lab/hand_grid.py` 의 `detect_grid()` 안에서 아래 두 줄을 잠시 주석 처리한다.

```python
    # 인쇄된 판형 테두리나 구분선(너비의 45% 이상이 어두운 행)은 홀이 아니므로 제외한다
    row_prof = [v if v <= 0.45 * span else 0 for v in row_prof]
```

Run: `.venv/bin/python -m pytest tests/test_hand_grid.py::BorderLine -q`
Expected: FAIL — `GridError: 홀 63개로 정리되지 않는다` 또는 개수 불일치. **여기서 통과하면 시험이 아무것도 안 묶은 것이다.** 그때는 `_with_line` 의 `ratio` 를 키우거나 줄 두께를 3px 로 올린다.

- [ ] **Step 3: 필터를 되살리고 근거 주석을 단다**

Step 2 에서 주석 처리한 두 줄을 되살리면서 주석을 아래로 갈아끼운다. 실측값을 남겨야 0.45 가 맨숭맨숭한 상수로 안 보인다.

```python
    span = x1 - x0
    row_prof = [sum(1 for x in range(x0, x1) if px[x, y] < 140)
                for y in range(y0, y1)]
    # 인쇄된 판형 테두리·구분선을 뺀다. 실측(2026-09-09): 홀 행은 폭의
    # 0.29~0.33 까지만 어둡고 테두리는 0.70 이다. 0.45 는 그 사이다.
    # **열 쪽은 이 방법을 못 쓴다** — 홀 열은 모든 행에 홀이 있어 세로로
    # 0.95~1.0 까지 차서 인쇄된 레일선과 안 갈린다. 그래서 열은 폭으로 거른다
    # (아래 `col_runs` 의 `r[1] - r[0] >= 4`).
    row_prof = [v if v <= 0.45 * span else 0 for v in row_prof]
```

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_grid.py -q`
Expected: PASS (16건)

- [ ] **Step 5: 기준 스위트를 돌린다**

Run:
```bash
.venv/bin/python -m pytest tests/test_hand_grid.py tests/test_hand_transcript.py tests/test_hand_compare.py tests/test_breadboard_wiring.py tests/test_breadboard_physical.py tests/test_breadboard_readability.py tests/test_breadboard_coords.py tests/test_breadboard_diagram_cli.py tests/test_skill_docs.py -q
```
Expected: PASS (184건)

- [ ] **Step 6: 실물 세 판형이 여전히 맞춰지는지 본다**

```bash
.venv/bin/python -c "
from scripts.lab import hand_grid as hg
for p in ['강의노트/공지사항/Breadboard.pdf',
          '/Users/hyunjun_macbook_pro/Downloads/논회실보드 최종본.pdf',
          '/Users/hyunjun_macbook_pro/Downloads/논실 2-1 수정.pdf']:
    b = hg.board_image(p); c = hg.calibrate(b)
    print(p.split('/')[-1], '잔차', round(c.res_x,2), round(c.res_y,2))
"
```
Expected: 셋 다 잔차 1px 미만. 학생 PDF 둘이 없으면 배포본만 확인하고 넘어간다.

- [ ] **Step 7: 커밋**

```bash
git add scripts/lab/hand_grid.py tests/test_hand_grid.py
git commit -m "fix: 판형 테두리 필터에 회귀 시험을 붙인다 — 지워도 조용하던 3줄"
```

---

### Task 2: 참조 브리지가 실재하는 홀을 가리킨다

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py` (`__init__` 113번째 줄 근처, `bridge_rails()`, `wiring()`)
- Modify: `scripts/lab/hand_compare.py` (`_from_wiring()`, 194번째 줄)
- Test: `tests/test_breadboard_wiring.py`, `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: `BreadboardRenderer.sym(x, row) -> (block, col, row) | None`
- Produces:
  - `BreadboardRenderer.bridges` — `[(kind, (block, col, row), (block, col, row))]`, 실제로 꽂힌 행
  - `wiring()['bridges']` — 위 리스트 그대로
  - `hand_compare._from_wiring(w, circuit_id) -> Diagram` — `wires` 에서 브리지를 뺀다

**배경.** `wiring()` 이 `self.sym(a, 1)` 로 행을 1 로 박는데 **1행은 레일 빈 행**이다. 실제 브리지는 29·30행이다. `_bridged` 가 `(kind, min_x, max_x)` 만 담아 행을 버리기 때문이다.

지금은 `_from_wiring` 이 `desc == '레일 브리지'` 문자열을 맞춰 우회한다. 그 문구를 바꾸면 폴백이 켜지고 회로마다 H1 치명이 4건 헛난다. 실증됐다:

```
[치명] H1 좌 GND레일1행 — 레일 1행에는 홀이 없다 …
[치명] H1 좌 중앙GND레일1행 — …
[치명] H1 좌 VCC레일1행 — …
[치명] H1 좌 중앙VCC레일1행 — …
```

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_breadboard_wiring.py` 의 `test_레일_브리지가_열_이름_쌍으로_남는다` (94번째 줄) **바로 아래에** 더한다.

```python
    def test_레일_브리지가_실제로_꽂힌_행을_담는다(self):
        """1행을 박아 두면 레일 빈 행이라 손그림 검토가 H1 을 헛낸다.

        `_bridged` 는 중복 방지 키라 행이 없다. 행을 따로 기록해야 한다.
        """
        for kind, a, b in self.and_bb.wiring()['bridges']:
            self.assertEqual(a[2], b[2], kind)
            self.assertNotIn(a[2], self.mod.RAIL_GAP_ROWS)
        rows = {k: a[2] for k, a, _b in self.and_bb.wiring()['bridges']}
        self.assertEqual(rows, {'gnd': 29, 'vcc': 30})
```

`tests/test_hand_compare.py` 의 `class Reference` 안에 더한다.

```python
    def test_참조_배선에는_브리지가_없다(self):
        """브리지가 wires 와 bridges 양쪽에 있으면 `check_holes` 가 같은 홀을
        두 번 세어 H2 가 헛난다."""
        ends = {frozenset((a, b)) for _k, a, b in self.nand.bridges}
        self.assertTrue(ends)
        for w in self.nand.wires:
            if w['frm'][0] == 'hole' and w['to'][0] == 'hole':
                self.assertNotIn(frozenset((w['frm'][1], w['to'][1])), ends)

    def test_배선_설명_문구가_바뀌어도_브리지가_남는다(self):
        """산문 대조를 쓰면 문구 한 글자에 참조 브리지가 통째로 사라지고,
        폴백이 1행을 주어 회로마다 H1 치명이 4건 헛난다."""
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            bb = hc.load_renderer().build_e1_nand(os.path.join(t, 'x.png'))
        w = bb.wiring()
        for x in w['wires']:
            if x.get('desc') == '레일 브리지':
                x['desc'] = '레일 브리지(전원 연결)'
        d = hc._from_wiring(w, 'e1_nand')
        self.assertEqual(len(d.bridges), 2)
        self.assertEqual([f for f in hc.check_holes(d, d) if f.rule == 'H1'], [])
```

- [ ] **Step 2: 실패를 확인한다**

Run:
```bash
.venv/bin/python -m pytest "tests/test_breadboard_wiring.py::Wiring::test_레일_브리지가_실제로_꽂힌_행을_담는다" "tests/test_hand_compare.py::Reference::test_배선_설명_문구가_바뀌어도_브리지가_남는다" -q
```
Expected: FAIL — 앞엣것은 `1 not in RAIL_GAP_ROWS` 단언 실패, 뒤엣것은 H1 이 4건 나온다.

- [ ] **Step 3: 렌더러가 브리지 행을 기록한다**

`render_breadboard.py` 의 `__init__` 에서 `self._bridged = set()` (113번째 줄) 다음 줄에 더한다.

```python
        # 실제로 꽂힌 브리지. `_bridged` 는 중복 방지 키(kind, x, x)라 **행이 없다**.
        # 행을 안 담으면 `wiring()` 이 1행을 주는데 1행은 레일 빈 행이라,
        # 손그림 검토가 참조 브리지마다 H1 치명을 헛낸다
        self.bridges = []
```

`bridge_rails()` 의 `self._uf_union(x_a, x_b)` 다음 줄에 더한다.

```python
        self.bridges.append((kind, self.sym(x_a, row), self.sym(x_b, row)))
```

`wiring()` 의 브리지 계산 두 줄을 지운다.

```python
        bridges = [(kind, self.sym(a, 1), self.sym(b, 1))
                   for kind, a, b in sorted(self._bridged)]
```

그리고 반환 사전의 `'bridges'` 값을 갈아끼운다.

```python
            'bridges': list(self.bridges),
```

- [ ] **Step 4: `_from_wiring` 이 산문 대신 홀 쌍으로 거른다**

`scripts/lab/hand_compare.py` 의 `_from_wiring()` 전체를 아래로 바꾼다.

```python
def _from_wiring(w, circuit_id):
    """`wiring()` 출력 -> `Diagram`. 손그림 쪽과 같은 모양으로 맞춘다.

    브리지는 `wires` 에서 빼고 `bridges` 로만 보낸다 — 양쪽에 두면
    `check_holes` 가 같은 홀을 두 번 세어 H2 가 헛난다. 거르는 기준은
    **끝점 홀 쌍**이다. 배선 설명 문구로 맞추면 문구가 바뀔 때 조용히 깨지고,
    그때 폴백이 1행짜리 브리지를 내어 H1 이 회로마다 4건 헛난다.
    """
    bridges = [(kind, a, b) for kind, a, b in w['bridges']
               if a is not None and b is not None]
    bridge_ends = {frozenset((a, b)) for _kind, a, b in bridges}
    wires = [dict(x) for x in w['wires']
             if not (x['frm'][0] == 'hole' and x['to'][0] == 'hole'
                     and frozenset((x['frm'][1], x['to'][1])) in bridge_ends)]
    by_hole = {c['res_top']: c['tag'] for c in w['chains']}
    resistors = []
    for r in w['resistors']:
        new_r = dict(r)
        new_r['tag'] = by_hole.get(new_r['top'], new_r.get('label', ''))
        resistors.append(new_r)
    return Diagram(
        chips=[dict(c) for c in w['chips']],
        wires=wires,
        leds=[dict(l) for l in w['leds']],
        resistors=resistors,
        chains=[dict(c) for c in w['chains']],
        unused_inputs=[dict(u) for u in w['unused_inputs']],
        unused_outputs=[dict(u) for u in w['unused_outputs']],
        bridges=bridges,
        overlaps=list(w['overlaps']),
        circuit=circuit_id)
```

- [ ] **Step 5: 낡은 산문 대조를 테스트에서도 뺀다**

`tests/test_hand_compare.py` 의 `test_H8_브리지가_없으면_잡는다` (411번째 줄 근처)에서 배선 걸러내는 줄을 지운다. 이제 `_from_wiring` 이 이미 뺐으므로 `hand.bridges = []` 만으로 브리지가 사라진다.

```python
    def test_H8_브리지가_없으면_잡는다(self):
        ref, hand = self._pair()
        hand.bridges = []
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H8']
        self.assertTrue(found)
        self.assertEqual(found[0].grade, '치명')
```

- [ ] **Step 6: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_breadboard_wiring.py tests/test_hand_compare.py -q`
Expected: PASS

- [ ] **Step 7: 자기대조가 여전히 0건인지 본다**

브리지 경로를 갈아끼웠으니 참조를 참조와 견주어 아무것도 안 나오는지가 관문이다.

```bash
.venv/bin/python -c "
from scripts.lab import hand_compare as hc
import copy
for cid in hc.CIRCUITS:
    ref = hc.reference_diagram(cid)
    hand = copy.deepcopy(ref); hand.signed = True; hand.title = cid
    bad = [f for f in hc.compare(ref, hand) if f.grade != '표기']
    print(cid, len(bad), [str(x) for x in bad][:2])
" 2>&1 | grep -v SUCCESS
```
Expected: 여덟 줄 전부 `0 []`

- [ ] **Step 8: 기준 스위트를 돌린다**

Run: 위 **기준 스위트** 명령
Expected: PASS

- [ ] **Step 9: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py scripts/lab/hand_compare.py tests/test_breadboard_wiring.py tests/test_hand_compare.py
git commit -m "fix: 브리지가 꽂힌 실재 행을 기록한다 — 산문 대조를 걷는다"
```

---

### Task 3: 레일 넷을 서명에서 접어 H6 소음을 지운다

**Files:**
- Modify: `scripts/lab/hand_compare.py` (`signatures()`, `check_power()` 335번째 줄)
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: `build_nets(diagram)`, `attachments(diagram, nets)`, `chip_keys(diagram)`, `node_of(hole)`, `_describe(item)`
- Produces: `signatures(diagram) -> dict[(chip_key, pin), frozenset]` — 레일이 든 넷은 극성 토큰만 남는다

**배경.** 원인은 H7 이 아니라 구조다. 입력은 GND 레일 홀에서 b열로 들어오도록 그려지므로(`_input_jumper`) **입력 핀이 GND 레일 넷 위에 앉는다.** 실험01 NAND 참조에서 그 넷의 부착물이 21개고 입력 핀 서명 크기가 20이다. 레일 어디가 흔들려도 입력 핀 전부가 H6 을 낸다.

핀 넷에 레일이 있으면 서명을 극성 토큰만으로 줄인다. 그 핀의 전기적 사실은 "GND 에 물려 있다"가 전부이고 같은 레일에 누가 더 붙어 있는지는 그 핀과 무관하다. 레일끼리의 관계는 H3·H4·H8 이 따로 본다.

시뮬레이션으로 미리 확인한 효과:

| 경우 | 지금 | 접은 뒤 |
|---|---|---|
| `round2` 실물 L1 저항 오배치 | H6 5건 | 2건, 둘 다 진짜 자리 |
| 미사용 입력 접지 1가닥 제거 | H6 3건 (허위) | 0건, H4 만 남음 |
| 입력 C 누락 (4쪽 실제 결함) | 잡음 | 잡음 |
| 자기대조 8개 회로 | 0건 | 0건 |

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_compare.py` 의 `class Signals` 안에 더한다.

```python
    def test_레일_넷은_극성_토큰_하나로_접힌다(self):
        """입력은 GND 레일 홀에서 들어오도록 그려져 입력 핀이 GND 넷에 앉는다.
        실험01 NAND 에서 그 넷 부착물이 21개다 — 접지 않으면 레일 어디가
        흔들려도 입력 핀 전부가 H6 을 낸다."""
        ref = hc.reference_diagram('e1_nand')
        sig = hc.signatures(ref)
        self.assertEqual(sig[('74HC08', 1)], frozenset({('RAIL', 'GND')}))
        self.assertEqual(sig[('74HC08', 7)], frozenset({('RAIL', 'GND')}))
        self.assertEqual(sig[('74HC08', 14)], frozenset({('RAIL', 'VCC')}))

    def test_레일이_없는_넷은_그대로_열거된다(self):
        """칩 사이 연결은 접으면 안 된다 — 거기가 신호선이다."""
        ref = hc.reference_diagram('e1_nand')
        sig = hc.signatures(ref)
        self.assertIn(('PIN', '74HC00', 1), sig[('74HC08', 3)])

    def test_미사용_입력_접지가_빠져도_입력핀은_조용하다(self):
        """접기 전에는 이 한 가닥 때문에 H6 이 3건 헛났다."""
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        hand.signed = True
        node = hc.node_of(hand.chips[0]['pins'][9])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        fs = hc.compare(ref, hand)
        self.assertEqual([f for f in fs if f.rule == 'H6'], [])
        self.assertTrue([f for f in fs if f.rule == 'H4'])

    def test_입력이_통째로_빠지면_접은_뒤에도_잡는다(self):
        """접기가 진짜 결함까지 삼키면 안 된다 — 4쪽의 실제 결함이다."""
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        hand.signed = True
        node = hc.node_of(hand.chips[1]['pins'][2])
        hand.wires = [w for w in hand.wires
                      if hc._endpoint_node(w['frm']) != node
                      and hc._endpoint_node(w['to']) != node]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H6']
        self.assertTrue(found)
        self.assertIn('74HC00 pin 2', found[0].where)
        self.assertIn('GND 레일', found[0].message)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest "tests/test_hand_compare.py::Signals" -q`
Expected: FAIL — `test_레일_넷은_극성_토큰_하나로_접힌다` 가 20개짜리 집합을 받아 실패하고, `test_미사용_입력_접지가_빠져도_입력핀은_조용하다` 가 H6 3건을 받아 실패한다.

- [ ] **Step 3: `signatures()` 가 레일 넷을 접는다**

`scripts/lab/hand_compare.py` 의 `signatures()` 전체를 아래로 바꾼다.

```python
def signatures(diagram):
    """(칩 이름, 핀 번호) -> 그 핀 넷의 부착물. 자기 자신은 뺀다.

    **레일이 든 넷은 극성 토큰으로 접는다.** 입력은 GND 레일 홀에서 b열로
    들어오도록 그려져(`_input_jumper`) 입력 핀이 GND 넷 위에 앉는다 — 실험01
    NAND 참조에서 그 넷 부착물이 21개고 입력 핀 서명이 20개다. 접지 않으면
    레일 어디가 흔들려도 입력 핀 전부가 H6 을 낸다. 미사용 입력 한 가닥만
    빼도 H6 이 3건 헛났다.

    그 핀의 전기적 사실은 '어느 극성에 물렸는가' 가 전부이고, 같은 레일에
    누가 더 붙어 있는지는 그 핀과 무관하다. 레일끼리의 관계는 H3·H4·H8 이
    따로 본다. 레일이 없는 넷(칩 사이 연결·LED 사슬)은 그대로 열거한다 —
    거기가 신호선이라 낱낱이 봐야 한다.
    """
    nets = build_nets(diagram)
    att = attachments(diagram, nets)
    out = {}
    for key, ch in zip(chip_keys(diagram), diagram.chips):
        for pin, hole in ch['pins'].items():
            rep = nets[node_of(hole)]
            seen = att.get(rep, set()) - {('PIN', key, pin)}
            rails = {a for a in seen if a[0] == 'RAIL'}
            out[(key, pin)] = frozenset(rails) if rails else frozenset(seen)
    return out
```

- [ ] **Step 4: H5 메시지가 사람 말을 쓰게 한다**

접은 뒤에는 H5 가 `('RAIL', 'GND')` 를 그대로 찍는다. `check_power()` 의 335번째 줄을 바꾼다.

```python
            what = ', '.join(sorted(_describe(s) for s in sig))
```

`_describe` 는 `check_power` 보다 아래에 정의돼 있지만 호출 시점에는 모듈이 다 읽힌 뒤라 문제없다.

- [ ] **Step 5: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py -q`
Expected: PASS

- [ ] **Step 6: 실물 판정이 줄었는지 본다**

이 과제의 목적이 그대로 걸린 자리다. `round2` 전사를 다시 대조해 치명이 6건에서 3건이 되고 H7 이 그대로 남는지 본다.

```bash
.venv/bin/python -c "
from pathlib import Path
from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import parse_transcript
hand = parse_transcript(Path('보고서/실험01/output/손그림검토/round2/전사/p1.json'))
ref = hc.reference_diagram(hand.circuit)
fs = hc.compare(ref, hand)
print('치명', sum(1 for f in fs if f.grade == '치명'))
for f in fs:
    if f.grade == '치명':
        print(' ', f)
" 2>&1 | grep -v SUCCESS
```
Expected: 치명 3건. H7 하나(`L1 (좌 d17)` 저항 아랫다리가 GND 에 안 닿는다)와 H6 둘(`74HC00 pin 1`, `74HC08 pin 3` 에 L1 저항 아랫다리가 더 있다). 셋 다 같은 결함을 가리키되 자리가 정확해야 한다.

`round2/전사/p1.json` 이 없으면 이 단계를 건너뛰고 Step 7 로 간다.

- [ ] **Step 7: 자기대조와 기준 스위트**

```bash
.venv/bin/python -c "
from scripts.lab import hand_compare as hc
import copy
for cid in hc.CIRCUITS:
    ref = hc.reference_diagram(cid)
    hand = copy.deepcopy(ref); hand.signed = True; hand.title = cid
    print(cid, len([f for f in hc.compare(ref, hand) if f.grade != '표기']))
" 2>&1 | grep -v SUCCESS
```
Expected: 여덟 줄 전부 `0`

Run: 위 **기준 스위트** 명령
Expected: PASS

- [ ] **Step 8: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "fix: 레일 넷을 서명에서 접는다 — 한 결함이 여섯 줄로 번지던 것"
```

---

### Task 4: H9 가 비교한 것을 그대로 말한다

**Files:**
- Modify: `scripts/lab/hand_compare.py` (`check_placement()`, 510~517번째 줄)
- Test: `tests/test_hand_compare.py`

**Interfaces:**
- Consumes: `HandFinding(rule, grade, where, message)`
- Produces: `check_placement(ref, hand) -> list[HandFinding]` — H9 는 행 집합만 비교한다

**배경.** 두 가지다.

첫째, 비교는 `(종류, 행)` 쌍으로 하는데 메시지는 행만 찍는다. 전사가 `kind` 를 빠뜨리면 이런 문장이 나온다. 실증됐다.

```
[표기] H9 레일 브리지 — 참조는 [29, 30]행인데 손그림은 [29, 30]행이다. …
```

둘째, "30행 아래 브리지는 전원을 못 올린다"가 하드코딩돼 있다. `round2` 는 28·29행으로 30행 **위**인데도 그 경고를 받았다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hand_compare.py` 의 `class Paperwork` **앞에** 아래 클래스를 넣는다.

```python
class BridgeRows(unittest.TestCase):
    """H9 는 행만 말하므로 행만 비교해야 한다."""

    def _pair(self):
        ref = hc.reference_diagram('e1_nand')
        hand = hc.reference_diagram('e1_nand')
        hand.signed = True
        hand.title = '2-1 NAND Gate'
        return ref, hand

    def test_종류가_없어도_행이_같으면_조용하다(self):
        """전사가 kind 를 빠뜨리면 '[29,30]인데 [29,30]이다' 가 나왔다."""
        ref, hand = self._pair()
        hand.bridges = [('', a, b) for _k, a, b in hand.bridges]
        self.assertEqual([f for f in hc.compare(ref, hand) if f.rule == 'H9'], [])

    def test_아래로_내려간_브리지에는_경고를_붙인다(self):
        ref, hand = self._pair()
        hand.bridges = [(k, (a[0], a[1], a[2] + 4), (b[0], b[1], b[2] + 4))
                        for k, a, b in hand.bridges]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H9']
        self.assertTrue(found)
        self.assertIn('아래', found[0].message)
        self.assertIn('[33, 34]', found[0].message)

    def test_위로_올라간_브리지에는_경고를_안_붙인다(self):
        """round2 는 28·29행인데 '30행 아래' 경고를 받았다."""
        ref, hand = self._pair()
        hand.bridges = [(k, (a[0], a[1], a[2] - 1), (b[0], b[1], b[2] - 1))
                        for k, a, b in hand.bridges]
        found = [f for f in hc.compare(ref, hand) if f.rule == 'H9']
        self.assertTrue(found)
        self.assertNotIn('아래', found[0].message)
        self.assertIn('영향이 없다', found[0].message)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest "tests/test_hand_compare.py::BridgeRows" -q`
Expected: FAIL — 세 건 모두. 첫째는 H9 가 나서 실패, 둘째·셋째는 문구가 안 맞아 실패.

- [ ] **Step 3: 행만 비교하고 방향을 본다**

`scripts/lab/hand_compare.py` 의 `check_placement()` 안 브리지 부분(510~517번째 줄)을 아래로 바꾼다.

```python
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
```

- [ ] **Step 4: 통과를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_hand_compare.py -q`
Expected: PASS

- [ ] **Step 5: 기준 스위트를 돌린다**

Run: 위 **기준 스위트** 명령
Expected: PASS

- [ ] **Step 6: 실물로 마지막 확인**

```bash
.venv/bin/python -c "
from pathlib import Path
from scripts.lab import hand_compare as hc
from scripts.lab.hand_transcript import parse_transcript
hand = parse_transcript(Path('보고서/실험01/output/손그림검토/round2/전사/p1.json'))
ref = hc.reference_diagram(hand.circuit)
for f in hc.compare(ref, hand):
    print(f)
" 2>&1 | grep -v SUCCESS
```
Expected: 치명 3건 + 표기 3건. H9 줄이 "참조는 [29, 30]행인데 손그림은 [28, 29]행이다. 도면상 같은 노드라 회로에는 영향이 없다" 로 나온다.

`round2/전사/p1.json` 이 없으면 건너뛴다.

- [ ] **Step 7: 커밋**

```bash
git add scripts/lab/hand_compare.py tests/test_hand_compare.py
git commit -m "fix: H9 가 비교한 것을 그대로 말한다 — 행만 보고 방향을 본다"
```

---

## 자기 점검

**설계 항목 대응**

| 설계 수정 | 과제 |
|---|---|
| 수정 1 · 레일 넷 접기 (H6 소음) | Task 3 |
| 수정 2 · 브리지 실재 행 | Task 2 |
| 수정 3 · H9 비교·메시지 | Task 4 |
| 수정 4 · 판형 회귀 시험 + 근거 주석 | Task 1 |
| 수정 5 · 미커밋 3줄 커밋 | Task 1 Step 7 |
| 곁들임 · H5 메시지 `_describe` | Task 3 Step 4 |
| 커밋 넷으로 분리 | Task 1~4 각 마지막 단계 |

**하지 않는 것** — `_reference_hidden` 되살리기, H6 넷 단위 묶기, `보고서/실험02`~`실험10` 복원, `round1` 잔해 정리. 설계의 "Not in this round" 그대로다.

**과제 사이 의존**

Task 1 은 독립이다. Task 2 는 Task 3·4 보다 먼저여야 한다 — `_from_wiring` 이 `Diagram.bridges` 를 채우는 방식을 바꾸고, Task 4 의 H9 가 그 값을 읽는다. Task 3 과 Task 4 는 서로 독립이지만 계획 순서대로 가면 된다.

**남는 위험 둘**

1. **Task 1 Step 2 가 통과해 버릴 수 있다.** 합성 줄이 `_merge_to_count` 의 병합 간격 안에서 이웃 홀 행과 붙어 버리면 63개가 그대로 나온다. 그때는 줄을 홀 행 사이 한가운데가 아니라 행 간격의 40% 지점으로 옮기거나 두께를 3px 로 올린다. **`EXPECTED_ROWS` 를 바꿔서 맞추지 않는다** — 판형의 행 수는 사실이지 조정 손잡이가 아니다.
2. **Task 3 의 접기가 아직 못 본 결함을 삼킬 수 있다.** 지금 확인한 건 실험01 다섯 회로다. 레일에 물리는 것이 더 많은 실험02 계열 회로가 손그림 검토에 들어올 때 다시 잰다. 그 시점의 관문은 이 계획이 쓴 자기대조 0건 검사다.
