import importlib.util
import tempfile
import unittest
from pathlib import Path

from scripts.lab import schematic
from scripts.lab.spec_parser import SpecItem

ROOT = Path(__file__).resolve().parents[1]
MANUAL3 = ROOT / "강의노트/실험3. 가산기 & 감산기 (25.03.25 수정).pdf"
HAS_FITZ = importlib.util.find_spec("fitz") is not None

SPEC = """---
schema: lab-spec/v2
experiment: 3
title: 가산기 & 감산기
source_manual: 강의노트/실험3. 가산기 & 감산기 (25.03.25 수정).pdf
power: {VCC: "+5V", GND: "GND"}
items:
  - id: E3.P1-2
    title: 실험 1-2) 전가산기
    device: [LED]
    ics: ["74HC86", "74HC08", "74HC32"]
    tables: [T3]
    pages: [5]
  - id: E3.P2-2
    title: 실험 2-2) 전감산기
    device: [LED]
    ics: ["74HC86"]
    tables: [T7]
---

본문
"""


class TestName(unittest.TestCase):
    def test_소실험_번호로_짓는다(self):
        item = SpecItem(id="E3.P1-2", title="t", device=["LED"], ics=[], tables=[])
        self.assertEqual(schematic.schematic_name(Path("보고서/실험03"), item),
                         "실험03_1-2_회로도.png")


class TestSetSpecSchematic(unittest.TestCase):
    def test_pages_다음_줄에_넣는다(self):
        out = schematic.set_spec_schematic(SPEC, "E3.P1-2", ["실험03_1-2_회로도.png"])
        self.assertIn("    pages: [5]\n    schematic: [실험03_1-2_회로도.png]\n  - id: E3.P2-2",
                      out)

    def test_있으면_바꾼다(self):
        once = schematic.set_spec_schematic(SPEC, "E3.P1-2", ["a.png"])
        twice = schematic.set_spec_schematic(once, "E3.P1-2", ["b.png", "c.png"])
        self.assertIn("    schematic: [b.png, c.png]\n", twice)
        self.assertNotIn("a.png", twice)
        self.assertEqual(twice.count("schematic:"), 1)

    def test_pages_가_없으면_항목_끝에_붙인다(self):
        out = schematic.set_spec_schematic(SPEC, "E3.P2-2", ["실험03_2-2_회로도.png"])
        self.assertIn('    tables: [T7]\n    schematic: [실험03_2-2_회로도.png]\n---', out)

    def test_다른_항목과_본문은_그대로다(self):
        out = schematic.set_spec_schematic(SPEC, "E3.P2-2", ["x.png"])
        self.assertEqual(out.replace("    schematic: [x.png]\n", ""), SPEC)

    def test_없는_항목이면_던진다(self):
        with self.assertRaises(ValueError):
            schematic.set_spec_schematic(SPEC, "E3.P9", ["x.png"])

    def test_파서가_읽는다(self):
        from scripts.lab.spec_parser import parse_spec
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "명세.md"
            p.write_text(schematic.set_spec_schematic(SPEC, "E3.P1-2", ["a.png"])
                         .replace("본문", "## T3 · x\n\n- kind: truth-table\n- encoding: 0/1\n"
                                  "- source: manual:p5\n\n| A | S |\n|---|---|\n| 0 | 0 |\n\n"
                                  "## T7 · y\n\n- kind: truth-table\n- encoding: 0/1\n"
                                  "- source: manual:p7\n\n| A | D |\n|---|---|\n| 0 | 0 |\n"),
                         encoding="utf-8")
            self.assertEqual(parse_spec(p).items[0].schematic, ["a.png"])


@unittest.skipUnless(HAS_FITZ and MANUAL3.exists(), "pymupdf 나 실험3 교안이 없다")
class TestDefaultBoxOnManual(unittest.TestCase):
    """실측(2026-09-19): p5 회로 이미지 [21,278,476,502], p7 [50,287,450,502].
    로고(Image33, 9쪽 중 8쪽에 반복)는 빼고, 이미지 아래 캡션 '회로 구성'(top 507)은
    4pt 여백 밖이라 들어오지 않는다."""

    def test_p5_는_회로_이미지를_고른다(self):
        x0, y0, x1, y1 = schematic.default_box(MANUAL3, 5)
        self.assertAlmostEqual(x0, 17, delta=2)
        self.assertAlmostEqual(y0, 274, delta=2)
        self.assertAlmostEqual(x1, 480, delta=2)
        self.assertLess(y1, 507)

    def test_p7_은_로고가_아니다(self):
        x0, y0, x1, y1 = schematic.default_box(MANUAL3, 7)
        self.assertLess(x1, 500)          # 로고는 x 529~703
        self.assertGreater(x1 - x0, 350)

    def test_crop_은_300dpi_PNG_를_낸다(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "c.png"
            box = (50.0, 287.0, 450.0, 502.0)
            schematic.crop(MANUAL3, 7, box, out)
            data = out.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            width = int.from_bytes(data[16:20], "big")
            self.assertAlmostEqual(width, 400 / 72 * 300, delta=3)
