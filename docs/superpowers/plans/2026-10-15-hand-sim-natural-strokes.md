# 손그림모사 자연스러운 벡터 펜 선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** make-hand-sim 이 긋는 배선을 계단현상 없는 얇은 벡터 펜 선(한 굵기, 은은한 휨)으로 바꿔 팀원이 덧칠 없이 부품만 그리게 한다.

**Architecture:** 엔진은 손그림 모드에서 배선을 긋지 않고 **획 목록**(`bb.hand_strokes`)으로 기록한다. 같은 획을 두 곳에서 그린다 — 손그림모사 PDF 에는 빈 판형 PDF 쪽을 그대로 복사하고 그 위에 pymupdf 벡터 선으로, PNG·부품그리기 안내판에는 MuPDF 가 안티앨리어싱한 RGBA 레이어(`bb.hand_layer`)를 overlay 아래에 합성한다. 노이즈는 구간마다 활 하나 + 미세 떨림(수직 방향만)이다.

**Tech Stack:** Python 3.14, Pillow, PyMuPDF(`pymupdf` 1.28), unittest/pytest.

**Spec:** `docs/superpowers/specs/2026-10-15-hand-sim-natural-strokes-design.md`

**실행 상태 (2026-10-15):** Task 1·2는 기존 커밋으로 완료, Task 3·4와 사용자 추가 요청인 PDF 쪽 넘침
수정까지 완료했다. 손그림 관련 54개 테스트와 PDF 시각 검토를 통과했다. 전체 시험은 3233 passed,
11 failed이며 실패 11개는 수정 전 스냅샷에서도 동일 재현했다. 상세 근거는
`docs/verify/hand-sim-natural-strokes.md`에 기록한다. 로컬 브랜치에 커밋하고 푸시하지 않는다.

## Global Constraints

- 선 굵기 `HAND_WIDTH = 2.0` 논리 px (손그림모사 PDF 에서 ≈ 0.93pt). 쪽 전체 상수 — 가닥마다 바꾸지 않는다.
- 휨: A = ±U(0.4, 1.0) · min(0.012·L, 2.5), 모양 `sin(π·t^k)`, k = U(0.75, 1.35), L < 15 이면 휨 0.
- 떨림: 8 논리 px 간격 무작위 값(±1) 코사인 보간 × 0.25, 양 끝 6 px 동안 0 에서 올린다. 표본 간격 3 논리 px.
- 오프셋은 구간의 **수직 방향만**. 첫 점·각 구간 끝점(모서리·마지막 점)은 입력 좌표 그대로.
- 끝점 도트 반지름 `HAND_DOT_R = 2.4`, 축마다 ±10%, 중심 고정.
- `hand` 없는 렌더는 픽셀 하나 바뀌지 않는다(`build_all` PNG `tobytes()` sha256 불변).
- 엔진 조각(`engine/*.py`)은 `render_breadboard.py` 이름공간에서 exec 된다 — 새 import 는 함수 안에서 한다(`import pymupdf`). 엔진 조각끼리는 import 없이 이름을 그대로 쓴다.
- 이 PC 에는 `.venv` 가 없다 — 명령은 `python -m pytest ...` 로 쓴다(스킬 문서의 `.venv/bin/python` 과 같은 뜻).
- 커밋 메시지는 저장소 관례(`feat(hand-sim): …` 한국어) + 끝줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- 시험에서 `hand_sim.main` 을 부를 땐 반드시 `--out-dir <임시>` — 커밋된 PDF 를 덮지 않는다.

## Review Focus

1. 경로에 같은 점이 연달아 있거나(길이 0 구간) 모서리 사이 구간이 아주 짧을 때 — 0 나누기 없이 모서리·끝점이 그대로여야 한다 → Task 1 `test_길이_0_구간도_된다`, `test_모서리는_그대로다`.
2. 판형 PDF 가 없는 v1(실험04 MUX) — 손그림모사 쪽이 템플릿 그림 + 벡터 획으로 나와야 한다 → Task 3 `test_실험04_v1_도_벡터_획`.
3. 손그림 모드에서 배선 밖 그림이 overlay 에 남은 경우 — 조용히 빠지지 않고 이유를 대고 멈춰야 한다 → Task 3 `test_overlay_에_남은_그림은_거절`.
4. 새 손그림모사 위에 팀원이 그려 온 PDF — `review-hand-diagram` 격자 보정이 통과해야 한다 → Task 3 `test_손그림모사는_격자_보정이_된다`.
5. MuPDF 알파 표본은 premultiplied — 잘못 읽으면 선 가장자리가 검게 번진다 → Task 2 `test_가장자리_색은_획_색`.

---

## File Structure

| 파일 | 책임 | 변화 |
|---|---|---|
| `.claude/skills/breadboard-diagram/scripts/engine/base.py` | 손그림 획 모델(`_hand_polyline`·`_hand_dot`·상수)과 획 그리기(`draw_strokes`·`strokes_layer`) | 수정 (174–210행 교체 + 함수 2개 추가) |
| `.claude/skills/breadboard-diagram/scripts/engine/renderer.py` | 손그림 모드에서 획 기록(`_hand_stroke`), export 합성 | 수정 (`__init__`, 640–645, 1073–1077, 1374–1376) |
| `scripts/lab/hand_sim.py` | 손그림모사 PDF = 빈 판형 쪽 + 벡터 획, 가드 | 수정 (`render_final`, `board_page`, `make_handout_pdf`, `make_pdfs`) |
| `tests/test_breadboard_hand.py` | 위 셋의 시험 | 수정 |
| `.claude/skills/make-hand-sim/SKILL.md` | 스킬 규칙 문서 | 수정 |
| `보고서/실험06/결선도/팀원전달용/실험06_손그림모사.pdf`, `실험06_부품그리기.pdf` | 재생성 산출물 | 재생성 |

---

### Task 1: 획 모델 — 활 + 떨림, 한 굵기

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/base.py:174-210`
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/renderer.py:640-645` (새 이름으로만 옮겨 이 태스크 끝에 전부 초록)
- Test: `tests/test_breadboard_hand.py` (`HandPolyline` 클래스 26–72행 교체)

