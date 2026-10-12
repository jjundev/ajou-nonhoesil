# 결선도 손그림 모사 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실험04 4x1 MUX 완성본 한 장을, 배선만 마커로 손으로 그은 것처럼 흔들리게 그린 PNG 로 뽑는다 — 팀원 손그림 대신 보고서에 붙일 수 있는지 눈으로 판정하는 시험판.

**Architecture:** 렌더러에 `hand=<시드 int>` 모드를 더한다. 흔들림은 `step_wire` 가 긋는 배선 선에만 건다(순수 함수 `_hand_polyline`) — 칩·배지·LED 는 그대로. 번호 원과 보드 밖 입력 꼬리표는 그리지 않되 점유표·순서표·`verify()` 는 평소와 똑같이 돈다. 시험 스크립트가 빌더를 `hand=` 로 불러 `tmp/hand-sim/` 에 PNG 만 쓴다.

**Tech Stack:** Python 3 · Pillow · `random.Random`(외부 노이즈 라이브러리 없음) · unittest/pytest(`.venv/bin/python -m pytest`)

**Spec:** 이 대화의 설계(파일 없음). 확정값은 아래 Global Constraints 에 옮겼다. 설계 표 중 코드 확인 후 바뀐 것:
- 로고는 템플릿 JPG 에 박혀 있다(`set_header` 는 아무것도 안 그린다, `engine/renderer.py:394`) → 이번 범위 밖, 그대로 둔다.
- `numbered` 를 끄지 않는다 — 빌더가 `enable_steps()` 로 다시 켜고 순서표가 필요하다. 번호 원 **그리기만** 막는다.
- `_ScaledDraw` 서브클래스로 하지 않는다 — 칩·배지·번호 원까지 흔들려 결정 #3(부품 그대로)과 부딪친다.
- 출력은 `손그림/` 이 아니라 `tmp/hand-sim/`(gitignore) — `손그림/` 에는 팀원 원본이 같은 이름 규칙으로 있다.

## Global Constraints

- 흔들림 진폭: 논리 좌표 **±2px**(SCALE=2 라 실픽셀 ±4px). 축마다 따로, 절대값이 2.0 을 넘지 않는다.
- 선 굵기: 배선 한 가닥마다 기본 굵기 × U(0.7, 1.3), 반올림, 최소 1 — 한 가닥 안에서는 일정(마커 펜).
- 배선 양 끝점은 **흔들지 않는다** — 홀 위에 정확히 앉아야 한다. 끝에서 12px 동안 진폭을 0→1 로 올린다.
- 끝점 도트: 반지름에 축마다 U(-1, +1)px.
- 번호 원(`_marker`)·보드 밖 입력 꼬리표(`_tag`)는 hand 모드에서 그리지 않는다. 보드 안 신호 배지(`signal_tag`)는 그린다.
- hand 모드 `export` 는 `verify()` 를 돌리고, 사이드카 JSON 과 PNG 도장(`STAMP_KEY`)은 쓰지 않는다.
- hand 는 완성본 전용: `baseline` 이나 `layer` 와 함께 주면 `ValueError`.
- `hand=None`(기본)이면 렌더 결과가 바이트 단위로 지금과 같다.
- 시드 = 출력 파일 이름(basename) UTF-8 sha256 앞 8바이트 big-endian int.
- 코드 주석·커밋 메시지는 한국어, 식별자는 영어(저장소 관례).

## Review Focus

1. **끝점이 홀에서 벗어남** — 흔든 선 끝이 옆 홀로 보이면 손그림이 오답이 된다. 첫·끝 점이 입력과 정확히 같아야 한다 → Task 1 `test_끝점은_그대로다`.
2. **hand 가 논리 상태를 바꿈** — 흔들린 좌표가 점유표·구간에 새면 `verify()` 가 다른 판정을 낸다. 같은 빌더의 `steps`·`_segments`·`_leads` 가 hand 유무와 무관하게 같아야 한다 → Task 2 `test_hand_는_논리_상태를_안_바꾼다`.
3. **같은 시드인데 그림이 다름** — 다시 뽑을 때마다 바뀌면 보고서 PNG 가 커밋마다 흔들린다 → Task 1 `test_같은_시드는_같은_점`, Task 2 `test_같은_시드는_같은_PNG`.
4. **기본 렌더가 달라짐** — hand 분기가 새어 기존 결선도 도장이 깨진다 → Task 2 `test_hand_없으면_PNG_가_그대로다` + 결선도 시험 전체.
5. **hand 렌더가 사이드카를 씀** — 같은 폴더에 `.json` 이 생기면 결선도 검사 도구가 그것을 정본으로 읽는다 → Task 2 `test_hand_export_는_PNG_만_쓴다`.

