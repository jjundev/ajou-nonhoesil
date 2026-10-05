import pytest

from scripts.lab import workbook_pdf as wp


def test_check_pdf_reports_page_count_and_size(tmp_path):
    from pypdf import PdfWriter
    pdf = tmp_path / "a.pdf"
    w = PdfWriter()
    for _ in range(2):
        w.add_blank_page(width=841.92, height=594.96)
    w.write(pdf)
    assert wp.check_pdf(pdf, 2) == []
    assert wp.check_pdf(pdf, 3)               # 쪽이 모자람
    assert wp.check_pdf(pdf, 1, exact=False) == []   # 해설지는 이상이면 된다
    assert wp.check_pdf(pdf, 1)               # 문제지는 정확히 같아야 한다
    bad = tmp_path / "b.pdf"
    w = PdfWriter(); w.add_blank_page(width=595, height=842); w.write(bad)
    assert "크기" in wp.check_pdf(bad, 1)[0]


def test_real_note_smoke(tmp_path):
    d = wp.NOTES / "실험05"
    if not (d / "실험05_기출문제.html").exists():
        pytest.skip("실험05 없음")
    assert wp.main(["실험05", "--kind", "기출문제", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "실험05_기출문제.pdf").exists()
