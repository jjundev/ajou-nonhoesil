# 손그림 모사 부품 그리기 안내 PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 손그림 모사 시험판과 같은 그림에서 선은 전부 회색(`KEEP`), 팀원이 새로 그릴 칩·LED·저항·입력 이름 배지만 색으로 그린 안내 PNG 와 A4 한 쪽 PDF(그림 + 부품표)를 `hand_sim --guide` 한 번으로 낸다.

**Architecture:** 렌더러에 `hand_guide` 옵션을 더한다 — hand 모드의 선 흔들기는 그대로 두고 선 색만 `KEEP` 으로, `_blank_parts` 는 비우지 않고 평소처럼 그린다. 부품 그리기는 난수를 안 쓰므로 같은 시드면 회색 선이 시험판 선과 픽셀 단위로 같은 자리다. PDF 는 `trace_guide.make_pdf` 와 같은 순서(임시 폴더 → `html_to_pdf` → 쪽 검사 → 옮김)로 `scripts/lab/hand_sim.py` 가 만든다.

**Tech Stack:** Python 3, Pillow, pypdf, headless Chrome(`scripts/lab/html2pdf.html_to_pdf`), unittest/pytest(`-n0` 로 단독 실행).

**Spec:** 이 대화의 grill-yourself 설계 "팀원 전달용 '부품 그리기' 안내 PDF" (확정: #6 `tmp/hand-sim/`·미커밋, #7 그림+부품표, #8 안내 한 쪽만). 파일로 남긴 spec 은 없다 — 이 계획의 Global Constraints 가 그 값을 옮긴다.

## Global Constraints

- 범위는 실험04 MUX(`build_e4_mux`) 한 장. DMUX·다른 주차는 손대지 않는다.
- 회색은 `KEEP = (165, 165, 165, 255)` (`engine/base.py`). 새 색을 만들지 않는다.
- 안내 모드에서 회색: `step_wire` 배선 전부(입력 점퍼 보라 포함)와 끝점, `connect_unused_inputs` 선·끝점, `_blank_parts` 밖에서 그리는 `signal_tag`(프로브 배지).
- 안내 모드에서 원래 색: `draw_chip`·`draw_led`(LED 신호 이름 포함)·`draw_resistor`, 입력 이름 배지(`INPUT`).
- `hand_guide=True` 인데 `hand is None` 이면 `ValueError('hand_guide 는 hand 와 함께 준다')`.
- `hand=None` 그림은 바이트 불변 — 실험04 14장 픽셀 해시를 작업 전 커밋 렌더와 대조한다.
- 출력: `tmp/hand-sim/실험04_1-1_부품그리기_4x1MUX.png` 와 `…_부품그리기_4x1MUX.pdf`. 커밋하지 않는다(`tmp/` 는 무시 대상).
- PDF 는 A4 세로 정확히 1쪽, 그림 1개. 넘치면 `ValueError` 로 멈추고 이전 PDF 는 그대로 둔다.
- 범례 문구(그대로): `회색 선은 이미 그려져 있어요 · 색으로 된 칩·LED·저항·입력 이름만 그리세요`
- 부품표 열: `종류 · 이름 · 자리`. 행 순서: 칩 → LED → 저항 → 입력, 각 종류 안은 엔진 기록 순서.

## Review Focus

- 회색 선이 시험판 선과 어긋남(난수 소비 순서가 두 모드에서 달라짐) — 겹쳐 보는 팀원이 바로 알아챈다. Task 1 의 `test_안내판_회색선은_시험판_선과_같은_자리` 가 잡는다.
- 프로브 배지가 있는 완성본에서 프로브 배지가 색으로 남음 — MUX 완성본엔 프로브가 없어 그림 시험이 못 본다. Task 1 에 `signal_tag` 단위 시험(`test_안내판_부품_밖_배지는_회색`)을 둔다.
- `--guide` 를 다른 완성본(DMUX)에 주면 빌더가 `hand_guide` 를 안 받아 `TypeError` 로 터짐 — 사람이 읽는 오류여야 한다. Task 2 의 `test_안내판을_못_받는_빌더는_이름과_함께_멈춘다`.
- 부품표가 길어 두 쪽으로 넘침 — Task 2 의 쪽 검사(`check_guide_pdf`)와 그 시험.
- 입력 행의 홀이 칩 쪽 끝이 아니라 레일 쪽 끝이어야 함(팀원이 이름을 적는 자리) — Task 2 의 `test_부품표_입력은_레일_쪽_끝`.

---

### Task 1: 렌더러 `hand_guide` — 선은 회색, 부품은 색

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/renderer.py` (`__init__` 의 hand 검사 옆, `step_wire` 색 결정 `if kept or view == 'faded'`, `connect_unused_inputs` 의 `col = KEEP if kept or view == 'faded' else WIRE[rail]`, `signal_tag`, `_blank_parts`)
- Modify: `보고서/실험04/결선도/배치.py:393-404` (`build_e4_mux`)
- Test: `tests/test_breadboard_hand.py` (`HandRender` 에 더한다)

**Interfaces:**
- Produces: `BreadboardRenderer(..., hand=None, hand_guide=False)`, 속성 `self.hand_guide: bool`; `build_e4_mux(output_path, template_path=None, stage=None, baseline=None, layer=None, hand=None, hand_guide=False)`. Task 2 는 `fn(str(out), hand=seed, hand_guide=True)` 로 부르고 돌려받은 렌더러의 `chips`·`led_chains`·`resistors`·`inputs`·`_segments`·`addr`·`_sym_addr` 를 읽는다.

- [ ] **Step 1: 실패하는 시험을 쓴다** — `HandRender` 에 `_render(self, hand, guide=False)` 로 `hand_guide=guide` 를 넘기게 고치고 아래를 더한다. `WIRE` 는 `self.mod.WIRE`.

```python
def test_안내판은_선이_회색이고_부품은_색이다(self):
    bb, _, _ = self._render(42, guide=True)
    for col in self.mod.WIRE.values():
        self.assertEqual(self._count(bb, col), 0, col)
    self.assertGreater(self._count(bb, self.mod.KEEP), 0)
    for rgba in [(30, 33, 36, 255), (220, 20, 20, 240), (225, 195, 145, 255), self.mod.INPUT]:
        self.assertGreater(self._count(bb, rgba), 0, rgba)

def test_안내판_회색선은_시험판_선과_같은_자리(self):
    blank, _, _ = self._render(42)
    guide, _, _ = self._render(42, guide=True)
    wire_cols = set(self.mod.WIRE.values()) | {self.mod.INPUT}
    a, b = blank.overlay.load(), guide.overlay.load()
    W, H = blank.overlay.size
    hits = [(x, y) for y in range(0, H, 2) for x in range(0, W, 2) if a[x, y] in wire_cols]
    same = sum(1 for x, y in hits if b[x, y] == self.mod.KEEP)
    self.assertGreater(same / len(hits), 0.99)

def test_안내판도_배치는_같다(self):
    a, _, _ = self._render(42)
    b, _, _ = self._render(42, guide=True)
    for attr in ('_segments', 'tag_boxes', 'chips', 'leds', 'resistors', 'inputs'):
        self.assertEqual(getattr(a, attr), getattr(b, attr), attr)

def test_안내판은_hand_없이_못_준다(self):
    with self.assertRaises(ValueError):
        self.mod.BreadboardRenderer(None, board='v1', hand_guide=True)

def test_안내판_부품_밖_배지는_회색(self):
    bb = self.mod.BreadboardRenderer(None, board='v1', hand=1, hand_guide=True)
    bb.signal_tag('P', 300, 300, col=self.mod.PROBE)
    self.assertEqual(self._count(bb, self.mod.PROBE), 0)
    self.assertGreater(self._count(bb, self.mod.KEEP), 0)
```

- [ ] **Step 2: 돌려서 실패를 본다**

Run: `.venv/bin/python -m pytest -n0 -q tests/test_breadboard_hand.py -k 안내판`
Expected: FAIL — `TypeError: ... unexpected keyword argument 'hand_guide'`

- [ ] **Step 3: 구현한다**
  - `__init__` 에 `hand_guide=False` 를 받고 검사 뒤 `self.hand_guide = hand_guide`.
  - `step_wire`·`connect_unused_inputs` 의 회색 조건에 `or self.hand_guide`.
  - `_blank_parts`: `if self.hand is None or self.hand_guide:` 면 평소대로 그리되, 그 동안 `self._in_parts = True` (try/finally 로 되돌림) — `signal_tag` 는 `self.hand_guide and not self._in_parts` 일 때 `col = KEEP`. `_in_parts` 기본값 `False` 를 `__init__` 에.
  - `build_e4_mux` 에 `hand_guide=False` 를 받아 `BreadboardRenderer(..., hand=hand, hand_guide=hand_guide)` 로 넘긴다.

- [ ] **Step 4: 통과를 본다**

Run: `.venv/bin/python -m pytest -n0 -q tests/test_breadboard_hand.py`
Expected: 전부 PASS (기존 19 + 새 5)

- [ ] **Step 5: hand=None 픽셀 불변을 잰다** — 각 `build_e4*` 를 임시 폴더에 렌더해 `Image.open(p).tobytes()` 의 sha256 을 찍는 스크래치 스크립트를 `git stash` 전후로 돌려 diff.
Expected: 14줄, 차이 없음.

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/engine/renderer.py 보고서/실험04/결선도/배치.py tests/test_breadboard_hand.py
git commit -m "feat(breadboard): hand_guide — 선은 회색, 그릴 부품만 색으로 그린다"
```

---

### Task 2: `hand_sim --guide` — 안내 PNG + 한 쪽 PDF

**Files:**
- Modify: `scripts/lab/hand_sim.py`
- Test: `tests/test_breadboard_hand.py` (`HandSimScript` 에 더한다)

**Interfaces:**
- Consumes: Task 1 의 `build_e4_mux(..., hand=, hand_guide=True)` 와 렌더러 속성.
- Produces:
  - `guide_rows(bb) -> list[tuple[str, str, str]]` — `(종류, 이름, 자리)`.
    - 칩: `('칩', label, f'{"좌" if block == "left" else "우"} 블록 · pin 1 = {pin1_row}행')`
    - LED: `('LED', tag, f'애노드 {bb._sym_addr(anode)} · 캐소드 {bb._sym_addr(cathode)}')` (`bb.led_chains`)
    - 저항: `('저항', label, f'{bb._sym_addr(top)} → {bb._sym_addr(bottom)}')` (`bb.resistors`)
    - 입력: `('입력', name, f'레일 쪽 끝 {bb.addr(*bb._segments[seg][1][0])} 옆')` (`bb.inputs`)
  - `render_guide_html(title: str, image_name: str, rows) -> str`
  - `check_guide_pdf(path) -> None` — 1쪽·그림 1개가 아니면 `ValueError`
  - `main([... '--guide'])` 은 `(시험판 PNG, 안내 PNG, 안내 PDF)` 튜플을, `--guide` 없으면 지금처럼 시험판 경로 하나를 돌려준다.

- [ ] **Step 1: 실패하는 시험을 쓴다**

```python
def test_부품표에_칩_LED_저항_입력이_다_있다(self):
    from scripts.lab import hand_sim
    bb = self._guide_board()      # build_e4_mux(tmp, hand=1, hand_guide=True) 를 돌려준다
    rows = hand_sim.guide_rows(bb)
    kinds = [k for k, _, _ in rows]
    self.assertEqual(kinds, sorted(kinds, key=['칩', 'LED', '저항', '입력'].index))
    self.assertEqual(kinds.count('칩'), len(bb.chips))
    self.assertEqual(kinds.count('LED'), len(bb.led_chains))
    self.assertEqual(kinds.count('저항'), len(bb.resistors))
    self.assertEqual([n for k, n, _ in rows if k == '입력'], [i['name'] for i in bb.inputs])

def test_부품표_입력은_레일_쪽_끝(self):
    from scripts.lab import hand_sim
    bb = self._guide_board()
    first = bb.inputs[0]
    rail_end = bb.addr(*bb._segments[first['seg']][1][0])
    row = next(r for r in hand_sim.guide_rows(bb) if r[0] == '입력')
    self.assertIn(rail_end, row[2])
    self.assertNotIn(bb._sym_addr(first['at']), row[2])

def test_안내_PDF_는_한_쪽에_그림_하나(self):
    from pypdf import PdfReader
    from scripts.lab import hand_sim
    tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp)
    sim, guide_png, pdf = hand_sim.main(['--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png',
                                         '--out', str(tmp), '--guide'])
    self.assertEqual(guide_png.name, '실험04_1-1_부품그리기_4x1MUX.png')
    self.assertEqual(pdf.name, '실험04_1-1_부품그리기_4x1MUX.pdf')
    pages = PdfReader(str(pdf)).pages
    self.assertEqual([len(p.images) for p in pages], [1])
    text = pages[0].extract_text()
    self.assertIn('회색 선은 이미 그려져 있어요', text)
    self.assertIn('74HC04', text)

def test_넘친_PDF_는_거절한다(self):
    from pypdf import PdfWriter
    from scripts.lab import hand_sim
    tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp)
    w = PdfWriter(); w.add_blank_page(595, 842); w.add_blank_page(595, 842)
    w.write(str(tmp / 'two.pdf'))
    with self.assertRaises(ValueError):
        hand_sim.check_guide_pdf(tmp / 'two.pdf')

def test_안내판을_못_받는_빌더는_이름과_함께_멈춘다(self):
    from scripts.lab import hand_sim
    with self.assertRaises(SystemExit) as cm:
        hand_sim.main(['--experiment', '4', '--final', '실험04_2-1_결선도_1x4DMUX.png', '--guide'])
    self.assertIn('hand_guide', str(cm.exception))
```
- [ ] **Step 2: 돌려서 실패를 본다**

Run: `.venv/bin/python -m pytest -n0 -q tests/test_breadboard_hand.py -k "부품표 or 안내_PDF or 넘친 or 못_받는"`
Expected: FAIL — `AttributeError: module 'scripts.lab.hand_sim' has no attribute 'guide_rows'` / `unrecognized arguments: --guide`

- [ ] **Step 3: 구현한다** — `scripts/lab/hand_sim.py`
  - `--guide` 플래그. 빌더 시그니처에 `hand_guide` 가 없으면 `SystemExit(f'{args.final}: 빌더 {fn.__name__} 가 hand_guide 를 안 받는다 — 지금은 실험04 MUX 만 된다')` (`inspect.signature`, 시험판을 그리기 전에 검사).
  - 안내 PNG 이름은 `args.final.replace('결선도', '부품그리기')`, 시드는 **시험판 파일 이름**의 `hand_seed` (같은 흔들림).
  - 엔진의 `[SUCCESS]` 출력은 그대로 둔다(시험판과 같다).
  - PDF: `trace_guide.make_pdf` 처럼 `tempfile.TemporaryDirectory()` 안에서 PNG 사본·HTML 을 쓰고 `html_to_pdf` → `check_guide_pdf` → `shutil.copyfile`. CSS 는 `@page { size: A4; margin: 10mm }`, 그림 `width:100%` 에 높이 상한 `max-height: 205mm`, 표 글자 9pt — 한 쪽에 들게.
  - 제목: `f'{bb.title} — 부품 그리기'`.

- [ ] **Step 4: 통과를 본다**

Run: `.venv/bin/python -m pytest -n0 -q tests/test_breadboard_hand.py`
Expected: 전부 PASS

- [ ] **Step 5: 실제로 뽑아 본다**

Run: `.venv/bin/python -m scripts.lab.hand_sim --experiment 4 --final 실험04_1-1_결선도_4x1MUX.png --guide`
Expected: `tmp/hand-sim/` 에 시험판 PNG, `실험04_1-1_부품그리기_4x1MUX.png`, `.pdf`. PDF 를 pymupdf 60dpi PNG 로 뽑아 Read 로 보고 — 선 회색, 칩·LED·저항·입력 배지 색, 표가 한 쪽 안.

- [ ] **Step 6: 전체 시험 + 커밋**

Run: `.venv/bin/python -m pytest -q`
Expected: 기존 실패 둘(실험06 `test_완성본끼리_빌더를_공유하지_않는다`, `test_review_pack_work_table`) 외 PASS

```bash
git add scripts/lab/hand_sim.py tests/test_breadboard_hand.py
git commit -m "feat(hand-sim): --guide 로 부품 그리기 안내 PNG·한 쪽 PDF 를 낸다"
```