**Interfaces:**
- Consumes: 없음
- Produces (엔진 이름공간, 테스트는 `mod.` 로 접근):
  - `HAND_WIDTH: float = 2.0`, `HAND_DOT_R: float = 2.4`, `HAND_BOW_MAX = 2.5`, `HAND_BOW_PER_LEN = 0.012`, `HAND_MIN_BOW_LEN = 15.0`, `HAND_TREMOR = 0.25`, `HAND_TREMOR_STEP = 8.0`, `HAND_SAMPLE = 3.0`, `HAND_RAMP = 6.0`
  - `_hand_polyline(points: list[tuple[float, float]], rng: random.Random) -> list[tuple[float, float]]`
  - `_hand_dot(p: tuple[float, float], rng: random.Random) -> list[float]` — `[x0, y0, x1, y1]`
  - 삭제: `_hand_noise`, `_hand_width`

- [x] **Step 0: 픽셀 불변 기준값 저장 (코드 고치기 전에 한 번)**

hand 없는 렌더가 이 계획 전체에서 안 바뀌는지 Task 2 끝에서 대조한다. 지금 기준을 저장한다. `SCRATCH` 는 자기 스크래치 폴더(저장소 밖)다.

```bash
SCRATCH="<your scratchpad dir>"
python - "$SCRATCH/pixhash_before.json" <<'EOF'
import hashlib, json, sys, tempfile
sys.path.insert(0, '.')
from PIL import Image
from scripts.lab.hand_grid import load_renderer
rb = load_renderer()
out = {}
for n in range(1, 7):
    with tempfile.TemporaryDirectory() as d:
        try:
            made = rb.build_all(rb.load_board(n), d)
        except Exception as e:          # 결선 파일이 없는 실험은 건너뛴다 — 이유를 남긴다
            out[f'e{n}'] = f'skip: {e!r}'
            continue
        for name in made:
            out[f'e{n}/{name}'] = hashlib.sha256(Image.open(f'{d}/{name}').tobytes()).hexdigest()
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'entries')
EOF
```
Expected: `N entries` (N ≥ 10). `skip:` 줄이 있으면 그 실험은 대조 대상이 아니다 — 그대로 둔다.

- [x] **Step 1: 실패하는 단위시험으로 `HandPolyline` 클래스를 교체한다**

`tests/test_breadboard_hand.py` 의 `class HandPolyline(unittest.TestCase):` 부터 `test_도트는_반지름_1px_안에서_찌그러진다` 끝(72행 `self.assertGreater(len({tuple(b) for b in boxes}), 1)`)까지를 아래로 바꾼다. 파일 위쪽 import 에 `import math` 를 더한다.

```python
def _seg_dist(p, a, b):
    """점 p 에서 선분 ab 까지 거리."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class HandPolyline(unittest.TestCase):
    """손그림 획 모델 — 구간마다 활 하나 + 미세 떨림, 수직 방향만(2026-10-15)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    PATH = [(100.0, 50.0), (100.0, 300.0), (400.0, 300.0)]

    def _out(self, seed=7, pts=None):
        return self.mod._hand_polyline(pts or self.PATH, random.Random(seed))

    def test_끝점은_그대로다(self):
        out = self._out()
        self.assertEqual(out[0], self.PATH[0])
        self.assertEqual(out[-1], self.PATH[-1])

    def test_모서리는_그대로다(self):
        # 모서리점이 결과에 정확히 들어 있다 — L 자 경로의 꺾임이 홀·경로점에 남는다
        for s in range(20):
            self.assertIn(self.PATH[1], self._out(s))

    def test_오프셋은_활_더하기_떨림을_안_넘는다(self):
        bound = self.mod.HAND_BOW_MAX + self.mod.HAND_TREMOR + 1e-9
        for s in range(50):
            for p in self._out(s):
                d = min(_seg_dist(p, self.PATH[0], self.PATH[1]), _seg_dist(p, self.PATH[1], self.PATH[2]))
                self.assertLessEqual(d, bound)

    def test_긴_직선은_가운데가_한쪽으로만_휜다(self):
        # 출렁이지 않는다 — 옛 모델(사인 셋)은 2~8칸마다 부호가 바뀌었다
        a, b = (0.0, 100.0), (400.0, 100.0)
        for s in range(50):
            mid = [y - 100.0 for x, y in self._out(s, [a, b]) if 80 <= x <= 320]
            self.assertTrue(all(v > 0 for v in mid) or all(v < 0 for v in mid), s)
            self.assertGreater(max(abs(v) for v in mid), 0.7, s)   # 활 ≥ 1.0 − 떨림 0.25

    def test_수직_방향으로만_움직인다(self):
        # 가로선 위 점들의 x 는 단조 증가 — 축별로 따로 흔들던 옛 모델과 다르다
        xs = [x for x, _ in self._out(3, [(0.0, 10.0), (200.0, 10.0)])]
        self.assertEqual(xs, sorted(xs))

    def test_같은_시드는_같은_점(self):
        self.assertEqual(self._out(3), self._out(3))
        self.assertNotEqual(self._out(3), self._out(4))

    def test_짧은_선은_휘지_않는다(self):
        out = self.mod._hand_polyline([(10.0, 10.0), (20.0, 10.0)], random.Random(1))
        self.assertEqual((out[0], out[-1]), ((10.0, 10.0), (20.0, 10.0)))
        self.assertTrue(all(abs(y - 10.0) <= self.mod.HAND_TREMOR + 1e-9 for _, y in out))

    def test_길이_0_구간도_된다(self):
        # 같은 점이 연달아 와도 0 나누기 없이 끝점이 그대로다
        pts = [(10.0, 10.0), (10.0, 10.0), (60.0, 10.0)]
        out = self.mod._hand_polyline(pts, random.Random(2))
        self.assertEqual((out[0], out[-1]), (pts[0], pts[-1]))

    def test_굵기는_상수다(self):
        self.assertEqual(self.mod.HAND_WIDTH, 2.0)
        self.assertFalse(hasattr(self.mod, '_hand_width'))

    def test_도트는_반지름_10퍼센트_안에서_찌그러진다(self):
        r = self.mod.HAND_DOT_R
        boxes = [self.mod._hand_dot((50.0, 60.0), random.Random(s)) for s in range(50)]
        for x0, y0, x1, y1 in boxes:
            self.assertAlmostEqual((x0 + x1) / 2, 50.0)
            self.assertAlmostEqual((y0 + y1) / 2, 60.0)
            self.assertTrue(0.9 * r - 1e-9 <= (x1 - x0) / 2 <= 1.1 * r + 1e-9)
            self.assertTrue(0.9 * r - 1e-9 <= (y1 - y0) / 2 <= 1.1 * r + 1e-9)
        self.assertGreater(len({tuple(b) for b in boxes}), 1)
```

