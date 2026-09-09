"""결선도가 **무엇과 무엇을 잇는가**를 렌더러가 아는지 검사한다.

2026-09-09 에 발견: 복합 회로의 `우 a10 → 우 b10` 점퍼는 같은 5홀 스트립
안에서 끝나 전기적으로 아무 일도 하지 않았고, 74HC32 pin 1 은 뜬 채였다.
실험02 Rn 은 1kΩ 아랫다리가 pin 5 행에 앉아 +5V 와 GND 를 직결시켰다.
둘 다 `verify()` R1~R4 와 시험 128건을 통과한 상태로 커밋돼 있었다 — R1~R4
는 전부 기하라서, 배선이 무엇을 잇는지는 아무도 보지 않았다.

브레드보드는 홀이 아니라 **스트립** 단위로 이어진다. 단자대는 한 행의 a~e
가 한 스트립이고 f~j 가 또 한 스트립, 전원 레일은 열 하나가 통째로 한
스트립이다. 그래서 홀 점유표(`_leads`)로는 이 층위가 안 보인다.
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


def _render(mod, fn):
    """빌더를 임시 파일로 렌더하고 렌더러 객체를 돌려준다."""
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


def _net_of(bb, label):
    for net in bb.nets():
        if label in net['labels']:
            return net
    raise AssertionError(f'{label} 이 어느 넷에도 없다')


class NetModel(unittest.TestCase):
    """스트립을 옳게 묶는가. 합성 보드에 몇 줄만 그리고 `nets()` 만 부른다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    def test_같은_행_a부터_e_는_한_스트립이다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        bb.step_wire([(c['d'], bb.r_y(10)), (c['d'], bb.r_y(13))], 'sig', '시험')
        self.assertIn('74HC08#10 pin 4', _net_of(bb, '74HC08#10 pin 1')['labels'])

    def test_칩_건너편_f부터_j_는_다른_스트립이다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        self.assertNotIn('74HC08#10 pin 14', _net_of(bb, '74HC08#10 pin 1')['labels'])

    def test_레일쌍은_브리지_전에는_다른_넷이다(self):
        bb = self.board()
        c = bb.cols['left']
        self.assertNotIn('좌 중앙GND레일', _net_of(bb, '좌 GND레일')['labels'])
        bb.bridge_rails(c['gnd'], c['mid_gnd'], 29, kind='gnd')
        self.assertIn('좌 중앙GND레일', _net_of(bb, '좌 GND레일')['labels'])

    def test_입력_점퍼의_레일_끝은_가상_노드다(self):
        """입력은 지금 GND 레일에 꽂혀 있지만(=0 자리) 1 을 줄 때 그 끝만
        VCC 로 옮긴다. 레일 연결로 세면 입력 A·B·C 가 GND 와 한 넷이 되어
        'pin 1 이 A 에 물렸는가' 를 물을 수 없다."""
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        self.mod._input_jumper(bb, c, 10, 'A', '74HC08 pin 1')
        net = _net_of(bb, '입력 A')
        self.assertIn('74HC08#10 pin 1', net['labels'])
        self.assertNotIn('좌 GND레일', net['labels'])


