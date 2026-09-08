"""결선도가 **그림대로 꽂히는가**를 렌더러가 내보내기 전에 증명하는지 검사한다.

2026-09-07 에 발견: 입력 A·B·C 가 보드 밖 x=95 허공에서 출발하고 있었다.
`addr()` 이 그 자리에 '보드밖(입력)' 이라는 이름을 붙여 주었고, `verify()` 는
docstring 과 달리 레일 끝점의 빈 행만 봤다. 그림도 순서표도 멀쩡해 보였다 —
따라 그리던 사람이 왼쪽 끝을 어디에 꽂아야 할지 몰라서 걸렸다.

합성 보드에 배선 한두 줄을 그리고 `verify()` 만 부른다. 파일을 쓰지 않아
빠르고, 어느 규칙이 잡았는지 메시지로 확인한다.
"""
import importlib.util
import inspect
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


class PhysicalRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    # ---- R1. 모든 끝점은 홀이다 ----

    def test_허공에서_출발한_배선은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(95, bb.r_y(10)), (c['b'], bb.r_y(10))], 'sig', '입력 A')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다.*보드밖'):
            bb.verify()

    def test_레일_빈_행에_꽂은_끝점은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['gnd'], bb.r_y(14)), (c['b'], bb.r_y(14))], 'sig', '입력 C')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다.*GND레일14행'):
            bb.verify()

    def test_전원잭은_보드_밖이어도_된다(self):
        bb = self.board()
        bb.connect_jacks()
        bb.verify()

    def test_홀_사이_골에_앉은_끝점은_홀이_아니다(self):
        # 열 피치가 16px 인데 허용치가 9px 였다 — 인접 열 사이에 '홀 아님' 이 없었다
        bb = self.board()
        c = bb.cols['left']
        self.assertEqual(bb.hole_at(c['c'], bb.r_y(10)), (c['c'], 10))
        self.assertIsNone(bb.hole_at(c['c'] + 8, bb.r_y(10)))
        self.assertIsNone(bb.hole_at(c['c'], bb.r_y(10) + 8))

    def test_잭이_아닌_보드_위쪽_허공은_면제되지_않는다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], 239), (c['c'], bb.r_y(10))], 'sig', '위에서 내려온 선')
        with self.assertRaisesRegex(AssertionError, '홀이 아니다'):
            bb.verify()

    # ---- R2. 한 홀에 리드 하나 ----

    def test_한_홀에_배선_둘은_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(12)), (c['c'], bb.r_y(13))], 'mid', '1단 -> 2단')
        bb.step_wire([(c['c'], bb.r_y(12)), (c['a'], bb.r_y(12))], 'mid', '갈래')
        with self.assertRaisesRegex(AssertionError, '한 홀에 리드 둘.*좌 c12'):
            bb.verify()

    def test_레일_홀이_차면_가까운_빈_홀로_옮긴다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.lead(c['gnd'], bb.r_y(7), '먼저 꽂힌 것')
        # 8행은 빈 행이고 7행은 찼다 -> 9행
        self.assertEqual(bb.free_rail_row(8, c['gnd']), 9)
        self.assertEqual(bb.free_rail_row(10, c['gnd']), 10)
        # 두 열을 같이 주면 둘 다 비어야 한다
        bb.lead(c['mid_gnd'], bb.r_y(31), '브리지 끝')
        self.assertEqual(bb.free_rail_row(31, c['mid_gnd'], c['mid_vcc']), 30)

    # ---- R4. 서로 다른 배선이 같은 축 위에 포개지지 않는다 ----

    def test_다른_색_배선이_한_줄에_포개지면_막힌다(self):
        # 2026-09-07 실험 1-1 의 원형: 입력 C 의 세로 구간이 초록 중간단 선에 덮여
        # pin 3 이 pin 5 로 들어가는 다른 회로로 읽혔다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(7)), (c['a'], bb.r_y(14))], 'sig', '입력 C')
        bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], 'mid', '중간단 갈래')
        # `.` 은 줄바꿈을 못 넘는다 — 메시지가 '포개졌다:\n  세로 …' 꼴이라 \s+ 로 잇는다
        with self.assertRaisesRegex(AssertionError, '포개졌다:\\s+세로'):
            bb.verify()

    def test_같은_색의_짧은_갈래_밑동은_봐준다(self):
        # 옛 복합 회로의 B 갈래: a19 에 꽂은 두 번째 점퍼가 입력선 위를 27px 되짚어
        # 여백(x=212)으로 나갔다. 두 홀 폭 안의 같은 색 포개짐은 갈래 밑동이라 검사는
        # 봐준다 (그림으로는 밑동이 안 보여 2026-09-08 에 실제 회로에서는 걷어냈다).
        # 끝점은 홀이어야 하므로(R1) 폴리라인을 a5 에서 끝낸다
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['gnd'], bb.r_y(19)), (c['b'], bb.r_y(19))], 'sig', '입력 B')
        bb.step_wire([(c['a'], bb.r_y(19)), (212, bb.r_y(19)), (212, bb.r_y(5)), (c['a'], bb.r_y(5))],
                     'sig', '갈래')
        bb.verify()

    def test_경고_모드는_던지지_않고_기록한다(self):
        bb = self.board()
        bb.overlap_policy = 'warn'
        c = bb.cols['left']
        bb.step_wire([(c['a'], bb.r_y(7)), (c['a'], bb.r_y(14))], 'sig', '입력 C')
        bb.step_wire([(c['a'], bb.r_y(12)), (c['a'], bb.r_y(19))], 'mid', '중간단 갈래')
        bb.verify()
        self.assertEqual(len(bb.overlap_warnings), 1)

    def test_경고_목록은_이번_verify_의_결과로_덮인다(self):
        # ad06489 가 고친 시나리오: 포개짐이 사라진 뒤에도 옛 경고가 남았다
        bb = self.board()
        bb.overlap_policy = 'warn'
        bb.overlap_warnings = ['옛 경고']
        bb.connect_jacks()
        bb.verify()
        self.assertEqual(bb.overlap_warnings, [])

    # ---- R2. 부품 다리와 칩 핀도 홀을 차지한다 ----

    def test_칩_핀_홀에_배선을_꽂으면_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        bb.step_wire([(c['f'], bb.r_y(10)), (c['mid_vcc'], bb.r_y(10))], 'vcc', 'pin 14')
        with self.assertRaisesRegex(AssertionError, '한 홀에 리드 둘.*74HC08 pin 14'):
            bb.verify()

    def test_LED_사슬은_다리마다_다른_홀을_쓴다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(15)), (c['c'], bb.r_y(24))], 'sig', '출력 -> L2')
        bb.led_chain(c['c'], 24, 'L2', '최종 출력')
        bb.verify()
        self.assertEqual(bb._leads[(c['c'], 24)], '신호 배선 · 출력 -> L2')
        self.assertEqual(bb._leads[(c['d'], 24)], 'L2 LED 애노드')
        self.assertEqual(bb._leads[(c['d'], 25)], 'L2 LED 캐소드')
        self.assertEqual(bb._leads[(c['e'], 25)], '330Ω 윗다리')
        self.assertEqual(bb._leads[(c['e'], 27)], '330Ω 아랫다리')
        # GND 점퍼는 레일 쪽 끝 홀(c27)에서. LED 열(d27)에서 뽑으면 레일로 가는 길에
        # 다른 다리 위를 지나진 않지만, 레일 쪽 끝이 항상 아무것도 안 넘는 자리다
        self.assertIn((c['c'], 27), bb._leads)
        self.assertNotIn((c['d'], 27), bb._leads)

    def test_오른쪽_끝_열의_LED_사슬은_왼쪽으로_자란다(self):
        bb = self.board()
        c = bb.cols['right']
        bb.step_wire([(c['d'], bb.r_y(12)), (c['d'], bb.r_y(22))], 'sig', 'pin 3 -> X')
        bb.led_chain(c['d'], 22, 'X', 'X 출력', block='right')
        bb.verify()
        self.assertEqual(bb._leads[(c['c'], 22)], 'X LED 애노드')
        self.assertEqual(bb._leads[(c['b'], 23)], '330Ω 윗다리')
        # 왼쪽으로 자란 사슬의 GND 점퍼는 저항 너머(a25)에서 — c25 나 d25 에서 뽑으면
        # 레일(542, 왼쪽)로 가는 가로선이 저항 아랫다리 b25 위를 지난다
        self.assertIn((c['a'], 25), bb._leads)
        self.assertNotIn((c['c'], 25), bb._leads)


