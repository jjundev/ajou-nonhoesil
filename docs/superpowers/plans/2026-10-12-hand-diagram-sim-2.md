# 결선도 손그림 모사 2단계 — 칩·LED·저항·글자 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `hand` 모드에서 칩·LED·저항을 채움 없는 흔들린 윤곽으로, 보드 위 영문·숫자 글자를 손글씨 글꼴(Bradley Hand Bold)로 그려 실험04 MUX 시험판을 팀원 손그림에 더 가깝게 한다.

**Architecture:** 1단계(`2026-10-12-hand-diagram-sim.md`, 커밋 65109e4..9557ecd)의 `_hand_polyline` 위에 닫힌 도형용 `_hand_loop`·`_hand_circle` 을 얹는다. 글자는 `_ScaledDraw.text` 가 **그리는 순간에만** en 글꼴을 같은 크기의 손글씨 글꼴로 갈아끼우고 원래 글자 상자 중심에 맞춘다 — 치수(`textbbox`·`getbbox`)는 원래 글꼴 그대로라 R14·배지 자리·번호 원 자리·`verify()` 가 안 바뀐다. 도형 분기는 모두 `if self.hand is not None:` 안에 둔다.

**Tech Stack:** Python 3 · Pillow · `.venv/bin/python -m pytest`

**Spec:** 이 대화의 grill-yourself 설계 "손그림 모사 2단계 — 칩·LED·저항·글자"(파일 없음). 확정값은 아래 Global Constraints 에 옮겼다. 1단계 계획 `docs/superpowers/plans/2026-10-12-hand-diagram-sim.md` 의 Global Constraints 는 그대로 유효하다.

## Global Constraints

- 손글씨 글꼴 후보(순서대로): `/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf`, `/System/Library/Fonts/Supplemental/Chalkboard.ttc`. 종류 이름 `'hand'`.
- `REQUIRED_GLYPHS['hand'] = "0123456789ABCDEHLSYΩ'·"`, `PREFERRED_GLYPHS['hand'] = ''`.
- 손글씨 글꼴을 못 찾으면 hand 렌더는 죽지 않고 글자만 인쇄체로 그린다(stderr 한 줄).
- 갈아끼우는 글꼴은 **en 글꼴(`font_path('en')`)로 만든 `_ScaledFont` 만**. kr 글꼴(머리글 등)은 그대로.
- `textbbox`·`textlength`·`_ScaledFont.getbbox` 는 갈아끼우지 않는다 — 배치는 원래 글꼴 치수.
- 칩 몸통: 채움 없음(투명, 판형이 비친다), 윤곽색·글자색 `HAND_INK = (40, 40, 40, 255)`, 윤곽 굵기 `_hand_width(2)`.
- LED 원·저항 몸통·칩 홈의 흔들림 진폭 **1px**. 배선·핀 선·다리는 1단계 그대로 2px.
- LED 원은 채움 없이 `color_rgb` 윤곽. 저항 몸통은 채움 없이 윤곽색 `(90, 70, 40, 255)`, 색띠는 원래 색.
- 난수는 `self._hand_rng` 하나를 나눠 쓴다. 같은 시드 → 같은 PNG.
- `hand=None` 이면 렌더 결과가 바이트 단위로 지금(9557ecd)과 같다.
- 코드 주석·커밋 메시지는 한국어, 식별자는 영어.

## Review Focus

- 손글씨 글꼴이 없는 PC(Windows·Linux) — hand 렌더가 예외 없이 끝나고 글자는 인쇄체. → Task 2 `test_손글씨_글꼴이_없어도_그린다`.
- 글꼴을 바꿔 그려도 배치가 같아야 한다 — 배지·칩 이름 상자·번호 원 자리가 hand 와 None 에서 같다. → Task 2 `test_글꼴을_바꿔도_배치는_같다`.
- `anchor=` 를 주는 `text()` 호출 — 중심 맞춤이 같은 kwargs 로 원래 상자를 재야 한다. → Task 1 `test_text_는_원래_상자_중심에_그린다`(anchor 포함 경우).
- kr 글꼴 글자(머리글)가 □ 로 나오지 않는다 — kr 은 갈아끼우지 않는다. → Task 1 `test_hand_real_은_en_글꼴만_바꾼다`.
- hand=None 기본 렌더 픽셀 불변 — 시험은 도장만 본다(1단계 Ruling). → Task 2 Step 7 에서 9557ecd 렌더와 sha256 직접 대조.

---

