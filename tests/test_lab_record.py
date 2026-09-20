import datetime
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config, record
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
        text = derive_record(parse_spec(ROOT / "tests/fixtures/spec_capture.md"))
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
        text = derive_record(parse_spec(ROOT / "tests/fixtures/spec_capture.md"))
        self.assertIn("> 예상:", text)

    def test_stepped_keeps_its_columns_without_an_expected_suffix(self):
        """스텝 표는 비어 있는 열 자체가 채울 칸이다. `예상` 을 붙이면 안 된다."""
        text = derive_record(parse_spec(ROOT / "tests/fixtures/spec_capture.md"))
        block = text[text.index("### T2"):]
        self.assertIn("| 스텝", block)
        self.assertNotIn("예상", block.split("- 메모:")[0])


class SharedLetterRecord(unittest.TestCase):
    """교안이 입력과 출력에 같은 글자를 쓰는 표(실험3 반감산기 `A B D B`).

    `{이름: 열 번호}` 로 셀을 찾으면 두 `B` 가 하나로 뭉개져 입력 `B` 칸에 출력
    값이 찍힌다. 기록에서는 출력에 `예상` 이 붙어 `B` 와 `B예상` 으로 갈린다.
    """

    def test_입력_B_와_출력_B예상_이_따로_찍힌다(self):
        text = derive_record(parse_spec(ROOT / "tests/fixtures/spec_shared_letter.md"))
        rows = [[c.strip() for c in ln.strip().strip("|").split("|")]
                for ln in text.split("\n")
                if ln.startswith("|") and not set(ln) <= set("|- ")]
        self.assertEqual(rows[0], ["A", "B", "D예상", "B예상", "확인"])
        self.assertEqual(rows[1:5], [["0", "0", "0", "0", ""], ["0", "1", "1", "1", ""],
                                     ["1", "0", "1", "0", ""], ["1", "1", "0", "0", ""]])


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
        text = derive_record(parse_spec(ROOT / "tests/fixtures/spec_capture.md"))
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
        self.spec = parse_spec(ROOT / "tests/fixtures/spec_capture.md")
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


