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


if __name__ == '__main__':
    unittest.main()