def _render(mod, fn):
    """빌더를 임시 파일로 렌더하고 렌더러 객체를 돌려준다. export() 안에서 verify() 가 돈다."""
    captured = {}
    orig = mod.BreadboardRenderer.export

    def spy(self_, *a, **k):
        captured['bb'] = self_
        return orig(self_, *a, **k)

    mod.BreadboardRenderer.export = spy
    try:
        with tempfile.TemporaryDirectory() as d:
            fn(os.path.join(d, 'x.png'))
    finally:
        mod.BreadboardRenderer.export = orig
    return captured['bb']


class AllCircuits(unittest.TestCase):
    """12장 전부가 그림대로 꽂힌다. 2026-09-08 까지 복합 회로만 포개짐 경고 둘을
    안고 경고 모드였다 — 초록 Z 선을 11행으로 옮겨 0 이 됐고 엄격 모드다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def builders(self):
        return {n: f for n, f in vars(self.mod).items()
                if n.startswith('build_') and not n.endswith('_all') and inspect.isfunction(f)}

    def test_모든_회로가_그림대로_꽂힌다(self):
        for name, fn in sorted(self.builders().items()):
            with self.subTest(회로=name):
                bb = _render(self.mod, fn)
                self.assertEqual(bb._not_holes, [])
                self.assertEqual(bb._double, [])

    def test_모든_회로가_엄격_모드로_포개짐_없이_통과한다(self):
        for name, fn in sorted(self.builders().items()):
            with self.subTest(회로=name):
                bb = _render(self.mod, fn)
                self.assertEqual(bb.overlap_policy, 'strict', f'{name}: 경고 모드로 도는 회로가 없어야 한다')
                self.assertEqual(bb.overlap_warnings, [])


if __name__ == '__main__':
    unittest.main()