- [x] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_breadboard_hand.py::HandPolyline -q`
Expected: FAIL — `AttributeError: ... 'HAND_BOW_MAX'` / `'HAND_DOT_R'`, `test_긴_직선…`·`test_수직_방향…` 실패, `_hand_dot()` 인자 수 오류.

- [x] **Step 3: `base.py` 174–210행(`_hand_noise` ~ `_hand_dot`)을 교체한다**

```python
# 손그림 모사 획(2026-10-15). 옛 모델 — 축별 사인 셋(파장 40~160, 행 간격 19)·가닥마다 굵기 ×0.7~1.3 —
# 을 팀원이 "계단현상·노이즈" 로 보고 전부 덧칠했다. 사람이 긋는 점퍼선은 전체가 한 번 살짝 휘고
# 손떨림만 있다 — 그래서 구간마다 활 하나 + 미세 떨림, 수직 방향만, 쪽 전체 한 굵기다.
HAND_WIDTH = 2.0          # 논리 px — 손그림모사 PDF 에서 ≈ 0.93pt (사용자 결정 #10)
HAND_DOT_R = 2.4          # 끝점 도트 반지름
HAND_BOW_MAX = 2.5        # 활 진폭 상한 ≈ 홀 간격의 13% (사용자 결정 #11)
HAND_BOW_PER_LEN = 0.012  # 짧은 구간은 길이에 비례해 덜 휜다
HAND_MIN_BOW_LEN = 15.0   # 이보다 짧은 구간은 휘지 않는다
HAND_TREMOR = 0.25        # 떨림 진폭
HAND_TREMOR_STEP = 8.0    # 떨림 무작위 값 간격
HAND_SAMPLE = 3.0         # 표본 간격
HAND_RAMP = 6.0           # 양 끝에서 떨림을 0 에서 올리는 길이


