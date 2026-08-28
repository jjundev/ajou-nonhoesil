import unittest
from pathlib import Path

from scripts.lab import md

ROOT = Path(__file__).resolve().parents[1]


class TestFrontmatter(unittest.TestCase):
    def test_scalars_and_inline_mapping(self):
        fm, body = md.split_frontmatter(
            '---\nweek: 2\ntitle: Basic Gates\n'
            'power: {VCC: "+5V", GND: "GND"}\n---\n본문\n'
        )
        self.assertEqual(fm["week"], 2)
        self.assertEqual(fm["title"], "Basic Gates")
        self.assertEqual(fm["power"], {"VCC": "+5V", "GND": "GND"})
        self.assertEqual(body, "본문\n")

    def test_block_mapping_inside_sequence(self):
        """`items:` 가 쓰는 형태. 시퀀스 원소가 여러 줄짜리 매핑이다."""
        fm, _ = md.split_frontmatter(
            "---\nitems:\n"
            "  - id: E1.P1-1\n"
            "    title: 3-input AND\n"
            "    device: [LED]\n"
            "    tables: [T1, T2]\n"
            "  - id: E1.P2\n"
            "    title: 복합회로\n"
            "    device: [LED]\n"
            "    tables: [T5]\n---\n"
        )
        self.assertEqual(len(fm["items"]), 2)
        self.assertEqual(fm["items"][0]["id"], "E1.P1-1")
        self.assertEqual(fm["items"][0]["device"], ["LED"])
        self.assertEqual(fm["items"][0]["tables"], ["T1", "T2"])
        self.assertEqual(fm["items"][1]["title"], "복합회로")

    def test_tilde_is_none(self):
        fm, _ = md.split_frontmatter("---\nfilled_by: ~\n---\n")
        self.assertIsNone(fm["filled_by"])

    def test_null_literal_is_none(self):
        self.assertIsNone(md.parse_value("null"))
        self.assertIsNone(md.parse_value(""))

    def test_booleans(self):
        self.assertIs(md.parse_value("false"), False)
        self.assertIs(md.parse_value("true"), True)

    def test_block_scalar_joins_lines(self):
        """`capture` 표의 `expected` 산문."""
        got = md.parse_block(
            "kind: capture\nexpected: |\n  첫 줄\n  둘째 줄\n"
        )
        self.assertEqual(got["expected"], "첫 줄 둘째 줄")

    def test_unclosed_frontmatter_raises(self):
        with self.assertRaises(ValueError):
            md.split_frontmatter("---\nweek: 2\n본문만 있고 닫는 구분자가 없다\n")

    def test_no_frontmatter_returns_empty(self):
        fm, body = md.split_frontmatter("# 제목\n본문\n")
        self.assertEqual(fm, {})
        self.assertEqual(body, "# 제목\n본문\n")


class TestSplitTop(unittest.TestCase):
    def test_respects_brackets_and_quotes(self):
        self.assertEqual(
            md.split_top('a: 1, b: [x, y], c: "p, q"'),
            ["a: 1", " b: [x, y]", ' c: "p, q"'],
        )