def _fill_first_blank_row(text: str):
    """빈 칸이 있는 첫 데이터 행을 채운다. `(채운 텍스트, 채운 칸 수)`.

    셀 자리로 찾는다 — 진리표의 확인 열이든 스텝표의 빈 열이든 같은 방법으로
    "사람이 실험실에서 적은 칸" 을 만든다.
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = line.split("|")
        blanks = [j for j in range(1, len(cells) - 1) if not cells[j].strip()]
        if not blanks:
            continue
        for j in blanks:
            cells[j] = " ✓ "
        lines[i] = "|".join(cells)
        return "\n".join(lines), len(blanks)
    raise AssertionError("빈 칸이 있는 데이터 행이 없다")


class 채워진기록보호(unittest.TestCase):
    """② 3단계가 채워진 `기록.md` 를 말없이 덮은 사고(2026-09-20 실험03)의 회귀.

    그날 덮인 파일에는 `filled_by: vision`·확인 칸 16개·종료 메모 4문항이 있었고
    전부 빈 템플릿이 됐다. 작업자가 알아채고 `git checkout` 으로 되돌렸지만,
    못 봤으면 실험 당일에만 알 수 있는 값이 조용히 사라졌을 것이다.
    """

    def setUp(self):
        self.spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        self.template = derive_record(self.spec)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "기록.md"

    def _filled(self) -> str:
        """실험을 마친 기록. 프론트매터·확인 칸·종료 메모가 다 들어 있다."""
        text, _ = _fill_first_blank_row(self.template)
        return (text.replace("filled_by: ~", "filled_by: vision")
                    .replace("- 막혔던 것:", "- 막혔던 것: GND 접촉 불량"))

    def test_없으면_템플릿을_만든다(self):
        """빈 템플릿을 처음 내는 경로는 가드가 생겨도 그대로다."""
        result = record.write_record(self.path, self.template)
        self.assertEqual(result["status"], "created")
        self.assertIsNone(result["backup"])
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.template)

    def test_채워진_기록을_덮지_않고_거절한다(self):
        filled = self._filled()
        self.path.write_text(filled, encoding="utf-8")
        with self.assertRaises(record.RecordExistsError) as cm:
            record.write_record(self.path, self.template)
        self.assertEqual(self.path.read_text(encoding="utf-8"), filled)
        # 근거를 메시지에 담아야 사용자가 보고 판단할 수 있다
        self.assertIn("filled_by: vision", str(cm.exception))
        self.assertIn("확인 칸", str(cm.exception))
        self.assertIn("종료 메모", str(cm.exception))

    def test_손대지_않은_템플릿은_다시_낸다(self):
        """명세를 고친 뒤 다시 뽑는 평범한 경로. 잃을 것이 없다."""
        self.path.write_text(self.template, encoding="utf-8")
        result = record.write_record(self.path, self.template + "\n### T99 · 새 표\n")
        self.assertEqual(result["status"], "regenerated")
        self.assertIn("새 표", self.path.read_text(encoding="utf-8"))

    def test_force_는_백업을_먼저_남긴다(self):
        """사용자가 되돌려 달라고 답한 경우에도 원본을 지우지 않는다."""
        filled = self._filled()
        self.path.write_text(filled, encoding="utf-8")
        result = record.write_record(self.path, self.template, force=True)
        self.assertEqual(result["status"], "overwritten")
        self.assertEqual(result["backup"].read_text(encoding="utf-8"), filled)
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.template)

    def test_확인_칸_하나만_채워도_지킨다(self):
        text, filled = _fill_first_blank_row(self.template)
        self.assertEqual(filled, 1)               # 진리표의 확인 칸 하나
        self.assertEqual(record.record_marks(text, self.template), ["확인 칸 1개"])

    def test_filled_by_만_적혀_있어도_지킨다(self):
        """확인 칸보다 프론트매터를 먼저 바꾼 기록도 사람 손이 닿은 것이다."""
        text = self.template.replace("filled_by: ~", "filled_by: hand")
        self.assertEqual(record.record_marks(text, self.template),
                         ["프론트매터 `filled_by: hand`"])

    def test_미기입은_채운_것으로_보지_않는다(self):
        """주석의 보기를 그대로 옮겨 적은 것뿐이다."""
        text = self.template.replace("filled_by: ~", "filled_by: 미기입")
        self.assertEqual(record.record_marks(text, self.template), [])

    def test_갓_파생한_템플릿에는_흔적이_없다(self):
        """고정 산문이 `실험을 진행하지 않았음` 을 설명한다 — 본문에서 통으로
        세면 손대지 않은 템플릿이 채워진 것으로 보인다."""
        self.assertEqual(record.record_marks(self.template, self.template), [])
        self.assertEqual(record.record_marks(self.template), [])

    def test_스텝표_기록_칸도_지킨다(self):
        """스텝표에는 확인 열이 없다 — 명세가 비워 둔 칸이 기록 칸이라 템플릿과
        견주지 않으면 채워진 것을 알 수 없다(실험02 는 확인 칸이 0개다)."""
        template = derive_record(parse_spec(ROOT / "tests/fixtures/spec_capture.md"))
        text, filled = _fill_first_blank_row(template)
        self.assertEqual(filled, 5)               # S1 행의 빈 열 다섯
        self.assertEqual(record.record_marks(text, template), ["기록 칸 5개"])

    def test_파형_캡션과_스케치도_지킨다(self):
        """실험02 는 진리표도 스텝표도 없이 파형만 있었다. 칸으로는 안 잡힌다."""
        template = derive_record(parse_spec(ROOT / "tests/fixtures/spec_capture.md"))
        self.assertEqual(record.record_marks(template, template), [])
        text = template.replace("- 캡션:", "- 캡션: 계단 10개, 리셋 1회")
        self.assertEqual(record.record_marks(text, template), ["메모·캡션 줄 1개"])
        text = template.replace("  스케치 — 파형을 여기에 그린다",
                                "  스케치 — 파형을 여기에 그린다\n  _/‾|_/‾|")
        self.assertEqual(record.record_marks(text, template), ["스케치 1줄"])

    def test_깨진_프론트매터는_보호_쪽으로_기운다(self):
        """판정할 수 없는 파일을 조용히 덮는 것보다 시끄럽게 멈추는 게 낫다."""
        self.path.write_text("---\nfilled_by: hand\n\n# 기록\n", encoding="utf-8")
        with self.assertRaises(record.RecordExistsError):
            record.write_record(self.path, self.template)

    def test_백업_이름이_같은_초에도_겹치지_않는다(self):
        now = datetime.datetime(2026, 9, 20, 14, 31, 2)
        self.path.write_text(self._filled(), encoding="utf-8")
        first = record.write_record(self.path, self.template, force=True, now=now)
        self.path.write_text(self._filled(), encoding="utf-8")
        second = record.write_record(self.path, self.template, force=True, now=now)
        self.assertNotEqual(first["backup"], second["backup"])
        self.assertTrue(first["backup"].exists())
        self.assertTrue(second["backup"].exists())


class 승인본기록은_그대로다(unittest.TestCase):
    """저장소에 이미 있는 세 기록은 전부 사람이 채운 것이다. 파생이 이것들을
    덮으려 하면 반드시 막혀야 한다 — 가드의 판정 대상이 실물이다."""

    def test_승인본_셋이_모두_보호된다(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for n in (1, 2, 3):
            with self.subTest(experiment=n):
                folder = ROOT / config.experiment_dir(n) / "체크리스트"
                template = derive_record(parse_spec(folder / "명세.md"))
                text = (folder / "기록.md").read_text(encoding="utf-8")
                self.assertTrue(record.record_marks(text, template),
                                "채워진 기록인데 흔적을 못 찾았다")
                # 사본에 대고 시험한다 — 가드가 깨진 판에서 이 테스트가
                # 승인본을 날려 버리면 회귀 테스트가 사고의 공범이 된다
                copy = Path(tmp.name) / f"기록{n}.md"
                copy.write_text(text, encoding="utf-8")
                with self.assertRaises(record.RecordExistsError):
                    record.write_record(copy, template)
                self.assertEqual(copy.read_text(encoding="utf-8"), text)