def _hand_tremor(rng, length):
    """길이 s -> [-1, 1] 미세 떨림 — `HAND_TREMOR_STEP` 마다 무작위 값, 사이는 코사인 보간."""
    knots = [rng.uniform(-1, 1) for _ in range(int(length // HAND_TREMOR_STEP) + 2)]

    def f(s):
        i = min(int(s // HAND_TREMOR_STEP), len(knots) - 2)
        t = s / HAND_TREMOR_STEP - i
        w = (1 - math.cos(math.pi * t)) / 2
        return knots[i] * (1 - w) + knots[i + 1] * w
    return f


def _hand_polyline(points, rng):
    """손그림 모사 배선 — 구간마다 수직 방향으로 활 하나 + 미세 떨림을 준 촘촘한 점열.
    첫 점과 각 구간 끝점(모서리·마지막 점)은 입력 그대로다(홀·경로점 위)."""
    pts = [tuple(map(float, p)) for p in points]
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.dist((x0, y0), (x1, y1))
        if L == 0:
            continue
        nx, ny = -(y1 - y0) / L, (x1 - x0) / L
        bow, k = 0.0, 1.0
        if L >= HAND_MIN_BOW_LEN:
            bow = (rng.choice((-1, 1)) * rng.uniform(0.4, 1.0)
                   * min(HAND_BOW_PER_LEN * L, HAND_BOW_MAX))
            k = rng.uniform(0.75, 1.35)
        trem = _hand_tremor(rng, L)
        n = max(1, math.ceil(L / HAND_SAMPLE))
        for i in range(1, n):
            t = i / n
            s = L * t
            ramp = min(1.0, s / HAND_RAMP, (L - s) / HAND_RAMP)
            off = bow * math.sin(math.pi * t ** k) + HAND_TREMOR * ramp * trem(s)
            out.append((x0 + (x1 - x0) * t + off * nx, y0 + (y1 - y0) * t + off * ny))
        out.append((x1, y1))
    return out


def _hand_dot(p, rng):
    """끝점 도트 상자 — 반지름 `HAND_DOT_R` 를 축마다 ±10%, 중심은 그대로."""
    rx = HAND_DOT_R * rng.uniform(0.9, 1.1)
    ry = HAND_DOT_R * rng.uniform(0.9, 1.1)
    return [p[0] - rx, p[1] - ry, p[0] + rx, p[1] + ry]
```

- [x] **Step 4: `renderer.py:640-645` 를 새 이름으로 옮긴다 (Task 2 가 이 분기를 다시 바꾼다)**

```python
        if self.hand is not None:
            rng = self._hand_rng
            draw.line(_hand_polyline(points, rng), fill=color, width=HAND_WIDTH, joint='curve')
            for p in (points[0], points[-1]):
                draw.ellipse(_hand_dot(p, rng), fill=color)
```

- [x] **Step 5: 통과를 확인한다**

Run: `python -m pytest tests/test_breadboard_hand.py -q`
Expected: 모두 PASS (렌더 시험도 — 아직 overlay 에 그린다).

- [x] **Step 6: Commit**

```bash
git add .claude/skills/breadboard-diagram/scripts/engine/base.py .claude/skills/breadboard-diagram/scripts/engine/renderer.py tests/test_breadboard_hand.py
git commit -m "feat(hand-sim): 손그림 획을 구간마다 활 하나 + 미세 떨림, 한 굵기로 바꾼다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 엔진 — 획 기록 + MuPDF 안티앨리어싱 레이어

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/base.py` (Task 1 의 `_hand_dot` 뒤에 함수 2개 추가)
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/renderer.py` (`__init__` 의 `self._hand_rng = …` 줄 뒤, 640–645 분기, 1073–1077, 1374–1376)
- Test: `tests/test_breadboard_hand.py` (`HandRender`, `HandRenderE5` 수정·추가)

**Interfaces:**
- Consumes: Task 1 의 `_hand_polyline`, `_hand_dot`, `HAND_WIDTH`
- Produces:
  - 획 dict: `{'points': list[tuple[float, float]], 'color': tuple[int, int, int, int], 'width': float, 'dots': list[list[float]]}` (논리 좌표)
  - `bb.hand_strokes: list[dict]` (hand 없으면 `[]`)
  - `bb.hand_layer: PIL.Image (RGBA, bb.im.size) | None` — export 뒤 hand 면 채워진다
  - `draw_strokes(page: pymupdf.Page, strokes: list[dict], to_pt: Callable[[float, float], tuple[float, float]], k: float) -> None`
  - `strokes_layer(strokes: list[dict], size: tuple[int, int], scale: int) -> PIL.Image` (RGBA, `(w*scale, h*scale)`)

- [x] **Step 1: 렌더 시험을 바꾸고 새 시험을 더한다 (실패하게)**

`HandRender` 안 `_count` 아래에 도우미를 더한다:

```python
    def _ink(self, bb, rgba):
        """획 레이어에서 그 색으로 꽉 찬 픽셀 수 — 가장자리(반투명)는 안 센다."""
        return sum(1 for p in bb.hand_layer.get_flattened_data() if p == rgba)
```

`test_입력은_선만_두고_이름_배지는_비운다` 의 첫 단언을 바꾼다:

```python
        self.assertGreater(self._ink(bb, self.mod.INPUT), 0)    # 보라 점퍼선은 남는다(획 레이어)
```

`test_안내판은_선이_회색이고_부품은_색이다` 를 통째로 바꾼다:

```python
    def test_안내판은_선이_회색이고_부품은_색이다(self):
        bb, _, _ = self._render(42, guide=True)
        for col in self.mod.WIRE.values():
            self.assertEqual(self._count(bb, col), 0, col)
            self.assertEqual(self._ink(bb, col), 0, col)
        self.assertGreater(self._ink(bb, self.mod.KEEP), 0)
        for rgba in [(30, 33, 36, 255), (220, 20, 20, 240), (225, 195, 145, 255), self.mod.INPUT]:
            self.assertGreater(self._count(bb, rgba), 0, rgba)
```

`test_안내판_회색선은_시험판_선과_같은_자리` 를 통째로 바꾼다:

```python
    def test_안내판_회색선은_시험판_선과_같은_자리(self):
        # 팀원이 시험판과 안내판을 겹쳐 본다 — 같은 시드면 획 좌표가 같아야 한다
        blank, _, _ = self._render(42)
        guide, _, _ = self._render(42, guide=True)
        self.assertTrue(blank.hand_strokes)
        self.assertEqual([(s['points'], s['dots']) for s in blank.hand_strokes],
                         [(s['points'], s['dots']) for s in guide.hand_strokes])
        self.assertEqual({s['color'] for s in guide.hand_strokes}, {self.mod.KEEP})
```

`HandRender` 끝(`test_기준선_이나_층과_못_섞는다` 뒤)에 더한다:

```python
    def test_손그림_overlay_는_비어_있다(self):
        # 배선은 획 레이어로 갔다 — 부품·배지·번호 원은 비웠으니 overlay 에 아무것도 없어야 한다
        bb, _, _ = self._render(42)
        self.assertIsNone(bb.overlay.getbbox())

    def test_모든_배선이_획이다(self):
        bb, _, _ = self._render(42)
        self.assertEqual(len(bb.hand_strokes), len(bb._segments))
        self.assertEqual({s['width'] for s in bb.hand_strokes}, {self.mod.HAND_WIDTH})

    def test_획_끝점은_구간_끝점(self):
        bb, _, _ = self._render(42)
        for s, (_, pts, _) in zip(bb.hand_strokes, bb._segments):
            self.assertEqual(s['points'][0], tuple(map(float, pts[0])))
            self.assertEqual(s['points'][-1], tuple(map(float, pts[-1])))

    def test_hand_없으면_획도_레이어도_없다(self):
        bb, _, _ = self._render(None)
        self.assertEqual(bb.hand_strokes, [])
        self.assertIsNone(bb.hand_layer)

    def test_획_레이어는_안티앨리어싱(self):
        bb, _, _ = self._render(42)
        self.assertEqual(bb.hand_layer.size, bb.im.size)
        alphas = {p[3] for p in bb.hand_layer.get_flattened_data()}
        self.assertGreater(len(alphas), 20)       # 0·255 말고도 중간 알파가 많다

    def test_가장자리_색은_획_색(self):
        # MuPDF 알파 표본은 premultiplied — 그대로 읽으면 가장자리가 검게 번진다
        bb, _, _ = self._render(42)
        cols = {s['color'][:3] for s in bb.hand_strokes}
        edge = [p for p in bb.hand_layer.get_flattened_data() if 64 <= p[3] < 255]
        self.assertTrue(edge)
        near = sum(1 for p in edge if min(max(abs(p[i] - c[i]) for i in range(3)) for c in cols) <= 30)
        self.assertGreater(near / len(edge), 0.9)
```

`HandRenderE5` 에서 `test_실험05_부품과_입력_이름은_비운다` 의 마지막 줄과 `test_실험05_안내판_선은_회색` 을 바꾼다:

```python
            self.assertGreater(sum(1 for p in bb.hand_layer.get_flattened_data()
                                   if p == self.mod.INPUT), 0, name)
```

```python
    def test_실험05_안내판_선은_회색(self):
        for name in self.BUILDERS:
            bb = self._render(name, 42, guide=True)
            for col in self.mod.WIRE.values():
                self.assertEqual(self._count(bb, col), 0, (name, col))
            self.assertEqual({s['color'] for s in bb.hand_strokes}, {self.mod.KEEP}, name)
            self.assertGreater(self._count(bb, (30, 33, 36, 255)), 0, name)   # 칩은 색

    def test_실험05_손그림_overlay_는_비어_있다(self):
        for name in self.BUILDERS:
            self.assertIsNone(self._render(name, 42).overlay.getbbox(), name)
```

- [x] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_breadboard_hand.py -q`
Expected: FAIL — `AttributeError: ... 'hand_layer'` / `'hand_strokes'`, overlay 비움 실패.

- [x] **Step 3: `base.py` 에 획 그리기 두 함수를 더한다 (`_hand_dot` 바로 뒤)**

```python
def draw_strokes(page, strokes, to_pt, k):
    """손그림 획을 pymupdf 쪽에 벡터로 긋는다 — 둥근 끝·둥근 이음, 끝점은 채운 타원.
    `to_pt(x, y)` 는 논리 좌표 -> 쪽 pt, `k` 는 굵기 배율(pt / 논리 px)."""
    import pymupdf
    for s in strokes:
        rgb = tuple(c / 255 for c in s['color'][:3])
        shape = page.new_shape()
        shape.draw_polyline([pymupdf.Point(*to_pt(x, y)) for x, y in s['points']])
        shape.finish(color=rgb, width=s['width'] * k, lineCap=1, lineJoin=1, closePath=False)
        for x0, y0, x1, y1 in s['dots']:
            shape.draw_oval(pymupdf.Rect(*to_pt(x0, y0), *to_pt(x1, y1)))
            shape.finish(color=None, fill=rgb, width=0)
        shape.commit()


def strokes_layer(strokes, size, scale):
    """획을 MuPDF 로 안티앨리어싱한 RGBA 레이어 — 논리 크기 빈 쪽에 그려 `scale` 배로 래스터화한다.
    PNG·안내판이 손그림모사 PDF 와 같은 코드로 같은 선을 얻는다."""
    import pymupdf
    w, h = size
    doc = pymupdf.open()
    page = doc.new_page(width=w, height=h)
    draw_strokes(page, strokes, lambda x, y: (x, y), 1.0)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=True)
    if (pix.width, pix.height) != (w * scale, h * scale):
        raise ValueError(f'획 레이어 크기 {pix.width}x{pix.height} 가 캔버스 {w * scale}x{h * scale} 와 다르다')
    # MuPDF 알파 표본은 premultiplied — 'RGBa' 로 읽어 풀어야 가장자리가 검게 번지지 않는다
    return Image.frombytes('RGBa', (pix.width, pix.height), pix.samples).convert('RGBA')
```

- [x] **Step 4: `renderer.py` — 획 기록**

`__init__` 의 `self._hand_rng = random.Random(hand) if hand is not None else None` 줄 바로 뒤에:

```python
        # 손그림 획 — 긋지 않고 기록한다. export 가 `strokes_layer` 로, hand_sim 이 PDF 벡터로 긋는다
        self.hand_strokes = []
        self.hand_layer = None
```

`step_wire` 안 클래스에 메서드를 더한다(`step_wire` 정의 바로 앞):

```python
    def _hand_stroke(self, points, color):
        """손그림 모드 배선 한 가닥 — 획으로 기록만 한다(2026-10-15). 시드 rng 를 쓰는 순서가 같아
        손그림모사와 안내판의 획 좌표가 같다."""
        rng = self._hand_rng
        self.hand_strokes.append({
            'points': _hand_polyline(points, rng),
            'color': tuple(color),
            'width': HAND_WIDTH,
            'dots': [_hand_dot(p, rng) for p in (points[0], points[-1])],
        })
```

`step_wire` 의 Task 1 분기(5줄)를 바꾼다:

```python
        if self.hand is not None:
            self._hand_stroke(points, color)
```

`connect_unused_inputs` 의 두 곳을 바꾼다. 현재:

```python
            draw.line([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))], fill=col, width=2)
```
→
```python
            if self.hand is not None:
                self._hand_stroke([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))], col)
            else:
                draw.line([(x_pin, self.r_y(row)), (x_rail, self.r_y(r_rail))], fill=col, width=2)