### Task 1: 닫힌 도형 흔들기와 손글씨 글꼴 갈아끼우기 (base.py)

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/base.py` (`FONT_CANDIDATES`·`REQUIRED_GLYPHS`·`PREFERRED_GLYPHS` :20-35, `_ScaledFont` :100, `_ScaledDraw` :121, `_hand_*` 뒤 :197)
- Test: `tests/test_breadboard_hand.py`

**Interfaces:**
- Consumes: `_hand_polyline(points, rng, amp=2.0, step=6.0, ramp=12.0)` (1단계)
- Produces:
  - `_hand_loop(points, rng, amp=1.0) -> list[tuple[float, float]]` — 꼭짓점 목록(닫지 않은 것)을 받아 첫 점으로 되돌아오는 흔들린 점열. 첫 점 = 끝 점 = `points[0]`.
  - `_hand_circle(center, r, rng, amp=1.0, n=24) -> list[tuple[float, float]]` — 각 `2πk/n`(k=0..n) 둘레 점을 `_hand_polyline(…, amp=amp, step=3.0, ramp=6.0)` 에 넘긴 결과. 첫 점 = 끝 점.
  - `_hand_arc(box, rng, amp=1.0, n=12) -> list` — `box=[x0,y0,x1,y1]` 타원의 t∈[0, π] 아래 반원(PIL `arc(box, 0, 180)` 과 같은 쪽), `_hand_polyline(…, amp=amp, step=3.0, ramp=6.0)`.
  - `_ScaledFont.path` 속성(생성자 인자 그대로).
  - `_ScaledDraw(image, hand_font_path=None)`; `_ScaledDraw.hand_real(font) -> ImageFont.FreeTypeFont | None` — `hand_font_path` 가 있고 `font` 가 `_ScaledFont` 이며 `font.path == font_path('en')` 이면 `ImageFont.truetype(hand_font_path, font.size * SCALE)`(크기별 캐시), 아니면 `None`.
  - `_ScaledDraw.text(xy, text, *a, **k)` — `hand_real(k['font'])` 가 있으면: 원래 글꼴로 같은 kwargs 의 `textbbox` 를 재고, 손글씨 글꼴 상자 중심을 그 중심에 맞춰 그린다(손글씨 쪽은 `anchor` 를 빼고 좌상단 기준으로 계산). 없으면 지금과 같다.

- [ ] **Step 1: 실패하는 시험을 쓴다** — `tests/test_breadboard_hand.py` 에 `HandShapes` 클래스(setUpClass 에서 `cls.mod = _load()`):

```python
def test_원은_닫혀_있고_반지름_안에서_떨린다(self):
    pts = self.mod._hand_circle((50.0, 60.0), 8, random.Random(1), amp=1.0)
    self.assertEqual(pts[0], pts[-1])
    for x, y in pts:
        d = math.hypot(x - 50.0, y - 60.0)
        self.assertTrue(8 - 2.0 <= d <= 8 + 1.5, d)

def test_사각형_윤곽은_첫_꼭짓점에서_닫힌다(self):
    box = [(10.0, 10.0), (40.0, 10.0), (40.0, 90.0), (10.0, 90.0)]
    pts = self.mod._hand_loop(box, random.Random(2), amp=1.0)
    self.assertEqual(pts[0], box[0])
    self.assertEqual(pts[-1], box[0])

def test_홈은_아래_반원이다(self):
    pts = self.mod._hand_arc([10, 0, 30, 12], random.Random(3), amp=1.0)
    for got, want in ((pts[0], (30, 6)), (pts[-1], (10, 6))):    # sin(π) 잔차 — 근사로 본다
        self.assertAlmostEqual(got[0], want[0])
        self.assertAlmostEqual(got[1], want[1])
    self.assertTrue(max(y for _, y in pts) > 10)

def test_손글씨_글꼴은_Bradley_Hand_다(self):
    self.assertTrue(self.mod.font_path('hand').endswith('Bradley Hand Bold.ttf'))

def test_hand_real_은_en_글꼴만_바꾼다(self):
    d = self.mod._ScaledDraw(Image.new('RGBA', (100, 100)), hand_font_path=self.mod.font_path('hand'))
    self.assertIsNotNone(d.hand_real(self.mod._font('en', 10)))
    self.assertIsNone(d.hand_real(self.mod._font('kr', 10)))
    self.assertIsNone(self.mod._ScaledDraw(Image.new('RGBA', (100, 100))).hand_real(self.mod._font('en', 10)))

