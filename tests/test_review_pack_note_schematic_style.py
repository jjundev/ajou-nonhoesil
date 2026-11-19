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