```

현재:

```python
            draw.ellipse([x_pin-3, self.r_y(row)-3, x_pin+3, self.r_y(row)+3], fill=col)
            draw.ellipse([x_rail-3, self.r_y(r_rail)-3, x_rail+3, self.r_y(r_rail)+3], fill=col)
```
→
```python
            if self.hand is None:
                draw.ellipse([x_pin-3, self.r_y(row)-3, x_pin+3, self.r_y(row)+3], fill=col)
                draw.ellipse([x_rail-3, self.r_y(r_rail)-3, x_rail+3, self.r_y(r_rail)+3], fill=col)
```

- [x] **Step 5: `renderer.py` export 합성 (1374–1376)**

현재:

```python
        # 유령선은 템플릿과 overlay 사이 — 회색 선·칩·새 선이 유령선을 덮는다
        final_im = Image.alpha_composite(Image.alpha_composite(self.im, self.ghost_layer),
                                         self.overlay)
```
→
```python
        # 유령선은 템플릿과 overlay 사이 — 회색 선·칩·새 선이 유령선을 덮는다
        base = Image.alpha_composite(self.im, self.ghost_layer)
        if self.hand is not None:
            # 손그림 획은 overlay 아래 — 안내판의 색 부품이 회색 선 위에 온다(2026-10-15)
            self.hand_layer = strokes_layer(self.hand_strokes, self.spec.size, SCALE)
            base = Image.alpha_composite(base, self.hand_layer)
        final_im = Image.alpha_composite(base, self.overlay)
```

- [x] **Step 6: 통과를 확인한다**

Run: `python -m pytest tests/test_breadboard_hand.py -q`
Expected: 모두 PASS. `test_같은_시드는_같은_PNG` 도 통과해야 한다(MuPDF 래스터는 결정적).
`test_손그림_overlay_는_비어_있다` 만 실패하면 손그림 모드에서 배선 밖 무언가가 아직 overlay 에 그려진다는
뜻이다 — `bb.overlay.getbbox()` 자리를 잘라 보고 무엇인지(출력 이름 배지 등) 적어 **멈추고 보고한다**.
시험을 느슨하게 고치지 않는다 — Task 3 의 가드가 같은 이유로 실험06 생성을 막는다.

- [x] **Step 7: 픽셀 불변을 대조한다**

```bash
SCRATCH="<your scratchpad dir>"
python - "$SCRATCH/pixhash_before.json" <<'EOF'
import hashlib, json, sys, tempfile
sys.path.insert(0, '.')
from PIL import Image
from scripts.lab.hand_grid import load_renderer
rb = load_renderer()
before = json.load(open(sys.argv[1], encoding='utf-8'))
bad = []
for n in range(1, 7):
    if str(before.get(f'e{n}', '')).startswith('skip'):
        continue
    with tempfile.TemporaryDirectory() as d:
        for name in rb.build_all(rb.load_board(n), d):
            h = hashlib.sha256(Image.open(f'{d}/{name}').tobytes()).hexdigest()
            if before.get(f'e{n}/{name}') != h:
                bad.append(f'e{n}/{name}')
