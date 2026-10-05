"""tests/test_merge_report.py

TDD tests for scripts/lab/merge_report.py:
- Output filename formatting (underscore convention)
- Body PDF auto-discovery and filtering
- Cover detection and on-demand generation gate
- Lossless PDF merging with pypdf
- Validation of merged PDF
"""

import tempfile
import unittest
from pathlib import Path

import pypdf

from scripts.lab import config
from scripts.lab.merge_report import (
    output_filename,
    find_body_pdf,
    merge_report_pdf,
    verify_merged_pdf,
    ensure_cover_pdf,
)


def _blank_pdf(suffix: str, pages: int) -> Path:
    """빈 쪽 PDF 를 임시 파일로 만들고 **닫은 뒤** 경로를 돌려준다.
    Windows 는 열려 있는 파일을 지우지 못하므로 `with` 안에서 넘기면
    `clean_body` 의 삭제가 조용히 실패한다."""
    fd, name = tempfile.mkstemp(suffix=suffix)
    writer = pypdf.PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595.27, height=841.89)
    with open(fd, "wb") as f:
        writer.write(f)
    return Path(name)

class TestOutputFilename(unittest.TestCase):
    def test_replaces_spaces_with_underscores(self):
        self.assertEqual(
            output_filename(1, "Basic Gates", "예비보고서"),
            "실험1_Basic_Gates_예비보고서.pdf",
        )

    def test_handles_korean_title(self):
        self.assertEqual(
            output_filename(2, "CMOS 연산 및 전압 특성", "결과보고서"),
            "실험2_CMOS_연산_및_전압_특성_결과보고서.pdf",
        )

    def test_handles_leading_trailing_whitespace(self):
        self.assertEqual(
            output_filename(3, "  Boolean Algebra  ", "예비보고서"),
            "실험3_Boolean_Algebra_예비보고서.pdf",
        )


class TestFindBodyPdf(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / "output").mkdir()
        (self.dir / "체크리스트").mkdir()
        (self.dir / "결선도").mkdir()

    def _touch(self, rel_path: str) -> Path:
        p = self.dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"%PDF-1.4 dummy")
        return p

    def test_finds_notion_uuid_export_pdf(self):
        target = self._touch("9e73816f-9564-4e49-aabf-1b43ebced8da_실험1_Basic_Gates_예비보고서.pdf")
        self._touch("output/실험1 Basic Gates 예비보고서 표지.pdf")
        self._touch("output/실험01_손그림결선도_최종통합본.pdf")
        self._touch("체크리스트/체크리스트.pdf")

        found = find_body_pdf(self.dir, kind="예비보고서")
        self.assertEqual(found.resolve(), target.resolve())

    def test_ignores_covers_and_diagrams_when_body_missing(self):
        self._touch("output/실험1 Basic Gates 예비보고서 표지.pdf")
        self._touch("output/실험01_손그림결선도_최종통합본.pdf")
        self._touch("체크리스트/체크리스트.pdf")

        with self.assertRaises(FileNotFoundError):
            find_body_pdf(self.dir, kind="예비보고서")

    def test_raises_on_ambiguous_multiple_candidates(self):
        self._touch("export1_예비보고서.pdf")
        self._touch("export2_예비보고서.pdf")

        with self.assertRaises(RuntimeError) as ctx:
            find_body_pdf(self.dir, kind="예비보고서")
        self.assertIn("복수의 본문 PDF", str(ctx.exception))


class TestPdfMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _create_sample_pdf(self, path: Path, page_texts: list[str]) -> Path:
        writer = pypdf.PdfWriter()
        for text in page_texts:
            writer.add_blank_page(width=595.27, height=841.89)  # A4 pt
        with open(path, "wb") as f:
            writer.write(f)
        return path

    def test_merges_cover_and_body_in_exact_order(self):
        cover_pdf = self._create_sample_pdf(self.dir / "cover.pdf", ["Cover Page"])
        body_pdf = self._create_sample_pdf(self.dir / "body.pdf", ["Page 1", "Page 2", "Page 3"])
        merged_pdf = self.dir / "merged.pdf"

        out = merge_report_pdf(cover_pdf, body_pdf, merged_pdf)
        self.assertTrue(out.exists())

        reader = pypdf.PdfReader(out)
        self.assertEqual(len(reader.pages), 4)

        # Verification function passes
        stats = verify_merged_pdf(out, expected_pages=4)
        self.assertEqual(stats["pages"], 4)
        self.assertTrue(stats["valid"])

    def test_verify_raises_on_page_count_mismatch(self):
        pdf = self._create_sample_pdf(self.dir / "test.pdf", ["P1", "P2"])
        with self.assertRaises(ValueError):
            verify_merged_pdf(pdf, expected_pages=3)


class TestEnsureCover(unittest.TestCase):
    def test_reuses_existing_matching_cover(self):
        root = config.find_project_root(Path("."))
        exp_dir = root / config.experiment_dir(1)
        from scripts.lab.spec_parser import parse_spec
        spec = parse_spec(exp_dir / "체크리스트/명세.md")
        cover = ensure_cover_pdf(exp_dir, spec, "예비보고서")
        self.assertTrue(cover.is_file())
        self.assertIn("표지.pdf", cover.name)


class TestIntegration(unittest.TestCase):
    def test_merge_lab_report_with_explicit_body_cleans_by_default(self):
        from scripts.lab.merge_report import merge_lab_report
        root = config.find_project_root(Path("."))
        exp_dir = root / config.experiment_dir(1)
        tmp_path = _blank_pdf("_notion_export_예비보고서.pdf", pages=3)
        self.addCleanup(tmp_path.unlink, missing_ok=True)
        out = merge_lab_report(1, kind="예비보고서", body_path=tmp_path)
        self.assertTrue(out.is_file())
        self.assertEqual(out.name, "실험1_Basic_Gates_예비보고서.pdf")
        reader = pypdf.PdfReader(str(out))
        self.assertEqual(len(reader.pages), 4)  # 1 cover + 3 body
        # clean_body=True 가 기본이므로 원본 파일이 자동 삭제되어야 함
        self.assertFalse(tmp_path.exists())

    def test_merge_lab_report_clean_body_false_keeps_file(self):
        from scripts.lab.merge_report import merge_lab_report
        root = config.find_project_root(Path("."))
        exp_dir = root / config.experiment_dir(1)
        tmp_path = _blank_pdf("_notion_export_keep_예비보고서.pdf", pages=2)
        self.addCleanup(tmp_path.unlink, missing_ok=True)
        out = merge_lab_report(1, kind="예비보고서", body_path=tmp_path, clean_body=False)
        self.assertTrue(out.is_file())
        self.assertTrue(tmp_path.is_file())



if __name__ == "__main__":
    unittest.main()