---

### Task 1: 흔들린 선 계산 함수

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/render_breadboard.py:1-12` (`import random` 추가)
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/base.py` (`_ScaledDraw` 바로 뒤, 161행 `_font` 앞)
- Test: `tests/test_breadboard_hand.py` (새 파일)

**Interfaces:**
- Produces:
  - `_hand_polyline(points: list[tuple[float, float]], rng: random.Random, amp: float = 2.0, step: float = 6.0, ramp: float = 12.0) -> list[tuple[float, float]]`
  - `_hand_width(width: int, rng: random.Random) -> int`
  - `_hand_dot(p: tuple[float, float], r: float, rng: random.Random) -> list[float]` — `[x0, y0, x1, y1]` 타원 상자

엔진 조각은 `render_breadboard.py` 이름공간에서 실행된다(`engine/base.py:1-3`) — 조각 안에서 import 하지 말고 진입점에 `import random` 을 둔다.

- [ ] **Step 1: 실패하는 시험 작성**

`tests/test_breadboard_layer.py:14-18` 의 `_load()` 를 그대로 베껴 엔진을 부른다. 파일 머리 import 는 이 파일 전체(Task 2·3 포함)가 쓰는 것을 한 번에 둔다: `random, shutil, tempfile, unittest, pathlib.Path, PIL.Image`, `ROOT = Path(__file__).resolve().parents[1]`.

```python
class HandPolyline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _pts(self, seed=7):
        pts = [(100.0, 50.0), (100.0, 300.0), (400.0, 300.0)]
        return pts, self.mod._hand_polyline(pts, random.Random(seed))

    def test_끝점은_그대로다(self):
        pts, out = self._pts()
        self.assertEqual(out[0], pts[0])
        self.assertEqual(out[-1], pts[-1])

    def test_진폭은_2px_를_안_넘는다(self):
        # 원 경로(두 축 정렬 구간) 위 가장 가까운 점까지 축별 거리
        _, out = self._pts()
        for x, y in out:
            d = min(max(abs(x - 100), max(0, 50 - y, y - 300)),
                    max(abs(y - 300), max(0, 100 - x, x - 400)))
            self.assertLessEqual(d, 2.0 + 1e-9)

    def test_실제로_흔들린다(self):
        _, out = self._pts()
        self.assertTrue(any(abs(x - 100) > 0.5 for x, y in out if 80 < y < 280))

    def test_같은_시드는_같은_점(self):
        self.assertEqual(self._pts(3)[1], self._pts(3)[1])
        self.assertNotEqual(self._pts(3)[1], self._pts(4)[1])

    def test_짧은_선도_된다(self):
        out = self.mod._hand_polyline([(10.0, 10.0), (13.0, 10.0)], random.Random(1))
        self.assertEqual((out[0], out[-1]), ((10.0, 10.0), (13.0, 10.0)))

    def test_굵기는_0_7_에서_1_3_배(self):
        ws = {self.mod._hand_width(3, random.Random(s)) for s in range(200)}
        self.assertTrue(ws <= {2, 3, 4} and len(ws) > 1)
        self.assertEqual(self.mod._hand_width(1, random.Random(0)) >= 1, True)
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -v`
Expected: FAIL — `AttributeError: module 'render_breadboard' has no attribute '_hand_polyline'`

- [ ] **Step 3: `base.py` 에 세 함수 구현**

`_hand_polyline` 알고리즘(시험만으로 정해지지 않는 부분):
```
L = 폴리라인 전체 길이
축마다(x, y) 사인 3개: 파장 U(40, 160), 위상 U(0, 2π), 가중치 U(0.5, 1) — 가중치 합으로 나눠 |합| ≤ 1
각 구간을 step 간격으로 다시 찍고(구간 끝 꼭짓점 포함, 중복 없이), 누적 길이 s 에서
  taper = min(1, s / ramp, (L - s) / ramp)
  점 += amp * taper * (noise_x(s), noise_y(s))
첫·끝 점은 계산 없이 입력값 그대로 넣는다(부동소수 오차로 0.0000001 어긋나지 않게)
```
`_hand_width`: `max(1, round(width * rng.uniform(0.7, 1.3)))`. `_hand_dot`: 축마다 `r + rng.uniform(-1, 1)`.

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -v`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/render_breadboard.py .claude/skills/breadboard-diagram/scripts/engine/base.py tests/test_breadboard_hand.py
git commit -m "feat(breadboard): 손그림 모사용 흔들린 선·굵기·도트 함수를 더한다"
```

