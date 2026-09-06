import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.record import PROMPTS, _width, derive_record
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]


class TestWeek2Record(unittest.TestCase):
    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.text = derive_record(self.spec)

    def test_frontmatter_marks_it_unfilled(self):
        self.assertIn("schema: lab-record/v2", self.text)
        self.assertIn("filled_by: ~", self.text)

    def test_expected_column_is_labelled_and_check_column_is_blank(self):
        self.assertIn("Y예상", self.text)
        self.assertIn("확인", self.text)

    def test_every_table_gets_a_memo_line(self):
        """개수를 박지 말고 명세에서 센다. 참조표(role=reference)는 기록에
        들어가지 않으므로 셈에서도 빼야 한다."""
        used = sum(1 for item in self.spec.items for tid in item.tables
                   if self.spec.table(tid).role != "reference")
        self.assertEqual(self.text.count("- 메모:"), used)

    def test_closing_prompts_are_present(self):
        for prompt in PROMPTS:
            self.assertIn(f"- {prompt}:", self.text)

    def test_row_count_survives_derivation(self):
        """8행 진리표는 기록에서도 8행이어야 한다."""
        block = self.text[self.text.index("### T1"):self.text.index("### T2")]
        data_rows = [ln for ln in block.split("\n")
                     if ln.startswith("|") and not set(ln) <= set("|- ")]
        self.assertEqual(len(data_rows), 9)   # 헤더 1 + 데이터 8


class TestKindSpecificShapes(unittest.TestCase):
    def test_capture_gets_a_sketch_grid_not_a_table(self):
        text = derive_record(parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md"))
        block = text[text.index("### T1"):text.index("### T2")]
        self.assertIn("스케치", block)
        self.assertIn("- 캡션:", block)
        self.assertNotIn("예상 |", block)

    def test_reference_tables_are_excluded(self):
        """T6~T9 는 교안 2입력 이론표다. 기록 칸을 만들면 안 된다."""
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        text = derive_record(spec)
        for tid in ("T6", "T7", "T8", "T9"):
            with self.subTest(table=tid):
                self.assertNotIn(f"### {tid} ·", text)
        for tid in ("T1", "T5"):
            with self.subTest(table=tid):
                self.assertIn(f"### {tid} ·", text)

    def test_capture_carries_the_prose_expectation(self):
        text = derive_record(parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md"))
        self.assertIn("> 예상:", text)

    def test_stepped_keeps_its_columns_without_an_expected_suffix(self):
        """스텝 표는 비어 있는 열 자체가 채울 칸이다. `예상` 을 붙이면 안 된다."""
        text = derive_record(parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md"))
        block = text[text.index("### T2"):]
        self.assertIn("| 스텝", block)
        self.assertNotIn("예상", block.split("- 메모:")[0])


class TestAlignment(unittest.TestCase):
    def test_korean_headers_align(self):
        """손으로 채울 표라 정렬이 실제로 중요하다 (한글은 2칸).

        파이프 개수·trailing space 만 보면 `_grid` 가 헤더·구분선·데이터 행을
        전부 같은 `widths` 리스트로 만들고 항상 `|` 로 끝내므로 **구조적으로
        항상 같다** — `_pad` 가 동공백 대신 `len()` 으로 계산해도 이 두 조건은
        여전히 성립해 회귀를 못 잡는다(C2). 대신 `_width`(east-asian-width
        인식) 로 각 셀의 실제 렌더 폭을 재서, 같은 열이면 행이 달라도 폭이
        항상 같은지(=정렬되는지) 를 직접 본다.
        """
        text = derive_record(parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md"))
        lines = text.split("\n")
        start = next(i for i, ln in enumerate(lines) if ln.startswith("| 스텝"))
        block = []
        i = start
        while i < len(lines) and lines[i].startswith("|"):
            block.append(lines[i])
            i += 1
        self.assertGreaterEqual(len(block), 4)   # 헤더 + 구분선 + 데이터 2행 이상

        def cells(line):
            return line.split("|")[1:-1]   # 맨 앞뒤의 빈 문자열을 버린다

        header_cells = cells(block[0])
        data_rows = [cells(ln) for ln in block[2:]]   # block[1] 은 구분선이다
        for row in data_rows:
            self.assertEqual(len(row), len(header_cells))
        for col in range(len(header_cells)):
            widths = {_width(header_cells[col])} | {_width(r[col]) for r in data_rows}
            with self.subTest(col=col, header=header_cells[col].strip()):
                self.assertEqual(len(widths), 1, f"열 {col} 의 렌더 폭이 행마다 다르다: {widths}")


if __name__ == "__main__":
    unittest.main()


class RecordTitleTest(unittest.TestCase):
    """기록 제목이 실제로 무엇을 찍는지 고정한다.

    이 자리는 지금까지 어떤 테스트도 보지 않았다 — 제목을 바꿔도 스위트가
    그대로 통과했다. 실제로 프리뷰 제목이 그렇게 조용히 덮어써진 적이 있다.
    """

    def test_제목이_실험_기준이고_주차가_없다(self):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        heading = next(l for l in derive_record(spec).splitlines()
                       if l.startswith("# "))
        self.assertEqual(heading, "# 실험1 Basic Gates 기록")
        self.assertNotIn("주차", heading)

    def test_week_는_v2에서_아예_없다(self):
        # v1 은 week 를 프론트매터에 남겼다 — v2 는 필드 자체를 걷어낸다.
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.assertNotIn("week:", derive_record(spec))

    def test_date_를_프론트매터에_넣지_않는다(self):
        # 일정을 산출물에도 적으면 config.EXPERIMENT_DATES 와 두 곳에 살게 되어
        # week 를 없앤 이유(단일 출처)와 같은 결함을 날짜로 다시 만든다.
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.assertNotIn("date:", derive_record(spec))


class RecordKindCells(unittest.TestCase):
    """기록.md 와 인쇄본은 쌍이다. 규약이 갈리면 전사에서 어긋난다."""

    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(10) / "체크리스트/명세.md")
        self.md = derive_record(self.spec)

    def test_stepped_에_확인_열을_붙이지_않는다(self):
        """인쇄본이 뺐다 — 대조할 예상값이 없는 표다."""
        block = self.md[self.md.index("### T2 ·"):]
        header = block.split("\n")[2]          # 표의 헤더 줄
        self.assertIn("7405 핀8", header)
        self.assertNotIn("확인", header)

    def test_stepped_의_스텝_행이_전부_온다(self):
        block = self.md[self.md.index("### T2 ·"):]
        for n in range(1, 11):
            with self.subTest(step=n):
                self.assertIn(f"| S{n} ", block)

    def test_capture_에_판독_조건_줄이_있다(self):
        block = self.md[self.md.index("### T1 ·"):self.md.index("### T2 ·")]
        for token in ("V/div", "time/div", "프로브", "X-Y"):
            with self.subTest(token=token):
                self.assertIn(token, block)

    def test_capture_에_스케치와_캡션이_있다(self):
        block = self.md[self.md.index("### T1 ·"):self.md.index("### T2 ·")]
        self.assertIn("스케치", block)
        self.assertIn("- 캡션:", block)
        self.assertIn("- 사진 파일:", block)

    def test_진리표는_확인_열을_유지한다(self):
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        text = derive_record(spec)
        block = text[text.index("### T1 ·"):]
        self.assertIn("확인", block.split("\n")[2])
