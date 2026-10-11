"""결선도 PNG 는 보드만, 글자는 옆 JSON 으로 (2026-09-28 읽기면 개편)."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
FIXTURE = ROOT / "tests/fixtures/board_min/배치.py"
FIXTURE_E5 = ROOT / "tests/fixtures/board_v2_e5/배치.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Sidecar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _min(self, d):
        name, fn = self.mod.load_board_file(FIXTURE).FINALS[0]
        p = os.path.join(d, name)
        return fn(p, None), p

    def test_PNG_는_보드_높이에서_끝난다(self):
        """옛 PNG 는 보드 아래 흰 띠에 범례·주석·순서표를 붙여 1.4 배쯤 길었다."""
        with tempfile.TemporaryDirectory() as d:
            bb, p = self._min(d)
            with Image.open(p) as im:
                self.assertEqual(im.size, (998 * self.mod.SCALE,
                                           (bb.r_y(35) + 20) * self.mod.SCALE))

    def test_사이드카가_PNG_옆에_생긴다(self):
        with tempfile.TemporaryDirectory() as d:
            bb, p = self._min(d)
            side = Path(p).with_suffix(".json")
            self.assertTrue(side.exists())
            data = json.loads(side.read_text(encoding="utf-8"))
        self.assertEqual(data, bb.sidecar())
        self.assertEqual(data["schema"], "breadboard-sidecar/v1")
        self.assertEqual(data["title"], "최소 보드")
        self.assertEqual([s["kind"] for s in data["steps"]], ["vcc", "gnd"])
        self.assertEqual(data["steps"][0]["from"], "전원잭")
        self.assertEqual(data["steps"][0]["n"], 1)
        self.assertIsNone(data["kept"])
        self.assertEqual(data["removals"], [])
        self.assertEqual(data["probes"], [])

    def test_자동_주석이_없다(self):
        """잭 색·미사용 핀 문구는 전원 박스와 핀 점검 상자가 싣는다."""
        with tempfile.TemporaryDirectory() as d:
            bb, _p = self._min(d)
        self.assertEqual(bb.notes, [])
        bb2 = self.mod.BreadboardRenderer()
        bb2.draw_chip('74HC08', 10)
        bb2.mark_unused_inputs([9, 10], 10, chip='74HC08')
        bb2.mark_unused_outputs([8], 10, chip='74HC08')
        self.assertEqual(bb2.notes, [])

    def test_도장은_v2(self):
        with tempfile.TemporaryDirectory() as d:
            bb, p = self._min(d)
            self.assertRegex(self.mod.read_stamp(p), r"^v2:[0-9a-f]{64}$")

    def test_걷기_보드_사이드카는_번호_있는_걷기를_싣는다(self):
        """실험03 BOARDS[1] 은 `2걷기_LED1프로브` 걷기 보드다."""
        board = self.mod.load_board(3)
        (n0, f0, s0), (n1, f1, s1) = board.BOARDS[0], board.BOARDS[1]
        with tempfile.TemporaryDirectory() as d:
            base = f0(os.path.join(d, n0), stage=s0, baseline=None).snapshot()
            walk = f1(os.path.join(d, n1), stage=s1, baseline=base)
            data = json.loads(Path(d, n1).with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(data, walk.sidecar())
        self.assertEqual(data["steps"], [])
        self.assertGreater(len(data["removals"]), 0)
        self.assertEqual([r["n"] for r in data["removals"]][:1], [1])
        self.assertIn("→", data["removals"][0]["text"])
        self.assertIsInstance(data["kept"], int)

    def test_실험02_계측이_사이드카에_있다(self):
        board = self.mod.load_board(2)
        name, fn = board.FINALS[0]
        with tempfile.TemporaryDirectory() as d:
            fn(os.path.join(d, name), None)
            data = json.loads(Path(d, name).with_suffix(".json").read_text(encoding="utf-8"))
        labels = [p["label"] for p in data["probes"]]
        self.assertIn("함수발생기 + CH1 (가로축)", labels)
        self.assertTrue(all(p["at"] for p in data["probes"]))


class SidecarLeds(unittest.TestCase):
    """v2 사이드카의 `leds` — 체크리스트 LED 점등 열·순서 번호의 출처(2026-10-11)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _export(self, fixture):
        name, fn = self.mod.load_board_file(fixture).FINALS[0]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, name)
            bb = fn(p, None)
            data = json.loads(Path(p).with_suffix(".json").read_text(encoding="utf-8"))
        return bb, data

    def _bb_e5(self):
        return self._export(FIXTURE_E5)[0]

    def _bb_min(self):
        return self._export(FIXTURE)[0]

    def _e5(self):
        return self._export(FIXTURE_E5)[1]

    def test_v2_사이드카는_LED_를_보드_순서로_싣는다(self):
        leds = self._e5()["leds"]
        self.assertEqual([l["tag"] for l in leds],
                         ["Y0", "Y1", "Y2", "Y3", "Y4", "Y5", "Y9", "Y6", "Y8", "Y7"])
        self.assertTrue(all(l["active_low"] is True for l in leds))
        self.assertTrue(all(l["at"].startswith("우 a") for l in leds))

    def test_v1_사이드카에는_leds_키가_없다(self):
        self.assertNotIn("leds", self._bb_min().sidecar())

    def test_leds_는_도장에_들지_않는다(self):
        self.assertNotIn("leds", self._bb_e5().content())


if __name__ == "__main__":
    unittest.main()
