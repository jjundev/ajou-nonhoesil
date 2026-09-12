"""결과보고서 재생성물 ↔ 승인본 대조.

승인본은 실험01 결보(노션 v5 동기화본)이고, baseline v5 는 같은 내용을 노션이
HTML 표로 돌려준 것이다. 둘을 같게 읽지 못하면 이 도구는 형태 차이를 결함으로
센다 — 그래서 자기대조와 승인본↔baseline 대조가 첫 테스트다.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.report_compare import compare_reports, counted, report_shape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / config.experiment_dir(1) / "output"
APPROVED = OUT / "실험01_결과보고서.md"
BASELINE_V5 = OUT / "실험01_결과보고서_notion_baseline_v5.md"


def _text(p):
    return p.read_text(encoding="utf-8")


def _variant(replacements):
    """승인본의 **첫 출현만** 바꾼 문자열."""
    text = _text(APPROVED)
    for old, new in replacements:
        assert text.count(old) >= 1, old
        text = text.replace(old, new, 1)
    return text


class Shape(unittest.TestCase):
    def test_승인본의_헤딩은_두_단계이고_제목은_따로_둔다(self):
        s = report_shape(_text(APPROVED))
        self.assertTrue(s.title.startswith("실험1 Basic Gates"))
        self.assertTrue(all(sec.level in (1, 2) for sec in s.sections))
        self.assertEqual(s.sections[0].heading, "실험 결과")

    def test_HTML_표와_파이프_표를_같은_셀로_읽는다(self):
        a = report_shape(_text(APPROVED))
        b = report_shape(_text(BASELINE_V5))
        self.assertEqual([sec.heading for sec in a.sections], [sec.heading for sec in b.sections])
        for x, y in zip(a.sections, b.sections):
            with self.subTest(x.heading):
                self.assertEqual(x.tables, y.tables)

    def test_여백_블록은_헤딩_앞_개수로_센다(self):
        s = report_shape("# 제목\n<table_of_contents color=\"gray\"/>\n<empty-block/>\n# 실험 결과\n본문.\n"
                         "<empty-block/>\n<empty-block/>\n# 고찰\n본문.\n")
        self.assertEqual([sec.empty_blocks for sec in s.sections], [1, 2])

    def test_참고문헌은_항목_단위다(self):
        s = report_shape("# 출처 및 참고문헌\n- 논리회로실험 강의노트\n- Nexperia, 74HC_HCT08 Rev. 9\n  https://x\n")
        self.assertEqual(len(s.references), 2)
        self.assertIn("https://x", s.references[1])


class Compare(unittest.TestCase):
    def test_자기대조는_0건이다(self):
        d = compare_reports(_text(APPROVED), _text(APPROVED))
        self.assertEqual(counted(d), 0, d)
        self.assertEqual(sorted(d), ["cell", "fact", "references", "structure", "style", "wording"])

    def test_승인본과_baseline_v5는_wording_밖_0건이다(self):
        d = compare_reports(_text(APPROVED), _text(BASELINE_V5))
        self.assertEqual(counted(d), 0, {k: v for k, v in d.items() if k != "wording"})

    def test_셀_하나가_다르면_cell_1건(self):
        d = compare_reports(_text(APPROVED), _variant([("\t| 1 | 1 | 1 | 1 | 1 |", "\t| 1 | 1 | 1 | 1 | 0 |")]))
        self.assertEqual(len(d["cell"]), 1, d["cell"])
        self.assertIn("'1'", d["cell"][0])
        self.assertIn("'0'", d["cell"][0])

    def test_소절이_빠지면_structure(self):
        d = compare_reports(_text(APPROVED), _variant([("## 실험 1-2) 3-input OR gate\n", "")]))
        self.assertTrue(any("실험 1-2) 3-input OR gate" in x for x in d["structure"]), d["structure"])

    def test_참고문헌_한_줄이_빠지면_references(self):
        d = compare_reports(_text(APPROVED), _variant([("- 논리회로실험 강의노트\n", "")]))
        self.assertEqual(len(d["references"]), 1, d["references"])

    def test_문체는_재생성_쪽만_본다(self):
        d = compare_reports(_text(APPROVED), _variant([("L1이 A·B", "L1 이 A·B")]))
        self.assertEqual(len(d["style"]), 1, d["style"])

    def test_wording_은_절마다_일치율_한_줄이다(self):
        d = compare_reports(_text(APPROVED), _text(APPROVED))
        self.assertTrue(all("1.00" in x for x in d["wording"]), d["wording"])
