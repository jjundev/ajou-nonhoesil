"""게이트 모의기 — 렌더러 넷에서 진리표를 돌린다. 합성 넷만 쓴다(렌더러 불필요)."""
import unittest

from tests._gate_sim import SimError, value_of


def net(*labels, rails=()):
    return {'labels': set(labels), 'rails': set(rails)}


class GateSim(unittest.TestCase):
    def test_인버터는_입력을_뒤집는다(self):
        nets = [net('입력 A', '74HC04#5 pin 1'), net('74HC04#5 pin 2', 'LED X 애노드')]
        self.assertEqual(value_of(nets, 'LED X 애노드', {'A': 0}), 1)
        self.assertEqual(value_of(nets, 'LED X 애노드', {'A': 1}), 0)

    def test_4입력_NAND(self):
        nets = [net('입력 A', '74HC20#17 pin 1'), net('입력 B', '74HC20#17 pin 2'),
                net('74HC20#17 pin 4', '74HC20#17 pin 5', rails=('vcc',)),
                net('74HC20#17 pin 6', 'LED Y 애노드')]
        self.assertEqual(value_of(nets, 'LED Y 애노드', {'A': 1, 'B': 1}), 0)
        self.assertEqual(value_of(nets, 'LED Y 애노드', {'A': 1, 'B': 0}), 1)

    def test_3입력_AND_게이트1은_pin_13_을_입력으로_쓴다(self):
        nets = [net('입력 A', '74HC11#17 pin 1', '74HC11#17 pin 2', '74HC11#17 pin 13'),
                net('74HC11#17 pin 12', 'LED Y0 애노드')]
        self.assertEqual(value_of(nets, 'LED Y0 애노드', {'A': 1}), 1)
        self.assertEqual(value_of(nets, 'LED Y0 애노드', {'A': 0}), 0)

    def test_게이트를_사슬로_잇는다(self):
        nets = [net('입력 A', '74HC04#5 pin 1'),
                net('74HC04#5 pin 2', '74HC04#5 pin 3'),
                net('74HC04#5 pin 4', 'LED Z 애노드')]
        self.assertEqual(value_of(nets, 'LED Z 애노드', {'A': 1}), 1)

    def test_뜬_입력이면_멈춘다(self):
        nets = [net('74HC04#5 pin 1'), net('74HC04#5 pin 2', 'LED X 애노드')]
        with self.assertRaisesRegex(SimError, '뜬'):
            value_of(nets, 'LED X 애노드', {})

    def test_관측과_무관한_게이트의_뜬_입력은_무시한다(self):
        nets = [net('입력 A', '74HC20#41 pin 1'),        # 게이트 A 는 중계로만 쓰고 나머지 입력은 뜬다
                net('74HC20#41 pin 6'),
                net('입력 B', '74HC20#41 pin 9', '74HC20#41 pin 10',
                    '74HC20#41 pin 12', '74HC20#41 pin 13'),
                net('74HC20#41 pin 8', 'LED Y 애노드')]
        self.assertEqual(value_of(nets, 'LED Y 애노드', {'A': 0, 'B': 1}), 0)

    def test_한_넷에_출력이_둘이면_멈춘다(self):
        nets = [net('입력 A', '74HC04#5 pin 1', '74HC04#5 pin 3'),
                net('74HC04#5 pin 2', '74HC04#5 pin 4', 'LED X 애노드')]
        with self.assertRaisesRegex(SimError, '출력 둘'):
            value_of(nets, 'LED X 애노드', {'A': 0})

    def test_같은_칩_라벨이_두_번이면_멈춘다(self):
        nets = [net('입력 A', '74HC04#5 pin 1'), net('74HC04#5 pin 1', 'LED X 애노드')]
        with self.assertRaisesRegex(SimError, '두 넷'):
            value_of(nets, 'LED X 애노드', {'A': 0})

    def test_입력값이_없으면_멈춘다(self):
        nets = [net('입력 A', '74HC04#5 pin 1'), net('74HC04#5 pin 2', 'LED X 애노드')]
        with self.assertRaisesRegex(SimError, '입력 A'):
            value_of(nets, 'LED X 애노드', {})

    def test_전원_레일은_상수다(self):
        nets = [net('74HC04#5 pin 1', rails=('gnd',)), net('74HC04#5 pin 2', 'LED X 애노드')]
        self.assertEqual(value_of(nets, 'LED X 애노드', {}), 1)


if __name__ == '__main__':
    unittest.main()
