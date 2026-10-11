"""보드 LED 순서와 단계별 급전 지도. 설계: docs/plans/2026-10-11-체크리스트-LED-점등열-설계.md"""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.leds import board_leds, circled, feeds_by_stage, lit, unresolved_feeds
from scripts.lab.netlist_parser import parse_netlist

ROOT = Path(__file__).resolve().parents[1]
E5_DIR = ROOT / config.experiment_dir(5) / "결선도"


class TestBoardLeds(unittest.TestCase):
    def test_C1_완성본_LED_순서와_번호(self):
        leds = board_leds(E5_DIR / "실험05_1-2_결선도_BCD디코더.png")
        self.assertEqual([(l.index, l.tag) for l in leds][5:8], [(6, "Y5"), (7, "Y9"), (8, "Y6")])
        self.assertTrue(leds[0].active_low)

    def test_leds_키가_없으면_빈_목록(self):
        with tempfile.TemporaryDirectory() as d:
            png = Path(d, "옛.png")
            png.write_bytes(b"")
            png.with_suffix(".json").write_text(
                json.dumps({"schema": "breadboard-sidecar/v1"}), encoding="utf-8")
            self.assertEqual(board_leds(png), [])
            self.assertEqual(board_leds(Path(d, "없음.png")), [])


class TestFeeds(unittest.TestCase):
    def setUp(self):
        net = parse_netlist(E5_DIR / "netlist.md")
        self.c1, self.c2 = net.circuits[0], net.circuits[1]

    def test_C1_급전은_누적된다(self):
        f = feeds_by_stage(self.c1)
        self.assertEqual(f[0], {"Y0": "Y0"})
        self.assertEqual(set(f[1]), {"Y0", "Y1", "Y2", "Y3"})
        self.assertEqual(len(f[3]), 10)

    def test_C2_임시_급전은_노드로_풀리고_걷기에서_빠진다(self):
        f = feeds_by_stage(self.c2)          # 단계: 1, 2, 3걷기, 3, 4, 5
        self.assertEqual(f[1]["A2"], "D0'")
        self.assertNotIn("A2", f[2])
        self.assertNotIn("A2", f[3])
        self.assertEqual(f[5]["A2"], "A2")

    def test_start_지도를_이어받는다(self):
        f = feeds_by_stage(self.c2, start={"X9": "Y0"})
        self.assertEqual(f[0]["X9"], "Y0")

    def test_실험05_는_못_푼_급전이_없다(self):
        self.assertEqual(unresolved_feeds(self.c1) + unresolved_feeds(self.c2), [])


class TestHelpers(unittest.TestCase):
    def test_점등_판정(self):
        self.assertTrue(lit(0, True))
        self.assertFalse(lit(1, True))
        self.assertTrue(lit(1, False))
        self.assertEqual(circled(7), "⑦")
        with self.assertRaises(ValueError):
            circled(21)


if __name__ == "__main__":
    unittest.main()
