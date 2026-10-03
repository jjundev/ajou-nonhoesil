"""실험04 v2 시험판 — MUX/디코더 류가 R8 면제 없이 v2 규약(R7~R10)을 지키는지 잰다.

승인본(`보고서/실험04`)은 v1 그대로다. 이 파일은 `tests/fixtures/board_v2_e4/배치.py` 만 본다.
진리표는 넷을 `tests/_gate_sim.py` 로 돌려 맞댄다 — 시험판은 교안 핀 번호를 일부러 바꿔서
netlist 핀 줄 대조를 쓸 수 없다.
"""
import importlib.util
import itertools
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tests._gate_sim import value_of

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Trial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board_file(TRIAL, 'board_v2_e4')
        cls.tmp = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def assert_v2_layout(self, bb):
        self.assertEqual({ch['block'] for ch in bb.chips}, {'left'})
        self.assertEqual(bb.cross_side_wires(), [])
        self.assertEqual(bb._block_role_violations(), [])
        worst = max(s['count'] for s in bb.side_leads())
        self.assertLessEqual(worst, self.mod.SIDE_LEAD_MAX)


class DmuxFinal(_Trial):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bb = cls.board.build_trial_dmux(os.path.join(cls.tmp, 'dmux.png'))

    def test_v2_규약을_지킨다(self):
        self.assert_v2_layout(self.bb)

    def test_진리표_전_행(self):
        nets = self.bb.nets()
        for d, s1, s0 in itertools.product((0, 1), repeat=3):
            ins = {'D': d, 'S1': s1, 'S0': s0}
            for i in range(4):
                want = 1 if d and (s1 * 2 + s0) == i else 0
                got = value_of(nets, f'LED Y{i} 애노드', ins)
                self.assertEqual(got, want, f'Y{i} @ {ins}')


class MuxFinal(_Trial):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bb = cls.board.build_trial_mux(os.path.join(cls.tmp, 'mux.png'))

    def test_v2_규약을_지킨다(self):
        self.assert_v2_layout(self.bb)

    def test_진리표_전_행(self):
        nets = self.bb.nets()
        names = ('E', 'S1', 'S0', 'D0', 'D1', 'D2', 'D3')
        for vals in itertools.product((0, 1), repeat=7):
            ins = dict(zip(names, vals))
            sel = ins['S1'] * 2 + ins['S0']
            want = 1 if ins['E'] == 0 and ins[f'D{sel}'] else 0
            self.assertEqual(value_of(nets, 'LED Y 애노드', ins), want, str(ins))

    def test_중계는_n_c_셋과_미사용_입력_하나다(self):
        relay = [w for w in self.bb.wiring()['wires'] if '중계' in w['desc']]
        self.assertEqual(len(relay), 4, [w['desc'] for w in relay])


def _marker_problems(bb):
    """번호 원이 가리는 것 — 꽂힌 홀(끝점·부품 다리), 다른 번호 원, 자기 것 말고 다른 배선.
    번호 원은 자기 배선 위에 앉으므로 상자를 지나는 배선이 **둘 이상**이면 남의 배선을 덮는다.
    2026-10-03 사용자: "번호 표시가 배선을 가리고, 배선 끝이 어느 칸에 꽂히는지 모른다"."""
    out = []
    boxes = bb.marker_boxes
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        for (hx, hr), what in bb._leads.items():
            if x0 - 1 <= hx <= x1 + 1 and y0 - 1 <= bb.r_y(hr) <= y1 + 1:
                out.append(f'번호 원 {(x0 + 8, y0 + 8)} 이 꽂힌 홀 {bb.addr(hx, bb.r_y(hr))} 을 가린다')
        for b in boxes[i + 1:]:
            if not (x1 <= b[0] or b[2] <= x0 or y1 <= b[1] or b[3] <= y0):
                out.append(f'번호 원 {(x0 + 8, y0 + 8)} 과 {(b[0] + 8, b[1] + 8)} 이 겹친다')
        L = bb.cols[bb.chips[0]['block']] if bb.chips else None
        for ch in bb.chips:
            cx0, cx1 = L['e'] + 4, L['f'] - 4
            cy0, cy1 = bb.r_y(ch['pin1_row']) - 10, bb.r_y(ch['pin1_row'] + 6) + 10
            if not (x1 <= cx0 or cx1 <= x0 or y1 <= cy0 or cy1 <= y0):
                out.append(f"번호 원 {(x0 + 8, y0 + 8)} 이 칩 {ch['label']}({ch['pin1_row']}행) 몸통을 가린다")
        crossing = []
        for _k, pts, desc in bb._segments:
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                n = int(max(abs(bx - ax), abs(by - ay)) / 2) + 1
                if any(x0 < ax + (bx - ax) * t / n < x1 and y0 < ay + (by - ay) * t / n < y1
                       for t in range(n + 1)):
                    crossing.append(desc)
                    break
        if len(crossing) > 1:
            out.append(f'번호 원 {(x0 + 8, y0 + 8)} 아래 배선 {len(crossing)}가닥: {crossing}')
    return out


