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

def polylines(name):
    tree = ET.parse(ROOT/'figures'/f'{name}.svg')
    return [[tuple(map(float, p.split(','))) for p in node.get('points').split()]
            for node in tree.iter() if node.tag.endswith('polyline')]

def test_mux2_wires_reach_curved_or_boundary():
    paths = [p for p in polylines('mux2-gates') if p[0][0] == 250]
    assert len(paths) == 2
    for path in paths:
        x, y = path[-1]
        # Quadratic input edge M390,175 Q420,215 390,255.
        t = (y-175)/80
        boundary_x = (1-t)**2*390 + 2*(1-t)*t*420 + t*t*390
        assert abs(x-boundary_x) < 0.1

def test_mux4_independent_outputs_do_not_cross():
    paths = [p for p in polylines('mux4-enable') if p[0][0] == 296]
    assert len(paths) == 4
    segments = [[(a,b) for a,b in zip(p,p[1:])] for p in paths]
    for i, first in enumerate(segments):
        for second in segments[i+1:]:
            for a,b in first:
                for c,d in second:
                    if a[0]==b[0] and c[1]==d[1]:
                        assert not (min(c[0],d[0])<=a[0]<=max(c[0],d[0]) and min(a[1],b[1])<=c[1]<=max(a[1],b[1]))
                    if a[1]==b[1] and c[0]==d[0]:
                        assert not (min(a[0],b[0])<=c[0]<=max(a[0],b[0]) and min(c[1],d[1])<=a[1]<=max(c[1],d[1]))
