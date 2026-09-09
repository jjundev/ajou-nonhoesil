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


if __name__ == '__main__':
    unittest.main()
