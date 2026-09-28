"""주차 결선 파일의 `LAYERS` — 완성본을 따라 그리기 층으로 나눈 경계 (2026-09-28).

층은 완성본 결선 번호 1..N 을 빈틈·겹침 없이 덮어야 하고, 층 보드의 결선 순서표는
완성본과 같아야 한다(뒤 층을 안 그려도 자리가 안 바뀐다).
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Layers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.boards = {}
        for n in cls.mod.board_numbers():
            board = cls.mod.load_board(n)
            if hasattr(board, 'LAYERS'):
                cls.boards[n] = board
        cls.tmp = tempfile.TemporaryDirectory()
        cls.finals = {}
        for n, board in cls.boards.items():
            for filename, fn in board.FINALS:
                if filename in board.LAYERS:
                    bb = fn(os.path.join(cls.tmp.name, filename), None)
                    cls.finals[filename] = (fn, bb, board.LAYERS[filename])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_실험04_에_LAYERS_가_있다(self):
        self.assertIn(4, self.boards)
        self.assertEqual(set(self.boards[4].LAYERS),
                         {f for f, _ in self.boards[4].FINALS})

    def test_층은_1부터_N까지_빈틈없이(self):
        for filename, (_fn, bb, layers) in self.finals.items():
            with self.subTest(filename=filename):
                expected = 1
                for lo, hi, label in layers:
                    self.assertEqual(lo, expected, f'{label} 이 {expected}번에서 시작해야 한다')
                    self.assertLessEqual(lo, hi)
                    self.assertTrue(label.strip())
                    expected = hi + 1
                self.assertEqual(expected - 1, len(bb.steps))

    def test_층_보드는_완성본과_같은_결선(self):
        """번호 배지는 층마다 완성본 배지의 제 몫만 — 층을 모으면 완성본 배지와 같다.

        배지 수를 hi-lo+1 로 세지 않는다. `connect_unused_inputs` 의 `step_note` 처럼
        배지 없이 순서표에만 오르는 번호가 있다(실험02 6·7번 — 완성본도 7번에 배지 5개).
        """
        for filename, (fn, final, layers) in self.finals.items():
            seen = []
            for i, (lo, hi, _label) in enumerate(layers, 1):
                with self.subTest(filename=filename, layer=i):
                    p = os.path.join(self.tmp.name, f'{i}_{filename}')
                    bb = fn(p, None, layer=(lo, hi))
                    self.assertEqual(bb.sidecar()['steps'], final.sidecar()['steps'])
                    self.assertLessEqual(len(bb.marker_boxes), hi - lo + 1)
                    self.assertTrue(set(bb.marker_boxes) <= set(final.marker_boxes))
                    seen += bb.marker_boxes
            with self.subTest(filename=filename, layer='합'):
                self.assertCountEqual(seen, final.marker_boxes)

    def test_단계와_층은_함께_못_준다(self):
        board = self.boards[4]
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            board.build_e4_mux(os.path.join(d, 'x.png'), None, stage=4, layer=(1, 7))


if __name__ == "__main__":
    unittest.main()