class TestTables(unittest.TestCase):
    def test_parses_header_and_rows(self):
        tables = md.parse_tables(
            "머리말\n\n| A | B | Y |\n|---|---|---|\n"
            "| 0 | 0 | 0 |\n| 1 | 1 | 1 |\n\n꼬리말\n"
        )
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].header, ["A", "B", "Y"])
        self.assertEqual(tables[0].rows, [["0", "0", "0"], ["1", "1", "1"]])
        self.assertEqual(tables[0].line, 4)   # 구분선의 1-based 줄 번호

    def test_ignores_pipe_free_prose(self):
        self.assertEqual(md.parse_tables("표가 하나도 없다\n"), [])

    def test_finds_multiple_tables(self):
        body = ("| A | Y |\n|---|---|\n| 0 | 1 |\n\n"
                "| S | R | Q |\n|---|---|---|\n| 0 | 1 | 0 |\n")
        self.assertEqual([len(t.header) for t in md.parse_tables(body)], [2, 3])

    def test_adjacent_tables_with_no_blank_line_between(self):
        """두 번째 표의 헤더를 첫 표의 행으로 삼키면 안 된다."""
        body = ("| A | Y |\n|---|---|\n| 0 | 1 |\n"
                "| S | R |\n|---|---|\n| 1 | 0 |\n")
        tables = md.parse_tables(body)
        self.assertEqual([t.header for t in tables], [["A", "Y"], ["S", "R"]])
        self.assertEqual([t.rows for t in tables], [[["0", "1"]], [["1", "0"]]])

    def test_dash_only_row_is_data_not_a_separator(self):
        """`-` 는 이 프로젝트의 don't-care 표기다. 구분선으로 오인하면
        데이터 행이 통째로 조용히 사라진다."""
        body = "| A | B |\n|---|---|\n| - | - |\n| 0 | 1 |\n"
        self.assertEqual(md.parse_tables(body)[0].rows, [["-", "-"], ["0", "1"]])

    def test_consecutive_dash_only_rows_all_survive(self):
        """인접한 무효 입력 코드가 연달아 오는 진리표 형태다.
        위치 판정만으로는 첫 행이 '다음 표의 헤더' 로 오인된다 —
        구분선 문법이 대시 3개 이상을 요구해야 이 결함 부류가 사라진다."""
        body = "| A | B |\n|---|---|\n| - | - |\n| - | - |\n| 0 | 1 |\n"
        self.assertEqual(md.parse_tables(body)[0].rows,
                         [["-", "-"], ["-", "-"], ["0", "1"]])

    def test_alignment_colons_are_still_a_separator(self):
        body = "| A | B |\n|:---|---:|\n| 0 | 1 |\n"
        self.assertEqual(md.parse_tables(body)[0].rows, [["0", "1"]])

    def test_table_at_eof_without_trailing_newline(self):
        body = "| A | B |\n|---|---|\n| 0 | 1 |"
        self.assertEqual(md.parse_tables(body)[0].rows, [["0", "1"]])

    def test_header_without_a_separator_is_not_a_table(self):
        self.assertEqual(md.parse_tables("| A | B |\n| 0 | 1 |\n"), [])

    def test_separator_without_a_header_is_not_a_table(self):
        self.assertEqual(md.parse_tables("|---|---|\n| 0 | 1 |\n"), [])

    def test_escaped_pipe_stays_inside_its_cell(self):
        """쪼개 버리면 validate 의 `\\|` 검사가 영영 발화하지 못한다."""
        body = "| A | B |\n|---|---|\n| a\\|b | c |\n"
        self.assertEqual(md.parse_tables(body)[0].rows, [["a\\|b", "c"]])

    def test_symbolic_cells_survive_untouched(self):
        """실험6 의 복합 토큰. 콜론·괄호·어포스트로피가 셀 안에서 살아남아야 한다."""
        body = ("| J | K | C | Q(t) |\n|---|---|---|------|\n"
                "| 1 | 1 | 1 | Q(t-1)' : Toggle |\n"
                "| x | x | 0 | Q(t-1) |\n")
        rows = md.parse_tables(body)[0].rows
        self.assertEqual(rows[0][3], "Q(t-1)' : Toggle")
        self.assertEqual(rows[1][3], "Q(t-1)")


class TestRealSpecFiles(unittest.TestCase):
    """Task 1 이 손으로 쓴 실물 명세가 그대로 파싱되어야 한다."""

    def test_week2_spec_parses(self):
        text = (ROOT / "2주차/체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["schema"], "lab-spec/v1")
        self.assertEqual(fm["week"], 2)
        self.assertEqual(fm["experiment"], 1)
        self.assertEqual(len(fm["items"]), 3)
        # 느슨한 하한은 회귀를 놓친다 — Task 1 픽스처의 실제 개수로 고정한다
        self.assertEqual(len(md.parse_tables(body)), 9)

    def test_week6_spec_parses(self):
        text = (ROOT / "6주차/체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["experiment"], 6)
        self.assertEqual(len(md.parse_tables(body)), 6)   # 표 5개 + 토큰 참조표 1개

    def test_week12_spec_parses(self):
        text = (ROOT / "12주차/체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["experiment"], 10)
        # T1 은 capture 라 셀 표가 없다. 본문의 마크다운 표는 T2(stepped) 하나뿐
        self.assertEqual(len(md.parse_tables(body)), 1)


if __name__ == "__main__":
    unittest.main()
