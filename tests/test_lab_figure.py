"""`scripts/lab/figure.py` — 예상 결과 그림의 판정·이름·자리.

실제 주차 폴더를 읽지 않는다. 픽스처는 옛 실험10(`capture` + `stepped`)과
전가산기 계열 파생 명세(`truth-table` 만)다.
"""

import json
import tempfile
import unittest
from pathlib import Path

from scripts.lab import figure, notion
from scripts.lab.spec_parser import SpecItem, parse_spec

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_SPEC = ROOT / "tests/fixtures/spec_capture.md"
DERIVED_SPEC = ROOT / "tests/fixtures/spec_derived.md"


def _item(item_id):
    return SpecItem(id=item_id, title="제목", device=[], ics=[], tables=[])


class CaptureGate(unittest.TestCase):
    def test_capture_표만_고른다(self):
        pairs = figure.capture_tables(parse_spec(CAPTURE_SPEC))
        self.assertEqual([(i.id, t.id) for i, t in pairs], [("E10.P1", "T1")])

    def test_capture_가_없으면_빈_목록이다(self):
        self.assertEqual(figure.capture_tables(parse_spec(DERIVED_SPEC)), [])

    def test_종료_문구에_표마다_id_와_kind_가_있다(self):
        msg = figure.gate_message(parse_spec(DERIVED_SPEC))
        self.assertRegex(msg, r"T\d+: truth-table")
        self.assertIn("capture 표가 없어", msg)
        self.assertNotIn("\n", msg)


class PngName(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.exp = Path(tmp.name) / "실험07"
        (self.exp / "결선도").mkdir(parents=True)

    def _touch(self, name):
        (self.exp / "결선도" / name).write_bytes(b"")

    def test_결선도_완성본_이름을_따른다(self):
        self._touch("실험07_1_결선도_계수기.png")
        self._touch("실험07_1_결선도_계수기_1단계_칩.png")
        self.assertEqual(figure.figure_png_name(self.exp, _item("E7.P1")),
                         "실험07_1_예상결과_계수기.png")

    def test_결선도가_없으면_소실험_번호로만_짓는다(self):
        self.assertEqual(figure.figure_png_name(self.exp, _item("E7.P2-1")),
                         "실험07_2-1_예상결과.png")

    def test_1_이_10_을_삼키지_않는다(self):
        self._touch("실험07_10_결선도_다른것.png")
        self.assertEqual(figure.figure_png_name(self.exp, _item("E7.P1")),
                         "실험07_1_예상결과.png")

    def test_완성본이_둘이면_멈춘다(self):
        self._touch("실험07_1_결선도_가.png")
        self._touch("실험07_1_결선도_나.png")
        with self.assertRaises(ValueError):
            figure.figure_png_name(self.exp, _item("E7.P1"))

    def test_명세_경로는_output_을_가리킨다(self):
        self.assertEqual(figure.spec_figure_path("a.png"), "../output/a.png")


class SpecFigure(unittest.TestCase):
    def setUp(self):
        self.text = CAPTURE_SPEC.read_text(encoding="utf-8")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "명세.md"

    def _parse(self, text):
        self.path.write_text(text, encoding="utf-8")
        return parse_spec(self.path)

    def test_capture_표에_figure_를_넣는다(self):
        spec = self._parse(figure.set_spec_figure(self.text, "T1", "../output/a.png"))
        self.assertEqual(spec.table("T1").figure, "../output/a.png")
        self.assertIsNone(spec.table("T2").figure)

    def test_다시_적으면_한_줄만_바뀐다(self):
        once = figure.set_spec_figure(self.text, "T1", "../output/a.png")
        twice = figure.set_spec_figure(once, "T1", "../output/b.png")
        self.assertEqual(twice.count("- figure:"), 1)
        self.assertEqual(self._parse(twice).table("T1").figure, "../output/b.png")

    def test_capture_가_아닌_표는_거절한다(self):
        with self.assertRaises(ValueError):
            figure.set_spec_figure(self.text, "T2", "../output/a.png")

    def test_없는_표는_거절한다(self):
        with self.assertRaises(ValueError):
            figure.set_spec_figure(self.text, "T9", "../output/a.png")


class Uploaded(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name)

    def test_기록이_없으면_안_올린_것이다(self):
        self.assertFalse(figure.is_uploaded(self.out, "실험07_Shift_Register_예비보고서.md"))

    def test_그_md_를_올린_예비보고서_기록이_있으면_올린_것이다(self):
        (self.out / notion.RECORD_NAME).write_text(json.dumps({
            "schema": "notion-uploads/v1",
            "uploads": [
                {"kind": "결과보고서", "source": "실험07_Shift_Register_예비보고서.md"},
                {"kind": "예비보고서", "source": "실험07_Shift_Register_예비보고서.md"},
            ]}), encoding="utf-8")
        self.assertTrue(figure.is_uploaded(self.out, "실험07_Shift_Register_예비보고서.md"))
        self.assertFalse(figure.is_uploaded(self.out, "실험08_예비보고서.md"))


MD = "\n".join([
    "# 실험 목적",
    "",
    "목적 문단.",
    "",
    "<empty-block/>",
    "# 실험 과정 및 예상 결과",
    "## 실험 1) 계단 파형 관찰",
    "",
    "첫 문단.",
    "",
    "둘째 문단.",
    "",
    "<empty-block/>",
    "## 실험 2) 전이점",
    "",
    "문단.",
    "",
    "<empty-block/>",
    "<empty-block/>",
    "# 회로 결선도",
    "## 실험 3) 결선만 있는 소절",
    "",
    "결선 문단.",
    "",
])


class Placeholder(unittest.TestCase):
    def test_소절_마지막_문단_뒤_여백_블록_앞에_넣는다(self):
        out = figure.insert_placeholder(MD, "실험 1) 계단 파형 관찰", "a.png", "캡션 문장.")
        self.assertIn(
            "둘째 문단.\n\n![실험 1) 계단 파형 관찰 예상 결과](a.png)\n\n캡션 문장.\n\n"
            "<empty-block/>\n## 실험 2) 전이점", out)

    def test_두_번_넣어도_한_번만_들어간다(self):
        once = figure.insert_placeholder(MD, "실험 1) 계단 파형 관찰", "a.png", "캡션.")
        self.assertEqual(figure.insert_placeholder(once, "실험 1) 계단 파형 관찰", "a.png", "캡션."), once)

    def test_예상_결과_절_밖의_소절은_거절한다(self):
        with self.assertRaises(ValueError):
            figure.insert_placeholder(MD, "실험 3) 결선만 있는 소절", "a.png", "캡션.")

    def test_없는_소절은_거절한다(self):
        with self.assertRaises(ValueError):
            figure.insert_placeholder(MD, "실험 9) 없음", "a.png", "캡션.")

    def test_캡션은_한_줄이어야_한다(self):
        with self.assertRaises(ValueError):
            figure.insert_placeholder(MD, "실험 1) 계단 파형 관찰", "a.png", "첫 줄\n둘째 줄")


if __name__ == "__main__":
    unittest.main()
