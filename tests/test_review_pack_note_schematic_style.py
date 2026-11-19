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