def test_text_는_원래_상자_중심에_그린다(self):
    for kw in ({}, {'anchor': 'mm'}):
        im = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
        d = self.mod._ScaledDraw(im, hand_font_path=self.mod.font_path('hand'))
        f = self.mod._font('en', 12)
        b = d.textbbox((50, 40), '74HC20', font=f, **kw)
        d.text((50, 40), '74HC20', fill=(0, 0, 0, 255), font=f, **kw)
        ink = im.getbbox()                                   # 실픽셀
        cx = (ink[0] + ink[2]) / 2 / self.mod.SCALE
        cy = (ink[1] + ink[3]) / 2 / self.mod.SCALE
        self.assertAlmostEqual(cx, (b[0] + b[2]) / 2, delta=2)
        self.assertAlmostEqual(cy, (b[1] + b[3]) / 2, delta=2)
```
(파일 머리에 `import math` 추가.)

- [ ] **Step 2: 실패를 본다**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -k HandShapes -q`
Expected: 6 failed — `AttributeError: ... '_hand_circle'` 등, `KeyError: 'hand'`, `TypeError: ... hand_font_path`

- [ ] **Step 3: 구현** — Interfaces 의 시그니처대로 base.py 에. `FONT_CANDIDATES['hand']`·`REQUIRED_GLYPHS['hand']`·`PREFERRED_GLYPHS['hand']` 는 Global Constraints 값. `_hand_loop` 은 `_hand_polyline(list(points) + [points[0]], rng, amp=amp)`. `_ScaledDraw.__init__` 은 `self._hand_path = hand_font_path`, `self._en_path = font_path('en') if hand_font_path else None`, `self._hand_cache = {}`.

- [ ] **Step 4: 통과를 본다**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -q`
Expected: 22 passed (1단계 16 + 6)

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/engine/base.py tests/test_breadboard_hand.py
git commit -m "feat(breadboard): 손그림 모사용 닫힌 도형 흔들기와 손글씨 글꼴 갈아끼우기를 더한다"
```

---

### Task 2: 칩·LED·저항을 손그림으로, 글자를 손글씨로 (renderer.py)

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/renderer.py` (`__init__` :12-42, `draw_resistor` :711, `draw_led` :735, `_vtext` :827, `draw_chip` :852)
- Test: `tests/test_breadboard_hand.py`

**Interfaces:**
- Consumes: Task 1 의 `_hand_loop`·`_hand_circle`·`_hand_arc`·`_ScaledDraw(image, hand_font_path)`·`_ScaledDraw.hand_real`; 1단계 `_hand_polyline`·`_hand_width`·`self._hand_rng`.
- Produces: 모듈 상수 `HAND_INK = (40, 40, 40, 255)`(renderer.py 클래스 위). 다른 공개 인터페이스 변화 없음.

- [ ] **Step 1: 실패하는 시험을 쓴다** — `HandRender` 에 추가:

```python
def _count(self, bb, rgba, box=None):
    im = bb.overlay if box is None else bb.overlay.crop(tuple(int(v * self.mod.SCALE) for v in box))
    return sum(1 for p in im.getdata() if p == rgba)

def _chip_box(self, bb, i=0):
    ch = bb.chips[i]
    c = bb.cols[ch['block']]
    return (c['chip_x1'], bb.r_y(ch['pin1_row']) - 8, c['chip_x2'], bb.r_y(ch['pin1_row'] + 6) + 8)

def test_칩_몸통을_칠하지_않는다(self):
    a, _, _ = self._render(None)
    b, _, _ = self._render(42)
    fill = (30, 33, 36, 255)
    self.assertGreater(self._count(a, fill, self._chip_box(a)), 1000)
    self.assertEqual(self._count(b, fill, self._chip_box(b)), 0)

def test_LED_와_저항_몸통을_칠하지_않는다(self):
    a, _, _ = self._render(None)
    b, _, _ = self._render(42)
    for rgba in ((220, 20, 20, 240), (225, 195, 145, 255)):
        self.assertGreater(self._count(a, rgba), 0, rgba)
        self.assertEqual(self._count(b, rgba), 0, rgba)

def test_칩_윤곽을_손그림_잉크로_긋는다(self):
    b, _, _ = self._render(42)
    self.assertGreater(self._count(b, self.mod.HAND_INK, self._chip_box(b)), 100)

def test_글꼴을_바꿔도_배치는_같다(self):
    a, _, _ = self._render(None)
    b, _, _ = self._render(42)
    self.assertEqual(a.tag_boxes, b.tag_boxes)
    self.assertEqual(a.chip_label_boxes, b.chip_label_boxes)
    self.assertEqual(a.margin_tag_boxes, b.margin_tag_boxes)
    self.assertEqual(a.settled_markers, b.settled_markers)

