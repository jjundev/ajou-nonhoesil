"""v2 배선기 — 엔진 `route_plan`·`wire_metrics`·밀도 재순위.

설계: `docs/plans/2026-10-04-v2-배선기-밀도-설계.md`. 기준 데이터는 실험04 v2 시험판
(`tests/fixtures/board_v2_e4/배치.py`). `plans_lambda0.json` 은 지금 `LAYOUT` 에서 λ=0 경로·번호 원
자리다 — 배선기를 바꿔도 λ=0 이면 그대로 나와야 한다. 배치(`LAYOUT`)를 바꾸면 다시 뜬다(2026-10-05
배치기 적용 때 다시 떴다).
"""
import importlib.util
import json
import math
import random
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.lab import route_sweep as rs
from tests import _renders

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'
SNAP = ROOT / 'tests/fixtures/board_v2_e4/plans_lambda0.json'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plain(plans):
    """튜플 → 리스트 (JSON 과 맞대려고)."""
    return json.loads(json.dumps(plans))


class LambdaZero(unittest.TestCase):
    """λ=0 이면 옮기기 전 시험판 배선기와 같은 경로·번호 원 자리."""
    render_group = 'board_v2_e4'

    @classmethod
    def setUpClass(cls):
        cls.mod = _renders.engine()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')
        cls.snap = json.loads(SNAP.read_text(encoding='utf-8'))

    def test_MUX(self):
        self.assertEqual(_plain(self.board._mux_paths(0.0)), self.snap['mux'])

    def test_DMUX(self):
        self.assertEqual(_plain(self.board._dmux_paths(0.0)), self.snap['dmux'])


class RoutePlanBoard(unittest.TestCase):
    def test_v1_이면_멈춘다(self):
        mod = _load()
        with self.assertRaisesRegex(ValueError, 'v2'):
            mod.route_plan(lambda bb, stage, superset=False: None, {}, [], board='v1')

    def test_막히면_막힌_선을_댄다(self):
        """수리가 앞 선을 바꿔 봐도 안 풀리면, 메시지는 수리하던 앞 선이 아니라 막힌 선의 끝을 댄다
        (2026-10-04 최종 검토 — 수리 루프가 frm·to 를 덮어써 앞 선 끝 + 막힌 선 설명이 섞였다)."""
        mod = _load()

        def fake_routes(bb, chips, frm, to, density_weight=0.0):
            if to == ('U', 99):
                return
            x, y = bb.cols['left']['b'], bb.r_y(frm[1])
            yield [(x, y), (x, y + 2 * bb.spec.row_pitch)], (x + 12, y + bb.spec.row_pitch)

        mod._routes = fake_routes
        wires = [(1, None, 'sig', ('U', 10), ('U', 12), '앞 선'),
                 (1, None, 'sig', ('U', 30), ('U', 99), '막힌 선')]
        with self.assertRaises(AssertionError) as cm:
            mod.route_plan(lambda bb, stage, superset=False: None, {}, wires)
        self.assertEqual(str(cm.exception), "경로 없음: ('U', 30) -> ('U', 99) (막힌 선)")


    def test_뒤_선_끝점을_덮은_번호_원은_다시_고른다(self):
        """번호 원은 그 선을 깔 때 고르니 **뒤에 깔린 선의 끝점**을 모른다 — 배치 탐색 후보 3 의 DMUX 에서
        Y1 번호 원이 나중에 꽂힌 좌 i22 를 덮었다(2026-10-05). 다 깐 superset 판에서 다시 본다."""
        mod = _load()
        L = mod.board_spec('v2').cols['left']
        y = lambda r: mod.board_spec('v2').row0 + (r - 1) * mod.board_spec('v2').row_pitch

        def fake_routes(bb, chips, frm, to, density_weight=0.0):
            if frm == ('U', 1):    # 앞 선 — 번호 원을 (아직 빈) c12 위에 둔다
                yield [(L['a'], y(10)), (L['a'] - 30, y(10)), (L['a'] - 30, y(14)), (L['a'], y(14))], (L['c'], y(12))
            else:                  # 뒤 선 — c12 에 꽂힌다
                yield [(L['c'], y(12)), (L['c'] + 12, y(12)), (L['c'] + 12, y(30)), (L['c'], y(30))], (L['c'] + 12, y(21))

        mod._routes = fake_routes
        wires = [(1, None, 'sig', ('U', 1), ('U', 2), '앞 선'),
                 (1, None, 'sig', ('U', 3), ('U', 4), '뒤 선')]
        plans = mod.route_plan(lambda bb, stage, superset=False: None, {}, wires)
        self.assertNotEqual(plans[0][1], (L['c'], y(12)))
        bb = mod.BreadboardRenderer(None, board='v2')
        bb.enable_steps()
        for (_s, _e, kind, _f, _t, desc), (p, m) in zip(wires, plans):
            bb.step_wire(p, kind, desc, marker_at=m)
        self.assertEqual([x for x in bb.marker_problems() if '홀' in x], [])

class Metrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_붙어_달리는_정도(self):
        c = self.mod._crowding
        self.assertEqual(c(('v', 0, 0, 100), ('h', 0, 0, 100), 19), 0)         # 축이 다르다
        self.assertEqual(c(('v', 0, 0, 100), ('v', 0, 0, 100), 19), 0)         # 포개짐은 R4 몫
        self.assertEqual(c(('v', 0, 0, 100), ('v', 19, 0, 100), 19), 0)        # 1칸 떨어지면 0
        self.assertAlmostEqual(c(('v', 0, 0, 100), ('v', 9.5, 50, 200), 19), 25)  # 겹침 50 × 0.5

    def test_지표(self):
        bb = SimpleNamespace(spec=SimpleNamespace(row_pitch=19.0), _segments=[
            ('sig', [(0, 0), (0, 190)], 'a'),
            ('mid', [(9.5, 0), (9.5, 95), (50, 95)], 'b'),
            ('gnd', [(4, 0), (4, 190)], '전원은 안 센다'),
        ])
        m = self.mod.wire_metrics(bb)
        self.assertAlmostEqual(m['length'], (190 + 95 + 40.5) / 19)
        self.assertEqual(m['bends'], 1)
        self.assertAlmostEqual(m['density'], 95 * 0.5 / 19)

    def test_사선은_밀도에_안_든다(self):
        bb = SimpleNamespace(spec=SimpleNamespace(row_pitch=19.0), _segments=[
            ('sig', [(0, 0), (30, 40)], '사선'),
            ('sig', [(5, 0), (35, 40)], '사선'),
        ])
        m = self.mod.wire_metrics(bb)
        self.assertAlmostEqual(m['length'], 100 / 19)
        self.assertEqual(m['density'], 0)

    def test_같은_선_안은_안_센다(self):
        bb = SimpleNamespace(spec=SimpleNamespace(row_pitch=19.0), _segments=[
            ('sig', [(0, 0), (0, 100), (6, 100), (6, 0)], 'U자'),
        ])
        self.assertEqual(self.mod.wire_metrics(bb)['density'], 0)

    def test_새_경로의_밀도_증분(self):
        placed = [('v', 100, 0, 200)]
        self.assertAlmostEqual(self.mod._density_cost(((105, 0), (105, 200)), placed, 19),
                               200 * (1 - 5 / 19))


class Rerank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    A = ((105, 0), (105, 200))      # 깔린 선(x=100) 5px 옆 — 싸지만 붙어 달린다
    B = ((150, 0), (150, 200))      # 50px 떨어짐 — 조금 비싸다

    def test_λ0_은_정적_순서다(self):
        got = self.mod._rerank([(200, self.A), (210, self.B)], [('v', 100, 0, 200)], 19, 0.0)
        self.assertEqual(got, [self.A, self.B])

    def test_λ_가_크면_떨어진_선이_앞선다(self):
        got = self.mod._rerank([(200, self.A), (210, self.B)], [('v', 100, 0, 200)], 19, 1.0)
        self.assertEqual(got, [self.B, self.A])

    def test_앞_top_개만_다시_매긴다(self):
        got = self.mod._rerank([(200, self.A), (210, self.B)], [('v', 100, 0, 200)], 19, 1.0, top=1)
        self.assertEqual(got, [self.A, self.B])

    def test_동률은_경로_순서다(self):
        C = ((160, 0), (160, 200))
        got = self.mod._rerank([(210, C), (210, self.B)], [], 19, 1.0)
        self.assertEqual(got, [self.B, C])


