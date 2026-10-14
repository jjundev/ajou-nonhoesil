"""저장 규칙: 복습노트 실험 폴더 루트에는 .html·.pdf 와 숨김 `.pack/` 만 둔다. md 도 `.pack/` 안이다."""
import shutil
from pathlib import Path
import pytest
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.manifest import DATA, data_url, link_data, strip_data
from scripts.lab.review_pack.pack_md import md_path, rebase_link, to_data_frame, to_root_frame

NOTES = Path('복습노트')
PACKS = sorted(p for p in NOTES.glob('실험[0-9][0-9]') if p.is_dir())
MD_NAMES = ('검증결과.md', '원문과_저작안내.md', '출처와_문항목록.md')

def test_link_helpers():
    assert DATA == '.pack'
    assert data_url('figures/a.svg') == '.pack/figures/a.svg'
    assert strip_data('.pack/figures/a.svg') == 'figures/a.svg'
    assert strip_data('figures/a.svg') == 'figures/a.svg'
    text = '<img src="figures/a.svg"><img src=\'assets/b.png\'><a href="실험05_실험설명.html#x">'
    assert link_data(text) == '<img src=".pack/figures/a.svg"><img src=\'.pack/assets/b.png\'><a href="실험05_실험설명.html#x">'
    assert link_data(link_data(text)) == link_data(text)      # 두 번 달아도 접두가 겹치지 않는다

def test_md_links_move_into_pack_frame():
    assert md_path('복습노트/실험05', 'a.md') == Path('복습노트/실험05/.pack/a.md')
    assert rebase_link('.pack/figures/a.png') == 'figures/a.png'
    assert rebase_link('%EC%9E%90%EB%A3%8C/figures/a.png', prefixes=('자료/',)) == 'figures/a.png'
    assert rebase_link('실험05_기출풀이.md#q1') == '실험05_기출풀이.md#q1'
    assert rebase_link('../../강의노트/a.pdf#page=3') == '../../../강의노트/a.pdf#page=3'
    assert rebase_link('#t-start') == '#t-start'
    assert rebase_link('https://example.com/x') == 'https://example.com/x'
    text = ('[a](.pack/figures/a.png) ![b](실험05_실험설명.md#t) [c](../../from_the_past/x.pdf) '
            '[d](#q) [e](https://x.org/y) [f]()')
    moved = to_data_frame(text)
    assert moved == ('[a](figures/a.png) ![b](실험05_실험설명.md#t) [c](../../../from_the_past/x.pdf) '
                     '[d](#q) [e](https://x.org/y) [f]()')
    assert to_root_frame(moved) == text

@pytest.mark.parametrize('pack', PACKS, ids=lambda p: p.name)
def test_pack_root_holds_only_html_pdf_and_pack(pack):
    for entry in pack.iterdir():
        if entry.name == '.DS_Store':
            continue
        if entry.is_dir():
            assert entry.name == DATA, f'{entry.name}/ 는 {DATA}/ 안에 둔다'
        else:
            assert entry.suffix in {'.html', '.pdf'}, f'{entry.name} 는 {DATA}/ 안에 둔다'
    assert (pack / DATA / 'manifest.json').is_file()
    for name in ('assets', 'evidence', 'figures'):
        assert (pack / DATA / name).is_dir()
    base = pack.name
    for name in [f'{base}_{k}.md' for k in ('실험설명', '기출문제', '기출풀이', '문제설명')] + list(MD_NAMES):
        assert (pack / DATA / name).is_file(), name

@pytest.mark.parametrize('pack', PACKS, ids=lambda p: p.name)
def test_published_pack_passes_checks(pack):
    assert check_pack(pack) == []

@pytest.mark.parametrize('stray', ['실험05_실험설명.md', '메모.txt', '자료/'])
def test_check_rejects_anything_but_html_pdf_at_root(tmp_path, stray):
    pack = tmp_path / '실험05'
    shutil.copytree(NOTES / '실험05', pack)
    (pack / '.DS_Store').write_bytes(b'')                      # 점파일은 운영체제 몫이라 보지 않는다
    assert check_pack(pack) == []
    if stray.endswith('/'):
        (pack / stray).mkdir()
    else:
        (pack / stray).write_text('x', encoding='utf-8')
    assert f'Pack file outside {DATA}/: {stray.rstrip("/")}' in check_pack(pack)
