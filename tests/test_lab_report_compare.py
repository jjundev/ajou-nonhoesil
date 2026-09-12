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

    def test_같은_이름의_소절_하나가_빠져도_다른_대절의_짝은_안_밀린다(self):
        # `## 실험 1-2) 3-input OR gate` 는 `# 실험 결과` 와 `# 실험 사진` 아래 한 번씩 있다.
        # 앞의 것(표가 있는 쪽)만 빼면 헤딩 수열 차이만 나야 하고, 사진 절의 같은 이름
        # 소절이 표 절의 짝으로 끌려와 가짜 표·그림 차이를 내면 안 된다.
        d = compare_reports(_text(APPROVED), _variant([("## 실험 1-2) 3-input OR gate\n", "")]))
        self.assertEqual(d["cell"], [], d["cell"])
        self.assertTrue(any("헤딩" in x and "실험 1-2) 3-input OR gate" in x for x in d["structure"]), d["structure"])
        self.assertFalse(any(("표 " in x or "그림" in x) and "실험 1-1)" not in x for x in d["structure"]), d["structure"])


from scripts.lab.report_compare import fact_tokens, judgment_markdown


class Facts(unittest.TestCase):
    def test_사실_토큰을_뽑는다(self):
        c = fact_tokens(["전류는 9.4mA 이고 74HC08 의 1번 핀이 고착-1 이면 A=B=1 에서 {01, 10, 11} 가 (미확인)"])
        self.assertEqual(c["9.4mA"], 1)
        self.assertEqual(c["74HC08"], 1)
        self.assertEqual(c["핀 1"], 1)
        self.assertEqual(c["고착-1"], 1)
        self.assertEqual(c["A=B=1"], 1)
        self.assertEqual(c["{01, 10, 11}"], 1)
        self.assertEqual(c["(미확인)"], 1)

    def test_수치가_바뀌면_fact_에_양쪽_값이_적힌다(self):
        d = compare_reports(_text(APPROVED), _variant([("9.4mA", "7.9mA")]))
        self.assertEqual(len(d["fact"]), 1, d["fact"])
        self.assertIn("9.4mA", d["fact"][0])
        self.assertIn("7.9mA", d["fact"][0])

    def test_자기대조는_fact_도_0(self):
        self.assertEqual(compare_reports(_text(APPROVED), _text(APPROVED))["fact"], [])


class Judgment(unittest.TestCase):
    def test_일곱_절과_메모리_주입_문장이_있다(self):
        d = Path(tempfile.mkdtemp())
        regen = d / "실험01_결과보고서.md"
        regen.write_text(_variant([("9.4mA", "7.9mA")]), encoding="utf-8")
        text = judgment_markdown(1, regen, leak_hits=["a.md: 문장"], agent_report="보고 본문")
        for n in range(1, 8):
            self.assertIn(f"## {n}.", text)
        self.assertIn("세션 메모리 주입", text)
        self.assertIn("7.9mA", text)
        self.assertIn("a.md: 문장", text)
        self.assertIn("보고 본문", text)
        self.assertIn("[ ] 규칙 없음", text)

    def test_누출_목록이_제너레이터여도_전부_적힌다(self):
        d = Path(tempfile.mkdtemp())
        regen = d / "실험01_결과보고서.md"
        regen.write_text(_text(APPROVED), encoding="utf-8")
        text = judgment_markdown(1, regen, leak_hits=(h for h in ["a.md: 하나", "b.md: 둘"]))
        self.assertIn("## 7. 구조적 누출 2건", text)
        self.assertIn("- a.md: 하나", text)
        self.assertIn("- b.md: 둘", text)