def _row(w, length, density):
    return {'weight': w, 'length': length, 'bends': 0, 'density': density}


class Sweep(unittest.TestCase):
    def test_한도_안에서_밀도_합_최소(self):
        rows = {'mux': [_row(0, 100, 10), _row(1, 110, 6), _row(2, 120, 2)],
                'dmux': [_row(0, 50, 5), _row(1, 52, 4), _row(2, 53, 1)]}
        self.assertEqual(rs.pick(rows), 1)        # λ=2 는 MUX 길이 +20%

    def test_줄지_않으면_0(self):
        rows = {'mux': [_row(0, 100, 10), _row(1, 101, 10)], 'dmux': [_row(0, 50, 5), _row(1, 50, 5)]}
        self.assertEqual(rs.pick(rows), 0)

    def test_막힌_λ_는_건너뛴다(self):
        rows = {'mux': [_row(0, 100, 10), {'weight': 1, 'blocked': '경로 없음'}],
                'dmux': [_row(0, 50, 5), _row(1, 50, 1)]}
        self.assertEqual(rs.pick(rows), 0)

    def test_기준_행이_없으면_멈춘다(self):
        with self.assertRaises(ValueError):
            rs.pick({'mux': [{'weight': 0, 'blocked': '경로 없음'}], 'dmux': [_row(0, 50, 5)]})
        with self.assertRaises(ValueError):
            rs.pick({'mux': [_row(1, 100, 10)], 'dmux': [_row(1, 50, 5)]})

    def test_막히면_막힘_행이다(self):
        def build(path, density_weight):
            raise AssertionError('경로 없음: U1 -> U3\n자세히')
        got = rs.measure(None, build, 'x.png', 4.0)
        self.assertEqual(got, {'weight': 4.0, 'blocked': '경로 없음: U1 -> U3'})


class ChosenWeight(unittest.TestCase):
    """엔진 DENSITY_WEIGHT 가 설계 #11 을 지킨다 — 두 회로 모두 길이 ≤ λ=0 × 1.15, 밀도 합은 줄었다.
    2026-10-04 스윕에서 λ=0.5 가 골라졌다(밀도 합 40.7 → 26.9칸) — 0 으로 돌아가면 걸린다."""
    render_group = 'board_v2_e4'

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.mod = _renders.engine()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')
        cls.tmp = tempfile.mkdtemp()

    def _m(self, build, name, w):
        import os
        return self.mod.wire_metrics(build(os.path.join(self.tmp, name), density_weight=w))

    def test_설계_11(self):
        w = self.mod.DENSITY_WEIGHT
        self.assertGreater(w, 0)
        got = {}
        for key, build in (('mux', self.board.build_trial_mux), ('dmux', self.board.build_trial_dmux)):
            got[key] = (self._m(build, f'{key}0.png', 0.0), self._m(build, f'{key}w.png', w))
            self.assertLessEqual(got[key][1]['length'], got[key][0]['length'] * 1.15, key)
        self.assertLess(sum(v[1]['density'] for v in got.values()),
                        sum(v[0]['density'] for v in got.values()))


