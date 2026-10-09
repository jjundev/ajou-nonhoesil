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


def _page_pdf(tmp_path, name, texts=(), images=()):
    """texts: (x, y, 글) / images: (x0, y0, x1, y1). A4 가로 한 쪽짜리 PDF."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=841.92, height=594.96)
    for x, y, s in texts:
        page.insert_text((x, y), s, fontname="korea", fontsize=8)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    pix.clear_with(200)
    for rect in images:
        page.insert_image(pymupdf.Rect(*rect), pixmap=pix)
    path = tmp_path / name
    doc.save(path)
    return path


def test_content_check_flags_raw_latex(tmp_path):
    # 2026-10-09 실험02 해설지 14쪽 전부에 KaTeX 가 안 돌아 원문이 찍혔다
    raw = _page_pdf(tmp_path, "raw.pdf", texts=[(50, 100, r"조건 $V_{CC}=5\,\mathrm{V}$")])
    assert "원문 LaTeX" in " ".join(wp.check_pdf_content(raw))
    sub = _page_pdf(tmp_path, "sub.pdf", texts=[(50, 100, "출력 $Y_2$ 를 구한다")])
    assert wp.check_pdf_content(sub)
    # 렌더된 KaTeX 는 구분자 없이 글자·MathML 주석만 남는다
    ok = _page_pdf(tmp_path, "ok.pdf", texts=[(50, 100, "V CC = 5 V"), (50, 120, r"V_{CC}=5\,\mathrm{V}")])
    assert wp.check_pdf_content(ok) == []


def test_content_check_flags_figure_running_under_answer_box(tmp_path):
    # 실험05 11쪽: 풀이 그림 하단(540)이 '답' 상자 상단(512)보다 아래라 잘렸다
    cut = _page_pdf(tmp_path, "cut.pdf", texts=[(300, 520, "답")], images=[(320, 380, 520, 540)])
    problems = wp.check_pdf_content(cut)
    assert problems and "1쪽" in problems[0] and "답" in problems[0]
    fine = _page_pdf(tmp_path, "fine.pdf", texts=[(300, 520, "답")],
                     images=[(320, 300, 520, 500), (379, 59, 672, 265)])
    assert wp.check_pdf_content(fine) == []
    # 점 격자 배경은 쪽 전체 크기 그림으로 찍힌다 — 그림으로 치지 않는다
    grid = _page_pdf(tmp_path, "grid.pdf", texts=[(300, 520, "답")], images=[(0, 0, 841.92, 594.96)])
    assert wp.check_pdf_content(grid) == []


def test_export_prints_after_the_page_script_finishes(tmp_path, monkeypatch):
    # 인쇄가 맞춤(fitSolution)을 기다리지 않으면 1단·글자 1.0 상태가 찍혀 그림이 '답' 상자 밑으로 간다
    seen = {}
    def fake_html_to_pdf(src, out, **kw):
        seen.update(kw)
        raise wp.PdfError("stop")
    monkeypatch.setattr(wp, "html_to_pdf", fake_html_to_pdf)
    monkeypatch.setattr(wp, "dom_state", lambda src: ("true", ""))
    d = wp.NOTES / "실험05"
    if not (d / "실험05_기출풀이.html").exists():
        pytest.skip("실험05 없음")
    with pytest.raises(wp.PdfError):
        wp.export(d, "기출풀이", tmp_path)
    assert seen.get("virtual_time_budget", 0) >= wp.BUDGET_MS


def test_real_answer_sheet_has_rendered_math_and_uncut_figures(tmp_path):
    # 실험02 는 수식 193개·풀이 그림 14장으로 두 결함이 다 드러난 해설지다
    d = wp.NOTES / "실험02"
    if not (d / "실험02_기출풀이.html").exists():
        pytest.skip("실험02 없음")
    assert wp.main(["실험02", "--kind", "기출풀이", "--out", str(tmp_path)]) == 0
    assert wp.check_pdf_content(tmp_path / "실험02_기출풀이.pdf") == []
