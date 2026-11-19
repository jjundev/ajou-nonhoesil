import base64
import io
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / '.claude/skills/logic-lab-review-pack/assets/vendor/pretendard/Pretendard-SemiBold.woff2'
SVG_NS = {'s': 'http://www.w3.org/2000/svg'}
SAMPLE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 60">
<title>테스트 회로</title>
<path class="fig-ink" d="M10 10H110" fill="none" stroke-width="4"/>
<circle class="fig-dot" cx="90" cy="10" r="5" data-node="out" data-node-color="blue"/>
<text class="fig-text" x="90" y="40" data-node="out" data-node-color="blue">V<tspan baseline-shift="sub" font-size="78%">o</tspan></text>
<text class="fig-text" x="10" y="40">Ω 출</text>
</svg>'''


def test_svg_embeds_real_semibold_and_keeps_node_and_subscript():
    from fontTools.ttLib import TTFont

    from scripts.lab.review_pack.note_schematic import style_note_schematic

    styled = style_note_schematic(SAMPLE, font_path=FONT)
    tree = ET.fromstring(styled)
    assert tree.get('viewBox') == '0 0 120 60'
    assert tree.find('s:title', SVG_NS).text == '테스트 회로'
    dot, label = tree.findall(".//*[@data-node='out']")
    assert dot.get('data-node-color') == label.get('data-node-color') == 'blue'
    assert label.find('s:tspan', SVG_NS).attrib == {'baseline-shift': 'sub', 'font-size': '78%'}
    encoded = re.search(r'data:font/woff2;base64,([\w+/=]+)', styled).group(1)
    with TTFont(io.BytesIO(base64.b64decode(encoded))) as subset:
        assert subset['OS/2'].usWeightClass == 600
        assert set(map(ord, 'VoΩ출')) <= set(subset.getBestCmap())


@pytest.fixture(scope='module')
def chromium():
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as browser:
        if not Path(browser.chromium.executable_path).is_file():
            pytest.skip('Playwright Chromium is unavailable')
        with browser.chromium.launch() as instance:
            yield instance


def test_svg_embedded_as_image_follows_parent_color_scheme(chromium, tmp_path):
    from PIL import Image

    from scripts.lab.review_pack.note_schematic import style_note_schematic

    (tmp_path / 'note.svg').write_text(style_note_schematic(SAMPLE, font_path=FONT))
    page_file = tmp_path / 'note.html'
    page_file.write_text('<img src="note.svg" width="120" height="60">')
    with chromium.new_page(color_scheme='light') as page:
        page.goto(page_file.as_uri())
        page.locator('img').evaluate('img => img.decode()')
        pixels = []
        for theme in ('light', 'dark'):
            page.evaluate('(theme) => document.documentElement.style.colorScheme = theme', theme)
            shot = page.locator('img').screenshot()
            with Image.open(io.BytesIO(shot)) as img:
                background, stroke = img.getpixel((2, 2)), img.getpixel((60, 10))
                assert background != stroke
                pixels.append((background, stroke))
        assert all(a != b for a, b in zip(*pixels))


INVENTORY = {
    6: 'not-loop sr-basic-nand sr-latch-enable d-latch jk-latch tff-from-jk-note',
    7: 'shift internal',
    8: 'ripple-block sync-block decoder-and 7490-block',
    9: 'nand-latch ram1bit ram2bit opendrain',
    10: 'opamp-inv summing network oc dac-block comparator flash',
}


def draw_schematics(experiment, target):
    import subprocess
    import sys

    source = ROOT / 'docs/learning-pack-source' / f'실험{experiment:02}'
    command = '''
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import importlib
module = importlib.import_module(sys.argv[2])
module.draw_note_schematics(Path(sys.argv[3]))
'''
    subprocess.run(
        [sys.executable, '-B', '-c', command, str(source),
         'figs' if experiment == 6 else 'figures', str(target)],
        cwd=ROOT, check=True, capture_output=True,
    )
    assert {p.stem for p in target.glob('*.svg')} == set(INVENTORY[experiment].split())


@pytest.mark.parametrize('experiment', range(6, 10))
def test_digital_note_schematic_inventory_and_reproducibility(experiment, tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    draw_schematics(experiment, first)
    draw_schematics(experiment, second)
    for path in first.glob('*.svg'):
        assert path.read_bytes() == (second / path.name).read_bytes()


def test_dac_note_schematic_inventory_and_summing_node(tmp_path):
    draw_schematics(10, tmp_path)
    tree = ET.parse(tmp_path / 'summing.svg')
    dots = tree.findall(".//s:circle[@data-node='summing']", SVG_NS)
    label = tree.find(".//s:text[@data-node='summing']", SVG_NS)
    assert len(dots) == 4
    assert {dot.get('data-node-color') for dot in dots} == {label.get('data-node-color')} == {'red'}


@pytest.mark.parametrize('experiment', range(6, 11))
@pytest.mark.parametrize('width', (375, 1280))
@pytest.mark.parametrize('theme', ('light', 'dark'))
def test_published_note_schematic_sources_and_theme(chromium, experiment, width, theme):
    from os import environ

    name = f'실험{experiment:02}'
    folder = Path(environ.get('LAB_NOTE_STAGE_PARENT', ROOT / '복습노트')).resolve() / name
    note = folder / f'{name}_실험설명.html'
    md = folder / '.pack' / f'{name}_실험설명.md'
    if experiment == 6:
        assert 'figures/tff-from-jk-note.svg' in note.read_text()
        assert 'figures/tff-from-jk-note.svg' in md.read_text()
        for path in (folder / f'{name}_문제설명.html', folder / '.pack' / f'{name}_문제설명.md'):
            assert 'figures/tff-from-jk.svg' in path.read_text()
            assert 'figures/tff-from-jk-note.svg' not in path.read_text()

    with chromium.new_page(viewport={'width': width, 'height': 880}, color_scheme='light',
                           reduced_motion='reduce') as page:
        page.route(re.compile('^https?://'), lambda route: route.abort())
        page.goto(note.as_uri())
        if theme == 'dark':
            page.locator('#theme-toggle').click()
        assert page.locator('html').evaluate('(el) => getComputedStyle(el).colorScheme') == theme
        for figure in INVENTORY[experiment].split():
            images = page.locator(f'img[src=".pack/figures/{figure}.svg"]')
            assert images.count() > 0, figure
            for image in images.all():
                topic_id = image.evaluate("img => img.closest('article.topic').id")
                page.evaluate('(id) => location.hash = id', topic_id)
                image.wait_for(state='visible')
                image.evaluate('img => img.decode()')
                sizes = image.evaluate('''img => {
                    const viewport = img.closest('.schematic-viewport');
                    const outer = viewport.getBoundingClientRect();
                    const figure = img.closest('.figure').getBoundingClientRect();
                    viewport.scrollLeft = viewport.scrollWidth;
                    return {left: outer.left, right: outer.right, min: figure.left,
                        max: figure.right, natural: img.naturalWidth,
                        imageWidth: img.clientWidth, viewportWidth: viewport.clientWidth,
                        scrollLeft: viewport.scrollLeft,
                        maxScroll: viewport.scrollWidth - viewport.clientWidth};
                }''')
                assert sizes['natural'] > 0
                assert sizes['min'] - 1 <= sizes['left'] <= sizes['right'] <= sizes['max'] + 1
                assert 0 <= sizes['left'] and sizes['right'] <= width
                assert abs(sizes['maxScroll'] - sizes['scrollLeft']) <= 1
                if width == 375 and figure in ('internal', 'ram2bit', 'dac-block'):
                    assert sizes['imageWidth'] > sizes['viewportWidth']


@pytest.mark.parametrize('experiment', range(6, 11))
def test_published_note_viewboxes_contain_geometry(chromium, experiment):
    from os import environ

    name = f'실험{experiment:02}'
    folder = Path(environ.get('LAB_NOTE_STAGE_PARENT', ROOT / '복습노트')).resolve() / name
    with chromium.new_page() as page:
        for figure in INVENTORY[experiment].split():
            path = folder / '.pack' / 'figures' / f'{figure}.svg'
            page.goto(path.as_uri())
            result = page.evaluate('''async () => {
                await document.fonts.ready;
                const root = document.documentElement;
                const bounds = root.viewBox.baseVal;
                const toViewBox = root.getCTM().inverse();
                const clipped = [];
                for (const item of root.querySelectorAll('text, circle, polyline, path, rect')) {
                    if (item.matches('.fig-paper')) continue;
                    const box = item.getBBox();
                    const transform = toViewBox.multiply(item.getCTM());
                    const a = new DOMPoint(box.x, box.y).matrixTransform(transform);
                    const b = new DOMPoint(box.x + box.width, box.y + box.height).matrixTransform(transform);
                    if (a.x < bounds.x - 0.1 || a.y < bounds.y - 0.1 ||
                        b.x > bounds.x + bounds.width + 0.1 || b.y > bounds.y + bounds.height + 0.1) {
                        clipped.push(item.outerHTML);
                    }
                }
                return {clipped, fonts: Array.from(document.fonts, font => [font.weight, font.status])};
            }''')
            assert result['fonts'] == [['600', 'loaded']], figure
            assert not result['clipped'], (figure, result['clipped'])