def _ref_on_seg(p, a, b, margin=6):
    """선검사를 넣기 전 엔진 `_on_seg` 본문 그대로(2026-10-05 `engine/router.py`)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = (dx * dx + dy * dy) ** .5
    if length < 1:
        return False
    along = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length
    if along <= margin or length - along <= margin:
        return False
    return abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / length < 1.5


def _ref_seg_in_box(a, b, box):
    """선검사를 넣기 전 엔진 `_seg_in_box` 본문 그대로(2026-10-05 `engine/checks.py`)."""
    x0, y0, x1, y1 = box
    n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / 2) + 1
    return any(x0 < a[0] + (b[0] - a[0]) * t / n < x1 and y0 < a[1] + (b[1] - a[1]) * t / n < y1
               for t in range(n + 1))


def _coord(rng, hi):
    """판 좌표 꼴 — 정수, 반 px, 아무 실수, 0.1 배수(0.1 + 0.2 꼴 반올림이 나온다)."""
    k = rng.randrange(4)
    if k == 0:
        return rng.randint(0, hi)
    if k == 1:
        return rng.randint(0, 2 * hi) / 2
    if k == 2:
        return rng.random() * hi
    return 0.1 * rng.randint(0, 10 * hi)


def _segment(rng, hi):
    """가로·세로·대각선·1px 미만 구간 하나."""
    a = (_coord(rng, hi), _coord(rng, hi))
    k = rng.randrange(4)
    if k == 0:
        return a, (_coord(rng, hi), a[1])
    if k == 1:
        return a, (a[0], _coord(rng, hi))
    if k == 2:
        return a, (_coord(rng, hi), _coord(rng, hi))
    return a, (a[0] + rng.random() * .9, a[1])


def _near_points(rng, a, b):
    """구간 ab 둘레의 점 — 끝 여백(6) 경계 앞뒤, 수직 거리 1.5·2 경계 앞뒤, 반 px 로 맞춘 것도."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    pts = [a, b]
    for t in (0, .01, 5.99, 6, 6.01, length / 2, length - 6.01, length - 6, length, rng.random() * length):
        for s in (0, 1.49, 1.5, 1.51, 1.99, 2, 2.01, rng.uniform(-5, 5)):
            for sign in (1, -1):
                p = (a[0] + t * ux - sign * s * uy, a[1] + t * uy + sign * s * ux)
                pts += [p, (round(p[0] * 2) / 2, round(p[1] * 2) / 2)]
    return pts


def _boxes(rng, a, b):
    """구간 ab 의 끝 둘레에 변이 걸치는 상자 — 변이 끝점과 같음·±ulp·±0.5·±1·±1.000001, 아무 상자 하나."""
    xs, ys = sorted((a[0], b[0])), sorted((a[1], b[1]))
    out = []
    for e in (0, 1e-9, -1e-9, .5, -.5, 1, -1, 1.000001, -1.000001):
        out += [(xs[1] + e, ys[0] - 5, xs[1] + 20, ys[1] + 5),
                (xs[0] - 20, ys[0] - 5, xs[0] - e, ys[1] + 5),
                (xs[0] - 5, ys[1] + e, xs[1] + 5, ys[1] + 20),
                (xs[0] - 5, ys[0] - 20, xs[1] + 5, ys[0] - e)]
    x0, y0 = _coord(rng, 200), _coord(rng, 200)
    out.append((x0, y0, x0 + rng.uniform(1, 40), y0 + rng.uniform(1, 40)))
    return out


