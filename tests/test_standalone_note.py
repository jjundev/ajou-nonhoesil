import shutil
import urllib.parse
import pytest

from scripts.lab import standalone_note as sn

PAGE = """<html><head><meta charset="utf-8">
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


# --- 문제설명 · 다실험 zip · Windows 호환 -------------------------------------

import re
import unicodedata
import zipfile


def _problem_page(note):
    (note / "실험99_문제설명.html").write_text(
        '<html><head><meta charset="utf-8"></head><body>'
        '<a class="topic" href="실험99_실험설명.html#t-decoder">디코더</a>'
        '<a href="#local">로컬</a></body></html>', encoding="utf-8")


def test_problem_kind_sibling_fragment_link_becomes_span(note):
    _problem_page(note)
    html = sn.build(note, "문제설명")
    assert sn.leftovers(html) == []
    assert '<span class="topic">디코더</span>' in html
    assert '<a href="#local">로컬</a>' in html


def test_linked_sibling_is_rewired_to_standalone_file(note):
    _problem_page(note)
    html = sn.build(note, "문제설명", linked={"실험설명"})
    assert sn.leftovers(html) == []
    name = "%EC%8B%A4%ED%97%9899_%EC%8B%A4%ED%97%98%EC%84%A4%EB%AA%85_standalone.html"
    assert f'href="{name}#t-decoder"' in html
    assert "<span" not in html


@pytest.fixture
def two_notes(note, tmp_path, monkeypatch):
    _problem_page(note)
    d = tmp_path / "실험98"
    shutil.copytree(note, d)
    for p in d.glob("실험99_*"):
        p.rename(d / p.name.replace("실험99", "실험98"))
    for p in d.glob("실험98_*.html"):
        p.write_text(p.read_text(encoding="utf-8").replace("실험99", "실험98"), encoding="utf-8")
    monkeypatch.setattr(sn, "NOTES", tmp_path)
    return tmp_path


def test_multi_experiment_makes_windows_safe_zip(two_notes, tmp_path):
    out = tmp_path / "out"
    rc = sn.main(["실험99", "실험98", "--kind", "all", "--out", str(out)])
    assert rc == 0
    assert not list(out.glob("*.html"))
    zp = out / "복습노트_standalone.zip"
    with zipfile.ZipFile(zp) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert sorted(names) == [
            "실험98/실험98_문제설명_standalone.html", "실험98/실험98_실험설명_standalone.html",
            "실험99/실험99_문제설명_standalone.html", "실험99/실험99_실험설명_standalone.html"]
        for info in z.infolist():
            assert unicodedata.is_normalized("NFC", info.filename)
            assert info.flag_bits & 0x800          # UTF-8 이름 플래그
            assert not re.search(r'[<>:"|?*\\]', info.filename)
            assert len(info.filename) <= 200
        assert not any("__MACOSX" in n or ".DS_Store" in n for n in names)
        for n in names:
            html = z.read(n).decode("utf-8")
            assert "charset" in html[:2048].lower()
            assert sn.leftovers(html) == []
        prob = z.read("실험99/실험99_문제설명_standalone.html").decode("utf-8")
        target = urllib.parse.unquote(re.search(r'href="([^"#]+_standalone\.html)#t-decoder"', prob).group(1))
        assert f"실험99/{target}" in names


def test_single_experiment_stays_loose_files(two_notes, tmp_path):
    out = tmp_path / "out"
    assert sn.main(["실험99", "--kind", "all", "--out", str(out)]) == 0
    assert sorted(p.name for p in out.iterdir()) == [
        "실험99_문제설명_standalone.html", "실험99_실험설명_standalone.html"]


def test_nfd_argument_is_normalized(two_notes, tmp_path):
    out = tmp_path / "out"
    nfd = unicodedata.normalize("NFD", "실험99")
    assert sn.main([nfd, "--out", str(out)]) == 0
    assert [p.name for p in out.iterdir()] == ["실험99_실험설명_standalone.html"]


def test_all_skips_missing_kind_and_names_it(two_notes, tmp_path, capsys):
    (two_notes / "실험98" / "실험98_문제설명.html").unlink()
    out = tmp_path / "out"
    assert sn.main(["all", "--kind", "문제설명", "--out", str(out)]) == 0
    assert "실험98" in capsys.readouterr().out
    with zipfile.ZipFile(out / "복습노트_standalone.zip") as z:
        assert z.namelist() == ["실험99/실험99_문제설명_standalone.html"]


def test_named_missing_kind_is_error(two_notes, tmp_path):
    with pytest.raises(SystemExit):
        sn.main(["실험99", "--kind", "기출풀이", "--out", str(tmp_path / "o")])


# --- 범위 인자 · zip 자체 검사 ------------------------------------------------

def test_range_argument_expands(two_notes, tmp_path):
    out = tmp_path / "out"
    assert sn.main(["실험98~99", "--out", str(out)]) == 0
    with zipfile.ZipFile(out / "복습노트_standalone.zip") as z:
        assert z.namelist() == ["실험98/실험98_실험설명_standalone.html",
                                "실험99/실험99_실험설명_standalone.html"]


def test_expand_forms():
    assert sn._expand(["실험01~05"]) == ["실험01", "실험02", "실험03", "실험04", "실험05"]
    assert sn._expand(["실험01~실험03", "실험06"]) == ["실험01", "실험02", "실험03", "실험06"]
    assert sn._expand(["all"]) == ["all"]
    assert sn._expand(["실험5~3"]) == ["실험5~3"]  # 거꾸로는 그대로 두어 '없는 폴더' 로 걸린다


def test_main_prints_zip_check_line(two_notes, tmp_path, capsys):
    assert sn.main(["실험99", "실험98", "--kind", "all", "--out", str(tmp_path / "o")]) == 0
    assert "zip 검사 통과" in capsys.readouterr().out


def test_check_zip_catches_broken_link_and_bad_name(tmp_path):
    zp = tmp_path / "x.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("실험01/실험01_문제설명_standalone.html",
                   '<meta charset="utf-8"><a href="실험01_실험설명_standalone.html#t">x</a>'.encode())
        z.writestr(unicodedata.normalize("NFD", "실험01/나쁜:이름.html"), b"<meta charset=utf-8>")
    problems = sn.check_zip(zp)[1]
    joined = "\n".join(problems)
    assert "실험01_실험설명_standalone.html" in joined   # 끊긴 링크
    assert "NFC" in joined and "금지 문자" in joined