def _wires_over_holes(bb):
    """신호선(`sig`·`mid`)이 끝점 말고 지나가는 홀. 검정 선이 검정 홀 위를 지나가면 거기
    꽂힌 것인지 지나가는 것인지 안 보인다(2026-10-03 사용자). 전원·GND·입력 점퍼(엔진이
    그린다)는 뺀다."""
    input_segs = {inp['seg'] for inp in bb.inputs}
    out = []
    for i, (kind, pts, desc) in enumerate(bb._segments):
        if kind not in ('sig', 'mid') or i in input_segs:
            continue
        ends = {bb.hole_at(*pts[0]), bb.hole_at(*pts[-1])}
        seen = set()
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / 2))
            for t in range(n + 1):
                h = bb.hole_at(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n)
                if h is not None and h not in ends and h not in seen:
                    seen.add(h)
        if seen:
            out.append(f'{desc}: 홀 {len(seen)}개 위를 지난다')
    return out


def _needless_body_crossings(bb):
    """양 끝이 칩 기둥(e~f)의 같은 쪽인데 칩 몸통을 가로지르는 신호선 — 칩 이름·핀 번호를
    덮고 쓸데없이 돌아간다. 양 끝이 다른 쪽(칩 안 이어 가기, a쪽 출력 → LED)이면 한 번은
    건너야 하므로 본다."""
    L = bb.cols['left']
    bodies = [(bb.r_y(ch['pin1_row']) - 10, bb.r_y(ch['pin1_row'] + 6) + 10) for ch in bb.chips]
    out = []
    for kind, pts, desc in bb._segments:
        if kind not in ('sig', 'mid'):
            continue
        if (pts[0][0] < L['e']) != (pts[-1][0] < L['e']):
            continue
        for a, b in zip(pts, pts[1:]):
            if (abs(a[1] - b[1]) < .5 and min(a[0], b[0]) < L['e'] and max(a[0], b[0]) > L['f']
                    and any(y0 <= a[1] <= y1 for y0, y1 in bodies)):
                out.append(desc)
                break
    return out


class WiresOverHoles(_Trial):
    def test_양_끝이_같은_쪽인_신호선은_칩_몸통을_건너지_않는다(self):
        bad = {}
        for name, fn in self.board.FINALS:
            got = _needless_body_crossings(fn(os.path.join(self.tmp, name)))
            if got:
                bad[name] = got
        self.assertEqual(bad, {})

    def test_신호선은_끝점_말고_홀_위를_지나지_않는다(self):
        bad = {}
        for name, fn in self.board.FINALS:
            got = _wires_over_holes(fn(os.path.join(self.tmp, name)))
            if got:
                bad[name] = got
        self.assertEqual(bad, {}, '\n'.join(f'{k}: {len(v)}가닥 — {v[:3]}' for k, v in bad.items()))


class Markers(_Trial):
    """번호 원이 배선 끝과 다른 배선을 가리지 않는다 — 완성본과 단계 그림 전부."""

    def test_완성본과_단계_그림의_번호_원이_아무것도_가리지_않는다(self):
        bad = {}
        base = None
        for name, fn, stage in self.board.BOARDS:
            if name in self.board.RESTART:
                base = None
            bb = fn(os.path.join(self.tmp, name), None, stage=stage, baseline=base)
            base = bb.snapshot()
            if _marker_problems(bb):
                bad[name] = _marker_problems(bb)
        for name, fn in self.board.FINALS:
            bb = fn(os.path.join(self.tmp, name))
            if _marker_problems(bb):
                bad[name] = _marker_problems(bb)
        self.assertEqual(bad, {}, '\n'.join(f'{k}: {len(v)}건 — {v[:3]}' for k, v in bad.items()))


def _nand(*v):
    return 0 if all(v) else 1