print('changed:', bad or 'none')
EOF
```
Expected: `changed: none`. 하나라도 있으면 hand 분기 밖을 건드린 것이다 — 고치고 다시 잰다.

- [x] **Step 8: Commit**

```bash
git add .claude/skills/breadboard-diagram/scripts/engine/base.py .claude/skills/breadboard-diagram/scripts/engine/renderer.py tests/test_breadboard_hand.py
git commit -m "feat(hand-sim): 손그림 배선을 획으로 기록하고 MuPDF 로 안티앨리어싱해 overlay 아래 합성한다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 손그림모사 PDF — 빈 판형 쪽 + 벡터 획

**Files:**
- Modify: `scripts/lab/hand_sim.py` (`render_final`, `board_page`, `make_handout_pdf`, `make_pdfs`, 모듈 docstring)
- Test: `tests/test_breadboard_hand.py` (`HandSimScript` 에 추가)

**Interfaces:**
- Consumes: `bb.hand_strokes`, `bb.overlay`, `bb.spec`, `bb.title`; 엔진 `draw_strokes(page, strokes, to_pt, k)`, `_default_template(spec)` (`load_renderer()` 로 접근)
- Produces:
  - `render_final(fn, final_name, work_dir) -> (guide_bb, handout_bb, guide_png: Path)`
  - `template_pdf(spec) -> Path | None`
  - `handout_transform(spec) -> (to_pt: Callable, k: float)`
  - `make_handout_pdf(spec, bbs: list, out: Path) -> Path`

- [x] **Step 1: 실패하는 시험을 더한다 (`HandSimScript` 끝)**

```python
    def _handout(self, experiment, builder, final_name, tamper=None):
        """완성본 하나로 손그림모사 PDF 를 임시 폴더에 만든다 — (pdf, 손그림모사 bb)."""
        from scripts.lab import hand_sim
        board = _load().load_board(experiment)
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        _, sim_bb, _ = hand_sim.render_final(getattr(board, builder), final_name, tmp)
        if tamper:
            tamper(sim_bb)
        return hand_sim.make_handout_pdf(sim_bb.spec, [sim_bb], tmp / 'sim.pdf'), sim_bb

    def test_손그림모사_쪽은_빈_판형_그대로다(self):
        from scripts.lab import hand_grid
        pdf, _ = self._handout(5, 'build_e5_bcd', '실험05_1_결선도_BCD.png')
        tpl = hand_grid.board_image(ROOT / '.claude/assets/breadboard_v2/Breadboard_v2.pdf', 0)
        self.assertEqual(hand_grid.board_image(pdf, 0).md5, tpl.md5)

    def test_손그림모사는_격자_보정이_된다(self):
        # 팀원이 이 위에 그려 오면 review-hand-diagram 이 바로 보정한다(실험06 2·3쪽 GridError 재발 방지)
        from scripts.lab import hand_grid
        pdf, _ = self._handout(5, 'build_e5_bcd', '실험05_1_결선도_BCD.png')
        cal = hand_grid.calibrate(hand_grid.board_image(pdf, 0), 'v2')
        self.assertLessEqual(max(cal.res_x, cal.res_y), 0.5)

    def test_배선은_벡터_획이다(self):
        import pymupdf
        from scripts.lab import hand_sim
        pdf, bb = self._handout(5, 'build_e5_bcd', '실험05_1_결선도_BCD.png')
        lines = [d for d in pymupdf.open(str(pdf))[0].get_drawings() if d['type'] == 's']
        self.assertEqual(len(lines), len(bb.hand_strokes))
        to_pt, k = hand_sim.handout_transform(bb.spec)
        for d, s in zip(lines, bb.hand_strokes):
            p = d['items'][0][1]
            want = to_pt(*s['points'][0])
            self.assertAlmostEqual(p.x, want[0], delta=0.05)
            self.assertAlmostEqual(p.y, want[1], delta=0.05)
            self.assertAlmostEqual(d['width'], s['width'] * k, delta=0.01)

    def test_실험04_v1_도_벡터_획(self):
        import pymupdf
        pdf, bb = self._handout(4, 'build_e4_mux', '실험04_1-1_결선도_4x1MUX.png')
        page = pymupdf.open(str(pdf))[0]
        self.assertEqual(len(page.get_images()), 1)
        self.assertEqual(len([d for d in page.get_drawings() if d['type'] == 's']), len(bb.hand_strokes))

    def test_overlay_에_남은_그림은_거절(self):
        # 배선 밖 그림(instrument 프로브 등)은 벡터 쪽에 못 옮긴다 — 조용히 빠지지 않고 멈춘다
        def tamper(bb):
            bb.overlay.putpixel((10, 10), (255, 0, 0, 255))
        with self.assertRaises(ValueError) as cm:
            self._handout(4, 'build_e4_mux', '실험04_1-1_결선도_4x1MUX.png', tamper=tamper)
        self.assertIn('overlay', str(cm.exception))
```

`실험05_1_결선도_BCD.png` 는 `보고서/실험05/결선도/배치.py` 의 `FINALS` 이름이어야 한다. 다르면 먼저 확인하고 그 이름을 쓴다:

```bash
python -c "from scripts.lab.hand_grid import load_renderer as L; print([n for n, _ in L().load_board(5).FINALS])"
```

- [x] **Step 2: 실패를 확인한다**

