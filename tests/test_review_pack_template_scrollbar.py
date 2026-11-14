import re
from pathlib import Path
import pytest

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')
TOKEN = re.compile(r'--scroll: #[0-9a-f]{6}; --scroll-hover: #[0-9a-f]{6};')
LIGHT = '--scroll: #c9d0db; --scroll-hover: #9aa3b2;'
DARK = '--scroll: #3f414b; --scroll-hover: #5b5e6a;'


def check_scrollbar(text, cards):
    assert len(TOKEN.findall(text)) == 3
    assert text.count(LIGHT) == 1 and text.count(DARK) == 2
    assert '.content::-webkit-scrollbar-thumb, .panel-inner::-webkit-scrollbar-thumb { background: var(--scroll); border-radius: 8px; border: 2px solid var(--bg); }' in text
    assert '.content::-webkit-scrollbar-thumb:hover, .panel-inner::-webkit-scrollbar-thumb:hover { background: var(--scroll-hover); }' in text
    assert '{ .content, .panel-inner { scrollbar-width: thin; scrollbar-color: var(--scroll) transparent; } }' in text
    card = '.equation-card::-webkit-scrollbar-thumb, .table-card::-webkit-scrollbar-thumb { background: var(--scroll); border-radius: 8px; border: 2px solid var(--surface); }'
    assert (card in text) == cards
    assert ('{ .equation-card, .table-card { scrollbar-width: thin; scrollbar-color: var(--scroll) transparent; } }' in text) == cards


@pytest.mark.parametrize('name,cards', [('note-template.html', True), ('review-template.html', False)])
def test_템플릿_스크롤바(name, cards):
    check_scrollbar((ASSETS / name).read_text(encoding='utf-8'), cards)


@pytest.mark.parametrize('name', ['note-template.html', 'review-template.html'])
def test_다크_두_블록_모두_토큰(name):
    text = (ASSETS / name).read_text(encoding='utf-8')
    media = text[text.index(':root:not([data-theme="light"]) {'):]
    media = media[:media.index('}')]
    forced = text[text.index(':root[data-theme="dark"] {'):]
    forced = forced[:forced.index('}')]
    assert DARK in media and DARK in forced


PACKS = sorted(Path('복습노트').glob('실험0[1-6]'))
CARD_RULE = '    .table-card { margin: var(--s4) 0;'


@pytest.mark.parametrize('page', [p for f in PACKS for p in (f / f'{f.name}_실험설명.html', f / f'{f.name}_문제설명.html')], ids=str)
def test_발행물_스크롤바(page):
    text = page.read_text(encoding='utf-8')
    check_scrollbar(text, cards=CARD_RULE in text)


@pytest.mark.parametrize('folder', PACKS, ids=str)
def test_팩_템플릿_사본은_스킬과_같다(folder):
    for name in ('note-template.html', 'review-template.html', 'template-provenance.json'):
        assert (folder / '.pack/assets' / name).read_bytes() == (ASSETS / name).read_bytes()


def test_노트_상단여백과_그림_둥근모서리():
    targets = [ASSETS / 'note-template.html'] + [
        Path('복습노트') / f'실험{n:02d}' / f'실험{n:02d}_실험설명.html'
        for n in range(6, 10)
    ]
    for path in targets:
        text = path.read_text(encoding='utf-8')
        assert '.topic h3 + .layer.eli5 { margin-top: var(--s5); }' in text, path
        assert '.figure svg { width: 100%; height: auto; max-width: 560px; color: var(--ink); border-radius: var(--radius); }' in text, path
        assert '.figure img { max-width: 100%; height: auto; border-radius: var(--radius); }' in text, path
        assert '.work-board img { border-radius: var(--radius); }' in text, path
