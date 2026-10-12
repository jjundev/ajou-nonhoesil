from pathlib import Path
import shutil

import pytest

from scripts.lab.review_pack.manifest import output_names

PACKS = Path('복습노트')


def old_html():
    return '''<html><style>
    /* ---------- 한 화면에 하나씩 (JS가 켤 때만) ---------- */
    </style><body><aside id="panel-left">
        <p class="panel-meta">읽은 토픽 <b id="progress-n">0</b> / <span id="progress-total">0</span></p>
        <div class="progress" aria-hidden="true"><span id="progress-bar"></span></div>
        <nav class="toc" aria-label="목차"><a href="실험03_실험설명.html">실험 설명</a><a href="실험03_기출풀이.html">기출 풀이</a><a href="실험03_기출문제.html">기출 문제</a><a href="#learning">실험 이해</a></nav>
    </aside><main><section id="learning"><article class="topic" id="t-half-adder"><h3>반가산기</h3>본문 &amp; 수식</article></section></main>
    <script>const KEY = 'od-note-read:logic-lab-03';
    e.target.closest('.toc a');
      // 목차: 기존 섹션 목록
        const sec = document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
      function indexFor(hash) {
        const id = decodeURIComponent((hash || '').replace(/^#/, ''));
      }
    </script></body></html>'''


def test_upgrade_preserves_main_ids_and_storage():
    from scripts.lab.review_pack.navigation_upgrade import upgrade_navigation_html
    old = old_html()
    upgraded = upgrade_navigation_html(old, names=output_names(3, review_presentation_version=2), kind='note')
    assert old[old.index('<main>'):old.index('</main>')+7] in upgraded
    assert "const KEY = 'od-note-read:logic-lab-03';" in upgraded
    assert 'class="pack-nav"' not in upgraded
    assert 'id="progress-n"' not in upgraded
    assert '<a href="#learning">' not in upgraded
    assert '<a href="#t-half-adder">' in upgraded
    assert '<h3 class="nav-label">이 페이지 목차</h3>' not in upgraded
    from scripts.lab.review_pack.html2md import Parser
    parser = Parser(); parser.feed(upgraded)
    assert len([n for n in parser.root.walk() if n.tag == 'a' and n.attrs.get('aria-current') == 'page']) == 0
    assert "e.target.closest('.toc a')" in upgraded


def test_upgrade_is_idempotent():
    from scripts.lab.review_pack.navigation_upgrade import upgrade_navigation_html
    names = output_names(3, review_presentation_version=2)
    first = upgrade_navigation_html(old_html(), names=names, kind='note')
    assert upgrade_navigation_html(first, names=names, kind='note') == first


def pack_copy(tmp_path, name='실험03'):
    folder = tmp_path/name
    shutil.copytree(PACKS/name, folder)
    (folder/f'{name}_실험설명.html').write_text(old_html())
    return folder


def test_dry_run_writes_nothing(tmp_path):
    from scripts.lab.review_pack.navigation_upgrade import upgrade_packs
    folder = pack_copy(tmp_path)
    before = {p: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    assert upgrade_packs([folder])
    assert before == {p: p.read_bytes() for p in before}


def test_unknown_page_aborts_batch_before_writes(tmp_path):
    from scripts.lab.review_pack.navigation_upgrade import upgrade_packs
    first, second = pack_copy(tmp_path), pack_copy(tmp_path, '실험04')
    # An unknown page must not be silently treated as a workbook.
    (second/'실험04_실험설명.html').write_text('<html>unknown</html>')
    before = (first/'실험03_실험설명.html').read_bytes()
    with pytest.raises(ValueError):
        upgrade_packs([first, second], apply=True, backup_root=tmp_path/'backup')
    assert (first/'실험03_실험설명.html').read_bytes() == before
    assert not (tmp_path/'backup').exists()


def test_apply_creates_backup_and_preserves_workbooks(tmp_path):
    from scripts.lab.review_pack.navigation_upgrade import upgrade_packs
    folder = pack_copy(tmp_path)
    source = (folder/'실험03_실험설명.html').read_bytes()
    workbooks = {p: p.read_bytes() for p in folder.glob('*_기출*.html')}
    changed = upgrade_packs([folder], apply=True, backup_root=tmp_path/'backup')
    assert folder/'실험03_실험설명.html' in changed
    assert (tmp_path/'backup/실험03/실험03_실험설명.html').read_bytes() == source
    assert all(p.read_bytes() == b for p, b in workbooks.items())
    assert upgrade_packs([folder]) == []


def test_all_published_notes_have_separate_navigation():
    from scripts.lab.review_pack.html2md import Parser
    from scripts.lab.review_pack.navigation import check_navigation
    for number in range(1,7):
        folder = PACKS/f'실험{number:02d}'
        path = folder/(folder.name+'_실험설명.html')
        assert path.is_file()
        parser = Parser(); parser.feed(path.read_text())
        assert check_navigation(parser.root, path.name) == []
