from pathlib import Path
from xml.etree import ElementTree as ET
import json
import re

ROOT = Path('docs/learning-pack-source/실험04')
NAMES = ['mux2-gates', 'mux4-enable', 'demux4-gates',
         'decoder-routing', 'tristate-bus', 'lab-signal-flow']

def test_experiment4_has_redrawn_note_figures():
    for name in NAMES:
        tree = ET.parse(ROOT/'figures'/f'{name}.svg')
        assert tree.getroot().get('viewBox')
        assert not any(n.tag.endswith('image') for n in tree.iter())
        assert any(n.tag.endswith('title') for n in tree.iter())
        assert not any(n.tag.endswith('script') for n in tree.iter())

def test_note_images_are_only_redrawn_vectors():
    from scripts.lab.review_pack.html2md import Parser
    manifest = json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
    images = []
    for row in manifest['topics']:
        text = (ROOT/row['fragment']).read_text(encoding='utf-8')
        assert not re.search('[ぁ-ゟァ-ヿ]', text)
        assert '이 개념으로 풀 문제' not in text
        parser = Parser(); parser.feed(text)
        for n in parser.root.walk():
            if n.tag == 'img':
                src = n.attrs['src']; images.append(src)
                assert src in {f'figures/{name}.svg' for name in NAMES}
                assert n.attrs.get('alt')
    assert set(images) == {f'figures/{name}.svg' for name in NAMES}
