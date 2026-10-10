import pytest

from scripts.lab import standalone_note as sn

PAGE = """<html><head>
<link rel="stylesheet" href="assets/a.css">
<script defer src="assets/k.js"></script>
<script defer src="assets/r.js"
  onload="render({d:&quot;$&quot;})"></script>
</head><body>
<a href="실험99_기출풀이.html">풀이</a>
<img src="figures/f.svg">
<script src="assets/w.js"></script>
</body></html>"""


@pytest.fixture
def note(tmp_path):
    d = tmp_path / "실험99"
    (d / "assets").mkdir(parents=True)
    (d / "figures").mkdir()
    (d / "assets/a.css").write_text(
        "@font-face{font-family:'Pretendard';font-weight:400;src:url(F4.woff2) format('woff2'),url(F4.woff) format('woff');}"
        "@font-face{font-family:'Pretendard';font-weight:100;src:url(F1.woff2) format('woff2');}"
        "body{background:url(bg.png)}")
    for n in ("F4.woff2", "F1.woff2", "bg.png"):
        (d / "assets" / n).write_bytes(b"x")
    (d / "assets/k.js").write_text("var K=1;//</script>")
    (d / "assets/r.js").write_text("var R=1;")
    (d / "assets/w.js").write_text("var W=1;")
    (d / "figures/f.svg").write_text("<svg/>")
    (d / "실험99_실험설명.html").write_text(PAGE, encoding="utf-8")
    return d


def test_build_is_standalone(note):
    html = sn.build(note, "실험설명")
    assert sn.leftovers(html) == []
    assert "assets/" not in html and "figures/" not in html


def test_defer_scripts_move_after_body_with_onload(note):
    html = sn.build(note, "실험설명")
    assert html.index("var W=1") < html.index("var K=1") < html.index("var R=1")
    assert html.index('render({d:"$"})') > html.index("var R=1")
    assert html.index("var K=1") < html.index("</body>")
    assert r"//<\/script>" in html


def test_sibling_links_and_fonts(note):
    html = sn.build(note, "실험설명")
    assert "<span>풀이</span>" in html and "실험99_기출풀이.html" not in html
    assert html.count("@font-face") == 1  # 굵기 100 은 버린다
    assert "format('woff')" not in html


def test_real_note_smoke(tmp_path):
    d = sn.NOTES / "실험05"
    if not (d / "실험05_실험설명.html").exists():
        pytest.skip("실험05 없음")
    assert sn.main(["실험05", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "실험05_실험설명_standalone.html").exists()


def test_sibling_links_with_current_page_attributes(note):
    src = note/'실험99_실험설명.html'
    src.write_text(src.read_text().replace('<a href="실험99_기출풀이.html">',
        '<a class="document" aria-current="page" href="실험99_기출풀이.html">'))
    result = sn.build(note, '실험설명')
    assert sn.leftovers(result) == []
    assert '<span class="document" aria-current="page">풀이</span>' in result


def test_standalone_keeps_topic_hash_links(note):
    src = note/'실험99_실험설명.html'
    src.write_text(src.read_text().replace('</body>', '<a href="#t-start">토픽</a></body>'))
    assert '<a href="#t-start">토픽</a>' in sn.build(note, '실험설명')
