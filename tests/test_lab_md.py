import unittest
from pathlib import Path

from scripts.lab import config, md

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

    def test_single_column_table_survives(self):
        """`_ROW`/`_SEP` 는 이미 두 번 손봤다(don't-care 행, escape 파이프).
        1열 표가 깨지면 직접 실행 없이는 조용히 사라질 수 있는데 회귀
        테스트가 없었다 (C3)."""
        body = "| A |\n|---|\n| 0 |\n| 1 |\n"
        tables = md.parse_tables(body)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].header, ["A"])
        self.assertEqual(tables[0].rows, [["0"], ["1"]])

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
        text = (ROOT / config.experiment_dir(1) / "체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["schema"], "lab-spec/v2")
        self.assertEqual(fm["experiment"], 1)
        self.assertEqual(len(fm["items"]), 5)
        # 느슨한 하한은 회귀를 놓친다 — 픽스처의 실제 개수로 고정한다
        self.assertEqual(len(md.parse_tables(body)), 10)  # 표 9개 + 토큰 규약표 1개

    def test_week6_spec_parses(self):
        text = (ROOT / config.experiment_dir(6) / "체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["experiment"], 6)
        self.assertEqual(len(md.parse_tables(body)), 6)   # 표 5개 + 토큰 참조표 1개

    def test_week12_spec_parses(self):
        text = (ROOT / config.experiment_dir(10) / "체크리스트/명세.md").read_text(encoding="utf-8")
        fm, body = md.split_frontmatter(text)
        self.assertEqual(fm["experiment"], 10)
        # T1 은 capture 라 셀 표가 없다. 본문의 마크다운 표는 T2(stepped) 하나뿐
        self.assertEqual(len(md.parse_tables(body)), 1)


class TestInlineComments(unittest.TestCase):
    """`기록.md` 의 `filled_by: ~   # hand | vision | 미기입` 이 `None` 이 아니라
    주석까지 붙은 문자열로 읽혔다. 소비자가 `is None` 으로 미기입을 판정하면
    조용히 틀린다 — ④ 결과보고서 스킬이 실제로 그걸 밟았다."""

    def test_comment_after_a_scalar_is_stripped(self):
        self.assertIsNone(md.parse_block("filled_by: ~   # hand | vision")["filled_by"])
        self.assertEqual(md.parse_block("week: 5   # 주차")["week"], 5)
        self.assertEqual(md.parse_block("t: hello # 뒤")["t"], "hello")

    def test_hash_inside_quotes_is_kept(self):
        self.assertEqual(md.parse_block('t: "has # inside"')["t"], "has # inside")

    def test_hash_without_leading_space_is_not_a_comment(self):
        """`#fff` 나 `c#sharp` 처럼 값 안의 `#` 는 주석이 아니다."""
        self.assertEqual(md.parse_block("t: c#sharp")["t"], "c#sharp")

    def test_value_that_starts_with_hash_is_kept(self):
        """앞 문자가 아예 없으면 '앞의 공백' 도 없다 — 주석이 아니다.
        이걸 주석으로 보면 `#fff` 같은 값이 조용히 None 이 된다."""
        self.assertEqual(md.parse_block("t: #fff")["t"], "#fff")
        self.assertEqual(md.parse_value("#fff"), "#fff")

    def test_hash_after_a_closing_bracket_is_a_comment(self):
        self.assertEqual(md.parse_block("t: [a, b] # 뒤")["t"], ["a", "b"])

    def test_hash_inside_single_quotes_is_kept(self):
        self.assertEqual(md.parse_block("t: 'has # inside'")["t"], "has # inside")

    def test_only_the_first_comment_marker_starts_the_comment(self):
        self.assertEqual(md.parse_block("t: v # a # b")["t"], "v")

    def test_comment_after_an_inline_mapping_is_stripped(self):
        self.assertEqual(md.parse_block("p: {x: 1} # 뒤")["p"], {"x": 1})

    def test_real_record_file_marks_unfilled_as_none(self):
        text = (ROOT / config.experiment_dir(1) / "체크리스트/기록.md").read_text(encoding="utf-8")
        front, _ = md.split_frontmatter(text)
        self.assertIsNone(front["filled_by"])


class ParseTableAt(unittest.TestCase):
    """`parse_tables` 가 위치를 잃어버려서 렌더러가 표를 제자리에 못 넣었다.
    한 줄 단위로 물을 수 있어야 산문·칩 상자와 순서를 지켜 섞을 수 있다."""

    def test_표_시작_줄에서_표와_다음_인덱스를_준다(self):
        lines = ["앞 산문", "| 핀 | 연결 |", "|---|---|", "| 14 | VCC |",
                 "뒤 산문"]
        table, nxt = md.parse_table_at(lines, 1)
        self.assertEqual(table.header, ["핀", "연결"])
        self.assertEqual(table.rows, [["14", "VCC"]])
        self.assertEqual(table.line, 3)      # 구분선의 1-based 줄 번호
        self.assertEqual(nxt, 4)             # `뒤 산문` 의 인덱스

    def test_표가_아니면_인덱스를_그대로_돌려준다(self):
        lines = ["앞 산문", "| 구분선이 없는 줄 |", "뒤 산문"]
        table, nxt = md.parse_table_at(lines, 0)
        self.assertIsNone(table)
        self.assertEqual(nxt, 0)
        table, nxt = md.parse_table_at(lines, 1)
        self.assertIsNone(table)
        self.assertEqual(nxt, 1)

    def test_대시_한_개_행을_구분선으로_보지_않는다(self):
        """`| - | - |` 는 이 프로젝트의 don't-care 데이터 행이다."""
        lines = ["| A | B |", "|---|---|", "| - | - |", "| 1 | 0 |"]
        table, nxt = md.parse_table_at(lines, 0)
        self.assertEqual(table.rows, [["-", "-"], ["1", "0"]])
        self.assertEqual(nxt, 4)

    def test_parse_tables_가_같은_결과를_준다(self):
        """추출이 기존 동작을 바꾸지 않았는지 본다."""
        body = "| A | B |\n|---|---|\n| 1 | 0 |\n\n산문\n\n| C |\n|---|\n| x |\n"
        got = md.parse_tables(body)
        self.assertEqual([t.header for t in got], [["A", "B"], ["C"]])
        self.assertEqual([t.line for t in got], [2, 8])


if __name__ == "__main__":
    unittest.main()