---

### Task 2: 렌더러 hand 모드와 실험04 MUX 빌더 연결

**Files:**
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/renderer.py:6` (`__init__`), `:541-548` (`_marker`), `:624-626` (`step_wire` 선·도트), `:1298-1333` (`export`)
- Modify: `.claude/skills/breadboard-diagram/scripts/engine/helpers.py:19-21` (`_tag`)
- Modify: `보고서/실험04/결선도/배치.py:393-411` (`build_e4_mux` 만)
- Test: `tests/test_breadboard_hand.py`

**Interfaces:**
- Consumes: Task 1 의 `_hand_polyline`, `_hand_width`, `_hand_dot`
- Produces:
  - `BreadboardRenderer(template_path=None, baseline=None, layer=None, board=DEFAULT_BOARD, palette=False, hand=None)` — `hand: int | None` 가 시드. 속성 `self.hand`, `self._hand_rng = random.Random(hand)`(hand 가 있을 때만)
  - `build_e4_mux(output_path, template_path=None, stage=None, baseline=None, layer=None, hand=None)` — `hand` 를 렌더러에 그대로 넘긴다
  - hand 모드 `export(output_path, max_row)` 는 PNG 하나만 쓴다

변경점 요약(각각 한 군데):
- `__init__`: `hand is not None` 이면서 `baseline` 이나 `layer` 가 있으면 `ValueError('hand 는 완성본에만 준다 — baseline·layer 와 함께 못 준다')`.
- `step_wire` 624~626: hand 면 `draw.line(_hand_polyline(points, rng), width=_hand_width(width, rng), joint='curve')`, 도트는 `_hand_dot`. **`points` 원본은 그 뒤 `lead`·`_segments`·`_register_pass` 에 그대로 넘긴다.**
- `_marker`: `marker_boxes.append` 는 하고, hand 면 그리지 않고 돌아간다.
- `helpers._tag`: `margin_tag_boxes.append` 는 하고, `bb.hand` 면 `draw_badge` 를 건너뛴다.
- `export`: hand 면 `verify()` → 합성·자르기 → `PngInfo` 없이 저장 → JSON 안 씀.

- [ ] **Step 1: 실패하는 시험 작성**

```python
class HandRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board(4)

    def _render(self, hand):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        out = tmp / 'mux.png'
        bb = self.board.build_e4_mux(str(out), hand=hand)
        return bb, out, tmp

    def test_hand_는_논리_상태를_안_바꾼다(self):
        a, _, _ = self._render(None)
        b, _, _ = self._render(42)
        self.assertEqual(a.steps, b.steps)
        self.assertEqual(a._segments, b._segments)
        self.assertEqual(a._leads, b._leads)

    def test_hand_export_는_PNG_만_쓴다(self):
        _, out, tmp = self._render(42)
        self.assertEqual(sorted(p.name for p in tmp.iterdir()), ['mux.png'])
        self.assertNotIn(self.mod.STAMP_KEY, Image.open(out).info)

    def test_같은_시드는_같은_PNG(self):
        _, a, _ = self._render(42)
        _, b, _ = self._render(42)
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_hand_없으면_PNG_가_그대로다(self):
        # 정본 완성본과 픽셀 비교 — 도장·사이드카는 기존 시험이 본다
        _, out, _ = self._render(None)
        ref = ROOT / '보고서/실험04/결선도/실험04_1-1_결선도_4x1MUX.png'
        self.assertEqual(Image.open(out).tobytes(), Image.open(ref).convert('RGB').tobytes())

    def test_번호_원을_안_그린다(self):
        bb, _, _ = self._render(42)
        self.assertTrue(bb.marker_boxes)
        px = bb.overlay.load()
        for x0, y0, x1, y1 in bb.marker_boxes:
            cx, cy = int((x0 + x1) / 2 * self.mod.SCALE), int((y0 + y1) / 2 * self.mod.SCALE)
            self.assertNotEqual(px[cx, cy], (255, 255, 255, 245))

    def test_기준선_이나_층과_못_섞는다(self):
        with self.assertRaises(ValueError):
            self.mod.BreadboardRenderer(None, layer=(1, 2), board='v1', hand=1)
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -v`
Expected: `HandRender` 6개 FAIL — `TypeError: build_e4_mux() got an unexpected keyword argument 'hand'`(마지막 하나는 `__init__` 쪽 TypeError). `test_hand_없으면_PNG_가_그대로다` 도 같은 이유로 FAIL.

- [ ] **Step 3: 위 변경점 요약대로 구현**

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -v`
Expected: 12 passed