def test_손글씨_글꼴이_없어도_그린다(self):
    saved = self.mod.FONT_CANDIDATES['hand']
    self.mod.FONT_CANDIDATES['hand'] = ()
    self.addCleanup(self.mod.FONT_CANDIDATES.__setitem__, 'hand', saved)
    b, out, _ = self._render(42)
    self.assertTrue(out.exists())
    self.assertIsNone(b.draw.hand_real(b.font_chip))
```

- [ ] **Step 2: 실패를 본다**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -k HandRender -q`
Expected: 칩·LED·저항 셋과 `test_칩_윤곽을_손그림_잉크로_긋는다`(`AttributeError: HAND_INK`) 실패, `test_손글씨_글꼴이_없어도_그린다` 는 `hand_real` 이 None 이라 통과할 수 있다 — 통과해도 Step 4 까지 유지(글꼴 연결 뒤 회귀 방지용). `test_글꼴을_바꿔도_배치는_같다` 는 지금 통과(배치 불변의 기준선).

- [ ] **Step 3: 구현**
  - `__init__`: hand 일 때 `font_path('hand')` 를 부르고 `FileNotFoundError` 면 `None` + stderr `[hand] 손글씨 글꼴이 없어 글자는 인쇄체로 그린다` 한 줄. `self.draw = _ScaledDraw(self.overlay, hand_font_path=<그 값 또는 None>)`.
  - `_vtext`: `real = self.draw.hand_real(font) or (font.real if isinstance(font, _ScaledFont) else font)` — 나머지 그대로.
  - `draw_chip`(hand 분기): 몸통 `self.draw.line(_hand_loop([(x1,y_top),(x2,y_top),(x2,y_bot),(x1,y_bot)], rng), fill=HAND_INK, width=_hand_width(2, rng), joint='curve')`; 홈 `_hand_arc` 를 `HAND_INK` 로; 핀 선 각각 `_hand_polyline` + `_hand_width(3, rng)`(색 그대로); `text_fill = num_fill = HAND_INK`. `lead`·`chips`·`chip_label_boxes`·`label_box` 계산은 그대로.
  - `draw_led`(hand 분기): 다리 두 선 `_hand_polyline`, 원 `_hand_circle((x, ymid), 8, rng)` 을 `(*color_rgb, 255)` 윤곽 `_hand_width(2, rng)`. 채움 없음.
  - `draw_resistor`(hand 분기): 다리 두 선 `_hand_polyline`, 몸통 `_hand_loop` 윤곽 `(90, 70, 40, 255)` `_hand_width(1, rng)`, 색띠 4줄 각각 `_hand_polyline(…, amp=1.0, ramp=2.0)` 원래 색·굵기 2.
  - hand 분기가 아니면 지금 코드 한 줄도 바꾸지 않는다.

- [ ] **Step 4: 통과를 본다**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -q`
Expected: 27 passed

- [ ] **Step 5: 시험판을 다시 뽑아 눈으로 본다**

Run: `.venv/bin/python -m scripts.lab.hand_sim --experiment 4 --final 실험04_1-1_결선도_4x1MUX.png`
Expected: `[SUCCESS] Exported (손그림 모사)` — `tmp/hand-sim/실험04_1-1_손그림모사_4x1MUX.png` 에 칩 4개가 빈 흔들린 네모, 칩 이름·핀 번호가 손글씨, LED 가 빈 빨간 원.

- [ ] **Step 6: 전체 시험**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -5`
Expected: 실패는 실험06 `test_완성본끼리_빌더를_공유하지_않는다` 와 `test_review_pack_work_table::test_published_payloads_obey_the_rule_and_match_the_source` 둘뿐(main 에서도 실패하는 기존 결함 — 1단계 기록).

- [ ] **Step 7: hand=None 픽셀 불변을 9557ecd 와 대조**

base 커밋 worktree(`git worktree add <scratchpad>/base 9557ecd`, `.venv` 링크)에서와 이 트리에서 각각 `build_e4_mux(<out>)` 로 MUX 완성본을 렌더해 PNG 픽셀(`Image.open(p).tobytes()`) sha256 을 비교한다.
Expected: 같다. 다 보면 base worktree 를 `git worktree remove` 로 지운다.

- [ ] **Step 8: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/engine/renderer.py tests/test_breadboard_hand.py
git commit -m "feat(breadboard): hand 모드에서 칩·LED·저항을 빈 윤곽으로, 글자를 손글씨로 그린다"
```