class PrefilterSame(unittest.TestCase):
    """`_on_seg`·`_seg_in_box` 의 범위 선검사가 답을 안 바꾼다 — 경로가 한 칸도 안 바뀌어야 하는 속도
    개선이다(`docs/plans/2026-10-05-배선기-속도-설계.md`). 대조용 `_ref_*` 는 선검사 전 본문이다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _renders.engine()

    def test_구간_위_점_검사가_원래와_같다(self):
        rng = random.Random(20261005)
        bad = []
        for _ in range(1000):
            a, b = _segment(rng, 800)
            for p in _near_points(rng, a, b):
                for margin in (6, 0):
                    want = _ref_on_seg(p, a, b, margin)
                    if self.mod._on_seg(p, a, b, margin) != want:
                        bad.append((p, a, b, margin, want))
        self.assertEqual(bad[:5], [], f'{len(bad)}건 다름')

    def test_선분_상자_검사가_원래와_같다(self):
        rng = random.Random(20261005)
        bad = []
        for _ in range(500):
            a, b = _segment(rng, 200)
            for box in _boxes(rng, a, b):
                want = _ref_seg_in_box(a, b, box)
                if self.mod.BreadboardRenderer._seg_in_box(a, b, box) != want:
                    bad.append((a, b, box, want))
        self.assertEqual(bad[:5], [], f'{len(bad)}건 다름')

    def test_반올림으로_끝점을_넘는_훑기점(self):
        # 0.7000000000000001 + (1.8 - 0.7000000000000001) == 1.8000000000000003 — 원래 훑기는 왼쪽 변이
        # 1.8 인 상자 안이라고 본다. 딱 맞는 경계로 일찍 끝내면 이 답이 바뀐다.
        a, b, box = (0.1 * 7, 5), (1.8, 5), (1.8, 0, 10, 10)
        self.assertTrue(_ref_seg_in_box(a, b, box))
        self.assertTrue(self.mod.BreadboardRenderer._seg_in_box(a, b, box))

    def test_꺾임_정리가_원래와_같다(self):
        rng = random.Random(20261005)
        bad = []
        for _ in range(20000):          # `_ordered` 꼴 후보 — 반 행 통로, 차선 X 가 끝 열과 같을 때도
            A = (_coord(rng, 800), _coord(rng, 800))
            B = (_coord(rng, 800), _coord(rng, 800))
            y1 = A[1] + rng.choice((0, 7.5, -7.5, 22.5, .3))
            y2 = B[1] + rng.choice((0, 7.5, -7.5, 22.5, .3))
            X = rng.choice((A[0], B[0], A[0] + .3, _coord(rng, 800)))
            raw = [A, (A[0], y1), (X, y1), (X, y2), (B[0], y2), B]
            got, want = self.mod._clean(list(raw)), _ref_clean(self.mod, list(raw))
            if got != want or repr(got) != repr(want):
                bad.append(raw)
        grid = (0, .3, .6, 10, 10.4, 20)
        for _ in range(20000):          # 0.5px 미만 중복과 같은 축 합치기가 섞인 아무 경로
            raw = [(rng.choice(grid), rng.choice(grid)) for _ in range(rng.randint(1, 7))]
            got, want = self.mod._clean(list(raw)), _ref_clean(self.mod, list(raw))
            if got != want or repr(got) != repr(want):
                bad.append(raw)
        self.assertEqual(bad[:5], [], f'{len(bad)}건 다름')


def _ref_clean(mod, path):
    """꺾임 정리 전 엔진 `_clean` 본문 그대로(2026-10-05 `engine/router.py`)."""
    _axis = mod._axis
    out = []
    for p in path:
        if out and abs(out[-1][0] - p[0]) < .5 and abs(out[-1][1] - p[1]) < .5:
            continue
        if len(out) >= 2 and _axis(out[-2], out[-1]) and _axis(out[-2], out[-1]) == _axis(out[-1], p):
            out[-1] = p
            continue
        out.append(p)
    return out


def _ref_valid(mod, bb, path, others_pts, segs):
    """근처 선 고르기 전 엔진 `_valid` 본문 그대로(2026-10-05 배선기 속도 1차 뒤 `engine/router.py`)."""
    _axis, _on_seg = mod._axis, mod._on_seg
    for a, b in zip(path, path[1:]):
        sa = bb._strip(bb.sym(a[0], bb._row_of(a[1]))) if bb.hole_at(*a) else None
        sb = bb._strip(bb.sym(b[0], bb._row_of(b[1]))) if bb.hole_at(*b) else None
        if sa is not None and sa == sb:
            return False
        if _axis(a, b) is None:
            return False
    for box, _ch in bb.chip_label_boxes:
        if any(bb._seg_in_box(a, b, box) for a, b in zip(path, path[1:])):
            return False
    for c in path[1:-1]:
        h = bb.hole_at(*c)
        if h is not None and h in bb._leads:
            return False
    for q in (path[0], path[-1]):
        for _k, pts in segs:
            for a, b in zip(pts, pts[1:]):
                if _on_seg(q, a, b):
                    return False
    for q in others_pts:
        for a, b in zip(path, path[1:]):
            if _on_seg(q, a, b):
                return False
    for m in bb.marker_boxes:
        x0, y0, x1, y1 = m[0] - 1, m[1] - 1, m[2] + 1, m[3] + 1
        for a, b in zip(path, path[1:]):
            if (min(a[0], b[0]) < x1 and max(a[0], b[0]) > x0
                    and min(a[1], b[1]) < y1 and max(a[1], b[1]) > y0):
                return False
    for c in path[1:-1]:
        for _k, pts in segs:
            if (any(abs(c[0] - q[0]) < 1.5 and abs(c[1] - q[1]) < 1.5 for q in pts)
                    or any(_on_seg(c, a, b, margin=0) for a, b in zip(pts, pts[1:]))):
                return False
    for _k, pts in segs:
        for q in pts[1:-1]:
            if any(_on_seg(q, a, b, margin=0) for a, b in zip(path, path[1:])):
                return False
    for a, b in zip(path, path[1:]):
        ax = _axis(a, b)
        for _k, pts in segs:
            for c, d in zip(pts, pts[1:]):
                if _axis(c, d) != ax:
                    continue
                if ax == 'v' and abs(a[0] - c[0]) < 1.5:
                    lo = max(min(a[1], b[1]), min(c[1], d[1]))
                    hi = min(max(a[1], b[1]), max(c[1], d[1]))
                    if hi - lo > 2:
                        return False
                if ax == 'h' and abs(a[1] - c[1]) < 1.5:
                    lo = max(min(a[0], b[0]), min(c[0], d[0]))
                    hi = min(max(a[0], b[0]), max(c[0], d[0]))
                    if hi - lo > 2:
                        return False
    return True


def _stage(mod, board, circuit, plans, k):
    """`plans` 앞 k 가닥을 깐 superset 판과 k 번째 선의 `_valid` 입력 (판, 후보, others, segs) —
    `route_plan` 의 `board_`·`_routes` 머리와 같은 꼴이다."""
    wires = mod.place_wires(circuit, board.LAYOUT)
    chips = mod.place_chips(circuit, board.LAYOUT)
    bb = mod.BreadboardRenderer(None, board='v2')
    bb.enable_steps()
    circuit.fixed(bb, None, True, board.LAYOUT)
    for (_s, _e, kind, _f, _t, desc), (p, m) in zip(wires[:k], plans[:k]):
        bb.step_wire(p, kind, desc, marker_at=m)
    _s, _e, _kind, frm, to, _desc = wires[k]
    srcs, dsts = mod._end_holes(bb, chips, frm), mod._end_holes(bb, chips, to)
    segs = [(kk, pts) for kk, pts, _d in bb._segments]
    others = [q for _kk, pts, _d in bb._segments for q in (pts[0], pts[-1])]
    others += [(x, bb.r_y(r)) for (x, r), what in bb._leads.items()
               if '다리' in what or '애노드' in what or '캐소드' in what]
    chip_rows = tuple((ch['pin1_row'], len(ch['pins'])) for ch in bb.chips)
    cands = [p for _c, p in mod._ordered(bb, chip_rows, tuple(srcs), tuple(dsts), to[0] == 'LED')]
    return bb, cands, others, segs


class ValidSame(unittest.TestCase):
    """`_valid` 가 후보 근처 선만 봐도 답이 같다 — 배선기 속도 2차(`docs/plans/2026-10-05-배선기-속도-2차-설계.md`).
    판은 커밋된 λ=0 경로(`plans_lambda0.json`)를 단계 k 까지 깐 것, 후보는 k 번째 선의 `_ordered` 전부.
    경로를 새로 재지 않으므로 느린 그룹에 안 넣는다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _renders.engine()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')
        cls.snap = json.loads(SNAP.read_text(encoding='utf-8'))

    def _check(self, circuit, name):
        plans = [([tuple(q) for q in p], tuple(m)) for p, m in self.snap[name]]
        seen, bad = set(), []
        for k in range(0, len(plans), 5):
            bb, cands, others, segs = _stage(self.mod, self.board, circuit, plans, k)
            boxes = self.mod._seg_boxes(segs)
            for p in cands:
                want = _ref_valid(self.mod, bb, p, others, segs)
                seen.add(want)
                if self.mod._valid(bb, p, others, segs, boxes) != want:
                    bad.append((k, p, want))
        self.assertEqual(seen, {True, False})      # 맞댄 답이 한쪽뿐이면 헛돈 시험이다
        self.assertEqual(bad[:3], [], f'{len(bad)}건 다름')

    def test_MUX(self):
        self._check(self.board.MUX, 'mux')

    def test_DMUX(self):
        self._check(self.board.DMUX, 'dmux')


if __name__ == '__main__':
    unittest.main()