- [ ] **Step 5: 결선도 시험 전체로 기본 렌더 회귀 확인**

Run: `.venv/bin/python -m pytest tests/ -k "breadboard or hand or trace" -q`
Expected: 실패 0 (작업 전 같은 명령의 통과 수와 같다 — 시작 전에 한 번 돌려 숫자를 적어 둔다)

- [ ] **Step 6: 커밋**

```bash
git add .claude/skills/breadboard-diagram/scripts/engine/renderer.py .claude/skills/breadboard-diagram/scripts/engine/helpers.py 보고서/실험04/결선도/배치.py tests/test_breadboard_hand.py
git commit -m "feat(breadboard): 완성본을 손그림처럼 흔들어 그리는 hand 모드를 더한다"
```

---

### Task 3: 시험판 한 장 뽑기

**Files:**
- Create: `scripts/lab/hand_sim.py`
- Test: `tests/test_breadboard_hand.py`

**Interfaces:**
- Consumes: Task 2 의 `build_e4_mux(..., hand=)`, 엔진 `load_board(n)`
- Produces:
  - `hand_seed(filename: str) -> int` — Global Constraints 의 시드 규칙
  - `main(argv: list[str] | None = None) -> Path` — 인자 `--experiment N --final <완성본 PNG 이름> [--out DIR]`(기본 `tmp/hand-sim`). 그 주차 `FINALS` 에서 이름이 같은 빌더를 찾아 `hand=hand_seed(out_name)` 로 부르고, 결과 경로를 돌려준다. 출력 이름은 `--final` 의 `결선도` 를 `손그림모사` 로 바꾼 것. `FINALS` 에 없는 이름이면 `SystemExit` 에 가능한 이름 목록을 싣는다.

엔진은 `tests/test_breadboard_layer.py:14-18` 과 같은 `importlib` 방식으로 부른다(`scripts/lab/trace_guide.py` 가 엔진을 부르는 방식이 있으면 그것을 따른다).

- [ ] **Step 1: 실패하는 시험 작성**

```python
class HandSimScript(unittest.TestCase):
    def test_시드는_파일이름으로_정해진다(self):
        from scripts.lab.hand_sim import hand_seed
        self.assertEqual(hand_seed('a.png'), hand_seed('a.png'))
        self.assertNotEqual(hand_seed('a.png'), hand_seed('b.png'))

    def test_완성본_한_장을_뽑는다(self):
        from scripts.lab import hand_sim
        tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp)
        out = hand_sim.main(['--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png',
                             '--out', str(tmp)])
        self.assertEqual(out.name, '실험04_1-1_손그림모사_4x1MUX.png')
        self.assertEqual([p.name for p in tmp.iterdir()], [out.name])

    def test_없는_완성본은_목록과_함께_멈춘다(self):
        from scripts.lab import hand_sim
        with self.assertRaises(SystemExit) as cm:
            hand_sim.main(['--experiment', '4', '--final', '없음.png'])
        self.assertIn('실험04_1-1_결선도_4x1MUX.png', str(cm.exception))
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py::HandSimScript -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.lab.hand_sim'`

- [ ] **Step 3: `scripts/lab/hand_sim.py` 구현** — 위 Interfaces 대로. 실험04 는 `build_e4_mux` 만 `hand=` 를 받으므로 DMUX 를 고르면 `TypeError` 가 그대로 올라가도 된다(이번 범위 밖).

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -v`
Expected: 15 passed

- [ ] **Step 5: 실제 한 장 뽑고 사용자에게 보인다**

Run: `.venv/bin/python -m scripts.lab.hand_sim --experiment 4 --final 실험04_1-1_결선도_4x1MUX.png`
Expected: `tmp/hand-sim/실험04_1-1_손그림모사_4x1MUX.png` 생성. 이 PNG 와 `보고서/실험04/결선도/손그림/실험04_1-1_손그림_4x1MUX.png` 를 나란히 사용자에게 보내 판정받는다 — 진폭·굵기·배지 유지가 맞는지. PNG 는 `tmp/` 라 커밋하지 않는다.

- [ ] **Step 6: 커밋**

```bash
git add scripts/lab/hand_sim.py tests/test_breadboard_hand.py
git commit -m "feat(breadboard): 완성본 한 장을 손그림 모사로 뽑는 시험 스크립트를 더한다"
```