Run: `python -m pytest tests/test_breadboard_hand.py::HandSimScript -q`
Expected: FAIL — `render_final` 이 3-튜플(bb, Path, Path)을 돌려줘 `sim_bb.spec` 이 없음 / `handout_transform` 없음.

- [x] **Step 3: `hand_sim.py` 를 고친다**

모듈 docstring 첫 항목을 바꾼다:

```python
- `실험NN_손그림모사.pdf` — 빈 판형 PDF 쪽 그대로에 배선만 벡터 펜 선(한 굵기, 은은한 휨)으로 얹은
  것. 칩·LED·저항·입력 이름은 비운다 — 팀원이 이 위에 부품을 그려 넣는다. 제목은 없다 — 실험 이름은
  작성자가 손으로 적는다. 판형 이미지가 원본 그대로라 `review-hand-diagram` 격자 보정이 그대로 된다.
```

`render_final` 끝 세 줄을 바꾼다:

```python
    seed = hand_seed(handout.name)
    sim_bb = fn(str(handout), hand=seed)
    bb = fn(str(guide), hand=seed, hand_guide=True)
    return bb, sim_bb, guide
```

docstring 첫 줄도: `"""완성본 하나 → (안내판 bb, 손그림모사 bb, 부품그리기 PNG). 둘은 같은 시드다."""`

`board_page` 를 아래 셋으로 바꾼다(`board_page` 의 동작은 같다):

```python
def template_pdf(spec):
    """빈 판형 PDF 경로 — 판형 PNG 옆 같은 이름의 .pdf. 없는 판형(v1)이면 None."""
    png = Path(spec.template[0])
    pdf = (png if png.is_absolute() else REPO_ROOT / png).with_suffix('.pdf')
    return pdf if pdf.exists() else None


def board_page(spec):
    """빈 판형 PDF 의 (쪽 크기 pt, 판형 그림 자리 Rect). 손그림모사 쪽을 이 판에 같은 자리로 놓아야
    팀원이 쓰던 빈 판형과 홀이 겹친다. 판형 PDF 가 없는 판형(v1)은 A4 너비에 판형 그림을 꽉 채운다."""
    pdf = template_pdf(spec)
    if pdf is not None:
        page = pymupdf.open(str(pdf))[0]
        rects = [r for im in page.get_images() for r in page.get_image_rects(im[0])]
        if len(rects) != 1:
            raise ValueError(f'{pdf.name} 에 판형 그림이 {len(rects)}개다 — 하나여야 자리를 안다')
        return page.rect, rects[0]
    w, h = spec.size
    rect = pymupdf.Rect(0, 0, 595, 595 * h / w)
    return rect, rect


def handout_transform(spec):
    """(논리 좌표 -> 손그림모사 쪽 pt, 굵기 배율 pt/논리 px). 판형 그림 자리에 논리 판 전체가 놓인다."""
    _, slot = board_page(spec)
    W, H = spec.size
    sx, sy = slot.width / W, slot.height / H
    return (lambda x, y: (slot.x0 + x * sx, slot.y0 + y * sy)), sx
```

`make_handout_pdf` 를 통째로 바꾼다:

```python
def make_handout_pdf(spec, bbs, out):
    """손그림모사 — 완성본마다 빈 판형 PDF 쪽을 그대로 복사하고 배선을 벡터 획으로 얹는다(2026-10-15).
    래스터로 박으면 태블릿에서 확대할 때 계단이 보여 팀원이 전부 덧칠했다. 제목·실험 이름은 싣지 않는다
    — 작성자가 손으로 적는다(2026-10-12 사용자)."""
    rb = load_renderer()
    size, slot = board_page(spec)
    to_pt, k = handout_transform(spec)
    tpl = template_pdf(spec)
    tpl_doc = pymupdf.open(str(tpl)) if tpl is not None else None
    doc = pymupdf.open()
    for bb in bbs:
        if bb.overlay.getbbox() is not None:
            raise ValueError(f'{bb.title}: 손그림 모드 overlay 에 배선 밖 그림이 남았다 — 벡터 쪽에 못 옮긴다 '
                             '(instrument 프로브 등). make-hand-sim §넓힐 때 손볼 곳')
        if tpl_doc is not None:
            doc.insert_pdf(tpl_doc, from_page=0, to_page=0)
            page = doc[-1]
        else:
            page = doc.new_page(width=size.width, height=size.height)
            page.insert_image(slot, filename=str(rb._default_template(spec)))
        rb.draw_strokes(page, bb.hand_strokes, to_pt, k)
    doc.save(str(out))
    return out
```

`make_pdfs` 의 반복을 바꾼다:

```python
        sim_bbs, guide_pages = [], []
        for name, fn in finals:
            bb, sim_bb, guide = render_final(fn, name, d)
            sim_bbs.append(sim_bb)
            guide_pages.append((f'{bb.title} — 부품 그리기', guide.name, guide_rows(bb)))
        sim_pdf = make_handout_pdf(bb.spec, sim_bbs, d / 'sim.pdf')
```

- [x] **Step 4: 통과를 확인한다**

Run: `python -m pytest tests/test_breadboard_hand.py -q`
Expected: 모두 PASS — 기존 `test_실험05_손그림모사는_브레드보드_PDF_판에_글자_없이`(쪽 크기·그림 자리·글자 없음)와 `test_실험04_MUX_한_장`(쪽별 그림 [1]) 포함.

- [x] **Step 5: Commit**

