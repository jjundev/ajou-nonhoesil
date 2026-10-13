"""저장 규칙: 복습노트 실험 폴더 루트에는 .html·.pdf 와 숨김 `.pack/` 만 둔다. md 도 `.pack/` 안이다."""
import hashlib
import json
import re
import shutil
from pathlib import Path
import pytest
from scripts.lab import migrate_pack_layout as mig
from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.manifest import DATA, data_url, link_data, strip_data
from scripts.lab.review_pack.pack_md import md_path, rebase_link, to_data_frame, to_root_frame

NOTES = Path('복습노트')
PACKS = sorted(p for p in NOTES.glob('실험[0-9][0-9]') if p.is_dir())
MD_NAMES = ('검증결과.md', '원문과_저작안내.md', '출처와_문항목록.md')

def tree(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and p.name != '.DS_Store'}

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

def _old_layout(pack):
    """발행본을 2026-10-13 이전 배치(루트 md, `자료/`)로 되돌린다 — 이전 도구 검사용."""
    (pack / DATA).rename(pack / '자료')
    for html in list(pack.glob('*.html')) + list((pack / '자료/problem-explanations').rglob('*.html')):
        html.write_text(re.sub(r'''(?<=["'(])\.pack/''', '자료/', html.read_text(encoding='utf-8')), encoding='utf-8')
    manifest = json.loads((pack / '자료/manifest.json').read_text(encoding='utf-8'))
    for name in [n[len(DATA) + 1:] for n in manifest['generated_files'] if n.startswith(DATA + '/') and n.count('/') == 1 and n.endswith('.md')]:
        text = to_root_frame((pack / '자료' / name).read_text(encoding='utf-8')).replace('](.pack/', '](자료/')
        (pack / name).write_text(text, encoding='utf-8')
        (pack / '자료' / name).unlink()
    manifest['generated_files'] = sorted(
        '자료' + n[len(DATA):] if n.startswith(DATA + '/') and not (n.count('/') == 1 and n.endswith('.md'))
        else n[len(DATA) + 1:] if n.startswith(DATA + '/') else n for n in manifest['generated_files'])
    (pack / '자료/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

def test_migration_restores_published_pack_byte_for_byte(tmp_path):
    pack = tmp_path / '실험05'
    shutil.copytree(NOTES / '실험05', pack)
    published = tree(pack)
    _old_layout(pack)
    assert (pack / '실험05_기출풀이.md').is_file() and not (pack / DATA).exists()
    assert '이동' in mig.migrate(pack, apply=False)[0] and (pack / '자료').is_dir()   # dry-run 은 손대지 않는다
    lines = mig.migrate(pack, apply=True)
    assert '검사 통과' in lines[-1]
    assert tree(pack) == published

def test_migration_is_noop_on_migrated_packs():
    for pack in PACKS:
        before = tree(pack)
        lines = mig.migrate(pack, apply=True)
        assert '이미' in lines[0]
        assert tree(pack) == before