class CircuitNets(unittest.TestCase):
    """회로마다 넷리스트가 약속한 대로 물렸는가. 정답의 권위는
    `보고서/실험01/결선도/netlist.md` 와 실험02 넷리스트다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_복합_74HC32_pin_1_이_입력_A_와_한_넷이다(self):
        """2026-09-09 까지 `우 a10 → 우 b10` 은 같은 스트립 안에서 끝나 아무
        일도 하지 않았고, a10 으로 A 를 가져오는 선이 없어 pin 1 이 떴다.
        netlist C5: `U9 pin 1 ← 입력 A`."""
        bb = _render(self.mod, self.mod.build_e1_comb_s3)
        self.assertIn('입력 A', _net_of(bb, '74HC32#10 pin 1')['labels'])

    def test_복합_Z_와_X_는_각자_LED_를_달고_있다(self):
        """`X ≡ Z` 라 두 LED 가 언제나 같이 켜져야 한다 — 공짜 자체 검산이다.
        서로 다른 넷에서 각각 켜져야 의미가 있다."""
        bb = _render(self.mod, self.mod.build_e1_comb_s3)
        z = _net_of(bb, '74HC04#7 pin 4')['labels']
        self.assertIn('LED Z 애노드', z)
        self.assertIn('74HC32#10 pin 2', z)
        self.assertIn('LED X 애노드', _net_of(bb, '74HC32#10 pin 3')['labels'])
        self.assertNotIn('LED X 애노드', z)

    def test_Rn_은_전원이_단락되지_않는다(self):
        """2026-09-09 까지 1kΩ 아랫다리가 pin 5 행(14행)에 앉았다. 그 스트립에
        `R1 반대쪽 -> +5V` 점퍼와 pin 5 접지선이 함께 꽂혀 +5V 가 GND 로
        직결됐다 — 그림대로 꽂으면 전원장치가 나간다."""
        bb = _render(self.mod, self.mod.build_e2_rn)
        for net in bb.nets():
            self.assertNotEqual({'vcc', 'gnd'}, net['rails'], sorted(net['labels']))

    def test_Rn_과_Rp_의_저항은_pin_2_에만_물린다(self):
        """부품 다리가 칩 행에 앉으면 그 핀이 저항 반대쪽 전원에 끌려간다.
        칩은 10~16행을 다 쓰므로 저항은 칩 행 **밖**으로 나가야 한다."""
        for name in ('build_e2_rn', 'build_e2_rp'):
            with self.subTest(회로=name):
                bb = _render(self.mod, getattr(self.mod, name))
                chip = bb.chips[0]
                r = bb.resistors[0]
                pin_strips = {bb._strip(s) for s in chip['pins'].values()}
                self.assertEqual(bb._strip(chip['pins'][2]), bb._strip(r['bottom']))
                self.assertNotIn(bb._strip(r['top']), pin_strips)

    def test_Rn_은_넷리스트대로_물린다(self):
        """netlist C3: R1 한쪽 → VCC, 다른 쪽 → pin 2. 미사용 입력 pin 5 → GND."""
        bb = _render(self.mod, self.mod.build_e2_rn)
        self.assertIn('저항1(1kΩ) 아랫다리', _net_of(bb, '74HC04#10 pin 2')['labels'])
        self.assertEqual({'vcc'}, _net_of(bb, '저항1(1kΩ) 윗다리')['rails'])
        self.assertEqual({'gnd'}, _net_of(bb, '74HC04#10 pin 5')['rails'])


class R5(unittest.TestCase):
    """넷 검사 자체. 합성 보드에 몇 줄만 그리고 `verify()` 를 부른다 —
    파일을 쓰지 않아 빠르고, 어느 갈래가 잡았는지 메시지로 확인한다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def board(self):
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        return bb

    def test_같은_스트립_안에서_끝나는_점퍼는_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(20)), (c['d'], bb.r_y(20))], 'sig', '갈래')
        with self.assertRaisesRegex(AssertionError, '같은 스트립'):
            bb.verify()

    def test_옆_행으로_가는_점퍼는_통과한다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['c'], bb.r_y(20)), (c['c'], bb.r_y(21))], 'sig', '갈래')
        bb.verify()

    def test_전원_두_레일이_한_넷이면_막힌다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.step_wire([(c['vcc'], bb.r_y(21)), (c['gnd'], bb.r_y(21))], 'vcc', '단락')
        with self.assertRaisesRegex(AssertionError, '단락'):
            bb.verify()

    def test_아무_데도_안_물린_칩_핀은_막힌다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        with self.assertRaisesRegex(AssertionError, '뜬 핀'):
            bb.verify()

    def test_미사용_출력은_뜬_핀이_아니다(self):
        bb = self.board()
        bb.draw_chip('74HC08', 10)
        bb.mark_unused_outputs([8], 10, chip='74HC08')
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertIn('74HC08#10 pin 1 이', str(e.exception))
        self.assertNotIn('74HC08#10 pin 8 이', str(e.exception))

    def test_계측기가_무는_핀은_뜬_핀이_아니다(self):
        """실험02 인버터는 pin 1 에 함수발생기를, pin 2 에 프로브를 문다 —
        점퍼가 없다고 뜬 것이 아니다."""
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC04', 10)
        bb.instrument(c['a'], 10, '함수발생기', '체인 입력')
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertNotIn('74HC04#10 pin 1 이', str(e.exception))
        self.assertIn('74HC04#10 pin 2 이', str(e.exception))

    def test_덜_그린_그림은_뜬_핀만_봐준다(self):
        bb = self.board()
        c = bb.cols['left']
        bb.draw_chip('74HC08', 10)
        bb.partial = True
        bb.verify()
        bb.step_wire([(c['c'], bb.r_y(20)), (c['d'], bb.r_y(20))], 'sig', '갈래')
        with self.assertRaisesRegex(AssertionError, '같은 스트립'):
            bb.verify()

    def test_양끝이_빈_스트립인_부품_다리는_막힌다(self):
        """뜬 핀만 보던 시절, 허공에 걸친 저항은 어떤 규칙도 안 봤다. 그림대로
        꽂으면 부하가 안 달린 채로 V_OL 을 재게 되고 **실험실에서는 아무 이상이
        없어 보인다** — 눈으로도 계측으로도 안 잡히는 자리다."""
        bb = self.board()
        c = bb.cols['left']
        bb.draw_resistor(c['c'], bb.r_y(21), bb.r_y(24), label="1kΩ")
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertIn('저항1(1kΩ) 윗다리 가 아무 데도 안 물렸다 — 뜬 다리', str(e.exception))
        self.assertIn('저항1(1kΩ) 아랫다리 가 아무 데도 안 물렸다 — 뜬 다리', str(e.exception))

        # 아랫다리를 레일에 물리면 그 다리는 더 이상 뜨지 않는다
        bb.step_wire([(c['a'], bb.r_y(24)), (c['gnd'], bb.r_y(24))], 'gnd', '아랫다리 -> GND')
        with self.assertRaises(AssertionError) as e:
            bb.verify()
        self.assertNotIn('아랫다리 가', str(e.exception))
        self.assertIn('윗다리 가', str(e.exception))

        # 윗다리까지 물리면 통과한다 — 짝이 붙은 다리는 넷에 라벨이 둘 이상이다
        bb.step_wire([(c['a'], bb.r_y(21)), (c['gnd'], bb.r_y(21))], 'gnd', '윗다리 -> GND')
        bb.verify()

    def test_입력_점퍼가_꽂힌_스트립이_VCC_에_물리면_단락이다(self):
        """입력 점퍼의 레일 끝은 라벨 판정에서만 가상 노드다. 그림에 그려진
        배선은 GND 레일에 실제로 꽂혀 있으므로, 그 스트립이 VCC 에도 물리면
        그림 그대로가 GND↔VCC 직결이다 — 치환한 넷에서는 안 보인다."""
        bb = self.board()
        c = bb.cols['left']
        self.mod._input_jumper(bb, c, 20, 'A', '어딘가')
        # 같은 스트립(좌 a~e 20행)에서 VCC 로. 가로선이 입력선 끝점 b20 위를
        # 지나지 않도록 d 열에서 세로로 빠져나간 뒤 17행에서 레일로 간다
        bb.step_wire([(c['d'], bb.r_y(20)), (c['d'], bb.r_y(17)), (c['vcc'], bb.r_y(17))],
                     'vcc', '입력 스트립 -> +5V')
        with self.assertRaisesRegex(AssertionError, '단락'):
            bb.verify()

    def test_모든_회로가_넷_검사를_통과한다(self):
        """`export()` 안에서 `verify()` 가 돈다 — 렌더가 되면 통과한 것이다."""
        import inspect
        builders = {n: f for n, f in vars(self.mod).items()
                    if n.startswith('build_') and not n.endswith('_all')
                    and inspect.isfunction(f)}
        self.assertEqual(len(builders), 13)
        for name, fn in sorted(builders.items()):
            with self.subTest(회로=name):
                _render(self.mod, fn)


if __name__ == '__main__':
    unittest.main()