```bash
git add scripts/lab/hand_sim.py tests/test_breadboard_hand.py
git commit -m "feat(hand-sim): 손그림모사 PDF 를 빈 판형 쪽 그대로 + 벡터 획으로 낸다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 스킬 문서 갱신 + 실험06 재생성

**Files:**
- Modify: `.claude/skills/make-hand-sim/SKILL.md`
- Regenerate: `보고서/실험06/결선도/팀원전달용/실험06_손그림모사.pdf`, `실험06_부품그리기.pdf`

**Interfaces:**
- Consumes: Task 3 의 `python -m scripts.lab.hand_sim --experiment 6`
- Produces: 커밋된 실험06 PDF 두 개

- [x] **Step 1: `SKILL.md` 를 고친다**

파일 표의 손그림모사 줄:

```markdown
| `실험NN_손그림모사.pdf` | 빈 판형 PDF 쪽 그대로 + 배선만 벡터 펜 선(한 굵기 0.9pt, 은은한 휨) — 제목·실험 이름도 없다(작성자가 손으로 적는다). 칩·LED·저항·입력 이름 배지·번호 원·보드 밖 꼬리표는 **비어 있다** | 이 위에 부품을 그려 넣는다. 선은 그대로 써도 되고 원하면 덧칠한다 |
```

절차 4 의 손그림모사 줄:

```markdown
   - 손그림모사: 글자(제목)가 **없고**, 칩·LED·저항 몸통과 입력 이름 배지·번호 원이 **없고**, 보라 입력
     점퍼선은 **있다**. 쪽을 400% 로 확대해도 선 가장자리에 계단이 없다(벡터). 쪽 이미지는 빈 판형 원본이다.
```

정한 규칙의 `- **흔들림은 \`step_wire\` 만** — ±2px, 굵기 ×0.7~1.3. …` 줄을 바꾼다:

```markdown
- **배선은 벡터 펜 선**(2026-10-15) — 엔진은 손그림 모드에서 배선을 긋지 않고 획(`bb.hand_strokes`)으로
  기록한다. 손그림모사 PDF 는 빈 판형 쪽 위에 pymupdf 벡터로, PNG·안내판은 같은 획을 MuPDF 로
  안티앨리어싱한 `bb.hand_layer` 로 긋는다. 획 모델은 구간마다 활 하나(최대 2.5 논리 px) + 미세 떨림(±0.25),
  수직 방향만, 쪽 전체 한 굵기(`HAND_WIDTH` 2.0 = 0.9pt). 근거: 옛 모델(축별 사인 셋 ±2px, 굵기 ×0.7~1.3,
  비안티앨리어싱 래스터)을 실험06 팀원이 "계단현상·노이즈" 로 보고 전부 덧칠했다. 번호 원·보드 밖
  꼬리표·사이드카·도장은 없다.
```

`- **손그림모사 쪽 = 빈 판형 PDF 쪽**(\`hand_sim.board_page\`) — …` 줄을 바꾼다:

```markdown
- **손그림모사 쪽 = 빈 판형 PDF 쪽 그대로**(`hand_sim.make_handout_pdf`) — v2 는 `Breadboard_v2.pdf` 쪽을
  복사해 판형 이미지 md5 가 원본과 같다. 그래서 그 위에 그려 온 PDF 를 `review-hand-diagram` 이 바로
  보정한다. 손그림 모드 overlay 에 배선 밖 그림이 남으면 생성기가 멈춘다. 제목·실험 이름은 싣지 않는다 —
  작성자가 손으로 적는다(사용자 결정). 판형 PDF 가 없는 v1 은 A4 너비에 템플릿 그림을 꽉 채운다.
```

"넓힐 때 손볼 곳" 의 첫 줄(`- \`connect_unused_inputs\` 의 미사용 입력 선은 \`draw.line\` 곧은 선이다 — 흔들리지 않는다.`)을 지우고, 그 절 끝 문장을 `이 둘 중 하나를 쓰는 주차가 오면 엔진 결함으로 보고하고 멈춘다.` 로 고친다.

- [x] **Step 2: 실험06 을 다시 뽑는다**

기존 PDF 를 스크래치에 복사해 둔 뒤 생성한다:

```bash
SCRATCH="<your scratchpad dir>"
cp 보고서/실험06/결선도/팀원전달용/실험06_손그림모사.pdf 보고서/실험06/결선도/팀원전달용/실험06_부품그리기.pdf "$SCRATCH/"
python -m scripts.lab.hand_sim --experiment 6
```
Expected: 오류 없이 끝난다. `overlay 에 배선 밖 그림이 남았다` 가 나오면 멈추고 그 완성본 이름을 보고한다.

- [x] **Step 3: 눈으로 본다**

```bash
SCRATCH="<your scratchpad dir>"
python - "$SCRATCH" <<'EOF'
import sys, pymupdf
S = sys.argv[1]
for name in ('손그림모사', '부품그리기'):
    d = pymupdf.open(f'보고서/실험06/결선도/팀원전달용/실험06_{name}.pdf')
    for i, p in enumerate(d):
        p.get_pixmap(dpi=60).save(f'{S}/{name}_p{i + 1}.png')
        if name == '손그림모사':     # 왼쪽 위 입력선 부근을 400% 로 — 계단이 없어야 한다
            # 판 왼쪽 위(레일~a열, 3~9행) — v2 논리 행 3 = y 374 → 쪽 y ≈ 48.3 + 374·0.466 ≈ 223pt
            p.get_pixmap(dpi=600, clip=pymupdf.Rect(40, 210, 200, 290)).save(f'{S}/{name}_p{i + 1}_zoom.png')
    print(name, len(d), '쪽')
EOF
```
Read 로 각 PNG 를 본다. 확인할 것:
- 손그림모사 3쪽(SR·D·JK): 제목 없음, 부품·배지 없음, 선이 얇고 한 굵기, 출렁이지 않고 한 번만 휜다. `_zoom` 에서 가장자리가 매끈하다.
- 부품그리기 3쪽: 선은 전부 회색, 칩·LED·저항·입력 배지는 색, 부품표가 쪽 안에서 끝난다.

- [x] **Step 4: 전체 시험**

Run: `python -m pytest -q`
Expected: 모두 PASS. 실패가 이 변경과 무관해 보이면(예: 간헐 시험) 메모리 `lab-harness-test-env` 의 방법으로 갈라 보고한다.

- [x] **Step 5: Commit**

```bash
git add .claude/skills/make-hand-sim/SKILL.md 보고서/실험06/결선도/팀원전달용/실험06_손그림모사.pdf 보고서/실험06/결선도/팀원전달용/실험06_부품그리기.pdf
git commit -m "docs(make-hand-sim): 벡터 펜 선 규칙으로 갱신하고 실험06 팀원전달용 PDF 를 다시 뽑는다

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
`결선도/` 에 새 PNG·JSON 이 생겼으면 커밋하지 말고 보고한다(스킬 절차 6).