# 단계마다 LED 가 보여야 할 함수 — 학생이 그 단계에서 확인하는 것이다. 임시 급전선이 엉뚱한
# 핀에 꽂히면 R1~R10 은 통과해도 여기서 걸린다.
_MUX_STAGE_LEDS = {
    1: {'L1': lambda i: 1 - i['E']},
    2: {'L1': lambda i: 1 - i['E'], 'L3': lambda i: 1 - i['S1']},
    3: {'L1': lambda i: 1 - i['E'], 'L3': lambda i: 1 - i['S1'], 'L2': lambda i: 1 - i['S0']},
}
_T = {
    'L1': lambda i: _nand(1 - i['E'], 1 - i['S1'], 1 - i['S0'], i['D0']),
    'L2': lambda i: _nand(1 - i['E'], 1 - i['S1'], i['S0'], i['D1']),
    'L3': lambda i: _nand(1 - i['E'], i['S1'], 1 - i['S0'], i['D2']),
    'L4': lambda i: _nand(1 - i['E'], i['S1'], i['S0'], i['D3']),
}
for _s, _tags in ((4, 'L1'), (5, 'L1 L2'), (6, 'L1 L2 L3'), (7, 'L1 L2 L3 L4')):
    _MUX_STAGE_LEDS[_s] = {t: _T[t] for t in _tags.split()}
_MUX_STAGE_LEDS[8] = {'Y': lambda i: 1 if i['E'] == 0 and i[f"D{i['S1'] * 2 + i['S0']}"] else 0}

_Y = {f'Y{n}': (lambda n: lambda i: 1 if i['D'] and i['S1'] * 2 + i['S0'] == n else 0)(n)
      for n in range(4)}
_DMUX_STAGE_LEDS = {1: ('Y3',), 2: ('Y3', 'Y1'), 3: ('Y3', 'Y1', 'Y2'), 4: ('Y3', 'Y1', 'Y2', 'Y0')}


class StageTruth(_Trial):
    """단계 그림마다 그 단계에 급전된 LED 가 맞는 함수를 보이는가 — 모든 입력 조합."""

    def check(self, bb, leds, names, stage):
        nets = bb.nets()
        for vals in itertools.product((0, 1), repeat=len(names)):
            ins = dict(zip(names, vals))
            for tag, f in leds.items():
                self.assertEqual(value_of(nets, f'LED {tag} 애노드', ins), f(ins),
                                 f'{stage}단계 {tag} @ {ins}')

    def test_MUX_단계마다_LED_가_그_노드를_보인다(self):
        names = ('E', 'S1', 'S0', 'D0', 'D1', 'D2', 'D3')
        for stage, leds in _MUX_STAGE_LEDS.items():
            bb = self.board.build_trial_mux(os.path.join(self.tmp, f'm{stage}.png'), stage=stage)
            self.check(bb, leds, names, stage)

    def test_DMUX_단계마다_LED_가_그_노드를_보인다(self):
        for stage, tags in _DMUX_STAGE_LEDS.items():
            bb = self.board.build_trial_dmux(os.path.join(self.tmp, f'd{stage}.png'), stage=stage)
            self.check(bb, {t: _Y[t] for t in tags}, ('D', 'S1', 'S0'), stage)


def _walk(board):
    """사슬 순서대로 (이름, 빌더, 단계, 그릴지) 를 낸다. 막힌 보드 뒤는 기준선이 없으므로
    다음 회로의 첫 보드(`RESTART`, `fresh_board` 로 기준선을 끊는 자리)까지 건너뛴다 —
    MUX 가 막혀도 DMUX 는 잰다."""
    skipping = False
    for name, fn, stage in board.BOARDS:
        if name in board.RESTART:
            skipping = False
        yield name, fn, stage, not skipping
        if name in board.KNOWN_BLOCKERS:
            skipping = True


class Chain(_Trial):
    """단계 사슬 — 막힘은 `KNOWN_BLOCKERS` 로, 새 신호선 수는 `MEASURED_NEW_SIGNAL` 로 고정한다."""

    def test_단계_보드마다_R10_이_통과하거나_기록된_막힘이다(self):
        base = None
        for name, fn, stage, draw in _walk(self.board):
            if name in self.board.RESTART:
                base = None
            if not draw:
                continue
            path = os.path.join(self.tmp, name)
            want = self.board.KNOWN_BLOCKERS.get(name)
            if want:
                with self.assertRaisesRegex(AssertionError, want):
                    fn(path, None, stage=stage, baseline=base)
                continue
            bb = fn(path, None, stage=stage, baseline=base)
            self.assertEqual(bb._block_role_violations(), [], name)
            self.assertEqual(len(bb.new_signal), self.board.MEASURED_NEW_SIGNAL[name], name)
            base = bb.snapshot()

    def test_측정표가_그린_보드를_빠짐없이_덮는다(self):
        drawn = [n for n, _f, _s, draw in _walk(self.board)
                 if draw and n not in self.board.KNOWN_BLOCKERS]
        self.assertEqual(list(self.board.MEASURED_NEW_SIGNAL), drawn)


if __name__ == '__main__':
    unittest.main()
